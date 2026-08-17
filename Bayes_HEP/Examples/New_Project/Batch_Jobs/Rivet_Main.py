from Bayes_HEP.Design_Points import reader as Reader
from Bayes_HEP.Design_Points import design_points as DesignPoints
from Bayes_HEP.Design_Points import rivet_html_parser as RivetParser

import argparse
import glob
import os
import random
import shutil
import subprocess
import sys
import numpy as np

# ─────────────────────────────────────────────
# CLI Arguments
# ─────────────────────────────────────────────
def bool_arg(x):
    return x.lower() == "true"

parser = argparse.ArgumentParser(description="Run Rivet/Model analysis pipeline.")
parser.add_argument("--main_dir",             type=str,      default="New_Project")
parser.add_argument("--input_dir",            type=str,      default=None)
parser.add_argument("--input_cleaned_dir",    type=str,      default=None)
parser.add_argument("--seed",                 type=int,      default=43)
parser.add_argument("--model_seed",           type=int,      default=283)
parser.add_argument("--Run_MAP",              type=bool_arg, default=False)
parser.add_argument("--clear_rivet_models",   type=bool_arg, default=False)
parser.add_argument("--Get_Design_Points",    type=bool_arg, default=False)
parser.add_argument("--nsamples",             type=int,      default=10)
parser.add_argument("--Rivet_Setup",          type=bool_arg, default=False)
parser.add_argument("--model",                type=str,      default="pythia8")
parser.add_argument("--Run_Model",            type=bool_arg, default=False)
parser.add_argument("--Run_Batch",            type=bool_arg, default=False)
parser.add_argument("--PT_Min",               type=int,      default=-1)
parser.add_argument("--PT_Max",               type=int,      default=-1)
parser.add_argument("--nevents",              type=int,      default=1000)
parser.add_argument("--Rivet_Merge",          type=bool_arg, default=False)
parser.add_argument("--equiv_on",             type=bool_arg, default=False)
parser.add_argument("--Write_input_Rivet",    type=bool_arg, default=False)
parser.add_argument("--Coll_System",          nargs="+",     default=["pp_7000"],
                    help="List of collision systems (e.g. pp_7000 pPb_5020)")
parser.add_argument("batch_start",            nargs="?",     type=int, default=0)
parser.add_argument("batch_end",              nargs="?",     type=int, default=None)

args = parser.parse_args()

# ─────────────────────────────────────────────
# Unpack args
# ─────────────────────────────────────────────
main_dir          = args.main_dir
input_dir         = args.input_dir or f"{main_dir}/input"
input_cleaned_dir = args.input_cleaned_dir or f"{main_dir}/output/input_cleaned"
seed              = args.seed
model_seed        = args.model_seed
Run_MAP           = args.Run_MAP
clear_rivet_models = args.clear_rivet_models
Get_Design_Points = args.Get_Design_Points
nsamples          = args.nsamples
Rivet_Setup       = args.Rivet_Setup
model             = args.model
Run_Model         = args.Run_Model
Run_Batch         = args.Run_Batch
PT_Min            = args.PT_Min
PT_Max            = args.PT_Max
nevents           = args.nevents
Rivet_Merge       = args.Rivet_Merge
equiv_on          = args.equiv_on
Write_input_Rivet = args.Write_input_Rivet
Coll_System       = args.Coll_System
batch_start       = args.batch_start
batch_end         = args.batch_end 

# ─────────────────────────────────────────────
# Clear Rivet Models Dir (optional)
# ─────────────────────────────────────────────
models_dir = f"{main_dir}/rivet/Models"
if clear_rivet_models and os.path.exists(models_dir):
    print(f"Clearing output directory: {models_dir}")
    shutil.rmtree(models_dir)

# ─────────────────────────────────────────────
# Design Points
# ─────────────────────────────────────────────
max_index = None  # used later in Write_input_Rivet

if Run_MAP:
    print("Loading MAP values from input_cleaned directory.")
    RawMAP = Reader.ReadDesign(f"{input_cleaned_dir}/Design/Design__Rivet__MAP.dat")
    priors, parameter_names, dim = DesignPoints.get_prior(RawMAP)
    design_points = np.atleast_2d(RawMAP["Design"])

