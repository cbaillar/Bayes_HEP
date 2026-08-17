#!/bin/bash

# ─────────────────────────────────────────────
# Arguments
# ─────────────────────────────────────────────
ANALYSES=$1
INPUT_DIR=$2
PROJECT_DIR=$3
COLLISION=$4
ECM=$5
NEVENTS=$6
SEED=$7
PARAM_TAG=$8
MERGE_TAG=$9
PT_MIN=${10}
PT_MAX=${11}

# ─────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────
MODEL=pythia8
TUNE=14  # 14 = Monash 2013
PYPATH=/usr/local/share/Pythia8/examples

OUTPUT=${MODEL}_${COLLISION}_${ECM}_s${SEED}_n${NEVENTS}
TEMP=${PROJECT_DIR}/Models/${MODEL}/Runs/${OUTPUT}_${MERGE_TAG}
MERGE_DIR=${PROJECT_DIR}/Models/${MODEL}/YODA/${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}

mkdir -p "$TEMP" "$MERGE_DIR"
cd "$TEMP" || exit 1

# ─────────────────────────────────────────────
# Copy config files
# ─────────────────────────────────────────────
cp ${PYPATH}/main144.cmnd .
cp ${PYPATH}/main144Rivet.cmnd .
cp ${INPUT_DIR}/parameter.cmnd .

# ─────────────────────────────────────────────
# Update main144.cmnd — set beam energy
# ─────────────────────────────────────────────
ECM_FORMATTED=$(printf "%-24s" "${ECM}.")
sed -i \
    -e "s/^\(Beams:eCM = \).*\( *! CM energy.*\)$/\1${ECM_FORMATTED}\2/" \
    main144.cmnd

# ─────────────────────────────────────────────
# Update parameter.cmnd
# ─────────────────────────────────────────────

# 1) Parse PARAM_TAG — extract values between underscores
IFS='_' read -r -a ARR <<< "$PARAM_TAG"
VALUES=()
for ((i=1; i<${#ARR[@]}; i+=2)); do
    VALUES+=("${ARR[i]}")
done

# 2) Inject pTHat cuts if specified
if [[ "$PT_MIN" != "-1" && "$PT_MAX" != "-1" ]]; then
    sed -i "/^! *These are fixed/a\\
PhaseSpace:pTHatMin = ${PT_MIN}.\\
PhaseSpace:pTHatMax = ${PT_MAX}." parameter.cmnd
elif [[ "$PT_MIN" != "-1" ]]; then
    sed -i "/^! *These are fixed/a PhaseSpace:pTHatMin = ${PT_MIN}." parameter.cmnd
elif [[ "$PT_MAX" != "-1" ]]; then
    sed -i "/^! *These are fixed/a PhaseSpace:pTHatMax = ${PT_MAX}." parameter.cmnd
fi

# 3) Overwrite tuning parameters after marker line
val_idx=0
tmpfile=$(mktemp)
overwrite_mode=false

while IFS= read -r line || [[ -n $line ]]; do
    trimmed_line=$(echo "$line" | xargs)

    if [[ "$trimmed_line" == "! These are tuning parameters" ]]; then
        overwrite_mode=true
        echo "$line" >> "$tmpfile"
        continue
    fi

    if $overwrite_mode && [[ "$line" =~ ^[[:space:]]*([A-Za-z0-9_:.]+)[[:space:]]*= ]]; then
        if [[ $val_idx -lt ${#VALUES[@]} ]]; then
            key=$(echo "$line" | cut -d= -f1 | xargs)
            echo "$key = ${VALUES[$val_idx]}" >> "$tmpfile"
            ((val_idx++))
        else
            echo "$line" >> "$tmpfile"
        fi
    else
        echo "$line" >> "$tmpfile"
    fi
done < parameter.cmnd

mv "$tmpfile" parameter.cmnd

# ─────────────────────────────────────────────
# Update main144Rivet.cmnd — build analysis list
# ─────────────────────────────────────────────
IFS=',' read -ra ANALYSIS_ARR <<< "$ANALYSES"
RIVET_ANALYSIS_LIST=""

for ANALYSIS in "${ANALYSIS_ARR[@]}"; do
    ANALYSIS="$(echo "$ANALYSIS" | xargs)"  # trim whitespace

    if [ ! -d "${PROJECT_DIR}/Rivet_Analyses/${ANALYSIS}" ]; then
        echo "Analysis directory ${PROJECT_DIR}/Rivet_Analyses/${ANALYSIS} does not exist."
        exit 1
    fi

    cp "${PROJECT_DIR}/Rivet_Analyses/${ANALYSIS}/Rivet"* .
    cp "${PROJECT_DIR}/Rivet_Analyses/${ANALYSIS}/"*.yoda* .
    cp "${PROJECT_DIR}/Rivet_Analyses/${ANALYSIS}/"* ${MERGE_DIR}/.

    # Tag analysis with collision info if not pp
    if [ "$COLLISION" != "pp" ]; then
        TAGGED_ANALYSIS="${ANALYSIS}:cent=GEN:beam=${COLLISION}:ENERGY=${ECM}"
    else
        TAGGED_ANALYSIS="${ANALYSIS}"
    fi

    if [ -z "$RIVET_ANALYSIS_LIST" ]; then
        RIVET_ANALYSIS_LIST="$TAGGED_ANALYSIS"
    else
        RIVET_ANALYSIS_LIST="${RIVET_ANALYSIS_LIST},${TAGGED_ANALYSIS}"
    fi
done

# Patch or append rivet analyses line
if grep -q '^Main:rivetAnalyses' main144Rivet.cmnd; then
    sed -i "s|^Main:rivetAnalyses .*|Main:rivetAnalyses = {${RIVET_ANALYSIS_LIST}}|" main144Rivet.cmnd
else
    echo "Main:rivetAnalyses = {${RIVET_ANALYSIS_LIST}}" >> main144Rivet.cmnd
fi

# ─────────────────────────────────────────────
# Run Pythia8
# ─────────────────────────────────────────────
mkfifo ${OUTPUT}.hepmc
cat ${OUTPUT}.hepmc > /dev/null &

pythia8-main144 -c main144.cmnd -c ${PYPATH}/main144HepMC.cmnd -c main144Rivet.cmnd -c parameter.cmnd -o ${OUTPUT} -n ${NEVENTS} -s ${SEED}

pkill -f "cat ${OUTPUT}.hepmc"
rm -f ${OUTPUT}.hepmc
rm -f *.so