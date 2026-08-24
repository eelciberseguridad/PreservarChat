# Compilar PreservarChat 2.5 FINAL para Windows

## x64

Instalá Python de 64 bits y ejecutá:

```bat
COMPILAR_PORTABLE_X64.bat
```

Salida:

```text
dist\PreservarChat_SOLO_x64.exe
```

## x86

Instalá Python de 32 bits y ejecutá:

```bat
COMPILAR_PORTABLE_X86.bat
```

Salida:

```text
dist\PreservarChat_SOLO_x86.exe
```

## Importante

PyInstaller no puede generar x86 desde Python x64 ni x64 desde Python x86.

La versión x86 usa menos dependencias opcionales. Algunas funciones de vista previa, especialmente miniaturas de video, pueden no estar disponibles si la dependencia correspondiente no ofrece soporte para Windows de 32 bits.

Los BAT verifican la arquitectura antes de compilar.

## Hash

Al terminar, el BAT muestra SHA-256 del EXE. También podés ejecutar:

```bat
VERIFICAR_EXE.bat
```

## Firma del ejecutable

El EXE generado es portable, pero no queda firmado con Authenticode. La firma de código requiere un certificado adecuado y se realiza después de compilar.
