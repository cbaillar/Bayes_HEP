#!/bin/bash
#SBATCH -J MAP
#SBATCH -A ISAAC-UTK0244

INPUT_DIR=$1
DO_PT_HAT_BINS=$2
PT_EDGES_STR=$3
PROJECT=$4
COLLISIONS=$5
NUM_DP=$6
NEVENTS=$7
CONTAINER=$8
BIND_PATH=$9

MAIN_DIR="${WORKDIR:-/workdir}/$PROJECT"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Rivet_Main.py"

DP_PER=$NUM_DP

DP_START=$((SLURM_ARRAY_TASK_ID * DP_PER ))
DP_END=$((DP_START + DP_PER ))

start_time=$(date +%s)

read -r -a PT_EDGES <<< "$PT_EDGES_STR"

echo "DP ${SLURM_ARRAY_TASK_ID} → range [$((DP_START+1)),${DP_END}]"
echo "$PT_EDGES"


RUN_BATCH_FUNC() {
    local PT_MIN=$1
    local PT_MAX=$2
    local SEED=$3
        
    srun --exclusive -n1 -N1 bash -c "
	    unset PYTHIA8DATA

        apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
            python "$MAIN_SCRIPT" "$DP_START" "$DP_END" \
            --main_dir "$MAIN_DIR" \
            --input_cleaned_dir "$INPUT_DIR" \
            --Run_MAP True \
            --clear_rivet_model False \
            --Get_Design_Points False \
            --Rivet_Setup False \
            --model_seed "$SEED" \
            --nevents "$NEVENTS" \
            --Run_Model True \
            --Run_Batch True \
            --PT_Min "$PT_MIN"\
            --PT_Max "$PT_MAX"\
            --Rivet_Merge False \
            --Write_input_Rivet False \
            --Coll_System ${COLLISIONS}
    "
}

if [ "$DO_PT_HAT_BINS" = true ]; then
    for ((k=0; k<${#PT_EDGES[@]}-1; k++)); do
        SEED=$(( SLURM_JOB_ID*100 + SLURM_ARRAY_TASK_ID*10 + k))
        MIN=${PT_EDGES[k]}
        MAX=${PT_EDGES[k+1]}
        echo "🧱 Bin ${MIN}-${MAX}"
        RUN_BATCH_FUNC "$MIN" "$MAX" "$SEED" &
    done
    k=${#PT_EDGES[@]}-1
    SEED=$(( SLURM_JOB_ID*100 + SLURM_ARRAY_TASK_ID*10 + k))
    LAST_MIN=${PT_EDGES[-1]}
    echo "🧱 Bin > ${LAST_MIN}"
    RUN_BATCH_FUNC "$LAST_MIN" -1 "$SEED" &
    wait
else
    for j in {0..6}; do
        SEED=$(( SLURM_JOB_ID*100 + SLURM_ARRAY_TASK_ID*10 + j ))
        RUN_BATCH_FUNC -1 -1 "$SEED" &
    done
    wait
fi

end_time=$(date +%s)
runtime=$((end_time - start_time))
echo "⏱️ Total runtime: ${runtime} seconds ($(printf '%02d:%02d:%02d\n' $((runtime/3600)) $((runtime%3600/60)) $((runtime%60))))"