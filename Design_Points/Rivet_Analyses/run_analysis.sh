#!/bin/bash

ANALYSES=$1
PROJECT_DIR=$2

RIVET_ANALYSES_PATH=/workdir/Design_Points/Rivet_analyses
RIVET_PATH=/usr/local/share/Rivet

LOG_FILE="/workdir/${PROJECT_DIR}/analyses.log"
> "$LOG_FILE"

IFS=',' read -ra ANALYSIS_LIST <<< "$ANALYSES"

for ANALYSIS in "${ANALYSIS_LIST[@]}"; do
  echo "Processing analysis: $ANALYSIS"
  STATUS=""
  BUILD_STATUS=""

  if [ -f "${RIVET_ANALYSES_PATH}/${ANALYSIS}.cc" ]; then
    echo "Analysis file found for $ANALYSIS"
    cd "${RIVET_ANALYSES_PATH}/$ANALYSIS"
    STATUS="found"

  elif [ -f "${RIVET_PATH}/${ANALYSIS}.cc" ]; then
      mkdir -p "${RIVET_ANALYSES_PATH}/$ANALYSIS"
      cd "${RIVET_ANALYSES_PATH}/$ANALYSIS"
      cp ${RIVET_PATH}/${ANALYSIS}* .
      echo "Analysis file found and copied over for $ANALYSIS"
    STATUS="found"
  else
    echo "No analysis file found for $ANALYSIS"
    STATUS="not_found"
    echo "$ANALYSIS $STATUS build_failed" >> "$LOG_FILE"
    cd ..
    continue
  fi

  if [ -f "Rivet${ANALYSIS}.so" ]; then
    BUILD_STATUS="build_success"
    echo "Rivet${ANALYSIS}.so already exists, skipping build."
  else
    rivet-build Rivet${ANALYSIS}.so ${ANALYSIS}.cc
    if [ $? -eq 0 ] && [ -f "Rivet${ANALYSIS}.so" ]; then
      BUILD_STATUS="build_success"
      echo "Successfully built Rivet${ANALYSIS}.so"
    else
      BUILD_STATUS="build_failed"
      echo "$ANALYSIS failed to build Rivet${ANALYSIS}.so"
    fi
  fi

  echo "$ANALYSIS $STATUS $BUILD_STATUS" >> "$LOG_FILE"
  cd ..
done