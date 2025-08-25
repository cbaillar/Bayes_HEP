#!/bin/bash

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

MODEL=pythia8
TUNE=14  # 14 = Monash 2013

PYPATH=/usr/local/share/Pythia8/examples

#WORK_PATH=/workdir/${PROJECT_DIR}
WORK_PATH=${PROJECT_DIR}

TUNES_PATH=/usr/local/share/Pythia8/tunes   # https://pythia.org/latest-manual/Welcome.html

OUTPUT=${MODEL}_${COLLISION}_${ECM}_s${SEED}_n${NEVENTS}
#TEMP=/workdir/${PROJECT_DIR}/Models/${MODEL}/YODA/runs/${OUTPUT}_${COLLISION}_${MERGE_TAG}
TEMP=${PROJECT_DIR}/Models/${MODEL}/Runs/${OUTPUT}_${MERGE_TAG}

mkdir -p "$TEMP"
cd "$TEMP" || exit 1

cp ${PYPATH}/main144.cmnd .
cp ${PYPATH}/main144Rivet.cmnd .
cp ${INPUT_DIR}/parameter.cmnd .


MERGE_DIR=${PROJECT_DIR}/Models/${MODEL}/YODA/${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}
mkdir -p "$MERGE_DIR"

# ── Update main144.cmnd ──────────────────────────────────

# Define nuclear IDs
declare -A NUCLEAR_IDS=(
  [p]=2212
  [Pb]=1000822080
  [Au]=1000791970
)

# Assign IDA and IDB based on collision system
case "$COLLISION" in
  pp)
    IDA=${NUCLEAR_IDS[p]};  IDB=${NUCLEAR_IDS[p]}
    BEAMTAG="PP${ECM%.*}"
    ;;
  pPb)
    IDA=${NUCLEAR_IDS[p]};  IDB=${NUCLEAR_IDS[Pb]}
    BEAMTAG="PPB${ECM%.*}"
    ;;
  Pbp)
    IDA=${NUCLEAR_IDS[Pb]}; IDB=${NUCLEAR_IDS[p]}
    BEAMTAG="PBP${ECM%.*}"
    ;;
  PbPb)
    IDA=${NUCLEAR_IDS[Pb]}; IDB=${NUCLEAR_IDS[Pb]}
    BEAMTAG="PBPB${ECM%.*}"
    ;;
  pAu)
    IDA=${NUCLEAR_IDS[p]};  IDB=${NUCLEAR_IDS[Au]}
    BEAMTAG="PAU${ECM%.*}"
    ;;
  Aup)
    IDA=${NUCLEAR_IDS[Au]}; IDB=${NUCLEAR_IDS[p]}
    BEAMTAG="AUP${ECM%.*}"
    ;;
  AuAu)
    IDA=${NUCLEAR_IDS[Au]}; IDB=${NUCLEAR_IDS[Au]}
    BEAMTAG="AUAU${ECM%.*}"
    ;;
  *)
    echo "Unsupported collision system: $COLLISION"
    exit 1
    ;;
esac

sed -i \
      -e "s/^\(Beams:idA *= *\).*\(!.*\)/\1${IDA}                        \2/" \
      -e "s/^\(Beams:idB *= *\).*\(!.*\)/\1${IDB}                        \2/" \
      -e "s/^\(Beams:eCM *= *\).*\(!.*\)/\1${ECM}.                        \2/" \
      main144.cmnd


# ── Update parameter.cmnd ──────────────────────────────────
# 1) Parse PARAM_TAG, just collect the values
IFS='_' read -r -a ARR <<< "$PARAM_TAG"
VALUES=()
for ((i=1; i<${#ARR[@]}; i+=2)); do
    VALUES+=("${ARR[i]}")
done

# 2)
# ── Inject pTHat cuts in the fixed section ─────────────
if [[ "$PT_MIN" != "-1" && "$PT_MAX" != "-1" ]]; then
  # insert both in the right order
  sed -i "/^! *These are fixed/a\\
PhaseSpace:pTHatMin = ${PT_MIN}.\\
PhaseSpace:pTHatMax = ${PT_MAX}." parameter.cmnd
else
  [[ "$PT_MIN" != "-1" ]] && sed -i "/^! *These are fixed/a PhaseSpace:pTHatMin = ${PT_MIN}." parameter.cmnd
  [[ "$PT_MAX" != "-1" ]] && sed -i "/^! *These are fixed/a PhaseSpace:pTHatMax = ${PT_MAX}." parameter.cmnd
fi
# 3) Overwrite only tuning parameters (after marker)
val_idx=0
tmpfile=$(mktemp)
overwrite_mode=false

while IFS= read -r line || [[ -n $line ]]; do
    trimmed_line=$(echo "$line" | xargs)

    # Start overwriting after this marker
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


# ── Update main144Rivet.cmnd ──────────────────────────────────
IFS=',' read -ra ANALYSIS_ARR <<< "$ANALYSES"   # split on commas into array
RIVET_ANALYSIS_LIST=""

for ANALYSIS in "${ANALYSIS_ARR[@]}"; do
    ANALYSIS="$(echo "$ANALYSIS" | xargs)"      # trim any stray whitespace

    if [ ! -d "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}" ]; then
        echo "Analysis directory ${WORK_PATH}/Rivet_Analyses/${ANALYSIS} does not exist."
        exit 1
    fi
    # Copy the plugin (assumes it’s called Rivet*.so / .cc etc.)
    #cp "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}/"* .
    cp "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}/Rivet"* .
    cp "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}/"*.yoda* .

    cp "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}/"* ${MERGE_DIR}/.

    if [ "$COLLISION" != "pp" ]; then
        TAGGED_ANALYSIS="${ANALYSIS}:cent=GEN:beam=${COLLISION}"
    else
        TAGGED_ANALYSIS="${ANALYSIS}"
    fi

    if [ -z "$RIVET_ANALYSIS_LIST" ]; then
        RIVET_ANALYSIS_LIST="$TAGGED_ANALYSIS"
    else
        RIVET_ANALYSIS_LIST="${RIVET_ANALYSIS_LIST},${TAGGED_ANALYSIS}"
    fi
done

# ── Patch main144Rivet.cmnd ──────────────────────────────────────────────
# If a line begins with Main:rivetAnalyses, replace it; otherwise append.
if grep -q '^Main:rivetAnalyses' main144Rivet.cmnd; then
    sed -i "s|^Main:rivetAnalyses .*|Main:rivetAnalyses = {${RIVET_ANALYSIS_LIST}}|" \
        main144Rivet.cmnd
else
    echo "Main:rivetAnalyses = {${RIVET_ANALYSIS_LIST}}" >> main144Rivet.cmnd
fi

mkfifo ${OUTPUT}.hepmc
cat ${OUTPUT}.hepmc > /dev/null &

pythia8-main144 -c main144.cmnd -c ${PYPATH}/main144HepMC.cmnd -c main144Rivet.cmnd -c parameter.cmnd -o ${OUTPUT} -n ${NEVENTS} -s ${SEED}

pkill -f "cat ${OUTPUT}.hepmc"
rm -f ${OUTPUT}.hepmc


rm *.so 