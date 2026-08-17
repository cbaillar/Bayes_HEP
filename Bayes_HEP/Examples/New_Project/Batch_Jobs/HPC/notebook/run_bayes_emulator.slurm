#!/bin/bash
#SBATCH -J emulator
#SBATCH -A ISAAC-UTK0244


########### USER-CUSTOMIZABLE VARIABLES #################
export MPLBACKEND=Agg

PROJECT=$1 
INDIR=$2
OUTDIR=$3 
COLLISIONS=$4
MODEL=$5
TRAIN=$6
VALIDATION=$7
PCA=$8
CONTAINER=$9
BIND_PATH=${10}

MAIN_DIR="${WORKDIR:-/workdir}/$PROJECT"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Bayes_Main.py"
INPUT_DIR="$MAIN_DIR/$INDIR"
OUTPUT_DIR="$MAIN_DIR/$OUTDIR"

#########################################################

apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
    python "$MAIN_SCRIPT" \
        --main_dir "$MAIN_DIR" \
        --input_dir "$INPUT_DIR" \
        --output_dir "$OUTPUT_DIR" \
        --clear_output False \
        --Coll_System ${COLLISIONS} \
        --model $MODEL \
        --train_size $TRAIN --validation_size $VALIDATION \
        --Train_Surmise True --Load_Surmise False --PCA $PCA\
        --Run_Calibration False --Result_plots False