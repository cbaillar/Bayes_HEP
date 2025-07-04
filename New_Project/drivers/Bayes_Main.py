from Design_Points import reader as Reader
from Design_Points import design_points as DesignPoints
from Design_Points import plots as Plots
from Design_Points import data_pred as DataPred
from Emulation import emulation as Emulation
from Calibration import calibration as Calibration

import os
import shutil
import matplotlib.pyplot as plt
import glob
import dill
    
###########################################################
################### SCRIPT PARAMETERS #####################

main_dir = "New_Project"
seed = 43 

clear_output = True         #clear output directory
Coll_System = ['pp_7000']   #['AuAu_200', 'PbPb_2760', 'PbPb_5020']

model = 'pythia8'
dmax = True                 #turn detmax on or off
train_size = 80             #percentage of design points used for training
validation_size = 20        #percentage of design points used for validation

######## Emulators
Train_Surmise = True
Train_Scikit = True   
PCA = True 

######## Calibration
Caibration = True 
nwalkers = 50
Samples = 100   #Number of MCMC samples  
percent = 0.15      # Get traces for the last percentage of samples
Load_Calibration = True 

####### Results 
size = 1000  # Number of samples for Results
Result_plots = True

###########################################################
###########################################################
output_dir = f"{main_dir}/output"
if clear_output and os.path.exists(output_dir):
    print(f"Clearing output directory: {output_dir}")
    shutil.rmtree(output_dir)
os.makedirs(output_dir, exist_ok=True)
os.makedirs(output_dir + "/plots", exist_ok=True)

############## Design Points ####################
print("Loading design points from input directory.")
RawDesign = Reader.ReadDesign(f'{main_dir}/input/Design/Design__Rivet.dat')
priors, parameter_names, dim= DesignPoints.get_prior(RawDesign)
train_points, validation_points, train_indices, validation_indices = DesignPoints.load_data(train_size, validation_size, RawDesign['Design'], priors, seed, dmax)

Plots.plot_design_points(train_points, validation_points, priors, detmax=dmax)
plt.suptitle(f"Design Point Parameter Space", fontsize=18)
plt.savefig(f"{output_dir}/plots/Design_Points.png")
plt.show()

print("Loading input directory.")
prediction_dir, data_dir = f"{main_dir}/input/Prediction", f"{main_dir}/input/Data"
    
Data = {}
Predictions = {}
all_data = {}

for system in Coll_System:
    System, Energy = system.split('_')[0], system.split('_')[1]  
    sys = System + Energy   

    prediction_files = glob.glob(os.path.join(prediction_dir, f"Prediction__{model}__{Energy}__{System}__*__values.dat"))
    data_files = glob.glob(os.path.join(data_dir, f"Data__{Energy}__{System}__*.dat"))

    all_predictions = [Reader.ReadPrediction(f) for f in prediction_files]
    all_data[sys] = [Reader.ReadData(f) for f in data_files]

    x, x_errors, y_data_results, y_data_errors = DataPred.get_data(all_data[sys], sys)
    y_train_results, y_train_errors, y_val_results, y_val_errors = DataPred.get_predictions(all_predictions, train_indices, validation_indices, sys)

print("Data and predictions loaded successfully.")

######### Emulators ########
Emulators = {}
PredictionVal = {}
PredictionTrain = {}
os.makedirs(output_dir + "/emulator", exist_ok=True)

######### Surmise Emulator ########
if Train_Surmise:
    print("Training Surmise emulators.")
    method_type = 'indGP'
    if PCA:
        method_type = 'PCGP'

    Emulators['surmise'], PredictionVal['surmise_val'], PredictionTrain['surmise_train'] = Emulation.train_surmise(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type)
else:
    print("Loading Surmise emulator.")
    Emulators['surmise'] = {}
    Emulators['surmise'], PredictionVal['surmise_val'], PredictionTrain['surmise_train'] = Emulation.load_surmise(Emulators['surmise'], x, train_points, validation_points, output_dir)

######## Scikit-learn Emulator ########
if Train_Scikit:
    print("Training Scikit-learn emulator.")
    method_type = 'GP'
    if PCA:
        print("PCA is not supported for Scikit-learn emulator. Using standard Gaussian Process.") 
        
    Emulators['scikit'], PredictionVal['scikit_val'], PredictionTrain['scikit_train'] = Emulation.train_scikit(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type)
else:
    print("Loading Scikit-learn emulator.")

    Emulators['scikit'] = {}
    Emulators['scikit'], PredictionVal['scikit_val'], PredictionTrain['scikit_train'] = Emulation.load_scikit(Emulators['scikit'], x, train_points, validation_points, output_dir)

os.makedirs(f"{output_dir}/plots/emulators/", exist_ok=True)
Plots.plot_rmse_comparison(x, y_train_results, y_val_results, PredictionTrain, PredictionVal, output_dir)
    
########### Calibration ###########
if Caibration:
    print("Running calibration.")
    os.makedirs(f"{output_dir}/calibration/samples/", exist_ok=True)
    os.makedirs(f"{output_dir}/calibration/pos0/", exist_ok=True)
    os.makedirs(f"{output_dir}/plots/calibration/", exist_ok=True)  
    os.makedirs(f"{output_dir}/plots/trace/", exist_ok=True)

    results, samples_results, min_samples = Calibration.run_calibration(x, y_data_results, y_data_errors, priors, Emulators, output_dir, nwalkers, Samples)
    
    Calibration.get_traces(output_dir, x, samples_results, Emulators, parameter_names, percent) 

if Load_Calibration:
    print("Calibration not performed. Loading Samples.")
    samples_results, min_samples= Calibration.load_samples(output_dir, x, Emulators)

########### Results ###########

if Result_plots:
    print("Generating results plots.")
    
    if min_samples < size:
        print(f"Warning: Minimum samples ({min_samples}) is less than requested size ({size}). Adjusting size to {min_samples}.")
        size = min_samples

    Plots.results(size, x, all_data, samples_results, y_data_results, y_data_errors, Emulators, output_dir)
    
print("done")