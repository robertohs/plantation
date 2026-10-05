"""
Plantation - Admin & Inventory Module Template
Popup modal interface, batch operations, database health, and botanical inventory audit.
"""

from typing import List, Optional
import html
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
    <div id="db-health-card" class="inventory-stat-card" style="margin-top: 10px; margin-bottom: 12px; padding: 12px 16px; border: 1px solid var(--border-dim); background: var(--bg-crust); border-radius: 4px; display: flex; flex-direction: column; align-items: flex-start; gap: 10px; text-align: left;">
        <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start; text-align: left; width: 100%;">
            <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap; justify-content: flex-start;">
                <span style="font-weight: 700; font-size: 11px; letter-spacing: 0.5px; color: var(--text-main);">ESTADO BASE DE DATOS & RESPALDOS AUTOMÁTICOS:</span>
                <span style="color: {status_color}; font-weight: 700; font-size: 11px; display: inline-flex; align-items: center; gap: 4px;">
                    ● {status_text}
                </span>
            </div>
            <div style="font-size: 11px; color: var(--text-dim); display: flex; flex-wrap: wrap; gap: 16px; justify-content: flex-start; text-align: left;">
                <span>Tamaño DB: <strong style="color: var(--text-sub);">{health['database_size_formatted']}</strong></span>
                <span>Copias en disco: <strong style="color: var(--blue-sky);">{health['total_backups']}</strong> (Programado cada 12h, max 20)</span>
                <span>Último respaldo: <strong style="color: var(--peach-orange);">{health['latest_backup_time']}</strong></span>
            </div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center; justify-content: flex-start; flex-wrap: wrap;">
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
            <button type="button"
                    class="btn btn-sm"
                    hx-get="/admin/modal/import-db"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    style="color: var(--peach-orange); border-color: var(--peach-orange);"
                    title="Importar o restaurar una base de datos SQLite previa con validación estricta de compatibilidad">
                📥 [IMPORTAR .DB]
            </button>
        </div>
    </div>
    """


def render_admin_stats_cards(inv: dict) -> str:
    """Renders the top summary metric cards for the admin modal."""
    sc = inv["status_counts"]
    stat_cards = [
        (inv['total'], "EJEMPLARES TOTALES", "var(--red-crimson)"),
        (sc.get('OK', 0), "SALUDABLES (● OK)", "var(--green-sage)"),
        (sc.get('notOK', 0), "ENFERMOS / CUARENTENA (● notOK)", "#ef4444"),
        (f"{inv['with_photos']} <span style='font-size: 11px; color: var(--text-dim);'>({inv['total_photos']} fotos)</span>", "CON FOTO", "var(--blue-sky)"),
        (inv['without_photos'], "SIN FOTOGRAFÍA", "var(--red-crimson)" if inv['without_photos'] > 0 else "var(--text-sub)"),
        (f"{inv['with_graft']} <span style='font-size: 11px; color: var(--text-dim);'>({inv['own_roots']} r. propia)</span>", "INJERTADOS", "var(--peach-orange)"),
        (len(inv['location_counts']), "UBICACIONES", "var(--green-sage)"),
    ]
    return "\n".join(
        f"""<div class="inventory-stat-card">
            <div class="inventory-stat-val" style="color: {col};">{val}</div>
            <div class="inventory-stat-lbl">{lbl}</div>
        </div>"""
        for val, lbl, col in stat_cards
    )


def render_admin_table_content(filter_tag: str = "ALL", search_q: str = "") -> str:
    """Renders only the table body and category tabs for quick HTMX swapping."""
    inv = db.get_inventory_stats()
    sc = inv["status_counts"]
    all_plants = db.get_plants()

    # Filter according to tab
    if filter_tag == "NO_PHOTOS":
        plants_to_show = [p for p in all_plants if not p.get("photos")]
    elif filter_tag == "GRAFTED":
        plants_to_show = [p for p in all_plants if db.is_grafted(p.get("graft"))]
    elif filter_tag == "ILL":
        plants_to_show = [p for p in all_plants if db.normalize_status(p.get("status")) == "notOK"]
    else:
        plants_to_show = all_plants

    if search_q:
        q = search_q.strip().lower()
        plants_to_show = [
            p for p in plants_to_show
            if q in (p.get("name") or "").lower()
            or q in (p.get("species") or "").lower()
            or q in (p.get("aka") or "").lower()
            or q in (p.get("location") or "").lower()
        ]

    rows = []
    for p in plants_to_show:
        name_esc = html.escape(str(p.get('name', '')))
        st = db.normalize_status(p.get("status"))
        status_cls = STATUS_BADGE_CLASSES.get(st, "status-OK")
        status_es = STATUS_SPANISH.get(st, st)
        photos = p.get("photos", [])
        photo_badge = f'<span style="color: var(--blue-sky); font-weight: bold;">{len(photos)}</span>' if photos else '<span style="color: var(--text-dim);">0</span>'
        aka_display = f'<span style="color: var(--peach-orange); font-weight: 600;">{html.escape(str(p.get("aka")))}</span>' if p.get("aka") else '<span style="color: var(--text-dim);">—</span>'
        height_display = f'<span style="color: var(--green-sage); font-size: 11px;">{html.escape(str(p.get("height")))}</span>' if p.get("height") else '<span style="color: var(--text-dim);">—</span>'

        rows.append(f"""
            <tr id="admin-row-{name_esc}">
                <td style="text-align: center;">
                    <input type="checkbox" name="keys" value="{name_esc}" class="admin-checkbox" />
                </td>
                <td>
                    <a href="#"
                       hx-get="/plants/{name_esc}"
                       hx-target="#modal-container"
                       hx-swap="innerHTML"
                       class="plant-key"
                       style="font-size: 13px; color: #ff66cc; text-decoration: underline; cursor: pointer;"
                       title="Abrir expediente">
                        {name_esc}
                    </a>
                </td>
                <td>{aka_display}</td>
                <td style="font-style: italic; color: var(--blue-sky); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{html.escape(str(p.get('species', '')))}">
                    {html.escape(str(p.get('species', '')))}
                </td>
                <td><span class="status-badge {status_cls}" style="font-size: 9.5px;">● {status_es}</span></td>
                <td>{html.escape(str(p.get('location') or '—'))}</td>
                <td>{height_display}</td>
                <td>{html.escape(str(p.get('padres') or '—'))}</td>
                <td>{html.escape(str(p.get('graft') or 'Pie franco'))}</td>
                <td style="text-align: center;">{photo_badge}</td>
                <td style="text-align: right; white-space: nowrap;">
                    <button type="button"
                            class="btn btn-sm"
                            hx-get="/plants/{name_esc}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Ver expediente técnico">
                        VER
                    </button>
                    <button type="button"
                            class="btn btn-sm btn-red"
                            hx-delete="/admin/plant/{name_esc}"
                            hx-target="#admin-row-{name_esc}"
                            hx-swap="outerHTML"
                            hx-confirm="¿Eliminar definitivamente el ejemplar '{name_esc}' y todas sus fotos del disco?"
                            title="Eliminar este ejemplar">
                        ELIMINAR
                    </button>
                </td>
            </tr>
        """)

    table_body = "".join(rows) if rows else """
        <tr>
            <td colspan="11" style="text-align: center; color: var(--text-dim); padding: 24px;">
                No hay ejemplares que coincidan con los criterios seleccionados.
            </td>
        </tr>
    """

    tab_defs = [
        ("ALL", f"TODOS ({inv['total']})"),
        ("NO_PHOTOS", f"SIN FOTO ({inv['without_photos']})"),
        ("GRAFTED", f"INJERTOS ({inv['with_graft']})"),
        ("ILL", f"EN CUARENTENA ({sc.get('notOK', 0)})"),
    ]
    tabs_html = "\n".join(
        f"""<button type="button"
                    class="inv-tab-btn {'active' if filter_tag == tag else ''}"
                    hx-get="/admin/filter?tab={tag}"
                    hx-target="#admin-table-container"
                    hx-swap="innerHTML">{label}</button>"""
        for tag, label in tab_defs
    )

    return f"""
    <div id="admin-table-and-tabs">
        <div class="inventory-toolbar" style="margin-top: 10px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div class="inventory-filter-tabs" style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                <span style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-right: 4px;">FILTRO:</span>
                {tabs_html}
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 11px; color: var(--text-dim);">Buscar en tabla:</span>
                <input type="text"
                       id="admin-search-box"
                       placeholder="Clave, especie..."
                       oninput="filterAdminRowsLocally(this.value)"
                       style="background: var(--bg-crust); border: 1px solid var(--border-dim); color: var(--text-main); font-size: 12px; padding: 4px 8px; border-radius: 3px; outline: none; width: 150px;" />
            </div>
        </div>

        <form id="admin-bulk-form"
              hx-post="/admin/bulk-delete"
              hx-target="#admin-table-container"
              hx-swap="innerHTML"
              hx-confirm="¿CONFIRMAR ELIMINACIÓN MASIVA de los ejemplares seleccionados y el borrado permanente de sus fotografías en disco?">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; gap: 8px; align-items: center;">
                    <button type="button"
                            class="btn btn-sm"
                            onclick="document.querySelectorAll('.admin-checkbox').forEach(cb => cb.checked = true);">
                        [✓ SELECCIONAR TODOS]
                    </button>
                    <button type="button"
                            class="btn btn-sm"
                            onclick="document.querySelectorAll('.admin-checkbox').forEach(cb => cb.checked = false);">
                        [✕ DESMARCAR TODOS]
                    </button>
                    <span id="admin-selected-counter" style="font-size: 11px; color: var(--text-dim); margin-left: 8px;">
                        Mostrando {len(plants_to_show)} ejemplares
                    </span>
                </div>
                <button type="submit" class="btn btn-sm btn-red" style="font-weight: bold;">
                    🗑 [ELIMINAR SELECCIÓN]
                </button>
            </div>

            <div class="admin-table-wrapper" style="max-height: 48vh; overflow-y: auto;">
                <table class="admin-table" id="admin-inventory-table">
                    <thead>
                        <tr style="position: sticky; top: 0; z-index: 10;">
                            <th style="width: 36px; text-align: center;">✓</th>
                            <th style="width: 70px;">CLAVE</th>
                            <th style="width: 100px;">ALIAS</th>
                            <th>ESPECIE BOTÁNICA</th>
                            <th>ESTADO</th>
                            <th>UBICACIÓN</th>
                            <th>ALTURA</th>
                            <th>LINAJE</th>
                            <th>INJERTO</th>
                            <th style="text-align: center;">FOTOS</th>
                            <th style="text-align: right;">ACCIONES</th>
                        </tr>
                    </thead>
                    <tbody id="admin-table-rows">
                        {table_body}
                    </tbody>
                </table>
            </div>
        </form>
    </div>
    """


def render_admin_modal(filter_tag: str = "ALL") -> str:
    """
    Renders the complete, first-class Admin & Inventory Management modal popup.
    Designed in the exact same modal pattern as Botanical Analytics/Stats.
    """
    inv = db.get_inventory_stats()
    table_section_html = render_admin_table_content(filter_tag=filter_tag)

    return f"""
    <div class="modal-overlay" id="admin-dashboard-modal" style="display: flex;">
        <div class="modal-dialog" style="max-width: 1100px; width: 96vw; max-height: 92vh; display: flex; flex-direction: column;">
            
            <!-- MODAL HEADER -->
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title" style="color: var(--peach-orange);">
                        ⚙ [ADMINISTRACIÓN // INVENTARIO]
                    </span>
                    <span style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-dim); background: var(--bg-surface); padding: 2px 8px; border-radius: 2px; border: 1px solid var(--border-dim);">
                        TOTAL: {inv['total']} EJEMPLARES
                    </span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="btn btn-sm"
                            hx-get="/admin/modal"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Recargar inventario y recalcular métricas">
                        ↻ ACTUALIZAR
                    </button>
                    <button class="modal-close-btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Cerrar panel de administración [ESC]">✕</button>
                </div>
            </div>

            <!-- MODAL BODY (SCROLLABLE) -->
            <div class="modal-body" style="padding: 16px 20px 20px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 14px;">
                
                <div id="admin-stats-summary" style="display: none;"></div>

                <!-- 1. DATABASE RELIABILITY & BACKUP STATUS -->
                {render_db_health_card()}

                <!-- 3. ACTIONS MASTER TOOLBAR -->
                <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-sub); display: flex; align-items: center; gap: 6px;">
                        <span>ACCIONES RÁPIDAS & DESCARGAS:</span>
                    </div>

                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button type="button"
                                class="btn btn-sm btn-green"
                                hx-get="/plants/modal/bulk-new"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                style="font-weight: 700;"
                                title="Añadir múltiples ejemplares simultáneamente con datos comunes y claves continuas">
                            ➕ [ALTA MASIVA DE PLANTAS]
                        </button>
                        <button type="button"
                                class="btn btn-sm btn-red"
                                hx-get="/plants/modal/bulk-delete"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                style="font-weight: 700;"
                                title="Eliminar múltiples ejemplares simultáneamente por rango, lista manual o criterios">
                            🗑 [BAJA MASIVA DE PLANTAS]
                        </button>
                        <a class="btn btn-sm btn-primary"
                           href="/pdf/full-catalog"
                           target="_blank"
                           title="Generar y descargar dossier de inventario completo en PDF">
                            🗎 [DOSSIER PDF]
                        </a>
                        <a class="btn btn-sm btn-green"
                           href="/admin/inventory.csv"
                           download="inventario_plantation.csv"
                           title="Exportar inventario estructurado a archivo CSV">
                            ⭳ [EXPORTAR CSV]
                        </a>
                    </div>
                </div>

                <!-- 4. INVENTORY TABLE & FILTERS CONTAINER -->
                <div id="admin-table-container">
                    {table_section_html}
                </div>

            </div>

            <!-- MODAL FOOTER -->
            <div class="modal-footer-sticky" style="display: flex; justify-content: flex-end; align-items: center;">
                <button type="button"
                        class="btn btn-red"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML">
                    CERRAR [ESC]
                </button>
            </div>

        </div>
    </div>

    <!-- Client-side fast filter script for instant search inside admin table -->
    <script>
        var _adminFilterTimer = null;
        function filterAdminRowsLocally(query) {{
            clearTimeout(_adminFilterTimer);
            _adminFilterTimer = setTimeout(function() {{
                var q = (query || '').toLowerCase().trim();
                var rows = document.querySelectorAll('#admin-table-rows tr');
                var visible = 0;
                rows.forEach(function(row) {{
                    var text = row.innerText.toLowerCase();
                    if (!q || text.indexOf(q) !== -1) {{
                        row.style.display = '';
                        visible++;
                    }} else {{
                        row.style.display = 'none';
                    }}
                }});
                var counter = document.getElementById('admin-selected-counter');
                if (counter) {{
                    counter.textContent = 'Mostrando ' + visible + ' ejemplares' + (q ? ' (filtrados)' : '');
                }}
            }}, 3);
        }}
    </script>
    """


def render_admin_panel_content(filter_tag: str = "ALL") -> str:
    """Backward-compatible proxy returning the modal popup."""
    return render_admin_modal(filter_tag=filter_tag)
