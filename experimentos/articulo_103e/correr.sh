set -e
C="$(cd "$(dirname "$0")" && pwd)"; RAIZ="$(cd "$C/../.." && pwd)"; PY="${PY:-python}"
export PYTHONIOENCODING=utf-8 PYTHONPATH="$RAIZ/src:$C"
cd "$C"
"$PY" -m grafomotor --config config.yaml preparar-reales > log_preparar.txt 2>&1; echo "1 preparar listo"
"$PY" exp_criterios.py > log_ml.txt 2>&1; echo "2 ML listo"
