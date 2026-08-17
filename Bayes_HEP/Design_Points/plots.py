import os
import re
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import pandas as pd
import bilby
import pickle
import seaborn as sns
from collections import OrderedDict


# ─────────────────────────────────────────────
# Design Point Plots
# ─────────────────────────────────────────────

def plot_design_points(output_dir, train_points, validation_points, priors):
    """Corner-style scatter matrix showing train and validation point coverage."""
    param_names = list(priors.keys())  # Extract parameter names from priors
    num_params = len(param_names)  # Get the number of parameters
    n_train = len(train_points)
    n_val   = len(validation_points)

    fig, axes = plt.subplots(num_params, num_params, figsize=(15, 15))
    axes = axes.flatten()

    # Initialize variables to collect handles and labels for the legend
    handles, labels = None, None

    for i in range(num_params):
        for j in range(num_params):
            ax = axes[i * num_params + j]

            if j > i:
                ax.axis('off')  # Hide upper triangle plots
                continue

            if i == j:
                # Histogram for diagonal elements
                ax.hist(train_points[:, i], bins=20, alpha=0.5, label='Train', color='blue')
                ax.hist(validation_points[:, i], bins=20, alpha=0.5, label='Validation', color='orange')
                ax.set_ylabel('Frequency')

                # Collect handles and labels for the legend once
                if handles is None and labels is None:
                    handles, labels = ax.get_legend_handles_labels()
            else:
                # Scatter plot for lower triangle elements
                ax.scatter(train_points[:, j], train_points[:, i], alpha=0.5, label='Train', color='blue')
                ax.scatter(validation_points[:, j], validation_points[:, i], alpha=0.5, label='Validation', color='orange')

            # Set x and y labels dynamically
            if i == num_params - 1:  # Set x-axis label for the bottom row
                ax.set_xlabel(param_names[j], fontsize=14)
                ax.tick_params(axis='x', labelrotation=45)

            if j == 0:  # Set y-axis label for the first column
                ax.set_ylabel(param_names[i], fontsize=14)

    # Set a global legend
    labels = [f'Train (N={n_train})', f'Validation (N={n_val})']
    fig.legend(handles, labels, fontsize=20, loc='upper right', bbox_to_anchor=(.95, .95))
    plt.tight_layout(rect=[0, 0, 0.95, 1])
    plt.subplots_adjust(hspace=0.4, wspace=0.4)  # Adjust spacing
    plt.suptitle(f"Design Point Parameter Space", fontsize=18)
    os.makedirs(f"{output_dir}/plots", exist_ok=True)
    plt.savefig(f"{output_dir}/plots/Design_Points.png")


# ─────────────────────────────────────────────
# Emulator Validation Plots
# ─────────────────────────────────────────────

def plot_combined_box_rmspe(ax, y_true, predictions, label):
    """Box plot of RMSPE across design points for each emulator, normalised by mean true value."""
    y_true = np.asarray(y_true)   # (n_dp, n_bins)
 
    # Normalize by mean absolute true value per bin — consistent with
    # plot_rmspe_per_inspire and plot_rmspe_vs_emuvar
    mean_true = np.abs(y_true.mean(axis=0))                    # (n_bins,)
    mean_true = np.where(mean_true > 1e-10, mean_true, 1e-10)
 
    rmspe_list  = []
    tick_labels = []
 
    for emulator_name, pred in predictions.items():
        pred = np.asarray(pred)   # (n_dp, n_bins)
 
        # RMSPE per design point: RMS across bins of the per-bin % error
        rmspe_per_dp = (np.sqrt(np.mean(((pred - y_true) / mean_true) ** 2, axis=1))
                        * 100)   # (n_dp,)
 
        rmspe_list.append(rmspe_per_dp)
        tick_labels.append(emulator_name)
 
    ax.boxplot(rmspe_list, tick_labels=tick_labels, whis=[0, 100])
    ax.set_title(f'{label}', fontsize=20)
    ax.tick_params(axis='both', which='major', labelsize=20)
 
 
def plot_rmspe_comparison(y_train_results, y_val_results, PredictionTrain, PredictionVal, output_dir):
    """Side-by-side training and validation RMSPE box plots for all systems and emulators."""
    systems = list(y_train_results.keys())
    emulator_names = list(PredictionTrain.keys())
 
    emulator_types = sorted(set(name.split('_')[0] for name in emulator_names))
 
    ncols = len(systems)
    fig, axes = plt.subplots(2, ncols, figsize=(10 * ncols, 16), sharey='row')
 
    if ncols == 1:
        axes = axes.reshape(2, 1)
 
    for i, system in enumerate(systems):
        label = system.replace("_", "\n")
 
        train_preds = {emu: PredictionTrain[f"{emu}_train"][system] for emu in emulator_types}
        val_preds   = {emu: PredictionVal[f"{emu}_val"][system]   for emu in emulator_types}
 
        plot_combined_box_rmspe(axes[0, i], y_train_results[system], train_preds, label=label)
        plot_combined_box_rmspe(axes[1, i], y_val_results[system],   val_preds,   label=label)
 
    axes[0, 0].set_ylabel('Training RMSPE [%]',   fontsize=30)
    axes[1, 0].set_ylabel('Validation RMSPE [%]', fontsize=30)
 
    os.makedirs(f"{output_dir}/plots/emulators", exist_ok=True)
    plt.tight_layout()
    plt.savefig(f"{output_dir}/plots/emulators/RMSPE_Comparison.png")


# ─────────────────────────────────────────────
# Calibration / Posterior Plots
# ─────────────────────────────────────────────

def plot_prior_vs_posterior(result, output_dir, system, em_type, sampler):
    """Overlay prior and posterior for each parameter."""

    posterior = result.posterior
    params    = result.search_parameter_keys
    priors    = result.priors

    ncols = min(3, len(params))
    nrows = int(np.ceil(len(params) / ncols))
    fig, axes = plt.subplots(nrows, ncols,
                              figsize=(5 * ncols, 4 * nrows))
    axes = np.array(axes).flatten()

    for i, p in enumerate(params):
        ax    = axes[i]
        prior = priors[p]
        x_pr  = np.linspace(prior.minimum, prior.maximum, 200)
        y_pr  = [prior.prob(xi) for xi in x_pr]

        ax.plot(x_pr, y_pr, 'r--', lw=2, label='Prior')
        ax.hist(posterior[p], bins=40, density=True,
                alpha=0.6, color='steelblue', label='Posterior')

        lo, hi = np.percentile(posterior[p], [5, 95])
        ax.axvline(lo, color='steelblue', ls=':', lw=1.5, label='90% CI')
        ax.axvline(hi, color='steelblue', ls=':', lw=1.5)
        ax.axvline(posterior[p].median(), color='navy',
                   ls='-', lw=2, label='Median')

        ax.set_xlabel(p, fontsize=12)
        ax.set_ylabel('Density', fontsize=12)
        ax.legend(fontsize=9)

    for j in range(i + 1, len(axes)):
        axes[j].axis('off')

    plt.suptitle(f'Prior vs Posterior — {system} {em_type} {sampler}', fontsize=14)
    plt.tight_layout()

    os.makedirs(f"{output_dir}/plots/prior_posterior", exist_ok=True)
    plt.savefig(f"{output_dir}/plots/prior_posterior/prior_posterior_{system}_{em_type}_{sampler}.png",
                bbox_inches='tight')
    plt.close()

