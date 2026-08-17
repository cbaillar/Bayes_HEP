# Bayes\_HEP on UTK's ISAAC Cluster

This guide covers the parts of the Bayes\_HEP workflow that are specific to running on **UTK's ISAAC HPC cluster** — the Jupyter notebook drivers and SLURM batch submission. For everything else (Docker setup, input configuration, the plain bash drivers), see the main [README.md](README.md).

The instructions and scripts here have ISAAC's paths and SLURM account hardcoded, and have only been tested on ISAAC.

---

## 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

apptainer build bayes_hep.sif docker://cbaillar/bayes_hep:UTK

apptainer shell --bind "$PWD":/workdir bayes_hep.sif

cp -r /usr/local/share/Bayes_HEP/Examples/New_Project .
```

Edit the input files under `New_Project/input/Rivet/` as described in the main README's [Input Configuration](README.md#2-input-configuration) section.

---

## 2. Notebook Execution (Jupyter)

As an alternative to the bash drivers (`New_Project/drivers/Rivet_Main.sh` / `Bayes_Main.sh`), `New_Project/drivers/notebook/` provides Jupyter notebook versions of the same two pipelines:

- `Rivet_Notebook.ipynb` — notebook version of `Rivet_Main.sh`/`Rivet_Main.py`
- `Bayes_Notebook.ipynb` — notebook version of `Bayes_Main.sh`/`Bayes_Main.py`

Each notebook has a single **Configuration** cell (paths and pipeline switches) that you edit for your project, then runs top to bottom. Long-running stages (model runs, emulator training, calibration, results) are submitted as SLURM array jobs from within the notebook using the scripts in `New_Project/Batch_Jobs/HPC/notebook/`, rather than run in-process, so the notebook itself stays responsive.

One-time setup:

```sh
bash New_Project/drivers/notebook/utilities/setup.sh <username>
```

This adds the required `anaconda3` module load to `~/.bashrc` and installs a Jupyter kernel (`bayes_hep`) that transparently runs code inside the Apptainer container. Then start Jupyter and open either notebook:

```sh
jupyter notebook --no-browser --port=8888 --ip=0.0.0.0
```

In each notebook's Configuration cell, `username` is your ISAAC username and `work_dir` is auto-built from it (`/lustre/isaac24/proj/UTK0244/{username}/Bayes_HEP`).

---

## 3. Batch Job Submission (SLURM)

Batch jobs are driven from `Rivet_Notebook.ipynb` / `Bayes_Notebook.ipynb` rather than submitted by hand. The notebooks call `sbatch` on the array-job scripts in `New_Project/Batch_Jobs/HPC/notebook/`:

| Script | Stage |
|---|---|
| `run_rivet.slurm` | Pythia8 + Rivet over the full design point set |
| `run_rivet_MAP.slurm` | Pythia8 + Rivet at a single MAP/best-fit point |
| `run_rivet_rerunDP.slurm` | Re-run a specific list of failed/selected design points |
| `run_rivet_merge.sh` / `run_rivet_mergeMAP.sh` | Merge YODA outputs and build HTML reports |
| `run_bayes_emulator.slurm` | Train/load the Surmise GP emulator |
| `run_bayes_calibration.slurm` | Bayesian calibration (MCMC/nested sampling) |
| `run_bayes_closure.slurm` | Closure test calibration |
| `run_bayes_results.slurm` | Posterior and result plots |

If you need to submit one of these directly instead of through a notebook, check the script header for its positional arguments (project paths, collision systems, sampler settings, `CONTAINER`/`BIND_PATH`, etc.) and pass them in order, e.g.:

```sh
sbatch New_Project/Batch_Jobs/HPC/notebook/run_bayes_calibration.slurm \
    New_Project input output pp_200 pythia8 dynesty 5 1000 0.8 2 0.2 \
    "$CONTAINER" "$BIND_PATH"
```

---

## 4. SLURM Job Management

- **Check job status:**

  ```sh
  squeue -u <your_username>
  ```

- **Cancel all jobs:**

  ```sh
  scancel -u <your_username>
  ```

---

## Adapting for other institutions (untested)

Everything above assumes UTK's ISAAC layout. It has not been tried anywhere else. If you want to attempt adapting it for a different cluster, these are the UTK-specific values baked into the scripts:

| File | What to change |
|---|---|
| `drivers/notebook/utilities/setup.sh` | `USER_DIR` (currently `/lustre/isaac24/proj/UTK0244/${USERNAME}`) and the `module load anaconda3/2024.06` line |
| `Rivet_Notebook.ipynb` / `Bayes_Notebook.ipynb` (Configuration cell) | `work_dir` (currently built from `/lustre/isaac24/proj/UTK0244/{username}/Bayes_HEP`) and the `error_path`/`output_path` scratch directories (currently `/lustre/isaac24/scratch/{username}/jobs/...`) |
| Every script in `Batch_Jobs/HPC/notebook/` (`run_rivet.slurm`, `run_rivet_MAP.slurm`, `run_rivet_rerunDP.slurm`, `run_bayes_emulator.slurm`, `run_bayes_calibration.slurm`, `run_bayes_closure.slurm`, `run_bayes_results.slurm`, `run_rivet_merge.sh`, `run_rivet_mergeMAP.sh`) | `#SBATCH -A ISAAC-UTK0244` — replace with your own SLURM account |

Even with those updated, none of this has been verified outside ISAAC — treat it as a starting point, not a guarantee.
