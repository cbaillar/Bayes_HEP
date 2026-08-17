import numpy as np
import bilby
import os

# ─────────────────────────────────────────────
# Sampling Utilities
# ─────────────────────────────────────────────

def latin_hypercube_sampling(dimensions, samples, seed):
    """Generate a Latin Hypercube sample in [0, 1]^dimensions."""
    np.random.seed(seed)
    result = np.empty((samples, dimensions))
    for i in range(dimensions):
        # Stratified random placement: one point per stratum
        points = np.linspace(0, 1, samples, endpoint=False) + np.random.rand(samples) / samples
        np.random.shuffle(points)
        result[:, i] = points

    return result


def detmax(A, n, max_iter=1000, tol=1e-6):
    """
    D-optimal design via coordinate exchange (DETMAX algorithm).

    Iteratively swaps candidate points in/out to maximise det(X^T X),
    i.e. to spread the selected n points as evenly as possible through
    the parameter space.

    Returns the selected sub-matrix B, the initial index set, and the
    final index set.
    """
    N = A.shape[0]

    # Start from a random subset of size n
    initidx = np.random.choice(N, size=n, replace=False)

    inidx  = initidx.copy()          # working "in" set (modified each iteration)
    outidx = np.setdiff1d(np.arange(N), inidx)

    for iter in range(max_iter):
        B  = A[inidx]
        W, U = np.linalg.eigh(B.T @ B)
        # Bh is the inverse square-root of B^T B in the eigenbasis
        Bh = U / np.sqrt(W) @ U.T

        logdet = np.log(W).sum()
        plus2  = ((A[outidx] @ Bh)**2).sum(1)   # leverage scores for candidates outside
        minus2 = ((A[inidx]  @ Bh)**2).sum(1)   # leverage scores for points inside
        pm2    = (A[inidx] @ Bh @ Bh.T @ A[outidx].T) ** 2

        # delta[i, j] > 0 means swapping inidx[i] for outidx[j] increases det
        delta = pm2 - np.outer(minus2, 1 + plus2) + plus2

        maxdelta_ind = np.argmax(delta)
        maxdelta_loc = (maxdelta_ind // (N - n), maxdelta_ind % (N - n))

        if delta[maxdelta_loc] < tol:
            print('maxdelta = {:.3E}, falling below tolerance of {:.3E} at '
                  'iteration {:d}'.format(delta[maxdelta_loc], tol, iter))
            break
        else:
            whichout = outidx[maxdelta_loc[1]]
            whichin  = inidx[maxdelta_loc[0]]

            # Swap the indices
            inidx[maxdelta_loc[0]]  = whichout
            outidx[maxdelta_loc[1]] = whichin

    if iter >= max_iter - 1:
        print('maxdelta = {:.3E}, reached iteration {:d}'.format(delta[maxdelta_loc], iter))

    B = A[inidx]
    return B, initidx, inidx


# ─────────────────────────────────────────────
# Design Point Generation
# ─────────────────────────────────────────────

def get_design(n_samples, priors, seed):
    """Generate LHS design points, mapped into each prior's native space via its
    rescale() (inverse-CDF) transform — works for any bilby prior type, not just Uniform."""
    lhs_samples = latin_hypercube_sampling(dimensions=len(priors), samples=n_samples, seed=seed)

    scaled_samples = np.zeros_like(lhs_samples)
    for i, key in enumerate(priors.keys()):
        scaled_samples[:, i] = priors[key].rescale(lhs_samples[:, i])

    return scaled_samples


def load_data(train_size, validation_size, design_points, priors, validation_indices_file=None):
    """
    Split design points into training and validation sets.

    Training indices are selected via DETMAX for maximal coverage.
    Validation indices are loaded from file if available (for reproducibility),
    otherwise taken from the tail of the remaining indices and saved.
    """
    if design_points is None:
        raise ValueError("No design points provided. Check input directory.")

    scaled_samples = np.array(design_points)
    N = len(scaled_samples)

    # Select training points using D-optimal exchange
    _, initidx, inidx = detmax(scaled_samples, train_size)
    train_indices = np.array(inidx)

    if validation_indices_file is not None and os.path.exists(validation_indices_file):
        validation_indices = np.loadtxt(validation_indices_file, dtype=int)
    else:
        remaining_indices  = np.setdiff1d(np.arange(N), train_indices)
        validation_indices = remaining_indices[-validation_size:]
        np.savetxt(validation_indices_file, validation_indices, fmt='%d')
        print(f"Saved validation indices to file")

    train_points      = scaled_samples[train_indices]
    validation_points = scaled_samples[validation_indices]

    return train_points, validation_points, train_indices, validation_indices


# ─────────────────────────────────────────────
# Prior Construction
# ─────────────────────────────────────────────

def get_prior(RawDesign):
    """Build a Bilby PriorDict from the parsed design file header."""

    # Map the string distribution names used in the .dat file to Bilby classes
    prior_type_map = {
        "Linear":            bilby.core.prior.Uniform,
        "Log":               bilby.core.prior.LogUniform,
        "Gaussian":          bilby.core.prior.Normal,
        "TruncatedGaussian": bilby.core.prior.TruncatedGaussian,
        "Delta":             bilby.core.prior.DeltaFunction,
        "PowerLaw":          bilby.core.prior.PowerLaw,
    }

    priors = {}

    for param in RawDesign['Parameter']:
        key = f"{param}:"
        if key in RawDesign:
            dist_type, *range_vals = RawDesign[key]
            range_vals = [val.strip('[],') for val in range_vals]
            range_vals = list(map(float, range_vals))

            if dist_type in prior_type_map:
                PriorClass = prior_type_map[dist_type]

                if dist_type in ("Linear", "Log", "PowerLaw"):
                    priors[param] = PriorClass(
                        minimum=range_vals[0], maximum=range_vals[1], name=param
                    )
                elif dist_type == "Gaussian":
                    priors[param] = PriorClass(
                        mu=range_vals[0], sigma=range_vals[1], name=param
                    )
                elif dist_type == "TruncatedGaussian":
                    priors[param] = PriorClass(
                        mu=range_vals[0], sigma=range_vals[1],
                        minimum=range_vals[2], maximum=range_vals[3], name=param
                    )
                elif dist_type == "Delta":
                    priors[param] = PriorClass(
                        peak=range_vals[0], name=param
                    )
            else:
                raise ValueError(f"Unsupported prior type '{dist_type}' for parameter '{param}'")

    parameter_names = list(priors.keys())
    dim = len(parameter_names)

    return priors, parameter_names, dim


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def generate_param_tag(param_names, values):
    """Build a compact string tag from parameter names and values for file naming."""
    return '_'.join(f"{name}_{value:.6g}" for name, value in zip(param_names, values))
