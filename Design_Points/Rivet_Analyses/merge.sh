#!/bin/bash

# Check for required arguments
if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <ModelType> <PROJECT_DIR> <CollisionSystem> <ECM> <ParamTag>"
    exit 1
fi

PROJECT_DIR=$1
MODEL=$2
COLLISION=$3
ECM=$4
MERGE_TAG=$5

OUTPUT=${MODEL}_${COLLISION}_${ECM}_${MERGE_TAG}

# Merge .yoda files that match the model
rivet-merge -o ${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}.yoda ${PROJECT_DIR}/Models/${MODEL}/YODA/runs/${MODEL}_*_${MERGE_TAG}/*.yoda

echo "Run completed. Merged output saved to ${PROJECT_DIR}/Models/${MODEL}/YODA/${OUTPUT}.yoda"