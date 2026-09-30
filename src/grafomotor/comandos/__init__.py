"""
Un módulo por paso de la cadena (ver `grafomotor/cli.py`).

Los comandos solo ORQUESTAN: leen artefactos, llaman a la lógica de los paquetes
(`preprocessing`, `features`, `model`, `dl`, `evaluation`, ...) y escriben resultados
con los nombres de `grafomotor.artefactos`. La lógica reutilizable no va aquí.
"""
