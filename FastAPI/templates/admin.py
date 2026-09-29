"""
Plantation - Admin & Inventory Module Template
Handles the collapsible inventory tray, batch operations, and data exports.
"""

from typing import List
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH


def render_admin_panel_content(filter_tag: str = "ALL") -> str:
    """Renders the comprehensive Inventory and Admin Management Tray."""
    inv = db.get_inventory_stats()
    sc = inv["status_counts"]
    all_plants = db.get_plants()

    # Filter according to tab
    if filter_tag == "NO_PHOTOS":
        plants_to_show = [p for p in all_plants if not p.get("photos")]
    elif filter_tag == "GRAFTED":
        plants_to_show = [p for p in all_plants if p.get("graft") and "sin injerto" not in (p.get("graft") or "").lower()]
    elif filter_tag == "ILL":
        plants_to_show = [p for p in all_plants if p.get("status") == "notOK"]
    else:
        plants_to_show = all_plants

    rows = []
    for p in plants_to_show:
        st = db.normalize_status(p.get("status"))
        status_cls = STATUS_BADGE_CLASSES.get(st, "status-OK")
        status_es = STATUS_SPANISH.get(st, st)
        photos = p.get("photos", [])
        photo_badge = f'<span style="color: var(--blue-sky); font-weight: bold;">{len(photos)}</span>' if photos else '<span style="color: var(--text-dim);">0</span>'
        aka_display = f'<span style="color: var(--peach-orange); font-weight: 600;">{p.get("aka")}</span>' if p.get("aka") else '<span style="color: var(--text-dim);">—</span>'

        height_display = f'<span style="color: var(--green-sage); font-size: 11px;">{p.get("height")}</span>' if p.get("height") else '<span style="color: var(--text-dim);">—</span>'

        rows.append(f"""
            <tr>
                <td style="text-align: center;">
                    <input type="checkbox" name="keys" value="{p.get('name')}" class="admin-checkbox" />
                </td>
                <td style="font-weight: bold; color: var(--red-crimson);">{p.get('name')}</td>
                <td>{aka_display}</td>
                <td style="font-style: italic; color: var(--blue-sky); max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{p.get('species')}">{p.get('species')}</td>
                <td><span class="status-badge {status_cls}" style="font-size: 9.5px;">● {status_es}</span></td>
                <td>{p.get('location') or '—'}</td>
                <td>{height_display}</td>
                <td>{p.get('padres') or '—'}</td>
                <td>{p.get('graft') or 'Sin injerto'}</td>
                <td style="text-align: center;">{photo_badge}</td>
                <td style="text-align: right; white-space: nowrap;">
                    <button type="button"
                            class="btn btn-sm"
                            hx-get="/plants/{p.get('name')}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        VER
                    </button>
                    <button type="button"
                            class="btn btn-sm btn-red"
                            hx-delete="/plants/{p.get('name')}"
                            hx-target="#plant-container"
                            hx-swap="innerHTML"
                            hx-confirm="¿Eliminar definitivamente el ejemplar '{p.get('name')}' y todas sus fotos del disco?">
                        ELIMINAR
                    </button>
                </td>
            </tr>
        """)

    table_body = "".join(rows) if rows else """
        <tr>
            <td colspan="11" style="text-align: center; color: var(--text-dim); padding: 18px;">
                No hay ejemplares en esta categoría de inventario.
            </td>
        </tr>
    """

    stat_cards = [
        (inv['total'], "EJEMPLARES TOTALES", "var(--red-crimson)"),
        (sc.get('OK', 0), "SALUDABLES (● OK)", "var(--green-sage)"),
        (sc.get('notOK', 0), "ENFERMOS / CUARENTENA (● notOK)", "#ef4444"),
        (f"{inv['with_photos']} <span style='font-size: 12px; color: var(--text-dim);'>({inv['total_photos']} fotos)</span>", "CON REGISTRO FOTO", "var(--blue-sky)"),
        (inv['without_photos'], "SIN FOTOGRAFÍA", "var(--red-crimson)" if inv['without_photos'] > 0 else "var(--text-sub)"),
        (f"{inv['with_graft']} <span style='font-size: 12px; color: var(--text-dim);'>({inv['own_roots']} r. propia)</span>", "INJERTADOS", "var(--text-main)"),
        (len(inv['location_counts']), "UBICACIONES ACTIVAS", "var(--green-sage)"),
    ]
    stats_grid_html = "\n".join(
        f"""<div class="inventory-stat-card">
            <div class="inventory-stat-val" style="color: {col};">{val}</div>
            <div class="inventory-stat-lbl">{lbl}</div>
        </div>"""
        for val, lbl, col in stat_cards
    )

    tab_defs = [
        ("ALL", f"TODOS ({inv['total']})"),
        ("NO_PHOTOS", f"SIN FOTO ({inv['without_photos']})"),
        ("GRAFTED", f"INJERTOS ({inv['with_graft']})"),
        ("ILL", f"EN CUARENTENA ({sc.get('notOK', 0)})"),
    ]
    tabs_html = "\n".join(
        f"""<button class="inv-tab-btn {'active' if filter_tag == tag else ''}"
                    hx-get="/admin/filter?tab={tag}"
                    hx-target="#admin-panel"
                    hx-swap="outerHTML">{label}</button>"""
        for tag, label in tab_defs
    )

    return f"""
    <div class="admin-tray" id="admin-panel">
        <div class="admin-header">
            <div>
                <span class="admin-title">PANEL DE ADMINISTRACIÓN & INVENTARIO BOTÁNICO</span>
                <span style="font-size: 11px; color: var(--text-dim); margin-left: 10px;">Control maestro, balances métricos y purga de fotografías en disco</span>
            </div>
            <button class="btn btn-sm"
                    hx-get="/admin/close"
                    hx-target="#admin-container"
                    hx-swap="innerHTML">
                [CERRAR PANEL ADMIN ✕]
            </button>
        </div>

        <div class="inventory-stats-grid">
            {stats_grid_html}
        </div>

        <div class="inventory-toolbar">
            <div class="inventory-filter-tabs">
                <span style="font-size: 11px; color: var(--text-dim); line-height: 24px; margin-right: 4px;">FILTRO TABLA:</span>
                {tabs_html}
            </div>

            <div style="display: flex; gap: 8px;">
                <a class="btn btn-sm btn-primary"
                   href="/pdf/full-catalog"
                   target="_blank"
                   title="Generar y descargar dossier de inventario completo en PDF">
                    🗎 [DOSSIER GENERAL PDF]
                </a>
                <a class="btn btn-sm btn-green"
                   href="/admin/inventory.csv"
                   download="inventario_plantation.csv"
                   title="Exportar inventario estructurado a archivo CSV">
                    ⭳ [EXPORTAR CSV]
                </a>
                <a class="btn btn-sm btn-green"
                   href="/admin/backup.db"
                   download
                   title="Descargar copia de seguridad instantánea de la base de datos SQLite (.db)">
                    💾 [BACKUP DB]
                </a>
            </div>
        </div>

        <form hx-post="/admin/bulk-delete"
              hx-target="#admin-container"
              hx-swap="innerHTML"
              hx-confirm="¿CONFIRMAR ELIMINACIÓN MASIVA de los ejemplares seleccionados y el borrado permanente de sus fotografías en disco?">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="display: flex; gap: 8px;">
                    <button type="button"
                            class="btn btn-sm"
                            onclick="document.querySelectorAll('.admin-checkbox').forEach(cb => cb.checked = true);">
                        [SELECCIONAR TODOS]
                    </button>
                    <button type="button"
                            class="btn btn-sm"
                            onclick="document.querySelectorAll('.admin-checkbox').forEach(cb => cb.checked = false);">
                        [DESMARCAR TODOS]
                    </button>
                </div>
                <button type="submit" class="btn btn-sm btn-red" style="font-weight: bold;">
                    🗑 [ELIMINAR SELECCIÓN]
                </button>
            </div>

            <div class="admin-table-wrapper">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th style="width: 36px; text-align: center;">✓</th>
                            <th style="width: 70px;">CLAVE</th>
                            <th style="width: 100px;">ALIAS</th>
                            <th>ESPECIE</th>
                            <th>ESTADO</th>
                            <th>UBICACIÓN</th>
                            <th>ALTURA</th>
                            <th>LINAJE</th>
                            <th>INJERTO</th>
                            <th style="text-align: center;">FOTOS</th>
                            <th style="text-align: right;">ACCIONES</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_body}
                    </tbody>
                </table>
            </div>
        </form>
    </div>
    """
