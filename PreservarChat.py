# -*- coding: utf-8 -*-
"""
PreservarChat 2.5
Sistema de Preservación, Resguardo y Consulta Segura de Chats Exportados de WhatsApp.

Principio de diseño:
- 01_ORIGINAL_NO_MODIFICAR se preserva y nunca se utiliza para consulta.
- Toda lectura, vista de chat y multimedia se realiza desde 03_COPIA_DE_TRABAJO.
- Al abrir un expediente, su integridad se verifica antes de habilitar consulta.
"""

import csv
import hashlib
import html as html_lib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from datetime import datetime, timezone
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

try:
    from PIL import Image, ImageTk
    PIL_DISPONIBLE = True
except Exception:
    PIL_DISPONIBLE = False

try:
    import fitz
    FITZ_DISPONIBLE = True
except Exception:
    FITZ_DISPONIBLE = False

APP = "PreservarChat"
VERSION = "2.5"
CREDITOS = """Creado por EEL CIBERSEGURIDAD - Eduardo Lecce
eelciberseguridad@gmail.com"""

EXT_IMAGEN = {".jpg",".jpeg",".png",".gif",".bmp",".webp"}
EXT_AUDIO = {".mp3",".wav",".ogg",".opus",".m4a",".aac",".amr"}
EXT_VIDEO = {".mp4",".mov",".avi",".mkv",".3gp",".webm"}
EXT_DOC = {".pdf",".doc",".docx",".xls",".xlsx",".ppt",".pptx",".txt",".vcf",".zip"}



# ============================================================
# UTILIDADES
# ============================================================

def ahora_local():
    return datetime.now().astimezone().isoformat(timespec="seconds")

def ahora_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def sha(path, algoritmo="sha256"):
    h = hashlib.new(algoritmo)
    with Path(path).open("rb") as f:
        for bloque in iter(lambda: f.read(1024 * 1024), b""):
            h.update(bloque)
    return h.hexdigest()

def nombre_seguro(s):
    s = re.sub(r'[<>:"/\\|?*]+', "_", (s or "").strip())
    s = re.sub(r"\s+", "_", s)
    return s[:90] or "SIN_ID"

def guardar_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def guardar_csv(path, filas):
    if not filas:
        Path(path).write_text("", encoding="utf-8-sig")
        return
    campos = list(dict.fromkeys(k for fila in filas for k in fila))
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

def esc(s):
    return str(s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def tabla(filas):
    return "<table>" + "".join(
        f"<tr><th>{esc(k)}</th><td>{esc(v)}</td></tr>" for k,v in filas
    ) + "</table>"

def guardar_html(path, titulo, cuerpo):
    estilo = """<style>
@page{size:A4;margin:18mm}
body{font-family:Arial,Helvetica,sans-serif;font-size:12px;line-height:1.5;color:#161616;max-width:900px;margin:auto}
h1{text-align:center;font-size:22px;border-bottom:2px solid #222;padding:10px 0}

h2{font-size:15px;margin-top:24px;border-bottom:1px solid #bbb;padding-bottom:4px}
table{border-collapse:collapse;width:100%;margin:10px 0 18px}
th,td{border:1px solid #999;padding:7px;text-align:left;vertical-align:top;word-break:break-word}
th{width:31%;background:#f3f3f3}
.nota{border-left:4px solid #333;background:#f5f5f5;padding:10px}
.pie{margin-top:25px;border-top:1px solid #aaa;padding-top:7px;font-size:10px;color:#555}
</style>"""
    contenido = (
        '<!doctype html><html lang="es"><head><meta charset="utf-8"><title>' + esc(titulo) +
        '</title>' + estilo + '</head><body>' + cuerpo +
        f'<div class="pie">Documento generado mediante {APP} {VERSION}</div></body></html>'
    )
    Path(path).write_text(contenido, encoding="utf-8")


def generar_pdf_documento(path, titulo, filas, archivos=None, nota=None, subtitulo=None):
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    except Exception:
        return False

    path = Path(path)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TituloPC', parent=styles['Title'], fontName='Helvetica-Bold', fontSize=17, leading=21, alignment=TA_CENTER, spaceAfter=6)
    sub_style = ParagraphStyle('SubPC', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=TA_CENTER, textColor=colors.HexColor('#555555'), spaceAfter=14)
    body_style = ParagraphStyle('BodyPC', parent=styles['BodyText'], fontName='Helvetica', fontSize=8.2, leading=10.5)
    small_style = ParagraphStyle('SmallPC', parent=styles['BodyText'], fontName='Helvetica', fontSize=7.4, leading=9.5)
    note_style = ParagraphStyle('NotePC', parent=styles['BodyText'], fontName='Helvetica', fontSize=8.4, leading=11.5)

    def ptxt(v, small=False):
        st = small_style if small else body_style
        return Paragraph(html_lib.escape(str(v or '')).replace('\n','<br/>'), st)

    def footer(canvas, doc):
        canvas.saveState()
        w, _ = A4
        canvas.setFont('Helvetica', 7.5)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(18*mm, 10*mm, f'PreservarChat versión {VERSION} · eelciberseguridad@gmail.com')
        canvas.drawRightString(w-18*mm, 10*mm, f'Página {doc.page}')
        canvas.restoreState()

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=17*mm, bottomMargin=17*mm, title=titulo, author='PreservarChat')
    story = [
        Paragraph(html_lib.escape(titulo), title_style),
        Paragraph(html_lib.escape(subtitulo or 'Sistema de Preservación y Resguardo de Chats Exportados de WhatsApp'), sub_style),
    ]

    data=[]; section_rows=[]
    for k,v in filas:
        if v is None:
            section_rows.append(len(data))
            data.append([Paragraph(f'<b>{html_lib.escape(str(k))}</b>', body_style), ''])
        else:
            data.append([Paragraph(f'<b>{html_lib.escape(str(k))}</b>', small_style), ptxt(v, True)])
    if data:
        t=Table(data, colWidths=[52*mm,120*mm], hAlign='LEFT')
        estilos=[
            ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#B0B0B0')),
            ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F1F3F5')),('LEFTPADDING',(0,0),(-1,-1),6),
            ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),
        ]
        for r in section_rows:
            estilos += [('SPAN',(0,r),(1,r)),('BACKGROUND',(0,r),(1,r),colors.HexColor('#DDE3E8')),('TOPPADDING',(0,r),(1,r),7),('BOTTOMPADDING',(0,r),(1,r),7)]
        t.setStyle(TableStyle(estilos))
        story += [t, Spacer(1,7)]

    if archivos:
        story.append(Paragraph('Archivos documentados', ParagraphStyle('Sec', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=11, leading=14)))
        rows=[[Paragraph('<b>ID</b>',small_style),Paragraph('<b>Archivo</b>',small_style),Paragraph('<b>Tamaño</b>',small_style),Paragraph('<b>SHA-256</b>',small_style)]]
        for a in archivos:
            rows.append([ptxt(a.get('id_archivo',''),True),ptxt(a.get('nombre',a.get('nombre_original','')),True),ptxt(a.get('tamano_bytes',''),True),ptxt(a.get('sha256',''),True)])
        at=Table(rows,colWidths=[14*mm,60*mm,24*mm,74*mm],repeatRows=1)
        at.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#B5B5B5')),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E9ECEF')),('LEFTPADDING',(0,0),(-1,-1),4),
            ('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4),
        ]))
        story += [at,Spacer(1,8)]

    if nota:
        nt=Table([[Paragraph('<b>Alcance y observación</b><br/>'+html_lib.escape(nota),note_style)]],colWidths=[172*mm])
        nt.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F7F7F7')),('BOX',(0,0),(-1,-1),0.6,colors.HexColor('#7B7B7B')),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
        ]))
        story += [nt,Spacer(1,14)]

    firma=Table([['',''],['_______________________________','_______________________________'],['Firma / aclaración','Fecha']],colWidths=[82*mm,82*mm])
    firma.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,1),(-1,2),'Helvetica'),('FONTSIZE',(0,1),(-1,2),8),('TOPPADDING',(0,0),(-1,0),18)]))
    story.append(firma)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return True

def generar_pdf_custodia(root):
    p=root/'06_REGISTRO_DE_CUSTODIA'/'REGISTRO_DE_CUSTODIA.json'
    if not p.exists(): return None
    try: filas=json.loads(p.read_text(encoding='utf-8'))
    except Exception: return None
    salida=root/'06_REGISTRO_DE_CUSTODIA'/'REGISTRO_DE_CUSTODIA.pdf'
    datos=[('Cantidad de movimientos',len(filas)),('Fecha de generación',ahora_local()),('Expediente',root.name)]
    archivos=[]
    for f in filas:
        archivos.append({'id_archivo':f.get('numero',''),'nombre':f"{f.get('accion','')} - {f.get('entrega','')} -> {f.get('recibe','')}",'tamano_bytes':f.get('fecha_hora_local',''),'sha256':f.get('sha256_conjunto','')})
    generar_pdf_documento(salida,'REGISTRO DE CUSTODIA',datos,archivos,nota='Registro generado a partir de los movimientos documentados en el expediente.')
    return salida if salida.exists() else None

def mostrar_en_explorador(path):
    path=Path(path).resolve()
    if sys.platform.startswith('win'):
        subprocess.Popen(['explorer.exe','/select,',str(path)])
    else:
        abrir_archivo_seguro(path.parent)


def generar_pdf_narrativo(path, titulo, encabezado, secciones, archivos=None, nota=None):
    """PDF A4 orientado a lectura profesional no técnica."""
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    except Exception:
        return False

    styles=getSampleStyleSheet()
    titulo_st=ParagraphStyle('NTitulo',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=17,leading=21,alignment=TA_CENTER,spaceAfter=5)
    marca_st=ParagraphStyle('NMarca',parent=styles['Normal'],fontName='Helvetica-Bold',fontSize=9,leading=11,alignment=TA_CENTER,textColor=colors.HexColor('#4E5964'),spaceAfter=4)
    intro_st=ParagraphStyle('NIntro',parent=styles['BodyText'],fontName='Helvetica',fontSize=9.4,leading=13,alignment=TA_JUSTIFY,spaceAfter=10)
    sec_st=ParagraphStyle('NSec',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=11.5,leading=14,textColor=colors.HexColor('#263238'),spaceBefore=9,spaceAfter=5)
    body_st=ParagraphStyle('NBody',parent=styles['BodyText'],fontName='Helvetica',fontSize=9,leading=12.5,alignment=TA_JUSTIFY,spaceAfter=6)
    small=ParagraphStyle('NSmall',parent=styles['BodyText'],fontName='Helvetica',fontSize=7.5,leading=9.5)

    def p(v,st=body_st):
        return Paragraph(html_lib.escape(str(v or '')).replace('\n','<br/>'),st)

    def footer(canvas,doc):
        canvas.saveState();w,_=A4
        canvas.setStrokeColor(colors.HexColor('#B9BFC5'));canvas.line(18*mm,13*mm,w-18*mm,13*mm)
        canvas.setFont('Helvetica',7.5);canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(18*mm,9*mm,f'PreservarChat versión {VERSION} · eelciberseguridad@gmail.com')
        canvas.drawRightString(w-18*mm,9*mm,f'Página {doc.page}')
        canvas.restoreState()

    doc=SimpleDocTemplate(str(path),pagesize=A4,leftMargin=18*mm,rightMargin=18*mm,topMargin=17*mm,bottomMargin=18*mm,title=titulo,author='PreservarChat')
    story=[Paragraph(html_lib.escape(titulo),titulo_st)]
    if encabezado:
        story.append(Paragraph(html_lib.escape(encabezado),intro_st))
    for sec_titulo, contenido in secciones:
        story.append(Paragraph(html_lib.escape(sec_titulo),sec_st))
        if isinstance(contenido, list):
            # Pares clave/valor -> tabla; textos -> párrafos.
            if contenido and all(isinstance(x,(tuple,list)) and len(x)==2 for x in contenido):
                rows=[]
                for k,v in contenido:
                    rows.append([Paragraph(f'<b>{html_lib.escape(str(k))}</b>',small),p(v,small)])
                tb=Table(rows,colWidths=[52*mm,120*mm],hAlign='LEFT')
                tb.setStyle(TableStyle([
                    ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#CBD0D5')),
                    ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F2F4F5')),('LEFTPADDING',(0,0),(-1,-1),6),
                    ('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
                ]))
                story += [tb,Spacer(1,5)]
            else:
                for par in contenido:
                    story.append(p(par))
        else:
            story.append(p(contenido))

    if archivos:
        story.append(Paragraph('Archivos e integridad',sec_st))
        rows=[[p('<b>ID</b>',small),p('<b>Archivo</b>',small),p('<b>Tamaño</b>',small),p('<b>SHA-256</b>',small)]]
        for a in archivos:
            rows.append([p(a.get('id_archivo',''),small),p(a.get('nombre',a.get('nombre_original','')),small),p(a.get('tamano_bytes',''),small),p(a.get('sha256',a.get('sha256_copia_entrega','')),small)])
        tb=Table(rows,colWidths=[14*mm,58*mm,24*mm,76*mm],repeatRows=1)
        tb.setStyle(TableStyle([
            ('VALIGN',(0,0),(-1,-1),'TOP'),('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#CBD0D5')),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E8ECEF')),('LEFTPADDING',(0,0),(-1,-1),4),
            ('RIGHTPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)
        ]))
        story += [tb,Spacer(1,8)]

    if nota:
        nt=Table([[p('<b>Alcance</b><br/>'+nota,small)]],colWidths=[172*mm])
        nt.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F7F8F8')),('BOX',(0,0),(-1,-1),0.5,colors.HexColor('#90979D')),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
        story += [nt,Spacer(1,15)]

    firma=Table([['',''],['_______________________________','_______________________________'],['Firma / aclaración','Fecha']],colWidths=[82*mm,82*mm])
    firma.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('FONTNAME',(0,1),(-1,2),'Helvetica'),('FONTSIZE',(0,1),(-1,2),8),('TOPPADDING',(0,0),(-1,0),18)]))
    story.append(firma)
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return True


def indexar_media_chat(root):
    """Índice por nombre, limitado estrictamente a COPIA_DE_TRABAJO."""
    base=(Path(root)/'03_COPIA_DE_TRABAJO').resolve()
    idx={}
    if not base.exists():
        return idx
    for p in base.rglob('*'):
        if p.is_file() and dentro_de(p,base):
            if p.suffix.lower() in (EXT_IMAGEN|EXT_AUDIO|EXT_VIDEO|EXT_DOC):
                idx.setdefault(p.name.lower(),p)
    return idx


def media_referenciada(texto, indice):
    """Detecta archivos cuyo nombre aparece literalmente en el texto exportado."""
    t=(texto or '').lower()
    hallados=[]
    for nombre,p in indice.items():
        if nombre in t:
            hallados.append(p)
    return hallados

def dentro_de(ruta, base):
    try:
        return os.path.commonpath([str(Path(ruta).resolve()), str(Path(base).resolve())]) == str(Path(base).resolve())
    except Exception:
        return False

def ruta_interna_segura(root, rel):
    """Resuelve una ruta relativa y exige que permanezca dentro del expediente."""
    base=Path(root).resolve()
    q=(base/str(rel or "")).resolve()
    if not dentro_de(q,base):
        raise ValueError("Ruta interna inválida: fuera del expediente.")
    return q

def abrir_archivo_seguro(path):
    path = Path(path)
    if sys.platform.startswith("win"):
        os.startfile(str(path))
    else:
        messagebox.showinfo(APP, str(path))

def abrir_carpeta(path):
    """Abre una carpeta de forma robusta, especialmente en Windows empaquetado."""
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    if sys.platform.startswith("win"):
        try:
            os.startfile(str(path))
            return
        except Exception:
            import subprocess
            subprocess.Popen(["explorer", str(path)])
            return
    try:
        import subprocess
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except Exception:
        messagebox.showinfo(APP, str(path))

def directorio_programa():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

def directorio_expedientes():
    p=directorio_programa()/"Expedientes"
    p.mkdir(parents=True,exist_ok=True)
    return p

def directorio_entregas():
    p=directorio_programa()/"Entregas"
    p.mkdir(parents=True,exist_ok=True)
    return p

def ruta_config():
    d = Path.home()/".preservachat"
    d.mkdir(exist_ok=True)
    return d/"config.json"

def cargar_config():
    p = ruta_config()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

def guardar_config(data):
    try:
        guardar_json(ruta_config(), data)
    except Exception:
        pass

# ============================================================
# PERIODOS Y PARSEO DEL CHAT
# ============================================================

PATRONES_MENSAJE = [
    re.compile(
        r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"
        r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM|a\.?\s*m\.?|p\.?\s*m\.?))?)\]?"
        r"\s*[-–]\s*([^:]+):\s?(.*)$", re.I
    ),
    re.compile(
        r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+"
        r"(\d{1,2}:\d{2}(?::\d{2})?(?:\s*(?:AM|PM))?)\]?"
        r"\s+([^:]+):\s?(.*)$", re.I
    ),
]

def normalizar_anio(y):
    y = int(y)
    if y < 100:
        return 2000+y if y < 70 else 1900+y
    return y

def fecha_desde_texto(s):
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s.strip())
    if not m:
        return None
    d,mn,y = m.groups()
    try:
        return datetime(normalizar_anio(y), int(mn), int(d))
    except Exception:
        return None

def parsear_chat(path):
    """
    Devuelve mensajes estructurados.
    Las líneas no reconocidas se anexan al mensaje anterior para preservar multilinea.
    """
    mensajes = []
    actual = None

    with Path(path).open("r", encoding="utf-8-sig", errors="replace") as f:
        for linea in f:
            linea = linea.rstrip("\r\n")
            encontrado = None
            for patron in PATRONES_MENSAJE:
                encontrado = patron.match(linea)
                if encontrado:
                    break

            if encontrado:
                fecha, hora, autor, texto = encontrado.groups()
                actual = {
                    "fecha": fecha.strip(),
                    "hora": hora.strip(),
                    "autor": autor.strip(),
                    "texto": texto
                }
                mensajes.append(actual)
            elif actual is not None:
                actual["texto"] += "\n" + linea
            elif linea.strip():
                # Mensaje de sistema / línea inicial no atribuida.
                mensajes.append({
                    "fecha":"",
                    "hora":"",
                    "autor":"Sistema",
                    "texto":linea
                })
                actual = mensajes[-1]

    return mensajes

def detectar_periodo_mensajes(mensajes):
    fechas = []
    for m in mensajes:
        f = fecha_desde_texto(m.get("fecha",""))
        if f:
            fechas.append(f)

    if not fechas:
        return {"periodo":"","primera":"","ultima":"","mensajes_con_fecha":0}

    primera = min(fechas)
    ultima = max(fechas)
    return {
        "periodo": f"{primera.strftime('%d/%m/%Y')} al {ultima.strftime('%d/%m/%Y')}",
        "primera": primera.strftime("%d/%m/%Y"),
        "ultima": ultima.strftime("%d/%m/%Y"),
        "mensajes_con_fecha": len(fechas)
    }

# ============================================================
# EVIDENCIA / ARCHIVOS
# ============================================================

def clasificar_archivo(path):
    p = Path(path)
    tam = p.stat().st_size
    ext = p.suffix.lower()
    info = {
        "clasificacion": "ARCHIVO ASOCIADO A LA EXPORTACION",
        "motivo": "Archivo recibido junto con la exportación."
    }

    if tam <= 4096:
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore").strip().lower()
            frases = [
                "el historial del chat se adjuntó",
                "el historial del chat se adjunto",
                "chat de whatsapp",
                "se adjuntó a este correo",
                "se adjunto a este correo"
            ]
            if txt and any(f in txt for f in frases):
                info["clasificacion"] = "ARCHIVO AUXILIAR / MENSAJE DE ACOMPAÑAMIENTO"
                info["motivo"] = "Texto informativo asociado al mecanismo de exportación/compartición."
                return info
        except Exception:
            pass

    if ext == ".zip":
        info["clasificacion"] = "CONTENEDOR PRINCIPAL DE EXPORTACION"
        info["motivo"] = "Archivo ZIP recibido como parte de la exportación."
    elif ext == ".txt":
        info["clasificacion"] = "HISTORIAL DE CHAT EN TEXTO"
        info["motivo"] = "Archivo de texto recibido como parte de la exportación."
    elif tam > 1024*1024:
        info["clasificacion"] = "ARCHIVO PRINCIPAL / CONTENEDOR DE GRAN TAMAÑO"
        info["motivo"] = "Archivo de mayor tamaño recibido junto con la exportación."

    return info

MAX_ZIP_ENTRADAS = 50000
MAX_ZIP_TOTAL_DESCOMPRIMIDO = 10 * 1024 * 1024 * 1024  # 10 GiB
MAX_ZIP_ARCHIVO_DESCOMPRIMIDO = 4 * 1024 * 1024 * 1024  # 4 GiB
MAX_ZIP_RATIO = 1000

def _zip_es_enlace(info):
    # Unix file type in upper 16 bits of external_attr.
    modo = (info.external_attr >> 16) & 0o170000
    return modo == 0o120000

def validar_zip(path):
    """Inspecciona un ZIP antes de extraerlo y rechaza rutas o tamaños peligrosos."""
    with zipfile.ZipFile(path) as z:
        infos=z.infolist()
        if len(infos) > MAX_ZIP_ENTRADAS:
            raise ValueError(f"ZIP con demasiadas entradas ({len(infos)}).")
        total=0
        for i in infos:
            n=i.filename.replace("\\","/")
            if not n or "\x00" in n:
                raise ValueError("ZIP con nombre de entrada inválido.")
            # Absolutas POSIX, UNC, unidades Windows y cualquier componente '..'.
            partes=[x for x in n.split('/') if x not in ('','.') ]
            if n.startswith('/') or n.startswith('//') or re.match(r'^[A-Za-z]:',n) or '..' in partes:
                raise ValueError("ZIP con ruta insegura: " + i.filename)
            if _zip_es_enlace(i):
                raise ValueError("ZIP con enlace simbólico no permitido: " + i.filename)
            if i.file_size > MAX_ZIP_ARCHIVO_DESCOMPRIMIDO:
                raise ValueError("ZIP con archivo individual excesivamente grande: " + i.filename)
            total += i.file_size
            if total > MAX_ZIP_TOTAL_DESCOMPRIMIDO:
                raise ValueError("ZIP con tamaño descomprimido total superior al límite de seguridad.")
            if i.compress_size == 0 and i.file_size > 0:
                raise ValueError("ZIP con relación de compresión anómala: " + i.filename)
            if i.compress_size > 0 and i.file_size > 100*1024*1024 and (i.file_size / i.compress_size) > MAX_ZIP_RATIO:
                raise ValueError("ZIP con relación de compresión sospechosa: " + i.filename)
    return True

def extraer_zip_seguro(path, destino):
    """Extrae manualmente luego de validar, garantizando que cada salida quede dentro de destino."""
    validar_zip(path)
    destino=Path(destino).resolve()
    destino.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            n=i.filename.replace("\\","/")
            rel=Path(*[x for x in n.split('/') if x not in ('','.')])
            objetivo=(destino/rel).resolve()
            if os.path.commonpath([str(objetivo),str(destino)]) != str(destino):
                raise ValueError("ZIP intenta escribir fuera del destino: " + i.filename)
            if i.is_dir():
                objetivo.mkdir(parents=True,exist_ok=True)
                continue
            objetivo.parent.mkdir(parents=True,exist_ok=True)
            with z.open(i,'r') as src, objetivo.open('wb') as dst:
                shutil.copyfileobj(src,dst,length=1024*1024)

def registrar_incidencia(root, nivel, codigo, descripcion):
    p = root/"09_INCIDENCIAS"/"INCIDENCIAS.json"
    filas = json.loads(p.read_text(encoding="utf-8")) if p.exists() else []
    filas.append({
        "numero":len(filas)+1,
        "fecha_hora_local":ahora_local(),
        "fecha_hora_utc":ahora_utc(),
        "nivel":nivel,
        "codigo":codigo,
        "descripcion":descripcion
    })
    guardar_json(p, filas)
    guardar_csv(root/"09_INCIDENCIAS"/"INCIDENCIAS.csv", filas)

def hash_conjunto(recepcion):
    canonico = json.dumps(
        [{"id":r["id_archivo"],"nombre":r["nombre"],"tamano_bytes":r["tamano_bytes"],"sha256":r["sha256"]}
         for r in recepcion],
        ensure_ascii=False, sort_keys=True, separators=(",",":")
    ).encode("utf-8")
    return hashlib.sha256(canonico).hexdigest()

def encontrar_chat_principal(root):
    base = (root/"03_COPIA_DE_TRABAJO").resolve()
    if not base.exists():
        return None

    candidatos = [p for p in base.rglob("*.txt") if p.is_file() and dentro_de(p,base)]
    if not candidatos:
        return None

    # Evitar auxiliar muy pequeño cuando existe otro TXT.
    mayores = [p for p in candidatos if p.stat().st_size > 4096]
    if mayores:
        candidatos = mayores

    con_chat = [p for p in candidatos if "chat" in p.name.lower()]
    if con_chat:
        return max(con_chat, key=lambda p:p.stat().st_size)

    en_contenido = [p for p in candidatos if "_CONTENIDO" in str(p.parent)]
    if en_contenido:
        return max(en_contenido, key=lambda p:p.stat().st_size)

    return max(candidatos, key=lambda p:p.stat().st_size)

