from Bayes_HEP.Design_Points import reader as Reader
from Bayes_HEP.Design_Points import design_points as DesignPoints
from Bayes_HEP.Design_Points import plots as Plots
from Bayes_HEP.Design_Points import data_pred as DataPred
from Bayes_HEP.Emulation import emulation as Emulation
from Bayes_HEP.Calibration import calibration as Calibration
from Bayes_HEP.Design_Points import rivet_html_parser as RivetParser
from Bayes_HEP.Design_Points import html_report as HtmlReport
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler

import argparse
import glob
import os
import shutil
import matplotlib.pyplot as plt
import dill
import numpy as np

# ─────────────────────────────────────────────
# CLI Arguments
# ─────────────────────────────────────────────
def bool_arg(x):
    return str(x).lower() in ['true', '1', 'yes', 'y']

parser = argparse.ArgumentParser(description="Run Bayesian Emulator and Calibration workflow.")

parser.add_argument("--work_dir", type=str, default=None,
    help="Top-level working directory (default: $WORKDIR or /workdir)")
parser.add_argument("--main_dir", type=str, default=None,
    help="Project main directory (default: <work_dir>/New_Project)")
parser.add_argument("--input_dir", type=str, default=None)
parser.add_argument("--output_dir", type=str, default=None)
parser.add_argument("--clear_output", type=bool_arg, default=True)
parser.add_argument("--clean_input", type=bool_arg, default=True)
parser.add_argument("--Coll_System", nargs="+", default=["pp_7000"],
    help="List of collision systems (e.g. pp_7000 pPb_5020)")
parser.add_argument("--model", type=str, default="pythia8")
parser.add_argument("--train_size", type=int, default=80,
    help="Number of design points for training")
parser.add_argument("--validation_size", type=int, default=20,
    help="Number of design points for validation")
parser.add_argument("--Train_Surmise", type=bool_arg, default=False)
parser.add_argument("--Load_Surmise", type=bool_arg, default=False)
parser.add_argument("--scaler_type", type=str, default=None,
    help="Type of scaler: StandardScaler, MinMaxScaler, RobustScaler, or None")
parser.add_argument("--PCA", type=bool_arg, default=True)
parser.add_argument("--Closure_Test", type=bool_arg, default=False)
parser.add_argument("--closure_index", type=int, default=0,
    help="Index number for closure test. 0-validation_size")
parser.add_argument("--Closure_plots", type=bool_arg, default=False)
parser.add_argument("--Run_Calibration", type=bool_arg, default=False)
parser.add_argument("--cov_mode", type=str, default="full",
    help="Type of cov modes: full or diag")
parser.add_argument("--SAMPLERS", type=str, nargs="+", default=["emcee"],
    help="Type of sampler: emcee, dynesty, dynamic_dynesty, ultranest")
parser.add_argument("--npool", type=int, default=5)
parser.add_argument("--Samples", type=int, default=100)
parser.add_argument("--thin_samples", type=int, default=2)
parser.add_argument("--burn_frac", type=float, default=0.2)
parser.add_argument("--dlog", type=float, default=0.8)
parser.add_argument("--size", type=int, default=1000,
    help="Number of samples for results")
parser.add_argument("--Result_plots", type=bool_arg, default=True)

args = parser.parse_args()

# ─────────────────────────────────────────────
# Unpack Args
# ─────────────────────────────────────────────
work_dir        = args.work_dir or os.environ.get('WORKDIR', '/workdir')
main_dir        = args.main_dir or f"{work_dir}/New_Project"
input_dir       = args.input_dir or f"{main_dir}/input"
output_dir      = args.output_dir or f"{main_dir}/output"
clear_output    = args.clear_output
clean_input     = args.clean_input
Coll_System     = args.Coll_System
model           = args.model
train_size      = args.train_size
validation_size = args.validation_size
Train_Surmise   = args.Train_Surmise
Load_Surmise    = args.Load_Surmise
scaler_type     = args.scaler_type
PCA             = args.PCA
Closure_Test    = args.Closure_Test
closure_index   = args.closure_index
Closure_plots   = args.Closure_plots
Run_Calibration = args.Run_Calibration
cov_mode        = args.cov_mode
SAMPLERS        = args.SAMPLERS
npool           = args.npool
Samples         = args.Samples
thin_samples    = args.thin_samples
burn_frac       = args.burn_frac
dlog            = args.dlog
size            = args.size
Result_plots    = args.Result_plots

