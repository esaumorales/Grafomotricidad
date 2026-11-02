"""Ayudas de lectura por figura, sin atribuir causas al clasificador."""
import math

GUIAS = {
 'F01': ('Forma de la línea', 'Mira si hay una sola línea de arriba hacia abajo, sin cortes, curvas ni esquinas.'),
 'F02': ('Las dos líneas', 'Mira si hay dos líneas de lado a lado. No deben juntarse ni formar curvas.'),
 'F03': ('El cruce', 'Mira si las dos líneas se cruzan y llegan al punto de encuentro sin quedar separadas.'),
 'F04': ('Forma del círculo', 'Recorre el borde: debe estar cerrado, sin lados rectos ni esquinas. Puede ser ovalado.'),
 'F05': ('Forma del cuadrado', 'Busca cuatro lados y cuatro esquinas parecidas a las del modelo. Los lados no necesitan medir lo mismo.'),
 'F06': ('Forma del triángulo', 'Busca tres lados y tres puntas. Revisa que los lados no sean ondulados.'),
 'F07': ('El aspa', 'Mira si dos líneas forman una X y se cruzan por dentro, no por sus extremos.'),
 'F08': ('Las ondas', 'Sigue la línea: debe ser continua y tener las dos ondas del modelo, sin ondas adicionales.'),
 'F09': ('El rectángulo y su cruce', 'Comprueba que el contorno esté cerrado y que las dos líneas de dentro se crucen. Al menos dos deben llegar a las esquinas.'),
 'F10': ('Forma del rombo', 'Busca cuatro lados, el contorno cerrado y una punta abajo. Los lados no necesitan medir lo mismo.'),
 'F11': ('El círculo y el triángulo', 'El círculo debe estar arriba y el triángulo abajo. Deben tocarse, sin cruzarse.'),
 'F12': ('La curva y la recta', 'Mira si hay una línea recta y una curva que se tocan en un punto, sin quedar una encima de la otra.'),
 'F13': ('Las dos curvas', 'Las dos curvas deben tocarse por el centro, por su lado abultado, sin quedar una encima de la otra.'),
 'F14': ('Las rectas y las ondas', 'Busca dos rectas que se juntan arriba y una curva de tres ondas que cruza ambas rectas.'),
 'F15': ('El cuadrado y el círculo', 'El cuadrado va arriba y el círculo abajo a la derecha. Deben cruzarse en dos puntos; solo una esquina del cuadrado queda dentro del círculo.'),
}

def observaciones(figura_id, medidas, referencia, sin_trazo=False, imagen_fiable=True):
    if not imagen_fiable:
        return [{'titulo':'Sin detalle automático de la forma', 'detalle':'No se pudieron obtener medidas adicionales fiables. Esto no cambia el resultado del modelo ni indica que el dibujo esté mal.', 'revisar':False, 'fuente':'limitacion'}]
    if sin_trazo:
        return [{'titulo':'Comprueba la foto', 'detalle':'El sistema no distingue el dibujo. Mira si la casilla está vacía o si el lápiz se ve demasiado claro en la foto.', 'revisar':True, 'fuente':'medicion'}]
    salida=[]
    def numero(key):
        value=medidas.get(key)
        return float(value) if value is not None and math.isfinite(float(value)) else None
    if figura_id in {'F01','F02'}:
        value=numero('angulo' if figura_id=='F01' else 'incl_partes')
        if value is not None:
            angle=abs(value-90) if figura_id=='F01' else value
            excede=angle>45
            salida.append({'titulo':'La inclinación supera lo permitido' if excede else 'La inclinación está dentro de lo permitido',
                'detalle':'Antes de valorar el dibujo, comprueba que la foto no esté girada.' if excede else 'Según la medida automática, no está demasiado inclinada para este criterio del manual.',
                'detalle_tecnico':f'Estimación: {angle:.1f}° respecto a la '+('vertical' if figura_id=='F01' else 'horizontal')+'. Límite del manual: 45°.',
                'revisar':excede,'fuente':'medicion'})
    if figura_id in GUIAS:
        titulo,detalle=GUIAS[figura_id]
        salida.append({'titulo':titulo,'detalle':detalle,'revisar':False,'fuente':'guia'})
    if not salida:
        salida.append({'titulo':'Necesita tu revisión','detalle':'Compara el dibujo con el modelo y consulta los criterios del manual.','revisar':True,'fuente':'guia'})
    return salida
