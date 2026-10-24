#!/usr/bin/env bash
# ==============================================================================
# HeatShield Bharat — Module 5 Firmware Test Runner
# Compiles and runs host C++ unit tests for firmware scaffolding.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FIRMWARE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== HeatShield Bharat: Running Module 5 Firmware Unit Tests ==="

if command -v g++ >/dev/null 2>&1; then
    echo "Found host g++ compiler. Compiling natively..."
    g++ -std=c++17 -Wall -Wextra -Werror "${SCRIPT_DIR}/test_firmware.cpp" -o "${SCRIPT_DIR}/test_runner"
    "${SCRIPT_DIR}/test_runner"
    rm -f "${SCRIPT_DIR}/test_runner"
elif command -v podman >/dev/null 2>&1; then
    echo "Host g++ not found. Using Podman container (alpine:latest) to build and run..."
    podman run --rm \
        -v "${FIRMWARE_DIR}:/workspace:Z" \
        -w /workspace \
        docker.io/library/alpine:latest \
        sh -c "apk add --no-cache g++ >/dev/null 2>&1 && g++ -std=c++17 -Wall -Wextra -Werror tests/test_firmware.cpp -o tests/test_runner && ./tests/test_runner && rm -f tests/test_runner"
elif command -v docker >/dev/null 2>&1; then
    echo "Host g++ not found. Using Docker container (alpine:latest) to build and run..."
    docker run --rm \
        -v "${FIRMWARE_DIR}:/workspace" \
        -w /workspace \
        alpine:latest \
        sh -c "apk add --no-cache g++ >/dev/null 2>&1 && g++ -std=c++17 -Wall -Wextra -Werror tests/test_firmware.cpp -o tests/test_runner && ./tests/test_runner && rm -f tests/test_runner"
else
    echo "ERROR: Neither g++, clang++, podman, nor docker found. Cannot compile host unit tests."
    exit 1
fi