def plot_emcee_convergence(ckpt, output_dir, system, em_type):
    """Acceptance fraction and autocorrelation diagnostics."""

    chain    = ckpt.get_chain()          # (nsteps, nwalkers, ndim)
    log_prob = ckpt.get_log_prob()       # (nsteps, nwalkers)
    acc      = ckpt.acceptance_fraction  # (nwalkers,)

    fig, axes = plt.subplots(3, 1, figsize=(12, 10))

    # 1 — Log probability evolution
    axes[0].plot(log_prob, alpha=0.3, lw=0.5, color='steelblue')
    axes[0].plot(log_prob.mean(axis=1), color='red', lw=2, label='Mean')
    axes[0].set_ylabel('Log probability', fontsize=14)
    axes[0].set_xlabel('Step', fontsize=14)
    axes[0].legend()
    axes[0].set_title(f'Log Probability — {system} {em_type}', fontsize=14)

    # 2 — Acceptance fraction per walker
    axes[1].bar(range(len(acc)), acc, color='steelblue', alpha=0.7)
    axes[1].axhline(0.2, color='red',   lw=2, ls='--', label='Min (0.2)')
    axes[1].axhline(0.5, color='green', lw=2, ls='--', label='Max (0.5)')
    axes[1].set_ylabel('Acceptance fraction', fontsize=14)
    axes[1].set_xlabel('Walker', fontsize=14)
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].set_title(f'Acceptance Fraction — mean={acc.mean():.3f}', fontsize=14)

    # 3 — Running autocorrelation estimate
    try:
        import emcee
        nsteps  = chain.shape[0]
        n_check = np.arange(100, nsteps, 100)
        taus    = []
        for n in n_check:
            try:
                t = emcee.autocorr.integrated_time(
                    chain[:n], tol=0, quiet=True)
                taus.append(np.mean(t))
            except:
                taus.append(np.nan)
        axes[2].plot(n_check, taus, color='steelblue', lw=2)
        axes[2].plot(n_check, n_check / 50, color='red',
                     lw=2, ls='--', label='τ = N/50 (converged)')
        axes[2].set_ylabel('Mean autocorr time τ', fontsize=14)
        axes[2].set_xlabel('Steps', fontsize=14)
        axes[2].legend()
        axes[2].set_title('Convergence: need chain >> 50τ', fontsize=14)
    except Exception as e:
        axes[2].text(0.5, 0.5, f'Autocorr failed: {e}',
                     transform=axes[2].transAxes, ha='center')

    plt.tight_layout()
    os.makedirs(f"{output_dir}/plots/convergence", exist_ok=True)
    plt.savefig(
        f"{output_dir}/plots/convergence/emcee_convergence_{system}_{em_type}.png",
        bbox_inches='tight')
    plt.close()

def plot_posterior_covariance(result, output_dir, system, em_type, sampler):
    """Plot correlation matrix of posterior."""

    posterior = result.posterior
    params    = result.search_parameter_keys
    corr      = posterior[params].corr()

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm',
                center=0, vmin=-1, vmax=1, ax=ax,
                xticklabels=params, yticklabels=params)
    ax.set_title(f'Posterior Correlation — {system} {em_type} {sampler}', fontsize=14)
    plt.tight_layout()

    os.makedirs(f"{output_dir}/plots/correlation", exist_ok=True)
    plt.savefig(f"{output_dir}/plots/correlation/correlation_{system}_{em_type}_{sampler}.png",
                bbox_inches='tight')
    plt.close()


def print_posterior_summary(result, sampler, system, em_type):
    """Print useful posterior statistics after loading result."""
    posterior  = result.posterior
    params     = result.search_parameter_keys

    print(f"\n{'='*60}")
    print(f"Posterior Summary — {system} | {em_type} | {sampler}")
    print(f"{'='*60}")
    print(f"N samples          : {len(posterior)}")
    print(f"ln evidence        : {result.log_evidence:.4f} +/- {result.log_evidence_err:.4f}")

    print(f"\n{'Parameter':<15} {'Mean':>9} {'Std':>9} {'5%':>9} {'50%':>9} {'95%':>9} {'Prior%':>8}")
    print("-" * 65)
    for p in params:
        s      = posterior[p]
        lo, med, hi = np.percentile(s, [5, 50, 95])
        prior  = result.priors[p]
        width  = prior.maximum - prior.minimum
        constr = s.std() / width * 100
        flag   = " ⚠️" if constr > 80 else ""
        print(f"{p:<15} {s.mean():>9.4f} {s.std():>9.4f} "
              f"{lo:>9.4f} {med:>9.4f} {hi:>9.4f} {constr:>7.1f}%{flag}")

    # Correlation matrix
    corr = posterior[params].corr()
    print(f"\nCorrelation matrix:")
    print(corr.round(3).to_string())

    # Flag strong correlations
    print(f"\nStrong correlations (|r| > 0.7):")
    found = False
    for i, p1 in enumerate(params):
        for j, p2 in enumerate(params):
            if j <= i:
                continue
            r = corr.loc[p1, p2]
            if abs(r) > 0.7:
                print(f"  {p1} <-> {p2}: r={r:.3f}")
                found = True
    if not found:
        print("  None")


