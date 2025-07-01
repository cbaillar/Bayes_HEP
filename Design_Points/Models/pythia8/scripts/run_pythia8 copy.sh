#!/bin/bash

###Used for testing did not change any parameters

#Can be used as base script


#ANALYSES="ATLAS_2010_I882098 ALICE_2022_I2088201 STAR_2016_I1414638"
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



if [ !COLLISION  == "pp" ]; then
    sed -i \
      -e "s/^\(Beams:idA *= *\).*\(!.*\)/\1${IDA}                        \2/" \
      -e "s/^\(Beams:idB *= *\).*\(!.*\)/\1${IDB}                        \2/" \
      -e "s/^\(Beams:eCM *= *\).*\(!.*\)/\1${ECM}.                        \2/" \
      -e "s/^\(SoftQCD:all *= *\).*\(!.*\)/\1${SOFTQCD}                        \2/" \
      main144.cmnd
else  
    sed -i "/^Beams:eCM.*/a Tune:pp = ${TUNE}                       ! Tune setting" main144.cmnd
fi

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