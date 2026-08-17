import bilby
from bilby.core.prior import PriorDict, Uniform, Constraint
import numpy as np
import matplotlib.pyplot as plt
import dill
import pickle
import os
import pandas as pd
import glob
from Bayes_HEP.Design_Points import plots as Plots

# ─────────────────────────────────────────────
# MAP Output
# ─────────────────────────────────────────────

def write_map_info(output_dir, system, em_type, sampler, map_vals, param_cols,
                   source, source_path, n_samples_extracted, log_prob_at_map,
                   log_evidence=None, log_evidence_err=None, ckpt=None):
    """Write MAP info to a txt file for provenance tracking."""

    calib_type = source_path.replace(f"{output_dir}/", "").split("/")[0]
    os.makedirs(f"{output_dir}/{calib_type}/map_info", exist_ok=True)
    out_path = f"{output_dir}/{calib_type}/map_info/{system}_{em_type}_{sampler}_map.txt"

    with open(out_path, "w") as f:
        f.write(f"MAP Info — {system} | {em_type} | {sampler}\n")
        f.write(f"{'='*60}\n")
        f.write(f"Source           : {source}\n")
        f.write(f"Source path      : {source_path}\n")
        f.write(f"N samples used   : {n_samples_extracted}\n")
        f.write(f"Log-prob at MAP  : {log_prob_at_map:.6f}\n")
        if log_evidence is not None:
            f.write(f"Log-evidence     : {log_evidence:.6f}\n")
        if log_evidence_err is not None:
            f.write(f"Log-evidence err : {log_evidence_err:.6f}\n")
        f.write(f"\nMAP Parameters:\n")
        for col, val in zip(param_cols, map_vals.flatten()):
            f.write(f"  {col:<20}: {val:.8f}\n")

        # sampler-specific diagnostics from checkpoint
        if ckpt is not None:
            f.write(f"\nCheckpoint Diagnostics:\n")
            if sampler == 'emcee':
                try:
                    chain = ckpt.get_chain()
                    f.write(f"  Steps completed  : {chain.shape[0]}\n")
                    f.write(f"  N walkers        : {chain.shape[1]}\n")
                    f.write(f"  N dim            : {chain.shape[2]}\n")
                    acc = np.mean(ckpt.acceptance_fraction)
                    f.write(f"  Mean acceptance  : {acc:.4f}\n")
                except Exception as e:
                    f.write(f"  [Could not extract emcee diagnostics: {e}]\n")
            else:  # nested
                try:
                    c = ckpt[0] if isinstance(ckpt, tuple) else ckpt
                    res = c.results
                    f.write(f"  Dead points      : {len(res.samples)}\n")
                    f.write(f"  Log-evidence     : {res.logz[-1]:.6f}\n")
                    f.write(f"  Log-evidence err : {res.logzerr[-1]:.6f}\n")
                    if hasattr(c, 'nlive'):
                        f.write(f"  N live points    : {c.nlive}\n")
                except Exception as e:
                    f.write(f"  [Could not extract dynesty diagnostics: {e}]\n")

    print(f"[MAP Info] Written to {out_path}")

    # --- new MAP .dat design file ---
    design_dir = f"{output_dir}/input_cleaned/Design"
    merged_dat_path = os.path.join(design_dir, f"Design__Rivet__Merged.dat")
    
    map_vals_flat = map_vals.flatten()
    # Read header lines from Merged.dat up to and including the last "# - Parameter" line
    header_lines = []
    with open(merged_dat_path, "r") as f:
        for line in f:
            if not line.startswith("#"):
                break
            if line.startswith("# Total Design") or line.startswith("# Design point indices"):
                continue  # skip these — we'll write our own
            header_lines.append(line)
    
    dat_path = os.path.join(design_dir, f"Design__Rivet__MAP.dat")

    with open(dat_path, "w") as f:
        f.writelines(header_lines)
        f.write("\n")
        f.write("# MAP values = 1\n")
        f.write("# Design point indices (row index): 0\n")
        row = " ".join(f"{v:.18e}" for v in map_vals_flat)
        f.write(row + "\n")

    print(f"[MAP Design] Written to {dat_path}")

# ─────────────────────────────────────────────
# Calibration
# ─────────────────────────────────────────────

