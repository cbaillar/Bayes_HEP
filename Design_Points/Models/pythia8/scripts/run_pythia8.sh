#!/bin/bash
ANALYSES=$1
PROJECT_DIR=$2
COLLISION=$3  # pp, pPb, Pbp, PbPb, pAu, Aup, AuAu
ECM=$4
NEVENTS=$5
SEED=$6
PARAM_TAG=$7
MERGE_TAG=$8  

MODEL=pythia8
SOFTQCD="on"
TUNE=14  # 14 = Monash 2013

PYPATH=/usr/local/share/Pythia8/examples
WORK_PATH=/workdir/Design_Points

TUNES_PATH=/usr/local/share/Pythia8/tunes   # https://pythia.org/latest-manual/Welcome.html

OUTPUT=${MODEL}_s${SEED}_n${NEVENTS}
TEMP=/workdir/${PROJECT_DIR}/Models/${MODEL}/YODA/runs/${OUTPUT}_${COLLISION}_${MERGE_TAG}

mkdir -p "$TEMP"
cd "$TEMP" || exit 1

cp ${PYPATH}/main144.cmnd .
cp ${PYPATH}/main144Rivet.cmnd .

# since COLLISION=pp, insert pp tune
sed -i "/^Beams:eCM.*/a Tune:pp = ${TUNE}                       ! Tune setting" main144.cmnd

# ── Bayesian overrides for pp @ 7 TeV ──────────────────────────────────
# 1) parse PARAM_TAG into P[key]=val
IFS='_' read -r -a ARR <<< "$PARAM_TAG"
declare -A P
for ((i=0; i<${#ARR[@]}; i+=2)); do
  P["${ARR[i]}"]="${ARR[i+1]}"
done

# 2) map to full Pythia knob names
declare -A K=(
  [FSRalphaS]="TimeShower:alphaSvalue"
  [ISRalphaS]="SpaceShower:alphaSvalue"
  [primordialKT]="BeamRemnants:primordialKT"
  [aLund]="StringZ:aLund"
  [bLund]="StringZ:bLund"
  [CRrange]="ColourReconnection:range"
)

# 3) rewrite main144.cmnd, inserting only the present knobs right after SoftQCD:all
tmpfile=$(mktemp)
while IFS= read -r line; do
  echo "$line" >> "$tmpfile"

  if [[ "$line" =~ ^SoftQCD:all ]]; then
    for short in pT0Ref ecmPow coreRadius coreFraction ISRalphaS FSRalphaS \
                 ISRpT0Ref FSRpTmin aLund bLund sigmaPT CRrange; do
      val="${P[$short]}"
      full="${K[$short]}"
      # only insert if we actually got a value
      if [[ -n "$val" ]]; then
        printf "%-35s = %s\n" "$full" "$val" >> "$tmpfile"
      fi
    done
  fi
done < main144.cmnd

mv "$tmpfile" main144.cmnd
# ────────────────────────────────────────────────────────────────────────

RIVET_ANALYSIS_LIST=""

for ANALYSIS in ${ANALYSES}; do

    if [ ! -d "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}" ]; then
      echo "Analysis directory ${WORK_PATH}/Rivet_Analyses/${ANALYSIS} does not exist."
      exit 1
    fi
    cp "${WORK_PATH}/Rivet_Analyses/${ANALYSIS}/Rivet"* .

    if [ !COLLISION  == "pp" ]; then
      TAGGED_ANALYSIS="${ANALYSIS}:cent=GEN:beam=${BEAMTAG}"
    else 
      TAGGED_ANALYSIS="${ANALYSIS}"
    fi
    
    if [ -z "$RIVET_ANALYSIS_LIST" ]; then
      RIVET_ANALYSIS_LIST="$TAGGED_ANALYSIS"
    else
      RIVET_ANALYSIS_LIST="${RIVET_ANALYSIS_LIST},$TAGGED_ANALYSIS"
    fi
done

sed -i "s/Main:rivetAnalyses *= *{[^}]*}/Main:rivetAnalyses = {${RIVET_ANALYSIS_LIST}}/" main144Rivet.cmnd

mkfifo ${OUTPUT}.hepmc
cat ${OUTPUT}.hepmc > /dev/null &

pythia8-main144 -c main144.cmnd -c ${PYPATH}/main144HepMC.cmnd -c main144Rivet.cmnd -o ${OUTPUT} -n ${NEVENTS} -s ${SEED}

pkill -f "cat ${OUTPUT}.hepmc"
rm -f ${OUTPUT}.hepmc

rm *.so 