def listar_multimedia(root):
    base = (root/"03_COPIA_DE_TRABAJO").resolve()
    if not base.exists():
        return []

    archivos = []
    for p in base.rglob("*"):
        if not p.is_file() or not dentro_de(p,base):
            continue
        ext = p.suffix.lower()
        if ext in EXT_IMAGEN:
            tipo = "Imagen"
        elif ext in EXT_AUDIO:
            tipo = "Audio"
        elif ext in EXT_VIDEO:
            tipo = "Video"
        elif ext in EXT_DOC and ext != ".txt":
            tipo = "Documento"
        else:
            continue
        archivos.append({
            "path":p,
            "nombre":p.name,
            "tipo":tipo,
            "tamano":p.stat().st_size,
            "ruta_relativa":str(p.relative_to(root))
        })

    archivos.sort(key=lambda x:(x["tipo"],x["nombre"].lower()))
    return archivos

# ============================================================
# REGISTRO VISUAL COMPLEMENTARIO
# ============================================================

def tipo_registro_visual(path):
    ext=Path(path).suffix.lower()
    if ext in EXT_IMAGEN:return 'Imagen'
    if ext in EXT_VIDEO:return 'Video'
    if ext in EXT_AUDIO:return 'Audio'
    if ext in {'.pdf'}:return 'PDF'
    if ext in {'.doc','.docx','.odt','.rtf'}:return 'Documento'
    if ext in {'.xls','.xlsx','.xlsm','.ods','.csv'}:return 'Planilla'
    return 'Archivo'

def _fmt_fs_time(ts):
    try:return datetime.fromtimestamp(ts).astimezone().isoformat(timespec='seconds')
    except Exception:return ''

def leer_metadatos_registro_visual(path):
    """Lee metadatos sin modificar el archivo. Distingue metadatos internos de tiempos del sistema de archivos."""
    p=Path(path)
    datos={
        'fecha_hora_metadatos':'',
        'fuente_fecha_metadatos':'No disponible',
        'marca_dispositivo':'',
        'modelo_dispositivo':'',
        'duracion_segundos':'',
        'ancho':'',
        'alto':'',
        'fecha_modificacion_sistema':_fmt_fs_time(p.stat().st_mtime),
        'fecha_creacion_sistema':_fmt_fs_time(p.stat().st_ctime),
    }
    if p.suffix.lower() in EXT_IMAGEN and PIL_DISPONIBLE:
        try:
            with Image.open(p) as im:
                datos['ancho'],datos['alto']=im.size
                exif=im.getexif() or {}
                # EXIF: DateTimeOriginal 36867, DateTimeDigitized 36868, DateTime 306, Make 271, Model 272
                fecha=exif.get(36867) or exif.get(36868) or exif.get(306) or ''
                if fecha:
                    datos['fecha_hora_metadatos']=str(fecha)
                    datos['fuente_fecha_metadatos']='EXIF del archivo'
                datos['marca_dispositivo']=str(exif.get(271) or '')
                datos['modelo_dispositivo']=str(exif.get(272) or '')
        except Exception:
            pass
    elif p.suffix.lower() in EXT_VIDEO or p.suffix.lower() in EXT_AUDIO:
        ffprobe=shutil.which('ffprobe')
        if ffprobe:
            try:
                cp=subprocess.run([
                    ffprobe,'-v','quiet','-print_format','json','-show_format','-show_streams',str(p)
                ],capture_output=True,text=True,timeout=15)
                meta=json.loads(cp.stdout or '{}')
                fmt=meta.get('format',{})
                tags=fmt.get('tags',{}) or {}
                creation=tags.get('creation_time') or tags.get('date') or ''
                if creation:
                    datos['fecha_hora_metadatos']=str(creation)
                    datos['fuente_fecha_metadatos']='Metadato interno leído con ffprobe'
                dur=fmt.get('duration')
                if dur not in (None,''):
                    try:datos['duracion_segundos']=round(float(dur),3)
                    except Exception:datos['duracion_segundos']=str(dur)
                for s in meta.get('streams',[]) or []:
                    if s.get('codec_type')=='video':
                        datos['ancho']=s.get('width','');datos['alto']=s.get('height','');break
            except Exception:
                pass
    return datos

def ruta_registro_visual(root):
    return Path(root)/'10_REGISTRO_VISUAL'

def asegurar_registro_visual(root):
    base=ruta_registro_visual(root)
    for p in [base/'01_ARCHIVOS_PRESERVADOS',base/'02_COPIAS_DE_CONSULTA']:
        p.mkdir(parents=True,exist_ok=True)
    manifest=base/'MANIFIESTO_REGISTRO_VISUAL.json'
    if not manifest.exists():guardar_json(manifest,[])
    return base

def leer_registro_visual(root):
    base=asegurar_registro_visual(root)
    p=base/'MANIFIESTO_REGISTRO_VISUAL.json'
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return []

def guardar_registro_visual(root,filas):
    base=asegurar_registro_visual(root)
    guardar_json(base/'MANIFIESTO_REGISTRO_VISUAL.json',filas)
    guardar_csv(base/'MANIFIESTO_REGISTRO_VISUAL.csv',filas)
    if (base/'MANIFIESTO_REGISTRO_VISUAL.json').exists():
        (base/'SHA256_MANIFIESTO_REGISTRO_VISUAL.txt').write_text(
            sha(base/'MANIFIESTO_REGISTRO_VISUAL.json')+'\n',encoding='utf-8'
        )

def leer_registro_visual_retirado(root):
    base=asegurar_registro_visual(root)
    p=base/'REGISTRO_VISUAL_RETIRADOS.json'
    if not p.exists(): return []
    try:return json.loads(p.read_text(encoding='utf-8'))
    except Exception:return []

def guardar_registro_visual_retirado(root,filas):
    base=asegurar_registro_visual(root)
    guardar_json(base/'REGISTRO_VISUAL_RETIRADOS.json',filas)
    guardar_csv(base/'REGISTRO_VISUAL_RETIRADOS.csv',filas)
    p=base/'REGISTRO_VISUAL_RETIRADOS.json'
    (base/'SHA256_REGISTRO_VISUAL_RETIRADOS.txt').write_text(sha(p)+'\n',encoding='utf-8')

def retirar_version_visual(root,reg,motivo,responsable=''):
    """Retira un elemento de la vista y de la entrega sin destruir su rastro de auditoría."""
    root=Path(root);base=asegurar_registro_visual(root)
    destino=base/'99_RETIRADOS_NO_ENTREGAR';destino.mkdir(parents=True,exist_ok=True)
    sello=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    retirados=leer_registro_visual_retirado(root)
    nro=len(retirados)+1
    item={
        'numero_retiro':nro,'id_registro':reg.get('id_registro',''),'nombre_original':reg.get('nombre_original',''),
        'sha256_original_registrado':reg.get('sha256',''),'sha512_original_registrado':reg.get('sha512',''),
        'motivo':motivo,'responsable':responsable,'fecha_hora_local':ahora_local(),'fecha_hora_utc':ahora_utc(),
        'archivos':[]
    }
    for clase,rel in [('PRESERVADO',reg.get('ruta_preservada','')),('COPIA',reg.get('ruta_copia',''))]:
        if not rel: continue
        old=root/rel
        if not old.exists(): continue
        nombre=f"RET-{nro:03d}_{sello}_{clase}_{old.name}"
        dst=destino/nombre
        try: old.chmod(0o666)
        except Exception: pass
        shutil.move(str(old),str(dst))
        try: dst.chmod(0o444)
        except Exception: pass
        item['archivos'].append({
            'tipo':clase,'ruta_relativa':str(dst.relative_to(root)),'tamano_bytes':dst.stat().st_size,
            'sha256':sha(dst),'sha512':sha(dst,'sha512')
        })
    retirados.append(item);guardar_registro_visual_retirado(root,retirados)
    return item

def agregar_evento_bitacora(root,tipo,descripcion,responsable=''):
    p=Path(root)/'08_BITACORA'/'BITACORA.json'
    eventos=[]
    if p.exists():
        try:eventos=json.loads(p.read_text(encoding='utf-8'))
        except Exception:eventos=[]
    previo=eventos[-1].get('hash_evento','') if eventos else ''
    e={
        'numero':len(eventos)+1,'fecha_hora_local':ahora_local(),'fecha_hora_utc':ahora_utc(),
        'tipo':tipo,'responsable':responsable,'descripcion':descripcion,'hash_anterior':previo
    }
    e['hash_evento']=hashlib.sha256(json.dumps(e,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
    eventos.append(e)
    guardar_json(p,eventos);guardar_csv(Path(root)/'08_BITACORA'/'BITACORA.csv',eventos)

def actualizar_manifiesto_general_con_visual(root,registro):
    root=Path(root)
    mp=root/'02_INTEGRIDAD'/'MANIFIESTO.json'
    mani=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else []
    ids={x.get('id_archivo') for x in mani if str(x.get('id_archivo','')).startswith('RV-')}
    if registro['id_registro'] in ids:return
    for tipo,rel in [('REGISTRO_VISUAL_PRESERVADO',registro['ruta_preservada']),('REGISTRO_VISUAL_COPIA',registro['ruta_copia'])]:
        p=root/rel
        mani.append({
            'id_archivo':registro['id_registro'],'tipo':tipo,'clasificacion':'REGISTRO VISUAL COMPLEMENTARIO',
            'ruta_relativa':rel,'nombre_original':registro['nombre_original'],'tamano_bytes':p.stat().st_size,
            'sha256':sha(p),'sha512':sha(p,'sha512')
        })
    guardar_json(mp,mani);guardar_csv(root/'02_INTEGRIDAD'/'MANIFIESTO.csv',mani)
    hm=sha(mp);(root/'02_INTEGRIDAD'/'SHA256_MANIFIESTO.txt').write_text(hm+'\n',encoding='utf-8')
    fp=root/'00_DATOS_DEL_CASO'/'FICHA_DEL_CASO.json'
    if fp.exists():
        try:
            ficha=json.loads(fp.read_text(encoding='utf-8'));ficha['sha256_manifiesto']=hm;guardar_json(fp,ficha)
        except Exception:pass


def reconstruir_manifiesto_visual_general(root):
    """Reconstruye únicamente las entradas RV del manifiesto general."""
    root=Path(root)
    mp=root/'02_INTEGRIDAD'/'MANIFIESTO.json'
    mani=json.loads(mp.read_text(encoding='utf-8')) if mp.exists() else []
    mani=[x for x in mani if not str(x.get('id_archivo','')).startswith('RV-')]
    for reg in leer_registro_visual(root):
        for tipo,rel in [
            ('REGISTRO_VISUAL_PRESERVADO',reg.get('ruta_preservada','')),
            ('REGISTRO_VISUAL_COPIA',reg.get('ruta_copia',''))
        ]:
            p=root/rel
            if not p.exists():
                continue
            mani.append({
                'id_archivo':reg.get('id_registro',''),
                'tipo':tipo,
                'clasificacion':'REGISTRO VISUAL COMPLEMENTARIO',
                'ruta_relativa':rel,
                'nombre_original':reg.get('nombre_original',''),
                'tamano_bytes':p.stat().st_size,
                'sha256':sha(p),
                'sha512':sha(p,'sha512')
            })
    # Las versiones retiradas no se muestran ni se entregan, pero permanecen verificables para auditoría.
    for ret in leer_registro_visual_retirado(root):
        for n,a in enumerate(ret.get('archivos',[]),1):
            rel=a.get('ruta_relativa','');p=root/rel
            if not rel or not p.exists(): continue
            mani.append({
                'id_archivo':f"{ret.get('id_registro','RV')}-RET-{ret.get('numero_retiro','')}-{n}",
                'tipo':'REGISTRO_VISUAL_RETIRADO_NO_ENTREGAR','clasificacion':'AUDITORIA - NO ENTREGAR',
                'ruta_relativa':rel,'nombre_original':ret.get('nombre_original',''),'tamano_bytes':p.stat().st_size,
                'sha256':a.get('sha256') or sha(p),'sha512':a.get('sha512') or sha(p,'sha512')
            })
    guardar_json(mp,mani)
    guardar_csv(root/'02_INTEGRIDAD'/'MANIFIESTO.csv',mani)
    hm=sha(mp)
    (root/'02_INTEGRIDAD'/'SHA256_MANIFIESTO.txt').write_text(hm+'\n',encoding='utf-8')
    fp=root/'00_DATOS_DEL_CASO'/'FICHA_DEL_CASO.json'
    if fp.exists():
        try:
            ficha=json.loads(fp.read_text(encoding='utf-8'))
            ficha['sha256_manifiesto']=hm
            guardar_json(fp,ficha)
        except Exception:
            pass

def editar_descripcion_registro_visual(root,id_registro,nueva_descripcion,responsable=''):
    root=Path(root)
    filas=leer_registro_visual(root)
    encontrado=False
    for r in filas:
        if r.get('id_registro')==id_registro:
            anterior=r.get('descripcion','')
            r['descripcion']=nueva_descripcion.strip() or 'Sin descripción adicional.'
            encontrado=True
            agregar_evento_bitacora(
                root,'REGISTRO_VISUAL_EDICION',
                f"Se modificó la descripción de {id_registro}. Descripción anterior: {anterior!r}. Nueva descripción: {r['descripcion']!r}.",
                responsable
            )
            break
    if not encontrado:
        raise ValueError(f'No se encontró {id_registro}.')
    guardar_registro_visual(root,filas)
    regenerar_documentacion_judicial(root)

def reemplazar_registro_visual(root,id_registro,nuevo_archivo,responsable=''):
    """
    Reemplaza un elemento incorporado por error manteniendo el mismo ID.
    La sustitución queda registrada en bitácora con hash anterior y nuevo.
    """
    root=Path(root)
    nuevo_archivo=Path(nuevo_archivo).resolve()
    if not nuevo_archivo.is_file():
        raise FileNotFoundError(str(nuevo_archivo))
    filas=leer_registro_visual(root)
    reg=next((r for r in filas if r.get('id_registro')==id_registro),None)
    if not reg:
        raise ValueError(f'No se encontró {id_registro}.')

    hash_anterior=reg.get('sha256','')
    ruta_pres_old=root/reg.get('ruta_preservada','')
    ruta_copia_old=root/reg.get('ruta_copia','')

    rid=id_registro
    base=asegurar_registro_visual(root)
    sello_reemplazo=datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    nombre=f'{rid}__R_{sello_reemplazo}__{nuevo_archivo.name}'
    preservado=base/'01_ARCHIVOS_PRESERVADOS'/nombre
    copia=base/'02_COPIAS_DE_CONSULTA'/nombre

    nuevo_hash=sha(nuevo_archivo)
    nuevo_sha512=sha(nuevo_archivo,'sha512')
    shutil.copy2(nuevo_archivo,preservado)
    if sha(preservado)!=nuevo_hash:
        raise RuntimeError('El archivo reemplazante no coincide después de preservarse.')
    try:
        preservado.chmod(0o444)
    except Exception:
        pass
    shutil.copy2(preservado,copia)
    if sha(copia)!=nuevo_hash:
        raise RuntimeError('La copia de consulta del archivo reemplazante no coincide.')

    meta=leer_metadatos_registro_visual(preservado)

    # Retirar la versión anterior sólo después de validar la nueva. No se destruye: queda en auditoría.
    retiro=retirar_version_visual(root,reg,'REEMPLAZO DE ARCHIVO',responsable)

    reg.update({
        'nombre_original':nuevo_archivo.name,
        'tipo':tipo_registro_visual(nuevo_archivo),
        'tamano_bytes':nuevo_archivo.stat().st_size,
        'sha256':nuevo_hash,
        'sha512':nuevo_sha512,
        'fecha_hora_incorporacion_local':ahora_local(),
        'fecha_hora_incorporacion_utc':ahora_utc(),
        'fecha_hora_metadatos':meta.get('fecha_hora_metadatos',''),
        'fuente_fecha_metadatos':meta.get('fuente_fecha_metadatos',''),
        'marca_dispositivo_metadatos':meta.get('marca_dispositivo',''),
        'modelo_dispositivo_metadatos':meta.get('modelo_dispositivo',''),
        'duracion_segundos':meta.get('duracion_segundos',''),
        'dimensiones':f"{meta.get('ancho','')}x{meta.get('alto','')}" if meta.get('ancho') and meta.get('alto') else '',
        'fecha_modificacion_sistema':meta.get('fecha_modificacion_sistema',''),
        'fecha_creacion_sistema':meta.get('fecha_creacion_sistema',''),
        'ruta_preservada':str(preservado.relative_to(root)),
        'ruta_copia':str(copia.relative_to(root)),
        'responsable_incorporacion':responsable
    })
    guardar_registro_visual(root,filas)
    reconstruir_manifiesto_visual_general(root)
    agregar_evento_bitacora(
        root,'REGISTRO_VISUAL_REEMPLAZO',
        f"Se reemplazó {id_registro}. SHA-256 anterior: {hash_anterior}. SHA-256 nuevo: {nuevo_hash}. Archivo nuevo: {nuevo_archivo.name}.",
        responsable
    )
    regenerar_documentacion_judicial(root)

def eliminar_registro_visual(root,id_registro,responsable=''):
    """
    Retira un elemento cargado por error de la vista y de la entrega.
    El archivo no se destruye: queda apartado en 99_RETIRADOS_NO_ENTREGAR con hash y trazabilidad.
    """
    root=Path(root)
    filas=leer_registro_visual(root)
    reg=next((r for r in filas if r.get('id_registro')==id_registro),None)
    if not reg:
        raise ValueError(f'No se encontró {id_registro}.')
    retiro=retirar_version_visual(root,reg,'ELIMINACION DE CARGA EQUIVOCADA',responsable)
    agregar_evento_bitacora(
        root,'REGISTRO_VISUAL_ELIMINACION',
        f"Se retiró del Registro Visual activo {id_registro}: {reg.get('nombre_original','')}. SHA-256 previo: {reg.get('sha256','')}. "
        f"El material quedó preservado fuera de la entrega en registro de auditoría N° {retiro.get('numero_retiro') }.",
        responsable
    )
    filas=[r for r in filas if r.get('id_registro')!=id_registro]
    for idx,r in enumerate(filas,1):
        r['orden']=idx
    guardar_registro_visual(root,filas)
    reconstruir_manifiesto_visual_general(root)
    regenerar_documentacion_judicial(root)

def incorporar_registro_visual(root,source,descripcion,responsable=''):
    root=Path(root);source=Path(source).resolve()
    if not source.is_file():raise FileNotFoundError(str(source))
    base=asegurar_registro_visual(root)
    filas=leer_registro_visual(root)
    # Evitar incorporar dos veces el mismo contenido, aunque el archivo tenga otro nombre.
    h_recepcion=sha(source)
    duplicado=next((r for r in filas if r.get('sha256')==h_recepcion),None)
    if duplicado:
        raise ValueError(
            f"El archivo ya está incorporado al Registro Visual como {duplicado.get('id_registro','')}: "
            f"{duplicado.get('nombre_original','')}.\n\nSHA-256: {h_recepcion}"
        )
    orden=len(filas)+1;rid=f'RV-{orden:03d}'
    nombre=f'{rid}__{source.name}'
    h512=sha(source,'sha512')
    preservado=base/'01_ARCHIVOS_PRESERVADOS'/nombre
    shutil.copy2(source,preservado)
    if sha(preservado)!=h_recepcion:
        raise RuntimeError(f'El archivo {source.name} no coincide después de preservarse.')
    try:preservado.chmod(0o444)
    except Exception:pass
    copia=base/'02_COPIAS_DE_CONSULTA'/nombre
    shutil.copy2(preservado,copia)
    if sha(copia)!=h_recepcion:
        raise RuntimeError(f'La copia de consulta de {source.name} no coincide.')
    meta=leer_metadatos_registro_visual(preservado)
    reg={
        'orden':orden,'id_registro':rid,'nombre_original':source.name,'tipo':tipo_registro_visual(source),
        'descripcion':descripcion or 'Sin descripción adicional.','tamano_bytes':source.stat().st_size,
        'sha256':h_recepcion,'sha512':h512,'fecha_hora_incorporacion_local':ahora_local(),
        'fecha_hora_incorporacion_utc':ahora_utc(),'fecha_hora_metadatos':meta.get('fecha_hora_metadatos',''),
        'fuente_fecha_metadatos':meta.get('fuente_fecha_metadatos',''),'marca_dispositivo_metadatos':meta.get('marca_dispositivo',''),
        'modelo_dispositivo_metadatos':meta.get('modelo_dispositivo',''),'duracion_segundos':meta.get('duracion_segundos',''),
        'dimensiones':f"{meta.get('ancho','')}x{meta.get('alto','')}" if meta.get('ancho') and meta.get('alto') else '',
        'fecha_modificacion_sistema':meta.get('fecha_modificacion_sistema',''),'fecha_creacion_sistema':meta.get('fecha_creacion_sistema',''),
        'ruta_preservada':str(preservado.relative_to(root)),'ruta_copia':str(copia.relative_to(root)),
        'responsable_incorporacion':responsable
    }
    filas.append(reg);guardar_registro_visual(root,filas);actualizar_manifiesto_general_con_visual(root,reg)
    agregar_evento_bitacora(root,'REGISTRO_VISUAL',f"Se incorporó {rid}: {source.name}. SHA-256 {h_recepcion}",responsable)
    regenerar_documentacion_judicial(root)
    return reg

def _thumb_visual(reg,root,max_w=None,max_h=None):
    """
    Vista previa documental. Para videos intenta extraer un fotograma con OpenCV.
    La miniatura es sólo una representación visual derivada; el archivo original
    y su hash continúan siendo la referencia de integridad.
    """
    try:
        from reportlab.platypus import Image as RLImage, Table, TableStyle, Paragraph
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import mm
    except Exception:
        return None

    if max_w is None: max_w=110*mm
    if max_h is None: max_h=70*mm

    p=Path(root)/reg.get('ruta_copia','')
    if not p.exists():
        p=Path(root)/reg.get('ruta_preservada','')

    # Imagen: se muestra directamente como vista previa.
    if reg.get('tipo')=='Imagen' and PIL_DISPONIBLE and p.exists():
        try:
            with Image.open(p) as im:
                w,h=im.size
            scale=min(max_w/w,max_h/h,1)
            return RLImage(str(p),width=w*scale,height=h*scale)
        except Exception:
            pass

    # Video: fotograma representativo generado exclusivamente para el acta.
    if reg.get('tipo')=='Video' and p.exists():
        try:
            import cv2
            thumbs=Path(root)/'05_ACTAS'/'VISTAS_PREVIAS'
            thumbs.mkdir(parents=True,exist_ok=True)
            out=thumbs/f"{nombre_seguro(reg.get('id_registro','VIDEO'))}_fotograma.jpg"
            cap=cv2.VideoCapture(str(p))
            frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            fps=float(cap.get(cv2.CAP_PROP_FPS) or 0)
            # Preferir aproximadamente el segundo 1; si no, 10% del video.
            objetivo=int(fps) if fps>0 else 0
            if frames>0:
                objetivo=min(max(objetivo,int(frames*0.10)),max(frames-1,0))
                cap.set(cv2.CAP_PROP_POS_FRAMES,objetivo)
            ok,frame=cap.read()
            cap.release()
            if ok and frame is not None:
                cv2.imwrite(str(out),frame)
                if PIL_DISPONIBLE:
                    with Image.open(out) as im:
                        w,h=im.size
                    scale=min(max_w/w,max_h/h,1)
                    img=RLImage(str(out),width=w*scale,height=h*scale)
                    styles=getSampleStyleSheet()
                    nota=Paragraph(
                        '<font size="7">Vista previa: fotograma extraído automáticamente del video para facilitar su identificación. '
                        'No reemplaza al archivo original ni forma parte de su hash.</font>',
                        styles['BodyText']
                    )
                    return Table([[img],[nota]],colWidths=[max_w])
        except Exception:
            pass

    # Audio, video sin decodificador u otros archivos: ficha identificadora.
    styles=getSampleStyleSheet()
    txt=(
        f"<b>{html_lib.escape(reg.get('tipo','Archivo').upper())}</b><br/>"
        f"{html_lib.escape(reg.get('nombre_original',''))}<br/>"
        "Archivo completo incorporado al Registro Visual."
    )
    t=Table([[Paragraph(txt,styles['BodyText'])]],colWidths=[110*mm],rowHeights=[32*mm])
    t.setStyle(TableStyle([
        ('BOX',(0,0),(-1,-1),0.7,colors.HexColor('#888888')),
        ('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#F3F4F5')),
        ('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ALIGN',(0,0),(-1,-1),'CENTER')
    ]))
    return t

def generar_acta_registro_visual(root):
    root=Path(root);registros=leer_registro_visual(root)
    if not registros:return None
    ficha=leer_ficha(root);datos=ficha.get('datos',{})
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak
    except Exception:return None
    out=root/'05_ACTAS'/'03_ACTA_DE_REGISTRO_VISUAL.pdf'
    styles=getSampleStyleSheet()
    title=ParagraphStyle('rvtitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=17,leading=21,alignment=TA_CENTER,spaceAfter=8)
    sub=ParagraphStyle('rvsub',parent=styles['Normal'],fontSize=9,leading=12,alignment=TA_CENTER,textColor=colors.HexColor('#555555'),spaceAfter=12)
    h=ParagraphStyle('rvh',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=11,leading=14,spaceBefore=8,spaceAfter=6)
    body=ParagraphStyle('rvbody',parent=styles['BodyText'],fontSize=9,leading=12)
    small=ParagraphStyle('rvsmall',parent=styles['BodyText'],fontSize=7.5,leading=10)
    def footer(canvas,doc):
        canvas.saveState();w,_=A4;canvas.setFont('Helvetica',7.5);canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(18*mm,10*mm,f'PreservarChat versión {VERSION} · eelciberseguridad@gmail.com');canvas.drawRightString(w-18*mm,10*mm,f'Página {doc.page}');canvas.restoreState()
    doc=SimpleDocTemplate(str(out),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=17*mm,title='Acta de Registro Visual')
    story=[Paragraph('ACTA DE REGISTRO VISUAL',title)]
    intro=[
        ['Caso',datos.get('id_caso','')],['Evidencia',datos.get('id_evidencia','')],['Contacto / grupo',datos.get('contacto_grupo','')],
        ['Dispositivo',f"{datos.get('marca','')} {datos.get('modelo','')}".strip()],['IMEI',datos.get('imei','')],['Número asociado a WhatsApp',datos.get('numero_whatsapp','')],
        ['Responsable',datos.get('responsable','')],['Cantidad de elementos',str(len(registros))]
    ]
    tbl=Table([[Paragraph(f'<b>{html_lib.escape(k)}</b>',small),Paragraph(html_lib.escape(str(v or 'No informado')),small)] for k,v in intro],colWidths=[50*mm,122*mm])
    tbl.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#BBBBBB')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F1F3F5')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story += [tbl,Spacer(1,8),Paragraph(
        'Durante el procedimiento se incorporaron los siguientes elementos de Registro Visual para documentar el estado observado del dispositivo y las operaciones realizadas. Se presentan en el mismo orden en que fueron incorporados. Las imágenes se muestran como vista previa; en los videos, cuando es técnicamente posible, se incluye un fotograma generado únicamente para facilitar su identificación.',body),Spacer(1,8)]
    for idx,r in enumerate(registros):
        story.append(Paragraph(f"{r.get('id_registro','')} · {html_lib.escape(r.get('tipo',''))}",h))
        thumb=_thumb_visual(r,root)
        if thumb:story.append(thumb);story.append(Spacer(1,5))
        filas=[
            ('Archivo',r.get('nombre_original','')),('Descripción',r.get('descripcion','')),
            ('Fecha/hora de incorporación',r.get('fecha_hora_incorporacion_local','')),
            ('Fecha/hora indicada por metadatos',r.get('fecha_hora_metadatos','') or 'No disponible'),
            ('Fuente de esa fecha',r.get('fuente_fecha_metadatos','') or 'No disponible'),
            ('Dispositivo informado en metadatos',(' '.join(x for x in [r.get('marca_dispositivo_metadatos',''),r.get('modelo_dispositivo_metadatos','')] if x)) or 'No disponible'),
            ('Duración',f"{r.get('duracion_segundos')} segundos" if r.get('duracion_segundos') not in ('',None) else 'No aplica / no disponible'),
            ('Dimensiones',r.get('dimensiones','') or 'No aplica / no disponible'),('SHA-256',r.get('sha256',''))
        ]
        t=Table([[Paragraph(f'<b>{html_lib.escape(k)}</b>',small),Paragraph(html_lib.escape(str(v)),small)] for k,v in filas],colWidths=[52*mm,120*mm])
        t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.3,colors.HexColor('#C0C0C0')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F7F7F7')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),4),('BOTTOMPADDING',(0,0),(-1,-1),4)]))
        story += [t,Spacer(1,8)]
        if idx < len(registros)-1:story.append(Spacer(1,4))
    story += [Spacer(1,8),Paragraph(
        '<b>Aclaración sobre metadatos.</b> Las fechas, horas, marca, modelo u otros datos consignados como metadatos se reproducen únicamente cuando estaban presentes y pudieron ser leídos del archivo incorporado. Esa información se documenta como dato contenido en el archivo y no constituye, por sí sola, una determinación sobre su autenticidad. La fecha/hora de incorporación, en cambio, corresponde al momento registrado por PreservarChat al incorporar el archivo.',body)]
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return out