def run_calibration(x, y_data_results, y_data_errors, priors, Emulators, output_dir, samplers, npool=5, Samples=1000, calb_type='calibration', scalers=None, cov_mode='diag'):
    """
    Run Bayesian calibration for all systems, emulator types, and samplers.

    For each combination a GaussianLikelihood is built using the emulator as a
    forward model, bilby runs the sampler, and MAP information is extracted and
    written to disk. A corner plot comparing all samplers is saved per system.
    """
    class GaussianLikelihood(bilby.Likelihood):
        def __init__(self, x, y, sigma, emulator, em_type, cov_mode, parameter_names):
            parameters = {name: None for name in parameter_names}
            super().__init__()
            self.x = x
            self.y = np.asarray(y)
            self.sigma = np.asarray(sigma)
            self.N = len(x)
            self.emulator = emulator
            self.em_type = em_type
            self.parameter_names = parameter_names

            if cov_mode not in ('diag', 'full'):
                raise ValueError(f"cov_mode must be 'diag' or 'full', got {cov_mode!r}")
            self.cov_mode = cov_mode

        def log_likelihood(self, parameters=None):
            if parameters is not None:
                self.parameters.update(parameters)

            params = np.array([self.parameters[key] for key in self.parameters])
            try:
                if self.em_type == 'surmise':
                    prediction = self.emulator.predict(self.x, params)
                    model = np.squeeze(prediction.mean().T)
                    
                elif self.em_type == 'scikit':
                    combined_result = []
                    params = np.atleast_1d(params)
                    repeated = np.tile(params, (self.x.shape[0], 1))
                    combined_result.append(np.hstack((self.x, repeated)))
                    combined_result = np.vstack(combined_result)
                    model, error = self.emulator.predict(combined_result, return_std=True)
                else:
                    print(f"[Unknown emulator type] {self.em_type}")
                    return -np.inf

                if self.cov_mode == 'diag':
                    log_l = self._log_likelihood_diag(prediction, model)
                else:
                    log_l = self._log_likelihood_full(prediction, model)

                if np.isnan(log_l) or np.isinf(log_l):
                    print("[Invalid LogL] NaN or inf detected in log-likelihood")
                    return -np.inf

                return log_l

            except Exception as e:
                print(f"[Likelihood Exception] {e}")
                return -np.inf

        def _log_likelihood_diag(self, prediction, model):
            """Original diagonal-only likelihood (Sigma_th = diag(var()))."""
            var = np.squeeze(prediction.var().T)
            var_safe = self.sigma**2 + var
            res = self.y - model
            return -0.5 * (np.sum(res**2 / var_safe) + np.sum(np.log(2 * np.pi * var_safe)))

        def _log_likelihood_full(self, prediction, model):
            """Full-covariance likelihood via Woodbury identity (Sigma_th = B @ B.T,
            low-rank from covxhalf())."""
            B = np.squeeze(prediction.covxhalf(), axis=1)
            d = self.sigma**2
            res = self.y - model
            n = len(res)
            k = B.shape[1]

            Dinv_res = res / d
            Dinv_B = B / d[:, None]

            M = np.eye(k) + B.T @ Dinv_B
            z = np.linalg.solve(M, B.T @ Dinv_res)

            quad_form = np.sum(res**2 / d) - (B.T @ Dinv_res) @ z
            sign, log_det_M = np.linalg.slogdet(M)
            log_det = log_det_M + np.sum(np.log(d))

            return -0.5 * (quad_form + log_det + n * np.log(2 * np.pi))

    results = dict()

    for system in x.keys():
        for em_type in Emulators:
            emulator = Emulators[em_type][system]

            if scalers is not None:
                y_data_scaled = scalers[system].transform(y_data_results[system].reshape(-1, 1)).flatten()
                sigma_scaled = y_data_errors[system] / scalers[system].scale_
            else:
                y_data_scaled = y_data_results[system]
                sigma_scaled = y_data_errors[system]

            likelihood = GaussianLikelihood(x[system], y_data_scaled, sigma_scaled, emulator, em_type, cov_mode, parameter_names=list(priors.keys()))

            for sampler in samplers:

                # Load pos0 for emcee warm restart if available
                extra_kwargs = {}
                if sampler == 'emcee':
                    pickle_path = f"{output_dir}/{calb_type}/{em_type}/{system}_results/emcee_emcee/sampler.pickle"
                    if not os.path.exists(pickle_path):
                        print(f"[pos0] No chain.dat found for {system} {em_type}, cold start.")
                    else:
                        print(f"[pos0] sampler.pickle found for {system} {em_type}, resume=True will handle restart.")

                Result = bilby.core.sampler.run_sampler(
                    likelihood=likelihood,
                    priors=priors,
                    sampler=sampler,
                    outdir=f"{output_dir}/{calb_type}/{em_type}/{system}_results",
                    label=sampler,
                    npool=npool,
                    resume=True,
                    clean=False,
                    verbose=False,
                    **samplers[sampler],
                    **extra_kwargs
                )
                results[em_type + '_' + sampler] = Result

                # --- MAP extraction ---
                try:
                    posterior = Result.posterior
                    param_cols = list(priors.keys())

                    if 'log_likelihood' in posterior.columns and 'log_prior' in posterior.columns:
                        log_prob = posterior['log_likelihood'] + posterior['log_prior']
                    elif 'log_likelihood' in posterior.columns:
                        log_prob = posterior['log_likelihood']
                    else:
                        print(f"Warning: no log_likelihood in posterior for {system}/{em_type}/{sampler} — skipping MAP extraction")
                        continue 

                    map_idx = log_prob.idxmax()
                    map_vals = posterior.loc[map_idx, param_cols].values
                    log_prob_at_map = log_prob[map_idx]
                    n_samples = len(posterior)

                    # extract Bayesian evidence (nested samplers only)
                    log_evidence = log_evidence_err = None
                    try:
                        if hasattr(Result, 'log_evidence') and Result.log_evidence is not None:
                            log_evidence = float(Result.log_evidence)
                        if hasattr(Result, 'log_evidence_err') and Result.log_evidence_err is not None:
                            log_evidence_err = float(Result.log_evidence_err)
                    except Exception:
                        pass

                    # load checkpoint for diagnostics
                    ckpt = None
                    if sampler == 'emcee':
                        pickle_path = f"{output_dir}/{calb_type}/{em_type}/{system}_results/emcee_emcee/sampler.pickle"
                        if os.path.exists(pickle_path):
                            with open(pickle_path, 'rb') as pf:
                                ckpt = pickle.load(pf)

                    write_map_info(
                        output_dir=output_dir,
                        system=system,
                        em_type=em_type,
                        sampler=sampler,
                        map_vals=map_vals,
                        param_cols=param_cols,
                        source='bilby_posterior',
                        source_path=f"{output_dir}/{calb_type}/{em_type}/{system}_results/{sampler}_result.json",
                        n_samples_extracted=n_samples,
                        log_prob_at_map=log_prob_at_map,
                        log_evidence=log_evidence,
                        log_evidence_err=log_evidence_err,
                        ckpt=ckpt,
                    )

                except Exception as e:
                    print(f"[MAP extraction failed] {system} {em_type} {sampler}: {e}")
                
               
                fig = bilby.core.result.plot_multiple(
                    list(results.values()),
                    labels=list(results.keys()),
                    save=True,
                    outdir=f'{system}.png'
                )
                plt.suptitle(system, fontsize=16)
                plt.savefig(f"{output_dir}/plots/{calb_type}/calibration_{system}.png", bbox_inches='tight')
                plt.close(fig)


