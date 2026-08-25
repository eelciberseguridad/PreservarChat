# PreservarChat 2.5.0
![PreservarChat 2.5.0](preservarchat-banner.png)

# 🛡️ PreservarChat 2.5

**PreservarChat** es una herramienta de escritorio para Windows desarrollada para organizar, preservar, documentar y verificar la integridad de conversaciones previamente exportadas desde WhatsApp.

## ⬇️ Descargar PreservarChat

[![Windows x64](https://img.shields.io/badge/DESCARGAR-WINDOWS%20x64-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/eelciberseguridad/PreservarChat/releases/download/v2.5.0/PreservarChat_SOLO_x64.exe)
[![Windows x86](https://img.shields.io/badge/DESCARGAR-WINDOWS%20x86-0078D4?style=for-the-badge&logo=windows&logoColor=white)](https://github.com/eelciberseguridad/PreservarChat/releases/download/v2.5.0/PreservarChat_SOLO_x86.exe)

> 🔐 Los ejecutables oficiales se publican junto con sus valores SHA-256 para permitir la verificación de integridad.

---

## 💬 De la exportación a la preservación

El programa trabaja con los archivos obtenidos mediante la función nativa **“Exportar chat” de WhatsApp**.

PreservarChat **no se conecta a WhatsApp, no utiliza su API, no accede a sus servidores y tampoco extrae información directamente del teléfono**.

Una vez cargados los archivosde la exportación, permite crear un expediente e incorporar información destinada a contextualizar el material: **nombre del caso, dispositivo utilizado, sistema operativo, versión de WhatsApp, cuenta de origen y datos del contacto o grupo cuya conversación fue exportada**, entre otros datos relevantes.

## 🔐 Preservación e integridad

Los archivos recibidos son individualizados y preservados dentro de una estructura organizada.

El programa genera copias de trabajo para evitar utilizar innecesariamente el material recibido durante las tareas posteriores y calcula valores criptográficos **SHA-256 y SHA-512**, que pueden utilizarse para comprobar posteriormente su integridad.

De esta manera, no se conserva solamente una conversación: se conserva también información que permite establecer **qué archivos fueron recibidos, a qué expediente fueron asociados y cuáles eran sus valores hash en el momento de su incorporación**.

## 📎 Material complementario

PreservarChat incorpora además un área de **Registro Visual y Documental Complementario**.

Allí pueden agregarse fotografías, capturas de pantalla, videos, audios, archivos PDF, documentos Word, planillas Excel y otros archivos relacionados con el procedimiento.

Cada elemento puede ser **individualizado, descripto y asociado al expediente**, junto con su correspondiente información de integridad.

El sistema incorpora además controles destinados a evitar la incorporación accidental de archivos duplicados.

## 📑 Documentación automática

Uno de los objetivos centrales de PreservarChat es que el procedimiento **no termine simplemente con una carpeta llena de archivos**.

A partir de la información efectivamente incorporada, genera **actas, manifiestos y documentación en PDF** que permiten describir de manera ordenada el procedimiento realizado.

**📱 Dispositivo → 💬 Conversación → 📂 Archivos → 🔐 Hashes → 📎 Material complementario → 📦 Entrega**

El **Acta Final de Entrega se genera por separado**, fuera del archivo que contiene el material, facilitando su consulta, impresión, presentación o eventual firma.

## 🔎 Verificación posterior

Si un archivo cambia, aunque sea mínimamente, su valor hash también cambia.

Los valores registrados permiten comparar posteriormente el material y determinar si el archivo sometido a verificación **coincide con aquel que fue documentado originalmente**.

PreservarChat mantiene además información sobre las operaciones realizadas dentro del expediente para mejorar la trazabilidad del procedimiento.

## 📦 Entrega organizada

Al finalizar, PreservarChat construye una **entrega estructurada** con el material preservado y su información de integridad.

Los contenedores generados reciben también valores **SHA-256**, permitiendo comprobar posteriormente que el material entregado coincide con el documentado al momento de su generación.

## 🪟 Seguridad y distribución

PreservarChat funciona localmente sobre Windows.

⚠️ **La versión actual se distribuye sin certificado público de firma de código (Code Signing).**

Por ese motivo Windows puede mostrar **“Editor desconocido”** o una advertencia de Microsoft Defender SmartScreen. Esto no significa por sí mismo que Windows haya detectado malware: indica que el ejecutable no dispone actualmente de una firma pública de código que permita autenticar criptográficamente al editor.

Por seguridad se recomienda descargar PreservarChat exclusivamente desde este repositorio y **comparar el SHA-256 del ejecutable descargado con el publicado en la Release correspondiente**.

## 🧪 No sustituye una pericia forense

**PreservarChat no es una herramienta de adquisición forense de dispositivos.**

No realiza extracción física o lógica del teléfono, no recupera mensajes eliminados, no analiza memoria, no accede a bases de datos internas de WhatsApp, no evade mecanismos de seguridad y no obtiene información que no haya sido previamente exportada.

> 🛡️ **PreservarChat es una herramienta de apoyo para preservación documental, organización, hashing, verificación y trazabilidad de material previamente exportado. No sustituye una adquisición ni una pericia informática forense cuando éstas resulten necesarias.**

## 💡 La idea detrás de PreservarChat

Guardar una conversación de WhatsApp es fácil.

Lo difícil aparece después:

**📄 ¿Qué archivo se recibió?**  
**💬 ¿De qué conversación provenía?**  
**📱 ¿Desde qué dispositivo se realizó la exportación?**  
**📎 ¿Qué material adicional se incorporó?**  
**#️⃣ ¿Cuál era su hash?**  
**🔎 ¿El archivo que tenemos hoy sigue siendo exactamente el mismo?**

PreservarChat fue desarrollado para que esas respuestas **no dependan únicamente de la memoria de quien realizó el procedimiento**.

### 🛡️ Preservar. Documentar. Verificar.

**PreservarChat 2.5**  
**Creado por EEL CIBERSEGURIDAD – Eduardo Lecce**