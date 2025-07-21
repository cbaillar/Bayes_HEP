# Bayes\_HEP Docker Instructions

These are the step-by-step instructions for running the Bayes\_HEP project on your HPC system using Apptainer (formerly Singularity).

---

## 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

docker pull cbaillar/bayes_hep:latest

docker run -it --rm -v "$PWD":/workdir -e WORKDIR=/workdir bayes_hep

cp -r /usr/local/share/Bayes_HEP/Examples/Docker_New_Project .
```

---

## 2. Input Configuration

Before running any analyses, **edit these files** in `HPC_New_Project/input/Rivet/` to match your study:

* `analyses_list.txt`
  List of Rivet analyses to run.
  i.e.: 

pp_7000:
ATLAS_2010_I882098 d03-x01-y01 d07-x01-y01 
ATLAS_2012_I1188891 d02-x01-y01

pp_13000:
CMS_2018_I1663452 d03-x01-y01

* `parameter_prior_list.txt`
  Set parameter prior ranges for sampling/tuning.

* `parameter.cmnd`
  Default Pythia parameter card; this is used as a template for all model runs.

---

## 3. Interactive Scripts

From inside the container (`apptainer shell ...`):

```sh
python Docker_New_Project/drivers/Rivet_Main.py

python Docker_New_Project/drivers/Bayes_Main.py
```

---

## 4. Batch Job Submission 

**Important:**
*Before submitting jobs, update the parameters in generate_design_points.sh located in `Docker_New_Project/Batch_Rivet/` to fit your project layout and desired cpu. This is a config file to run Batch_Rivet_Main.py (which is a modified version of Rivet_Main.py)*

Parameters in generate_design_points.sh:

COLLISIONS="pp_7000"    #"pp_7000 pp_13000"
TOTAL_POINTS=5          # Total number of design points
TOTAL_EVENTS=10         # Total number of events across all jobs
NEVENTS=10              # Events per job
CPU=5                   # USER sets how many CPUs to use
TARGET_EVENTS_PER_JOB=1000000

Run the following script to prepare and submit jobs:

```sh
bash Docker_New_Project/Batch_Rivet/generate_design_points.sh

```

---

# Bayes\_HEP HPC Instructions

These are the step-by-step instructions for running the Bayes\_HEP project on your HPC system using Apptainer (formerly Singularity).

---

## 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

apptainer build bayes_hep.sif docker://cbaillar/bayes_hep:latest

apptainer shell --bind "$PWD":/workdir bayes_hep.sif

cp -r /usr/local/share/Bayes_HEP/Examples/HPC_New_Project .
```

---

## 2. Input Configuration

Before running any analyses, **edit these files** in `HPC_New_Project/input/Rivet/` to match your study:

* `analyses_list.txt`
  List of Rivet analyses to run.
  i.e.: 

pp_7000:
ATLAS_2010_I882098 d03-x01-y01 d07-x01-y01 
ATLAS_2012_I1188891 d02-x01-y01

pp_13000:
CMS_2018_I1663452 d03-x01-y01

* `parameter_prior_list.txt`
  Set parameter prior ranges for sampling/tuning.

* `parameter.cmnd`
  Default Pythia parameter card; this is used as a template for all model runs.

---

## 3. Interactive Scripts

From inside the container (`apptainer shell ...`):

```sh
python HPC_New_Project/drivers/Rivet_Main.py
python HPC_New_Project/drivers/Bayes_Main.py
```

---

## 4. Batch Job Submission (SLURM)

**Important:**
*Before submitting jobs, update the parameters in generate_design_points.sh and directory paths in all scripts under `HPC_New_Project/Batch_Rivet/` to fit your project layout and cluster paths.*

Parameters in generate_design_points.sh:

USER_DIR="/lustre/isaac24/proj/UTK0244/cbaillar"
COLLISIONS="pp_7000 pp_13000" #"pp_7000 pp_13000"
TOTAL_POINTS=10        # Total number of design points
TOTAL_EVENTS=100    # Total number of events
NEVENTS=50          # Events per job

Run the following scripts to prepare and submit jobs:

```sh
bash HPC_New_Project/Batch_Rivet/generate_design_points.sh
```


Parameters in run_bayes.slurm:

USER_DIR="/lustre/isaac24/proj/UTK0244/cbaillar"
COLLISIONS="pp_7000"
MODEL="pythia8"
N_WALKERS=50        # Number of Random walkers for emcee sampler
NPOOL=10            # Number of CPUs for N_WALKERS
SAMPLES=10000       # Number of samples for MCMC
RESULT_SIZE=100     # Number of samples for result plotting

```sh
sbatch HPC_New_Project/Batch_Rivet/run_bayes.slurm
```

---

## 5. Monitoring & Managing SLURM Jobs

* **Check job status:**

  ```sh
  squeue -u <your_username>
  ```

* **Cancel all jobs:**

  ```sh
  scancel -u <your_username>
  ```

---

## Tips

* Always check `.slurm` files and batch scripts for correct project paths before submitting.
* Output and error files are typically written to the locations specified in your SLURM scripts.
* If you modify input or code, rebuild or restart your container session as needed.

---

**Questions?**
If you encounter issues, check the job output/error logs, and verify that your inputs and paths are correct. For more help, reach out to your system administrator or project maintainer.
