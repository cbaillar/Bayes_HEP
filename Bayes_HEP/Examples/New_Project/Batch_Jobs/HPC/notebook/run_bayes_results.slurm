#!/bin/bash
#SBATCH -J results
#SBATCH -A ISAAC-UTK0244


########### USER-CUSTOMIZABLE VARIABLES #################
export MPLBACKEND=Agg

PROJECT=$1 
INDIR=$2
OUTDIR=$3 
COLLISIONS_STR=$4
MODEL=$5
TRAIN=$6
VALIDATION=$7
SAMPLERS_STR=$8
SIZE=$9
CONTAINER=${10}
BIND_PATH=${11}

MAIN_DIR="${WORKDIR:-/workdir}/$PROJECT"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Bayes_Main.py"
INPUT_DIR="$MAIN_DIR/$INDIR"
OUTPUT_DIR="$MAIN_DIR/$OUTDIR"

IFS=',' read -ra COLLISIONS_ARR <<< "$COLLISIONS_STR"
IFS=',' read -ra SAMPLERS_ARR <<< "$SAMPLERS_STR"


#########################################################

apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
    python "$MAIN_SCRIPT" \
        --main_dir "$MAIN_DIR" \
        --input_dir "$INPUT_DIR" \
        --output_dir "$OUTPUT_DIR" \
        --clear_output False \
        --Coll_System "${COLLISIONS_ARR[@]}" \
        --model $MODEL \
        --train_size $TRAIN --validation_size $VALIDATION \
        --Train_Surmise False --Load_Surmise True \
        --SAMPLERS "${SAMPLERS_ARR[@]}" \
        --Result_plots True --size $SIZE