"""
Plantation - Printable Dossier Template
Dedicated HTML view for web browser printing and technical specimen archiving.
"""

from typing import Any, Dict
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH


def render_printable_dossier_html(plant: Dict[str, Any]) -> str:
    """Renders a dedicated, printable botanical technical dossier with concise Alias labeling."""
    status = db.normalize_status(plant.get("status"))
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-OK")
    status_es = STATUS_SPANISH.get(status, status)
    photos = plant.get("photos", [])
    _, age_detailed = db.calculate_plant_age(plant.get("sowing_cutting_date"), plant.get("graft", ""))

    photos_html = ""
    if photos:
        items = []
        for ph in photos:
            items.append(f'''
            <div class="dossier-photo-card">
                <img src="/images/{ph}" alt="{plant.get('name')}" class="dossier-photo-img" />
                <div class="dossier-photo-cap">{ph}</div>
            </div>
            ''')
        photos_html = f'''
        <div class="dossier-section-title">REGISTRO FOTOGRÁFICO Y MORFOLÓGICO</div>
        <div class="dossier-gallery">
            {"".join(items)}
        </div>
        '''

    aka_val = (plant.get("aka") or "").strip()
    aka_display = f'<span>ALIAS: <strong style="color: var(--peach-orange);">"{aka_val}"</strong></span>' if aka_val else ''

    return f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Dossier Técnico - [{plant.get('name')}] {plant.get('species')}</title>
    <link rel="stylesheet" href="/static/style.css" />
    <style>
        .dossier-container {{
            max-width: 900px;
            margin: 24px auto;
            background: var(--bg-surface);
            border: 1px solid var(--border-dim);
            border-radius: 4px;
            padding: 32px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        }}
        .dossier-topbar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid var(--border-red);
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .dossier-brand {{
            font-family: var(--font-mono);
            font-size: 20px;
            font-weight: 700;
            color: var(--text-main);
            letter-spacing: 1px;
        }}
        .dossier-badge-status {{
            font-size: 13px;
            padding: 4px 12px;
            border-radius: 3px;
            font-weight: 700;
        }}
        .dossier-taxa-box {{
            background: var(--bg-mantle);
            border: 1px solid var(--border-dim);
            padding: 16px;
            border-radius: 3px;
            margin-bottom: 24px;
        }}
        .dossier-species {{
            font-size: 22px;
            font-style: italic;
            color: var(--blue-sky);
            margin: 6px 0;
        }}
        .dossier-table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 24px;
            font-size: 13px;
        }}
        .dossier-table th, .dossier-table td {{
            padding: 10px 14px;
            border: 1px solid var(--border-dim);
            text-align: left;
        }}
        .dossier-table th {{
            background: var(--bg-mantle);
            color: var(--red-crimson);
            font-size: 11px;
            letter-spacing: 0.8px;
            width: 28%;
        }}
        .dossier-table td {{
            background: var(--bg-surface);
            color: var(--text-main);
        }}
        .dossier-gallery {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 16px;
            margin-top: 14px;
            margin-bottom: 24px;
        }}
        .dossier-photo-card {{
            background: var(--bg-mantle);
            border: 1px solid var(--border-dim);
            border-radius: 3px;
            overflow: hidden;
            text-align: center;
        }}
        .dossier-photo-img {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            display: block;
        }}
        .dossier-photo-cap {{
            padding: 6px 8px;
            font-size: 10px;
            color: var(--text-sub);
        }}
        .dossier-actions {{
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            margin-top: 24px;
            padding-top: 16px;
            border-top: 1px solid var(--border-dim);
        }}
        @media print {{
            body {{
                background: #ffffff !important;
                color: #111111 !important;
            }}
            .dossier-container {{
                max-width: 100% !important;
                margin: 0 !important;
                padding: 12px !important;
                box-shadow: none !important;
                border: none !important;
                background: #ffffff !important;
            }}
            .dossier-actions {{
                display: none !important;
            }}
            .dossier-brand, .dossier-table th, .dossier-table td, .dossier-taxa-box {{
                color: #000000 !important;
                background: #ffffff !important;
                border-color: #cccccc !important;
            }}
            .dossier-species {{
                color: #1a4d2e !important;
            }}
            .dossier-table th {{
                background: #f4f4f4 !important;
                color: #222222 !important;
            }}
        }}
    </style>
</head>
<body data-theme="catpuchin">
    <div class="dossier-container">
        <div class="dossier-topbar">
            <div>
                <div class="dossier-brand">[PLANTATION] EXPEDIENTE BOTÁNICO OFICIAL</div>
                <div style="font-size: 11px; color: var(--text-dim); margin-top: 4px;">SISTEMA TÉCNICO DE REGISTRO & TAXONOMÍA DE COLECCIÓN</div>
            </div>
            <div>
                <span class="status-badge {status_cls} dossier-badge-status">● {status_es}</span>
            </div>
        </div>

        <div class="dossier-taxa-box">
            <div style="font-size: 11px; color: var(--red-crimson); font-weight: bold; letter-spacing: 1px;">IDENTIFICADOR</div>
            <div class="dossier-species">{plant.get('species')}</div>
            <div style="font-size: 13px; color: var(--text-main); display: flex; gap: 14px; flex-wrap: wrap;">
                <span>CLAVE DE COLECCIÓN: <strong style="color: var(--red-crimson);">[{plant.get('name')}]</strong></span>
                {aka_display}
            </div>
        </div>

        <div class="dossier-section-title">DATOS & REGISTRO</div>
        <table class="dossier-table">
            <tbody>
                <tr>
                    <th>ALIAS</th>
                    <td><strong style="color: var(--peach-orange);">{aka_val or '—'}</strong></td>
                </tr>
                <tr>
                    <th>FECHA DE REGISTRO</th>
                    <td>{plant.get('registration_date') or '—'}</td>
                </tr>
                <tr>
                    <th>EDAD</th>
                    <td><strong>{age_detailed}</strong></td>
                </tr>
                <tr>
                    <th>FECHA SIEMBRA / ESQUEJADO</th>
                    <td>{plant.get('sowing_cutting_date') or '—'}</td>
                </tr>
                <tr>
                    <th>LINAJE (PADRES)</th>
                    <td>{plant.get('padres') or 'Desconocido'}</td>
                </tr>
                <tr>
                    <th>INJERTO</th>
                    <td>{plant.get('graft') or 'Sin injerto (Raíz propia)'}</td>
                </tr>
                <tr>
                    <th>ÚLTIMA PODA</th>
                    <td>{plant.get('last_pruned') or '—'}</td>
                </tr>
                <tr>
                    <th>ÚLTIMO TRASPLANTE</th>
                    <td>{plant.get('last_repotted') or '—'}</td>
                </tr>
                <tr>
                    <th>FERTILIZACIÓN / NUTRICIÓN</th>
                    <td>{plant.get('fertilizante') or '—'}</td>
                </tr>
                <tr>
                    <th>NOTAS & OBSERVACIONES</th>
                    <td>{plant.get('comentarios') or 'Sin observaciones registradas.'}</td>
                </tr>
            </tbody>
        </table>

        {photos_html}

        <div class="dossier-actions">
            <a href="/pdf/plant/{plant.get('name')}" class="btn btn-red" target="_blank">
                🗎 [DESCARGAR PDF GENERADO]
            </a>
            <button class="btn btn-primary" onclick="window.print()">
                🖨 [IMPRIMIR DOSSIER]
            </button>
            <button class="btn" onclick="window.close()">
                ✕ [CERRAR VENTANA]
            </button>
        </div>
    </div>
</body>
</html>'''