def generar_manifiesto_integridad_pdf(root):
    root=Path(root);ficha=leer_ficha(root);datos=ficha.get('datos',{});regs=leer_registro_visual(root)
    recep=[];rp=root/'02_INTEGRIDAD'/'HASHES_DE_RECEPCION.json'
    if rp.exists():
        try:recep=json.loads(rp.read_text(encoding='utf-8'))
        except Exception:pass
    filas=[
        ('ID de caso',datos.get('id_caso','')),('ID de evidencia',datos.get('id_evidencia','')),('Contacto / Grupo Auditado',datos.get('contacto_grupo','')),('Número del contacto exportado',datos.get('numero_contacto','')),
        ('Período del chat',datos.get('periodo','')),('SHA-256 del registro del conjunto de archivos recibidos',ficha.get('sha256_conjunto_recibido','')),
        ('SHA-256 del manifiesto general',ficha.get('sha256_manifiesto',''))
    ]
    archivos=[]
    for r in recep:archivos.append({'id_archivo':r.get('id_archivo'),'nombre':r.get('nombre'),'tamano_bytes':r.get('tamano_bytes'),'sha256':r.get('sha256')})
    for r in regs:archivos.append({'id_archivo':r.get('id_registro'),'nombre':r.get('nombre_original'),'tamano_bytes':r.get('tamano_bytes'),'sha256':r.get('sha256')})
    out=root/'05_ACTAS'/'04_MANIFIESTO_DE_INTEGRIDAD.pdf'
    generar_pdf_documento(out,'MANIFIESTO DE INTEGRIDAD',filas,archivos,nota='Este manifiesto reúne los archivos recibidos como exportación de WhatsApp y, cuando existen, los elementos de Registro Visual complementario. Cada valor SHA-256 permite comprobar posteriormente si el contenido binario del archivo coincide con el documentado.')
    return out if out.exists() else None

def regenerar_documentacion_judicial(root):
    """Regenera documentación comprensible para profesionales no técnicos."""
    root=Path(root)
    ficha=leer_ficha(root)
    if not ficha:
        return

    datos=ficha.get('datos',{})
    recep=ficha.get('archivos_recibidos',[])
    regs=leer_registro_visual(root)
    hconjunto=ficha.get('sha256_conjunto_recibido','')
    hm=ficha.get('sha256_manifiesto','')

    dispositivo=f"{datos.get('marca','')} {datos.get('modelo','')}".strip() or 'No informado'

    # -----------------------------------------------------
    # ACTA DE PRESERVACIÓN
    # -----------------------------------------------------
    secciones=[
        ('1. Identificación del caso',[
            ('Número de caso',datos.get('id_caso','')),
            ('Identificación de evidencia',datos.get('id_evidencia','')),
            ('Fecha',datos.get('fecha','')),
            ('Hora',datos.get('hora','')),
            ('Zona horaria',datos.get('zona_horaria','')),
            ('Lugar',datos.get('lugar','')),
            ('Responsable',datos.get('responsable','')),
            ('Identificación / función',datos.get('identificacion_funcion','') or 'No informada'),
            ('Requirente / entregante',datos.get('requirente','')),
            ('Autorización / referencia',datos.get('autorizacion',''))
        ]),
        ('2. Identificación del dispositivo y de la conversación',[
            ('Dispositivo',dispositivo),
            ('IMEI',datos.get('imei','') or 'No informado'),
            ('Número de serie',datos.get('serie','') or 'No informado'),
            ('Número asociado a WhatsApp',datos.get('numero_whatsapp','')),
            ('Sistema operativo',datos.get('sistema_operativo','')),
            ('Versión de WhatsApp',datos.get('version_whatsapp','') or 'No informada'),
            ('Estado informado del dispositivo',datos.get('estado_dispositivo','') or 'No informado'),
            ('Contacto / Grupo Auditado',datos.get('contacto_grupo','')),('Número del contacto exportado',datos.get('numero_contacto','')),
            ('Período detectado en el chat',datos.get('periodo','') or 'No determinado'),
            ('Persona / profesional / organización que realiza la exportación',datos.get('persona_exporto','') or 'No informada'),
            ('Método informado de obtención',datos.get('metodo',''))
        ]),
        ('3. Recepción del material',[
            f"Se recibieron {len(recep)} archivo(s) relacionados con la exportación del chat de WhatsApp. "
            "Cada archivo fue identificado por su nombre, tamaño y valor SHA-256 antes de generar las copias de resguardo.",
            *[
                f"{r.get('id_archivo','')} — {r.get('nombre','')} — {r.get('tamano_bytes',0)} bytes — "
                f"SHA-256: {r.get('sha256','')}"
                for r in recep
            ]
        ]),
        ('4. Procedimiento de preservación',[
            "Luego de identificar los archivos recibidos, se generó una copia destinada a preservación y se comprobó que su contenido coincidiera con el archivo recibido.",
            "Posteriormente se creó una copia separada para consulta. Esa copia es la utilizada para visualizar la conversación y sus archivos asociados, manteniéndose separada la copia de preservación.",
            f"Como identificación del conjunto recibido se registró el valor SHA-256: {hconjunto}.",
            (f"Durante el procedimiento se incorporaron {len(regs)} elemento(s) de Registro Visual complementario."
             if regs else
             "No se incorporaron elementos de Registro Visual complementario al momento de generar esta acta.")
        ]),
        ('5. Resultado',[
            "Los archivos recibidos fueron identificados, preservados y verificados. "
            "Las copias de consulta coincidieron con los valores de integridad registrados para el material recibido.",
            ('Observaciones',datos.get('observaciones','') or 'Sin observaciones adicionales.')
        ])
    ]

    nota=(
        "La presente acta deja constancia de la recepción y preservación de los archivos incorporados al caso. "
        "Los valores hash permiten comprobar que el contenido digital no cambió desde el momento en que fueron calculados. "
        "Por sí solos no determinan quién escribió una conversación ni su autenticidad con anterioridad a la recepción."
    )

    generar_pdf_narrativo(
        root/'05_ACTAS'/'01_ACTA_DE_PRESERVACION.pdf',
        'ACTA DE PRESERVACIÓN DE CHAT EXPORTADO DE WHATSAPP',
        '',
        secciones,
        recep,
        nota
    )

    # -----------------------------------------------------
    # ACTA DE INTEGRIDAD - lenguaje sencillo
    # -----------------------------------------------------
    archivos_verificados=[
        {
            'id_archivo':r.get('id_archivo'),
            'nombre':r.get('nombre'),
            'tamano_bytes':r.get('tamano_bytes'),
            'sha256':r.get('sha256')
        }
        for r in recep
    ]
    archivos_verificados += [
        {
            'id_archivo':r.get('id_registro'),
            'nombre':r.get('nombre_original'),
            'tamano_bytes':r.get('tamano_bytes'),
            'sha256':r.get('sha256')
        }
        for r in regs
    ]

    sec_int=[
        ('1. Identificación del caso',[
            ('Número de caso',datos.get('id_caso','')),
            ('Identificación de evidencia',datos.get('id_evidencia','')),
            ('Contacto / Grupo Auditado',datos.get('contacto_grupo','')),
            ('Período detectado',datos.get('periodo','') or 'No determinado')
        ]),
        ('2. Objeto de la verificación',[
            "Se realizó una nueva comprobación de los archivos documentados en el expediente para determinar si su contenido se mantiene igual al que fue registrado al momento de la preservación.",
            "Para ello se volvió a calcular el valor SHA-256 de cada archivo y se lo comparó con el valor previamente registrado."
        ]),
        ('3. Material verificado',[
            f"Se verificaron los archivos de la exportación de WhatsApp y {len(regs)} elemento(s) de Registro Visual complementario.",
            f"SHA-256 registrado para el conjunto recibido: {hconjunto}.",
            f"SHA-256 del manifiesto del expediente: {hm}."
        ]),
        ('4. Resultado de la comprobación',[
            "Los archivos disponibles al momento de esta verificación coinciden con los valores de integridad registrados en el expediente.",
            "Una coincidencia significa que el contenido digital del archivo es el mismo que el identificado al momento de calcular su hash."
        ]),
        ('5. Alcance',[
            "Esta comprobación controla la integridad de los archivos. No determina por sí sola la identidad de las personas que participaron en una conversación ni la autenticidad histórica del contenido antes de su incorporación al expediente."
        ])
    ]

    generar_pdf_narrativo(
        root/'05_ACTAS'/'02_ACTA_DE_INTEGRIDAD.pdf',
        'ACTA DE VERIFICACIÓN DE INTEGRIDAD',
        '',
        sec_int,
        archivos_verificados,
        nota
    )

    generar_acta_registro_visual(root)
    generar_manifiesto_integridad_pdf(root)

    # Acta final del dispositivo: resumen profesional disponible siempre en ACTAS.
    sec_final_dispositivo=[
        ('1. Datos de identificación',[
            ('Caso / referencia',datos.get('id_caso','')),
            ('Fecha',datos.get('fecha','')),
            ('Hora',datos.get('hora','')),
            ('Zona horaria',datos.get('zona_horaria','')),
            ('Lugar',datos.get('lugar','')),
            ('Responsable',datos.get('responsable','')),
            ('Requirente / entregante',datos.get('requirente',''))
        ]),
        ('2. Dispositivo y conversación',[
            ('Dispositivo',f"{datos.get('marca','')} {datos.get('modelo','')}".strip() or 'No informado'),
            ('IMEI',datos.get('imei','') or 'No informado'),
            ('Número de serie',datos.get('serie','') or 'No informado'),
            ('Sistema operativo',datos.get('sistema_operativo','')),
            ('Versión de WhatsApp',datos.get('version_whatsapp','') or 'No informada'),
            ('Número asociado a WhatsApp',datos.get('numero_whatsapp','')),
            ('Contacto / Grupo Auditado',datos.get('contacto_grupo','')),
            ('Período detectado',datos.get('periodo','') or 'No determinado'),
            ('Persona / profesional / organización que realiza la exportación',datos.get('persona_exporto','') or 'No informada'),
            ('Método informado',datos.get('metodo','') or 'No informado'),
            ('Estado informado del dispositivo',datos.get('estado_dispositivo','') or 'No informado')
        ]),
        ('3. Material identificado',[
            f"Se documentaron {len(recep)} archivo(s) de la exportación de WhatsApp.",
            *[f"{r.get('id_archivo','')} — {r.get('nombre','')} — SHA-256: {r.get('sha256','')}" for r in recep]
        ]),
        ('4. Registro Visual',[
            (f"Se incorporaron {len(regs)} elemento(s) complementario(s)." if regs else "No se incorporó Registro Visual complementario."),
            *[
                f"{r.get('id_registro','')} — {r.get('tipo','')} — {r.get('nombre_original','')} — "
                f"Descripción: {r.get('descripcion','')} — SHA-256: {r.get('sha256','')}"
                for r in regs
            ]
        ])
    ]
    generar_pdf_narrativo(
        root/'05_ACTAS'/'05_ACTA_FINAL_DEL_DISPOSITIVO.pdf',
        'ACTA FINAL DEL DISPOSITIVO Y MATERIAL DOCUMENTADO',
        '',
        sec_final_dispositivo,
        None,
        'Este documento resume los datos informados del dispositivo, la conversación y el material digital documentado.'
    )

# ============================================================
# CREAR EXPEDIENTE
# ============================================================

def crear_expediente(fuentes, destino, datos):
    root = destino / f"{nombre_seguro(datos['id_caso'])}_{nombre_seguro(datos['id_evidencia'])}_PRESERVARCHAT"
    if root.exists():
        raise FileExistsError("Ya existe un expediente con el mismo ID.")

    carpetas = [
        "00_DATOS_DEL_CASO","01_ORIGINAL_NO_MODIFICAR","02_INTEGRIDAD",
        "03_COPIA_DE_TRABAJO","04_DOCUMENTACION_DEL_ORIGEN","05_ACTAS",
        "06_REGISTRO_DE_CUSTODIA","07_INFORME","08_BITACORA","09_INCIDENCIAS","10_REGISTRO_VISUAL"
    ]
    for n in carpetas:
        (root/n).mkdir(parents=True, exist_ok=True)
    asegurar_registro_visual(root)

    recepcion = []
    for i,src in enumerate(fuentes,start=1):
        aid = f"A{i:03d}"
        clas = clasificar_archivo(src)
        recepcion.append({
            "id_archivo":aid,
            "nombre":src.name,
            "ruta_fuente":str(src),
            "tamano_bytes":src.stat().st_size,
            "clasificacion":clas["clasificacion"],
            "motivo_clasificacion":clas["motivo"],
            "sha256":sha(src),
            "sha512":sha(src,"sha512"),
            "fecha_hora_local":ahora_local(),
            "fecha_hora_utc":ahora_utc()
        })

    guardar_json(root/"02_INTEGRIDAD"/"HASHES_DE_RECEPCION.json",recepcion)
    guardar_csv(root/"02_INTEGRIDAD"/"HASHES_DE_RECEPCION.csv",recepcion)

    hconjunto = hash_conjunto(recepcion)
    (root/"02_INTEGRIDAD"/"SHA256_DEL_CONJUNTO.txt").write_text(hconjunto+"\n",encoding="utf-8")

    manifiesto = []
    derivados = []

    for r,src in zip(recepcion,fuentes):
        aid = r["id_archivo"]
        nombre_guardado = f"{aid}__{src.name}"

        original = root/"01_ORIGINAL_NO_MODIFICAR"/nombre_guardado
        shutil.copy2(src,original)
        oh256 = sha(original)
        oh512 = sha(original,"sha512")

        if (oh256,oh512)!=(r["sha256"],r["sha512"]):
            registrar_incidencia(root,"CRITICA","HASH_RECEPCION_DIFERENTE",
                                  f"{src.name}: original preservado no coincide con recepción.")
            raise RuntimeError("INCIDENTE CRÍTICO: hash de recepción y original preservado no coinciden.")

        try:
            original.chmod(0o444)
        except Exception:
            pass

        copia = root/"03_COPIA_DE_TRABAJO"/nombre_guardado
        shutil.copy2(original,copia)
        ch256 = sha(copia)
        ch512 = sha(copia,"sha512")

        if (ch256,ch512)!=(oh256,oh512):
            registrar_incidencia(root,"CRITICA","HASH_COPIA_DIFERENTE",
                                  f"{src.name}: copia de trabajo no coincide.")
            raise RuntimeError("INCIDENTE CRÍTICO: copia de trabajo no coincidente.")

        manifiesto.extend([
            {
                "id_archivo":aid,"tipo":"ORIGINAL_PRESERVADO","clasificacion":r["clasificacion"],
                "ruta_relativa":str(original.relative_to(root)),"nombre_original":src.name,
                "tamano_bytes":original.stat().st_size,"sha256":oh256,"sha512":oh512
            },
            {
                "id_archivo":aid,"tipo":"COPIA_DE_TRABAJO","clasificacion":r["clasificacion"],
                "ruta_relativa":str(copia.relative_to(root)),"nombre_original":src.name,
                "tamano_bytes":copia.stat().st_size,"sha256":ch256,"sha512":ch512
            }
        ])

        if copia.suffix.lower()==".zip":
            try:
                out = root/"03_COPIA_DE_TRABAJO"/f"{aid}_CONTENIDO"
                out.mkdir(exist_ok=True)
                extraer_zip_seguro(copia,out)
                for p in out.rglob("*"):
                    if p.is_file():
                        derivados.append(p)
                        manifiesto.append({
                            "id_archivo":aid,"tipo":"DERIVADO_DESDE_COPIA",
                            "clasificacion":"CONTENIDO EXTRAIDO DESDE COPIA",
                            "ruta_relativa":str(p.relative_to(root)),
                            "nombre_original":p.name,
                            "tamano_bytes":p.stat().st_size,
                            "sha256":sha(p),"sha512":sha(p,"sha512")
                        })
            except Exception as e:
                registrar_incidencia(root,"ALTA","ERROR_ZIP",f"{src.name}: {e}")

    guardar_json(root/"02_INTEGRIDAD"/"MANIFIESTO.json",manifiesto)
    guardar_csv(root/"02_INTEGRIDAD"/"MANIFIESTO.csv",manifiesto)
    hm = sha(root/"02_INTEGRIDAD"/"MANIFIESTO.json")
    (root/"02_INTEGRIDAD"/"SHA256_MANIFIESTO.txt").write_text(hm+"\n",encoding="utf-8")

    chat = encontrar_chat_principal(root)
    mensajes = parsear_chat(chat) if chat else []
    periodo_auto = detectar_periodo_mensajes(mensajes)
    datos["periodo"] = periodo_auto["periodo"]

    try:
        ejecutado = Path(sys.executable if getattr(sys,"frozen",False) else __file__).resolve()
        hash_programa = sha(ejecutado)
    except Exception:
        ejecutado = Path("NO_DISPONIBLE")
        hash_programa = ""

    guardar_json(root/"00_DATOS_DEL_CASO"/"IDENTIFICACION_DEL_SISTEMA.json",{
        "producto":APP,"version":VERSION,"archivo_ejecutado":str(ejecutado),
        "sha256_programa":hash_programa,
        "fecha_hora_local":ahora_local(),"fecha_hora_utc":ahora_utc()
    })

    guardar_json(root/"00_DATOS_DEL_CASO"/"FICHA_DEL_CASO.json",{
        "producto":APP,"version":VERSION,"datos":datos,
        "periodo_detectado_automaticamente":periodo_auto,
        "chat_principal_copia_trabajo":str(chat.relative_to(root)) if chat else "",
        "cantidad_archivos_recibidos":len(fuentes),
        "sha256_conjunto_recibido":hconjunto,
        "sha256_manifiesto":hm,
        "archivos_recibidos":recepcion
    })

    # Bitácora
    eventos=[]
    previo=""
    pasos=[
        ("RECEPCION","Recepción e identificación de los archivos entregados."),
        ("HASH_RECEPCION","Cálculo SHA-256 y SHA-512 antes de copiar."),
        ("PRESERVACION","Copia a 01_ORIGINAL_NO_MODIFICAR y verificación de hashes."),
        ("COPIA_TRABAJO","Creación de copias verificadas en 03_COPIA_DE_TRABAJO."),
        ("EXTRACCION","Extracción de ZIP únicamente desde copia de trabajo."),
        ("PERIODO_CHAT",f"Detección automática del período: {periodo_auto['periodo'] or 'no detectado'}."),
        ("MANIFIESTO","Generación del manifiesto de integridad y hash del conjunto."),
        ("DOCUMENTACION","Generación de actas, informe, custodia y registros.")
    ]
    for n,(tipo,texto) in enumerate(pasos,1):
        e={
            "numero":n,"fecha_hora_local":ahora_local(),"fecha_hora_utc":ahora_utc(),
            "tipo":tipo,"responsable":datos["responsable"],"descripcion":texto,
            "hash_anterior":previo
        }
        e["hash_evento"]=hashlib.sha256(
            json.dumps(e,ensure_ascii=False,sort_keys=True).encode("utf-8")
        ).hexdigest()
        eventos.append(e)
        previo=e["hash_evento"]

    guardar_json(root/"08_BITACORA"/"BITACORA.json",eventos)
    guardar_csv(root/"08_BITACORA"/"BITACORA.csv",eventos)

    custodia=[{
        "numero":1,"fecha_hora_local":ahora_local(),"fecha_hora_utc":ahora_utc(),
        "accion":"INCORPORACION","entrega":datos["requirente"],"recibe":datos["responsable"],
        "cantidad_archivos":len(fuentes),"sha256_conjunto":hconjunto,
        "observaciones":"Originales separados de copias de trabajo."
    }]
    guardar_json(root/"06_REGISTRO_DE_CUSTODIA"/"REGISTRO_DE_CUSTODIA.json",custodia)
    guardar_csv(root/"06_REGISTRO_DE_CUSTODIA"/"REGISTRO_DE_CUSTODIA.csv",custodia)

    listado="<ul>"+"".join(
        f"<li><b>{esc(r['id_archivo'])}</b> — {esc(r['nombre'])} — "
        f"{esc(r['clasificacion'])} — {r['tamano_bytes']} bytes — SHA-256: {esc(r['sha256'])}</li>"
        for r in recepcion
    )+"</ul>"

    filas=[
        ("ID de caso",datos["id_caso"]),
        ("ID de evidencia",datos["id_evidencia"]),
        ("Responsable",datos["responsable"]),
        ("Identificación / función",datos["identificacion_funcion"]),
        ("Requirente / solicitante / entregante",datos["requirente"]),
        ("Autorización / consentimiento / referencia",datos["autorizacion"]),
        ("Lugar",datos["lugar"]),
        ("Fecha declarada",datos["fecha"]),
        ("Hora declarada",datos["hora"]),
        ("Zona horaria",datos["zona_horaria"]),
        ("Marca del dispositivo",datos["marca"]),
        ("Modelo",datos["modelo"]),
        ("IMEI",datos["imei"]),
        ("Número de serie",datos["serie"]),
        ("Número asociado a WhatsApp",datos["numero_whatsapp"]),
        ("Sistema operativo",datos["sistema_operativo"]),
        ("Versión de WhatsApp",datos["version_whatsapp"]),
        ("Estado del dispositivo al inicio",datos["estado_dispositivo"]),
        ("Contacto / grupo",datos["contacto_grupo"]),
        ("Período detectado automáticamente",datos["periodo"]),
        ("Incluye multimedia",datos["incluye_multimedia"]),
        ("Método de obtención",datos["metodo"]),
        ("Persona que realizó la exportación",datos["persona_exporto"]),
        ("Cantidad de archivos recibidos",len(fuentes)),
        ("SHA-256 del conjunto recibido",hconjunto),
        ("SHA-256 del manifiesto",hm),
        ("Observaciones",datos["observaciones"])
    ]

    guardar_html(
        root/"05_ACTAS"/"01_ACTA_DE_PRESERVACION.html",
        "Acta de preservación",
        "<h1>ACTA DE PRESERVACIÓN Y RESGUARDO DE CHAT DE WHATSAPP</h1>"+
        tabla(filas)+"<h2>Archivos recibidos</h2>"+listado+
        '<div class="nota"><b>Alcance:</b> se documenta la integridad desde el momento de recepción. '
        'El procedimiento no determina por sí solo autenticidad, identidad, autoría o atribución.</div>'
    )

    guardar_html(
        root/"05_ACTAS"/"02_ACTA_DE_INTEGRIDAD.html",
        "Acta de integridad",
        "<h1>ACTA DE VERIFICACIÓN DE INTEGRIDAD</h1>"+
        tabla([
            ("Archivos fuente recibidos",len(fuentes)),
            ("SHA-256 del conjunto",hconjunto),
            ("SHA-256 del manifiesto",hm),
            ("Resultado","TODOS LOS ARCHIVOS FUENTE Y SUS COPIAS COINCIDEN"),
            ("Hora UTC",ahora_utc())
        ])+listado
    )

    guardar_html(
        root/"07_INFORME"/"INFORME_DE_PRESERVACION.html",
        "Informe de preservación",
        "<h1>INFORME DE PRESERVACIÓN Y RESGUARDO</h1>"+
        tabla(filas)+"<h2>Archivos que integraron la recepción</h2>"+listado
    )

    nota_alcance=(
        "Este documento describe cómo se recibió, preservó y verificó la exportación. "
        "Los hashes permiten comprobar que los archivos documentados no cambiaron desde su cálculo. "
        "Por sí solos no acreditan identidad, autoría ni autenticidad histórica del contenido anterior a la recepción."
    )

    sec_preservacion=[
        ('1. Identificación del caso',[
            ('ID de caso',datos['id_caso']),('ID de evidencia',datos['id_evidencia']),
            ('Responsable del procedimiento',datos['responsable']),('Requirente / entregante',datos['requirente']),
            ('Lugar',datos['lugar']),('Fecha y hora declaradas',f"{datos['fecha']} {datos['hora']} {datos['zona_horaria']}")
        ]),
        ('2. Origen declarado del material',[
            ('Contacto / Grupo Auditado',datos['contacto_grupo']),('Número del contacto exportado',datos.get('numero_contacto','')),('Teléfono de la cuenta de WhatsApp de origen',datos['numero_whatsapp']),
            ('Dispositivo',f"{datos['marca']} {datos['modelo']}".strip()),('IMEI',datos['imei']),('Número de serie',datos['serie']),
            ('Sistema operativo',datos['sistema_operativo']),('Versión de WhatsApp',datos['version_whatsapp']),
            ('Persona / profesional / organización que realiza la exportación',datos['persona_exporto']),('Método informado',datos['metodo']),
            ('Autorización / referencia',datos['autorizacion'])
        ]),
        ('3. Qué se hizo, en orden cronológico',[
            'Primero se identificaron los archivos exactamente como fueron recibidos y se calculó SHA-256 y SHA-512 antes de copiarlos.',
            'Luego se creó una copia preservada en la carpeta ORIGINAL_NO_MODIFICAR y se comprobó que sus hashes coincidieran con los obtenidos en recepción.',
            'A continuación se generó una copia de trabajo separada. Esa copia fue nuevamente verificada por hash y es la única utilizada para lectura, visualización y extracción de contenido.',
            'Cuando el material recibido era un ZIP, su contenido se extrajo únicamente desde la copia de trabajo. El original preservado no se utilizó para esa operación.',
            f"Finalmente, PreservarChat detectó automáticamente el período del chat como {datos['periodo'] or 'no determinado'} y generó manifiestos, bitácora, actas e informe."
        ]),
        ('4. Resultado de la preservación',[
            ('Cantidad de archivos recibidos',len(fuentes)),('SHA-256 del conjunto',hconjunto),('SHA-256 del manifiesto',hm),
            ('Resultado','Integridad verificada: recepción, original preservado y copia de trabajo coinciden.')
        ]),
        ('5. Observaciones',datos['observaciones'] or 'Sin observaciones adicionales.')
    ]
    generar_pdf_narrativo(
        root/'05_ACTAS'/'01_ACTA_DE_PRESERVACION.pdf','ACTA DE PRESERVACIÓN Y RESGUARDO',
        'Documento destinado a dejar constancia, en lenguaje claro, de la recepción, preservación y verificación de una exportación de WhatsApp.',
        sec_preservacion,recepcion,nota_alcance
    )

    sec_integridad=[
        ('1. Qué se verificó',[
            'Se recalculó el SHA-256 de los archivos documentados y se comparó con los valores registrados durante la recepción y preservación.',
            'La comprobación alcanza a los archivos originales preservados y a las copias de trabajo registradas en el manifiesto.'
        ]),
        ('2. Identificación',[
            ('ID de caso',datos['id_caso']),('ID de evidencia',datos['id_evidencia']),('Contacto / Grupo Auditado',datos['contacto_grupo']),('Período',datos['periodo'])
        ]),
        ('3. Resultado',[
            ('SHA-256 del conjunto',hconjunto),('SHA-256 del manifiesto',hm),
            ('Conclusión','Los archivos verificados coinciden con los valores hash documentados. No se detectaron diferencias durante esta comprobación.')
        ]),
        ('4. Cómo interpretar esta acta',[
            'Un resultado coincidente permite comprobar que los archivos verificados conservan el mismo contenido binario que el documentado al momento del hashing.',
            'Este control no reemplaza la valoración jurídica ni acredita, por sí mismo, quién escribió cada mensaje.'
        ])
    ]
    generar_pdf_narrativo(
        root/'05_ACTAS'/'02_ACTA_DE_INTEGRIDAD.pdf','ACTA DE VERIFICACIÓN DE INTEGRIDAD',
        'Comprobación de integridad del material preservado y de sus copias de trabajo.',
        sec_integridad,recepcion,nota_alcance
    )

    sec_informe=[
        ('Resumen del caso',[
            ('Caso',datos['id_caso']),('Evidencia',datos['id_evidencia']),('Contacto / Grupo Auditado',datos['contacto_grupo']),
            ('Período detectado',datos['periodo']),('Responsable',datos['responsable'])
        ]),
        ('Procedimiento realizado',[
            'El material fue recibido, hasheado antes de copiar, preservado en un área separada, duplicado para trabajo y nuevamente verificado.',
            'Toda lectura posterior y la visualización de multimedia se realiza desde COPIA_DE_TRABAJO. ORIGINAL_NO_MODIFICAR queda reservado para preservación.',
            'Se generaron manifiestos, bitácora, registro de custodia, actas y controles de integridad.'
        ]),
        ('Resultado',[
            ('Integridad','VERIFICADA'),('SHA-256 del conjunto',hconjunto),('Archivos derivados registrados',len(derivados))
        ])
    ]
    generar_pdf_narrativo(root/'07_INFORME'/'INFORME_DE_PRESERVACION.pdf','INFORME DE PRESERVACIÓN Y RESGUARDO',
                           'Síntesis del procedimiento realizado sobre la exportación incorporada al expediente.',sec_informe,recepcion,nota_alcance)
    generar_pdf_custodia(root)

    estado={
        "caso":datos["id_caso"],"evidencia":datos["id_evidencia"],
        "contacto_grupo":datos["contacto_grupo"],"periodo":datos["periodo"],
        "archivos_recibidos":len(fuentes),"archivos_derivados":len(derivados),
        "sha256_conjunto":hconjunto,"integridad":"VERIFICADA",
        "fecha_hora_utc":ahora_utc()
    }
    guardar_json(root/"ESTADO_DEL_EXPEDIENTE.json",estado)
    regenerar_documentacion_judicial(root)

    return root,estado,recepcion,periodo_auto

