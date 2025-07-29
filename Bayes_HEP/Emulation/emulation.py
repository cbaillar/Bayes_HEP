from surmise.emulation import emulator
from sklearn.gaussian_process import GaussianProcessRegressor as GPR
from sklearn.gaussian_process import kernels

import sklearn.decomposition as sklearn_decomposition
import sklearn.gaussian_process as sklearn_gaussian_process
import sklearn.preprocessing as sklearn_preprocessing

import dill
import numpy as np

def train_surmise(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type='indGP'):
    Emulators['surmise'] = {}
    Surmise_val = {}
    Surmise_train = {}

    for system in x.keys():
        print(f"Training Surmise emulator for {system} system.")        
        emu = emulator(x=x[system], theta=train_points, f=y_train_results[system].T, method=method_type)
        Emulators['surmise'][system] = emu

        Surmise_val[system] = emu.predict(x=x[system], theta=validation_points).mean().T
        Surmise_train[system] = emu.predict(x=x[system], theta=train_points).mean().T
    
    with open(f"{output_dir}/emulator/surmise.pkl", "wb") as f:
        dill.dump(Emulators['surmise'], f)
    print("Surmise emulators trained and saved.")

    return Emulators['surmise'], Surmise_val, Surmise_train

def load_surmise(Emulators, x, train_points, validation_points, output_dir):
    Surmise_val = {}
    Surmise_train = {}
    with open(f"{output_dir}/emulator/surmise.pkl", "rb") as f:
        Emulators['surmise'] = dill.load(f)

    for system in x.keys():
        print(f"Loading Surmise emulator for {system} system.")        
        emu = Emulators['surmise'][system]
        Surmise_val[system] = emu.predict(x=x[system], theta=validation_points).mean().T
        Surmise_train[system] = emu.predict(x=x[system], theta=train_points).mean().T

    return Emulators['surmise'], Surmise_val, Surmise_train


def train_scikit(Emulators, x, y_train_results, train_points, validation_points, output_dir, method_type='GP'):
    Emulators['scikit'] = {}

    Scikit_val = {}
    Scikit_train = {}

    for system in x.keys():
        print(f"Training Scikit-learn emulator for {system} system.")

        input_dim = len(x[system]) + train_points.shape[1]  # dynamically calculate for each system
        length_scale = np.ones(input_dim)
        kernel = 1.0 * kernels.Matern(length_scale=length_scale, length_scale_bounds=(1e-2, 1e3))

        combined_train = []
        combined_val = []

        for train_point in train_points:
            combined_train.append(np.concatenate((x[system], train_point)))
        for val_point in validation_points:
            combined_val.append(np.concatenate((x[system], val_point)))

        combined_train = np.array(combined_train)
        combined_val = np.array(combined_val)

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
        gpr.fit(combined_train, y_train_results[system])

        Emulators['scikit'][system] = gpr
        Scikit_train[system] = gpr.predict(combined_train)
        Scikit_val[system] = gpr.predict(combined_val)

    with open(f"{output_dir}/emulator/scikit.pkl", "wb") as f:
        dill.dump(Emulators['scikit'], f)
    print("Scikit-learn emulator trained and saved.")

    return Emulators['scikit'], Scikit_val, Scikit_train

def load_scikit(Emulators, x, train_points, validation_points, output_dir):

    Scikit_val = {}
    Scikit_train = {}

    with open(f"{output_dir}/emulator/scikit.pkl", "rb") as f:
        Emulators['scikit'] = dill.load(f)

    for system in x.keys():
        print(f"Loading Scikit-learn emulator for {system} system.")
    
        combined_train = []
        combined_val = []

        for train_point in train_points:
            combined_train.append(np.concatenate((x[system], train_point)))
        for val_point in validation_points:
            combined_val.append(np.concatenate((x[system], val_point)))

        combined_train = np.array(combined_train)
        combined_val = np.array(combined_val)

        gpr = Emulators['scikit'][system]

        Scikit_train[system] = gpr.predict(combined_train)
        Scikit_val[system] = gpr.predict(combined_val)

    return Emulators['scikit'], Scikit_val, Scikit_train