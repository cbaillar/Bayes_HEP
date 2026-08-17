from surmise.emulation import emulator
from sklearn.gaussian_process import GaussianProcessRegressor as GPR
from sklearn.gaussian_process import kernels

import sklearn.decomposition as sklearn_decomposition
import sklearn.gaussian_process as sklearn_gaussian_process
import sklearn.preprocessing as sklearn_preprocessing

import dill
import numpy as np

# ─────────────────────────────────────────────
# Preprocessing
# ─────────────────────────────────────────────

def scale_preprocessing(scaler_type, x, y_data_results, y_train_results, y_val_results):
    """
    Fit a scaler on the experimental data and apply it to training and validation sets.

    The scaler is fitted on experimental y values (not simulation) so that the
    emulator operates in a space consistent with the likelihood evaluation.
    Returns the fitted scalers dict and the scaled result arrays.
    """
    scalers = {}
    for system in x.keys():
        scaler = scaler_type()

        # Fit on experimental data only — keeps scale consistent with likelihood
        scaler.fit(y_data_results[system].reshape(-1, 1))

        # Transform training data row-by-row (each row = one design point)
        y_train_results_scaled = np.zeros_like(y_train_results[system])
        for i in range(y_train_results[system].shape[0]):
            y_train_results_scaled[i, :] = scaler.transform(y_train_results[system][i, :].reshape(-1, 1)).flatten()
        y_train_results[system] = y_train_results_scaled

        # Transform validation data
        y_val_results_scaled = np.zeros_like(y_val_results[system])
        for i in range(y_val_results[system].shape[0]):
            y_val_results_scaled[i, :] = scaler.transform(y_val_results[system][i, :].reshape(-1, 1)).flatten()
        y_val_results[system] = y_val_results_scaled

        scalers[system] = scaler

    return scalers, y_train_results, y_val_results


# ─────────────────────────────────────────────
# Surmise Emulator
# ─────────────────────────────────────────────

def train_surmise(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type='indGP'):
    """Train a Surmise emulator for each system and save to disk."""
    Emulators['surmise'] = {}
    Surmise_val   = {}
    Surmise_train = {}

    for system in x.keys():
        print(f"Training Surmise emulator for {system} system.")

        emu = emulator(x=x[system], theta=train_points, f=y_train_results[system].T, method=method_type)
        Emulators['surmise'][system] = emu

        Surmise_val[system]   = emu.predict(x=x[system], theta=validation_points).mean().T
        Surmise_train[system] = emu.predict(x=x[system], theta=train_points).mean().T

        with open(f"{output_dir}/emulator/surmise_{system}.pkl", "wb") as f:
            dill.dump(Emulators['surmise'][system], f)

    print("Surmise emulators trained and saved.")

    return Emulators['surmise'], Surmise_val, Surmise_train


def load_surmise(Emulators, x, train_points, validation_points, output_dir):
    """Load saved Surmise emulators from disk and compute train/val predictions."""
    Emulators['surmise'] = {}
    Surmise_val   = {}
    Surmise_train = {}

    for system in x.keys():
        with open(f"{output_dir}/emulator/surmise_{system}.pkl", "rb") as f:
            Emulators['surmise'][system] = dill.load(f)

        print(f"Loading Surmise emulator for {system} system.")
        emu = Emulators['surmise'][system]
        Surmise_val[system]   = emu.predict(x=x[system], theta=validation_points).mean().T
        Surmise_train[system] = emu.predict(x=x[system], theta=train_points).mean().T

    return Emulators['surmise'], Surmise_val, Surmise_train


# ─────────────────────────────────────────────
# Scikit-learn GP Emulator
# ─────────────────────────────────────────────

