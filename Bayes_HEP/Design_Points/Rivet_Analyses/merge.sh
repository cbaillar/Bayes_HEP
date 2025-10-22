#!/bin/bash

PROJECT_DIR=$1
MODEL=$2
COLLISION=$3
ECM=$4
MERGE_TAG=$5
MC_WEIGHTS=$6

OUTPUT=${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}
OUTPUT_DIR=${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}

#mkdir -p ${OUTPUT_DIR}
cd ${OUTPUT_DIR}
cp ${PROJECT_DIR}/Models/${MODEL}/Runs/${MODEL}_${COLLISION}_${ECM}_*_${MERGE_TAG}/${MODEL}_*.yoda .

    rivet-merge --pwd -o ${OUTPUT_DIR}/${OUTPUT}.yoda -e ${MODEL}_*.yoda

echo "Run completed. Merged output saved to ${OUTPUT_DIR}/${OUTPUT}.yoda"
