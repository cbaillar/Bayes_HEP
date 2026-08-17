# Bayes\_HEP Instructions

This guide provides step-by-step instructions for running the **Bayes\_HEP** project using Docker or Apptainer (formerly Singularity), both interactively and in batch mode. For the Jupyter-notebook and SLURM-based workflow used on UTK's ISAAC cluster, see [README_UTK.md](README_UTK.md).

---

## 🚀 Docker Workflow

### 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

docker pull cbaillar/bayes_hep:UTK

docker run -it --rm -v "$PWD":/workdir -e WORKDIR=/workdir cbaillar/bayes_hep

cp -r /usr/local/share/Bayes_HEP/Examples/New_Project .
```

---

### 2. Input Configuration

Edit the following files in `New_Project/input/Rivet/`:

- `analyses_list.txt` – List of Rivet analyses and histograms to run. Example:

  ```
  pp_7000:
  ATLAS_2010_I882098 d03-x01-y01 d07-x01-y01
  ATLAS_2012_I1188891 d02-x01-y01

  pp_13000:
  CMS_2018_I1663452 d03-x01-y01
  ```

- `parameter_prior_list.dat` – Parameter names, prior types, and ranges for sampling

- `parameter.cmnd` – Default Pythia8 parameter card used as a template for all runs

---

### 3. Interactive Execution (Inside Container)

Driver scripts in `New_Project/drivers/` wrap all CLI arguments as named variables at the top of the file — edit them to configure your run, then execute:

```sh
# Run the Rivet / model pipeline (design points, simulation, merging, input writing)
bash New_Project/drivers/Rivet_Main.sh