Scale = scaler_type is not None and scaler_type != 'None'

# ─────────────────────────────────────────────
# Output Directory
# ─────────────────────────────────────────────
if clear_output and os.path.exists(output_dir):
    print(f"Clearing output directory: {output_dir}")
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(output_dir + "/plots", exist_ok=True)

# ─────────────────────────────────────────────
# Design Points
# ─────────────────────────────────────────────
print("Loading design points from input directory.")

input_cleaned_dir  = f"{output_dir}/input_cleaned"
merged_Design_file = "Design__Rivet__Merged.dat"
merged_output_file = f'{input_cleaned_dir}/Design/{merged_Design_file}'
prediction_dir     = f"{input_cleaned_dir}/Prediction"
data_dir           = f"{input_cleaned_dir}/Data"

if not os.path.exists(input_cleaned_dir):
    shutil.copytree(input_dir, input_cleaned_dir)

    if not os.path.exists(merged_output_file):
        shutil.copy(f"{input_cleaned_dir}/Rivet/parameter_prior_list.dat", merged_output_file)
        index_files   = DataPred.get_design_index(input_cleaned_dir)
        existing_rows = DataPred.get_existing_design_points(index_files)

        with open(merged_output_file, 'a') as f:
            f.write(f"\n\n# Total Design Points Merged = {len(existing_rows)}")
            f.write('\n' + "# Design point indices (row index): " + ' '.join(str(i) for i in range(len(existing_rows))) + '\n')
            f.write("\n".join(existing_rows) + "\n")

        print(f"➕ Appended {len(existing_rows)} design points to {merged_output_file}")

        design_dir = f"{input_cleaned_dir}/Design"
        for filename in os.listdir(design_dir):
            filepath = os.path.join(design_dir, filename)
            if filepath != merged_output_file:
                os.remove(filepath)

    DG_predictions_files = glob.glob(f"{prediction_dir}/*.dat")
    DataPred.group_histograms_by_design(DG_predictions_files, prediction_dir)
    DataPred.zeros_nan_remover(main_dir, prediction_dir, data_dir)

print(f"Loading {merged_Design_file} from input directory.")

RawDesign = Reader.ReadDesign(f'{input_cleaned_dir}/Design/{merged_Design_file}')
priors, parameter_names, dim = DesignPoints.get_prior(RawDesign)
train_points, validation_points, train_indices, validation_indices = DesignPoints.load_data(train_size, validation_size, RawDesign['Design'], priors, validation_indices_file=f'{input_cleaned_dir}/validation_indices.txt')

Plots.plot_design_points(output_dir, train_points, validation_points, priors)

# ─────────────────────────────────────────────
# Load Data and Predictions
# ─────────────────────────────────────────────
print("Loading input directory.")

Data        = {}
Predictions = {}
all_data    = {}
n_hist      = {}

for system in Coll_System:

    if system == 'all':
        sys = 'all'
        prediction_files = sorted(glob.glob(os.path.join(prediction_dir, f"Prediction__{model}__*__values.dat")))
        data_files       = sorted(glob.glob(os.path.join(data_dir, f"Data__*.dat")))
    else:
        System, Energy   = system.split('_')
        sys              = System + Energy
        prediction_files = sorted(glob.glob(os.path.join(prediction_dir, f"Prediction__{model}__{Energy}__{System}__*__values.dat")))
        data_files       = sorted(glob.glob(os.path.join(data_dir, f"Data__{Energy}__{System}__*.dat")))

    all_predictions = [Reader.ReadPrediction(f) for f in prediction_files]
    all_data[sys]   = [Reader.ReadData(f) for f in data_files]
    n_hist[sys]     = len(prediction_files)

    x, x_errors, y_data_results, y_data_errors                     = DataPred.get_data(all_data[sys], sys)
    y_train_results, y_train_errors, y_val_results, y_val_errors    = DataPred.get_predictions(all_predictions, train_indices, validation_indices, sys)

print("Data and predictions loaded successfully.")

# ─────────────────────────────────────────────
# Scaling (optional)
# ─────────────────────────────────────────────
Emulators    = {}
PredictionVal   = {}
PredictionTrain = {}
scalers = None