# ============================================================
# VERIFICACIÓN / CASOS
# ============================================================

def verificar_bitacora_encadenada(root):
    p=Path(root)/'08_BITACORA'/'BITACORA.json'
    if not p.exists():
        return False,'Bitácora no encontrada.'
    try:eventos=json.loads(p.read_text(encoding='utf-8'))
    except Exception as e:return False,f'Bitácora ilegible: {e}'
    previo=''
    for pos,e in enumerate(eventos,1):
        esperado=e.get('hash_evento','')
        if e.get('hash_anterior','') != previo:
            return False,f'Cadena interrumpida en evento {pos}.'
        base=dict(e);base.pop('hash_evento',None)
        actual=hashlib.sha256(json.dumps(base,ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest()
        if actual != esperado:
            return False,f'Hash de evento inválido en evento {pos}.'
        previo=esperado
    return True,f'{len(eventos)} evento(s) verificados.'

def verificar_expediente(root, guardar_reporte=True):
    root=Path(root)
    p=root/"02_INTEGRIDAD"/"MANIFIESTO.json"
    if not p.exists():
        raise FileNotFoundError("No se encontró el manifiesto del expediente.")

    mani=json.loads(p.read_text(encoding="utf-8"))
    resultados=[]

    # Verificar que el propio manifiesto conserve el hash registrado.
    hash_actual_mani=sha(p)
    hp=root/'02_INTEGRIDAD'/'SHA256_MANIFIESTO.txt'
    hash_reg_mani=hp.read_text(encoding='utf-8').strip() if hp.exists() else ''
    mani_ok=bool(hash_reg_mani) and hash_actual_mani==hash_reg_mani
    resultados.append({
        'archivo':'02_INTEGRIDAD/MANIFIESTO.json','tipo':'CONTROL_MANIFIESTO',
        'estado':'INTEGRO' if mani_ok else 'MODIFICADO'
    })

    for item in mani:
        ruta=(root/item["ruta_relativa"]).resolve()
        if not dentro_de(ruta,root):
            estado='RUTA_INVALIDA'
        elif not ruta.exists():
            estado="FALTANTE"
        else:
            estado="INTEGRO" if sha(ruta)==item["sha256"] else "MODIFICADO"

        resultados.append({
            "archivo":item["ruta_relativa"],
            "tipo":item.get("tipo",""),
            "estado":estado
        })

    bit_ok,bit_detalle=verificar_bitacora_encadenada(root)
    resultados.append({
        'archivo':'08_BITACORA/BITACORA.json','tipo':'CADENA_BITACORA',
        'estado':'INTEGRO' if bit_ok else 'MODIFICADO'
    })

    ok=all(x["estado"]=="INTEGRO" for x in resultados)
    reporte={
        "fecha_hora_local":ahora_local(),
        "fecha_hora_utc":ahora_utc(),
        "resultado":"INTEGRIDAD VERIFICADA" if ok else "SE DETECTARON INCIDENCIAS",
        "manifiesto_sha256_actual":hash_actual_mani,
        "manifiesto_sha256_registrado":hash_reg_mani,
        "bitacora":bit_detalle,
        "archivos":resultados
    }

    if guardar_reporte:
        guardar_json(
            root/"02_INTEGRIDAD"/("VERIFICACION_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".json"),
            reporte
        )
    return reporte

def leer_ficha(root):
    p=root/"00_DATOS_DEL_CASO"/"FICHA_DEL_CASO.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def buscar_expedientes(base):
    resultados=[]
    base=Path(base)
    if not base.is_dir():
        return resultados

    # Si la propia carpeta seleccionada ya es un caso, incluirla.
    candidatos=[]
    if base.name.endswith("_PRESERVARCHAT") or base.name.endswith("_PRESERVACHAT"):
        candidatos.append(base)
    candidatos.extend(p for p in base.rglob("*_PRESERVARCHAT") if p.is_dir())
    candidatos.extend(p for p in base.rglob("*_PRESERVACHAT") if p.is_dir())

    vistos=set()
    for p in candidatos:
        key=str(p.resolve()).lower()
        if key in vistos:
            continue
        vistos.add(key)

        if not (p/"02_INTEGRIDAD"/"MANIFIESTO.json").exists():
            continue
        if not (p/"03_COPIA_DE_TRABAJO").is_dir():
            continue

        ficha=leer_ficha(p)
        datos=ficha.get("datos",{})
        ep=p/"ESTADO_DEL_EXPEDIENTE.json"
        estado={}
        if ep.exists():
            try:
                estado=json.loads(ep.read_text(encoding="utf-8"))
            except Exception:
                pass

        resultados.append({
            "ruta":p,
            "caso":datos.get("id_caso",estado.get("caso","")),
            "evidencia":datos.get("id_evidencia",estado.get("evidencia","")),
            "contacto":datos.get("contacto_grupo",estado.get("contacto_grupo","")),
            "periodo":datos.get("periodo",estado.get("periodo","")),
            "integridad":estado.get("integridad",""),
            "trabajo":p/"03_COPIA_DE_TRABAJO"
        })

    resultados.sort(key=lambda x:(x["caso"],x["evidencia"]))
    return resultados

# ============================================================
# ENTREGA
# ============================================================

def generar_entrega(root,destino_base):
    """
    Entrega oficial:
      ENTREGA CASO ....zip
        01 CHAT EXPORTADO.zip
            archivos recibidos + HASHES CHAT.txt
        02 REGISTRO VISUAL.zip
            RV-001..., RV-002... + HASHES REGISTRO VISUAL.txt

      Fuera del ZIP oficial:
        ACTA FINAL DE ENTREGA.pdf
        SHA-256 del ZIP oficial en TXT
    """
    root=Path(root)
    destino_base=Path(destino_base)
    if not destino_base.is_dir():
        raise ValueError("La carpeta de destino de entregas no es válida.")

    rep=verificar_expediente(root,guardar_reporte=True)
    if rep["resultado"]!="INTEGRIDAD VERIFICADA":
        raise RuntimeError(
            "No se puede generar la entrega porque existen archivos faltantes o modificados. "
            "Revise la pestaña Verificar."
        )

    ficha=leer_ficha(root)
    datos=ficha.get("datos",{})
    regs=leer_registro_visual(root)
    mani=json.loads((root/"02_INTEGRIDAD"/"MANIFIESTO.json").read_text(encoding="utf-8"))
    originales=[x for x in mani if x.get("tipo")=="ORIGINAL_PRESERVADO"]
    if not originales:
        raise RuntimeError("No se localizaron los archivos recibidos que deben integrar la entrega.")

    caso=nombre_seguro(datos.get("id_caso","CASO")).replace("_"," ")
    base_base=f"Entrega caso {caso}"
    base_nombre=base_base
    n=2
    while (destino_base/(base_nombre+".zip")).exists() or (destino_base/(base_nombre+" ACTA FINAL DE ENTREGA.pdf")).exists():
        base_nombre=f"{base_base} ({n})"
        n+=1
    temp=destino_base/(base_nombre+" TEMP")
    if temp.exists():
        shutil.rmtree(temp)
    temp.mkdir(parents=True)

    # -----------------------------------------------------
    # 01 CHAT EXPORTADO.zip
    # -----------------------------------------------------
    chat_temp=temp/"CHAT"
    chat_temp.mkdir()
    chat_items=[]
    for item in originales:
        src=root/item["ruta_relativa"]
        esperado=item["sha256"]
        if sha(src)!=esperado:
            raise RuntimeError(f"El archivo {item.get('nombre_original',src.name)} no coincide con el hash registrado.")

        nombre=item.get("nombre_original",src.name)
        dst=chat_temp/nombre
        if dst.exists():
            dst=chat_temp/f"{item.get('id_archivo','ARCHIVO')} {nombre}"
        shutil.copyfile(src,dst)
        h=sha(dst)
        if h!=esperado:
            raise RuntimeError(f"La copia para entrega no coincide: {dst.name}")
        chat_items.append({
            "id":item.get("id_archivo",""),
            "archivo":dst.name,
            "tamano_bytes":dst.stat().st_size,
            "sha256":h
        })

    chat_hash_lines=[
        "ARCHIVOS DE LA EXPORTACION DE WHATSAPP",
        "======================================",
        "",
        f"Caso / referencia: {datos.get('id_caso','')}",
        f"Contacto / grupo: {datos.get('contacto_grupo','')}",
        f"Período detectado: {datos.get('periodo','') or 'No determinado'}",
        ""
    ]
    for x in chat_items:
        chat_hash_lines += [
            f"ID: {x['id']}",
            f"Archivo: {x['archivo']}",
            f"Tamaño: {x['tamano_bytes']} bytes",
            f"SHA-256: {x['sha256']}",
            ""
        ]
    (chat_temp/"HASHES CHAT.txt").write_text("\n".join(chat_hash_lines),encoding="utf-8")

    chat_zip=temp/"01 CHAT EXPORTADO.zip"
    with zipfile.ZipFile(chat_zip,"w",zipfile.ZIP_DEFLATED) as z:
        for p in chat_temp.iterdir():
            if p.is_file():
                z.write(p,arcname=p.name)
    hash_chat_zip=sha(chat_zip)
    shutil.rmtree(chat_temp)

    # -----------------------------------------------------
    # 02 REGISTRO VISUAL.zip
    # Individualización correlativa y descripción en TXT.
    # -----------------------------------------------------
    visual_items=[]
    rv_zip=None
    hash_rv_zip=""
    if regs:
        rv_temp=temp/"REGISTRO VISUAL"
        rv_temp.mkdir()
        for n,r in enumerate(regs,1):
            src=root/r["ruta_preservada"]
            esperado=r["sha256"]
            if sha(src)!=esperado:
                raise RuntimeError(f"El Registro Visual {r.get('id_registro','')} no coincide con el hash registrado.")

            ext=Path(r.get("nombre_original","")).suffix
            ident=r.get("id_registro") or f"RV-{n:03d}"
            nombre=f"{ident} - {r.get('nombre_original','archivo'+ext)}"
            dst=rv_temp/nombre
            shutil.copyfile(src,dst)
            h=sha(dst)
            if h!=esperado:
                raise RuntimeError(f"La copia del Registro Visual no coincide: {dst.name}")

            visual_items.append({
                "orden":n,
                "id":ident,
                "tipo":r.get("tipo","Archivo"),
                "archivo":dst.name,
                "nombre_original":r.get("nombre_original",""),
                "descripcion":r.get("descripcion","") or "Sin descripción",
                "fecha_incorporacion":r.get("fecha_hora_incorporacion_local",""),
                "fecha_metadatos":r.get("fecha_hora_metadatos","") or "No disponible",
                "tamano_bytes":dst.stat().st_size,
                "sha256":h
            })

        rv_hash_lines=[
            "REGISTRO VISUAL",
            "===============",
            "",
            f"Caso / referencia: {datos.get('id_caso','')}",
            "Los elementos se detallan en el mismo orden en que fueron incorporados.",
            ""
        ]
        for x in visual_items:
            rv_hash_lines += [
                f"{x['orden']}. {x['id']}",
                f"Tipo: {x['tipo']}",
                f"Archivo: {x['archivo']}",
                f"Nombre original: {x['nombre_original']}",
                f"Descripción: {x['descripcion']}",
                f"Fecha/hora de incorporación: {x['fecha_incorporacion']}",
                f"Fecha/hora informada por metadatos: {x['fecha_metadatos']}",
                f"Tamaño: {x['tamano_bytes']} bytes",
                f"SHA-256: {x['sha256']}",
                ""
            ]
        (rv_temp/"HASHES REGISTRO VISUAL.txt").write_text("\n".join(rv_hash_lines),encoding="utf-8")

        rv_zip=temp/"02 REGISTRO VISUAL.zip"
        with zipfile.ZipFile(rv_zip,"w",zipfile.ZIP_DEFLATED) as z:
            for p in rv_temp.iterdir():
                if p.is_file():
                    z.write(p,arcname=p.name)
        hash_rv_zip=sha(rv_zip)
        shutil.rmtree(rv_temp)

    # -----------------------------------------------------
    # ZIP OFICIAL: se cierra antes de redactar el Acta Final para que
    # el acta pueda identificar primero el contenedor principal y su hash.
    # -----------------------------------------------------
    zip_final=destino_base/(base_nombre+".zip")
    with zipfile.ZipFile(zip_final,"w",zipfile.ZIP_DEFLATED) as z:
        z.write(chat_zip,arcname=chat_zip.name)
        if rv_zip is not None:
            z.write(rv_zip,arcname=rv_zip.name)
    zip_hash=sha(zip_final)

    # -----------------------------------------------------
    # 03 ACTA FINAL DE ENTREGA
    # -----------------------------------------------------
    dispositivo=f"{datos.get('marca','')} {datos.get('modelo','')}".strip() or "No informado"

    # ACTA FINAL: redacción narrativa, pensada para abogados, fiscalías y juzgados.
    acta=destino_base/(base_nombre+" ACTA FINAL DE ENTREGA.pdf")
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle
    except Exception as e:
        raise RuntimeError(f"No se pudo generar el Acta Final: {e}")

    styles=getSampleStyleSheet()
    titulo=ParagraphStyle('tit',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=16,leading=20,alignment=TA_CENTER,spaceAfter=14)
    subt=ParagraphStyle('sub',parent=styles['Heading2'],fontName='Helvetica-Bold',fontSize=11.5,leading=14,spaceBefore=10,spaceAfter=6)
    cuerpo=ParagraphStyle('cuerpo',parent=styles['BodyText'],fontSize=9.7,leading=14,spaceAfter=7)
    chico=ParagraphStyle('chico',parent=styles['BodyText'],fontSize=8.2,leading=11)
    hashst=ParagraphStyle('hash',parent=chico,fontName='Courier',fontSize=7,leading=9)

    def esc(v):
        return html_lib.escape(str(v or ''))

    def valor(v):
        return str(v or '').strip()

    def fila_si(etiqueta,valor_campo):
        v=valor(valor_campo)
        return [Paragraph(f'<b>{esc(etiqueta)}</b>',chico),Paragraph(esc(v),chico)] if v else None

    def pie(canvas,doc):
        canvas.saveState()
        w,_=A4
        canvas.setStrokeColor(colors.HexColor('#D0D0D0'))
        canvas.line(18*mm,13*mm,w-18*mm,13*mm)
        canvas.setFont('Helvetica',7.5)
        canvas.setFillColor(colors.HexColor('#666666'))
        canvas.drawString(18*mm,9*mm,f'PreservarChat versión {VERSION} · eelciberseguridad@gmail.com')
        canvas.drawRightString(w-18*mm,9*mm,f'Página {doc.page}')
        canvas.restoreState()

    doc=SimpleDocTemplate(str(acta),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=17*mm,bottomMargin=19*mm)
    story=[Paragraph('ACTA FINAL DE ENTREGA DE DOCUMENTACIÓN DIGITAL',titulo)]

    cuenta=valor(datos.get('titular_whatsapp'))
    fecha=valor(datos.get('fecha'))
    hora=valor(datos.get('hora'))
    contacto=valor(datos.get('contacto_grupo'))
    numero_contacto=valor(datos.get('numero_contacto'))
    periodo=valor(datos.get('periodo'))
    solicitante=valor(datos.get('requirente'))

    # 1. Descripción narrativa del procedimiento. Las tablas de síntesis se dejan para el final.
    story += [Paragraph('Descripción del procedimiento',subt)]

    fecha_disp=valor(datos.get('fecha'))
    hora_disp=valor(datos.get('hora'))
    marca_disp=valor(datos.get('marca'))
    modelo_disp=valor(datos.get('modelo'))
    so_disp=valor(datos.get('sistema_operativo'))
    imei_disp=valor(datos.get('imei'))
    ver_wa=valor(datos.get('version_whatsapp'))
    inicio_disp=[]
    if fecha_disp: inicio_disp.append(f"En fecha <b>{esc(fecha_disp)}</b>")
    if hora_disp: inicio_disp.append(f"siendo las <b>{esc(hora_disp)}</b> horas")
    texto_disp=', '.join(inicio_disp)
    if texto_disp: texto_disp += ', '
    texto_disp += 'se realizó la exportación desde el dispositivo auditado'
    nombre_disp=' '.join(x for x in [marca_disp,modelo_disp] if x).strip()
    if nombre_disp: texto_disp += f" <b>{esc(nombre_disp)}</b>"
    if so_disp: texto_disp += f", con sistema operativo <b>{esc(so_disp)}</b>"
    if imei_disp: texto_disp += f", IMEI <b>{esc(imei_disp)}</b>"
    if ver_wa: texto_disp += f" y versión de WhatsApp <b>{esc(ver_wa)}</b>"
    texto_disp += '.'
    story += [Paragraph(texto_disp,cuerpo)]

    intro="La conversación exportada corresponde"
    if contacto:
        intro += f" al contacto / grupo agendado como <b>{esc(contacto)}</b>"
    else:
        intro += " al chat identificado en los datos registrados"
    if numero_contacto:
        intro += f", asociado al N° de teléfono <b>{esc(numero_contacto)}</b>"
    intro += "."
    if periodo:
        if ' al ' in periodo:
            desde,hasta=periodo.split(' al ',1)
            intro += f" El período de la conversación comprende desde el <b>{esc(desde)}</b> al <b>{esc(hasta)}</b>."
        else:
            intro += f" El período de la conversación comprende <b>{esc(periodo)}</b>."
    story += [Paragraph(intro,cuerpo)]

    if cuenta:
        t=f"La conversación fue exportada desde la cuenta de WhatsApp perteneciente a <b>{esc(cuenta)}</b>"
        if valor(datos.get('numero_whatsapp')):
            t+=f", asociada al número <b>{esc(datos.get('numero_whatsapp'))}</b>"
        t+="."
        story += [Paragraph(t,cuerpo)]

    if solicitante:
        story += [Paragraph(
            f"La preservación y documentación digital fue realizada a solicitud de <b>{esc(solicitante)}</b>.",
            cuerpo
        )]

    story += [Paragraph('Origen y método de exportación',subt)]
    metodo=(
        "Según el método informado y documentado en este procedimiento, la exportación fue realizada mediante la función nativa "
        "<b>“Exportar chat”</b> incluida en la propia aplicación WhatsApp, sin utilización de aplicaciones de terceros, APIs, "
        "servicios externos, conexiones adicionales ni herramientas de extracción ajenas a WhatsApp. "
        "<b>PreservarChat no se conecta a WhatsApp, no accede a sus servidores, no utiliza la API de WhatsApp y no interviene "
        "en la generación de la exportación.</b> Su actuación comienza una vez que los archivos exportados son incorporados "
        "al sistema, a efectos de preservarlos, identificarlos, calcular sus valores hash, documentarlos y organizar su entrega."
    )
    story += [Paragraph(metodo,cuerpo)]

    # 2. Explicación ordenada de la entrega, todavía en forma narrativa.
    story += [Paragraph('Contenido de la entrega',subt)]
    cantidad_contenedores = 1 + (1 if visual_items else 0)
    palabra_contenedores = "archivo" if cantidad_contenedores == 1 else "archivos"
    palabra_chat = "archivo" if len(chat_items) == 1 else "archivos"
    story += [Paragraph(
        f"Para su entrega se generó el archivo <b>{esc(base_nombre)}.zip — SHA-256: "
        f"<font name='Courier'>{esc(zip_hash)}</font></b>. "
        f"Este archivo constituye el contenedor final de entrega y reúne <b>{cantidad_contenedores} {palabra_contenedores}</b>, "
        "cada uno identificado mediante su correspondiente valor SHA-256.",
        cuerpo
    )]

    story += [Paragraph(
        f"El archivo <b>01 CHAT EXPORTADO.zip — SHA-256: <font name='Courier'>{esc(hash_chat_zip)}</font></b> "
        f"contiene <b>{len(chat_items)} {palabra_chat}</b> obtenidos de la exportación de la conversación de WhatsApp. "
        "Cada archivo queda individualizado por su nombre y por su correspondiente valor SHA-256.",
        cuerpo
    )]

    if visual_items:
        palabra_visual = "elemento" if len(visual_items) == 1 else "elementos"
        story += [Paragraph(
            f"El archivo <b>02 REGISTRO VISUAL.zip — SHA-256: <font name='Courier'>{esc(hash_rv_zip)}</font></b> "
            f"reúne el material de Registro Visual complementario incorporado al procedimiento y contiene "
            f"<b>{len(visual_items)} {palabra_visual}</b>, individualizados por nombre, descripción y SHA-256.",
            cuerpo
        )]

    story += [Paragraph('Responsable de la exportación',subt)]
    exportador=valor(datos.get('persona_exporto'))
    info_exportador=[]
    if exportador:
        info_exportador.append(f"La exportación fue realizada por <b>{esc(exportador)}</b>.")
    if valor(datos.get('exportador_direccion')):
        info_exportador.append(f"Domicilio / dirección: <b>{esc(datos.get('exportador_direccion'))}</b>.")
    if valor(datos.get('exportador_localidad')):
        info_exportador.append(f"Localidad / jurisdicción: <b>{esc(datos.get('exportador_localidad'))}</b>.")
    if valor(datos.get('exportador_telefono')):
        info_exportador.append(f"Teléfono de contacto: <b>{esc(datos.get('exportador_telefono'))}</b>.")
    if valor(datos.get('exportador_email')):
        info_exportador.append(f"Correo electrónico: <b>{esc(datos.get('exportador_email'))}</b>.")
    if info_exportador:
        story += [Paragraph(' '.join(info_exportador),cuerpo)]

    story += [Paragraph(
        "El <b>ACTA FINAL DE ENTREGA</b> se genera como documento independiente del archivo ZIP de entrega, "
        "permitiendo su consulta, impresión o presentación sin necesidad de abrir ni modificar el contenedor digital. "
        "Su eventual firma podrá realizarse posteriormente por el mecanismo que corresponda.",
        cuerpo
    )]

    story += [Paragraph(
        "Los valores SHA-256 consignados permiten comparar posteriormente los archivos recibidos con los aquí documentados "
        "y advertir cualquier modificación de su contenido digital.",
        cuerpo
    )]

    # 3. Resumen técnico al final: primero dispositivo, luego conversación y finalmente archivos creados.
    story += [Spacer(1,8), Paragraph('Resumen de datos',subt)]

    story += [Paragraph('Dispositivo auditado',subt)]
    datos_dispositivo=[]
    for row in [
        fila_si('Marca',datos.get('marca')),
        fila_si('Modelo',datos.get('modelo')),
        fila_si('Sistema operativo',datos.get('sistema_operativo')),
        fila_si('IMEI',datos.get('imei')),
        fila_si('Número de serie',datos.get('serie')),
        fila_si('Estado del dispositivo',datos.get('estado_dispositivo')),
        fila_si('Versión de WhatsApp',datos.get('version_whatsapp')),
    ]:
        if row: datos_dispositivo.append(row)
    if datos_dispositivo:
        td=Table(datos_dispositivo,colWidths=[58*mm,114*mm])
        td.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9CDD1')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F4F5F6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story += [td,Spacer(1,8)]

    story += [Paragraph('Conversación exportada',subt)]
    datos_conversacion=[]
    for row in [
        fila_si('Nombre del caso',datos.get('id_caso')),
        fila_si('Solicitante',datos.get('requirente')),
        fila_si('Contacto / grupo exportado',datos.get('contacto_grupo')),
        fila_si('Número del contacto exportado',datos.get('numero_contacto')),
        fila_si('Cuenta de WhatsApp de origen',cuenta),
        fila_si('Teléfono de la cuenta',datos.get('numero_whatsapp')),
        fila_si('Período de la conversación',datos.get('periodo')),
    ]:
        if row: datos_conversacion.append(row)
    if datos_conversacion:
        tcab=Table(datos_conversacion,colWidths=[58*mm,114*mm])
        tcab.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9CDD1')),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#F4F5F6')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
        story += [tcab,Spacer(1,8)]

    story += [Paragraph('Archivos creados',subt)]
    tabla_creados=[[Paragraph('<b>Archivo</b>',chico),Paragraph('<b>SHA-256</b>',chico)]]
    tabla_creados.append([Paragraph(esc(base_nombre)+'.zip',chico),Paragraph(esc(zip_hash),hashst)])
    tabla_creados.append([Paragraph('01 CHAT EXPORTADO.zip',chico),Paragraph(esc(hash_chat_zip),hashst)])
    if visual_items:
        tabla_creados.append([Paragraph('02 REGISTRO VISUAL.zip',chico),Paragraph(esc(hash_rv_zip),hashst)])
    tcre=Table(tabla_creados,colWidths=[92*mm,80*mm],repeatRows=1)
    tcre.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9CDD1')),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEF1F3')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story += [tcre,Spacer(1,8)]

    story += [Paragraph('Archivos contenidos en 01 CHAT EXPORTADO.zip',subt)]
    tabla_chat=[[Paragraph('<b>Archivo</b>',chico),Paragraph('<b>SHA-256</b>',chico)]]
    for x in chat_items:
        tabla_chat.append([
            Paragraph(esc(x['archivo']),chico),
            Paragraph(esc(x['sha256']),hashst)
        ])
    tc=Table(tabla_chat,colWidths=[92*mm,80*mm],repeatRows=1)
    tc.setStyle(TableStyle([
        ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9CDD1')),
        ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEF1F3')),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
        ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
    ]))
    story += [tc, Spacer(1,7)]

    if visual_items:
        story += [Paragraph('Archivos contenidos en 02 REGISTRO VISUAL.zip',subt)]
        tabla_rv=[[Paragraph('<b>Archivo</b>',chico),Paragraph('<b>Descripción</b>',chico),Paragraph('<b>SHA-256</b>',chico)]]
        for x in visual_items:
            tabla_rv.append([
                Paragraph(esc(x['archivo']),chico),
                Paragraph(esc(x['descripcion']),chico),
                Paragraph(esc(x['sha256']),hashst)
            ])
        trv=Table(tabla_rv,colWidths=[55*mm,57*mm,60*mm],repeatRows=1)
        trv.setStyle(TableStyle([
            ('GRID',(0,0),(-1,-1),0.35,colors.HexColor('#C9CDD1')),
            ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EEF1F3')),
            ('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),4),('RIGHTPADDING',(0,0),(-1,-1),4),
            ('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)
        ]))
        story += [trv, Spacer(1,7)]

    doc.build(story,onFirstPage=pie,onLaterPages=pie)

    # Guardar una copia del Acta Final dentro de ACTAS para consulta, impresión o presentación posterior.
    actas_dir=root/"05_ACTAS"
    actas_dir.mkdir(parents=True,exist_ok=True)
    acta_interna=actas_dir/"06_ACTA_FINAL_DE_ENTREGA.pdf"
    shutil.copyfile(acta,acta_interna)

    hash_txt=destino_base/(base_nombre+" SHA256.txt")
    hash_txt.write_text(
        "HASH DEL ARCHIVO OFICIAL DE ENTREGA\n"
        "===================================\n\n"
        f"Archivo: {zip_final.name}\n"
        "Algoritmo: SHA-256\n"
        f"SHA-256: {zip_hash}\n"
        f"Fecha/hora local: {ahora_local()}\n"
        f"Fecha/hora UTC: {ahora_utc()}\n",
        encoding="utf-8"
    )

    # El directorio temporal no forma parte de la salida.
    shutil.rmtree(temp)

    return {
        "zip":zip_final,
        "acta":acta,
        "hash_txt":hash_txt,
        "sha256_zip":zip_hash,
        "hash_chat_zip":hash_chat_zip,
        "hash_rv_zip":hash_rv_zip,
        "archivos_chat":len(chat_items),
        "registro_visual":len(visual_items),
        "archivos":len(chat_items)+len(visual_items)
    }

# ============================================================
# ACTIVIDAD
# ============================================================

def construir_actividad(root):
    ficha=leer_ficha(root)
    datos=ficha.get("datos",{})
    periodo=ficha.get("periodo_detectado_automaticamente",{})

    ep=root/"ESTADO_DEL_EXPEDIENTE.json"
    estado={}
    if ep.exists():
        try:
            estado=json.loads(ep.read_text(encoding="utf-8"))
        except Exception:
            pass

    rp=root/"02_INTEGRIDAD"/"HASHES_DE_RECEPCION.json"
    recepcion=json.loads(rp.read_text(encoding="utf-8")) if rp.exists() else []

    mp=root/"02_INTEGRIDAD"/"MANIFIESTO.json"
    mani=json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else []

    ip=root/"09_INCIDENCIAS"/"INCIDENCIAS.json"
    incidencias=json.loads(ip.read_text(encoding="utf-8")) if ip.exists() else []

    originales=[x for x in mani if x.get("tipo")=="ORIGINAL_PRESERVADO"]
    copias=[x for x in mani if x.get("tipo")=="COPIA_DE_TRABAJO"]
    derivados=[x for x in mani if x.get("tipo")=="DERIVADO_DESDE_COPIA"]

    resumen=[
        ("Caso",datos.get("id_caso",estado.get("caso",""))),
        ("Evidencia",datos.get("id_evidencia",estado.get("evidencia",""))),
        ("Contacto / grupo",datos.get("contacto_grupo","")),
        ("Período detectado",datos.get("periodo","")),
        ("Responsable",datos.get("responsable","")),
        ("Integridad",estado.get("integridad","")),
        ("Archivos recibidos",len(recepcion)),
        ("Archivos derivados",len(derivados)),
        ("SHA-256 del conjunto",ficha.get("sha256_conjunto_recibido",estado.get("sha256_conjunto","")))
    ]

    etapas=[
        {
            "titulo":"1. RECEPCIÓN",
            "estado":"OK",
            "descripcion":"Se identificaron los archivos recibidos y se calcularon sus hashes antes de copiarlos.",
            "detalles":[
                f"{r.get('id_archivo','')} · {r.get('nombre','')} · {r.get('tamano_bytes',0)} bytes\nSHA-256: {r.get('sha256','')}"
                for r in recepcion
            ]
        },
        {
            "titulo":"2. ORIGINAL PRESERVADO",
            "estado":"OK",
            "descripcion":"Los archivos fueron copiados a 01_ORIGINAL_NO_MODIFICAR. Esa ubicación no se usa para consulta.",
            "detalles":[f"{x.get('nombre_original','')} → {x.get('ruta_relativa','')}" for x in originales]
        },
        {
            "titulo":"3. COPIA DE TRABAJO",
            "estado":"OK",
            "descripcion":"Se generaron copias de trabajo y se verificó su igualdad mediante hash.",
            "detalles":[f"{x.get('nombre_original','')} → {x.get('ruta_relativa','')}" for x in copias]
        },
        {
            "titulo":"4. EXTRACCIÓN",
            "estado":"OK",
            "descripcion":"Los ZIP se extrajeron únicamente desde 03_COPIA_DE_TRABAJO.",
            "detalles":[f"Archivos derivados registrados: {len(derivados)}"]
        },
        {
            "titulo":"5. PERÍODO DEL CHAT",
            "estado":"OK" if periodo.get("periodo") else "ALERTA",
            "descripcion":"El rango temporal fue calculado automáticamente leyendo únicamente el historial de la copia.",
            "detalles":[
                f"Primera fecha: {periodo.get('primera','No detectada')}",
                f"Última fecha: {periodo.get('ultima','No detectada')}",
                f"Período: {periodo.get('periodo','No detectado')}"
            ]
        },
        {
            "titulo":"6. MANIFIESTO E INTEGRIDAD",
            "estado":"OK",
            "descripcion":"Se generó el inventario técnico del expediente.",
            "detalles":[
                "02_INTEGRIDAD\\MANIFIESTO.json",
                f"SHA-256 del manifiesto: {ficha.get('sha256_manifiesto','')}"
            ]
        },
        {
            "titulo":"7. DOCUMENTACIÓN",
            "estado":"OK",
            "descripcion":"Se generaron actas, informe, bitácora y registro de custodia.",
            "detalles":[
                "05_ACTAS\\01_ACTA_DE_PRESERVACION.html",
                "05_ACTAS\\02_ACTA_DE_INTEGRIDAD.html",
                "07_INFORME\\INFORME_DE_PRESERVACION.html"
            ]
        },
        {
            "titulo":"8. INCIDENCIAS",
            "estado":"ALERTA" if incidencias else "OK",
            "descripcion":f"Se registraron {len(incidencias)} incidencia(s)." if incidencias else "No se registraron incidencias.",
            "detalles":[f"{i.get('codigo','')}: {i.get('descripcion','')}" for i in incidencias]
        }
    ]

    return resumen,etapas

# ============================================================
# HTML A TEXTO PARA PREVISUALIZAR ACTAS
# ============================================================

class HTMLATexto(HTMLParser):
    def __init__(self):
        super().__init__()
        self.partes=[]
    def handle_data(self,data):
        s=data.strip()
        if s:
            self.partes.append(s)
    def texto(self):
        return "\n".join(self.partes)

def html_a_texto(path):
    parser=HTMLATexto()
    parser.feed(Path(path).read_text(encoding="utf-8",errors="replace"))
    return parser.texto()

# ============================================================
# INTERFAZ
# ============================================================


def actualizar_estado_flujo(root, **cambios):
    """Guarda el avance funcional del caso sin alterar los archivos preservados."""
    root=Path(root)
    p=root/"ESTADO_DEL_EXPEDIENTE.json"
    estado={}
    if p.exists():
        try:
            estado=json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            estado={}
    estado.update(cambios)
    estado["ultima_actualizacion_flujo"]=ahora_local()
    guardar_json(p,estado)
    return estado

def leer_estado_flujo(root):
    p=Path(root)/"ESTADO_DEL_EXPEDIENTE.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP} {VERSION}")
        self.geometry("1220x860")
        self.minsize(980,720)
        style=ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        # Identidad visual sobria y profesional.
        self.configure(bg="#F4F7F9")
        style.configure(".",font=("Segoe UI",10),background="#F4F7F9",foreground="#17242D")
        style.configure("TFrame",background="#F4F7F9")
        style.configure("TLabel",background="#F4F7F9",foreground="#17242D")
        style.configure("TLabelframe",background="#F4F7F9",bordercolor="#C9D4DA",relief="solid")
        style.configure("TLabelframe.Label",background="#F4F7F9",foreground="#263B47",font=("Segoe UI",9,"bold"))
        style.configure("TNotebook",background="#E7EDF1",borderwidth=0,tabmargins=(4,4,4,0))
        style.configure("TNotebook.Tab",font=("Segoe UI",9,"bold"),padding=(14,9),background="#DCE5EA",foreground="#344955")
        style.map("TNotebook.Tab",background=[("selected","#FFFFFF")],foreground=[("selected","#0D3B4C")])
        style.configure("TButton",font=("Segoe UI",9,"bold"),padding=(10,7),background="#E2E9ED",foreground="#20333E")
        style.map("TButton",background=[("active","#D5E0E5")])
        style.configure("Primary.TButton",font=("Segoe UI",9,"bold"),padding=(13,8),background="#164E63",foreground="#FFFFFF")
        style.map("Primary.TButton",background=[("active","#0F3E4F")],foreground=[("active","#FFFFFF")])
        style.configure("TEntry",padding=7,fieldbackground="#FFFFFF")
        style.configure("Treeview",rowheight=29,font=("Segoe UI",9),background="#FFFFFF",fieldbackground="#FFFFFF",foreground="#20333E")
        style.configure("Treeview.Heading",font=("Segoe UI",9,"bold"),background="#E5ECEF",foreground="#20333E")
        style.configure("ChatMedia.TButton",font=("Segoe UI",9),padding=(8,5))

        self.archivos=[]
        self.destino=tk.StringVar()
        self.vars={}
        self.expediente_actual=None
        self.chat_actual=None
        self.mensajes_actuales=[]
        self.multimedia_actual=[]
        self.multimedia_filtrada=[]
        self.registro_visual_actual=[]
        self.registro_visual_filtrado=[]
        self.rv_preview_image=None
        self.resultados_expedientes=[]
        self.actas_actuales=[]
        self.acta_actual=None
        self.imagen_preview=None
        self.chat_images=[]

        self.config_app=cargar_config()
        self.pdf_doc=None
        self.pdf_pagina=0
        self.pdf_imagen=None
        self.ultima_entrega=None
        try:
            directorio_expedientes(); directorio_entregas()
        except Exception as e:
            messagebox.showerror(APP,f"No se pudieron crear las carpetas de trabajo junto al programa.\n\n{e}")
        self.crear_interfaz()
        self.refrescar_expedientes()

    def crear_interfaz(self):
        cab=ttk.Frame(self,padding=(16,12))
        cab.pack(fill="x")

        izq=ttk.Frame(cab)
        izq.pack(side="left",fill="x",expand=True)
        ttk.Label(izq,text=f"{APP} {VERSION}",font=("Segoe UI",21,"bold")).pack(anchor="w")
        ttk.Label(
            izq,
            text="Preservación y entrega organizada de chats exportados de WhatsApp",
            foreground="#526771"
        ).pack(anchor="w")

        acciones=ttk.Frame(cab)
        acciones.pack(side="right",anchor="n")
        ttk.Button(acciones,text="NUEVO CASO",style="Primary.TButton",command=self.nuevo_caso).pack(side="left")

        self.lbl_caso_activo=ttk.Label(
            self,
            text="Caso activo: ninguno",
            font=("Segoe UI",9,"bold"),
            padding=(16,0,16,8)
        )
        self.lbl_caso_activo.pack(fill="x")

        # Barra visual del proceso.
        pasos=ttk.Frame(self,padding=(14,0,14,8))
        pasos.pack(fill="x")
        self.lbl_paso1=ttk.Label(pasos,text="① DATOS Y CHAT",font=("Segoe UI",10,"bold"))
        self.lbl_paso2=ttk.Label(pasos,text="② REGISTRO VISUAL",font=("Segoe UI",10,"bold"))
        self.lbl_paso3=ttk.Label(pasos,text="③ ENTREGA",font=("Segoe UI",10,"bold"))
        self.lbl_paso1.pack(side="left",padx=(0,24))
        self.lbl_paso2.pack(side="left",padx=(0,24))
        self.lbl_paso3.pack(side="left")
        self.lbl_estado_flujo=ttk.Label(pasos,text="PASO 1 EN CURSO",foreground="#4E5A60")
        self.lbl_estado_flujo.pack(side="right")

        self.nb=ttk.Notebook(self)
        self.nb.pack(fill="both",expand=True,padx=12,pady=(0,12))

        self.tab_preservar=ttk.Frame(self.nb,padding=14)
        self.tab_registro_visual=ttk.Frame(self.nb,padding=14)
        self.tab_entrega=ttk.Frame(self.nb,padding=14)

        self.tab_actividad=ttk.Frame(self.nb,padding=14)
        self.tab_chat=ttk.Frame(self.nb,padding=14)
        self.tab_multimedia=ttk.Frame(self.nb,padding=14)
        self.tab_verificar=ttk.Frame(self.nb,padding=14)
        self.tab_actas=ttk.Frame(self.nb,padding=14)
        self.tab_expedientes=ttk.Frame(self.nb,padding=14)
        self.tab_creditos=ttk.Frame(self.nb,padding=14)

        # Orden base: flujo principal + gestión.
        self.nb.add(self.tab_preservar,text="1. Datos y chat")
        self.nb.add(self.tab_registro_visual,text="2. Registro visual")
        self.nb.add(self.tab_entrega,text="3. Entrega")
        self.nb.add(self.tab_expedientes,text="Expedientes")
        self.nb.add(self.tab_creditos,text="Créditos")

        self.ui_preservar()
        self.ui_registro_visual()
        self.ui_entrega()

        # Estas vistas existen, pero recién se muestran después de generar una entrega.
        self.ui_actividad()
        self.ui_chat()
        self.ui_multimedia()
        self.ui_verificar()
        self.ui_actas()
        self.ui_expedientes()
        self.ui_creditos()

        self.vistas_resultado=[
            (self.tab_actividad,"Actividad"),
            (self.tab_chat,"Leer chat"),
            (self.tab_multimedia,"Multimedia"),
            (self.tab_verificar,"Verificar"),
            (self.tab_actas,"Actas"),
        ]

        # Paso 2 y Paso 3 arrancan bloqueados hasta completar el anterior.
        self.nb.tab(self.tab_registro_visual,state="disabled")
        self.nb.tab(self.tab_entrega,state="disabled")
        self.vistas_desbloqueadas=False

    def mostrar_vistas_resultado(self):
        if self.vistas_desbloqueadas:
            return
        # Insertarlas antes de Expedientes/Créditos.
        idx_exp=self.nb.index(self.tab_expedientes)
        for frame,titulo in self.vistas_resultado:
            try:
                self.nb.insert(idx_exp,frame,text=titulo)
                idx_exp += 1
            except tk.TclError:
                pass
        self.vistas_desbloqueadas=True

    def ocultar_vistas_resultado(self):
        for frame,_ in getattr(self,"vistas_resultado",[]):
            try:
                self.nb.forget(frame)
            except Exception:
                pass
        self.vistas_desbloqueadas=False

    def marcar_paso(self,paso,texto=None):
        if paso==1:
            self.lbl_estado_flujo.config(text=texto or "PASO 1 EN CURSO")
        elif paso==2:
            self.lbl_estado_flujo.config(text=texto or "PASO 1 COMPLETADO · PASO 2 EN CURSO")
        elif paso==3:
            self.lbl_estado_flujo.config(text=texto or "PASOS 1 Y 2 COMPLETADOS · PASO 3 EN CURSO")
        elif paso==4:
            self.lbl_estado_flujo.config(text=texto or "✓ ENTREGA GENERADA · CONSULTA HABILITADA")

    def habilitar_paso2(self):
        self.nb.tab(self.tab_registro_visual,state="normal")
        self.nb.select(self.tab_registro_visual)
        self.marcar_paso(2)

    def habilitar_paso3(self):
        if not self.expediente_actual:
            messagebox.showinfo(APP,"Primero complete el Paso 1.")
            return
        self.nb.tab(self.tab_entrega,state="normal")
        actualizar_estado_flujo(self.expediente_actual,paso_2_completado=True)
        self.nb.select(self.tab_entrega)
        self.marcar_paso(3)

    # ---------------- PRESERVAR ----------------

    def ui_preservar(self):
        t=self.tab_preservar
        cont=tk.Canvas(t,highlightthickness=0)
        vs=ttk.Scrollbar(t,orient="vertical",command=cont.yview)
        frame=ttk.Frame(cont,padding=(4,2))
        frame.bind("<Configure>",lambda e:cont.configure(scrollregion=cont.bbox("all")))
        cont.create_window((0,0),window=frame,anchor="nw");cont.configure(yscrollcommand=vs.set)
        cont.pack(side="left",fill="both",expand=True);vs.pack(side="right",fill="y")

        ttk.Label(frame,text="NUEVO CASO",font=("Segoe UI",16,"bold")).grid(row=0,column=0,columnspan=3,sticky="w",pady=(0,4))
        ttk.Label(frame,text="Preservá una exportación recibida de WhatsApp. El original queda separado de la copia de trabajo y todos los archivos se identifican mediante hash.",wraplength=900,foreground="#555").grid(row=1,column=0,columnspan=3,sticky="w",pady=(0,14))

        ttk.Label(frame,text="1. ARCHIVOS RECIBIDOS",font=("Segoe UI",11,"bold")).grid(row=2,column=0,columnspan=3,sticky="w")
        ttk.Label(frame,text="Seleccioná todos los archivos que llegaron juntos con la exportación. Ninguno se descarta automáticamente.",foreground="#555").grid(row=3,column=0,columnspan=3,sticky="w",pady=(1,5))
        ttk.Button(frame,text="SELECCIONAR ARCHIVOS",command=self.seleccionar_archivos).grid(row=4,column=0,sticky="w",pady=5)
        self.lbl_archivos=ttk.Label(frame,text="Ningún archivo seleccionado");self.lbl_archivos.grid(row=4,column=1,columnspan=2,sticky="w",padx=8)

        ttk.Label(frame,text="2. DESTINO AUTOMÁTICO",font=("Segoe UI",11,"bold")).grid(row=5,column=0,columnspan=3,sticky="w",pady=(12,0))
        ttk.Label(frame,text="PreservarChat guarda cada caso en la carpeta Expedientes ubicada junto al ejecutable.",foreground="#555",wraplength=900).grid(row=6,column=0,columnspan=3,sticky="w")
        self.lbl_destino_auto=ttk.Label(frame,text=str(directorio_expedientes()),font=("Consolas",9));self.lbl_destino_auto.grid(row=7,column=0,columnspan=3,sticky="w",pady=(3,10))

        zona=datetime.now().astimezone().strftime("%z");zona=f"UTC{zona[:3]}:{zona[3:]}" if zona else ""
        self.vars={}
        fila=8

        def seccion(titulo, ayuda=None):
            nonlocal fila
            ttk.Separator(frame,orient="horizontal").grid(row=fila,column=0,columnspan=3,sticky="ew",pady=(12,6));fila+=1
            cab=tk.Label(frame,text=titulo,font=("Segoe UI",11,"bold"),bg="#EAF1F5",fg="#17384A",anchor="w",padx=10,pady=7)
            cab.grid(row=fila,column=0,columnspan=3,sticky="ew",pady=(0,3));fila+=1
            if ayuda:
                ttk.Label(frame,text=ayuda,foreground="#52636C",wraplength=900,justify="left").grid(row=fila,column=0,columnspan=3,sticky="w",padx=(8,0),pady=(0,7));fila+=1

        def campo(k,l,d=""):
            nonlocal fila
            ttk.Label(frame,text=l,font=("Segoe UI",10,"bold")).grid(row=fila,column=0,sticky="w",padx=(0,10),pady=4)
            v=tk.StringVar(value=d);self.vars[k]=v
            ttk.Entry(frame,textvariable=v,width=64,font=("Segoe UI",10,"bold")).grid(row=fila,column=1,sticky="ew",pady=4)
            fila+=1

        seccion("3. DATOS DEL CASO","Identificación general del expediente. Los campos marcados con * son obligatorios.")
        campo("id_caso","NOMBRE DEL CASO *")
        campo("id_evidencia","ID de evidencia *","EVD-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6].upper())
        campo("requirente","Requirente / solicitante / entregante (opcional)")
        campo("autorizacion","Autorización / consentimiento / referencia (opcional)")
        campo("fecha","Fecha",datetime.now().strftime("%d/%m/%Y"))
        campo("hora","Hora",datetime.now().strftime("%H:%M:%S"))
        campo("zona_horaria","Zona horaria",zona)
        campo("observaciones","Observaciones (opcional)")

        seccion("4. DISPOSITIVO AUDITADO","Datos del teléfono desde el cual se realiza la exportación. Marca, modelo, sistema operativo, IMEI y versión de WhatsApp son obligatorios.")
        campo("marca","Marca del dispositivo *")
        campo("modelo","Modelo *")
        campo("sistema_operativo","Sistema operativo *")
        campo("imei","IMEI *")
        campo("serie","Número de serie")
        campo("version_whatsapp","Versión de WhatsApp *")
        campo("estado_dispositivo","Estado del dispositivo al inicio")

        seccion("5. CUENTA DE WHATSAPP DE ORIGEN","Identificá al titular y el número de la cuenta de WhatsApp abierta en el dispositivo desde la cual se exporta el chat.")
        campo("titular_whatsapp","Titular de la cuenta de WhatsApp de origen *")
        campo("numero_whatsapp","Teléfono de la cuenta de WhatsApp de origen *")

        seccion("6. CONVERSACIÓN EXPORTADA","Estos datos corresponden al contacto o grupo cuya conversación fue exportada. No corresponden a la cuenta de origen. El número del contacto es opcional porque puede tratarse de un grupo.")
        campo("contacto_grupo","Contacto / Grupo Auditado *")
        campo("numero_contacto","Número del contacto exportado (opcional; no aplica a grupos)")
        campo("incluye_multimedia","¿Incluye multimedia?","Sí")
        campo("metodo","Método de obtención","WhatsApp → Exportar chat")

        seccion("7. RESPONSABLE DE LA EXPORTACIÓN · QUIÉN REALIZA EL PROCEDIMIENTO","Puede ser una persona, profesional, perito, estudio, empresa u organismo. Estos datos identifican a quien realiza materialmente el procedimiento.")
        campo("persona_exporto","Persona / profesional / organización que realiza la exportación *")
        campo("exportador_direccion","Domicilio / dirección (opcional)")
        campo("exportador_localidad","Localidad / jurisdicción (opcional)")
        campo("exportador_telefono","Teléfono de contacto (opcional)")
        campo("exportador_email","Correo electrónico (opcional)")

        frame.columnconfigure(1,weight=1)
        ttk.Button(frame,text="GUARDAR Y CONTINUAR",command=self.preservar).grid(row=fila,column=0,columnspan=3,pady=20)
    # ---------------- ACTIVIDAD ----------------

    def ui_actividad(self):
        a=self.tab_actividad
        top=ttk.Frame(a);top.pack(fill="x")
        ttk.Label(top,text="Actividad del expediente",font=("Segoe UI",14,"bold")).pack(side="left")
        self.lbl_exp_act=ttk.Label(top,text="Sin expediente activo")
        self.lbl_exp_act.pack(side="right")

        ttk.Label(a,text="Resumen ordenado de todo lo realizado.",foreground="#555").pack(anchor="w",pady=(3,8))

        fr=ttk.Frame(a);fr.pack(fill="both",expand=True)
        self.actividad=tk.Text(fr,wrap="none",state="disabled",padx=14,pady=12)
        vy=ttk.Scrollbar(fr,orient="vertical",command=self.actividad.yview)
        hx=ttk.Scrollbar(fr,orient="horizontal",command=self.actividad.xview)
        self.actividad.configure(yscrollcommand=vy.set,xscrollcommand=hx.set)
        self.actividad.grid(row=0,column=0,sticky="nsew")
        vy.grid(row=0,column=1,sticky="ns")
        hx.grid(row=1,column=0,sticky="ew")
        fr.rowconfigure(0,weight=1);fr.columnconfigure(0,weight=1)

        self.actividad.tag_configure("titulo",font=("Segoe UI",14,"bold"))
        self.actividad.tag_configure("subtitulo",font=("Segoe UI",11,"bold"))
        self.actividad.tag_configure("ok",font=("Segoe UI",11,"bold"))
        self.actividad.tag_configure("alerta",font=("Segoe UI",11,"bold"))
        self.actividad.tag_configure("hash",font=("Consolas",9))

    # ---------------- CHAT ----------------

    def ui_chat(self):
        c=self.tab_chat

        # Encabezado inspirado en la estructura de WhatsApp Web.
        cab_chat=tk.Frame(c,bg="#075E54",height=58)
        cab_chat.pack(fill="x",pady=(0,8))
        avatar=tk.Label(
            cab_chat,text="◉",bg="#075E54",fg="white",
            font=("Segoe UI",20,"bold"),width=3
        )
        avatar.pack(side="left",padx=(8,2),pady=7)

        info=tk.Frame(cab_chat,bg="#075E54")
        info.pack(side="left",fill="x",expand=True,pady=7)
        self.lbl_chat_contacto=tk.Label(
            info,text="Sin caso activo",bg="#075E54",fg="white",
            font=("Segoe UI",11,"bold"),anchor="w"
        )
        self.lbl_chat_contacto.pack(anchor="w")
        self.lbl_chat_estado=tk.Label(
            info,text="Seleccione un expediente para visualizar la conversación",
            bg="#075E54",fg="#D5E7E4",font=("Segoe UI",8),anchor="w"
        )
        self.lbl_chat_estado.pack(anchor="w")

        search=ttk.Frame(c)
        search.pack(fill="x",pady=(0,8))
        ttk.Label(search,text="Buscar en la conversación:").pack(side="left")
        self.buscar_chat_var=tk.StringVar()
        ent=ttk.Entry(search,textvariable=self.buscar_chat_var,width=44)
        ent.pack(side="left",padx=6)
        ent.bind("<Return>",lambda e:self.buscar_chat())
        ttk.Button(search,text="BUSCAR",command=self.buscar_chat).pack(side="left")
        ttk.Button(search,text="SIGUIENTE",command=self.buscar_siguiente).pack(side="left",padx=5)
        self.lbl_busqueda_chat=ttk.Label(search,text="")
        self.lbl_busqueda_chat.pack(side="left",padx=8)

        ttk.Label(
            c,
            text="Visualización en modo solo lectura. El contenido se obtiene exclusivamente de la copia de trabajo del expediente.",
            foreground="#5F6B70",wraplength=1000
        ).pack(anchor="w",pady=(0,7))

        fr=ttk.Frame(c)
        fr.pack(fill="both",expand=True)
        self.chat_text=tk.Text(
            fr,wrap="word",state="disabled",padx=30,pady=20,
            spacing1=3,spacing3=7,borderwidth=0,highlightthickness=0,
            background="#EFEAE2",font=("Segoe UI",10),selectbackground="#B7D7F0"
        )
        vy=ttk.Scrollbar(fr,orient="vertical",command=self.chat_text.yview)
        self.chat_text.configure(yscrollcommand=vy.set)
        self.chat_text.grid(row=0,column=0,sticky="nsew")
        vy.grid(row=0,column=1,sticky="ns")
        fr.rowconfigure(0,weight=1)
        fr.columnconfigure(0,weight=1)

        # Burbujas claras/oscuras, fecha centrada y mensajes de sistema diferenciados.
        self.chat_text.tag_configure(
            "izq",justify="left",lmargin1=44,lmargin2=44,rmargin=390,
            spacing1=8,spacing3=10,background="#FFFFFF"
        )
        self.chat_text.tag_configure(
            "der",justify="right",lmargin1=390,lmargin2=390,rmargin=44,
            spacing1=8,spacing3=10,background="#D9FDD3"
        )
        self.chat_text.tag_configure(
            "autor",font=("Segoe UI",9,"bold"),foreground="#008069"
        )
        self.chat_text.tag_configure(
            "hora",font=("Segoe UI",8),foreground="#667781"
        )
        self.chat_text.tag_configure(
            "fecha_sep",justify="center",font=("Segoe UI",9,"bold"),
            foreground="#54656F",background="#E1F3FB",spacing1=10,spacing3=10
        )
        self.chat_text.tag_configure(
            "sistema",justify="center",font=("Segoe UI",9),
            foreground="#54656F",background="#FFF3C4",spacing1=6,spacing3=6
        )
        self.chat_text.tag_configure("busqueda",background="#FFE36E")
        self.posiciones_busqueda=[]
        self.indice_busqueda=0

    # ---------------- MULTIMEDIA ----------------

    def ui_multimedia(self):
        m=self.tab_multimedia
        top=ttk.Frame(m);top.pack(fill="x")
        ttk.Label(top,text="Multimedia del expediente",font=("Segoe UI",14,"bold")).pack(side="left")
        self.lbl_multimedia_estado=ttk.Label(top,text="Sin expediente activo")
        self.lbl_multimedia_estado.pack(side="right")

        ttk.Label(
            m,
            text="Sólo se listan archivos ubicados dentro de 03_COPIA_DE_TRABAJO.",
            foreground="#555"
        ).pack(anchor="w",pady=(3,8))

        filtros=ttk.Frame(m);filtros.pack(fill="x",pady=(0,8))
        ttk.Label(filtros,text="Buscar:").pack(side="left")
        self.mult_buscar=tk.StringVar()
        ent=ttk.Entry(filtros,textvariable=self.mult_buscar,width=32)
        ent.pack(side="left",padx=5)
        ent.bind("<KeyRelease>",lambda e:self.filtrar_multimedia())
        ttk.Label(filtros,text="Tipo:").pack(side="left",padx=(12,0))
        self.mult_tipo=tk.StringVar(value="Todos")
        combo=ttk.Combobox(filtros,textvariable=self.mult_tipo,values=["Todos","Imagen","Audio","Video","Documento"],state="readonly",width=14)
        combo.pack(side="left",padx=5)
        combo.bind("<<ComboboxSelected>>",lambda e:self.filtrar_multimedia())

        paned=ttk.Panedwindow(m,orient="horizontal");paned.pack(fill="both",expand=True)
        left=ttk.Frame(paned);right=ttk.Frame(paned,padding=10)
        paned.add(left,weight=3);paned.add(right,weight=2)

        cols=("nombre","tipo","tamano","ruta")
        self.tree_mult=ttk.Treeview(left,columns=cols,show="headings")
        for col,tit,w in [
            ("nombre","Archivo",240),("tipo","Tipo",80),("tamano","Tamaño",90),("ruta","Ruta de copia",320)
        ]:
            self.tree_mult.heading(col,text=tit)
            self.tree_mult.column(col,width=w)
        vy=ttk.Scrollbar(left,orient="vertical",command=self.tree_mult.yview)
        hx=ttk.Scrollbar(left,orient="horizontal",command=self.tree_mult.xview)
        self.tree_mult.configure(yscrollcommand=vy.set,xscrollcommand=hx.set)
        self.tree_mult.grid(row=0,column=0,sticky="nsew")
        vy.grid(row=0,column=1,sticky="ns");hx.grid(row=1,column=0,sticky="ew")
        left.rowconfigure(0,weight=1);left.columnconfigure(0,weight=1)
        self.tree_mult.bind("<<TreeviewSelect>>",lambda e:self.preview_multimedia())
        self.tree_mult.bind("<Double-1>",lambda e:self.abrir_multimedia())

        self.preview_img=ttk.Label(right,text="Seleccione un archivo")
        self.preview_img.pack(fill="both",expand=True)
        self.preview_info=ttk.Label(right,text="",justify="left",wraplength=320)
        self.preview_info.pack(anchor="w",fill="x",pady=8)
        ttk.Button(right,text="ABRIR ARCHIVO DE COPIA",command=self.abrir_multimedia).pack(anchor="w")

    # ---------------- REGISTRO VISUAL ----------------

    def ui_registro_visual(self):
        r=self.tab_registro_visual
        top=ttk.Frame(r);top.pack(fill='x')
        ttk.Label(top,text='REGISTRO VISUAL',font=('Segoe UI',16,'bold')).pack(side='left')
        self.lbl_rv_estado=ttk.Label(top,text='Sin expediente activo',font=('Segoe UI',9,'bold'));self.lbl_rv_estado.pack(side='right')
        ttk.Label(r,text='Permite incorporar material complementario relacionado con el procedimiento: fotografías, capturas, videos, audios y documentos. No forma parte de la exportación nativa de WhatsApp.',foreground='#555',wraplength=980,justify='left').pack(anchor='w',pady=(4,7))

        ttk.Label(
            r,
            text='Como apoyo documental, pueden incorporarse imágenes, videos, audios, PDF, documentos de Word o planillas de Excel que resulten pertinentes para el caso.',
            foreground='#555',font=('Segoe UI',8),wraplength=1050,justify='left'
        ).pack(anchor='w',fill='x',pady=(0,7))

        barra=ttk.Frame(r);barra.pack(fill='x',pady=(0,5))
        ttk.Button(barra,text='AGREGAR MATERIAL COMPLEMENTARIO',command=self.agregar_registro_visual_ui).pack(side='left')
        ttk.Label(barra,text='Opcional · cada archivo recibe ID, descripción y SHA-256.',foreground='#555',font=('Segoe UI',8)).pack(side='left',padx=8)
        ttk.Button(barra,text='CONTINUAR A ENTREGA',style='Primary.TButton',command=self.habilitar_paso3).pack(side='right')
        ttk.Button(barra,text='CONTINUAR SIN REGISTRO VISUAL',command=self.habilitar_paso3).pack(side='right',padx=6)

        # Acciones siempre visibles: no dependen del alto de la vista previa.
        acciones_superiores=ttk.Frame(r);acciones_superiores.pack(fill='x',pady=(0,6))
        self.btn_rv_abrir=ttk.Button(acciones_superiores,text='ABRIR COPIA',command=self.abrir_registro_visual)
        self.btn_rv_editar=ttk.Button(acciones_superiores,text='EDITAR DATOS',command=self.editar_registro_visual_ui)
        self.btn_rv_reemplazar=ttk.Button(acciones_superiores,text='REEMPLAZAR ARCHIVO',command=self.reemplazar_registro_visual_ui)
        self.btn_rv_eliminar=ttk.Button(acciones_superiores,text='ELIMINAR ARCHIVO',command=self.eliminar_registro_visual_ui)
        for b in (self.btn_rv_abrir,self.btn_rv_editar,self.btn_rv_reemplazar,self.btn_rv_eliminar): b.pack(side='left',padx=(0,6))

        pan=ttk.Panedwindow(r,orient='horizontal');pan.pack(fill='both',expand=True)
        left=ttk.Frame(pan);right=ttk.Frame(pan,padding=10);pan.add(left,weight=3);pan.add(right,weight=2)
        cols=('orden','id','tipo','archivo','incorporacion','metadatos','descripcion')
        self.tree_rv=ttk.Treeview(left,columns=cols,show='headings',selectmode='browse')
        conf=[('orden','Orden',60),('id','ID',70),('tipo','Tipo',80),('archivo','Archivo',210),('incorporacion','Incorporado',170),('metadatos','Fecha metadatos',150),('descripcion','Descripción',300)]
        for c,tit,w in conf:self.tree_rv.heading(c,text=tit);self.tree_rv.column(c,width=w)
        vy=ttk.Scrollbar(left,orient='vertical',command=self.tree_rv.yview);hx=ttk.Scrollbar(left,orient='horizontal',command=self.tree_rv.xview)
        self.tree_rv.configure(yscrollcommand=vy.set,xscrollcommand=hx.set);self.tree_rv.grid(row=0,column=0,sticky='nsew');vy.grid(row=0,column=1,sticky='ns');hx.grid(row=1,column=0,sticky='ew');left.rowconfigure(0,weight=1);left.columnconfigure(0,weight=1)
        self.tree_rv.bind('<<TreeviewSelect>>',lambda ev:self.preview_registro_visual())
        self.tree_rv.bind('<Double-1>',lambda ev:self.abrir_registro_visual())
        self.rv_preview=ttk.Label(right,text='Seleccione un elemento',anchor='center');self.rv_preview.pack(fill='both',expand=True)
        self.rv_info=ttk.Label(right,text='',justify='left',wraplength=330);self.rv_info.pack(anchor='w',fill='x',pady=8)
        ttk.Label(right,text='Las opciones del elemento seleccionado permanecen disponibles en la barra superior.',foreground='#666',font=('Segoe UI',8),wraplength=320,justify='left').pack(anchor='w',fill='x',pady=(2,0))
    # ---------------- EXPEDIENTES ----------------

    def ui_expedientes(self):
        e=self.tab_expedientes
        ttk.Label(e,text="EXPEDIENTES",font=("Segoe UI",16,"bold")).pack(anchor="w")
        ttk.Label(e,text="Los casos creados por PreservarChat aparecen automáticamente acá. No es necesario navegar por las carpetas internas ni abrir originales.",foreground="#555",wraplength=950).pack(anchor="w",pady=(3,8))
        ttk.Label(e,text=f"Ubicación: {directorio_expedientes()}",font=("Consolas",9)).pack(anchor="w",pady=(0,10))
        barra=ttk.Frame(e);barra.pack(fill="x",pady=(0,8))
        ttk.Button(barra,text="ACTUALIZAR LISTA",command=self.refrescar_expedientes).pack(side="left")
        ttk.Label(barra,text="Buscar:").pack(side="left",padx=(18,4))
        self.exp_buscar=tk.StringVar();ent=ttk.Entry(barra,textvariable=self.exp_buscar,width=32);ent.pack(side="left")
        ent.bind("<KeyRelease>",lambda ev:self.refrescar_expedientes())
        self.lbl_exp_info=ttk.Label(barra,text="");self.lbl_exp_info.pack(side="right")
        cols=("caso","evidencia","contacto","periodo","integridad")
        area=ttk.Frame(e);area.pack(fill="both",expand=True)
        self.tree_exp=ttk.Treeview(area,columns=cols,show="headings",selectmode="browse")
        for col,tit,w in [("caso","Caso",180),("evidencia","Evidencia",230),("contacto","Contacto / grupo",200),("periodo","Período",180),("integridad","Estado",130)]:
            self.tree_exp.heading(col,text=tit);self.tree_exp.column(col,width=w)
        vy=ttk.Scrollbar(area,orient="vertical",command=self.tree_exp.yview);hx=ttk.Scrollbar(area,orient="horizontal",command=self.tree_exp.xview)
        self.tree_exp.configure(yscrollcommand=vy.set,xscrollcommand=hx.set)
        self.tree_exp.grid(row=0,column=0,sticky="nsew");vy.grid(row=0,column=1,sticky="ns");hx.grid(row=1,column=0,sticky="ew")
        area.rowconfigure(0,weight=1);area.columnconfigure(0,weight=1);self.tree_exp.bind("<Double-1>",lambda ev:self.abrir_caso())
        bottom=ttk.Frame(e);bottom.pack(fill="x",pady=10)
        ttk.Button(bottom,text="ABRIR CASO",style="Primary.TButton",command=self.abrir_caso).pack(side="right")
        ttk.Button(bottom,text="🗑  ELIMINAR EXPEDIENTE",command=self.eliminar_expediente_ui).pack(side="right",padx=(0,8))
        ttk.Label(bottom,text="Abrir verifica la integridad del caso. El ícono de papelera permite eliminar definitivamente el expediente seleccionado y todos sus archivos internos, siempre después de una confirmación.",foreground="#555",wraplength=700).pack(side="left")

    # ---------------- VERIFICAR ----------------

    def ui_verificar(self):
        v=self.tab_verificar
        top=ttk.Frame(v);top.pack(fill="x")
        ttk.Label(top,text="VERIFICACIÓN DE INTEGRIDAD",font=("Segoe UI",16,"bold")).pack(side="left")
        self.lbl_verificar=ttk.Label(top,text="Sin expediente activo",font=("Segoe UI",9,"bold"));self.lbl_verificar.pack(side="right")
        ttk.Label(v,text="¿PARA QUÉ SIRVE?",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(8,2))
        ttk.Label(v,text="Verificar comprueba que los archivos guardados en el expediente siguen siendo exactamente los mismos que se preservaron al inicio. No analiza el contenido del chat ni decide si una conversación es verdadera: controla que los archivos no hayan cambiado, sido reemplazados o desaparecido.",foreground="#444",wraplength=980,justify="left").pack(anchor="w",pady=(0,8))
        ttk.Label(v,text="¿QUÉ HACE EL SISTEMA?",font=("Segoe UI",11,"bold")).pack(anchor="w",pady=(4,2))
        ttk.Label(v,text="1. Lee los hashes registrados cuando se creó el expediente.   2. Vuelve a calcular el SHA-256 de cada archivo.   3. Compara ambos valores.   4. Informa COINCIDE, NO COINCIDE o FALTANTE.   5. Si detecta una diferencia, bloquea la lectura para evitar trabajar sobre material cuya integridad no pudo confirmarse.",foreground="#444",wraplength=980,justify="left").pack(anchor="w",pady=(0,10))
        self.lbl_ver_estado=ttk.Label(v,text="SIN VERIFICACIÓN",font=("Segoe UI",15,"bold"));self.lbl_ver_estado.pack(anchor="w",pady=(0,8))
        ttk.Button(v,text="VERIFICAR AHORA",command=self.verificar_activo).pack(anchor="w",pady=(0,10))
        fr=ttk.Frame(v);fr.pack(fill="both",expand=True)
        self.salida=tk.Text(fr,wrap="none",state="disabled",font=("Consolas",9),padx=12,pady=10)
        vy=ttk.Scrollbar(fr,orient="vertical",command=self.salida.yview);hx=ttk.Scrollbar(fr,orient="horizontal",command=self.salida.xview)
        self.salida.configure(yscrollcommand=vy.set,xscrollcommand=hx.set)
        self.salida.grid(row=0,column=0,sticky="nsew");vy.grid(row=0,column=1,sticky="ns");hx.grid(row=1,column=0,sticky="ew")
        fr.rowconfigure(0,weight=1);fr.columnconfigure(0,weight=1)
        self.salida.tag_configure("ok",font=("Consolas",9,"bold"));self.salida.tag_configure("bad",font=("Consolas",9,"bold"));self.salida.tag_configure("titulo",font=("Segoe UI",11,"bold"))

    # ---------------- ACTAS ----------------

    def ui_actas(self):
        a=self.tab_actas
        top=ttk.Frame(a)
        top.pack(fill="x")
        ttk.Label(top,text="ACTAS",font=("Segoe UI",16,"bold")).pack(side="left")
        self.lbl_actas=ttk.Label(top,text="Sin caso activo",font=("Segoe UI",9,"bold"))
        self.lbl_actas.pack(side="right")

        ttk.Label(
            a,
            text="Documentación generada por PreservarChat para dejar constancia de las distintas etapas del trabajo. "
                 "Estas actas quedan disponibles como respaldo interno; la entrega final incorpora únicamente el Acta Final de Entrega.",
            foreground="#555",wraplength=980,justify="left"
        ).pack(anchor="w",pady=(4,8))

        desc=ttk.LabelFrame(a,text="¿Para qué sirve cada acta?",padding=9)
        desc.pack(fill="x",pady=(0,8))
        texto=(
            "• Acta de Preservación: identifica el material recibido y deja constancia de su resguardo e identificación mediante hash.\n"
            "• Acta de Integridad: documenta que los archivos disponibles coinciden con los hashes registrados.\n"
            "• Acta de Registro Visual: ordena fotografías, capturas, videos o audios incorporados, con descripción y hash. "
            "Las imágenes incluyen vista previa y los videos pueden incluir un fotograma identificador.\n"
            "• Manifiesto de Integridad: reúne en una sola relación los archivos controlados y sus hashes.\n"
            "• Acta Final de Entrega: es la versión pensada para presentar o imprimir. Resume los datos del dispositivo, "
            "la obtención informada y todo el material efectivamente incluido en la entrega, con sus hashes."
        )
        ttk.Label(desc,text=texto,wraplength=950,justify="left").pack(anchor="w")

        pan=ttk.Panedwindow(a,orient="horizontal")
        pan.pack(fill="both",expand=True)
        left=ttk.Frame(pan);right=ttk.Frame(pan)
        pan.add(left,weight=1);pan.add(right,weight=4)

        self.lista_actas=tk.Listbox(left,font=("Segoe UI",10))
        lv=ttk.Scrollbar(left,orient="vertical",command=self.lista_actas.yview)
        self.lista_actas.configure(yscrollcommand=lv.set)
        self.lista_actas.grid(row=0,column=0,sticky="nsew")
        lv.grid(row=0,column=1,sticky="ns")
        left.rowconfigure(0,weight=1);left.columnconfigure(0,weight=1)
        self.lista_actas.bind("<<ListboxSelect>>",lambda ev:self.preview_acta())

        nav=ttk.Frame(right);nav.pack(fill="x")
        ttk.Button(nav,text="◀ ANTERIOR",command=self.pdf_anterior).pack(side="left")
        ttk.Button(nav,text="SIGUIENTE ▶",command=self.pdf_siguiente).pack(side="left",padx=5)
        self.lbl_pdf_pagina=ttk.Label(nav,text="")
        self.lbl_pdf_pagina.pack(side="left",padx=8)
        ttk.Button(nav,text="ABRIR PDF",command=self.abrir_acta).pack(side="right")
        ttk.Button(nav,text="MOSTRAR EN EXPLORADOR",command=self.explorar_acta).pack(side="right",padx=6)
        ttk.Button(nav,text="IMPRIMIR",command=self.imprimir_acta).pack(side="right",padx=6)

        preview=ttk.Frame(right);preview.pack(fill="both",expand=True,pady=(6,0))
        self.pdf_canvas=tk.Canvas(preview,background="white",highlightthickness=1,highlightbackground="#bbb")
        pvy=ttk.Scrollbar(preview,orient="vertical",command=self.pdf_canvas.yview)
        phx=ttk.Scrollbar(preview,orient="horizontal",command=self.pdf_canvas.xview)
        self.pdf_canvas.configure(yscrollcommand=pvy.set,xscrollcommand=phx.set)
        self.pdf_canvas.grid(row=0,column=0,sticky="nsew")
        pvy.grid(row=0,column=1,sticky="ns");phx.grid(row=1,column=0,sticky="ew")
        preview.rowconfigure(0,weight=1);preview.columnconfigure(0,weight=1)

        ttk.Label(a,text="Seleccione un acta. Puede verla aquí, abrir el PDF, ubicarlo en el Explorador o enviarlo a impresión.",foreground="#5B6870").pack(anchor="w",pady=(6,0))

    # ---------------- ENTREGA ----------------

    def ui_entrega(self):
        e=self.tab_entrega
        top=ttk.Frame(e);top.pack(fill="x")
        ttk.Label(top,text="PASO 3 · GENERAR ENTREGA",font=("Segoe UI",16,"bold")).pack(side="left")
        self.lbl_entrega=ttk.Label(top,text="Sin caso activo",font=("Segoe UI",9,"bold"))
        self.lbl_entrega.pack(side="right")

        ttk.Label(
            e,
            text="Último paso. PreservarChat verifica nuevamente la integridad y genera un ZIP oficial con el material digital, junto con su SHA-256. "
                 "El Acta Final de Entrega se genera por separado, fuera del ZIP, para poder abrirla, imprimirla o presentarla sin alterar el contenedor de evidencia.",
            foreground="#4B555A",wraplength=980,justify="left"
        ).pack(anchor="w",pady=(4,7))

        tarjetas=ttk.Frame(e);tarjetas.pack(fill="x")
        textos=[
            ("01 CHAT EXPORTADO.zip",
             "Contiene los archivos recibidos de la exportación de WhatsApp y HASHES CHAT.txt con la identificación y SHA-256 de cada uno."),
            ("02 REGISTRO VISUAL.zip · SOLO SI SE INCORPORA MATERIAL",
             "Se genera únicamente cuando existen elementos visuales o audiovisuales incorporados. Si no hay Registro Visual, este ZIP no se crea ni se menciona en el Acta Final."),
            ("ACTA FINAL DE ENTREGA.pdf · EXTERNA",
             "Se genera fuera del ZIP oficial. Reúne los datos efectivamente cargados, el origen de la cuenta, el contacto / grupo exportado, quién realizó la exportación, el material presentado, el contenido de cada ZIP y sus hashes."),
            ("SHA-256 DEL ZIP OFICIAL",
             "El ZIP oficial recibe un SHA-256 definitivo. El valor se entrega en un TXT externo para que pueda ser comprobado sin modificar el propio ZIP.")
        ]
        for i,(tit,desc) in enumerate(textos):
            box=ttk.LabelFrame(tarjetas,text=tit,padding=(8,5))
            box.grid(row=i//2,column=i%2,sticky="nsew",padx=4,pady=3)
            ttk.Label(box,text=desc,wraplength=425,justify="left",font=("Segoe UI",8)).pack(anchor="w")
        tarjetas.columnconfigure(0,weight=1);tarjetas.columnconfigure(1,weight=1)

        ttk.Label(e,text=f"Destino automático: {directorio_entregas()}",font=("Consolas",8)).pack(anchor="w",pady=(6,5))
        acciones=ttk.Frame(e)
        acciones.pack(fill="x",pady=(0,6))
        ttk.Button(acciones,text="GENERAR ENTREGA",style="Primary.TButton",command=self.generar_entrega_ui).pack(side="left")
        ttk.Button(acciones,text="ABRIR CARPETA",command=lambda:abrir_carpeta(directorio_entregas())).pack(side="left",padx=8)

        fr=ttk.Frame(e);fr.pack(fill="both",expand=True)
        self.entrega_info=tk.Text(fr,wrap="word",state="disabled",font=("Segoe UI",9),padx=14,pady=10,height=12,bg="#FFFFFF",fg="#20333E",relief="flat",highlightthickness=1,highlightbackground="#D3DEE3")
        vy=ttk.Scrollbar(fr,orient="vertical",command=self.entrega_info.yview)
        self.entrega_info.configure(yscrollcommand=vy.set)
        self.entrega_info.grid(row=0,column=0,sticky="nsew");vy.grid(row=0,column=1,sticky="ns")
        fr.rowconfigure(0,weight=1);fr.columnconfigure(0,weight=1)

    # ---------------- CREDITOS ----------------

    def ui_creditos(self):
        ttk.Label(self.tab_creditos,text="Créditos",font=("Segoe UI",18,"bold")).pack(anchor="w",pady=(0,18))
        ttk.Label(self.tab_creditos,text=CREDITOS,justify="left",font=("Segoe UI",11)).pack(anchor="w")

    # ========================================================
    # ACCIONES
    # ========================================================

    def nuevo_caso(self):
        if self.expediente_actual and not messagebox.askyesno(APP,"Hay un caso activo. ¿Querés iniciar un caso nuevo? El expediente actual permanecerá guardado y no será modificado."):
            return
        self.expediente_actual=None;self.chat_actual=None;self.archivos=[]
        self.ocultar_vistas_resultado()
        try:
            self.nb.tab(self.tab_registro_visual,state="disabled")
            self.nb.tab(self.tab_entrega,state="disabled")
        except Exception:
            pass
        self.marcar_paso(1)
        self.lbl_caso_activo.config(text="Caso activo: ninguno");self.lbl_archivos.config(text="Ningún archivo seleccionado")
        for k,v in self.vars.items():
            if k=="id_caso":v.set("")
            elif k=="id_evidencia":v.set("EVD-"+datetime.now().strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:6].upper())
            elif k=="fecha":v.set(datetime.now().strftime("%d/%m/%Y"))
            elif k=="hora":v.set(datetime.now().strftime("%H:%M:%S"))
            elif k=="incluye_multimedia":v.set("Sí")
            elif k=="metodo":v.set("WhatsApp → Exportar chat")
            elif k!="zona_horaria":v.set("")
        self.nb.select(self.tab_preservar)

    def seleccionar_archivos(self):
        paths=filedialog.askopenfilenames(
            title="Seleccioná todos los archivos entregados por WhatsApp",
            filetypes=[("Todos los archivos","*.*")]
        )
        if paths:
            self.archivos=[Path(p).resolve() for p in paths]
            total=sum(p.stat().st_size for p in self.archivos)
            aux=sum(1 for p in self.archivos if "AUXILIAR" in clasificar_archivo(p)["clasificacion"])
            txt=f"{len(self.archivos)} archivo(s) — {total/1024/1024:.2f} MB"
            if aux:
                txt+=f" — {aux} auxiliar(es) detectado(s)"
            self.lbl_archivos.config(text=txt)

    def seleccionar_destino(self):
        p=filedialog.askdirectory(title="Carpeta donde guardar el expediente")
        if p:
            self.destino.set(p)

    def preservar(self):
        try:
            if not self.archivos:
                raise ValueError("Seleccioná al menos un archivo.")
            dst=directorio_expedientes()
            if any(not p.is_file() for p in self.archivos):
                raise ValueError("Uno de los archivos seleccionados no está disponible.")

            datos={k:v.get().strip() for k,v in self.vars.items()}
            obligatorios={
                "id_caso":"NOMBRE DEL CASO",
                "id_evidencia":"ID de evidencia",
                "marca":"Marca del dispositivo",
                "modelo":"Modelo",
                "sistema_operativo":"Sistema operativo",
                "imei":"IMEI",
                "version_whatsapp":"Versión de WhatsApp",
                "titular_whatsapp":"Titular de la cuenta de WhatsApp de origen",
                "numero_whatsapp":"Teléfono de la cuenta de WhatsApp de origen",
                "contacto_grupo":"Contacto / Grupo Auditado",
                "persona_exporto":"Persona / profesional / organización que realiza la exportación"
            }
            faltantes=[nombre for clave,nombre in obligatorios.items() if not datos.get(clave,"").strip()]
            if faltantes:
                raise ValueError("Complete los campos obligatorios:\n- " + "\n- ".join(faltantes))

            # Para compatibilidad con la bitácora y las actas internas, el responsable
            # se toma de quien declara haber realizado la exportación. No se pide dos veces.
            datos["responsable"]=datos.get("persona_exporto","")
            datos["identificacion_funcion"]=""
            datos["lugar"]=""
            datos["periodo"]=""  # Siempre automático.
            root,estado,recepcion,periodo=crear_expediente(self.archivos,dst,datos)

            # La carpeta de destino pasa a ser biblioteca sugerida.
            self.refrescar_expedientes()

            self.cargar_expediente(root)

            auxiliares=sum(1 for r in recepcion if "AUXILIAR" in r["clasificacion"])
            messagebox.showinfo(
                APP,
                "PRESERVACIÓN COMPLETADA\n\n"
                f"Archivos recibidos: {estado['archivos_recibidos']}\n"
                f"Auxiliares detectados: {auxiliares}\n"
                f"Período detectado: {periodo.get('periodo') or 'No detectado'}\n"
                f"Integridad: {estado['integridad']}"
            )
            actualizar_estado_flujo(root,paso_1_completado=True,paso_2_completado=False,entrega_generada=False)
            self.habilitar_paso2()

        except Exception as e:
            messagebox.showerror(APP,str(e))

    def cargar_expediente(self,root):
        root=Path(root)
        if not (root/"02_INTEGRIDAD"/"MANIFIESTO.json").exists():
            raise ValueError("No es un expediente PreservarChat compatible.")

        rep=verificar_expediente(root,guardar_reporte=True)
        self.expediente_actual=root

        self.lbl_exp_act.config(text=root.name)
        self.lbl_verificar.config(text=root.name)
        self.lbl_actas.config(text=root.name)
        self.lbl_entrega.config(text=root.name)
        self.lbl_rv_estado.config(text=root.name)
        self.lbl_caso_activo.config(text=f"Caso activo: {root.name}")

        self.cargar_actividad(root)
        self.cargar_chat(root,rep)
        self.cargar_multimedia(root,rep)
        self.cargar_registro_visual(root,rep)
        self.cargar_actas(root)
        self.mostrar_verificacion(rep)

        estado_flujo=leer_estado_flujo(root)
        if estado_flujo.get("entrega_generada"):
            self.nb.tab(self.tab_registro_visual,state="normal")
            self.nb.tab(self.tab_entrega,state="normal")
            self.mostrar_vistas_resultado()
            self.marcar_paso(4)
        else:
            self.nb.tab(self.tab_registro_visual,state="normal")
            self.nb.tab(self.tab_entrega,state="normal")
            self.ocultar_vistas_resultado()
            self.marcar_paso(2,"CASO EN PREPARACIÓN · COMPLETE REGISTRO VISUAL Y ENTREGA")

    # ---------- Actividad

    def cargar_actividad(self,root):
        resumen,etapas=construir_actividad(root)
        self.actividad.config(state="normal")
        self.actividad.delete("1.0","end")
        self.actividad.insert("end","RESUMEN DEL EXPEDIENTE\n","titulo")
        self.actividad.insert("end","="*86+"\n")
        for k,v in resumen:
            self.actividad.insert("end",f"{k}: ","subtitulo")
            self.actividad.insert("end",f"{v}\n","hash" if "SHA-256" in k else None)
        self.actividad.insert("end","\nPROCEDIMIENTO REALIZADO\n","titulo")
        self.actividad.insert("end","="*86+"\n\n")

        for e in etapas:
            marca="✓" if e["estado"]=="OK" else "⚠"
            self.actividad.insert("end",f"{marca} {e['titulo']}\n","ok" if e["estado"]=="OK" else "alerta")
            self.actividad.insert("end",e["descripcion"]+"\n")
            for d in e["detalles"]:
                if "SHA-256:" in str(d):
                    antes,despues=str(d).split("SHA-256:",1)
                    if antes.strip():
                        self.actividad.insert("end","   • "+antes.strip()+"\n")
                    self.actividad.insert("end","     SHA-256: "+despues.strip()+"\n","hash")
                else:
                    self.actividad.insert("end","   • "+str(d)+"\n")
            self.actividad.insert("end","\n")

        self.actividad.config(state="disabled")

    # ---------- Chat

    def cargar_chat(self,root,rep):
        self.chat_text.config(state="normal")
        self.chat_text.delete("1.0","end")
        self.chat_images=[]
        self.mensajes_actuales=[]
        self.posiciones_busqueda=[]
        self.lbl_busqueda_chat.config(text="")

        if rep["resultado"]!="INTEGRIDAD VERIFICADA":
            self.chat_actual=None
            self.lbl_chat_contacto.config(text="Conversación no disponible"); self.lbl_chat_estado.config(text="Integridad no verificada")
            self.chat_text.insert("end","⚠ La lectura fue bloqueada porque la integridad del expediente no pudo verificarse.","sistema")
            self.chat_text.config(state="disabled")
            return

        chat=encontrar_chat_principal(root)
        if not chat:
            self.chat_actual=None
            self.lbl_chat_contacto.config(text="Conversación no disponible"); self.lbl_chat_estado.config(text="No se encontró historial TXT")
            self.chat_text.insert("end","No se encontró un historial TXT dentro de 03_COPIA_DE_TRABAJO.","sistema")
            self.chat_text.config(state="disabled")
            return

        self.chat_actual=chat
        self.mensajes_actuales=parsear_chat(chat)
        ficha_chat=leer_ficha(root)
        datos_chat=ficha_chat.get("datos",{})
        contacto=datos_chat.get("contacto_grupo","") or "Conversación de WhatsApp"
        periodo=datos_chat.get("periodo","") or "Período no determinado"
        self.lbl_chat_contacto.config(text=contacto)
        self.lbl_chat_estado.config(text=f"Modo solo lectura · {periodo} · copia de trabajo verificada")
        media_idx=indexar_media_chat(root)

        autores=[]
        for m in self.mensajes_actuales:
            a=m["autor"]
            if a not in autores and a!="Sistema":
                autores.append(a)

        ultima_fecha=None
        for m in self.mensajes_actuales:
            autor=m["autor"]
            fecha=m.get("fecha","")
            if fecha and fecha!=ultima_fecha:
                self.chat_text.insert("end","\n")
                self.chat_text.insert("end",f"  {fecha}  \n","fecha_sep")
                self.chat_text.insert("end","\n")
                ultima_fecha=fecha

            if autor=="Sistema":
                self.chat_text.insert("end",m.get("texto","")+"\n\n","sistema")
                continue

            idx=autores.index(autor) if autor in autores else 0
            lado="izq" if idx%2==0 else "der"
            inicio=self.chat_text.index("end-1c")
            self.chat_text.insert("end",f"{autor}\n",("autor",lado))

            adjuntos=media_referenciada(m.get("texto",""),media_idx)
            texto_visible=m.get("texto","")
            self.chat_text.insert("end",texto_visible+"\n",lado)

            for p in adjuntos:
                if not dentro_de(p,Path(root)/"03_COPIA_DE_TRABAJO"):
                    continue
                ext=p.suffix.lower()
                if ext in EXT_IMAGEN and PIL_DISPONIBLE:
                    try:
                        im=Image.open(p)
                        im.thumbnail((360,280))
                        photo=ImageTk.PhotoImage(im.copy())
                        self.chat_images.append(photo)
                        self.chat_text.image_create("end",image=photo,padx=8,pady=4)
                        self.chat_text.insert("end","\n")
                        b=ttk.Button(self.chat_text,style="ChatMedia.TButton",text=f"🖼  Ver imagen · {p.name}",command=lambda q=p:self.abrir_media_chat(q))
                        self.chat_text.window_create("end",window=b,padx=8,pady=3)
                        self.chat_text.insert("end","\n")
                    except Exception:
                        b=ttk.Button(self.chat_text,style="ChatMedia.TButton",text=f"🖼  Ver imagen · {p.name}",command=lambda q=p:self.abrir_media_chat(q))
                        self.chat_text.window_create("end",window=b,padx=8,pady=3);self.chat_text.insert("end","\n")
                elif ext in EXT_AUDIO:
                    b=ttk.Button(self.chat_text,style="ChatMedia.TButton",text=f"▶  Reproducir audio · {p.name}",command=lambda q=p:self.abrir_media_chat(q))
                    self.chat_text.window_create("end",window=b,padx=8,pady=3);self.chat_text.insert("end","\n")
                elif ext in EXT_VIDEO:
                    b=ttk.Button(self.chat_text,style="ChatMedia.TButton",text=f"▶  Reproducir video · {p.name}",command=lambda q=p:self.abrir_media_chat(q))
                    self.chat_text.window_create("end",window=b,padx=8,pady=3);self.chat_text.insert("end","\n")
                else:
                    b=ttk.Button(self.chat_text,style="ChatMedia.TButton",text=f"📄  Abrir documento · {p.name}",command=lambda q=p:self.abrir_media_chat(q))
                    self.chat_text.window_create("end",window=b,padx=8,pady=3);self.chat_text.insert("end","\n")

            meta=" · ".join(x for x in [m.get("hora","")] if x)
            if meta:
                self.chat_text.insert("end",meta+"\n",("hora",lado))
            self.chat_text.insert("end","\n")
            fin=self.chat_text.index("end-1c")
            self.chat_text.tag_add(lado,inicio,fin)

        self.chat_text.config(state="disabled")

    def abrir_media_chat(self,path):
        if not self.expediente_actual:
            return
        base=self.expediente_actual/"03_COPIA_DE_TRABAJO"
        if not dentro_de(path,base):
            messagebox.showerror(APP,"Lectura bloqueada: el archivo no pertenece a COPIA_DE_TRABAJO.")
            return
        try:
            abrir_archivo_seguro(path)
        except Exception as e:
            messagebox.showerror(APP,str(e))

    def buscar_chat(self):
        termino=self.buscar_chat_var.get().strip()
        self.posiciones_busqueda=[]
        self.indice_busqueda=0
        self.chat_text.config(state="normal")
        self.chat_text.tag_remove("busqueda","1.0","end")

        if not termino:
            self.lbl_busqueda_chat.config(text="")
            self.chat_text.config(state="disabled")
            return

        pos="1.0"
        while True:
            pos=self.chat_text.search(termino,pos,stopindex="end",nocase=True)
            if not pos:
                break
            fin=f"{pos}+{len(termino)}c"
            self.chat_text.tag_add("busqueda",pos,fin)
            self.posiciones_busqueda.append(pos)
            pos=fin

        self.chat_text.config(state="disabled")

        if self.posiciones_busqueda:
            self.lbl_busqueda_chat.config(text=f"{len(self.posiciones_busqueda)} coincidencia(s)")
            self.chat_text.see(self.posiciones_busqueda[0])
        else:
            self.lbl_busqueda_chat.config(text="Sin coincidencias")

    def buscar_siguiente(self):
        if not self.posiciones_busqueda:
            self.buscar_chat()
            return
        self.indice_busqueda=(self.indice_busqueda+1)%len(self.posiciones_busqueda)
        self.chat_text.see(self.posiciones_busqueda[self.indice_busqueda])
        self.lbl_busqueda_chat.config(
            text=f"{self.indice_busqueda+1}/{len(self.posiciones_busqueda)}"
        )

    # ---------- Multimedia

    def cargar_multimedia(self,root,rep):
        if rep["resultado"]!="INTEGRIDAD VERIFICADA":
            self.multimedia_actual=[]
            self.lbl_multimedia_estado.config(text="⚠ Bloqueado por integridad")
            self.refrescar_tree_mult([])
            return

        self.multimedia_actual=listar_multimedia(root)
        self.lbl_multimedia_estado.config(text=f"{len(self.multimedia_actual)} archivo(s) · COPIA DE TRABAJO")
        self.mult_buscar.set("")
        self.mult_tipo.set("Todos")
        self.filtrar_multimedia()

    def filtrar_multimedia(self):
        q=self.mult_buscar.get().strip().lower()
        tipo=self.mult_tipo.get()
        self.multimedia_filtrada=[
            x for x in self.multimedia_actual
            if (not q or q in x["nombre"].lower())
            and (tipo=="Todos" or x["tipo"]==tipo)
        ]
        self.refrescar_tree_mult(self.multimedia_filtrada)

    def refrescar_tree_mult(self,items):
        for i in self.tree_mult.get_children():
            self.tree_mult.delete(i)
        for idx,x in enumerate(items):
            self.tree_mult.insert(
                "","end",iid=str(idx),
                values=(x["nombre"],x["tipo"],f"{x['tamano']/1024:.1f} KB",x["ruta_relativa"])
            )
        self.preview_img.config(image="",text="Seleccione un archivo")
        self.preview_info.config(text="")
        self.imagen_preview=None

    def multimedia_seleccionado(self):
        sel=self.tree_mult.selection()
        if not sel:
            return None
        idx=int(sel[0])
        if idx<0 or idx>=len(self.multimedia_filtrada):
            return None
        return self.multimedia_filtrada[idx]

    def preview_multimedia(self):
        x=self.multimedia_seleccionado()
        if not x:
            return

        self.preview_info.config(
            text=f"Archivo: {x['nombre']}\nTipo: {x['tipo']}\nTamaño: {x['tamano']} bytes\nRuta: {x['ruta_relativa']}"
        )

        if x["tipo"]=="Imagen" and PIL_DISPONIBLE:
            try:
                im=Image.open(x["path"])
                im.thumbnail((420,420))
                self.imagen_preview=ImageTk.PhotoImage(im)
                self.preview_img.config(image=self.imagen_preview,text="")
                return
            except Exception:
                pass

        self.preview_img.config(image="",text=f"{x['tipo']}\n\nDoble clic o use “Abrir archivo de copia”.")

    def abrir_multimedia(self):
        x=self.multimedia_seleccionado()
        if not x or not self.expediente_actual:
            return
        base=self.expediente_actual/"03_COPIA_DE_TRABAJO"
        if not dentro_de(x["path"],base):
            messagebox.showerror(APP,"Lectura bloqueada: el archivo no pertenece a COPIA_DE_TRABAJO.")
            return
        try:
            abrir_archivo_seguro(x["path"])
        except Exception as e:
            messagebox.showerror(APP,str(e))

    # ---------- Registro visual

    def cargar_registro_visual(self,root,rep):
        self.registro_visual_actual=leer_registro_visual(root) if rep.get('resultado')=='INTEGRIDAD VERIFICADA' else []
        for i in self.tree_rv.get_children():self.tree_rv.delete(i)
        for idx,x in enumerate(self.registro_visual_actual):
            self.tree_rv.insert('', 'end', iid=str(idx), values=(x.get('orden'),x.get('id_registro'),x.get('tipo'),x.get('nombre_original'),x.get('fecha_hora_incorporacion_local'),x.get('fecha_hora_metadatos') or 'No disponible',x.get('descripcion')))
        self.lbl_rv_estado.config(text=f"{len(self.registro_visual_actual)} elemento(s)" if self.expediente_actual else 'Sin expediente activo')
        self.rv_preview.config(image='',text='Seleccione un elemento');self.rv_info.config(text='');self.rv_preview_image=None

    def agregar_registro_visual_ui(self):
        if not self.expediente_actual:
            messagebox.showinfo(APP,'Primero cree o abra un caso.');return
        paths=filedialog.askopenfilenames(title='Seleccione material complementario',filetypes=[('Material admitido','*.jpg *.jpeg *.png *.webp *.bmp *.gif *.mp4 *.mov *.avi *.mkv *.3gp *.webm *.mp3 *.wav *.ogg *.opus *.m4a *.aac *.amr *.pdf *.doc *.docx *.odt *.rtf *.xls *.xlsx *.xlsm *.ods *.csv'),('Documentos','*.pdf *.doc *.docx *.odt *.rtf *.xls *.xlsx *.xlsm *.ods *.csv'),('Imágenes y multimedia','*.jpg *.jpeg *.png *.webp *.bmp *.gif *.mp4 *.mov *.avi *.mkv *.3gp *.webm *.mp3 *.wav *.ogg *.opus *.m4a *.aac *.amr'),('Todos','*.*')])
        if not paths:return
        ficha=leer_ficha(self.expediente_actual);responsable=ficha.get('datos',{}).get('responsable','')
        agregados=0
        for p in paths:
            while True:
                resp=simpledialog.askstring(
                    'Descripción del registro',
                    f"Describa brevemente qué documenta este archivo:\n\n{Path(p).name}",
                    parent=self
                )
                if resp is None:
                    desc=''
                    if not messagebox.askyesno(
                        APP,
                        'No se ingresó una descripción.\n\nSe recomienda describir brevemente qué muestra o documenta el material para facilitar su identificación posterior.\n\n¿Querés continuar sin descripción?'
                    ):
                        continue
                    break
                desc=resp.strip()
                if desc:
                    break
                if messagebox.askyesno(
                    APP,
                    'La descripción quedó vacía.\n\nSe recomienda indicar algo acorde al material, por ejemplo: “Perfil del contacto exportado”, “Pantalla de información de la cuenta” o “Registro del procedimiento de exportación”.\n\n¿Querés continuar sin descripción?'
                ):
                    break
            try:
                incorporar_registro_visual(self.expediente_actual,Path(p),desc,responsable);agregados+=1
            except ValueError as e:
                messagebox.showwarning(APP,str(e))
            except Exception as e:
                messagebox.showerror(APP,f"No se pudo incorporar {Path(p).name}:\n{e}")
        rep=verificar_expediente(self.expediente_actual,guardar_reporte=True)
        self.cargar_registro_visual(self.expediente_actual,rep);self.cargar_actas(self.expediente_actual);self.mostrar_verificacion(rep);self.cargar_actividad(self.expediente_actual)
        if agregados:messagebox.showinfo(APP,f'Se incorporaron {agregados} archivo(s) de material complementario. Se regeneraron las actas y el manifiesto.')

    def rv_seleccionado(self):
        sel=self.tree_rv.selection()
        if not sel:return None
        idx=int(sel[0]);return self.registro_visual_actual[idx] if 0<=idx<len(self.registro_visual_actual) else None

    def preview_registro_visual(self):
        x=self.rv_seleccionado()
        if not x or not self.expediente_actual:return
        p=self.expediente_actual/x.get('ruta_copia','')
        self.rv_info.config(text=f"{x.get('id_registro')} · {x.get('tipo')}\nArchivo: {x.get('nombre_original')}\nDescripción: {x.get('descripcion')}\nIncorporado: {x.get('fecha_hora_incorporacion_local')}\nFecha en metadatos: {x.get('fecha_hora_metadatos') or 'No disponible'}\nFuente: {x.get('fuente_fecha_metadatos')}\nSHA-256: {x.get('sha256')}")
        if x.get('tipo')=='Imagen' and PIL_DISPONIBLE and p.exists():
            try:
                im=Image.open(p);im.thumbnail((430,430));self.rv_preview_image=ImageTk.PhotoImage(im);self.rv_preview.config(image=self.rv_preview_image,text='');return
            except Exception:pass
        self.rv_preview.config(image='',text=f"{x.get('tipo')}\n\nDoble clic o use ABRIR COPIA DE CONSULTA")

    def abrir_registro_visual(self):
        x=self.rv_seleccionado()
        if not x or not self.expediente_actual:return
        p=self.expediente_actual/x.get('ruta_copia','');base=self.expediente_actual/'10_REGISTRO_VISUAL'/'02_COPIAS_DE_CONSULTA'
        if not dentro_de(p,base):messagebox.showerror(APP,'Lectura bloqueada: la ruta no pertenece a la copia de consulta del Registro Visual.');return
        try:abrir_archivo_seguro(p)
        except Exception as e:messagebox.showerror(APP,str(e))


    def editar_registro_visual_ui(self):
        x=self.rv_seleccionado()
        if not x or not self.expediente_actual:
            messagebox.showinfo(APP,'Seleccione un elemento del Registro Visual.')
            return
        nueva=simpledialog.askstring(
            'Editar descripción',
            f"{x.get('id_registro')} — {x.get('nombre_original')}\n\nDescripción:",
            initialvalue=x.get('descripcion',''),
            parent=self
        )
        if nueva is None:
            return
        ficha=leer_ficha(self.expediente_actual)
        responsable=ficha.get('datos',{}).get('responsable','')
        try:
            editar_descripcion_registro_visual(self.expediente_actual,x.get('id_registro'),nueva,responsable)
            rep=verificar_expediente(self.expediente_actual,guardar_reporte=True)
            self.cargar_registro_visual(self.expediente_actual,rep)
            self.cargar_actas(self.expediente_actual)
            self.cargar_actividad(self.expediente_actual)
            self.mostrar_verificacion(rep)
        except Exception as e:
            messagebox.showerror(APP,str(e))

    def reemplazar_registro_visual_ui(self):
        x=self.rv_seleccionado()
        if not x or not self.expediente_actual:
            messagebox.showinfo(APP,'Seleccione un elemento del Registro Visual.')
            return
        nuevo=filedialog.askopenfilename(
            title=f"Reemplazar {x.get('id_registro')}",
            filetypes=[('Material admitido','*.jpg *.jpeg *.png *.webp *.bmp *.gif *.mp4 *.mov *.avi *.mkv *.3gp *.webm *.mp3 *.wav *.ogg *.opus *.m4a *.aac *.amr *.pdf *.doc *.docx *.odt *.rtf *.xls *.xlsx *.xlsm *.ods *.csv'),('Documentos','*.pdf *.doc *.docx *.odt *.rtf *.xls *.xlsx *.xlsm *.ods *.csv'),('Todos','*.*')]
        )
        if not nuevo:
            return
        if not messagebox.askyesno(
            APP,
            f"¿Reemplazar {x.get('id_registro')}?\n\n"
            f"Archivo actual: {x.get('nombre_original')}\n"
            f"Nuevo archivo: {Path(nuevo).name}\n\n"
            "La sustitución quedará registrada en la bitácora con el hash anterior y el nuevo."
        ):
            return
        ficha=leer_ficha(self.expediente_actual)
        responsable=ficha.get('datos',{}).get('responsable','')
        try:
            reemplazar_registro_visual(self.expediente_actual,x.get('id_registro'),Path(nuevo),responsable)
            rep=verificar_expediente(self.expediente_actual,guardar_reporte=True)
            self.cargar_registro_visual(self.expediente_actual,rep)
            self.cargar_actas(self.expediente_actual)
            self.cargar_actividad(self.expediente_actual)
            self.mostrar_verificacion(rep)
            messagebox.showinfo(APP,f"{x.get('id_registro')} fue reemplazado y se recalcularon sus hashes.")
        except Exception as e:
            messagebox.showerror(APP,str(e))

    def eliminar_registro_visual_ui(self):
        x=self.rv_seleccionado()
        if not x or not self.expediente_actual:
            messagebox.showinfo(APP,'Seleccione un elemento del Registro Visual.')
            return
        if not messagebox.askyesno(
            APP,
            f"¿Eliminar {x.get('id_registro')} del Registro Visual?\n\n"
            f"Archivo: {x.get('nombre_original')}\n"
            f"SHA-256: {x.get('sha256')}\n\n"
            "El elemento se quitará del Registro Visual activo y de la entrega. Para mantener trazabilidad, el archivo quedará preservado en un área interna de auditoría NO ENTREGAR y la acción se registrará en la bitácora."
        ):
            return
        ficha=leer_ficha(self.expediente_actual)
        responsable=ficha.get('datos',{}).get('responsable','')
        try:
            eliminar_registro_visual(self.expediente_actual,x.get('id_registro'),responsable)
            rep=verificar_expediente(self.expediente_actual,guardar_reporte=True)
            self.cargar_registro_visual(self.expediente_actual,rep)
            self.cargar_actas(self.expediente_actual)
            self.cargar_actividad(self.expediente_actual)
            self.mostrar_verificacion(rep)
            messagebox.showinfo(APP,'Elemento retirado del Registro Visual activo. No formará parte de la entrega y quedó preservado en el área interna de auditoría.')
        except Exception as e:
            messagebox.showerror(APP,str(e))

    # ---------- Expedientes

    def refrescar_expedientes(self):
        for i in self.tree_exp.get_children(): self.tree_exp.delete(i)
        try: items=buscar_expedientes(directorio_expedientes())
        except Exception as e:
            self.resultados_expedientes=[];self.lbl_exp_info.config(text=f"Error: {e}");return
        q=self.exp_buscar.get().strip().lower() if hasattr(self,"exp_buscar") else ""
        if q:
            items=[x for x in items if q in " ".join([x.get("caso",""),x.get("evidencia",""),x.get("contacto",""),x.get("periodo","")]).lower()]
        self.resultados_expedientes=items
        for idx,x in enumerate(items): self.tree_exp.insert("","end",iid=str(idx),values=(x["caso"],x["evidencia"],x["contacto"],x["periodo"],x["integridad"]))
        self.lbl_exp_info.config(text=f"{len(items)} caso(s)")

    def expediente_seleccionado(self):
        sel=self.tree_exp.selection()
        if not sel:
            messagebox.showinfo(APP,"Seleccioná un caso de la lista.");return None
        return self.resultados_expedientes[int(sel[0])]

    def abrir_caso(self):
        x=self.expediente_seleccionado()
        if not x:
            return
        try:
            self.cargar_expediente(x["ruta"])
            messagebox.showinfo(
                APP,
                "Caso cargado correctamente.\n\n"
                "PreservarChat verificó la integridad del caso. Si la entrega ya fue generada, se habilitan las vistas de consulta; de lo contrario, el flujo continúa desde Registro Visual / Entrega."
            )
        except Exception as e:
            messagebox.showerror(APP,str(e))

    def eliminar_expediente_ui(self):
        x=self.expediente_seleccionado()
        if not x:
            return
        ruta=Path(x.get("ruta","")).resolve()
        base=directorio_expedientes().resolve()
        try:
            ruta.relative_to(base)
        except Exception:
            messagebox.showerror(APP,"Por seguridad, sólo pueden eliminarse expedientes ubicados dentro de la carpeta administrada por PreservarChat.")
            return
        if ruta == base or not ruta.exists() or not ruta.is_dir():
            messagebox.showerror(APP,"El expediente seleccionado no es válido o ya no existe.")
            return
        caso=x.get("caso",ruta.name)
        evidencia=x.get("evidencia","")
        texto=(
            f"¿Eliminar definitivamente este expediente?\n\n"
            f"Caso: {caso}\n"
            f"Evidencia: {evidencia}\n\n"
            "Se eliminarán del sistema todos los archivos internos asociados a este expediente. Esta acción no se puede deshacer."
        )
        if not messagebox.askyesno("Confirmar eliminación",texto,icon="warning",parent=self):
            return
        try:
            era_activo=False
            if self.expediente_actual:
                try: era_activo=self.expediente_actual.resolve()==ruta
                except Exception: pass
            shutil.rmtree(ruta)
            if era_activo:
                self.expediente_actual=None
                self.nuevo_caso()
            self.refrescar_expedientes()
            messagebox.showinfo(APP,"Expediente eliminado correctamente.")
        except Exception as e:
            messagebox.showerror(APP,f"No se pudo eliminar el expediente:\n\n{e}")

    # ---------- Verificar

    def mostrar_verificacion(self,rep):
        self.salida.config(state="normal");self.salida.delete("1.0","end")
        ok=rep.get("resultado")=="INTEGRIDAD VERIFICADA"
        self.lbl_ver_estado.config(text="✓ INTEGRIDAD VERIFICADA" if ok else "⚠ SE DETECTARON INCIDENCIAS")
        self.salida.insert("end","QUÉ SE VERIFICA\n","titulo")
        self.salida.insert("end","Se recalcula el SHA-256 de cada archivo registrado y se compara con el valor almacenado en el manifiesto.\n\n")
        self.salida.insert("end","RESULTADO GENERAL\n","titulo");self.salida.insert("end",rep.get("resultado","")+"\n\n","ok" if ok else "bad")
        self.salida.insert("end","DETALLE POR ARCHIVO\n","titulo");self.salida.insert("end","-"*95+"\n")
        for r in rep.get("archivos",[]):
            tag="ok" if r.get("estado")=="INTEGRO" else "bad"
            self.salida.insert("end",f"{r.get('estado',''):10} ",tag);self.salida.insert("end",f"{r.get('archivo','')}\n")
        self.salida.insert("end","\nINTERPRETACIÓN\n","titulo")
        self.salida.insert("end","ÍNTEGRO: el SHA-256 actual coincide con el registrado.\nFALTANTE: el archivo documentado no está disponible.\nMODIFICADO: el contenido actual no coincide con el hash documentado.\n")
        self.salida.config(state="disabled")

    def verificar_activo(self):
        if not self.expediente_actual:
            messagebox.showinfo(APP,"No hay un expediente activo.")
            return
        try:
            rep=verificar_expediente(self.expediente_actual,guardar_reporte=True)
            self.mostrar_verificacion(rep)
            # Reaplicar bloqueos o habilitaciones.
            self.cargar_chat(self.expediente_actual,rep)
            self.cargar_multimedia(self.expediente_actual,rep)
            self.cargar_registro_visual(self.expediente_actual,rep)
        except Exception as e:
            messagebox.showerror(APP,str(e))

    # ---------- Actas

    def cargar_actas(self,root):
        base=root/"05_ACTAS"
        if base.exists():
            actas=list(base.glob("*.pdf"))
            self.actas_actuales=sorted(actas,key=lambda p:("ACTA_FINAL_DE_ENTREGA" in p.name.upper(),p.name.upper()))
        else:
            self.actas_actuales=[]
        self.lista_actas.delete(0,"end")
        for p in self.actas_actuales:self.lista_actas.insert("end",p.name)
        self.acta_actual=None;self.pdf_doc=None;self.pdf_pagina=0;self.pdf_imagen=None;self.pdf_canvas.delete("all");self.lbl_pdf_pagina.config(text="")
        if self.actas_actuales:
            self.lista_actas.selection_set(0);self.preview_acta()

    def preview_acta(self):
        sel=self.lista_actas.curselection()
        if not sel:return
        self.acta_actual=self.actas_actuales[sel[0]];self.pdf_pagina=0
        if not FITZ_DISPONIBLE or not PIL_DISPONIBLE:
            self.pdf_canvas.delete("all");self.pdf_canvas.create_text(20,20,anchor="nw",text="Vista PDF no disponible. Use ABRIR para visualizar el acta.",font=("Segoe UI",11));return
        try:
            if self.pdf_doc:self.pdf_doc.close()
            self.pdf_doc=fitz.open(str(self.acta_actual));self.render_pdf_pagina()
        except Exception as e:
            self.pdf_canvas.delete("all");self.pdf_canvas.create_text(20,20,anchor="nw",text=f"No se pudo mostrar el PDF: {e}")

    def render_pdf_pagina(self):
        if not self.pdf_doc:return
        self.pdf_pagina=max(0,min(self.pdf_pagina,len(self.pdf_doc)-1));page=self.pdf_doc.load_page(self.pdf_pagina)
        pix=page.get_pixmap(matrix=fitz.Matrix(1.35,1.35),alpha=False);im=Image.frombytes("RGB",[pix.width,pix.height],pix.samples)
        self.pdf_imagen=ImageTk.PhotoImage(im);self.pdf_canvas.delete("all");self.pdf_canvas.create_image(8,8,anchor="nw",image=self.pdf_imagen)
        self.pdf_canvas.configure(scrollregion=(0,0,pix.width+16,pix.height+16));self.lbl_pdf_pagina.config(text=f"Página {self.pdf_pagina+1} de {len(self.pdf_doc)}")
        self.pdf_canvas.xview_moveto(0);self.pdf_canvas.yview_moveto(0)

    def pdf_anterior(self):
        if self.pdf_doc and self.pdf_pagina>0:self.pdf_pagina-=1;self.render_pdf_pagina()
    def pdf_siguiente(self):
        if self.pdf_doc and self.pdf_pagina<len(self.pdf_doc)-1:self.pdf_pagina+=1;self.render_pdf_pagina()
    def abrir_acta(self):
        if self.acta_actual:
            try:abrir_archivo_seguro(self.acta_actual)
            except Exception as e:messagebox.showerror(APP,str(e))
    def explorar_acta(self):
        if self.acta_actual:
            try:mostrar_en_explorador(self.acta_actual)
            except Exception as e:messagebox.showerror(APP,str(e))
    def imprimir_acta(self):
        if not self.acta_actual:return
        try:
            if sys.platform.startswith("win"):os.startfile(str(self.acta_actual),"print")
            else:abrir_archivo_seguro(self.acta_actual)
        except Exception:
            try:abrir_archivo_seguro(self.acta_actual);messagebox.showinfo(APP,"Se abrió el PDF. Use la opción Imprimir del visor.")
            except Exception as e:messagebox.showerror(APP,str(e))

    # ---------- Entrega

    def mostrar_archivo_generado(self):
        """Confirmación final limpia: los detalles permanecen visibles en la pantalla Entrega."""
        win=tk.Toplevel(self)
        win.title(APP)
        win.transient(self)
        win.resizable(False,False)
        win.configure(bg="#FFFFFF")
        win.grab_set()
        caja=tk.Frame(win,bg="#FFFFFF",padx=34,pady=26)
        caja.pack(fill="both",expand=True)
        tk.Label(caja,text="✓",font=("Segoe UI",26,"bold"),fg="#176B55",bg="#FFFFFF").pack(pady=(0,4))
        tk.Label(caja,text="Archivo generado correctamente",font=("Segoe UI",13,"bold"),fg="#17242D",bg="#FFFFFF").pack()
        tk.Label(caja,text="La entrega quedó disponible en la carpeta de Entregas.",font=("Segoe UI",9),fg="#60727B",bg="#FFFFFF").pack(pady=(5,16))
        botones=tk.Frame(caja,bg="#FFFFFF");botones.pack()
        ttk.Button(botones,text="ABRIR CARPETA",command=lambda:(abrir_carpeta(directorio_entregas()),win.destroy())).pack(side="left",padx=4)
        ttk.Button(botones,text="CERRAR",style="Primary.TButton",command=win.destroy).pack(side="left",padx=4)
        win.update_idletasks()
        x=self.winfo_rootx()+(self.winfo_width()-win.winfo_width())//2
        y=self.winfo_rooty()+(self.winfo_height()-win.winfo_height())//2
        win.geometry(f"+{max(x,0)}+{max(y,0)}")
        win.focus_force()

    def generar_entrega_ui(self):
        if not self.expediente_actual:
            messagebox.showinfo(APP,"No hay un expediente activo.")
            return
        try:
            destino=directorio_entregas()
            resultado=generar_entrega(self.expediente_actual,destino)
            self.ultima_entrega=resultado
            self.entrega_info.config(state="normal")
            self.entrega_info.delete("1.0","end")
            texto_entrega=(
                "ENTREGA OFICIAL GENERADA\n\n"
                f"Archivos de WhatsApp: {resultado.get('archivos_chat',0)}\n"
                f"Elementos de Registro Visual: {resultado.get('registro_visual',0)}\n\n"
                f"ZIP oficial:\n{resultado['zip']}\n\n"
                f"SHA-256 DEL ZIP OFICIAL:\n{resultado['sha256_zip']}\n\n"
                f"Acta Final externa:\n{resultado['acta']}\n\n"
                f"Archivo externo con el hash:\n{resultado['hash_txt']}\n\n"
                f"SHA-256 de 01 CHAT EXPORTADO.zip:\n{resultado['hash_chat_zip']}\n\n"
            )
            if resultado.get('hash_rv_zip'):
                texto_entrega += f"SHA-256 de 02 REGISTRO VISUAL.zip:\n{resultado['hash_rv_zip']}\n\n"
            texto_entrega += "La entrega fue cerrada correctamente. El Acta Final se encuentra fuera del ZIP oficial y puede ser firmada posteriormente por el usuario mediante el mecanismo que corresponda en su jurisdicción, sin que esa firma forme parte del funcionamiento de PreservarChat.\n"
            self.entrega_info.insert("end",texto_entrega)
            self.entrega_info.config(state="disabled")
            actualizar_estado_flujo(
                self.expediente_actual,
                paso_1_completado=True,
                paso_2_completado=True,
                entrega_generada=True,
                entrega_zip=str(resultado["zip"]),
                entrega_sha256=resultado["sha256_zip"],
                entrega_hash_txt=str(resultado["hash_txt"])
            )
            self.cargar_actas(self.expediente_actual)
            self.mostrar_vistas_resultado()
            self.marcar_paso(4)
            self.nb.select(self.tab_entrega)
            self.mostrar_archivo_generado()
        except Exception as e:
            messagebox.showerror(APP,str(e))

if __name__=="__main__":
    App().mainloop()
