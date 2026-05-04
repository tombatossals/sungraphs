#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BASE_DIR"

"$BASE_DIR/.venv/bin/python" generate_history.py $(date "+%Y-%m-%d")

git add -A
git commit -q -m "data: history $(date '+%Y-%m-%d')"
git push -q