def train_scikit(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type='GP'):
    """
    Train a scikit-learn GP emulator for each system and save to disk.

    The GP input is [x_obs | theta] concatenated, so the emulator maps
    (observable kinematics, model parameters) → predicted observable value.
    A Matern kernel with per-dimension length scales is used.
    """
    Emulators['scikit'] = {}
    Scikit_val   = {}
    Scikit_train = {}

    for system in x.keys():
        print(f"Training Scikit-learn emulator for {system} system.")

        # Length scale per input dimension (x dims + parameter dims)
        input_dim    = x[system].shape[1] + train_points.shape[1]
        length_scale = np.ones(input_dim)
        kernel       = 1.0 * kernels.Matern(length_scale=length_scale, length_scale_bounds=(1e-2, 1e3))

        combined_train = []
        combined_val   = []

        # Build combined input: tile each design point across all observable rows
        for train_point in train_points:
            train_point = np.atleast_1d(train_point)
            repeated    = np.tile(train_point, (x[system].shape[0], 1))
            combined_train.append(np.hstack((x[system], repeated)))

        for val_point in validation_points:
            val_point = np.atleast_1d(val_point)
            repeated  = np.tile(val_point, (x[system].shape[0], 1))
            combined_val.append(np.hstack((x[system], repeated)))

        combined_train = np.vstack(combined_train)
        combined_val   = np.vstack(combined_val)


    #    ##############################
    #    if method_type == "PCA":
    #        scaler = sklearn_preprocessing.StandardScaler()
    #        pca = sklearn_decomposition.PCA(n_components=max_n_components, svd_solver='full', whiten=False) # Include all PCs here, so we can access them later
    #        Y_pca = pca.fit_transform(scaler.fit_transform(Y))
    #        Y_pca_truncated = Y_pca[:,:config.n_pc]    # Select PCs here
    #        Y_reconstructed_truncated = Y_pca_truncated.dot(pca.components_[:config.n_pc,:])
    #        Y_reconstructed_truncated_unscaled = scaler.inverse_transform(Y_reconstructed_truncated)
    #        explained_variance_ratio = pca.explained_variance_ratio_
#
#
    #        emulators = [sklearn_gaussian_process.GaussianProcessRegressor(kernel=kernel,
    #                                                         alpha=config.alpha,
    #                                                         n_restarts_optimizer=config.n_restarts,
    #                                                         copy_X_train=False).fit(combined_train, y) for y in Y_pca_truncated.T]


    ################################

        gpr = GPR(kernel=kernel, alpha=0, n_restarts_optimizer=0)
        gpr.fit(combined_train, y_train_results[system].reshape(-1))

        Emulators['scikit'][system] = gpr
        Scikit_train[system] = gpr.predict(combined_train)
        Scikit_val[system]   = gpr.predict(combined_val)

    with open(f"{output_dir}/emulator/scikit.pkl", "wb") as f:
        dill.dump(Emulators['scikit'], f)
    print("Scikit-learn emulator trained and saved.")

    return Emulators['scikit'], Scikit_val, Scikit_train


def load_scikit(Emulators, x, train_points, validation_points, output_dir):
    """Load a saved scikit-learn GP emulator and compute train/val predictions."""
    Emulators['scikit'] = {}
    Scikit_val   = {}
    Scikit_train = {}

    with open(f"{output_dir}/emulator/scikit.pkl", "rb") as f:
        Emulators['scikit'] = dill.load(f)

    for system in x.keys():
        print(f"Loading Scikit-learn emulator for {system} system.")

        combined_train = []
        combined_val   = []

        for train_point in train_points:
            train_point = np.atleast_1d(train_point)
            repeated    = np.tile(train_point, (x[system].shape[0], 1))
            combined_train.append(np.hstack((x[system], repeated)))

        for val_point in validation_points:
            val_point = np.atleast_1d(val_point)
            repeated  = np.tile(val_point, (x[system].shape[0], 1))
            combined_val.append(np.hstack((x[system], repeated)))

        combined_train = np.vstack(combined_train)
        combined_val   = np.vstack(combined_val)

        gpr = Emulators['scikit'][system]

        Scikit_train[system] = gpr.predict(combined_train)
        Scikit_val[system]   = gpr.predict(combined_val)

    return Emulators['scikit'], Scikit_val, Scikit_train
