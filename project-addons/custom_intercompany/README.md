* Marcar todas la ubicaciones de existencias como ubicaciones de devolución.
* Crear una ubicación vista "Stock global" y colgar todas las ubicaciones de existencias de esta.
* Definir la ubicación creada en el anterior punto como la view_location_id de todos los almacenes.
* Cambiar las rutas de entrega de todos los almacenes poniendo como ubicación origen "Stock global"
* Los quants y ubicaciones tendrán una regla de permisos 1 = 1

* Cambios de funcionamiento
* Como las ubicaciones son compartidas debemos identificarlas según el alamcen/compañia a la que pertenecen
* La ubicación de stock de los almacenes deberá ser el stock del almacen de dismac
* Cálculo de precio intercompañia simplificado: Buscar ic_price_subtotal
* En la compañia, IC fields:
    - IC Purchase Journal
    - IC Pricelist (% de incremente/decremento) sobre el precio de venta al cliente
    - IC. Sale Type. Tipo de venta intercompñia, de donde se cogerán los valores por defecto para la factura de venta.
    - OJO con no cruzar compañias


    


* POS
* Hay un pequeño desarrollo para conseguir priorizar una ubicación sobre las otras y saltarse el orden devuelto por el gather quants.
    - Para ello: 
        - El TPV debe de apuntar a una ubicación. En este caso Global Stock o Stock Dismac. Es donde busca el TPV las exsitencias.
        - El tipo de albarán asignado al TPV deberá de tener una ubicación por defecto que será la que se priorice a  la hora de reordenar los quants devueltos por el gather