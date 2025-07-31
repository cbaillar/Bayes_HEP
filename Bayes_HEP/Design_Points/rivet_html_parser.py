import os
import re
import atexit
import numpy as np

# Buffer for accumulating predictions across DPs
_prediction_buffers = {}

def extract_data(filename, model, input_data_name, input_pred_name, obs, subobs, DP):
    datafile = {}
    with open(filename, 'r') as f:
        exec(f.read(), datafile)

    # Write data file only for DP 1
    if DP == 1:
        x     = np.array(datafile['xpoints']['Data'])
        xerr  = np.array(datafile['xerrs']['Data'])  # shape: (2, N)
        y     = np.array(datafile['yvals']['Data'])
        yerr  = np.array(datafile['yerrs']['Data'])  # shape: (2, N)

        write_data_dat_file(input_data_name, x, xerr, y, yerr, obs, subobs)

    # Find prediction keys that start with model name
    pred_key = next((k for k in datafile['yvals'] if k.startswith(model)), None)
    err_key  = next((k for k in datafile['yerrs'] if k.startswith(model)), None)

    if pred_key is None or err_key is None:
        raise KeyError(f"Could not find prediction keys starting with '{model}' in {filename}")

    y_pred = np.array(datafile['yvals'][pred_key])
    y_perr = np.array(datafile['yerrs'][err_key])

    # Buffer prediction data for multi-column output
    buffer_key = input_pred_name
    # ensure values column shape is (N,)
    vals = np.atleast_1d(y_pred).flatten()
    # combine stat+sys if needed
    if y_perr.ndim == 2 and y_perr.shape[0] == 2:
        errs = np.sqrt(y_perr[0]**2 + y_perr[1]**2).flatten()
    else:
        errs = np.atleast_1d(y_perr).flatten()

    buf = _prediction_buffers.setdefault(buffer_key, {
        'values': [], 'errors': [], 'datafile': input_data_name, 'obs': obs, 'subobs': subobs
    })
    buf['values'].append(vals)
    buf['errors'].append(errs)


def _write_full_prediction_files(filename, values_matrix, errors_matrix, datafile, obs, subobs):
    n_DP = values_matrix.shape[1]
    header_lines = [
        "# Version 0.0",
        f"# Data {datafile}.dat",
        f"# Observable: {obs}",
        f"# Subobservable: {subobs}",
        "# Design Design_Rivet.dat",
        "# " + " ".join(f"design_point{dp}" for dp in range(1, n_DP+1))
    ]
    # Write values
    with open(f'{filename}__values.dat', 'w') as f:
        f.write("\n".join(header_lines) + "\n")
        for row in values_matrix:
            f.write(" ".join(f"{v:.6e}" for v in row) + "\n")
    # Write errors
    with open(f'{filename}__errors.dat', 'w') as f:
        f.write("\n".join(header_lines) + "\n")
        for row in errors_matrix:
            f.write(" ".join(f"{e:.6e}" for e in row) + "\n")


def _flush_all_predictions():
    for fname, info in _prediction_buffers.items():
        values_matrix = np.column_stack(info['values'])
        errors_matrix = np.column_stack(info['errors'])
        _write_full_prediction_files(fname, values_matrix, errors_matrix, info['datafile'], info['obs'], info['subobs'])

atexit.register(_flush_all_predictions)


def write_data_dat_file(filename, x, xerr, y, yerr , obs, subobs):
    if not (len(x) == len(y) == len(xerr[0]) == len(xerr[1]) == len(yerr[0]) == len(yerr[1])):
        raise ValueError("Data arrays must be of equal length.")

    with open(f'{filename}.dat', 'w') as f:
        f.write("# Version 0.0\n")
        f.write(f"# Observable: {obs} \n")
        f.write(f"# Subobservable: {subobs} \n")
        f.write("# Label xmin xmax y y_err\n")
        for i in range(len(x)):
            xi = float(x[i])
            xe_low = float(xerr[0][i])
            xe_high = float(xerr[1][i])
            yi = float(y[i])
            ye_low = float(yerr[0][i])
            ye_high = float(yerr[1][i])

            xmin = xi - xe_low
            xmax = xi + xe_high
            yerr_avg = 0.5 * (ye_low + ye_high)

            f.write(f"{xmin:.6e} {xmax:.6e} {yi:.6e} {yerr_avg:.6e}\n")

def extract_labels(filename):
    raw_obs = None
    raw_subobs = None

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith("ax_xLabel"):
                label = line.split("=", 1)[1].strip()
                if label.startswith("r'") or label.startswith('r"'):
                    label = label[1:]
                raw_subobs = label.strip("'\"")

            elif line.startswith("ax_yLabel"):
                label = line.split("=", 1)[1].strip()
                if label.startswith("r'") or label.startswith('r"'):
                    label = label[1:]
                raw_obs = label.strip("'\"")

            if raw_obs and raw_subobs:
                break

    if raw_obs is None or raw_subobs is None:
        raise ValueError(f"Could not find both ax_yLabel and ax_xLabel in {filename}")

    return raw_obs, raw_subobs



