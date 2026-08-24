# Seguridad

PreservarChat fue diseñado para reducir errores de manipulación y documentar la preservación de archivos exportados, pero no debe interpretarse como un sistema infalible ni como almacenamiento inmutable.

## Controles implementados

- Cálculo de hashes SHA-256 y SHA-512.
- Separación entre material incorporado y copias de trabajo.
- Manifiesto del expediente y comprobaciones de integridad.
- Bitácora encadenada para detectar alteraciones.
- Verificación antes de generar la entrega.
- Controles frente a rutas peligrosas dentro de archivos ZIP.
- Límites defensivos al procesar ZIP para reducir riesgos de extracción abusiva.
- Control de duplicados mediante huella criptográfica en las áreas implementadas.
- Confirmaciones antes de operaciones destructivas.
- Restricción de borrado de expedientes al directorio administrado por la aplicación.

## Límites

El atributo de solo lectura de Windows y la bitácora reducen cambios accidentales y permiten detectar modificaciones, pero no convierten el almacenamiento local en WORM. Un usuario con privilegios administrativos y control completo del equipo podría modificar archivos y estructuras internas.

La aplicación tampoco determina por sí sola la autenticidad de una conversación, la identidad real de un interlocutor, si un dispositivo fue comprometido ni si existió información que no quedó incluida en la exportación.

## Reporte de vulnerabilidades

No publiques datos reales de expedientes, conversaciones, números de teléfono, documentos ni evidencias en un issue público.
