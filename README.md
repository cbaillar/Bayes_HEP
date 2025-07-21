# Bayes\_HEP Instructions

This guide provides step-by-step instructions for running the **Bayes\_HEP** project using Docker or Apptainer (formerly Singularity), both interactively and in batch mode on HPC systems.

---

## 🚀 Docker Workflow

### 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

docker pull cbaillar/bayes_hep:latest

docker run -it --rm -v "$PWD":/workdir -e WORKDIR=/workdir cbaillar/bayes_hep

cp -r /usr/local/share/Bayes_HEP/Examples/Docker_New_Project .
```

---

### 2. Input Configuration

Edit the following files in `Docker_New_Project/input/Rivet/`:

- \`\` – List of Rivet analyses to run\
  Example:

  ```
  pp_7000:
  ATLAS_2010_I882098 d03-x01-y01 d07-x01-y01
  ATLAS_2012_I1188891 d02-x01-y01

  pp_13000:
  CMS_2018_I1663452 d03-x01-y01
  ```

- \`\` – Set parameter prior ranges for sampling/tuning

- \`\` – Default Pythia parameter card used as a template for all runs

---

### 3. Interactive Execution (Inside Container)

```sh
python Docker_New_Project/drivers/Rivet_Main.py
python Docker_New_Project/drivers/Bayes_Main.py
```

---

### 4. Batch Job Submission (Docker)

Before submitting jobs, update `generate_design_points.sh` in `Docker_New_Project/Batch_Rivet/` to match your setup.

Key parameters:

```sh
COLLISIONS="pp_7000"        # Space-separated systems, e.g., "pp_7000 pp_13000"
TOTAL_POINTS=5              # Total number of design points
TOTAL_EVENTS=10             # Total number of events
NEVENTS=10                  # Events per job
CPU=5                       # Number of CPUs to use
TARGET_EVENTS_PER_JOB=1000000
```

Submit jobs:

```sh
bash Docker_New_Project/Batch_Rivet/generate_design_points.sh
```

---

## 🧠 HPC Workflow (Apptainer/Singularity)

### 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

apptainer build bayes_hep.sif docker://cbaillar/bayes_hep:latest

apptainer shell --bind "$PWD":/workdir bayes_hep.sif

cp -r /usr/local/share/Bayes_HEP/Examples/HPC_New_Project .
```

---

### 2. Input Configuration

Edit the following files in `HPC_New_Project/input/Rivet/`:

- \`\` – List of Rivet analyses (see example above)
- \`\` – Parameter prior ranges
- \`\` – Default Pythia template

---

### 3. Interactive Execution (Inside Container)

```sh
python HPC_New_Project/drivers/Rivet_Main.py
python HPC_New_Project/drivers/Bayes_Main.py
```

---

### 4. Batch Job Submission (SLURM)

Before submitting jobs, update:

- `generate_design_points.sh` and other scripts in `HPC_New_Project/Batch_Rivet/`
- Paths like `USER_DIR` and any project-specific configurations

Key parameters in `generate_design_points.sh`:

```sh
USER_DIR="/lustre/isaac24/proj/UTK0244/cbaillar"
COLLISIONS="pp_7000 pp_13000"
TOTAL_POINTS=10
TOTAL_EVENTS=100
NEVENTS=50
```

Submit jobs:

```sh
bash HPC_New_Project/Batch_Rivet/generate_design_points.sh
```

For MCMC calibration (`run_bayes.slurm`):

```sh
USER_DIR="/lustre/isaac24/proj/UTK0244/cbaillar"
COLLISIONS="pp_7000"
MODEL="pythia8"
N_WALKERS=50
NPOOL=10
SAMPLES=10000
RESULT_SIZE=100
```

Submit:

```sh
sbatch HPC_New_Project/Batch_Rivet/run_bayes.slurm
```

---

## 📊 SLURM Job Management

- **Check job status:**

  ```sh
  squeue -u <your_username>
  ```

- **Cancel all jobs:**

  ```sh
  scancel -u <your_username>
  ```

---

## ✅ Tips

- Double-check all `.slurm` and `.sh` files for correct paths and parameters.
- SLURM output and error logs will be saved in the locations specified in your scripts.
- Rebuild or restart containers after modifying input files or source code.

---

## ❓ Need Help?

If you encounter errors:

- Check SLURM logs for job status and error messages
- Ensure all paths and inputs are correct
- Contact your system administrator or project maintainer for support

