#!/bin/bash
#SBATCH -J calibration
#SBATCH -A ISAAC-UTK0244

########### USER-CUSTOMIZABLE VARIABLES #################
export MPLBACKEND=Agg

PROJECT=$1 
INDIR=$2
OUTDIR=$3 
COLLISIONS=$4 
MODEL=$5
SAMPLER=$6
NPOOL=$7
CLOSURE_INDEX=$8
SAMPLES=$9       # Number of samples for MCMC
DLOG=${10} 
THIN_SAMPLES=${11}
BURN_FRAC=${12}
CONTAINER=${13}
BIND_PATH=${14}

MAIN_DIR="${WORKDIR:-/workdir}/$PROJECT"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Bayes_Main.py"
INPUT_DIR="$MAIN_DIR/$INDIR"
OUTPUT_DIR="$MAIN_DIR/$OUTDIR"



      "$CLOSURE_TEST"
    
#########################################################

apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
    python "$MAIN_SCRIPT" \
        --main_dir "$MAIN_DIR" \
        --input_dir "$INPUT_DIR" \
        --output_dir "$OUTPUT_DIR" \
        --clear_output False \
        --Coll_System ${COLLISIONS} \
        --model "$MODEL" \
        --Train_Surmise False --Load_Surmise True \
        --Closure_Test True --cov_mode full --closure_index "$CLOSURE_INDEX" --SAMPLERS "$SAMPLER" --thin_samples "$THIN_SAMPLES" --burn_frac "$BURN_FRAC" --dlog "$DLOG" --npool "$NPOOL" --Samples "$SAMPLES" \
        --Result_plots False 