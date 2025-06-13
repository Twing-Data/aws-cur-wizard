#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"

show_help() {
cat <<'EOHELP'
AWS-CUR → Rill one-click runner
===============================

Usage  
  ./run.sh [OPTIONS]

Steps performed
  1.   Normalise raw CUR files found in \$INPUT_DATA_DIR
  2.   Generate metrics / explore / *one canvas per tag-prefix*
  3.   Launch Rill against the output project

Required environment variables ( via .env or export )  
  INPUT_DATA_DIR         Path containing raw CUR CSV or parquet files  
  NORMALIZED_DATA_DIR    Where the normalised parquet will be written  
  RILL_PROJECT_PATH      Rill project root folder

Optional environment variables  
  DIM_PREFIXES           Comma list of dimension prefixes for canvases
  COST_COL               Default spend measure (overrides interactive picker)

Common OPTIONS (forwarded to generate_rill_yaml.py)  
  --cost-col COL         Spend metric column to use for all dashboards  
  --dim-prefixes LIST    Comma-separated prefixes, e.g. "resource_tags_,product_"  
  --list-cost-columns    Only show the detected numeric \$ columns and exit  
  -h, --help             Show this help and exit

Anything not recognised by run.sh is passed straight through to the
Python generator, so you can use *all* of its flags.

Examples
  ./run.sh                              # relies on defaultcost_col 
  ./run.sh --cost-col line_item_blended_cost
  DIM_PREFIXES="resource_tags_,product_" ./run.sh
EOHELP
}

if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
  show_help
  exit 0
fi

if [[ -f "$HERE/.env" ]]; then
  set -a

  . "$HERE/.env"
  set +a
else
  echo "⚠️  No .env file found at $HERE/.env; ensure INPUT_DATA_DIR, NORMALIZED_DATA_DIR and RILL_PROJECT_PATH are exported."
fi

: "${INPUT_DATA_DIR:?Need to set INPUT_DATA_DIR}"
: "${NORMALIZED_DATA_DIR:?Need to set NORMALIZED_DATA_DIR}"
: "${RILL_PROJECT_PATH:?Need to set RILL_PROJECT_PATH}"


GEN_FLAGS=("$@")          

echo "▶ Normalizing CUR files from INPUT_DATA_DIR: $INPUT_DATA_DIR"
python "$HERE/scripts/normalize.py"

echo "▶ Generating Rill YAML (using RILL_PROJECT_PATH: $RILL_PROJECT_PATH)"
python "$HERE/scripts/generate_rill_yaml.py" \
       --parquet     "$NORMALIZED_DATA_DIR/normalized.parquet" \
       --output-dir  "$RILL_PROJECT_PATH" \
       "${GEN_FLAGS[@]}"

for arg in "$@"; do
  if [[ "$arg" == "--list-cost-columns" ]]; then
    exit 0
  fi
done

echo "▶ Launching Rill from project path: $RILL_PROJECT_PATH"
cd "$RILL_PROJECT_PATH"
rill start --reset