# ─────────────────────────────────────────────
# Post-run Merge and Comparison
# ─────────────────────────────────────────────

def merge(Coll_System, Emulators, output_dir):
    """Load all saved sampler result JSONs and produce a combined corner plot per system."""
    for system in Coll_System:
        results = dict()
        sys = system if system == 'all' else system.replace('_', '')
        for em_type in Emulators:
            # Find all available json files
            json_files = glob.glob(f"{output_dir}/calibration/{em_type}/{sys}_results/*_result.json")
            
            for json_file in json_files:
                sampler = os.path.basename(json_file).replace("_result.json", "")
                
                Result = bilby.result.read_in_result(filename=json_file)
                results[em_type + '_' + sampler] = Result

            if len(results) <= 1:
                print(f"[merge] Need more than one result to compare for {sys}/{em_type}, skipping.")
                continue

            # Corner plot comparing samplers for this system/em_type
            fig = bilby.core.result.plot_multiple(
                list(results.values()),
                labels=list(results.keys()),
                save=True,
                outdir=f'{sys}.png'
            )
            plt.suptitle(system, fontsize=16)
            plt.savefig(f"{output_dir}/plots/calibration/calibration_{sys}.png", bbox_inches='tight')
            plt.close(fig)

def closure(Coll_System, Emulators, output_dir, closure_name, truths):
    """Load all saved sampler result JSONs and produce a combined corner plot per system."""

    cov_mode_order = {'full': 0, 'diag': 1}  # draw full first (larger band), diag drawn on top

    def sort_key(label):
        for cov_mode, priority in cov_mode_order.items():
            if cov_mode in label:
                return (priority, label)
        return (len(cov_mode_order), label)

    for system in Coll_System:
        results = dict()
        sys = system if system == 'all' else system.replace('_', '')
        for em_type in Emulators:
            # Find all available json files
            json_files = glob.glob(f"{output_dir}/{closure_name}/{em_type}/{sys}_results/*_result.json")
            
            for json_file in json_files:
                sampler = os.path.basename(json_file).replace("_result.json", "")
                
                Result = bilby.result.read_in_result(filename=json_file)
                results[em_type + '_' + sampler] = Result

            # order so 'full' is listed/drawn before 'diag'
            ordered_keys = sorted(results.keys(), key=sort_key)
            ordered_results = {k: results[k] for k in ordered_keys}

            # Corner plot comparing samplers for this system/em_type
            fig = bilby.core.result.plot_multiple(
                list(ordered_results.values()),
                labels=list(ordered_results.keys()),
                truth=truths,
                truth_color='black',
                save=True,
                outdir=f'{sys}.png'
            )
            plt.suptitle(system, fontsize=16)
            plt.savefig(f"{output_dir}/plots/{closure_name}/calibration_{sys}.png", bbox_inches='tight')
            plt.close(fig)