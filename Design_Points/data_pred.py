import numpy as np

x, x_errors, y_data_results, y_data_errors, y_train_results, y_train_errors, y_val_results, y_val_errors  = {},  {}, {}, {}, {}, {}, {}, {}

def get_system(filename):
    if "200__AuAu" in filename:
        return "AuAu200"
    elif "2760__PbPb" in filename:
        return "PbPb2760"
    elif "5020__PbPb" in filename:
        return "PbPb5020"
    return None


def get_data(all_data, system):
    for data_entry in all_data:
        #system = get_system(data_entry["FileName"])

        x_values = np.array(data_entry["Data"]["x"])
        x_errors_values = np.array(data_entry["Data"]["xerr"])
        y_data_values = np.array(data_entry["Data"]["y"])
        y_data_errors_values = np.array(data_entry["Data"]["yerr"])

        if system not in x:
            x[system] = x_values
            x_errors[system] = x_errors_values
            y_data_results[system] = y_data_values
            y_data_errors[system] = y_data_errors_values
        else:
            x[system] = np.concatenate((x[system], x_values))
            x_errors[system] = np.concatenate((x_errors[system], x_errors_values))
            y_data_results[system] = np.concatenate((y_data_results[system], y_data_values))
            y_data_errors[system] = np.concatenate((y_data_errors[system], y_data_errors_values))

    return x, x_errors, y_data_results, y_data_errors

def get_predictions(all_predictions, train_indices, validation_indices, system):
    for prediction in all_predictions:
        if "values" not in prediction["FileName"]:
            continue
        #system = get_system(prediction["FileName"])

        prediction_values = np.array(prediction["Prediction"])
        prediction_errors = np.array(prediction["PredictionErrors"])

        if system not in y_train_results:
            y_train_results[system] = prediction_values[train_indices]
            y_train_errors[system] = prediction_errors[train_indices]
            y_val_results[system] = prediction_values[validation_indices]
            y_val_errors[system] = prediction_errors[validation_indices]
        else:
            y_train_results[system] = np.hstack((y_train_results[system], prediction_values[train_indices]))
            y_train_errors[system] = np.hstack((y_train_errors[system], prediction_errors[train_indices]))
            y_val_results[system] = np.hstack((y_val_results[system], prediction_values[validation_indices]))
            y_val_errors[system] = np.hstack((y_val_errors[system], prediction_errors[validation_indices]))
         
    return y_train_results, y_train_errors, y_val_results, y_val_errors