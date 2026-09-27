"""
Plantation - WeasyPrint PDF Dossier Generator
Generates valid, printable PDF documents (PDF-1.4 standard)
in dark mode aesthetic (Catppuccin Mocha/Macchiato with red accents)
with Spanish titles, subtitles, technical botanical cards, and visual photo previews.
Created only on demand when downloaded.
"""

import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional
import weasyprint

from img_conv import IMAGES_DIR

STATUS_COLORS = {
    "OK": ("#a6da95", "#1e332a", "OK"),
    "notOK": ("#f5a97f", "#3a2e28", "notOK"),
    "Ok": ("#a6da95", "#1e332a", "OK"),
    "Triving": ("#a6da95", "#1e332a", "OK"),
    "Disease": ("#f5a97f", "#3a2e28", "notOK"),
    "Diseaced": ("#f5a97f", "#3a2e28", "notOK"),
    "Extremely Ill": ("#f5a97f", "#3a2e28", "notOK")
}


def get_image_data_uri(filename: str) -> Optional[str]:
    """Reads an image from disk and converts it to a base64 data URI for WeasyPrint."""
    if not filename:
        return None
    path = os.path.join(IMAGES_DIR, os.path.basename(filename))
    if not os.path.exists(path) or not os.path.isfile(path):
        return None

    ext = os.path.splitext(filename)[1].lower()
    mime = "image/jpeg"
    if ext in (".png",):
        mime = "image/png"
    elif ext in (".webp",):
        mime = "image/webp"
    elif ext in (".avif",):
        mime = "image/avif"

    try:
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def get_pdf_css() -> str:
    """CSS stylesheet for WeasyPrint conforming to Catppuccin dark mode with red accents."""
    return """
    @page {
        size: A4;
        margin: 1.5cm 1.2cm 1.8cm 1.2cm;
        background-color: #181926;
        @bottom-right {
            content: "PÁG " counter(page) " / " counter(pages);
            font-family: 'Maple Mono', 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 8pt;
            color: #939ab7;
        }
        @bottom-left {
            content: "PLANTATION // EXPEDIENTE ";
            font-family: 'Maple Mono', 'JetBrains Mono', 'Fira Code', monospace;
            font-size: 8pt;
            color: #ed8796;
        }
    }

    body {
        background-color: #181926;
        color: #cad3f5;
        font-family: 'Maple Mono', 'JetBrains Mono', 'Courier New', monospace;
        font-size: 9.5pt;
        line-height: 1.45;
        margin: 0;
        padding: 0;
    }

    .header-banner {
        border-bottom: 2px solid #ed8796;
        padding-bottom: 12px;
        margin-bottom: 20px;
    }

    .header-title-box {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }

    .app-tag {
        color: #ed8796;
        font-size: 8pt;
        font-weight: bold;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 4px;
    }

    .main-title {
        color: #f4dbd6;
        font-size: 18pt;
        font-weight: 700;
        margin: 0 0 4px 0;
        letter-spacing: 1px;
    }

    .sub-title {
        color: #a5adcb;
        font-size: 9.5pt;
        margin: 0;
    }

    .meta-box {
        text-align: right;
        font-size: 8pt;
        color: #8087a2;
    }

    .card {
        background-color: #24273a;
        border: 1px solid #363a4f;
        border-radius: 4px;
        padding: 14px;
        margin-bottom: 18px;
        page-break-inside: avoid;
    }

    .card-header {
        border-bottom: 1px dashed #494d64;
        padding-bottom: 8px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    .plant-key-badge {
        font-size: 13pt;
        font-weight: bold;
        color: #ed8796;
        letter-spacing: 1px;
    }

    .status-badge {
        font-size: 8.5pt;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 3px;
        border: 1px solid;
        text-transform: uppercase;
    }

    .species-name {
        font-size: 12pt;
        font-style: italic;
        color: #8aadf4;
        margin-top: 4px;
        margin-bottom: 8px;
    }

    .grid-props {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px 16px;
        margin-bottom: 12px;
    }

    .prop-item {
        background-color: #1e2030;
        border: 1px solid #363a4f;
        padding: 6px 10px;
        border-radius: 3px;
    }

    .prop-label {
        font-size: 7.5pt;
        color: #939ab7;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 2px;
    }

    .prop-value {
        font-size: 9pt;
        color: #cad3f5;
        font-weight: 600;
        word-break: break-word;
    }

    .prop-full {
        grid-column: span 2;
    }

    .section-title {
        font-size: 9pt;
        font-weight: bold;
        color: #ed8796;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin: 10px 0 6px 0;
        border-left: 3px solid #ed8796;
        padding-left: 6px;
    }

    .text-box {
        background-color: #1e2030;
        border: 1px solid #363a4f;
        padding: 8px 10px;
        font-size: 8.5pt;
        color: #b8c0e0;
        border-radius: 3px;
        margin-bottom: 10px;
        white-space: pre-wrap;
    }

    .photo-gallery {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 8px;
    }

    .photo-box {
        width: 48%;
        background-color: #181926;
        border: 1px solid #494d64;
        border-radius: 3px;
        padding: 5px;
        text-align: center;
        page-break-inside: avoid;
    }

    .photo-img {
        width: 100%;
        height: 160px;
        object-fit: cover;
        border-radius: 2px;
        display: block;
    }

    .photo-caption {
        font-size: 7pt;
        color: #939ab7;
        margin-top: 4px;
        font-family: monospace;
    }

    .vector-preview {
        width: 100%;
        height: 120px;
        background-color: #1e2030;
        border: 1px dashed #494d64;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        color: #8087a2;
        font-size: 8pt;
    }

    /* Index Table */
    table.index-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 15px;
        margin-bottom: 25px;
        font-size: 8pt;
        page-break-inside: avoid;
    }

    table.index-table th {
        background-color: #24273a;
        color: #ed8796;
        border: 1px solid #363a4f;
        padding: 6px 8px;
        text-align: left;
        font-weight: bold;
        text-transform: uppercase;
    }

    table.index-table td {
        border: 1px solid #363a4f;
        padding: 5px 8px;
        color: #cad3f5;
        background-color: #1e2030;
    }

    table.index-table tr:nth-child(even) td {
        background-color: #24273a;
    }

    .page-break {
        page-break-before: always;
    }
    """


