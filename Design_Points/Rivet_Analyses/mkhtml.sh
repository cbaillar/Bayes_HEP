#!/bin/bash

ANALYSES=$1
PROJECT_DIR=$2
MODEL=$3
COLLISION=$4
ECM=$5
PARAM_TAG=$6

INPUT=${MODEL}_${COLLISION}_${ECM}_${PARAM_TAG}

for ANALYSIS in ${ANALYSES}; do
    rivet-mkhtml ${PROJECT_DIR}/Models/${MODEL}/YODA/${INPUT}.yoda:${MODEL} \
                 --output ${PROJECT_DIR}/Models/${MODEL}/html_reports/${INPUT}_${ANALYSIS}_report.html \
                 --title "${ANALYSIS} Analysis Report for ${INPUT}" 
done

echo "HTML reports generated for analyses: ${ANALYSES}"