def plot_diagnostics(output_dir, x, Emulators, samplers, parameter_names):
    """
    Generate diagnostic plots for all systems, emulators, and samplers.

    emcee   : convergence (autocorr + acceptance) + prior vs posterior + correlation matrix
    dynesty : prior vs posterior + correlation matrix (no convergence plot)
    """

    for system in x.keys():
        for em_type in Emulators:
            for sampler in samplers:

                json_path = f"{output_dir}/calibration/{em_type}/{system}_results/{sampler}_result.json"
                pickle_candidates = [
                    f"{output_dir}/calibration/{em_type}/{system}_results/{sampler}_emcee/sampler.pickle",
                    f"{output_dir}/calibration/{em_type}/{system}_results/{sampler}_resume.pickle",
                ]
                pickle_path = next((p for p in pickle_candidates if os.path.exists(p)), None)

                print(f"\n[Diagnostics] {system} | {em_type} | {sampler}")

                # --- Load result and run shared plots ---
                if os.path.exists(json_path):
                    result = bilby.core.result.read_in_result(filename=json_path)
                    print_posterior_summary(result, sampler, system, em_type)
                    plot_prior_vs_posterior(result, output_dir, system, em_type, sampler)
                    plot_posterior_covariance(result, output_dir, system, em_type, sampler)
                else:
                    print(f"[Diagnostics] No JSON found — skipping shared plots")
                    result = None

                # --- Sampler-specific plots ---
                if sampler in MCMC_SAMPLERS:
                    if pickle_path:
                        with open(pickle_path, 'rb') as f:
                            ckpt = pickle.load(f)
                        plot_emcee_convergence(ckpt, output_dir, system, em_type)
                    elif result is not None and result.walkers is not None:
                        # reconstruct fake sampler object from result.walkers
                        # just plot the walker traces directly
                        _plot_walker_traces(
                            result.walkers, parameter_names,
                            output_dir, system, em_type
                        )
                    else:
                        print(f"[Diagnostics] No emcee pickle or walkers found")

                else:
                    print(f"[Diagnostics] Unknown sampler '{sampler}' — skipping")


def _plot_walker_traces(chain, parameter_names, output_dir, system, em_type):
    """Walker trace plot from chain array (nsteps, nwalkers, ndim)."""
    nsteps, nwalkers, ndim = chain.shape
    n_walkers_plot = min(10, nwalkers)

    fig, axes = plt.subplots(ndim, 1, figsize=(12, 2 * ndim), sharex=True)
    if ndim == 1:
        axes = [axes]

    for i, p in enumerate(parameter_names):
        for w in range(n_walkers_plot):
            axes[i].plot(chain[:, w, i], alpha=0.4, lw=0.7)
        axes[i].set_ylabel(p, fontsize=11)

    axes[-1].set_xlabel('Step', fontsize=11)
    plt.suptitle(f'Walker Traces — {system} {em_type}', fontsize=13)
    plt.tight_layout()

    os.makedirs(f"{output_dir}/plots/trace", exist_ok=True)
    plt.savefig(f"{output_dir}/plots/trace/walkers_{system}_{em_type}.png",
                bbox_inches='tight')
    plt.close()


# ─────────────────────────────────────────────
# Sampler Constants and Sample Extraction
# ─────────────────────────────────────────────

NESTED_SAMPLERS = {'dynesty', 'dynamic_dynesty', 'ultranest'}
MCMC_SAMPLERS   = {'emcee'}

def get_posterior_samples(sample_pool, size, sampler, result, posterior_threshold=0):
    """Draw samples for prediction bands.
    posterior_threshold: percentile cutoff e.g. 80 keeps top 20%, 85 keeps top 15%.
    Use 0 (default) to keep the full posterior, so the resulting band is a true CI.
    """

    if sampler in NESTED_SAMPLERS:
        # bilby already resamples nested-sampling output to equal weight
        # (dynesty.utils.resample_equal) before storing it as result.samples,
        # so no importance reweighting here — that would double-weight it.
        n = min(size, sample_pool.shape[0])
        rows = np.random.choice(
            sample_pool.shape[0],
            size=n,
            replace=False
        )
        return sample_pool[rows]

    elif sampler in MCMC_SAMPLERS:
        log_post = result.posterior["log_likelihood"].values + result.posterior["log_prior"].values
        threshold = np.percentile(log_post, posterior_threshold)
        high_mask = log_post >= threshold
        high_samples = sample_pool[high_mask]

        if len(high_samples) < 10:
            print(f"[Warning] Too few high-posterior samples above {posterior_threshold}th percentile, using all.")
            high_samples = sample_pool

        n = min(size, high_samples.shape[0])
        rows = np.random.choice(
            high_samples.shape[0],
            size=n,
            replace=False
        )
        return high_samples[rows]

    else:
        print(f"[Warning] Unknown sampler type '{sampler}' — no result file handling defined. Skipping.")
        return None


# ─────────────────────────────────────────────
# Results Plots
# ─────────────────────────────────────────────

def plot_uncertainty_comparison(x, all_data, y_data_results, y_data_errors, Emulators, samplers, output_dir):
    """Scatter plot of experimental vs emulator variance at the MAP, coloured by Inspire key."""
    for i, system in enumerate(x.keys()):
        for em_type in Emulators:
            for sampler in samplers:
                json_path = f"{output_dir}/calibration/{em_type}/{system}_results/{sampler}_result.json"

                result = bilby.core.result.read_in_result(filename=json_path)
                posterior   = result.posterior
                param_cols  = [c for c in posterior.columns if not c.startswith('log_')]
                log_post    = posterior['log_likelihood'] + posterior['log_prior']
                map_idx     = log_post.idxmax()
                map_params  = np.array([posterior.loc[map_idx, c] for c in param_cols]).reshape(1, -1)

                # Get emulator prediction at MAP
                pred_obj  = Emulators[em_type][system].predict(x[system], map_params)
                y_emu     = np.squeeze(pred_obj.mean())   # (n_bins,)
                var_emu   = np.squeeze(pred_obj.var())    # (n_bins,)

                y_exp     = np.asarray(y_data_results[system])   # mean experimental value
                var_exp   = np.asarray(y_data_errors[system])**2  # experimental variance

                # Scale both by y_exp * y_emu
                scale     = np.abs(y_exp * y_emu) + 1e-10
                x_scaled  = var_exp  / scale
                y_scaled  = var_emu  / scale

                # Color by Inspire group
                inspire_keys = []
                colors_map   = {}
                color_cycle  = plt.rcParams['axes.prop_cycle'].by_key()['color']
                for j_float in np.unique(x[system][:,0]):
                    j = int(j_float)
                    insp = all_data[system][j].get('Inspire','')
                    if insp not in colors_map:
                        colors_map[insp] = color_cycle[len(colors_map) % len(color_cycle)]

                bin_colors = []
                bin_inspire = []
                for idx in range(len(y_exp)):
                    j_vals = x[system][idx, 0]
                    j      = int(j_vals)
                    insp   = all_data[system][j].get('Inspire','')
                    bin_colors.append(colors_map[insp])
                    bin_inspire.append(insp)

                # Plot
                fig, ax = plt.subplots(figsize=(8, 7))

                for insp, color in colors_map.items():
                    mask = np.array(bin_inspire) == insp
                    ax.scatter(x_scaled[mask], y_scaled[mask],
                               color=color, alpha=0.6, s=25, label=insp, zorder=3)

                # Diagonal on log scale
                lim_min = min(x_scaled[x_scaled > 0].min(), y_scaled[y_scaled > 0].min()) * 0.5
                lim_max = max(x_scaled.max(), y_scaled.max()) * 2
                lims = [lim_min, lim_max]
                ax.plot(lims, lims, 'k--', lw=0.8, alpha=0.5)

                ax.set_xscale('log')
                ax.set_yscale('log')
                ax.set_xlim(lims); ax.set_ylim(lims)
                ax.set_xlabel(r'$\sigma^2_{\rm exp}/(y_{\rm exp}\,y_{\rm emu})$', fontsize=13)
                ax.set_ylabel(r'$\sigma^2_{\rm emu}/(y_{\rm exp}\,y_{\rm emu})$', fontsize=13)
                ax.set_title(f"Experimental vs Emulator Uncertainty — MAP_{sampler}", fontsize=14)
                ax.legend(fontsize=9, loc='upper left')

                plt.tight_layout()
                os.makedirs(f"{output_dir}/plots/emulators", exist_ok=True)
                plt.savefig(f"{output_dir}/plots/emulators/uncertainty_comparison_MAP_{sampler}.png", dpi=150, bbox_inches='tight')
                plt.show()