def render_plant_card_html(p: Dict[str, Any]) -> str:
    """Renders a single botanical dossier card in HTML for WeasyPrint."""
    status = p.get("status", "Ok")
    color, bg, es_status = STATUS_COLORS.get(status, ("#cad3f5", "#24273a", status))

    photos = p.get("photos", [])
    photo_html_items = []

    for fn in photos:
        uri = get_image_data_uri(fn)
        if uri:
            photo_html_items.append(f"""
                <div class="photo-box">
                    <img class="photo-img" src="{uri}" alt="{fn}" />
                </div>
            """)

    if not photo_html_items:
        gallery_content = """
            <div class="vector-preview">
                <div>[DIAGRAMA BOTÁNICO VECTORIAL / SIN ARCHIVO FOTOGRÁFICO ADJUNTO]</div>
                <div style="font-size: 7pt; color: #6e738d; margin-top: 4px;">EJEMPLAR REGISTRADO EN ARCHIVO DE PLANTATION</div>
            </div>
        """
    else:
        gallery_content = f"""<div class="photo-gallery">{''.join(photo_html_items)}</div>"""

    aka_str = f'<span style="color: #f5a97f; font-weight: bold; margin-left: 6px; font-size: 8.5pt;">"{p.get("aka")}"</span>' if p.get('aka') else ""

    return f"""
    <div class="card">
        <div class="card-header">
            <div>
                <span class="plant-key-badge">[ID: {p.get('name', 'N/A')}]</span>
                {aka_str}
            </div>
            <div>
                <span class="status-badge" style="color: {color}; border-color: {color}; background-color: {bg};">
                    ● {es_status}
                </span>
            </div>
        </div>

        <div class="species-name">{p.get('species', 'Especie no especificada')}</div>

        <div class="grid-props">
   <div class="prop-item">
                <div class="prop-label">Fecha Siembra/Esqueje</div>
                <div class="prop-value">{p.get('sowing_cutting_date') or 'No registrada'}</div>
            </div>
             <div class="prop-item">
                <div class="prop-label">Injerto / Patrón</div>
                <div class="prop-value">{p.get('graft') or 'Sin injerto'}</div>
            </div>
            <div class="prop-item">
                <div class="prop-label">Linaje / Padres</div>
                <div class="prop-value">{p.get('padres') or 'Desconocido'}</div>
            </div>
         
            <div class="prop-item">
                <div class="prop-label">Último Trasplante</div>
                <div class="prop-value">{p.get('last_repotted') or 'No registrado'}</div>
            </div>
            <div class="prop-item prop-full">
                <div class="prop-label">Última Poda </div>
                <div class="prop-value">{p.get('last_pruned') or 'Sin registro de poda'}</div>
            </div>
        </div>

        <div class="section-title">Historial de Fertilización y Tratamientos</div>
        <div class="text-box">{p.get('fertilizante') or 'Sin tratamientos registrados a la fecha.'}</div>

        <div class="section-title">Observaciones</div>
        <div class="text-box">{p.get('comentarios') or 'Sin notas adicionales.'}</div>

        <div class="section-title">Evidencia Fotográfica ({len(photos)} fotos)</div>
        {gallery_content}
    </div>
    """


