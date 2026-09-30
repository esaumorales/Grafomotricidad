"""
Modelo B: aprendizaje profundo (ResNet-18 preentrenada; EfficientNet-B0 como alternativa).

  imagen.py   preprocesamiento MÍNIMO de la foto (perspectiva + recorte + 224×224, 3 canales)
  aumentos.py aumento de datos moderado (sin volteos ni rotaciones grandes)
  modelo.py   red común + 15 cabezas (una por figura)
  entrenar.py entrenamiento en dos fases (cabezas congeladas -> ajuste fino de las últimas capas)
  gradcam.py  Grad-CAM + chequeo de que la red mira el trazo y no sombras/bordes

Requiere PyTorch, timm y pytorch-grad-cam (requirements-dl.txt). `imagen.py` y
`aumentos.py` no importan torch a nivel de módulo salvo lo indispensable.
"""
