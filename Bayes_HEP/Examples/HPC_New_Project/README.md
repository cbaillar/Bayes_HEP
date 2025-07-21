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
  List of Rivet analyses to run (one per line).

* `parameter_prior_list.txt`
  Set parameter prior ranges for sampling/tuning.

* `parameter.cmnd`
  Default Pythia parameter card; this is used as a template for all model runs.

---

## 3. Interactive Workflow

From inside the container (`apptainer shell ...`):

```sh
python HPC_New_Project/drivers/Rivet_Main.py
python HPC_New_Project/drivers/Bayes_Main.py
```

---

## 4. Batch Job Submission

**Important:**
*Before submitting jobs, update file and directory paths in all scripts under `HPC_New_Project/Batch_Rivet/` to fit your project layout and cluster paths.*

Run the following scripts to prepare and submit jobs:

```sh
bash HPC_New_Project/Batch_Rivet/generate_design_points.sh

chmod +x HPC_New_Project/Batch_Rivet/run_bayes.slurm
sbatch HPC_New_Project/Batch_Rivet/run_bayes.slurm
```

---

## 5. Monitoring & Managing Jobs

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