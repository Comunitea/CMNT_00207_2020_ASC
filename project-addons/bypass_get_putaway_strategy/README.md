La función get_putaway_streegy busca en los padres una regla, pero:
- Si le fijas una ubicación, 
- La ubicación fijada es de tipo interno
- No tiene hijos

NO TIENE Sentido que el sistema me sobreescriba mi ubicación si yo se lo propongo.
Ejemplo:

Stock move de producto 1, de ajuste a ubiación 12
SI el producto tienen ubicación prefijada ubicación 15, y en stock esa reglas

Debería de ser 
Stock Move                              Stock Move Line
Origen   Destino                                            
Ajuste a Stock        >>>               Ubicación 15
Ajuste a Ubicación 12 >>>               Ubicación 12
