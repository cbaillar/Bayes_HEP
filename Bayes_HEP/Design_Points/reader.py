import numpy as np
import os

# ─────────────────────────────────────────────
# Design File Readers
# ─────────────────────────────────────────────

def ReadDesign(FileName):
    """Read a design parameter file (.dat) and return header metadata and design matrix."""
    Result = {}
    Version = ''
    Result["FileName"] = FileName

    has_data = False

    with open(FileName) as f:
        lines = f.readlines()

    for Line in lines:
        Items = Line.strip().split()
        if len(Items) < 2:
            continue

        if Items[0] == '#':
            if Items[1] == 'Version':
                Version = Items[2]
            elif Items[1] == 'Parameter':
                Result["Parameter"] = Items[2:]
            elif Items[1] == '-':
                # Each '# - Parameter <name> <dist> [range]' line defines a prior
                param = Items[3]
                Result[param] = Items[4:]
        else:
            has_data = True

    # Only load the numeric block if data rows exist (prior-only files have no rows)
    if has_data:
        Result["Design"] = np.loadtxt(FileName)
    else:
        Result["Design"] = None

    return Result


# ─────────────────────────────────────────────
# Experimental Data Reader
# ─────────────────────────────────────────────

def ReadData(FileName):
    """Read an experimental data file and return binned x/y values and metadata."""
    Result  = {}
    Version = ''

    Result["FileName"] = FileName
    filename = os.path.basename(FileName).replace('.dat', '')
    parts    = filename.split('__')

    # Parse metadata from filename: Data__Energy__System__Inspire__Histogram
    Result["Energy"]     = parts[1]
    Result["System"]     = parts[2]
    Result["Experiment"] = parts[3].split('_')[0]
    Result["Inspire"]    = parts[3]
    Result["Histogram"]  = parts[4]

    # ── Read header ───────────────────────────────────────────────────────────
    for Line in open(FileName):
        Items = Line.split()
        if len(Items) < 2:
            continue
        if Items[0] != '#':
            continue

        key = Items[1]

        if key == 'Version':
            Version = Items[2]
        elif key == 'Observable:':
            Result["Observable"] = Items[2:]
        elif key == 'Subobservable:':
            Result["Subobservable"] = Items[2:]
        elif key == 'Title:':
            Result["Title"] = ' '.join(Items[2:])
        elif key == 'XScale:':
            Result["XScale"] = Items[2]
        elif key == 'YScale:':
            Result["YScale"] = Items[2]
        elif key == 'XLims:':
            Result["XLims"] = (float(Items[2]), float(Items[3]))
        elif key == 'YLims:':
            Result["YLims"] = (float(Items[2]), float(Items[3]))
        elif key == 'xmin':
            Result["Label"] = Items[1:]

    # ── Validate column layout ────────────────────────────────────────────────
    XMode = ''
    if Result.get("Label", [])[0:4] == ['xmin', 'xmax', 'y', 'y_err']:
        XMode = 'xminmax'
    else:
        raise AssertionError(
            'Invalid list of initial columns! Should be (xmin, xmax, y, y_err)'
        )

    # ── Read data ─────────────────────────────────────────────────────────────
    RawData = np.loadtxt(FileName)

    Result["Data"] = {}
    if XMode == 'xminmax':
        # Convert bin edges to bin centres and half-widths
        Result["Data"]["x"]    = (RawData[:, 0] + RawData[:, 1]) / 2
        Result["Data"]["xerr"] = (RawData[:, 1] - RawData[:, 0]) / 2
        Result["Data"]["y"]    = RawData[:, 2]
        Result["Data"]["yerr"] = RawData[:, 3]

    return Result


# ─────────────────────────────────────────────
# Model Prediction Reader
# ─────────────────────────────────────────────

def ReadPrediction(FileName):
    """Read a model prediction file and its paired errors file, returning transposed arrays."""
    Result = {}
    Version = ''

    Result["FileName"] = FileName
    filename = os.path.basename(FileName).replace('.dat', '')
    print(filename)
    parts = filename.split('__')

    # Parse metadata from filename: Prediction__Model__Energy__System__Inspire__Histogram
    Result["Model"]      = parts[1]
    Result["Energy"]     = parts[2]
    Result["System"]     = parts[3]
    Result["Experiment"] = parts[4].split('_')[0]
    Result["Histogram"]  = parts[5]

    # ── Read header ───────────────────────────────────────────────────────────
    for Line in open(FileName):
        Items = Line.split()
        if (len(Items) < 2): continue
        if Items[0] != '#': continue

        if(Items[1] == 'Version'):
            Version = Items[2]
        elif(Items[1] == 'Data'):
            Result["Data"] = Items[2]
        elif(Items[1] == 'Observable:'):
            Result["Observable"] = Items[2:]
        elif(Items[1] == 'Subobservable:'):
            Result["Subobservable"] = Items[2:]
        elif(Items[1] == 'Design'):
            Result["Design"] = Items[2]

    # Transpose so shape is (n_design, n_bins) → stored as (n_bins, n_design)
    Result["Prediction"] = np.loadtxt(FileName).T

    # ── Read paired errors file ───────────────────────────────────────────────
    ErrorFileName = FileName.replace('values.dat', 'errors.dat')

    for Line in open(ErrorFileName):
        Items = Line.split()
        if (len(Items) < 2): continue
        if Items[0] != '#': continue

        if(Items[1] == 'Version'):
            Version = Items[2]
        elif(Items[1] == 'Data'):
            Result["Data"] = Items[2]
        elif(Items[1] == 'Design'):
            Result["Design"] = Items[2]

    Result["PredictionErrors"] = np.loadtxt(ErrorFileName).T

    return Result
