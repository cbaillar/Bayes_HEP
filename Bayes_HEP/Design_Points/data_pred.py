from Bayes_HEP.Design_Points import reader as Reader
import numpy as np
import os
import glob

# Module-level accumulators — populated by get_data and get_predictions
x, x_errors, y_data_results, y_data_errors, y_train_results, y_train_errors, y_val_results, y_val_errors = {}, {}, {}, {}, {}, {}, {}, {}

# ─────────────────────────────────────────────
# Data and Prediction Loading
# ─────────────────────────────────────────────

def get_data(all_data, system):
    """
    Accumulate experimental x/y values across all histograms for a given system.

    The x array is two-column: [histogram_index, subobservable_value], so the
    emulator can distinguish between observables with the same kinematic range.
    """
    for i, data_entry in enumerate(all_data):
        x_values = np.column_stack((
            np.full(len(data_entry["Data"]["x"]), i),   # histogram index (Λ column)
            np.array(data_entry["Data"]["x"])            # subobservable value
        ))
        x_errors_values    = np.array(data_entry["Data"]["xerr"])
        y_data_values      = np.array(data_entry["Data"]["y"])
        y_data_errors_values = np.array(data_entry["Data"]["yerr"])

        if system not in x:
            x[system]             = x_values
            x_errors[system]      = x_errors_values
            y_data_results[system] = y_data_values
            y_data_errors[system]  = y_data_errors_values
        else:
            x[system]             = np.concatenate((x[system], x_values))
            x_errors[system]      = np.concatenate((x_errors[system], x_errors_values))
            y_data_results[system] = np.concatenate((y_data_results[system], y_data_values))
            y_data_errors[system]  = np.concatenate((y_data_errors[system], y_data_errors_values))

    return x, x_errors, y_data_results, y_data_errors


def get_predictions(all_predictions, train_indices, validation_indices, system):
    """
    Split model predictions into training and validation sets for a given system.

    Only 'values' files are processed; paired 'errors' files are handled inside
    ReadPrediction. Results are horizontally stacked across histograms.
    """
    for prediction in all_predictions:
        if "values" not in prediction["FileName"]:
            continue

        prediction_values = np.array(prediction["Prediction"])
        prediction_errors = np.array(prediction["PredictionErrors"])

        if system not in y_train_results:
            y_train_results[system] = prediction_values[train_indices]
            y_train_errors[system]  = prediction_errors[train_indices]
            y_val_results[system]   = prediction_values[validation_indices]
            y_val_errors[system]    = prediction_errors[validation_indices]
        else:
            y_train_results[system] = np.hstack((y_train_results[system], prediction_values[train_indices]))
            y_train_errors[system]  = np.hstack((y_train_errors[system],  prediction_errors[train_indices]))
            y_val_results[system]   = np.hstack((y_val_results[system],   prediction_values[validation_indices]))
            y_val_errors[system]    = np.hstack((y_val_errors[system],    prediction_errors[validation_indices]))

    return y_train_results, y_train_errors, y_val_results, y_val_errors


# ─────────────────────────────────────────────
# Design Index Utilities
# ─────────────────────────────────────────────

def get_design_index(input_dir):
    """Return sorted list of non-merged design .dat files in the Design directory."""
    index_files = glob.glob(f"{input_dir}/Design/Design__Rivet__*.dat")
    index_files = [file for file in index_files if "Merged" not in file]
    index_files = sorted(index_files, key=lambda file: int(file.split("__")[-1].split(".")[0]))
    return index_files


def get_max_design_index(main_dir):
    """Return sorted design file list and the highest design index found."""
    index_files = glob.glob(f"{main_dir}/input/Design/Design__Rivet__*.dat")
    index_files = [file for file in index_files if "Merged" not in file]
    index_files = sorted(index_files, key=lambda file: int(file.split("__")[-1].split(".")[0]))
    index_numbers = [int(file.split("__")[-1].split(".")[0]) for file in index_files]
    max_index = max(index_numbers) if index_numbers else 0
    return index_files, max_index


def get_existing_design_points(index_files):
    """Collect all non-comment data rows from a list of design files."""
    existing_rows = []
    for oldfile in index_files:
        with open(oldfile) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                existing_rows.append(line)
    return existing_rows


# ─────────────────────────────────────────────
# Prediction File Management
# ─────────────────────────────────────────────

