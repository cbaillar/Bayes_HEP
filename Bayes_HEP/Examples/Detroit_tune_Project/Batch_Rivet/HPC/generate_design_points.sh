#!/bin/bash
###### THIS IS FOR BATCHING JOBS WITH SLURM ON HPC

# === Config ===
USER_DIR="/lustre/isaac24/proj/UTK0244/cbaillar"
COLLISIONS="pp_200" #"pp_7000 pp_13000"
TOTAL_POINTS=10        # Total number of design points
TOTAL_EVENTS=100    # Total number of events
NEVENTS=50          # Events per job

# === PATHS ===
MAIN_DIR="${WORKDIR:-/workdir}/Detroit_tune_Project"
MAIN_SCRIPT="$MAIN_DIR/Batch_Rivet/Rivet_Main.py"
PROJ_DIR="$USER_DIR/Bayes_HEP/New_Project"
HPC_DIR="$PROJ_DIR/Batch_Rivet/HPC"

CONTAINER="$USER_DIR/Bayes_HEP/bayes_hep.sif"
BIND_PATH="$USER_DIR/Bayes_HEP:/workdir"

# === Derived Values ===
NUM_EVENT_JOBS=$((TOTAL_EVENTS / NEVENTS))
NUM_EVENT_JOBS=$((NUM_EVENT_JOBS > 0 ? NUM_EVENT_JOBS : 1))

BATCH_SIZE=10 #this needs to match #SBATCH --ntasks-per-node=10
NUM_BATCHES=$(( (TOTAL_POINTS + BATCH_SIZE - 1) / BATCH_SIZE ))

echo "🧠 HPC Job Submission:"
echo "  - Total points: $TOTAL_POINTS"
echo "  - Events per job: $NEVENTS"
echo "  - Design points per batch: $BATCH_SIZE"
echo "  - Event batches: $NUM_EVENT_JOBS"
echo "  - Design batches: $NUM_BATCHES"
echo "  - Total jobs: $((NUM_BATCHES * NUM_EVENT_JOBS))"
echo ""

# === Generate Design Points (once) ===
apptainer exec --bind "$BIND_PATH" "$CONTAINER" \
    python "$MAIN_SCRIPT" \
        --main_dir "$MAIN_DIR" \
        --clear_rivet_model True \
        --Get_Design_Points True \
        --Rivet_Setup True \
        --Run_Model False \
        --Run_Batch False \
        --Rivet_Merge False \
        --Write_input_Rivet False \
        --Coll_System ${COLLISIONS} \
        --nsamples "$TOTAL_POINTS"

if [ $? -ne 0 ]; then
    echo "❌ Design point generation failed! NOT submitting jobs."
    exit 1
fi

# === Submit SLURM jobs ===
jobids=()
round=0
for ((j=0; j<TOTAL_EVENTS; j+=NEVENTS)); do
    ((round++))
    for ((i=0; i<TOTAL_POINTS; i+=BATCH_SIZE)); do
        start=$i
        end=$((i + BATCH_SIZE))
        [ $end -gt $TOTAL_POINTS ] && end=$TOTAL_POINTS

        echo "🔹 Submitting run job: points $start to $end (round $round)"
        jid=$(sbatch "$HPC_DIR/run_batch.slurm" "$start" "$end" "$MAIN_DIR" "$MAIN_SCRIPT" "$COLLISIONS" "$NEVENTS" "$CONTAINER" "$BIND_PATH" | awk '{print $4}')

        if [[ "$jid" =~ ^[0-9]+$ ]]; then
            jobids+=($jid)
        else
            echo "❌ sbatch failed for $start to $end (round $round): $jid"
        fi
    done
done

# === Submit Rivet_Merge stage ===
merge_dep=$(IFS=:; echo "${jobids[*]}")
echo "📦 Submitting merge jobs after: afterok:$merge_dep"

if [ -z "$merge_dep" ]; then
    echo "🚫 Merge job submission skipped: No valid dependencies."
    exit 1
fi

merge_jobids=()
for ((i=0; i<TOTAL_POINTS; i+=BATCH_SIZE)); do
    start=$i
    end=$((i + BATCH_SIZE))
    [ $end -gt $TOTAL_POINTS ] && end=$TOTAL_POINTS

    jid=$(sbatch --dependency=afterok:$merge_dep "$HPC_DIR/merge_batch.slurm" "$start" "$end" "$MAIN_DIR" "$MAIN_SCRIPT" "$COLLISIONS" "$CONTAINER" "$BIND_PATH" | awk '{print $4}')
    merge_jobids+=($jid)
done

# === Submit Write Phase ===
write_dep=$(IFS=:; echo "${merge_jobids[*]}")
echo "📄 Submitting write inputs job after: afterok:$write_dep"

sbatch --dependency=afterok:$write_dep "$HPC_DIR/write_rivet_inputs.slurm" "$MAIN_DIR" "$MAIN_SCRIPT" "$COLLISIONS" "$CONTAINER" "$BIND_PATH"