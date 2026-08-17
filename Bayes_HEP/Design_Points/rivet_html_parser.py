import os
import re
import atexit
import numpy as np

# Buffer for accumulating predictions across DPs
_prediction_buffers = {}

def extract_data(filename, model, input_data_name, input_pred_name, obs, subobs, DP,
                 x_scale=None, y_scale=None, x_lims=None, y_lims=None, title=None):
    datafile = {}
    with open(filename, 'r') as f:
        exec(f.read(), datafile)

    # Write data file only for DP 1
    if DP == 1:
        x    = np.array(datafile['xpoints']['Data'])
        xerr = np.array(datafile['xerrs']['Data'])   # shape: (2, N)
        y    = np.array(datafile['yvals']['Data'])
        yerr = np.array(datafile['yerrs']['Data'])   # shape: (2, N)

        write_data_dat_file(input_data_name, x, xerr, y, yerr, obs, subobs,
                            x_scale=x_scale, y_scale=y_scale,
                            x_lims=x_lims,   y_lims=y_lims,
                            title=title)

    # Find prediction keys that start with model name
    pred_key = next((k for k in datafile['yvals'] if k.startswith(model)), None)
    err_key  = next((k for k in datafile['yerrs'] if k.startswith(model)), None)

    if pred_key is None or err_key is None:
        raise KeyError(f"Could not find prediction keys starting with '{model}' in {filename}")

    y_pred = np.array(datafile['yvals'][pred_key])
    y_perr = np.array(datafile['yerrs'][err_key])

    # Buffer prediction data for multi-column output
    vals = np.atleast_1d(y_pred).flatten()
    if y_perr.ndim == 2 and y_perr.shape[0] == 2:
        errs = np.sqrt(y_perr[0]**2 + y_perr[1]**2).flatten()
    else:
        errs = np.atleast_1d(y_perr).flatten()

    buf = _prediction_buffers.setdefault(input_pred_name, {
        'values':   [],
        'errors':   [],
        'datafile': input_data_name,
        'obs':      obs,
        'subobs':   subobs,
        'x_scale':  x_scale,
        'y_scale':  y_scale,
        'x_lims':   x_lims,
        'y_lims':   y_lims,
        'title':    title,
    })
    buf['values'].append(vals)
    buf['errors'].append(errs)


def _write_full_prediction_files(filename, values_matrix, errors_matrix,
                                 datafile, obs, subobs,
                                 x_scale=None, y_scale=None,
                                 x_lims=None, y_lims=None, title=None):
    n_DP = values_matrix.shape[1]
    header_lines = [
        "# Version 0.0",
        f"# Data {datafile}.dat",
        f"# Observable: {obs}",
        f"# Subobservable: {subobs}",
    ]
    if title is not None:
        header_lines.append(f"# Title: {title}")
    if x_scale is not None:
        header_lines.append(f"# XScale: {x_scale}")
    if y_scale is not None:
        header_lines.append(f"# YScale: {y_scale}")
    if x_lims is not None:
        header_lines.append(f"# XLims: {x_lims[0]:.6e} {x_lims[1]:.6e}")
    if y_lims is not None:
        header_lines.append(f"# YLims: {y_lims[0]:.6e} {y_lims[1]:.6e}")
    header_lines += [
        "# Design Design_Rivet.dat",
        "# " + " ".join(f"design_point{dp}" for dp in range(1, n_DP + 1)),
    ]

    header = "\n".join(header_lines) + "\n"

    with open(f'{filename}__values.dat', 'w') as f:
        f.write(header)
        for row in values_matrix:
            f.write(" ".join(f"{v:.6e}" for v in row) + "\n")

    with open(f'{filename}__errors.dat', 'w') as f:
        f.write(header)
        for row in errors_matrix:
            f.write(" ".join(f"{e:.6e}" for e in row) + "\n")


