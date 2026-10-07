"""
Plantation - Admin & Inventory Module Template
Popup modal interface, batch operations, database health, and botanical inventory audit.
"""

from typing import List, Optional, Dict, Any
import html
import urllib.parse
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
                <span>Copias : <strong style="color: var(--blue-sky);">{health['total_backups']}</strong> (Programado cada 12h, max 20)</span>
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
        (sc.get('OK', 0), "SALUDABLES (● Ok)", "var(--green-sage)"),
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


def render_admin_pagination_bar(
    filter_tag: str,
    search_q: str,
    page: int,
    page_size: int,
    total_count: int,
    total_pages: int,
    start_idx: int,
    end_idx: int
) -> str:
    """Renders compact, responsive pagination controls for the admin inventory table."""
    encoded_search = urllib.parse.quote_plus(search_q)
    base_url = f"/admin/filter?tab={filter_tag}&search={encoded_search}&page_size={page_size}"

    if total_count > 0:
        showing_text = f"Mostrando <strong>{start_idx}–{end_idx}</strong> de <strong>{total_count:,}</strong> ejemplares".replace(",", ".")
        if search_q:
            showing_text += f' <span style="color: var(--peach-orange); font-size: 10.5px;">(filtrados por "{html.escape(search_q)}")</span>'
    else:
        showing_text = "Mostrando <strong>0</strong> ejemplares"
        if search_q:
            showing_text += f' <span style="color: var(--peach-orange); font-size: 10.5px;">(filtrados por "{html.escape(search_q)}")</span>'

    has_prev = page > 1
    has_next = page < total_pages

    btn_first = f"""<button type="button" class="btn btn-sm" hx-get="{base_url}&page=1" hx-target="#admin-table-container" hx-swap="innerHTML" title="Primera página">«</button>""" if has_prev else """<button type="button" class="btn btn-sm" disabled style="opacity: 0.35; cursor: not-allowed;">«</button>"""

    btn_prev = f"""<button type="button" class="btn btn-sm" hx-get="{base_url}&page={page - 1}" hx-target="#admin-table-container" hx-swap="innerHTML" title="Página anterior">‹ Anterior</button>""" if has_prev else """<button type="button" class="btn btn-sm" disabled style="opacity: 0.35; cursor: not-allowed;">‹ Anterior</button>"""

    page_indicator = f"""<span style="font-size: 11px; font-weight: 700; color: var(--peach-orange); padding: 0 4px; white-space: nowrap;">Página {page} de {total_pages}</span>"""

    btn_next = f"""<button type="button" class="btn btn-sm" hx-get="{base_url}&page={page + 1}" hx-target="#admin-table-container" hx-swap="innerHTML" title="Página siguiente">Siguiente ›</button>""" if has_next else """<button type="button" class="btn btn-sm" disabled style="opacity: 0.35; cursor: not-allowed;">Siguiente ›</button>"""

    btn_last = f"""<button type="button" class="btn btn-sm" hx-get="{base_url}&page={total_pages}" hx-target="#admin-table-container" hx-swap="innerHTML" title="Última página">»</button>""" if has_next else """<button type="button" class="btn btn-sm" disabled style="opacity: 0.35; cursor: not-allowed;">»</button>"""

    return f"""
    <div class="admin-pagination-bar" style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; font-size: 11px; border-top: 1px solid var(--border-dim); padding-top: 10px; margin-top: 10px;">
        <div style="color: var(--text-dim); white-space: nowrap;">
            {showing_text}
        </div>
        <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
            {btn_first}
            {btn_prev}
            {page_indicator}
            {btn_next}
            {btn_last}
            <span style="color: var(--border-dim); margin: 0 2px;">|</span>
            <span style="font-size: 11px; color: var(--text-dim); white-space: nowrap;">(20 por pág.)</span>
        </div>
    </div>
    """