def plot_rmspe_per_inspire(y_val_results, PredictionVal, all_data, x,
                          output_dir, split_label='Validation'):
    """
    RMSPE per Inspire group — companion plot to plot_r2_per_observable.
    Same x-axis grouping so both plots can sit side by side in a paper.

    Summary plot  : one column per Inspire key, dots = RMSPE of individual bins.
    Detail plots  : one plot per Inspire key, one column per histogram (j),
                    dots = RMSPE of individual bins within that histogram.

    RMSPE is normalized by the mean absolute true value per bin (consistent
    with plot_rmspe_vs_emuvar) to avoid blow-up when individual y_t ~ 0.
    """
    systems        = list(y_val_results.keys())
    emulator_names = list(PredictionVal.keys())
    emulator_types = sorted(set(name.split('_')[0] for name in emulator_names))

    for system in systems:
        y_true   = np.asarray(y_val_results[system])   # (n_dp, n_bins)
        unique_j = np.unique(x[system][:, 0])
        N_val    = y_true.shape[0]

        # ── Build index structures ────────────────────────────────────────────
        inspire_groups = OrderedDict()
        for j_float in unique_j:
            j       = int(j_float)
            indices = np.where(x[system][:, 0] == j_float)[0]
            if len(indices) == 0:
                continue
            inspire = all_data[system][j].get('Inspire', f'j{j}')
            inspire_groups.setdefault(inspire, []).append((j, indices))

        inspire_keys = list(inspire_groups.keys())
        n_inspire    = len(inspire_keys)

        # ── Precompute RMSPE per bin per emulator ─────────────────────────────
        # Normalize by mean absolute true value per bin (not per point)
        # so bins near zero don't blow up, and results match plot_rmspe_vs_emuvar.
        rmspe_store = {}
        for em_type in emulator_types:
            key = f"{em_type}_val" if split_label == 'Validation' else f"{em_type}_train"
            if key not in PredictionVal or system not in PredictionVal[key]:
                continue
            pred = np.asarray(PredictionVal[key][system])   # (n_dp, n_bins)
            rmspe_store[em_type] = {}
            for j_float in unique_j:
                j       = int(j_float)
                indices = np.where(x[system][:, 0] == j_float)[0]
                if len(indices) == 0:
                    continue
                y_t       = y_true[:, indices]                          # (n_dp, k)
                p         = pred[:,  indices]                           # (n_dp, k)
                mean_true = np.abs(y_t.mean(axis=0))                   # (k,)
                mean_true = np.where(mean_true > 1e-10, mean_true, 1e-10)
                rmspe     = (np.sqrt(np.mean((y_t - p) ** 2, axis=0))
                             / mean_true * 100)                         # (k,) %
                rmspe_store[em_type][j] = rmspe

        if not rmspe_store:
            print(f"[RMSPE] No predictions for {system}, skipping.")
            continue

        colors   = plt.rcParams['axes.prop_cycle'].by_key()['color']
        em_color = {et: colors[k % len(colors)]
                    for k, et in enumerate(rmspe_store.keys())}
        n_em     = len(rmspe_store)
        offsets  = np.linspace(-0.2, 0.2, n_em) if n_em > 1 else [0.0]

        os.makedirs(f"{output_dir}/plots/emulators/rmspe_detail", exist_ok=True)

        # ── Summary: one column per Inspire key ──────────────────────────────
        x_pos = np.arange(n_inspire)
        fig, ax = plt.subplots(figsize=(max(8, n_inspire * 2.0), 7))

        for k, (em_type, rmspe_by_j) in enumerate(rmspe_store.items()):
            for i, inspire in enumerate(inspire_keys):
                all_rmspe = np.concatenate([rmspe_by_j[j]
                                            for j, _ in inspire_groups[inspire]
                                            if j in rmspe_by_j])
                valid = all_rmspe[np.isfinite(all_rmspe)]
                if len(valid) == 0:
                    continue
                np.random.seed(i)
                jitter = np.random.uniform(-0.08, 0.08, size=len(valid))
                ax.scatter(
                    np.full(len(valid), x_pos[i] + offsets[k]) + jitter,
                    valid,
                    color=em_color[em_type], alpha=0.65, s=35, zorder=3,
                    label=em_type if i == 0 else '_nolegend_'
                )

        bin_counts = [sum(len(idx) for _, idx in inspire_groups[k])
                      for k in inspire_keys]
        xlabels = [f"{k}\n({c} bins)" for k, c in zip(inspire_keys, bin_counts)]
        _finish_rmspe_ax(ax, x_pos, xlabels, split_label, N_val=N_val,
                         x_label='Inspire Key',
                         title=f'Emulator RMSPE per Publication — {system}')

        fname = (f"{output_dir}/plots/emulators/"
                 f"RMSPE_per_inspire_{system}_{split_label}.png")
        plt.tight_layout()
        plt.savefig(fname, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"[RMSPE] Summary saved: {fname}")

        # ── Detail: one plot per Inspire key ─────────────────────────────────
        for inspire in inspire_keys:
            hist_list = inspire_groups[inspire]
            n_hists   = len(hist_list)
            x_pos_d   = np.arange(n_hists)
            offsets_d = np.linspace(-0.2, 0.2, n_em) if n_em > 1 else [0.0]

            fig, ax = plt.subplots(figsize=(max(8, n_hists * 0.9), 7))

            for k, (em_type, rmspe_by_j) in enumerate(rmspe_store.items()):
                for i, (j, _) in enumerate(hist_list):
                    if j not in rmspe_by_j:
                        continue
                    valid = rmspe_by_j[j][np.isfinite(rmspe_by_j[j])]
                    if len(valid) == 0:
                        continue
                    np.random.seed(j)
                    jitter = np.random.uniform(-0.06, 0.06, size=len(valid))
                    ax.scatter(
                        np.full(len(valid), x_pos_d[i] + offsets_d[k]) + jitter,
                        valid,
                        color=em_color[em_type], alpha=0.75, s=40, zorder=3,
                        label=em_type if i == 0 else '_nolegend_'
                    )

            xtick_labels = []
            for j, _ in hist_list:
                histogram = all_data[system][j].get('Histogram', f'j{j}')
                obs       = all_data[system][j].get('Observable', '')
                obs_str   = " ".join(obs) if isinstance(obs, list) else str(obs)
                obs_clean = re.sub(r'\\[a-zA-Z]+\{?|\}|\$|\{|\\,|\\;',
                                   '', obs_str).strip()[:25]
                xtick_labels.append(f"{histogram}\n{obs_clean}")

            _finish_rmspe_ax(ax, x_pos_d, xtick_labels, split_label, N_val=N_val,
                             x_label='Histogram',
                             title=f'RMSPE Detail — {inspire} — {system}',
                             fontsize=8)

            safe_inspire = inspire.replace('/', '_')
            fname_d = (f"{output_dir}/plots/emulators/rmspe_detail/"
                       f"RMSPE_{safe_inspire}_{system}_{split_label}.png")
            plt.tight_layout()
            plt.savefig(fname_d, dpi=150, bbox_inches='tight')
            plt.close(fig)
            print(f"[RMSPE] Detail saved: {fname_d}")


