from Design_Points import reader as Reader
from Design_Points import design_points as DesignPoints
from Design_Points import plots as Plots
from Design_Points import rivet_html_parser as RivetParser

import os
import shutil
import subprocess

###########################################################
################### SCRIPT PARAMETERS #####################
main_dir = "New_Project"
seed = 43                   #seed for LHS
model_seed = 283            #seed for model

clear_rivet = True          #clear rivet directory
Coll_System = ['pp_7000']   #Rivet example
Get_Design_Points = True   #True: uses LHS to get design points False: loads design points in input file
nsamples = 10              #number of design points
model = 'pythia8'           #only pythia8 (atm)
Run_Model = True            #run design points through model and Rivet
nevents = 1000              # number of events for model in each run
Write_input_Rivet = True    #gets Data/Pred info from html files 

######## Wish list: Come up with a way to run design points in batches
######## Wish list: incorporate parameter.cmnd instead of using sed in run_pythia.sh
###########################################################
###########################################################

if clear_rivet and os.path.exists(f"{main_dir}/rivet"):
    print(f"Clearing output directory: {main_dir}/rivet")
    shutil.rmtree(f"{main_dir}/rivet")

os.makedirs(f"{main_dir}/rivet", exist_ok=True)

############## Design Points ####################

if Get_Design_Points: 
    print("Generating design points.")
    Design_file = 'Design__Rivet.dat'
    output_file = f'{main_dir}/input/Design/{Design_file}'
    shutil.copy(f"{main_dir}/input/Rivet/parameter_prior_list.dat", output_file)

    RawDesign = Reader.ReadDesign(f'{main_dir}/input/Rivet/parameter_prior_list.dat')
    priors, parameter_names, dim= DesignPoints.get_prior(RawDesign)
    design_points = DesignPoints.get_design(nsamples, priors, seed)

    with open(output_file, 'a') as f:
    # Write index line based on row positions
        index_line = '\n' + "# Design point indices (row index): " + ' '.join(str(i) for i in range(len(design_points))) + '\n'
        f.write(index_line)

        # Write design points
        for row in design_points:
            f.write(' '.join(f"{val:.18e}" for val in row) + '\n')
    print(f"Appended {len(design_points)} design points to {output_file}")

else:
    print("Loading design points from input directory.")
    RawDesign = Reader.ReadDesign(f'{main_dir}/input/Design/Design__Rivet.dat')
    priors, parameter_names, dim= DesignPoints.get_prior(RawDesign)
    design_points = RawDesign['Design']

################# Rivet Analyses ####################
input_dir = f'{main_dir}/input/Rivet'
project_dir = f'{main_dir}/rivet'
analyses_file = 'analyses_list.txt'
tagged_analyses = {}
analyses_list = []
system_tag = None

print("Running Rivet.py with analyses_list.txt.")
os.makedirs(project_dir, exist_ok=True)

with open(f"{input_dir}/{analyses_file}", 'r') as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if line.endswith(':'):
            system_tag = line[:-1] 
            tagged_analyses[system_tag] = {}  
        elif system_tag is not None:
            parts = line.split()
            analysis = parts[0]
            histograms = parts[1:]
            tagged_analyses[system_tag][analysis] = histograms
            analyses_list.append(analysis)
        else:
            raise ValueError(f"Found analysis line before tag: {line}")
    
# Build analyses
subprocess.run(['bash', 'Design_Points/Rivet_analyses/run_analysis.sh', ','.join(analyses_list), project_dir], check=True)

# Filter successful builds
with open(f"{project_dir}/analyses.log", 'r') as f:
    analyses_results = f.read().splitlines()
analyses_list = [line.split()[0] for line in analyses_results if line.strip().endswith('build_success')]

print(f"Analyses completed successfully: {analyses_list}")

############# Run Model/Rivet ###############
if Run_Model:
    if design_points is None:
        print("Design points not found. Need to generate design points first.")
        exit(1)
        
    for system in Coll_System:
        System, Energy = system.split('_')[0], system.split('_')[1]  

        for i, point in enumerate(design_points):
            print(f"Running {model} for Design Point {i+1}: {point}")
            param_tag = DesignPoints.generate_param_tag(parameter_names, design_points[i])
            merge_tag = f"DP_{i+1}"

            # Run the model
            subprocess.run(['bash', f'Design_Points/Models/{model}/scripts/run_{model}.sh', ','.join(analyses_list), project_dir, System, Energy, str(nevents), str(model_seed), param_tag, merge_tag], check=True)

            # Merge results
            subprocess.run(['bash', 'Design_Points/Rivet_analyses/merge.sh', project_dir, model, System, Energy, merge_tag], check=True)

            # Generate HTML report
            subprocess.run(['bash', 'Design_Points/Rivet_analyses/mkhtml.sh', ','.join(analyses_list), project_dir, model, System, Energy, merge_tag], check=True)


############# Write out Data/Prediction Files #################
if Write_input_Rivet:
    for system in Coll_System:
        System, Energy = system.split('_')
        sys = System + Energy

        for i, point in enumerate(design_points):
            DP = i + 1
            for analysis in analyses_list:
                for hist in tagged_analyses[system_tag][analysis]:
                    Experiment = analysis.split('_')[0]

                    base = f"{project_dir}/Models/{model}/html_reports/{model}_{System}_{Energy}_DP_{DP}_{analysis}_report.html/{analysis}/{hist}"
                    datafile = base + "__data.py"
                    labelfile = base + ".py"
                    raw_obs, raw_subobs, obs_clean, subobs_clean = RivetParser.extract_labels(labelfile)

                    input_data_name = f"{main_dir}/input/Data/Data__{Energy}__{System}__{obs_clean}__{subobs_clean}_{Experiment}__{hist}"
                    input_pred_name = f"{main_dir}/input/Prediction/Prediction__{model}__{Energy}__{System}__{obs_clean}__{subobs_clean}_{Experiment}__{hist}"

                    RivetParser.extract_data(datafile, model, input_data_name, input_pred_name, DP)

print("done")