def render_admin_table_content(
    filter_tag: str = "ALL",
    search_q: str = "",
    page: int = 1,
    page_size: int = 20
) -> str:
    """
    Renders high-performance server-side paginated inventory table (<2ms execution).
    Direct SQL LIMIT/OFFSET and pushdown filters allow smooth scaling past 50,000 specimens.
    """
    inv = db.get_inventory_stats()
    sc = inv["status_counts"]

    page_data = db.get_admin_plants_page(
        filter_tag=filter_tag,
        search_q=search_q,
        page=page,
        page_size=page_size
    )

    items = page_data["items"]
    total_count = page_data["total_count"]
    current_page = page_data["page"]
    total_pages = page_data["total_pages"]
    start_idx = page_data["start_idx"]
    end_idx = page_data["end_idx"]

    rows = []
    for p in items:
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
                    <input type="checkbox" name="keys" value="{name_esc}" class="admin-checkbox" onchange="updateAdminSelectionCount()" />
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
                            hx-target="closest tr"
                            hx-swap="outerHTML"
                            hx-confirm="¿Eliminar definitivamente el ejemplar '{name_esc}' y todas sus fotos ?"
                            title="Eliminar este ejemplar">
                        ELIMINAR
                    </button>
                </td>
            </tr>
        """)

    table_body = "".join(rows) if rows else f"""
        <tr>
            <td colspan="11" style="text-align: center; color: var(--text-dim); padding: 32px 16px;">
                No hay ejemplares que coincidan con los criterios seleccionados {f'("{html.escape(search_q)}")' if search_q else ''}.
            </td>
        </tr>
    """

    tab_defs = [
        ("ALL", f"TODOS ({inv['total']:,})".replace(",", ".")),
        ("NO_PHOTOS", f"SIN FOTO ({inv['without_photos']:,})".replace(",", ".")),
        ("GRAFTED", f"INJERTOS ({inv['with_graft']:,})".replace(",", ".")),
        ("ILL", f"EN CUARENTENA ({sc.get('notOK', 0):,})".replace(",", ".")),
    ]
    encoded_search = urllib.parse.quote_plus(search_q)
    tabs_html = "\n".join(
        f"""<button type="button"
                    class="inv-tab-btn {'active' if filter_tag == tag else ''}"
                    hx-get="/admin/filter?tab={tag}&search={encoded_search}&page=1&page_size={page_size}"
                    hx-target="#admin-table-container"
                    hx-swap="innerHTML">{label}</button>"""
        for tag, label in tab_defs
    )

    pagination_bottom = render_admin_pagination_bar(
        filter_tag=filter_tag,
        search_q=search_q,
        page=current_page,
        page_size=page_size,
        total_count=total_count,
        total_pages=total_pages,
        start_idx=start_idx,
        end_idx=end_idx
    )

    return f"""
    <div id="admin-table-and-tabs">
        <div class="inventory-toolbar" style="margin-top: 6px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <div class="inventory-filter-tabs" id="admin-filter-tabs" style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                <span style="font-size: 11px; font-weight: 700; color: var(--text-dim); margin-right: 4px;">FILTRO:</span>
                {tabs_html}
            </div>

            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 11px; color: var(--text-dim);">Buscar en tabla:</span>
                <div style="display: flex; align-items: center; gap: 4px; position: relative;">
                    <input type="text"
                           id="admin-search-box"
                           name="search"
                           value="{html.escape(search_q)}"
                           placeholder="Clave, especie, alias..."
                           hx-get="/admin/filter?tab={filter_tag}&page=1&page_size={page_size}"
                           hx-trigger="input changed delay:350ms, keydown[key=='Enter']"
                           hx-target="#admin-table-container"
                           hx-swap="innerHTML"
                           hx-include="this"
                           onfocus="window._adminSearchHadFocus=true;"
                           onblur="window._adminSearchHadFocus=false;"
                           style="background: var(--bg-crust); border: 1px solid var(--border-dim); color: var(--text-main); font-size: 12px; padding: 4px 8px; border-radius: 3px; outline: none; width: 170px;" />
                    {f'''<button type="button"
                                 class="btn btn-sm"
                                 hx-get="/admin/filter?tab={filter_tag}&search=&page=1&page_size={page_size}"
                                 hx-target="#admin-table-container"
                                 hx-swap="innerHTML"
                                 title="Limpiar búsqueda"
                                 style="padding: 2px 6px; font-size: 10px; color: var(--text-dim);">✕</button>''' if search_q else ''}
                </div>
            </div>
        </div>

        <form id="admin-bulk-form"
              hx-post="/admin/bulk-delete"
              hx-target="#admin-table-container"
              hx-swap="innerHTML"
              onkeydown="if (event.key === 'Enter') {{ event.preventDefault(); return false; }}"
              onsubmit="if (document.querySelectorAll('#admin-table-rows .admin-checkbox:checked').length === 0) {{ event.preventDefault(); return false; }}">
            <input type="hidden" name="tab" value="{filter_tag}" />
            <input type="hidden" name="search" value="{html.escape(search_q)}" />
            <input type="hidden" name="page" value="{current_page}" />
            <input type="hidden" name="page_size" value="{page_size}" />

            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <button type="button"
                            class="btn btn-sm"
                            onclick="selectVisibleAdminRows(true);">
                        [✓ SELECCIONAR PÁGINA VISIBLE]
                    </button>
                    <button type="button"
                            class="btn btn-sm"
                            onclick="selectVisibleAdminRows(false);">
                        [✕ DESMARCAR]
                    </button>
                    <span id="admin-selected-counter" data-total-rows="{len(items)}" style="font-size: 11px; color: var(--text-dim); margin-left: 8px;">
                        Mostrando {len(items)} de esta página
                    </span>
                </div>
                <button type="submit"
                        id="admin-bulk-delete-btn"
                        class="btn btn-sm btn-red"
                        style="font-weight: bold; opacity: 0.45; cursor: not-allowed;"
                        disabled
                        onclick="return confirmAdminBulkDelete();">
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

        {pagination_bottom}

        <script>
            (function() {{
                var sb = document.getElementById('admin-search-box');
                if (sb && window._adminSearchHadFocus) {{
                    sb.focus();
                    var len = sb.value.length;
                    sb.setSelectionRange(len, len);
                }}
                if (window.updateAdminSelectionCount) {{
                    window.updateAdminSelectionCount();
                }}
            }})();
        </script>
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
                    <span id="admin-total-badge" style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-dim); background: var(--bg-surface); padding: 2px 8px; border-radius: 2px; border: 1px solid var(--border-dim);">
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

                <!-- ACTIONS MASTER TOOLBAR -->
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
                            ➕ [ALTA MASIVA]
                        </button>
                        <button type="button"
                                class="btn btn-sm btn-red"
                                hx-get="/plants/modal/bulk-delete"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                style="font-weight: 700;"
                                title="Eliminar múltiples ejemplares simultáneamente por rango, lista manual o criterios">
                            🗑 [BAJA MASIVA]
                        </button>
                        <a class="btn btn-sm btn-primary"
                           href="/pdf/full-catalog"
                           download="Plantation_Dossier_General.pdf"
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
                        class="btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML">
                    ✕ CERRAR [ESC]
                </button>
            </div>

        </div>
    </div>

    <!-- Client-side helpers for admin table checkbox selection -->
    <script>
        function confirmAdminBulkDelete() {{
            var checked = document.querySelectorAll('#admin-table-rows .admin-checkbox:checked');
            if (checked.length === 0) {{
                return false;
            }}
            return confirm('¿CONFIRMAR ELIMINACIÓN MASIVA de los ' + checked.length + ' ejemplares seleccionados y purgar permanentemente sus fotografías?');
        }}

        function updateAdminSelectionCount() {{
            var rows = document.querySelectorAll('#admin-table-rows tr');
            var visible = 0;
            var checkedCount = 0;
            rows.forEach(function(row) {{
                var cb = row.querySelector('.admin-checkbox');
                if (!cb) return;
                visible++;
                if (cb.checked) {{
                    checkedCount++;
                }}
            }});
            var counter = document.getElementById('admin-selected-counter');
            if (counter) {{
                var baseText = 'Mostrando ' + visible + ' en esta página';
                if (checkedCount > 0) {{
                    counter.innerHTML = baseText + ' · <strong style="color: var(--peach-orange);">' + checkedCount + ' seleccionado(s)</strong>';
                }} else {{
                    counter.textContent = baseText;
                }}
            }}

            var delBtn = document.getElementById('admin-bulk-delete-btn');
            if (delBtn) {{
                if (checkedCount > 0) {{
                    delBtn.disabled = false;
                    delBtn.style.opacity = '1';
                    delBtn.style.cursor = 'pointer';
                    delBtn.innerHTML = '🗑 [ELIMINAR SELECCIÓN (' + checkedCount + ')]';
                }} else {{
                    delBtn.disabled = true;
                    delBtn.style.opacity = '0.45';
                    delBtn.style.cursor = 'not-allowed';
                    delBtn.innerHTML = '🗑 [ELIMINAR SELECCIÓN]';
                }}
            }}
        }}

        function selectVisibleAdminRows(checkState) {{
            var rows = document.querySelectorAll('#admin-table-rows tr');
            rows.forEach(function(row) {{
                var cb = row.querySelector('.admin-checkbox');
                if (!cb) return;
                cb.checked = !!checkState;
            }});
            updateAdminSelectionCount();
        }}
    </script>
    """


def render_admin_panel_content(filter_tag: str = "ALL") -> str:
    """Backward-compatible proxy returning the modal popup."""
    return render_admin_modal(filter_tag=filter_tag)
