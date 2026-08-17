#!/bin/bash
#SBATCH -J merge
#SBATCH -A ISAAC-UTK0244

INPUT_DIR=$1
TYPE=$2
PROJECT=$3
COLLISIONS=$4
NUM_DP=$5
EQUIV=$6
CONTAINER=$7
BIND_PATH=$8

MAIN_DIR="${WORKDIR:-/workdir}/$PROJECT"
MAIN_SCRIPT="$MAIN_DIR/Batch_Jobs/Rivet_Main.py"

if (( NUM_DP > 12 )); then
    DP_PER=$(( NUM_DP / 12 ))
else
    DP_PER=1
fi

DP_START=$((SLURM_ARRAY_TASK_ID * DP_PER ))
DP_END=$((DP_START + DP_PER ))


if [ "$TYPE" = "merge" ]; then

    if [ "$EQUIV" = "True" ]; then
        echo "true"

        srun --exclusive -n1 -N1 bash -c "
	        unset PYTHIA8DATA

            apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
                python "$MAIN_SCRIPT" "$DP_START" "$DP_END" \
                --main_dir "$MAIN_DIR" \
                --input_dir "$INPUT_DIR" \
                --Rivet_Merge True \
                --equiv_on True \
                --Coll_System ${COLLISIONS}
        "
    else
        srun --exclusive -n1 -N1 bash -c "
	            unset PYTHIA8DATA

                apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
                    python "$MAIN_SCRIPT" "$DP_START" "$DP_END" \
                    --main_dir "$MAIN_DIR" \
                    --input_dir "$INPUT_DIR" \
                    --Rivet_Merge True \
                    --Coll_System ${COLLISIONS}
            "
    fi
else
    srun --exclusive -n1 -N1 bash -c "
	    unset PYTHIA8DATA

        apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
            python "$MAIN_SCRIPT" "$DP_START" "$DP_END" \
            --main_dir "$MAIN_DIR" \
            --input_dir "$INPUT_DIR" \
            --Write_input_Rivet True \
            --Coll_System ${COLLISIONS}
    "
fi   