def _flush_all_predictions():
    for fname, info in _prediction_buffers.items():
        values_matrix = np.column_stack(info['values'])
        errors_matrix = np.column_stack(info['errors'])
        _write_full_prediction_files(
            fname, values_matrix, errors_matrix,
            info['datafile'], info['obs'], info['subobs'],
            x_scale=info.get('x_scale'),
            y_scale=info.get('y_scale'),
            x_lims=info.get('x_lims'),
            y_lims=info.get('y_lims'),
            title=info.get('title'),
        )

atexit.register(_flush_all_predictions)


def write_data_dat_file(filename, x, xerr, y, yerr, obs, subobs,
                        x_scale=None, y_scale=None,
                        x_lims=None,  y_lims=None,
                        title=None):

    if not (len(x) == len(y) == len(xerr[0]) == len(xerr[1])
            == len(yerr[0]) == len(yerr[1])):
        raise ValueError("Data arrays must be of equal length.")

    with open(f'{filename}.dat', 'w') as f:
        f.write("# Version 0.0\n")
        f.write(f"# Observable: {obs}\n")
        f.write(f"# Subobservable: {subobs}\n")
        if title is not None:
            f.write(f"# Title: {title}\n")
        if x_scale is not None:
            f.write(f"# XScale: {x_scale}\n")
        if y_scale is not None:
            f.write(f"# YScale: {y_scale}\n")
        if x_lims is not None:
            f.write(f"# XLims: {x_lims[0]:.6e} {x_lims[1]:.6e}\n")
        if y_lims is not None:
            f.write(f"# YLims: {y_lims[0]:.6e} {y_lims[1]:.6e}\n")
        f.write("# xmin xmax y y_err\n")

        for i in range(len(x)):
            xi      = float(x[i])
            xe_low  = float(xerr[0][i])
            xe_high = float(xerr[1][i])
            yi      = float(y[i])
            ye_low  = float(yerr[0][i])
            ye_high = float(yerr[1][i])

            xmin     = xi - xe_low
            xmax     = xi + xe_high
            yerr_avg = 0.5 * (ye_low + ye_high)

            f.write(f"{xmin:.6e} {xmax:.6e} {yi:.6e} {yerr_avg:.6e}\n")


def extract_labels(filename):
    """
    Extract plot metadata from a Python plot script.
    Returns: (obs, subobs, x_scale, y_scale, x_lims, y_lims, title)
    """
    raw_obs    = None
    raw_subobs = None
    x_scale    = None
    y_scale    = None
    x_lims     = None
    y_lims     = None
    title      = None

    def _strip_rstring(s):
        s = s.strip()
        if s.startswith("r'") or s.startswith('r"'):
            s = s[1:]
        return s.strip("'\"")

    def _parse_tuple(s):
        s = s.strip().strip('()')
        parts = [p.strip() for p in s.split(',')]
        return tuple(float(p) for p in parts if p)

    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('ax_xLabel'):
                val = line.split('=', 1)[1].strip()
                raw_subobs = _strip_rstring(val)

            elif line.startswith('ax_yLabel'):
                val = line.split('=', 1)[1].strip()
                raw_obs = _strip_rstring(val)

            elif line.startswith('ax_title'):
                val = line.split('=', 1)[1].strip()
                title = _strip_rstring(val)

            elif line.startswith('ax_xScale'):
                val = line.split('=', 1)[1].strip()
                x_scale = val.strip("'\"")

            elif line.startswith('ax_yScale'):
                val = line.split('=', 1)[1].strip()
                y_scale = val.strip("'\"")

            elif line.startswith('xLims'):
                val = line.split('=', 1)[1].strip()
                x_lims = _parse_tuple(val)

            elif line.startswith('yLims'):
                val = line.split('=', 1)[1].strip()
                y_lims = _parse_tuple(val)

    if raw_obs is None or raw_subobs is None:
        raise ValueError(
            f"Could not find both ax_yLabel and ax_xLabel in {filename}"
        )

    return raw_obs, raw_subobs, x_scale, y_scale, x_lims, y_lims, title