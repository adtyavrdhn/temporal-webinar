#!/usr/bin/env bash
# Prepare the spike's environment: Python 3.12 venv with the pinned deps from spike/uv.lock.
set -euo pipefail
cd "$(dirname "$0")/../spike"
uv sync --frozen
