# PreservarChat 2.5 FINAL
![PreservarChat 2.5.0](preservarchat-banner.png)

# PreservarChat 2.5 FINAL

PreservarChat es una herramienta de escritorio para Windows desarrollada para organizar, preservar, documentar y verificar la integridad de conversaciones previamente exportadas desde WhatsApp.

Su objetivo es transformar una exportación común de WhatsApp —junto con la información del dispositivo, la cuenta de origen y el material documental complementario— en un expediente digital estructurado, verificable y documentado.

## Descargar

[![Windows x64](https://img.shields.io/badge/DescARGAR-Windows%20x64-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/eelciberseguridad/PreservarChat/releases/download/v2.5.0/PreservarChat_SOLO_x64.exe)

[![Windows x86](https://img.shields.io/badge/DESCARGAR-Windows%20x86-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/eelciberseguridad/PreservarChat/releases/download/v2.5.0/PreservarChat_SOLO_x86.exe)

## ¿Qué hace PreservarChat?

En PreservarChat se adjuntan los archivos obtenidos mediante la función nativa **“Exportar chat” de WhatsApp** y crea una copia de trabajo dentro de un expediente organizado, evitando utilizar los archivos recibidos como área habitual de trabajo.

Durante el procedimiento permite registrar los datos relevantes del caso, identificar el dispositivo utilizado, documentar la cuenta de WhatsApp de origen e individualizar el contacto o grupo cuya conversación fue exportada.

Los archivos incorporados son identificados y sometidos a funciones hash criptográficas, permitiendo disponer de valores de referencia para comprobar posteriormente si su contenido digital permanece sin modificaciones.

## Preservación e integridad

PreservarChat incorpora:

- Creación y administración de expedientes locales.
- Individualización del caso.
- Registro del dispositivo utilizado.
- Identificación de la cuenta de WhatsApp de origen.
- Identificación del contacto o grupo exportado.
- Detección del período temporal de la conversación cuando puede obtenerse del contenido.
- Preservación de los archivos recibidos y generación de copias de trabajo.
- Cálculo de valores **SHA-256 y SHA-512**.
- Verificación posterior de integridad mediante hashes.
- Registro de actividad del expediente.
- Consulta organizada del chat preservado.
- Acceso al contenido multimedia asociado.
- Detección de archivos duplicados.
- Generación de manifiestos y documentación del procedimiento.

## Registro documental complementario

Además de la conversación exportada, el usuario puede incorporar material relacionado con el procedimiento, como fotografías, capturas de pantalla, videos, audios y documentos.

Cada elemento puede ser individualizado mediante una descripción y queda asociado al expediente con sus correspondientes valores de integridad.

Esto permite conservar, por ejemplo, documentación relativa al dispositivo, identificación visual de una cuenta o perfil, capturas relevantes y otros elementos que ayuden a contextualizar la exportación realizada.

## Documentación automática

A partir de la información efectivamente incorporada, PreservarChat genera documentación en PDF destinada a dejar constancia del procedimiento realizado.

El sistema puede generar actas de preservación e integridad, documentación del registro complementario, manifiestos y un **Acta Final de Entrega** que resume de manera ordenada:

**Dispositivo auditado → conversación exportada → archivos preservados → hashes → material complementario → archivos finales generados.**

El Acta Final se genera separadamente del contenedor de entrega para facilitar su consulta, impresión o eventual firma mediante el mecanismo que corresponda.

## Entrega organizada

Al finalizar, PreservarChat construye una entrega estructurada que reúne los archivos preservados y su información de integridad.

Los contenedores generados reciben sus propios valores SHA-256, permitiendo verificar posteriormente que el material entregado coincide con el documentado al momento de su generación.

El expediente permanece disponible dentro de la aplicación para su consulta y verificación posterior.

## Qué NO hace PreservarChat

PreservarChat **no se conecta a WhatsApp**, no accede a sus servidores, no utiliza la API de WhatsApp y no extrae información directamente de un teléfono.

La conversación debe haber sido obtenida previamente mediante la función nativa **“Exportar chat”** disponible en WhatsApp.

PreservarChat tampoco realiza adquisición física o lógica del dispositivo, recuperación de información eliminada, análisis de memoria, extracción de bases de datos internas ni otras operaciones propias de herramientas especializadas de informática forense.

> **PreservarChat es una herramienta de apoyo para preservación documental, organización, hashing, verificación y trazabilidad de material previamente exportado. No sustituye una adquisición ni una pericia informática forense cuando estas resulten necesarias.**

## Filosofía del proyecto

Una conversación exportada no debería convertirse simplemente en otro archivo guardado dentro de una carpeta.

PreservarChat busca que desde el momento de su recepción pueda quedar **identificada, organizada, preservada, documentada y posteriormente verificable**.

---

**Creado por EEL CIBERSEGURIDAD – Eduardo Lecce**
