#!/bin/bash

PROJECT_DIR=$1
MODEL=$2
COLLISION=$3
ECM=$4
MERGE_TAG=$5

OUTPUT=${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}

rivet-merge -o ${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}.yoda ${PROJECT_DIR}/Models/${MODEL}/YODA/runs/${MODEL}_${COLLISION}_${ECM}_*_${MERGE_TAG}/*.yoda

echo "Run completed. Merged output saved to ${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}.yoda"