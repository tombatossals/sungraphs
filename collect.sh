#!/usr/bin/env bash

set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$BASE_DIR"

"$BASE_DIR/.venv/bin/python" collect.py
"$BASE_DIR/.venv/bin/python" generate_history.py "$(date '+%Y-%m-%d')"

git add -A
git commit -q -m "data: collect $(date '+%Y-%m-%d %H:%M')"
git push -q

cd frontend
npm run build -s 2>&1 >/dev/null
