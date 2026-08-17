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
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Rivet_Main.py"
INPUT_DIR="${MAIN_DIR}/input"
OUTPUT_DIR="${MAIN_DIR}/output"
INPUT_CLEANED_DIR="${OUTPUT_DIR}/input_cleaned"
SEED=43
MODEL_SEED=283
RUN_MAP=false
CLEAR_RIVET_MODELS=false
GET_DESIGN_POINTS=false
NSAMPLES=5
RIVET_SETUP=false
MODEL=pythia8
RUN_MODEL=false
RUN_BATCH=false
PT_MIN=-1
PT_MAX=-1
NEVENTS=1000
RIVET_MERGE=true
EQUIV_ON=false
WRITE_INPUT_RIVET=true
COLL_SYSTEM="pp_200"        # space-separated: "pp_200 pp_7000"

if [ "$RUN_BATCH" = "true" ]; then
    BATCH_START=0
    BATCH_END=10
else
    BATCH_START=0
    BATCH_END=$NSAMPLES
fi

# ─────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────
CMD=(python "$MAIN_SCRIPT" "$BATCH_START" "$BATCH_END"
    --main_dir           "$MAIN_DIR"
    --input_cleaned_dir  "$INPUT_CLEANED_DIR"
    --seed               "$SEED"
    --model_seed         "$MODEL_SEED"
    --Run_MAP            "$RUN_MAP"
    --clear_rivet_models "$CLEAR_RIVET_MODELS"
    --Get_Design_Points  "$GET_DESIGN_POINTS"
    --nsamples           "$NSAMPLES"
    --Rivet_Setup        "$RIVET_SETUP"
    --model              "$MODEL"
    --Run_Model          "$RUN_MODEL"
    --Run_Batch          "$RUN_BATCH"
    --PT_Min             "$PT_MIN"
    --PT_Max             "$PT_MAX"
    --nevents            "$NEVENTS"
    --Rivet_Merge        "$RIVET_MERGE"
    --equiv_on           "$EQUIV_ON"
    --Write_input_Rivet  "$WRITE_INPUT_RIVET"
    --Coll_System        $COLL_SYSTEM)

if [ "$RUNNER" = "apptainer" ]; then
    apptainer exec --bind "$BIND_PATH" "$CONTAINER" "${CMD[@]}"
elif [ "$RUNNER" = "docker" ]; then
    docker run --rm -v "$BIND_PATH" "$CONTAINER" "${CMD[@]}"
else
    "${CMD[@]}"
fi