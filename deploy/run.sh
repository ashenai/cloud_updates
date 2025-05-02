#!/bin/bash

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Source environment variables
source "${SCRIPT_DIR}/env.sh"

# Check if a script name was provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <script-name> [args...]"
    echo "Available scripts:"
    echo "  - deploy.sh"
    echo "  - monitor.sh"
    echo "  - setup.sh"
    exit 1
fi

SCRIPT_NAME="$1"
shift  # Remove the first argument (script name)

# Check if the script exists
if [ ! -f "${SCRIPT_DIR}/${SCRIPT_NAME}" ]; then
    echo "Error: Script '${SCRIPT_NAME}' not found in ${SCRIPT_DIR}"
    exit 1
fi

# Make the script executable
chmod +x "${SCRIPT_DIR}/${SCRIPT_NAME}"

# Run the requested script with remaining arguments
exec "${SCRIPT_DIR}/${SCRIPT_NAME}" "$@"