# Run the Bayesian emulation and calibration pipeline
bash New_Project/drivers/Bayes_Main.sh
```

Each driver calls a Python entry point in `New_Project/Batch_Jobs/` (`Rivet_Main.py` / `Bayes_Main.py`) and supports three runner modes set via the `RUNNER` variable at the top of the script:

| `RUNNER` | Description |
|---|---|
| `local` | Run directly inside the container (default) |
| `apptainer` | Run via `apptainer exec` — set `CONTAINER` and `BIND_PATH` |
| `docker` | Run via `docker run` — set `CONTAINER` and `BIND_PATH` |

#### Key parameters in `Rivet_Main.sh`

```sh
MAIN_DIR="${WORKDIR}/New_Project"
SEED=43                     # random seed
MODEL_SEED=283               # model (Pythia8) seed
RUN_MAP=false                # run a single MAP/best-fit point instead of the full design
CLEAR_RIVET_MODELS=false     # wipe rivet/Models before running
GET_DESIGN_POINTS=false      # generate new LHS design points
NSAMPLES=5                   # number of design points to generate
RIVET_SETUP=false            # build Rivet analyses
RUN_MODEL=false              # run Pythia8 + Rivet
RUN_BATCH=false               # run only a batch slice (BATCH_START:BATCH_END) of the design points
PT_MIN=-1                    # pT-hat bin lower edge (-1 = disabled)
PT_MAX=-1                    # pT-hat bin upper edge (-1 = disabled)
NEVENTS=1000                 # events per design point
RIVET_MERGE=true             # merge Rivet YODA outputs
EQUIV_ON=false                # treat equivalent design points as one during merge
WRITE_INPUT_RIVET=true       # extract data/prediction .dat files
COLL_SYSTEM="pp_200"         # space-separated: "pp_200 pp_7000"
```

#### Key parameters in `Bayes_Main.sh`

```sh
MAIN_DIR="${WORKDIR}/New_Project"
COLL_SYSTEM="all"           # space-separated: "pp_200 pp_7000", or "all"
CLEAR_OUTPUT=false           # wipe the output directory before running
CLEAN_INPUT=false            # wipe cleaned/merged input before re-merging
TRAIN_SIZE=70                # number of design points for training
VALIDATION_SIZE=38           # number of design points for validation
TRAIN_SURMISE=false          # train Surmise GP emulator
LOAD_SURMISE=true            # load previously trained Surmise emulator
SCALER_TYPE=None             # StandardScaler, MinMaxScaler, RobustScaler, or None — leave at None (see note below)
PCA=true                      # true = Surmise PCGP method, false = Surmise indGP method (see note below)
CLOSURE_TEST=false           # run a closure test against a held-out design point
CLOSURE_INDEX=25              # design point index used for the closure test
CLOSURE_PLOTS=false          # generate closure test plots
RUN_CALIBRATION=false        # run Bayesian calibration
COV=full                      # covariance mode: full or diag
SAMPLERS="dynesty"            # space-separated: "emcee dynesty ultranest"
NPOOL=5                       # number of parallel workers
SAMPLES=1000                  # MCMC steps (emcee) or live points (nested)
THIN_SAMPLES=2                 # thinning factor applied to chains
BURN_FRAC=0.2                  # fraction of the chain discarded as burn-in
DLOG=0.8                       # dlogz stopping criterion (nested samplers)
SIZE=5000                      # number of posterior samples drawn for result plots
RESULT_PLOTS=true             # generate posterior and result plots
```

> **`SCALER_TYPE` must stay `None`.** Surmise already scales the data internally, and the scikit-learn scaler path (`StandardScaler`/`MinMaxScaler`/`RobustScaler`) is not yet wired up — setting it to anything else is not currently supported.
>
> **`PCA` selects the Surmise emulator method**, not a separate preprocessing step: `PCA=true` uses Surmise's `PCGP` method, `PCA=false` uses `indGP` (one independent GP per observable). A standalone scikit-learn PCA step is not yet configured.

---

### 4. Batch Job Submission (Docker)

Edit `New_Project/Batch_Jobs/Docker/run_rivet_batch.sh` to configure your run:

```sh
COLLISIONS="pp_7000"            # space-separated systems
TOTAL_POINTS=5                  # total number of design points
TOTAL_EVENTS=1000               # total events across all jobs
NEVENTS=1000                    # events per job
CPU=5                           # CPUs to use (checked against available)
TARGET_EVENTS_PER_JOB=1000000  # used to compute adaptive batch size
```

Submit:

```sh
bash New_Project/Batch_Jobs/Docker/run_rivet_batch.sh
```

The script automatically:
- Computes an adaptive batch size based on total work and available CPUs
- Generates design points, runs all batches in parallel, merges Rivet outputs, and writes input files
- Saves per-batch stdout/stderr logs to `New_Project/Batch_Jobs/logs/`

---

## 🧠 HPC Workflow (Apptainer/Singularity)

### 1. Setup

```sh
mkdir Bayes_HEP
cd Bayes_HEP

apptainer build bayes_hep.sif docker://cbaillar/bayes_hep:UTK

apptainer shell --bind "$PWD":/workdir bayes_hep.sif

cp -r /usr/local/share/Bayes_HEP/Examples/New_Project .
```

---

### 2. Input Configuration

Edit the same input files as described in the Docker section under `New_Project/input/Rivet/`.

---

### 3. Interactive Execution (Inside Container)

Set `RUNNER="apptainer"` and configure `CONTAINER` and `BIND_PATH` in the driver files, then run as above:

```sh
bash New_Project/drivers/Rivet_Main.sh
bash New_Project/drivers/Bayes_Main.sh
```

---

### 4. Notebook Execution & SLURM Batch Jobs (UTK / ISAAC)

For Jupyter-notebook-driven execution and SLURM array-job batch submission, see **[README_UTK.md](README_UTK.md)** — that workflow was built specifically for UTK's ISAAC cluster and has ISAAC's paths and SLURM account hardcoded.

---

## ✅ Tips

- Edit variables at the top of each driver `.sh` file — do not edit the Python scripts directly for routine runs.
- Double-check all `.slurm` and `.sh` files for correct paths and parameters before submitting.
- SLURM output and error logs will be saved in the locations specified in your scripts.
- Rebuild or restart containers after modifying source code.

---

## ❓ Need Help?

If you encounter errors:

- Check logs in `New_Project/Batch_Jobs/logs/` for batch jobs
- Check SLURM logs for HPC job status and error messages
- Ensure all paths and inputs are correct
- Contact your system administrator or project maintainer for support