def group_histograms_by_design(DG_predictions_files, merged_dir):
    """
    Merge per-design-group prediction files into a single file per histogram.

    Files are grouped by stripping the DG token from the filename, sorted by
    DG index, then column-stacked so each column is one design point.
    The individual DG files are removed after merging.
    """
    hist_groups = {}
    for f in DG_predictions_files:
        parts = os.path.basename(f).split("__")
        parts = [p for p in parts if not p.startswith("DG")]
        key = "__".join(parts)
        hist_groups.setdefault(key, []).append(f)

    for key, DG_list in hist_groups.items():
        DG_list.sort(
            key=lambda p: int(
                next(
                    (t.split("_")[1] for t in os.path.basename(p).split("__") if t.startswith("DG_")),
                    "-1",
                )
            )
        )

        # Preserve all header lines except the last (column-label line)
        headers = [line for line in open(DG_list[0]) if line.startswith("#")][:-1]
        data   = [np.loadtxt(f) for f in DG_list]
        merged = np.column_stack(data)
        with open(f"{merged_dir}/{key}", "w") as f:
            f.writelines(headers)
            f.write("# " + " ".join(f"design_point{i+1}" for i in range(merged.shape[1])) + "\n")
            np.savetxt(f, merged, fmt="%.6e")

        for f in DG_list:
            if "DG" in f:
                os.remove(f)


def zeros_nan_remover(main_dir, prediction_dir, data_dir):
    """
    Remove data rows that contain zeros or NaNs from prediction and data files.

    Scans all prediction files first; if none need cleaning the function exits
    early. Otherwise, for each file the bad row indices are collected and popped
    from both the prediction file and its paired data file. A removal report is
    written to removal_report.txt.
    """
    # number_of_DG tracks merged design groups for data-file index mapping
    number_of_DG = 0
    if number_of_DG == 0: number_of_DG = 1  # avoid division by zero

    removal_report_list = []

    prediction_files = os.listdir(prediction_dir)
    prediction_files.sort()
    prediction_files_path = [f'{prediction_dir}/{prediction_files}' for prediction_files in prediction_files]

    data_files = os.listdir(data_dir)
    data_files.sort()
    data_files_path = [f'{data_dir}/{data_files}' for data_files in data_files]

    all_predictions = [Reader.ReadPrediction(f) for f in prediction_files_path]

    # Quick pass: check whether any cleaning is needed at all
    escape_cleaning = True
    for file_number in range(len(all_predictions)):
        for design_point in all_predictions[file_number]['Prediction']:
            if 0 in design_point or any([np.isnan(n) for n in design_point]):
                escape_cleaning = False

    # Main cleaning loop — skipped entirely if escape_cleaning is True
    for file_number in range(len(all_predictions)):

        if escape_cleaning:
            print('\nNo file to clean. Skipping this step.\n')
            break

        missing = 0
        design_point_number = 0
        line_delete = []

        # Wrap scalar prediction (single design point) in a list so it's iterable
        if isinstance(all_predictions[file_number]['Prediction'][0], float):
            all_predictions[file_number]['Prediction'] = [all_predictions[file_number]['Prediction']]

        for design_point in all_predictions[file_number]['Prediction']:
            design_point_number += 1
            data_point_number = 0

            for data_point in design_point:
                data_point_number += 1

                if data_point == 0:
                    missing += 1
                    line_delete.append(data_point_number)

                if np.isnan(data_point):
                    missing += 1
                    line_delete.append(data_point_number)

        unique_line_delete = list(set(line_delete))
        unique_line_delete.sort()

        # Load prediction file into memory for in-place row removal
        with open(prediction_files_path[file_number], 'r') as f:
            file_list = [line for line in f]

        for x in unique_line_delete:
            file_list.pop(x - (data_point_number + 1))

        with open(prediction_files_path[file_number], 'w') as f:
            f.writelines(file_list)

        split_path = prediction_files[file_number].split('__')

        if split_path[-1].split('.')[0] == 'values':

            # Mirror the same row removals in the corresponding data file
            with open(data_files_path[int((file_number) / (2 * number_of_DG))], 'r') as f:
                file_list = [line for line in f]

            for x in unique_line_delete:
                file_list.pop(x - (data_point_number + 1))
            with open(data_files_path[int(file_number / (2 * number_of_DG))], 'w') as f:
                f.writelines(file_list)

            print(f'{split_path[4]} {split_path[5]}     ROWS REMOVED: {len(unique_line_delete)}     TOTAL UNFILLED VALUES: {missing}')
            print(f'INDEX OF DATA POINTS REMOVED: {unique_line_delete}')
            print('----------------------------------------------------------------------------------')

            removal_report_list.append(f'{split_path[4]} {split_path[5]}     ROWS REMOVED: {len(unique_line_delete)}     TOTAL UNFILLED VALUES: {missing}\n')
            removal_report_list.append(f'INDEX OF DATA POINTS REMOVED: {unique_line_delete}\n\n')

    if escape_cleaning == False:
        with open('removal_report.txt', 'w') as f:
            f.writelines(removal_report_list)
