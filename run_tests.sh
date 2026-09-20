#!/usr/bin/env bash

set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_command="${PYTHON:-${project_root}/.venv/bin/python}"

if [[ ! -x "${python_command}" ]]; then
    python_command="${PYTHON_BIN:-python3}"
fi

cd "${project_root}"
exec "${python_command}" -m unittest discover --verbose
