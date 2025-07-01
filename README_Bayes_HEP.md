This repository contains driver scripts to automate the workflow for tuning Monte Carlo models (like Pythia8) and performing Bayesian calibration using design points, emulators, and experimental data comparisons.

---

## 🧠 Overview

### `New_Project/drivers/Rivet_Main.py`
This script:
- Generates design points using Latin Hypercube Sampling (LHS)
- Runs model simulations (e.g., Pythia8) using the design points
- Executes Rivet analyses and collects results
- Writes parsed data/prediction inputs to disk for use in Bayesian calibration

### `New_Project/drivers/Bayes_Main.py`
This script:
- Splits design points into training and validation sets using `detmax` (if enabled)
- Trains Gaussian Process emulators (`surmise` and/or `scikit-learn`)
- Runs MCMC-based calibration with `bilby`
- Generates posterior result plots

---

## 🚀 Example Usage

```bash
# Run design points through model and Rivet
python New_Project/drivers/Rivet_Main.py

# Run emulator training + calibration
python New_Project/drivers/Bayes_Main.py
```

---

## ⚙️ Parameters

### Rivet_Main.py

```python
main_dir = "New_Project"
seed = 43                   # seed for LHS
model_seed = 283            # seed for model

clear_rivet = True          # clear rivet directory
Coll_System = ['pp_7000']   # collision system(s)
Get_Design_Points = True    # True = generate with LHS; False = load from file
nsamples = 10               # number of design points
model = 'pythia8'           # currently only 'pythia8'
Run_Model = True            # run the model and Rivet
nevents = 1000              # number of events per model run
Write_input_Rivet = True    # extract Data/Prediction from HTML reports
```

### Bayes_Main.py

```python
main_dir = "New_Project"
seed = 43
clear_output = True
Coll_System = ['pp_7000']

model = 'pythia8'
dmax = True                 # use detmax for selecting training points
train_size = 80             # percent of points for training
validation_size = 20        # percent for validation

# Emulator Training
Train_Surmise = True
Train_Scikit = True
PCA = True

# Calibration Settings
Calibration = True
nwalkers = 50
Samples = 100
percent = 0.15              # % of trace to retain for posterior
Load_Calibration = True

# Result Plotting
size = 1000
Result_plots = True
```

---

## 📁 Input Files

### `analyses_list.txt`
Defines which Rivet analyses and histograms to use. Grouped by system tag:

```
PbPb5020:
ALICE_2020_I1819050 d01-x01-y01 d01-x01-y02
CMS_2017_I1625109 d02-x01-y01
```

### `parameter_prior_list.dat`
Defines model parameters and their prior ranges for LHS.

```
# Parameter FSRalphaS ISRalphaS primordialKT aLund bLund CRrange
# - Parameter FSRalphaS:     Linear [0.12, 0.15]  
# - Parameter ISRalphaS:     Linear [0.12, 0.15]  
# - Parameter primordialKT:  Linear [1.0, 3.0]     
# - Parameter aLund:         Linear [0.5, 1.0]     
# - Parameter bLund:         Linear [0.6, 1.6]     
# - Parameter CRrange:       Linear [1.5, 2.5] 
```

### `parameter.cmnd` (coming soon)
Will allow direct `.cmnd`-based model runs.

```
! Used for Bayesian Parameterization 
SpaceShower:alphaSvalue             = 0.148337
TimeShower:alphaSvalue              = 0.120345
StringZ:aLund                       = 0.828033
StringZ:bLund                       = 1.03103
ColourReconnection:range            = 1.62662
```

### `Design__*.dat`
Design points generated or loaded by `Rivet_Main.py`.

### `Data__*.dat`
Parsed data files from Rivet HTML reports:

```
# Version 0.0
# Label xmin xmax y y_err
-2.500000e+00 -2.400000e+00 2.196000e+00 1.510132e-01
```

### `Prediction__*.dat`
Model predictions at each design point:

```
# Version 0.0
# Data New_Project/input/Data/Data__7000__pp__1_N_ev_dN_ch_deta__eta_ATLAS__d03-x01-y01.dat
# Design Design_Rivet.dat
# design_point1 design_point2 
2.863941e-01 2.799061e-01 
2.856105e-01 2.587497e-01 
...
```

---

## 📌 Notes

- Make sure you have the `hepstore/rivet-pythia` container ready (via Docker or Singularity).
- All design point outputs and calibration-ready files will be stored in `input/Design`, `input/Data`, and `input/Prediction`.
"""