def _finish_rmspe_ax(ax, x_pos, labels, split_label, N_val,
                     x_label, title, fontsize=10):
    """Shared axis finishing for RMSPE plots."""
    ax.axhline(0.0, color='black', lw=0.8, ls='--', alpha=0.4)
    for xp in x_pos[:-1]:
        ax.axvline(xp + 0.5, color='lightgray', lw=0.6, zorder=0)
    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=fontsize, rotation=30, ha='right')
    ax.set_ylabel(f'RMSPE [%] ({split_label})', fontsize=14)
    ax.set_xlabel(x_label, fontsize=14)
    ax.set_title(title, fontsize=14)
    ax.set_ylim(bottom=0)
    ax.set_xlim(-0.5, len(x_pos) - 0.5)
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    ax.text(0.98, 0.98, f'$N_{{\\rm val}} = {N_val}$',
            transform=ax.transAxes, fontsize=12,
            ha='right', va='top',
            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7))

def plot_rmspe_vs_emuvar(y_val_results, PredictionVal, all_data, x, Emulators,
                         validation_points, output_dir, split_label='Validation'):
    """
    For every histogram j in every system, plot RMSPE (validation) vs
    emulator uncertainty estimate (GP predicted std), both in percent.

    RMSPE and emulator uncertainty are both normalized by the mean absolute
    true value per bin so they are directly comparable on the same axis.

    Emulator uncertainty is the GP predictive std at the validation parameter
    points (not MAP), averaged over those points per bin.
    """
    systems        = list(y_val_results.keys())
    emulator_names = list(PredictionVal.keys())
    emulator_types = sorted(set(name.split('_')[0] for name in emulator_names))

    for system in systems:
        y_true   = np.asarray(y_val_results[system])   # (n_dp, n_bins)
        unique_j = np.unique(x[system][:, 0])

        # ── GP predictive std at validation parameter points ──────────────────
        # validation_points is shared across systems (not keyed by system).
        # var().T gives (n_val, n_bins); sqrt → std per validation point per bin.
        emu_std_store = {}
        for em_type in emulator_types:
            pred_obj = Emulators[em_type][system].predict(x=x[system],
                                                          theta=validation_points)
            var = np.squeeze(pred_obj.var().T)              # (n_val, n_bins)
            emu_std_store[em_type] = np.sqrt(var)           # (n_val, n_bins)

        # ── Validation predictions from PredictionVal ─────────────────────────
        val_pred_store = {}
        for em_type in emulator_types:
            key = f"{em_type}_val" if split_label == 'Validation' else f"{em_type}_train"
            val_pred_store[em_type] = np.asarray(PredictionVal[key][system])

        # ── Loop over every histogram j ───────────────────────────────────────
        for j_float in unique_j:
            j       = int(j_float)
            indices = np.where(x[system][:, 0] == j_float)[0]
            if len(indices) == 0:
                continue

            inspire       = all_data[system][j]["Inspire"]
            histogram     = all_data[system][j]["Histogram"]
            observable    = all_data[system][j]["Observable"]
            subobservable = all_data[system][j]["Subobservable"]

            if isinstance(subobservable, (list, tuple)):
                subobservable = " ".join(subobservable).strip()
            if isinstance(observable, (list, tuple)):
                observable = " ".join(observable).strip()

            x_vals = x[system][indices, 1]
            y_t    = y_true[:, indices]       # (n_val, k)
            N_val  = y_t.shape[0]

            # Shared normalization for both quantities
            mean_true = np.abs(y_t.mean(axis=0))                     # (k,)
            mean_true = np.where(mean_true > 1e-10, mean_true, 1e-10)

            fig, ax = plt.subplots(figsize=(7, 5))
            colors = plt.rcParams['axes.prop_cycle'].by_key()['color']

            for k, em_type in enumerate(emulator_types):
                p = val_pred_store[em_type][:, indices]               # (n_val, k)

                # RMSPE: RMS over validation points, normalized by mean true
                rmspe_pct = (np.sqrt(np.mean((y_t - p) ** 2, axis=0))
                             / mean_true * 100)                       # (k,)

                color = colors[k % len(colors)]
                ax.plot(x_vals, rmspe_pct, 's-', color=color,
                        label=f'{em_type} RMSPE (validation)', markersize=7)

                # Emulator uncertainty: GP std at validation points,
                # averaged over validation points, normalized by mean true
                if em_type in emu_std_store:
                    emu_std = emu_std_store[em_type][:, indices]      # (n_val, k)
                    emu_pct = emu_std.mean(axis=0) / mean_true * 100  # (k,)
                    ax.plot(x_vals, emu_pct, 's--', color=color,
                            fillstyle='none',
                            label=f'{em_type} uncertainty estimate', markersize=7)

            ax.set_xlabel(subobservable, fontsize=13)
            ax.set_ylabel('Uncertainty [%]', fontsize=13)
            ax.set_title(f'{histogram} — {observable} — {system}', fontsize=12)
            ax.text(0.98, 0.02, f'$N_{{\\rm val}} = {N_val}$',
                    transform=ax.transAxes, fontsize=11,
                    ha='right', va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3',
                              facecolor='white', alpha=0.7))
            ax.legend(fontsize=10)
            ax.grid(alpha=0.3)

            safe_inspire = inspire.replace('/', '_')
            save_dir = (f"{output_dir}/plots/emulators/rmspe_emuvar/"
                        f"{safe_inspire}")
            os.makedirs(save_dir, exist_ok=True)
            fname = f"{save_dir}/{system}_{histogram}.png"
            plt.tight_layout()
            plt.savefig(fname, dpi=150, bbox_inches='tight')
            plt.close(fig)

        print(f"[rmspe_emuvar] {system} done — "
              f"{len(unique_j)} histograms saved to "
              f"{output_dir}/plots/emulators/rmspe_emuvar/")
        

