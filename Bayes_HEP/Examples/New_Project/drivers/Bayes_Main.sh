#!/bin/bash

# ─────────────────────────────────────────────
# Runner: local (in container) | apptainer | docker
# ─────────────────────────────────────────────
RUNNER="apptainer"

WORK_DIR="/lustre/isaac24/proj/UTK0244/cbaillar/Bayes_HEP"
CONTAINER="${WORK_DIR}/bayes_hep.sif"   # path to .sif (apptainer) or image name (docker)
BIND_PATH="${WORK_DIR}:/workdir"        # host:container mount path

# ─────────────────────────────────────────────
# Parameters
# ─────────────────────────────────────────────
WORKDIR=${WORKDIR:-/workdir}
MAIN_DIR="${WORKDIR}/New_Project"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Bayes_Main.py"
INPUT_DIR="${MAIN_DIR}/input"
OUTPUT_DIR="${MAIN_DIR}/output"
MODEL=pythia8
CLEAR_OUTPUT=false
CLEAN_INPUT=false
TRAIN_SIZE=70
VALIDATION_SIZE=38
TRAIN_SURMISE=false
LOAD_SURMISE=true
SCALER_TYPE=None
PCA=true
CLOSURE_TEST=false
CLOSURE_INDEX=25
CLOSURE_PLOTS=false
RUN_CALIBRATION=false
COV=full                         #full or diag
SAMPLERS="dynesty"              # space-separated: "emcee dynesty ultranest"
NPOOL=5
SAMPLES=1000
THIN_SAMPLES=2
BURN_FRAC=0.2
DLOG=0.8
SIZE=5000
RESULT_PLOTS=true
COLL_SYSTEM="all"          # space-separated: "pp_200 pp_7000"

# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
CMD=(python3 "$MAIN_SCRIPT"
    --main_dir          "$MAIN_DIR"
    --input_dir         "$INPUT_DIR"
    --output_dir        "$OUTPUT_DIR"
    --model             "$MODEL"
    --clear_output      "$CLEAR_OUTPUT"
    --clean_input       "$CLEAN_INPUT"
    --train_size        "$TRAIN_SIZE"
    --validation_size   "$VALIDATION_SIZE"
    --Train_Surmise     "$TRAIN_SURMISE"
    --Load_Surmise      "$LOAD_SURMISE"
    --scaler_type       "$SCALER_TYPE"
    --PCA               "$PCA"
    --Closure_Test      "$CLOSURE_TEST"
    --closure_index     "$CLOSURE_INDEX"
    --Closure_plots     "$CLOSURE_PLOTS"
    --Run_Calibration   "$RUN_CALIBRATION"
    --cov_mode          "$COV"
    --SAMPLERS          $SAMPLERS
    --npool             "$NPOOL"
    --Samples           "$SAMPLES"
    --thin_samples      "$THIN_SAMPLES"
    --burn_frac         "$BURN_FRAC"
    --dlog              "$DLOG"
    --size              "$SIZE"
    --Result_plots      "$RESULT_PLOTS"
    --Coll_System       $COLL_SYSTEM)

if [ "$RUNNER" = "apptainer" ]; then
    apptainer exec --bind "$BIND_PATH" "$CONTAINER" "${CMD[@]}"
elif [ "$RUNNER" = "docker" ]; then
    docker run --rm -v "$BIND_PATH" "$CONTAINER" "${CMD[@]}"
else
    "${CMD[@]}"
fi