def generate_single_plant_pdf(plant: Dict[str, Any]) -> bytes:
    """Generates an individual botanical dossier PDF for a single plant."""
    key = plant.get("name", "PLANTA")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Dossier Botánico - {key}</title>
        <style>
            {get_pdf_css()}
        </style>
    </head>
    <body>
        <div class="header-banner">
            <div class="header-title-box">
                <div>
                    <h1 class="main-title">Plantation // Ficha Técnica Individual</h1>
                    <p class="sub-title">Documento de control biológico, linaje y estado.</p>
                </div>
                <div class="meta-box">
                    <div>FECHA EMISIÓN: {now_str}</div>
                    <div>ESTÁNDAR: PDF-1.4</div>
                    <div style="color: #ed8796; font-weight: bold; margin-top: 3px;"> // Uso interno</div>
                </div>
            </div>
        </div>

        {render_plant_card_html(plant)}
    </body>
    </html>
    """

    doc = weasyprint.HTML(string=html_content)
    # Produce PDF bytes
    return doc.write_pdf()


def generate_catalog_pdf(plants: List[Dict[str, Any]], title: str = "CATÁLOGO GENERAL DE EJEMPLARES") -> bytes:
    """Generates a complete multi-page dossier PDF containing index summary table and all specimen cards."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build Index Table rows
    table_rows = []
    for p in plants:
        status = p.get("status", "Ok")
        color, _, es_status = STATUS_COLORS.get(status, ("#cad3f5", "#24273a", status))
        table_rows.append(f"""
            <tr>
                <td style="font-weight: bold; color: #ed8796;">{p.get('name')}</td>
                <td style="font-style: italic;">{p.get('species')}</td>
                <td><span style="color: {color}; font-weight: bold;">● {es_status}</span></td>
                <td>{p.get('location') or '—'}</td>
                <td>{p.get('registration_date') or '—'}</td>
                <td>{p.get('padres') or '—'}</td>
                <td>{p.get('graft') or '—'}</td>
                <td style="text-align: center;">{len(p.get('photos', []))}</td>
            </tr>
        """)

    index_html = f"""
        <div class="card" style="margin-top: 10px;">
            <div class="section-title" style="margin-top: 0; font-size: 11pt;">Índice General y Sumario de Ejemplares Registrados ({len(plants)} plantas)</div>
            <table class="index-table">
                <thead>
                    <tr>
                        <th>Clave</th>
                        <th>Especie Botánica</th>
                        <th>Estado Sanitario</th>
                        <th>Ubicación</th>
                        <th>Fecha Reg.</th>
                        <th>Linaje / Padres</th>
                        <th>Injerto</th>
                        <th>Fotos</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join(table_rows)}
                </tbody>
            </table>
        </div>
    """

    # Build cards
    cards_html = []
    for idx, p in enumerate(plants):
        break_class = ' class="page-break"' if idx > 0 else ''

        cards_html.append(f"""
            <div{break_class}>
                {render_plant_card_html(p)}
            </div>
        """)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Plantation - Dossier General</title>
        <style>
            {get_pdf_css()}
        </style>
    </head>
    <body>
        <div class="header-banner">
            <div class="header-title-box">
                <div>
                    <div class="app-tag">Plantation</div>
                    <h1 class="main-title">{title}</h1>
                    <p class="sub-title">Inventario integral, linajes cruzados, tratamientos sanitarios e historial fotográfico.</p>
                </div>
                <div class="meta-box">
                    <div>FECHA GENERACIÓN: {now_str}</div>
                    <div>TOTAL REGISTROS: {len(plants)}</div>
                    <div style="color: #ed8796; font-weight: bold; margin-top: 3px;">CATÁLOGO OFICIAL</div>
                </div>
            </div>
        </div>

        {index_html}

        <div class="page-break"></div>

        <div style="margin-bottom: 15px;">
            <h2 style="color: #ed8796; font-size: 13pt; margin: 0; letter-spacing: 1px;">FICHAS TÉCNICAS DETALLADAS</h2>
            <div style="color: #8087a2; font-size: 8.5pt;">EXPEDIENTE INDIVIDUAL POR EJEMPLAR</div>
        </div>

        {''.join(cards_html)}
    </body>
    </html>
    """

    doc = weasyprint.HTML(string=html_content)
    return doc.write_pdf()
