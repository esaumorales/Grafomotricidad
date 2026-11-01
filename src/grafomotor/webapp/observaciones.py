"""Observaciones geométricas de apoyo; no explicaciones causales del clasificador."""
import math


def observaciones(figura_id, medidas, referencia, sin_trazo=False, imagen_fiable=True):
    if not imagen_fiable:
        return [{"titulo": "Lectura automática no fiable", "detalle": "No se pueden confirmar medidas de este dibujo con el procesamiento actual. Revisa la fotografía y los criterios del manual; no se atribuye una dificultad al niño.", "revisar": True}]
    if sin_trazo:
        return [{"titulo": "Trazo no detectado", "detalle": "No se detectó suficiente trazo. Comprueba si el dibujo está en blanco o si la fotografía perdió detalle.", "revisar": True}]
    salida = []
    def numero(key):
        v = medidas.get(key)
        return float(v) if v is not None and math.isfinite(float(v)) else None
    partes, esperadas = numero('partes'), referencia.get('partes')
    if partes is not None and esperadas is not None and math.isfinite(float(esperadas)):
        diferente = partes != esperadas
        salida.append({"titulo": "Lectura del trazo", "detalle": f"El procesamiento separó la imagen en {int(partes)} componentes; en la referencia, {int(esperadas)}. Son componentes de imagen, no un conteo confirmado de líneas dibujadas. " + ("La diferencia puede deberse a ruido o interrupciones de la foto; compruébala visualmente." if diferente else "La coincidencia no confirma que se cumplan los criterios del manual."), "revisar": diferente})
    if figura_id in {'F04', 'F05', 'F06', 'F10'}:
        extremos = numero('extremos')
        if extremos is not None:
            salida.append({"titulo": "Cierre de la figura", "detalle": f"Se detectan {int(extremos)} extremos libres. " + ("Comprueba si el contorno quedó abierto o hay prolongaciones del trazo." if extremos else "No se detectan extremos libres; verifica visualmente que el contorno esté cerrado."), "revisar": extremos > 0})
    if figura_id == 'F01':
        a = numero('angulo')
        if a is not None:
            inclinacion = abs(a - 90)
            salida.append({"titulo": "Inclinación de la línea", "detalle": f"La inclinación estimada respecto a la vertical es {inclinacion:.1f}°. " + ("Supera los 45° indicados en el manual; comprueba la orientación de la foto." if inclinacion > 45 else "Está dentro del límite de 45°; aún debes comprobar que sea una sola línea recta."), "revisar": inclinacion > 45})
    if figura_id == 'F02':
        a = numero('incl_partes')
        if a is not None:
            salida.append({"titulo": "Inclinación de las líneas", "detalle": f"La mayor inclinación estimada de las partes principales es {a:.1f}° respecto a la horizontal. " + ("Supera los 45° del manual; revisa la foto y los trazos." if a > 45 else "Está dentro del límite de 45°; comprueba también que no converjan ni sean curvas."), "revisar": a > 45})
    if not salida:
        salida.append({"titulo": "Revisión visual necesaria", "detalle": "No hay medidas suficientes para describir esta figura. Utiliza los criterios del manual y comprueba la fotografía.", "revisar": True})
    return salida