if Scale:
    print("Scaling training and validation data.")

    SCALER_MAP = {
        "StandardScaler": StandardScaler,
        "MinMaxScaler":   MinMaxScaler,
        "RobustScaler":   RobustScaler
    }

    if scaler_type not in SCALER_MAP:
        raise ValueError(f"Unknown scaler '{scaler_type}'. Choose from: {list(SCALER_MAP)}")

    scaler_class = SCALER_MAP[scaler_type]
    scalers, y_train_results, y_val_results = Emulation.scale_preprocessing(scaler_class, x, y_data_results, y_train_results, y_val_results)

# ─────────────────────────────────────────────
# Emulator
# ─────────────────────────────────────────────
if Train_Surmise:
    print("Training Surmise emulators.")
    os.makedirs(output_dir + "/emulator", exist_ok=True)
    method_type = 'PCGP' if PCA else 'indGP'
    Emulators['surmise'], PredictionVal['surmise_val'], PredictionTrain['surmise_train'] = Emulation.train_surmise(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type)
    Plots.plot_rmspe_comparison(y_train_results, y_val_results, PredictionTrain, PredictionVal, output_dir)
    Plots.plot_rmspe_per_inspire(y_val_results, PredictionVal, all_data, x, output_dir, 'Validation')
    Plots.plot_rmspe_vs_emuvar(y_val_results, PredictionVal, all_data, x, Emulators, validation_points, output_dir, 'Validation')

elif Load_Surmise:
    print("Loading Surmise emulator.")
    Emulators['surmise'] = {}
    Emulators['surmise'], PredictionVal['surmise_val'], PredictionTrain['surmise_train'] = Emulation.load_surmise(Emulators['surmise'], x, train_points, validation_points, output_dir)


# ─────────────────────────────────────────────
# Calibration
# ─────────────────────────────────────────────
sampler_configs = {
    "dynesty":   dict(nlive=200*dim, dlogz=dlog, sample='rwalk', bound='multi', facc=0.5, walks=10*dim),
    "emcee":     dict(nwalkers=200*dim, nsteps=Samples, thin=thin_samples, nburn=0, burn_in_fraction=burn_frac),
    "ultranest": dict(nlive=100*dim, show_status=True, dlogz=dlog),
}

samplers = {name: sampler_configs[name] for name in SAMPLERS}
closure_name = f'closure_{closure_index}'
truths = dict(zip(parameter_names, validation_points[closure_index]))

y_pseudo={}
for system in Coll_System:
    y_pseudo[system] = y_val_results[system][closure_index]

if Closure_Test:
    print("Running closure calibration.")
    os.makedirs(f"{output_dir}/plots/closure/", exist_ok=True)
    Calibration.run_calibration(x, y_pseudo, y_data_errors, priors, Emulators, output_dir, samplers, npool, Samples, closure_name, scalers, cov_mode)

if Closure_plots: 
    Plots.combined_results(size, x, all_data, y_pseudo, y_data_errors, Emulators, SAMPLERS, n_hist, output_dir, scalers=None, band_threshold=90, design_points=RawDesign['Design'], result_type=closure_name, legend=False)  
    Plots.results(size, x, all_data, y_pseudo, y_data_errors, Emulators, SAMPLERS, n_hist, output_dir, scalers=None, band_threshold=90, design_points=RawDesign['Design'], result_type=closure_name, legend=True)  
    Calibration.closure(Coll_System, Emulators, output_dir, closure_name, truths)

if Run_Calibration:
    print("Running calibration.")
    os.makedirs(f"{output_dir}/plots/calibration/", exist_ok=True)
    calb_type='calibration'
    Calibration.run_calibration(x, y_data_results, y_data_errors, priors, Emulators, output_dir, samplers, npool, Samples, calb_type, scalers, cov_mode)

# ─────────────────────────────────────────────
# Results
# ─────────────────────────────────────────────
if Result_plots:
    print("Generating results plots.")
    Plots.plot_diagnostics(output_dir, x, Emulators, SAMPLERS, parameter_names)
    Calibration.merge(Coll_System, Emulators, output_dir)
    Plots.plot_uncertainty_comparison(x, all_data, y_data_results, y_data_errors, Emulators, SAMPLERS, output_dir)
    Plots.results(size, x, all_data, y_data_results, y_data_errors, Emulators, SAMPLERS, n_hist, output_dir, scalers=None, band_threshold=90, design_points=RawDesign['Design'], result_type='calibration', legend=True)  

    HtmlReport.generate_report(output_dir, Coll_System, Emulators, samplers,
                               all_data=all_data, priors=priors, model=model,
                               train_size=train_size, validation_size=validation_size)


print("done")