#!/bin/bash

NAME=$1

# Define the IDL batch file
IDL_BATCH_FILE="${NAME}.pro"

# Log file for IDL output
LOG_FILE="../log/${NAME}.log"

# Source the .bashrc to get environment variables and functions
source ~/.bashrc

# Call the idlinit function to set up the IDL environment
idlinit

# Check if IDL is available by using the full path
IDL_EXEC="/lnx/swsrv/idl/idl/bin/idl"

if [ ! -f "$IDL_EXEC" ]; then
  echo "IDL executable not found at $IDL_EXEC. Please check your installation."
  exit 1
fi

# Run the IDL script in the background using nohup and redirect output to a log file
nohup "$IDL_EXEC" -e "@${IDL_BATCH_FILE}" > "$LOG_FILE" 2>&1 &

# Get the Process ID of the last background process
PID=$!

# Disown the process to make it immune to hangups
disown $PID

# Output the PID for reference
echo "IDL script ${IDL_BATCH_FILE} is running in the background with PID: $PID"