elif Get_Design_Points:
    print("Generating design points.")
    design_dir = f"{input_dir}/Design"
    os.makedirs(design_dir, exist_ok=True)

    index_numbers = [
        int(f.split("__")[-1].split(".")[0])
        for f in glob.glob(f"{design_dir}/Design__Rivet__*.dat")
    ]
    max_index = (max(index_numbers) if index_numbers else 0) + 1
    Design_file = f"Design__Rivet__{max_index}.dat"
    output_file = f"{design_dir}/{Design_file}"

    prior_src = f"{input_dir}/Rivet/parameter_prior_list.dat"
    shutil.copy(prior_src, output_file)
    RawDesign = Reader.ReadDesign(prior_src)
    priors, parameter_names, dim = DesignPoints.get_prior(RawDesign)

    existing_rows = set()
    for oldfile in glob.glob(f"{design_dir}/*.dat"):
        with open(oldfile) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    existing_rows.add(line)

    while True:
        design_points = np.atleast_2d(DesignPoints.get_design(nsamples, priors, seed))
        current_rows = {" ".join(f"{v:.18e}" for v in row) for row in design_points}
        if current_rows.isdisjoint(existing_rows):
            print("🟢 No duplicates detected")
            break
        print("🟡 Duplicates detected, re-generating design points")
        seed = random.randint(1, 2**32 - 1)

    with open(output_file, "a") as f:
        f.write(f"\n\n# LHS Seed = {seed}; Number of Design Points = {nsamples}")
        f.write("\n# Design point indices (row index): " + " ".join(str(i) for i in range(len(design_points))) + "\n")
        for row in design_points:
            f.write(" ".join(f"{v:.18e}" for v in row) + "\n")
    print(f"Appended {len(design_points)} design points to {output_file}")

else:
    print("Loading design points from input directory.")
    design_dir = f"{input_dir}/Design"
    index_numbers = [
        int(f.split("__")[-1].split(".")[0])
        for f in glob.glob(f"{design_dir}/Design__Rivet__*.dat")
    ]
    if not index_numbers:
        print("No Design files found. Please generate design points first.")
        sys.exit(1)

    max_index = max(index_numbers)
    RawDesign = Reader.ReadDesign(f"{design_dir}/Design__Rivet__{max_index}.dat")
    priors, parameter_names, dim = DesignPoints.get_prior(RawDesign)
    design_points = np.atleast_2d(RawDesign["Design"])

# Resolve batch range now that design_points is known
if Run_Batch:
    batch_end = batch_end if batch_end is not None else len(design_points)
else:
    batch_start = 0
    batch_end = len(design_points)

# ─────────────────────────────────────────────
# Parse Analyses List
# ─────────────────────────────────────────────
use_input  = f"{input_cleaned_dir}/Rivet" if Run_MAP else f"{input_dir}/Rivet"
project_dir = f"{main_dir}/rivet"
os.makedirs(project_dir, exist_ok=True)

tagged_analyses = {}  # {system: {analysis: [histograms]}}
analyses_list   = {}  # {system: [analyses]}
system_tag = None

with open(f"{use_input}/analyses_list.txt") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        if line.endswith(":"):
            system_tag = line[:-1]
            tagged_analyses[system_tag] = {}
            if system_tag in Coll_System:
                analyses_list[system_tag] = []
        elif system_tag is not None:
            parts = line.split()
            analysis, histograms = parts[0], parts[1:]
            tagged_analyses[system_tag][analysis] = histograms
            if system_tag in Coll_System:
                analyses_list[system_tag].append(analysis)
        else:
            raise ValueError(f"Found analysis line before any system tag: {line}")

missing = [s for s in Coll_System if s not in analyses_list]
if missing:
    raise ValueError(f"❌ Missing analyses for system(s): {missing}")

# ─────────────────────────────────────────────
# Rivet Setup (Build Analyses)
# ─────────────────────────────────────────────
if Rivet_Setup:
    all_analyses = [a for sys in analyses_list.values() for a in sys]
    print(f"📦 Building analyses: {all_analyses}")
    subprocess.run([
        "bash",
        "/usr/local/share/Bayes_HEP/Design_Points/Rivet_Analyses/run_analysis.sh",
        ",".join(all_analyses),
        project_dir,
    ], check=True)

with open(f"{project_dir}/analyses.log") as f:
    analyses_results = f.read().splitlines()

