This Dockerfile creates a containerized environment for running Rivet + Pythia simulations and performing Bayesian inference using `bilby`, `surmise`, and `scikit-learn`.

---

## 📦 Base Image

The build starts from:

```
hepstore/rivet-pythia:latest
```

> ⚠️ **Important**: Avoid using `:latest` in production. Pin to a tested version (e.g., `4.0.3-8313`) to ensure reproducibility.

---

## 🧪 Included Packages

In addition to the Rivet + Pythia tools from the base image, this Dockerfile installs:

- [`bilby`](https://lscsoft.docs.ligo.org/bilby/)
- [`surmise`](https://github.com/snthilina/surmise)
- [`scikit-learn`](https://scikit-learn.org/)

---

## 🚀 Getting Started

### Build the Docker Image

```docker build -t bayes_hep .
docker build -t bayes_hep .
```

### Run the Container

Mount your working directory inside the container and start an interactive shell:

```bash
docker run -it --rm -v "$PWD":/workdir bayes_hep
```

> Your files in the current directory will be accessible at `/workdir` inside the container.

---

## 📁 Default Workdir

Inside the container, the working directory is set to:

```
/workdir
```

This is where your scripts, data, and results should reside and be mounted from the host.

---

## 🛠 Notes

- Designed to support pipelines involving design point generation, Rivet analyses, emulator training, and Bayesian calibration.
- Use with `New_Project/drivers/Rivet_Main.py` and `Bayes_Main.py`.
