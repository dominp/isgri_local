#!/bin/bash
cd exec

for file in *.pro; do
  if [[ -f "$file" ]]; then
    filename=$(basename "$file" .pro)
    ./run.sh $filename
    # Perform your actions here
  fi
done