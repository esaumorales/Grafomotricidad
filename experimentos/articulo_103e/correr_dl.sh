set -e
C="$(cd "$(dirname "$0")" && pwd)"; RAIZ="$(cd "$C/../.." && pwd)"; PY="${PY:-python}"
export PYTHONIOENCODING=utf-8 PYTHONPATH="$RAIZ/src:$C"
cd "$C"
for a in resnet18 mobilenetv2 efficientnet_b0; do
  "$PY" -m grafomotor --config config.yaml entrenar-dl --arq $a > log_dl_$a.txt 2>&1; echo "$a listo"
done
"$PY" dl_corte.py > log_dl_corte.txt 2>&1; echo "corte listo"