def results(size, x, all_data, y_data_results, y_data_errors, Emulators, samplers,
            n_hist, output_dir, scalers=None, band_threshold=90, 
            design_points=None, result_type='calibration', legend=True):
    """
    Main results plot: posterior band, MAP prediction, prior band, and data for every histogram.

    design_points : optional array (n_design, n_params) — if provided, the emulator is
                    evaluated at all design points to show the prior predictive band.
    """
    multi_emulator = len(Emulators) > 1
    multi_sampler  = len(samplers) > 1

    band_upper = 100 - (100 - band_threshold) / 2
    band_lower = (100 - band_threshold) / 2

    maps = {}
    for i, system in enumerate(x.keys()):

        predictions = {}
        maps[system] = {}

        # ── prior band (emulator) ────────────────────────────
        prior_predictions = {}   # em_type -> array (n_bins_total, size)
        if design_points is not None:
            dp = design_points
            for em_type in Emulators:
                if em_type == 'surmise':
                    prior_pred = Emulators[em_type][system].predict(x[system], dp).mean()
                    if scalers is not None:
                        prior_pred = scalers[system].inverse_transform(prior_pred)

                    # shape: (n_bins_total, size)
                    prior_predictions[em_type] = prior_pred

                elif em_type == 'scikit':
                    combined = []
                    for sample in dp:
                        sample = np.atleast_1d(sample)
                        repeated = np.tile(sample, (x[system].shape[0], 1))
                        combined.append(np.hstack((x[system], repeated)))
                    combined = np.vstack(combined)
                    flat = Emulators[em_type][system].predict(combined)
                    prior_pred = np.asarray(flat).reshape(dp.shape[0], x[system].shape[0]).T
                    prior_predictions[em_type] = prior_pred

        # ── posterior samples ─────────────────
        for em_type in Emulators:
            predictions[em_type] = {}
            maps[system][em_type]= {}
            for sampler in samplers:

                json_path = f"{output_dir}/{result_type}/{em_type}/{system}_results/{sampler}_result.json"

                if os.path.exists(json_path):
                    result = bilby.core.result.read_in_result(filename=json_path)
                    sample_pool = result.samples
                    if sample_pool is None or len(sample_pool) == 0:
                        print(f"[Results] Empty samples for {system} {em_type} {sampler}, skipping.")
                        continue
                    posterior = result.posterior
                    log_post = posterior["log_likelihood"] + posterior["log_prior"]
                    param_cols = result.search_parameter_keys

                    idx = log_post.values.argmax()
                    map_vals = np.array([posterior.iloc[idx][col] for col in param_cols]).reshape(1, -1)
                    log_prob_at_map = log_post.iloc[idx]
                    
                    samples = get_posterior_samples(sample_pool, size, sampler, result)
                    if samples is None:
                        continue
                    
                    maps[system][em_type][sampler] = map_vals

                else:
                    print(f"[Results] No result file for {system} {em_type} {sampler}, skipping.")
                    continue

                if em_type == 'surmise':
                    post = Emulators[em_type][system].predict(x[system], samples).mean()
                    map_pred = Emulators[em_type][system].predict(x[system], map_vals).mean()
                    if scalers is not None:
                        post = scalers[system].inverse_transform(post)
                        map_pred = scalers[system].inverse_transform(map_pred)

                elif em_type == 'scikit':
                    combined_result = []
                    for sample in samples:
                        sample = np.atleast_1d(sample)
                        repeated = np.tile(sample, (x[system].shape[0], 1))
                        combined_result.append(np.hstack((x[system], repeated)))
                    combined_result = np.vstack(combined_result)
                    post_flat = Emulators[em_type][system].predict(combined_result)
                    post = np.asarray(post_flat).reshape(samples.shape[0], x[system].shape[0]).T
                    map_combined = np.hstack((x[system], np.tile(map_vals, (x[system].shape[0], 1))))
                    map_pred = Emulators[em_type][system].predict(map_combined)

                predictions[em_type][sampler] = (post, map_pred)

        # ── plotting ──────────────────────────────────────────────────────────
        for j in range(n_hist[system]):
            fig, ax = plt.subplots(figsize=(10, 8))
            handles, labels = [], []
            legend_added_for = set()

            x_param = x[system][x[system][:, 0] == j]
            x_val   = x_param[:, 1]
            start   = sum(len(x[system][x[system][:, 0] == k]) for k in range(j))
            nbins   = len(x_param)
            end     = start + nbins

            observable    = all_data[system][j]["Observable"]
            subobservable = all_data[system][j]["Subobservable"]
            experiment    = all_data[system][j]["Experiment"].upper()
            energy        = all_data[system][j]["Energy"]
            inspire       = all_data[system][j]["Inspire"]
            histogram     = all_data[system][j]["Histogram"]
            plot_title    = all_data[system][j]["Title"]

            # ── prior band (one per emulator, drawn first so it sits behind) ──
            for em_type in Emulators:
                if em_type not in prior_predictions:
                    continue
                prior_slice = prior_predictions[em_type][start:end, :]   # (nbins, n_design)
                prior_lo  = np.percentile(prior_slice, band_lower,  axis=1)
                prior_hi  = np.percentile(prior_slice, band_upper, axis=1)

                fill_prior = ax.fill_between(
                    x_val, prior_lo, prior_hi,
                    alpha=0.15, color='gray',
                    label=f'{em_type} prior'
                )
                if f'prior_{em_type}' not in legend_added_for:
                    handles.append(fill_prior)
                    labels.append(f'{em_type.capitalize()} {band_threshold:g}% Prior' if multi_emulator else f'{band_threshold:g}% Prior')
                    legend_added_for.add(f'prior_{em_type}')

            # ── posterior band + MAP (your original code, unchanged) ──────────
            for em_type in Emulators:
                for sampler in samplers:
                    if sampler not in predictions[em_type]:
                        continue
                    
                    post, map_pred = predictions[em_type][sampler]
                    post_slice = post[start:end, :]
                    map_slice  = map_pred[start:end]

                    upper  = np.percentile(post_slice.T, band_upper, axis=0)
                    lower  = np.percentile(post_slice.T, band_lower,  axis=0)

                    label_key = f"{em_type}_{sampler}"

                    color = ax._get_lines.get_next_color()
                    ax.fill_between(x_val, lower, upper,
                                    alpha=0.3, color=color)
                    line_map = ax.plot(x_val, map_slice,
                                       linestyle='--', color=color)

                    if label_key not in legend_added_for:
                        band_handle = Patch(
                            facecolor=color,
                            alpha=0.3
                        )
                        prefix = f'{em_type.capitalize()} ' if multi_emulator else ''
                        suffix = f' [{sampler}]' if multi_sampler else ''
                        handles.append(band_handle)
                        labels.append(f'{prefix}{band_threshold:g}% C.I.{suffix}')
                        handles.append(line_map[0])
                        labels.append(f'{prefix}MAP{suffix}')
                        legend_added_for.add(label_key)

            # ── data ────────────────────────────────────────────────────────

            if result_type == 'calibration':
                label_tag=f'{experiment} Data'
            else:
                label_tag=f'Truth'

            line_err = ax.errorbar(
                x_val,
                y_data_results[system][start:end],
                yerr=[y_data_errors[system][start:end], y_data_errors[system][start:end]],
                color='black', fmt='o', markersize=6, capsize=3,
                label=label_tag
            )
            if 'data' not in legend_added_for:
                handles.append(line_err)
                labels.append(label_tag)
                legend_added_for.add('data')

            if isinstance(plot_title, (list, tuple)):
                plot_title = " ".join(plot_title).strip()
            if isinstance(subobservable, (list, tuple)):
                subobservable = " ".join(subobservable).strip()
            if isinstance(observable, (list, tuple)):
                observable = " ".join(observable).strip()

            ax.set_title(plot_title, fontsize=24)
            ax.set_ylabel(observable, fontsize=24)
            ax.set_xlabel(subobservable, fontsize=24)

            x_scale = all_data[system][j].get("XScale", None)
            y_scale = all_data[system][j].get("YScale", None)
            x_lims  = all_data[system][j].get("XLims",  None)
            y_lims  = all_data[system][j].get("YLims",  None)

            if x_scale is not None:
                ax.set_xscale(x_scale)
            if y_scale is not None:
                ax.set_yscale(y_scale)
            if x_lims is not None:
                ax.set_xlim(x_lims)
            if y_lims is not None:
                ax.set_ylim(y_lims)

            os.makedirs(f"{output_dir}/plots/{result_type}/results_{system}/{inspire}", exist_ok=True)
            if legend:
                ax.legend(handles, labels, loc='upper left',
                    bbox_to_anchor=(1.02, 1), borderaxespad=0, fontsize=16)
            plt.savefig(f"{output_dir}/plots/{result_type}/results_{system}/{inspire}/{histogram}.png",
                        bbox_inches='tight')
            plt.close(fig)

