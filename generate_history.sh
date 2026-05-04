#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BASE_DIR"

DATE_ARG="${1:-today}"
DATE_STR=$(date -d "$DATE_ARG" "+%Y-%m-%d")

"$BASE_DIR/.venv/bin/python" generate_history.py "$DATE_STR"

git add -A
git commit -q -m "data: history $DATE_STR"
git push -q
