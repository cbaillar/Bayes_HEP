#!/bin/bash

PROJECT_DIR=$1
MODEL=$2
COLLISION=$3
ECM=$4
MERGE_TAG=$5
EQUIV_ON=$6

OUTPUT=${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}
OUTPUT_DIR=${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}

cd ${OUTPUT_DIR}
cp ${PROJECT_DIR}/Models/${MODEL}/Runs/${MODEL}_${COLLISION}_${ECM}_*_${MERGE_TAG}/${MODEL}_*.yoda .

if [ "${EQUIV_ON}" = "True" ]; then
    rivet-merge --pwd -o ${OUTPUT_DIR}/${OUTPUT}.yoda -e ${MODEL}_*.yoda
else
    rivet-merge --pwd -o ${OUTPUT_DIR}/${OUTPUT}.yoda ${MODEL}_*.yoda
fi

echo "Run completed. Merged output saved to ${OUTPUT_DIR}/${OUTPUT}.yoda"