successful_builds = [l.split()[0] for l in analyses_results if l.strip().endswith("build_success")]
failed_builds     = [l.split()[0] for l in analyses_results if l.strip().endswith("build_failed")]

print(f"✅ Successful builds: {successful_builds}")
if failed_builds:
    print(f"❌ Failed builds: {failed_builds}")
    sys.exit(1)
print("🎉 No failed builds!")

# ─────────────────────────────────────────────
# Run Model
# ─────────────────────────────────────────────
if Run_Model:
    for system in Coll_System:
        system_analyses = analyses_list.get(system)
        if not system_analyses:
            print(f"⚠️ No analyses defined for system: {system}")
            continue

        System, Energy = system.split("_")
        print(f"🧪 Running model for system: {system}")

        for i in range(batch_start, min(batch_end, len(design_points))):
            point = design_points[i]
            print(f"Running {model} for Design Point {i + 1}: {point}")
            param_tag = DesignPoints.generate_param_tag(parameter_names, point)
            merge_tag = f"MAP_{i + 1}" if Run_MAP else f"DP_{i + 1}"

            subprocess.run([
                "bash",
                f"/usr/local/share/Bayes_HEP/Design_Points/Models/{model}/run_{model}.sh",
                ",".join(system_analyses), use_input, project_dir,
                System, Energy, str(nevents), str(model_seed),
                param_tag, merge_tag, str(PT_Min), str(PT_Max),
            ], check=True)

# ─────────────────────────────────────────────
# Rivet Merge + HTML Reports
# ─────────────────────────────────────────────
if Rivet_Merge:
    for system in Coll_System:
        system_analyses = analyses_list.get(system)
        if not system_analyses:
            print(f"⚠️ No analyses listed for {system}")
            continue

        System, Energy = system.split("_")
        print(system_analyses)

        for i, point in enumerate(design_points):
            merge_tag = f"MAP_{i + 1}" if Run_MAP else f"DP_{i + 1}"

            subprocess.run([
                "bash",
                "/usr/local/share/Bayes_HEP/Design_Points/Rivet_Analyses/merge.sh",
                project_dir, model, System, Energy, merge_tag, str(equiv_on),
            ], check=True)

            subprocess.run([
                "bash",
                "/usr/local/share/Bayes_HEP/Design_Points/Rivet_Analyses/mkhtml.sh",
                project_dir, model, System, Energy, merge_tag,
            ], check=True)

# ─────────────────────────────────────────────
# Write Data / Prediction Files
# ─────────────────────────────────────────────
if Write_input_Rivet:
    if Run_MAP:
        os.makedirs(f"{input_cleaned_dir}/Data_MAP",       exist_ok=True)
        os.makedirs(f"{input_cleaned_dir}/Prediction_MAP", exist_ok=True)
    else:
        os.makedirs(f"{input_dir}/Data",       exist_ok=True)
        os.makedirs(f"{input_dir}/Prediction", exist_ok=True)

    for system in Coll_System:
        System, Energy = system.split("_")
        system_analyses = analyses_list[system]

        for i, point in enumerate(design_points):
            DP = i + 1
            for analysis in system_analyses:
                for hist in tagged_analyses[system][analysis]:
                    if Run_MAP:
                        base = (
                            f"{project_dir}/Models/{model}/html_reports"
                            f"/{model}_{System}_{Energy}_MAP_{DP}_report.html/{analysis}/{hist}"
                        )
                        data_path = f"{input_cleaned_dir}/Data_MAP/Data__{Energy}__{System}__{analysis}__{hist}"
                        pred_path = f"{input_cleaned_dir}/Prediction_MAP/Prediction__{model}__{Energy}__{System}__{analysis}__{hist}__MAP"
                    else:
                        base = (
                            f"{project_dir}/Models/{model}/html_reports"
                            f"/{model}_{System}_{Energy}_DP_{DP}_report.html/{analysis}/{hist}"
                        )
                        data_path = f"{input_dir}/Data/Data__{Energy}__{System}__{analysis}__{hist}"
                        pred_path = f"{input_dir}/Prediction/Prediction__{model}__{Energy}__{System}__{analysis}__{hist}__DG_{max_index}"

                    obs, subobs = RivetParser.extract_labels(f"{base}.py")
                    RivetParser.extract_data(f"{base}__data.py", model, data_path, pred_path, obs, subobs, DP)

print("done")