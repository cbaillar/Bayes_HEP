#!/bin/bash

PROJECT_DIR=$1
MODEL=$2
COLLISION=$3
ECM=$4
PARAM_TAG=$5

INPUT=${MODEL}_${COLLISION}_${ECM}_${PARAM_TAG}
INPUT_DIR=${PROJECT_DIR}/Models/${MODEL}/YODA/${INPUT}

cd ${INPUT_DIR}

rivet-mkhtml --pwd "${INPUT}.yoda:${MODEL}" \
             --output "${PROJECT_DIR}/Models/${MODEL}/html_reports/${INPUT}_report.html" 

echo "HTML reports generated for analyses: ${COLLISION}_${ECM}"