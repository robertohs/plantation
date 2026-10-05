"""
Plantation - Admin & Inventory Module Template
Handles the collapsible inventory tray, batch operations, and data exports.
"""

from typing import List, Optional
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH


def render_db_health_card(integrity_result_msg: Optional[str] = None) -> str:
    """Renders real-time database reliability, auto-backup metrics, and integrity check interface."""
    health = db.get_database_health()
    ok = health["integrity_ok"]
    status_color = "var(--green-sage)" if ok else "var(--red-crimson)"
    status_text = "INTEGRIDAD OK (0 anomalías)" if ok else f"ALERTA: {health['integrity_message']}"
    if integrity_result_msg:
        status_text = integrity_result_msg

    return f"""
    <div id="db-health-card" class="inventory-stat-card" style="margin-top: 12px; margin-bottom: 12px; padding: 12px 16px; border: 1px solid var(--border-color); background: rgba(0,0,0,0.18); border-radius: 4px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px;">
        <div style="display: flex; flex-direction: column; gap: 4px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <span style="font-weight: 700; font-size: 11px; letter-spacing: 0.5px; color: var(--text-main);">ESTADO BASE DE DATOS & RESPALDOS AUTOMÁTICOS:</span>
                <span style="color: {status_color}; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                    ● {status_text}
                </span>
            </div>
            <div style="font-size: 11px; color: var(--text-dim); display: flex; flex-wrap: wrap; gap: 16px;">
                <span>Tamaño DB: <strong style="color: var(--text-sub);">{health['database_size_formatted']}</strong></span>
                <span>Copias en disco: <strong style="color: var(--blue-sky);">{health['total_backups']}</strong> (Programado cada 12h, max 20)</span>
                <span>Último respaldo: <strong style="color: var(--peach-orange);">{health['latest_backup_time']}</strong></span>
            </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <button type="button"
                    class="btn btn-sm"
                    hx-get="/admin/check-integrity"
                    hx-target="#db-health-card"
                    hx-swap="outerHTML"
                    title="Ejecutar PRAGMA integrity_check en SQLite">
                🔍 [VERIFICAR INTEGRIDAD]
            </button>
            <button type="button"
                    class="btn btn-sm btn-green"
                    hx-post="/admin/create-backup"
                    hx-target="#db-health-card"
                    hx-swap="outerHTML"
                    title="Crear un respaldo hot backup inmediato en DB/backups/">
                ⚡ [CREAR RESPALDO AHORA]
            </button>
        </div>
    </div>
    """



def render_admin_panel_content(filter_tag: str = "ALL") -> str:
    """Renders the comprehensive Inventory and Admin Management Tray."""
    inv = db.get_inventory_stats()
    sc = inv["status_counts"]
    all_plants = db.get_plants()

    # Filter according to tab
    if filter_tag == "NO_PHOTOS":
        plants_to_show = [p for p in all_plants if not p.get("photos")]
    elif filter_tag == "GRAFTED":
        plants_to_show = [p for p in all_plants if db.is_grafted(p.get("graft"))]
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
                <td><span class="plant-key" style="font-size: 13px; color: #ff66cc;">{p.get('name')}</span></td>
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

        {render_db_health_card()}

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
                <button type="button"
                        class="btn btn-sm btn-green"
                        hx-get="/plants/modal/bulk-new"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Añadir múltiples ejemplares simultáneamente con datos comunes y claves secuenciales">
                    ➕ [ALTA MASIVA DE PLANTAS]
                </button>
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
