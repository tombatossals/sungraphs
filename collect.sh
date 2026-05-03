#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BASE_DIR"

"$BASE_DIR/.venv/bin/python" collect.py

git add -A
git commit -q -m "up"
git push -q
