import subprocess

project_dir = '/workdir/New_Project'
analyses_list = 'analyses_list.txt'

# Set parameters
model = 'pythia8'
collision_system = 'pp'
ecm = '7000'  # GeV
nevents = 1000
seed = 40
param_tag = 'A_20_B_0.2_C_0.1_D_0.05'


# Read analyses list (just the analysis names)
with open(f"{project_dir}/{analyses_list}", 'r') as f:
    analyses_list = [line.split()[0] for line in f if line.strip()]

print(f"Analyses to run: {analyses_list}")

# Build analyses
subprocess.run(['bash', 'Rivet_analyses/run_analysis.sh', ','.join(analyses_list), project_dir], check=True)

# Filter successful builds
with open(f"{project_dir}/analyses.log", 'r') as f:
    analyses_results = f.read().splitlines()
analyses_list = [line.split()[0] for line in analyses_results if line.strip().endswith('build_success')]

print(f"Analyses completed successfully: {analyses_list}")

# Run the model
subprocess.run(['bash', f'Models/{model}/scripts/run_{model}.sh', ','.join(analyses_list), project_dir, collision_system, ecm, str(nevents), str(seed), param_tag], check=True)

# Merge results
subprocess.run(['bash', 'Rivet_analyses/merge.sh', project_dir, model, collision_system, ecm, param_tag], check=True)

# Generate HTML report
subprocess.run(['bash', 'Rivet_analyses/mkhtml.sh', ','.join(analyses_list), project_dir, model, collision_system, ecm, param_tag], check=True)
