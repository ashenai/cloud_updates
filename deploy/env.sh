#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    set -a
    source .env
    set +a
fi

# Default values for required variables
export APP_BASE_DIR="${APP_BASE_DIR:-/var/www/vhosts/shen-ai.cloud}"
export DOMAIN_NAME="${DOMAIN_NAME:-shen-ai.cloud}"
export APP_USER="${APP_USER:-ashenai}"
export APP_GROUP="${APP_GROUP:-psacln}"

# Required secrets - will fail if not set
: "${ADMIN_EMAIL:?ADMIN_EMAIL is required}"
: "${REPO_FULL_NAME:?REPO_FULL_NAME is required}"
: "${SSL_CERT_PATH:?SSL_CERT_PATH is required}"
: "${SSL_KEY_PATH:?SSL_KEY_PATH is required}"