def combined_results(size, x, all_data, y_data_results, y_data_errors, Emulators, samplers,
                      n_hist, output_dir, scalers=None, band_threshold=90,
                      design_points=None, result_type='calibration', legend=True):
    """
    Same as results(), but overlays multiple likelihood variants (e.g. diagonal vs
    full-covariance) that were sampled with the same emulator and live in the same
    {sampler}_results directory, named {sampler}_{cov_mode}_result.json
    (e.g. dynesty_diag_result.json, dynesty_full_result.json).

    cov_modes are discovered automatically per system/em_type by scanning the
    result directory -- nothing needs to be passed in. 'full' is always drawn
    before 'diag' so the (larger) full-covariance band sits behind the
    (narrower) diagonal band rather than covering it.
    """
    multi_emulator = len(Emulators) > 1
    multi_sampler  = len(samplers) > 1

    band_upper = 100 - (100 - band_threshold) / 2
    band_lower = (100 - band_threshold) / 2

    cov_mode_order = {'full': 0, 'diag': 1}   # draw full first (bigger band, behind)

    for i, system in enumerate(x.keys()):

        predictions = {}
        cov_modes = {}   # em_type -> sorted list of cov_mode strings found

        # ── prior band (emulator) ────────────────────────────
        prior_predictions = {}   # em_type -> array (n_bins_total, size)
        if design_points is not None:
            dp = design_points
            for em_type in Emulators:
                if em_type == 'surmise':
                    prior_pred = Emulators[em_type][system].predict(x[system], dp).mean()
                    if scalers is not None:
                        prior_pred = scalers[system].inverse_transform(prior_pred)

                    # shape: (n_bins_total, size)
                    prior_predictions[em_type] = prior_pred

                elif em_type == 'scikit':
                    combined = []
                    for sample in dp:
                        sample = np.atleast_1d(sample)
                        repeated = np.tile(sample, (x[system].shape[0], 1))
                        combined.append(np.hstack((x[system], repeated)))
                    combined = np.vstack(combined)
                    flat = Emulators[em_type][system].predict(combined)
                    prior_pred = np.asarray(flat).reshape(dp.shape[0], x[system].shape[0]).T
                    prior_predictions[em_type] = prior_pred

        # ── posterior samples ─────────────────
        for em_type in Emulators:
            predictions[em_type] = {}

            json_dir = f"{output_dir}/{result_type}/{em_type}/{system}_results"
            found = set()
            if os.path.isdir(json_dir):
                for sampler in samplers:
                    pat = re.compile(rf"^{re.escape(sampler)}_(.+)_result\.json$")
                    for fname in os.listdir(json_dir):
                        m = pat.match(fname)
                        if m:
                            found.add(m.group(1))
            cov_modes[em_type] = sorted(found, key=lambda c: (cov_mode_order.get(c, 99), c))

            for cov_mode in cov_modes[em_type]:
                predictions[em_type][cov_mode] = {}
                for sampler in samplers:

                    json_path = f"{json_dir}/{sampler}_{cov_mode}_result.json"

                    if os.path.exists(json_path):
                        result = bilby.core.result.read_in_result(filename=json_path)
                        sample_pool = result.samples
                        if sample_pool is None or len(sample_pool) == 0:
                            print(f"[Results] Empty samples for {system} {em_type} {cov_mode} {sampler}, skipping.")
                            continue
                        posterior = result.posterior
                        log_post = posterior["log_likelihood"] + posterior["log_prior"]
                        param_cols = result.search_parameter_keys

                        idx = log_post.values.argmax()
                        map_vals = np.array([posterior.iloc[idx][col] for col in param_cols]).reshape(1, -1)
                        log_prob_at_map = log_post.iloc[idx]

                        samples = get_posterior_samples(sample_pool, size, sampler, result)
                        if samples is None:
                            continue

                    else:
                        print(f"[Results] No result file for {system} {em_type} {cov_mode} {sampler}, skipping.")
                        continue

                    if em_type == 'surmise':
                        post = Emulators[em_type][system].predict(x[system], samples).mean()
                        map_pred = Emulators[em_type][system].predict(x[system], map_vals).mean()
                        if scalers is not None:
                            post = scalers[system].inverse_transform(post)
                            map_pred = scalers[system].inverse_transform(map_pred)

                    elif em_type == 'scikit':
                        combined_result = []
                        for sample in samples:
                            sample = np.atleast_1d(sample)
                            repeated = np.tile(sample, (x[system].shape[0], 1))
                            combined_result.append(np.hstack((x[system], repeated)))
                        combined_result = np.vstack(combined_result)
                        post_flat = Emulators[em_type][system].predict(combined_result)
                        post = np.asarray(post_flat).reshape(samples.shape[0], x[system].shape[0]).T
                        map_combined = np.hstack((x[system], np.tile(map_vals, (x[system].shape[0], 1))))
                        map_pred = Emulators[em_type][system].predict(map_combined)

                    predictions[em_type][cov_mode][sampler] = (post, map_pred)

        # ── plotting ──────────────────────────────────────────────────────────
        for j in range(n_hist[system]):
            fig, ax = plt.subplots(figsize=(10, 8))
            handles, labels = [], []
            legend_added_for = set()

            x_param = x[system][x[system][:, 0] == j]
            x_val   = x_param[:, 1]
            start   = sum(len(x[system][x[system][:, 0] == k]) for k in range(j))
            nbins   = len(x_param)
            end     = start + nbins

            observable    = all_data[system][j]["Observable"]
            subobservable = all_data[system][j]["Subobservable"]
            experiment    = all_data[system][j]["Experiment"].upper()
            energy        = all_data[system][j]["Energy"]
            inspire       = all_data[system][j]["Inspire"]
            histogram     = all_data[system][j]["Histogram"]
            plot_title    = all_data[system][j]["Title"]

            # ── prior band (one per emulator, drawn first so it sits behind) ──
            for em_type in Emulators:
                if em_type not in prior_predictions:
                    continue
                prior_slice = prior_predictions[em_type][start:end, :]   # (nbins, n_design)
                prior_lo  = np.percentile(prior_slice, band_lower,  axis=1)
                prior_hi  = np.percentile(prior_slice, band_upper, axis=1)

                fill_prior = ax.fill_between(
                    x_val, prior_lo, prior_hi,
                    alpha=0.15, color='gray',
                    label=f'{em_type} prior'
                )
                if f'prior_{em_type}' not in legend_added_for:
                    handles.append(fill_prior)
                    labels.append(f'{em_type.capitalize()} {band_threshold:g}% Prior' if multi_emulator else f'{band_threshold:g}% Prior')
                    legend_added_for.add(f'prior_{em_type}')

            # ── posterior band + MAP (full drawn first, diag drawn on top) ─────
            for em_type in Emulators:
                for cov_mode in cov_modes[em_type]:
                    for sampler in samplers:
                        if sampler not in predictions[em_type][cov_mode]:
                            continue

                        post, map_pred = predictions[em_type][cov_mode][sampler]
                        post_slice = post[start:end, :]
                        map_slice  = map_pred[start:end]

                        upper  = np.percentile(post_slice.T, band_upper, axis=0)
                        lower  = np.percentile(post_slice.T, band_lower,  axis=0)

                        label_key = f"{em_type}_{cov_mode}_{sampler}"

                        color = ax._get_lines.get_next_color()
                        ax.fill_between(x_val, lower, upper,
                                        alpha=0.3, color=color)
                        line_map = ax.plot(x_val, map_slice,
                                           linestyle='--', color=color)

                        if label_key not in legend_added_for:
                            band_handle = Patch(
                                facecolor=color,
                                alpha=0.3
                            )
                            prefix = f'{em_type.capitalize()} ' if multi_emulator else ''
                            prefix = f'{cov_mode.capitalize()} ' + prefix
                            suffix = f' [{sampler}]' if multi_sampler else ''
                            handles.append(band_handle)
                            labels.append(f'{prefix}{band_threshold:g}% C.I.{suffix}')
                            handles.append(line_map[0])
                            labels.append(f'{prefix}MAP{suffix}')
                            legend_added_for.add(label_key)

            # ── data ────────────────────────────────────────────────────────

            if result_type == 'calibration':
                label_tag=f'{experiment} Data'
            else:
                label_tag=f'Truth'

            line_err = ax.errorbar(
                x_val,
                y_data_results[system][start:end],
                yerr=[y_data_errors[system][start:end], y_data_errors[system][start:end]],
                color='black', fmt='o', markersize=6, capsize=3,
                label=label_tag
            )
            if 'data' not in legend_added_for:
                handles.append(line_err)
                labels.append(label_tag)
                legend_added_for.add('data')

            if isinstance(plot_title, (list, tuple)):
                plot_title = " ".join(plot_title).strip()
            if isinstance(subobservable, (list, tuple)):
                subobservable = " ".join(subobservable).strip()
            if isinstance(observable, (list, tuple)):
                observable = " ".join(observable).strip()

            ax.set_title(plot_title, fontsize=24)
            ax.set_ylabel(observable, fontsize=24)
            ax.set_xlabel(subobservable, fontsize=24)

            x_scale = all_data[system][j].get("XScale", None)
            y_scale = all_data[system][j].get("YScale", None)
            x_lims  = all_data[system][j].get("XLims",  None)
            y_lims  = all_data[system][j].get("YLims",  None)

            if x_scale is not None:
                ax.set_xscale(x_scale)
            if y_scale is not None:
                ax.set_yscale(y_scale)
            if x_lims is not None:
                ax.set_xlim(x_lims)
            if y_lims is not None:
                ax.set_ylim(y_lims)

            os.makedirs(f"{output_dir}/plots/{result_type}/results_{system}/{inspire}", exist_ok=True)
            if legend:
                ax.legend(handles, labels, loc='upper left',
                    bbox_to_anchor=(1.02, 1), borderaxespad=0, fontsize=16)
            plt.savefig(f"{output_dir}/plots/{result_type}/results_{system}/{inspire}/{histogram}.png",
                        bbox_inches='tight')
            plt.close(fig)