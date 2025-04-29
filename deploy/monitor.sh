#!/bin/bash
set -e

# Configuration
APP_URL="https://shen-ai.cloud/cloud_updates/health"
MAX_RETRIES=5
RETRY_DELAY=15

check_health() {
    local retry_count=0
    local success=false

    while [ $retry_count -lt $MAX_RETRIES ]; do
        response=$(curl -s -w "%{http_code}" $APP_URL)
        status_code=${response: -3}
        body=${response:0:${#response}-3}

        if [ "$status_code" = "200" ]; then
            echo "Health check passed!"
            success=true
            break
        else
            echo "Attempt $((retry_count + 1)): Health check failed with status $status_code"
            ((retry_count++))
            sleep $RETRY_DELAY
        fi
    done

    if [ "$success" = false ]; then
        echo "Health check failed after $MAX_RETRIES attempts"
        exit 1
    fi
}

# Check application logs for errors
check_logs() {
    local log_file="/var/www/vhosts/shen-ai.cloud/logs/gunicorn_error.log"
    if [ -f "$log_file" ]; then
        errors=$(tail -n 50 "$log_file" | grep -i "error")
        if [ ! -z "$errors" ]; then
            echo "Found errors in application log:"
            echo "$errors"
            exit 1
        fi
    fi
}

# Main execution
echo "Starting deployment monitoring..."
check_health
check_logs
echo "Monitoring completed successfully"