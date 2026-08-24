# Guía paso a paso — PreservarChat 2.5 FINAL

## 1. Preparación

Trabajá únicamente con material autorizado. Prepará el dispositivo, los datos básicos del caso y una ubicación segura para el expediente.

## 2. Exportación desde WhatsApp

La exportación se realiza con la función nativa de WhatsApp. PreservarChat no inicia la exportación y no usa una API.

Conservá los archivos resultantes sin editarlos.

## 3. Datos del caso

Creá un expediente y completá los campos obligatorios.

## 4. Dispositivo

Documentá marca, modelo, sistema operativo, IMEI y versión de WhatsApp. Número de serie y estado se registran cuando correspondan.

## 5. Cuenta de WhatsApp de origen

Registrá el titular informado y el número de la cuenta desde la cual se exporta.

## 6. Conversación exportada

Completá contacto/grupo, número cuando corresponda y cargá solamente los archivos pertenecientes a esa conversación.

## 7. Material complementario

Podés agregar capturas, fotos, videos, audios y documentos PDF, Word, Excel, ODT/ODS, RTF o CSV.

Es recomendable describir brevemente cada elemento, por ejemplo:

- `Perfil del contacto exportado.`
- `Información de la cuenta de origen.`
- `Comprobante relacionado con la conversación.`
- `Video del procedimiento de exportación.`

## 8. Verificación

Ejecutá **Verificar expediente** antes de entregar. Si la aplicación informa incidencias, no cierres la entrega hasta comprender la causa.

El hash demuestra coincidencia binaria respecto de la huella registrada; no demuestra por sí mismo autenticidad, autoría ni contexto.

## 9. Actas

Revisá las actas. La aplicación permite abrir el PDF, mostrarlo en el Explorador y enviarlo a impresión.

## 10. Entrega

Generá la entrega solamente cuando el expediente esté verificado.

El ZIP final recibe su SHA-256 y el Acta Final queda como documento independiente fuera del ZIP.

## 11. Después de copiar la entrega

Cuando la evidencia sea transferida a otro soporte o equipo, podés volver a calcular el SHA-256 del ZIP y compararlo con el valor registrado.

## Prueba recomendada antes de un caso real

Con archivos ficticios:

**crear → cargar → verificar → generar entrega → cerrar → volver a abrir → verificar otra vez**.

Esto valida la compilación concreta sobre la computadora donde será usada.
