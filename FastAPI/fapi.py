"""
Plantation - FastAPI Router & HTMX Server-Rendered Components
Zero custom JavaScript - Pure HTML5, CSS3, and HTMX 2.
CLI-like aesthetic with Maple Mono font and Catppuccin theme.
Fast, modular, and optimized for speed.
"""

import csv
import io
import os
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Form, HTTPException, Request, Response, UploadFile, File
from fastapi.responses import HTMLResponse, Response, FileResponse

import db
from img_conv import (
    IMAGES_DIR,
    cleanup_plant_photos,
    delete_photo_file,
    validate_and_save_photo,
)
from pdf_gen import generate_catalog_pdf, generate_single_plant_pdf

router = APIRouter()

# Global state tracker for toggling admin drawer
admin_state = {"open": False}

STATUS_BADGE_CLASSES = {
    "OK": "status-OK",
    "notOK": "status-notOK",
    "Ok": "status-OK",
    "Triving": "status-OK",
    "Disease": "status-notOK",
    "Diseaced": "status-notOK",
    "Extremely Ill": "status-notOK"
}

STATUS_SPANISH = {
    "OK": "OK",
    "notOK": "notOK",
    "Ok": "OK",
    "Triving": "OK",
    "Disease": "notOK",
    "Diseaced": "notOK",
    "Extremely Ill": "notOK"
}


def render_card_html(p: dict) -> str:
    """Renders a single plant card with bounded headers, AKA badge, and thumbnail preview."""
    status = p.get("status", "OK")
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-OK")
    status_es = STATUS_SPANISH.get(status, status)
    photos = p.get("photos", [])
    aka = p.get("aka", "").strip()
    aka_html = f'<span class="plant-aka" title=\'Alias: "{aka}"\'>"{aka}"</span>' if aka else ""
    age_short, age_detailed = db.calculate_plant_age(p.get("sowing_cutting_date"), p.get("graft", ""))

    if photos:
        thumb_src = f"/images/{photos[0]}"
        thumb_html = f"""
            <img class="card-thumbnail-img" src="{thumb_src}" alt="{p.get('name')}" loading="lazy" />
            <span class="thumbnail-badge-count">[{len(photos)} FOTO{'S' if len(photos) > 1 else ''}]</span>
        """
    else:
        thumb_html = f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100%; color: var(--text-dim); text-align: center; padding: 10px;">
                <div style="font-size: 22px; color: var(--border-active); margin-bottom: 4px;">[ ✿ ]</div>
                <div style="font-size: 11px; letter-spacing: 1px;">SIN FOTO ADJUNTA</div>
                <div style="font-size: 9.5px; color: var(--text-dim); margin-top: 2px;">CLAVE: {p.get('name')}</div>
            </div>
        """

    return f"""
    <div class="plant-card" id="plant-card-{p.get('name')}">
        <div class="plant-card-header">
            <div class="plant-key-box" style="display: flex; align-items: center; gap: 4px; flex-wrap: wrap;">
                <span class="plant-key" title="{p.get('name')}">[ID: {p.get('name')}]</span>
                {aka_html}
            </div>
            <div class="plant-status-box">
                <span class="status-badge {status_cls}">● {status_es}</span>
            </div>
        </div>

        <div class="plant-species" title="{p.get('species')}">{p.get('species', 'Sin especie')}</div>

        <div class="card-thumbnail-box">
            {thumb_html}
        </div>

        <div class="plant-specs-list">
            <div class="spec-cell">
                <div class="spec-label">Ubicación</div>
                <div class="spec-val" title="{p.get('location') or '—'}">{p.get('location') or '—'}</div>
            </div>
            <div class="spec-cell">
                <div class="spec-label">Edad</div>
                <div class="spec-val" title="{age_detailed}">{age_short}</div>
            </div>
            <div class="spec-cell">
                <div class="spec-label">Linaje / Padres</div>
                <div class="spec-val" title="{p.get('padres') or '—'}">{p.get('padres') or '—'}</div>
            </div>
            <div class="spec-cell">
                <div class="spec-label">Injerto</div>
                <div class="spec-val" title="{p.get('graft') or '—'}">{p.get('graft') or '—'}</div>
            </div>
            <div class="spec-cell full-width">
                <div class="spec-label">Último Mantenimiento</div>
                <div class="spec-val">Poda: {p.get('last_pruned') or '—'} | Trasplante: {p.get('last_repotted') or '—'}</div>
            </div>
        </div>

        <div class="card-footer">
            <button class="btn btn-sm btn-primary"
                    hx-get="/plants/{p.get('name')}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML">
                [EXPEDIENTE]
            </button>
            <a class="btn btn-sm btn-red"
               href="/pdf/plant/{p.get('name')}"
               target="_blank"
               title="Descargar dossier técnico en PDF">
                [PDF 🗎]
            </a>
        </div>
    </div>
    """


def render_plants_grid(plants: List[dict]) -> str:
    """Renders the plants cards grid or an empty state."""
    if not plants:
        return """
        <div style="background: var(--bg-surface); border: 1px dashed var(--border-dim); padding: 40px 20px; text-align: center; border-radius: 4px; grid-column: 1 / -1;">
            <div style="color: var(--red-crimson); font-size: 18px; font-weight: bold; margin-bottom: 8px;">[ NO SE ENCONTRARON EJEMPLARES ]</div>
            <div style="color: var(--text-dim); font-size: 13px; max-width: 500px; margin: 0 auto 16px auto;">
                No hay plantas registradas con los criterios de búsqueda o filtro seleccionados.
            </div>
            <button class="btn btn-red"
                    hx-get="/plants/modal/new"
                    hx-target="#modal-container"
                    hx-swap="innerHTML">
                + REGISTRAR PRIMER EJEMPLAR
            </button>
        </div>
        """
    cards = [render_card_html(p) for p in plants]
    return f"""<div class="plants-grid">{''.join(cards)}</div>"""


def render_stats_bar() -> str:
    """Renders catalog stats counters with 2 health states."""
    stats = db.get_stats()
    sc = stats.get("status_counts", {})
    ok_count = sc.get('OK', 0)
    not_ok_count = sc.get('notOK', 0)
    return f"""
    <div class="stats-summary" id="stats-bar">
        <div>
            TOTAL EJEMPLARES: <span class="stats-count-tag">{stats.get('total', 0)}</span> |
            FOTOS EN DISCO: <span style="color: var(--blue-sky); font-weight: bold;">{stats.get('total_photos', 0)}</span> |
            UBICACIONES: <span style="color: var(--text-main); font-weight: bold;">{stats.get('locations_count', 0)}</span>
        </div>
        <div style="display: flex; gap: 14px; font-size: 11.5px; font-weight: 600;">
            <span style="color: var(--green-sage);">● OK: {ok_count}</span>
            <span style="color: var(--peach-orange);">● notOK: {not_ok_count}</span>
        </div>
    </div>
    """


@router.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    """Main application shell."""
    plants = db.get_plants()
    admin_state["open"] = False

    content = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>Plantation - Registro Botánico & Dossier PDF</title>
        <meta name="description" content="Gestor botánico y dossiers técnicos con SQLite, HTMX y exportación PDF." />
        <link rel="stylesheet" href="/static/style.css" />
        <script src="https://unpkg.com/htmx.org@2.0.4"></script>
        <script>
            (function() {{
                try {{
                    var t = localStorage.getItem('plantation_theme') || 'catpuchin';
                    document.documentElement.setAttribute('data-theme', t);
                }} catch(e) {{}}
            }})();
        </script>
    </head>
    <body>
        <!-- Header -->
        <header class="cli-header">
            <a href="/" class="brand-box">
                <span class="brand-logo">[PLN]</span>
                <div>
                    <div class="brand-title">PLANTATION <span class="cursor-blink">▋</span></div>
                </div>
            </a>
            <div class="nav-actions">
                <button class="btn btn-red"
                        hx-get="/plants/modal/new"
                        hx-target="#modal-container"
                        hx-swap="innerHTML">
                    + [NUEVO EJEMPLAR]
                </button>
                <div id="admin-nav-slot">
                    <button class="btn"
                            id="admin-nav-btn"
                            hx-get="/admin/toggle"
                            hx-target="#admin-container"
                            hx-swap="innerHTML">
                        ⚙ [ADMINISTRACIÓN]
                    </button>
                </div>
                <!-- Right of administration: Color Scheme Switcher Button & Dropdown -->
                <div class="theme-dropdown-container" id="theme-switcher-container">
                    <button type="button"
                            class="btn"
                            id="theme-toggle-btn"
                            onclick="toggleThemeDropdown(event)"
                            aria-haspopup="true"
                            aria-expanded="false"
                            title="Cambiar esquema de color de la interfaz">
                        🎨 <span id="theme-btn-label">[TEMA: CATPPUCCIN]</span> <span style="font-size: 9px; opacity: 0.8; margin-left: 2px;">▼</span>
                    </button>
                    <div id="theme-dropdown-menu" class="theme-dropdown-menu" style="display: none;">
                        <div class="theme-dropdown-header">ESQUEMA DE COLOR // PALETA</div>
                        
                        <button type="button" class="theme-option-btn" data-theme-name="japanese indigo" onclick="selectTheme('japanese indigo')">
                            <span class="theme-swatch" style="background: #0b1120; border-color: #38bdf8;">
                                <span class="theme-swatch-dot" style="background: #38bdf8; box-shadow: 0 0 6px #38bdf8;"></span>
                            </span>
                            <span class="theme-info">
                                <span class="theme-name">Japanese Indigo</span>
                                <span class="theme-desc">藍染 Aizome · Índigo woad & azul cielo</span>
                            </span>
                            <span class="theme-check">✓</span>
                        </button>

                        <button type="button" class="theme-option-btn" data-theme-name="catpuchin" onclick="selectTheme('catpuchin')">
                            <span class="theme-swatch" style="background: #181926; border-color: #ed8796;">
                                <span class="theme-swatch-dot" style="background: #ed8796; box-shadow: 0 0 6px #ed8796;"></span>
                            </span>
                            <span class="theme-info">
                                <span class="theme-name">Catppuccin</span>
                                <span class="theme-desc">Mocha & Carmesí suave original</span>
                            </span>
                            <span class="theme-check">✓</span>
                        </button>

                        <button type="button" class="theme-option-btn" data-theme-name="golden" onclick="selectTheme('golden')">
                            <span class="theme-swatch" style="background: #17130e; border-color: #f1b343;">
                                <span class="theme-swatch-dot" style="background: #f1b343; box-shadow: 0 0 6px #f1b343;"></span>
                            </span>
                            <span class="theme-info">
                                <span class="theme-name">Golden</span>
                                <span class="theme-desc">Kintsugi · Oro pulido & ámbar bronce</span>
                            </span>
                            <span class="theme-check">✓</span>
                        </button>

                        <button type="button" class="theme-option-btn" data-theme-name="darkerthanblack" onclick="selectTheme('darkerthanblack')">
                            <span class="theme-swatch" style="background: #000000; border-color: #ff334b;">
                                <span class="theme-swatch-dot" style="background: #ff334b; box-shadow: 0 0 6px #ff334b;"></span>
                            </span>
                            <span class="theme-info">
                                <span class="theme-name">Darker Than Black</span>
                                <span class="theme-desc">OLED Noir · Negro absoluto & neón</span>
                            </span>
                            <span class="theme-check">✓</span>
                        </button>
                    </div>
                </div>
            </div>
        </header>

        <!-- Admin / Inventory Drawer -->
        <div id="admin-container"></div>

        <!-- Main Body -->
        <main class="app-layout">
            <!-- Controls & Filters Toolbar -->
            <div class="control-toolbar">
                <div class="search-line">
                    <span class="input-prompt">query&gt;</span>
                    <input type="text"
                           id="search-input"
                           class="search-input"
                           placeholder="Búsqueda por Clave (ej. A2, 900), Alias (ej. ocaso, darkRed), Especie, Ubicación..."
                           oninput="onSearchFilterInput(this.value)"
                           autocomplete="off" />
                    <span id="search-spinner" class="htmx-indicator" style="color: var(--red-crimson); font-size: 11px;">[BUSCANDO...]</span>
                </div>

                <input type="hidden" id="current-status-filter" value="ALL" />
                <input type="hidden" id="current-age-filter" value="ALL" />

                <div class="filter-bar" style="display: flex; flex-wrap: wrap; gap: 12px; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                        <span class="filter-label">ESTADO:</span>
                        <button type="button"
                                class="status-pill status-filter-btn active"
                                onclick="applyPlantFilter('status', 'ALL', this)">
                            TODOS
                        </button>
                        <button type="button"
                                class="status-pill status-pill-ok status-filter-btn"
                                onclick="applyPlantFilter('status', 'OK', this)">
                            ● OK
                        </button>
                        <button type="button"
                                class="status-pill status-pill-notok status-filter-btn"
                                onclick="applyPlantFilter('status', 'notOK', this)">
                            ● notOK
                        </button>
                    </div>

                    <div style="display: inline-block; width: 1px; height: 18px; background: var(--border-dim); margin: 0 4px;"></div>

                    <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                        <span class="filter-label">EDAD:</span>
                        <button type="button"
                                class="status-pill age-filter-btn active"
                                onclick="applyPlantFilter('age', 'ALL', this)">
                            TODAS
                        </button>
                        <button type="button"
                                class="status-pill status-pill-age age-filter-btn"
                                onclick="applyPlantFilter('age', 'less_1', this)">
                            &lt; 1 AÑO
                        </button>
                        <button type="button"
                                class="status-pill status-pill-age age-filter-btn"
                                onclick="applyPlantFilter('age', '1_to_2', this)">
                            1 - 2 AÑOS
                        </button>
                        <button type="button"
                                class="status-pill status-pill-age age-filter-btn"
                                onclick="applyPlantFilter('age', '3_plus', this)">
                            3+ AÑOS
                        </button>
                    </div>
                </div>
            </div>

            <!-- Stats Bar -->
            {render_stats_bar()}

            <!-- Plants Grid Container -->
            <div id="plant-container">
                {render_plants_grid(plants)}
            </div>
        </main>

        <!-- Modal Container -->
        <div id="modal-container"></div>

        <!-- Footer -->
        <footer class="cli-footer">
            <div>
                PLANTATION -- <code style="color: var(--red-crimson);">DB-plantation</code>
            </div>
            <div>
                HTMX //
            </div>
        </footer>
        <!-- Theme Management Script -->
        <script>
            var THEME_LABELS = {{
                'japanese indigo': 'JAPANESE INDIGO',
                'japanese-indigo': 'JAPANESE INDIGO',
                'catpuchin': 'CATPPUCCIN',
                'catppuccin': 'CATPPUCCIN',
                'golden': 'GOLDEN',
                'darkerthanblack': 'DARKER THAN BLACK',
                'darker-than-black': 'DARKER THAN BLACK'
            }};

            function selectTheme(themeName) {{
                try {{
                    localStorage.setItem('plantation_theme', themeName);
                }} catch(e) {{}}
                applyTheme(themeName);
                closeThemeDropdown();
            }}

            function applyTheme(themeName) {{
                document.documentElement.setAttribute('data-theme', themeName);
                var labelEl = document.getElementById('theme-btn-label');
                if (labelEl) {{
                    var clean = THEME_LABELS[themeName] || themeName.toUpperCase();
                    labelEl.textContent = '[TEMA: ' + clean + ']';
                }}
                document.querySelectorAll('.theme-option-btn').forEach(function(btn) {{
                    var t = btn.getAttribute('data-theme-name');
                    if (t === themeName || (themeName === 'catppuccin' && t === 'catpuchin')) {{
                        btn.classList.add('active');
                    }} else {{
                        btn.classList.remove('active');
                    }}
                }});
            }}

            function toggleThemeDropdown(e) {{
                if (e) {{
                    e.stopPropagation();
                    e.preventDefault();
                }}
                var menu = document.getElementById('theme-dropdown-menu');
                var btn = document.getElementById('theme-toggle-btn');
                if (!menu) return;
                var isClosed = menu.style.display === 'none' || !menu.style.display;
                menu.style.display = isClosed ? 'flex' : 'none';
                if (btn) btn.setAttribute('aria-expanded', isClosed ? 'true' : 'false');
            }}

            function closeThemeDropdown() {{
                var menu = document.getElementById('theme-dropdown-menu');
                var btn = document.getElementById('theme-toggle-btn');
                if (menu) menu.style.display = 'none';
                if (btn) btn.setAttribute('aria-expanded', 'false');
            }}

            document.addEventListener('click', function(e) {{
                var container = document.getElementById('theme-switcher-container');
                if (container && !container.contains(e.target)) {{
                    closeThemeDropdown();
                }}
            }});

            document.addEventListener('DOMContentLoaded', function() {{
                var saved = 'catpuchin';
                try {{
                    saved = localStorage.getItem('plantation_theme') || 'catpuchin';
                }} catch(e) {{}}
                applyTheme(saved);
            }});

            var _searchDebounceTimer = null;

            function executePlantFilter() {{
                var searchInp = document.getElementById('search-input');
                var search = searchInp ? searchInp.value.trim() : '';
                var statusVal = document.getElementById('current-status-filter') ? document.getElementById('current-status-filter').value : 'ALL';
                var ageVal = document.getElementById('current-age-filter') ? document.getElementById('current-age-filter').value : 'ALL';

                var params = new URLSearchParams();
                if (search) params.set('search', search);
                if (statusVal && statusVal !== 'ALL') params.set('status', statusVal);
                if (ageVal && ageVal !== 'ALL') params.set('age', ageVal);

                var qs = params.toString();
                var endpoint = '/plants' + (qs ? '?' + qs : '');

                var spinner = document.getElementById('search-spinner');
                if (spinner) spinner.style.display = 'inline-block';

                htmx.ajax('GET', endpoint, {{
                    target: '#plant-container',
                    swap: 'innerHTML'
                }}).then(function() {{
                    if (spinner) spinner.style.display = 'none';
                }}).catch(function() {{
                    if (spinner) spinner.style.display = 'none';
                }});
            }}

            function applyPlantFilter(type, value, btn) {{
                if (type === 'status') {{
                    var el = document.getElementById('current-status-filter');
                    if (el) el.value = value;
                    document.querySelectorAll('.status-filter-btn').forEach(function(b) {{
                        b.classList.remove('active');
                    }});
                }} else if (type === 'age') {{
                    var el = document.getElementById('current-age-filter');
                    if (el) el.value = value;
                    document.querySelectorAll('.age-filter-btn').forEach(function(b) {{
                        b.classList.remove('active');
                    }});
                }}
                if (btn) btn.classList.add('active');
                executePlantFilter();
            }}

            function onSearchFilterInput(val) {{
                clearTimeout(_searchDebounceTimer);
                _searchDebounceTimer = setTimeout(executePlantFilter, 160);
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content)


@router.get("/plants", response_class=HTMLResponse)
def list_plants_partial(
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None
):
    """HTMX endpoint returning reactive filtered plants grid with search, 2-state health, and age."""
    plants = db.get_plants(search_query=search, status_filter=status, age_filter=age)
    return HTMLResponse(render_plants_grid(plants))


# ==============================================================================
# MODALS: VIEW, CREATE (WITH FRIENDLY DRAG & DROP PHOTO UPLOAD), EDIT
# ==============================================================================

def render_photo_item_html(plant_name: str, ph: str) -> str:
    """Renders a photo card in the technical dossier with instant deletion and confirmation pop-up."""
    return f"""
        <div class="modal-photo-item">
            <button type="button"
                    class="photo-delete-badge"
                    hx-delete="/plants/{plant_name}/photos/{ph}"
                    hx-target="#plant-photos-wrapper"
                    hx-swap="innerHTML"
                    hx-confirm="¿Está seguro de eliminar esta fotografía de forma permanente?"
                    title="Eliminar foto del ejemplar">✕</button>
            <img class="modal-photo-thumb" src="/images/{ph}" alt="{ph}" />
            <div style="font-size: 10px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="{ph}">
                {ph}
            </div>
            <button type="button"
                    class="photo-delete-btn"
                    hx-delete="/plants/{plant_name}/photos/{ph}"
                    hx-target="#plant-photos-wrapper"
                    hx-swap="innerHTML"
                    hx-confirm="¿Está seguro de eliminar esta fotografía de forma permanente?"
                    title="Eliminar foto permanentemente">
                🗑 [ELIMINAR]
            </button>
        </div>
    """


def render_view_plant_modal_content(plant: dict, alert_msg: str = "") -> str:
    """Helper to render full view modal content for a plant."""
    status = plant.get("status", "Ok")
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-Ok")
    status_es = STATUS_SPANISH.get(status, status)
    photos = plant.get("photos", [])
    plant_name = plant.get("name", "")

    photo_items = [render_photo_item_html(plant_name, ph) for ph in photos]

    photos_html = "".join(photo_items) if photo_items else """
        <div style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 10px 0; text-align: center;">
            No hay fotografías adjuntas para este ejemplar. Puede arrastrar o seleccionar imágenes abajo.
        </div>
    """

    alert_banner = ""
    if alert_msg:
        alert_banner = f"""
            <div class="alert-box alert-success" style="margin-bottom: 12px; font-size: 12px;">
                ✓ {alert_msg}
            </div>
        """

    return f"""
    <div class="modal-overlay" id="plant-dossier-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title">[EXPEDIENTE TÉCNICO: {plant.get('name')}]</span>
                    <span class="status-badge {status_cls}">● {status_es}</span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="modal-close-btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Cerrar expediente">✕</button>
                </div>
            </div>

            <div class="modal-body">
                {alert_banner}

                <!-- Taxonomy & Lineage Header -->
                <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: var(--red-crimson); font-weight: bold; letter-spacing: 1px;">TAXONOMÍA & CLASIFICACIÓN</div>
                    <div style="font-size: 16px; font-style: italic; color: var(--blue-sky); margin: 3px 0 6px 0; word-break: break-word;">
                        {plant.get('species')}
                    </div>
                    <div style="font-size: 12px; color: var(--text-sub); display: flex; gap: 14px; flex-wrap: wrap;">
                        <span>CLAVE: <strong style="color: var(--text-main); font-weight: 700;">[{plant.get('name')}]</strong></span>
                        {f'<span>ALIAS / AKA: <strong style="color: var(--peach-orange); font-weight: 700;">"{plant.get("aka")}"</strong></span>' if plant.get("aka") else ''}
                        <span>UBICACIÓN FÍSICA: <span style="color: var(--text-main); font-weight: 600;">{plant.get('location') or 'Sin registrar'}</span></span>
                    </div>
                </div>

                <!-- Technical Specification Grid -->
                <div class="form-grid">
                    <div class="form-group">
                        <span class="form-label">Fecha de Registro</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('registration_date') or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Linaje / Progenitores (Padres)</span>
                        <div class="form-input" style="background: var(--bg-mantle); word-break: break-word;">{plant.get('padres') or 'Desconocido'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Fecha Siembra / Esquejado</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('sowing_cutting_date') or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Injerto / Patrón</span>
                        <div class="form-input" style="background: var(--bg-mantle); word-break: break-word;">{plant.get('graft') or 'Sin injerto'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Última Poda</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('last_pruned') or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Último Trasplante</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('last_repotted') or '—'}</div>
                    </div>
                    <div class="form-group full">
                        <span class="form-label">Fertilización & Tratamientos Aplicados</span>
                        <div class="form-input" style="background: var(--bg-mantle); min-height: 50px; white-space: pre-wrap;">{plant.get('fertilizante') or 'Sin tratamientos registrados'}</div>
                    </div>
                    <div class="form-group full">
                        <span class="form-label">Comentarios & Observaciones Clínicas</span>
                        <div class="form-input" style="background: var(--bg-mantle); min-height: 50px; white-space: pre-wrap;">{plant.get('comentarios') or 'Sin observaciones'}</div>
                    </div>
                </div>

                <!-- Photos Section with Friendly Drag & Drop Upload -->
                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="form-label" style="color: var(--red-crimson);">ARCHIVOS FOTOGRÁFICOS ADJUNTOS ({len(photos)})</span>
                        <span style="font-size: 10.5px; color: var(--text-dim);">Formato auto-convertido a AVIF/WebP (&lt;KEY&gt;_&lt;n&gt;)</span>
                    </div>

                    <!-- Friendly Drag-and-Drop Zone -->
                    <form hx-post="/plants/{plant.get('name')}/photos"
                          hx-target="#plant-photos-wrapper"
                          hx-swap="innerHTML"
                          hx-encoding="multipart/form-data"
                          id="individual-photo-form"
                          style="margin-bottom: 14px;">
                        <div class="drop-zone"
                             ondragover="event.preventDefault(); this.classList.add('drag-active');"
                             ondragleave="this.classList.remove('drag-active');"
                             ondrop="event.preventDefault(); this.classList.remove('drag-active'); if (event.dataTransfer.files.length) {{ var fi = document.getElementById('plant-single-photo-input'); fi.files = event.dataTransfer.files; htmx.trigger(this.closest('form'), 'submit'); }}"
                             onclick="document.getElementById('plant-single-photo-input').click();">
                            <input type="file"
                                   id="plant-single-photo-input"
                                   name="photo"
                                   accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/tiff"
                                   style="display:none;"
                                   onchange="if (this.files.length) {{ htmx.trigger(this.closest('form'), 'submit'); }}" />
                            <div class="drop-icon">📷</div>
                            <div class="drop-title">Arrastra una fotografía aquí o <span class="drop-link">selecciona un archivo</span></div>
                            <div class="drop-subtitle">Formatos aceptados: JPG, PNG, WEBP, AVIF, HEIC (máx 10 MB). Subida instantánea.</div>
                        </div>
                    </form>

                    <div id="plant-photos-wrapper">
                        <div class="modal-photo-list">
                            {photos_html}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Sticky Footer with Prominent Actions -->
            <div class="modal-footer-sticky">
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <a class="btn btn-red"
                       href="/pdf/plant/{plant.get('name')}"
                       target="_blank"
                       title="Descargar dossier técnico en PDF">
                        🗎 [DESCARGAR PDF]
                    </a>
                    <a class="btn btn-primary"
                       href="/plants/{plant.get('name')}/dossier"
                       target="_blank"
                       title="Abrir vista de impresión y dossier técnico">
                        🖨 [VER / IMPRIMIR DOSSIER]
                    </a>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="btn btn-primary"
                            hx-get="/plants/{plant.get('name')}/modal/edit"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        ✏ [EDITAR DATOS]
                    </button>
                    <button class="btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            style="font-weight: 600; padding: 7px 18px;"
                            title="Salir del expediente">
                        ✕ [EXIT]
                    </button>
                </div>
            </div>
        </div>
    </div>
    """


@router.get("/plants/{name}", response_class=HTMLResponse)
def view_plant_modal(name: str):
    """Renders comprehensive technical dossier modal with friendly drag & drop upload."""
    plant = db.get_plant(name)
    if not plant:
        return HTMLResponse("<div class='modal-overlay'><div class='modal-dialog'><div class='modal-body'>Planta no encontrada.</div></div></div>")
    return HTMLResponse(render_view_plant_modal_content(plant))


@router.get("/plants/modal/new", response_class=HTMLResponse)
def new_plant_modal():
    """Renders the New Plant registration modal with friendly drag & drop photo uploader and default dates."""
    existing_keys = db.get_all_keys()
    keys_datalist = "".join([f'<option value="{k}">' for k in existing_keys])
    today_str = datetime.now().strftime("%Y-%m-%d")

    return HTMLResponse(f"""
    <div class="modal-overlay" id="new-plant-modal">
        <div class="modal-dialog">
            <form id="new-plant-form"
                  hx-post="/plants"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  enctype="multipart/form-data"
                  hx-encoding="multipart/form-data"
                  class="modal-form-wrapper">

                <!-- Header without top save button -->
                <div class="modal-header">
                    <span class="modal-title">+ [REGISTRAR NUEVO EJEMPLAR BOTÁNICO]</span>
                    <button type="button"
                            class="modal-close-btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Cerrar ventana">✕</button>
                </div>

                <div class="modal-body">
                    <datalist id="existing-keys-list">
                        {keys_datalist}
                    </datalist>

                    <div class="form-grid">
                        <!-- Section 01 -->
                        <div class="form-section-title">01 // IDENTIFICACIÓN & ESTADO SANITARIO</div>

                        <div class="form-group">
                            <label class="form-label" for="inp-key">CLAVE (NAME KEY) *</label>
                            <input type="text"
                                   id="inp-key"
                                   name="name"
                                   placeholder="Ej. A3, 105, B-12 (letras y números, máx 20)"
                                   maxlength="20"
                                   required
                                   class="form-input" />
                            <span style="font-size: 10px; color: var(--text-dim);">Identificador alfanumérico único.</span>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-aka">ALIAS / NOMBRE ESPECIAL (AKA)</label>
                            <input type="text"
                                   id="inp-aka"
                                   name="aka"
                                   placeholder="Ej. ocaso, darkRed, golden..."
                                   class="form-input" />
                            <span style="font-size: 10px; color: var(--text-dim);">Nombre especial o comercial (ej. para injertos o clones).</span>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-status">ESTADO SANITARIO *</label>
                            <select id="inp-status" name="status" class="form-select" required>
                                <option value="OK" selected>● OK (Saludable / Verde)</option>
                                <option value="notOK">● notOK (Atención / Naranja)</option>
                            </select>
                        </div>

                        <!-- Section 02 -->
                        <div class="form-section-title">02 // TAXONOMÍA & UBICACIÓN FÍSICA</div>

                        <div class="form-group full">
                            <label class="form-label" for="inp-species">ESPECIE BOTÁNICA / NOMBRE COMÚN *</label>
                            <input type="text"
                                   id="inp-species"
                                   name="species"
                                   placeholder="Ej. Ariocarpus retusus / Lophophora williamsii"
                                   required
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-location">UBICACIÓN FÍSICA</label>
                            <input type="text"
                                   id="inp-location"
                                   name="location"
                                   placeholder="Ej. Invernadero 2, Estante B"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-reg-date">FECHA DE REGISTRO</label>
                            <input type="date"
                                   id="inp-reg-date"
                                   name="registration_date"
                                   value="{today_str}"
                                   class="form-input" />
                        </div>

                        <!-- Section 03 -->
                        <div class="form-section-title">03 // LINAJE, CULTIVO & INJERTO</div>

                        <div class="form-group">
                            <label class="form-label" for="inp-padres">PADRES / LINAJE</label>
                            <input type="text"
                                   id="inp-padres"
                                   name="padres"
                                   list="existing-keys-list"
                                   placeholder="Ej. A1 + 900, o clave existente, o Desconocido"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-sow-date">FECHA SIEMBRA / ESQUEJE / INJERTO</label>
                            <input type="date"
                                   id="inp-sow-date"
                                   name="sowing_cutting_date"
                                   value="{today_str}"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-graft">INJERTO / PATRÓN</label>
                            <input type="text"
                                   id="inp-graft"
                                   name="graft"
                                   placeholder="Ej. Sin injerto, o Myrtillocactus"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="inp-repotted">ÚLTIMO TRASPLANTE</label>
                            <input type="text"
                                   id="inp-repotted"
                                   name="last_repotted"
                                   placeholder="Ej. 2025-02-10 (Sustrato mineral 80% pómice)"
                                   class="form-input" />
                        </div>

                        <div class="form-group full">
                            <label class="form-label" for="inp-pruned">ÚLTIMA PODA</label>
                            <input type="text"
                                   id="inp-pruned"
                                   name="last_pruned"
                                   placeholder="Ej. 2025-08-15 (Limpieza radicular y poda apical)"
                                   class="form-input" />
                        </div>

                        <!-- Section 04 -->
                        <div class="form-section-title">04 // TRATAMIENTOS & OBSERVACIONES</div>

                        <div class="form-group full">
                            <label class="form-label" for="inp-fert">FERTILIZANTE Y TRATAMIENTOS</label>
                            <textarea id="inp-fert"
                                      name="fertilizante"
                                      placeholder="Tipos de fertilizantes aplicados, fechas, quelatos, tratamientos fitosanitarios..."
                                      class="form-textarea"></textarea>
                        </div>

                        <div class="form-group full">
                            <label class="form-label" for="inp-notes">COMENTARIOS & NOTAS</label>
                            <textarea id="inp-notes"
                                      name="comentarios"
                                      placeholder="Observaciones de floración, velocidad de desarrollo, notas morfológicas..."
                                      class="form-textarea"></textarea>
                        </div>

                        <!-- Friendly Drag-and-Drop Photo Uploader for New Plant -->
                        <div class="form-group full">
                            <div class="form-section-title">05 // FOTOGRAFÍAS ADJUNTAS (OPCIONAL)</div>
                            <div class="drop-zone"
                                 id="new-plant-dropzone"
                                 ondragover="event.preventDefault(); this.classList.add('drag-active');"
                                 ondragleave="this.classList.remove('drag-active');"
                                 ondrop="event.preventDefault(); this.classList.remove('drag-active'); if (event.dataTransfer.files.length) {{ var fi = document.getElementById('new-plant-photos-input'); fi.files = event.dataTransfer.files; var ps = document.getElementById('new-photo-preview-strip'); ps.innerHTML = '<span class=\\'preview-chip\\'><span class=\\'preview-chip-icon\\'>✓</span> ' + event.dataTransfer.files.length + ' foto(s) seleccionada(s) lista(s) para subir</span>'; }}"
                                 onclick="if (event.target.id !== 'new-plant-photos-input') document.getElementById('new-plant-photos-input').click();">
                                <input type="file"
                                       id="new-plant-photos-input"
                                       name="photos"
                                       multiple
                                       accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/tiff"
                                       style="display:none;"
                                       onclick="event.stopPropagation();"
                                       onchange="var ps = document.getElementById('new-photo-preview-strip'); if (this.files.length) {{ ps.innerHTML = '<span class=\\'preview-chip\\'><span class=\\'preview-chip-icon\\'>✓</span> ' + this.files.length + ' foto(s) seleccionada(s) lista(s) para subir</span>'; }} else {{ ps.innerHTML = ''; }}" />
                                <div class="drop-icon">📷</div>
                                <div class="drop-title">Arrastra fotos aquí o <span class="drop-link">selecciona archivos</span></div>
                                <div class="drop-subtitle">Formatos: JPG, PNG, WEBP, AVIF, HEIC. Soporta selección múltiple simultánea.</div>
                            </div>
                            <div id="new-photo-preview-strip" class="preview-strip"></div>
                        </div>
                    </div>
                </div>

                <!-- Sticky Footer with Prominent Save Button -->
                <div class="modal-footer-sticky">
                    <button type="button"
                            class="btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        ✕ [CANCELAR]
                    </button>
                    <button type="submit"
                            class="btn btn-green"
                            style="font-size: 13px; font-weight: 700; padding: 8px 20px;">
                        💾 [GUARDAR NUEVO EJEMPLAR]
                    </button>
                </div>
            </form>
        </div>
    </div>
    """)


@router.post("/plants", response_class=HTMLResponse)
async def create_plant_submit(
    name: str = Form(...),
    species: str = Form(...),
    aka: str = Form(""),
    location: str = Form(""),
    registration_date: str = Form(""),
    padres: str = Form(""),
    sowing_cutting_date: str = Form(""),
    graft: str = Form(""),
    last_pruned: str = Form(""),
    last_repotted: str = Form(""),
    fertilizante: str = Form(""),
    status: str = Form("OK"),
    comentarios: str = Form(""),
    photos: List[UploadFile] = File([])
):
    """Processes creation of a new plant record including friendly multi-photo handling and aka."""
    data = {
        "name": name,
        "species": species,
        "aka": aka,
        "location": location,
        "registration_date": registration_date,
        "padres": padres,
        "sowing_cutting_date": sowing_cutting_date,
        "graft": graft,
        "last_pruned": last_pruned,
        "last_repotted": last_repotted,
        "fertilizante": fertilizante,
        "status": status,
        "comentarios": comentarios,
        "photos": []
    }

    success, msg_or_key = db.create_plant(data)
    if not success:
        return HTMLResponse(f"""
        <div class="modal-overlay">
            <div class="modal-dialog" style="max-width: 480px;">
                <div class="modal-header">
                    <span class="modal-title" style="color: var(--red-crimson);">[ERROR DE VALIDACIÓN]</span>
                    <button class="modal-close-btn" hx-get="/modal/close" hx-target="#modal-container" hx-swap="innerHTML">✕</button>
                </div>
                <div class="modal-body">
                    <div class="alert-box alert-error">{msg_or_key}</div>
                    <div style="text-align: right; margin-top: 12px;">
                        <button class="btn btn-red" hx-get="/plants/modal/new" hx-target="#modal-container" hx-swap="innerHTML">VOLVER A INTENTAR</button>
                    </div>
                </div>
            </div>
        </div>
        """)

    # Save uploaded photos if any
    clean_key_name = msg_or_key
    if photos:
        for p_file in photos:
            if p_file and getattr(p_file, "filename", None):
                content = await p_file.read()
                if len(content) > 0:
                    p_success, p_filename, _ = validate_and_save_photo(clean_key_name, content, p_file.filename)
                    if p_success and p_filename:
                        db.add_photo_to_plant(clean_key_name, p_filename)

    # Immediately close modal and update plants grid & stats via OOB swaps
    plants = db.get_plants()
    admin_oob = f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>' if admin_state.get("open") else ""
    return HTMLResponse(f"""
        <div id="plant-container" hx-swap-oob="innerHTML">
            {render_plants_grid(plants)}
        </div>
        <div id="stats-bar" hx-swap-oob="outerHTML">
            {render_stats_bar()}
        </div>
    """ + admin_oob)


@router.get("/plants/{name}/modal/edit", response_class=HTMLResponse)
def edit_plant_modal(name: str):
    """Renders the Edit modal form for an existing plant with prominent, intuitive Save controls."""
    plant = db.get_plant(name)
    if not plant:
        return HTMLResponse("<div class='modal-overlay'><div class='modal-dialog'><div class='modal-body'>Planta no encontrada.</div></div></div>")

    existing_keys = db.get_all_keys()
    keys_datalist = "".join([f'<option value="{k}">' for k in existing_keys])
    st = plant.get("status", "Ok")
    is_disease = (st in ("Disease", "Diseaced"))
    status_cls = STATUS_BADGE_CLASSES.get(st, "status-Ok")
    status_es = STATUS_SPANISH.get(st, st)
    photos = plant.get("photos", [])

    photo_previews = []
    for ph in photos:
        photo_previews.append(f"""
            <div style="display: flex; align-items: center; gap: 8px; background: var(--bg-mantle); padding: 4px 8px; border: 1px solid var(--border-dim); border-radius: 3px;">
                <img src="/images/{ph}" style="width: 28px; height: 28px; object-fit: cover; border-radius: 2px;" alt="{ph}" />
                <span style="font-size: 10.5px; color: var(--text-dim);">{ph}</span>
            </div>
        """)
    photos_summary_html = "".join(photo_previews) if photo_previews else '<span style="font-size: 11px; color: var(--text-dim);">Sin fotografías registradas aún.</span>'

    return HTMLResponse(f"""
    <div class="modal-overlay" id="edit-plant-modal">
        <div class="modal-dialog">
            <form id="edit-plant-form"
                  hx-post="/plants/{plant.get('name')}/edit"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  class="modal-form-wrapper">

                <!-- Header Pinned at Top without save button -->
                <div class="modal-header">
                    <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                        <span class="modal-title" style="color: var(--red-crimson);">[EDITAR FICHA TÉCNICA: {plant.get('name')}]</span>
                        <span class="status-badge {status_cls}">● {status_es}</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <button type="button"
                                class="btn btn-sm"
                                hx-get="/plants/{plant.get('name')}"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                title="Volver al expediente técnico">
                            ← EXPEDIENTE
                        </button>
                        <button type="button"
                                class="modal-close-btn"
                                hx-get="/modal/close"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                title="Cerrar ventana">✕</button>
                    </div>
                </div>

                <!-- Scrollable Body with Logical Sections -->
                <div class="modal-body">
                    <!-- Informative Banner -->
                    <div style="background: rgba(166, 227, 161, 0.08); border: 1px solid var(--green-sage); border-radius: 3px; padding: 10px 14px; font-size: 11.5px; display: flex; align-items: center; justify-content: space-between; gap: 10px;">
                        <div>
                            <span style="color: var(--green-sage); font-weight: bold;">EDICIÓN ACTIVA:</span> Modifique los datos que desee actualizar y haga clic en <strong>[GUARDAR CAMBIOS]</strong> al pie del formulario.
                        </div>
                        <div style="color: var(--text-dim); font-size: 11px; white-space: nowrap;">
                            CLAVE SQLITE: <strong style="color: var(--red-crimson);">{plant.get('name')}</strong>
                        </div>
                    </div>

                    <datalist id="existing-keys-list-edit">
                        {keys_datalist}
                    </datalist>

                    <div class="form-grid">
                        <!-- Section 01 -->
                        <div class="form-section-title">01 // IDENTIFICACIÓN & ESTADO SANITARIO</div>

                        <div class="form-group">
                            <label class="form-label">CLAVE (KEY - IDENTIFICADOR PRIMARIO)</label>
                            <input type="text"
                                   value="{plant.get('name')}"
                                   readonly
                                   style="opacity: 0.7; cursor: not-allowed;"
                                   class="form-input" />
                            <span style="font-size: 10px; color: var(--text-dim);">La clave es el identificador primario inmutable.</span>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-aka">ALIAS / NOMBRE ESPECIAL (AKA)</label>
                            <input type="text"
                                   id="edit-aka"
                                   name="aka"
                                   value="{plant.get('aka') or ''}"
                                   placeholder="Ej. ocaso, darkRed, golden..."
                                   class="form-input" />
                            <span style="font-size: 10px; color: var(--text-dim);">Nombre especial para plantas injertadas o cultivares.</span>
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-status">ESTADO SANITARIO *</label>
                            <select id="edit-status" name="status" class="form-select" required>
                                <option value="OK" {'selected' if st == 'OK' or st in ('Ok', 'Triving') else ''}>● OK (Saludable / Verde)</option>
                                <option value="notOK" {'selected' if st == 'notOK' or is_disease or st == 'Extremely Ill' else ''}>● notOK (Atención / Naranja)</option>
                            </select>
                        </div>

                        <!-- Section 02 -->
                        <div class="form-section-title">02 // TAXONOMÍA & UBICACIÓN FÍSICA</div>

                        <div class="form-group full">
                            <label class="form-label" for="edit-species">ESPECIE BOTÁNICA / NOMBRE COMÚN *</label>
                            <input type="text"
                                   id="edit-species"
                                   name="species"
                                   value="{plant.get('species') or ''}"
                                   required
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-location">UBICACIÓN FÍSICA</label>
                            <input type="text"
                                   id="edit-location"
                                   name="location"
                                   value="{plant.get('location') or ''}"
                                   placeholder="Ej. Invernadero A, Banco 1"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-reg-date">FECHA DE REGISTRO</label>
                            <input type="date"
                                   id="edit-reg-date"
                                   name="registration_date"
                                   value="{plant.get('registration_date') or ''}"
                                   class="form-input" />
                        </div>

                        <!-- Section 03 -->
                        <div class="form-section-title">03 // LINAJE, CULTIVO & INJERTO</div>

                        <div class="form-group">
                            <label class="form-label" for="edit-padres">PADRES / LINAJE</label>
                            <input type="text"
                                   id="edit-padres"
                                   name="padres"
                                   list="existing-keys-list-edit"
                                   value="{plant.get('padres') or ''}"
                                   placeholder="Ej. A1 + 900, o clave existente, o Desconocido"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-sow-date">FECHA SIEMBRA / ESQUEJE / INJERTO</label>
                            <input type="date"
                                   id="edit-sow-date"
                                   name="sowing_cutting_date"
                                   value="{plant.get('sowing_cutting_date') or ''}"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-graft">INJERTO / PATRÓN</label>
                            <input type="text"
                                   id="edit-graft"
                                   name="graft"
                                   value="{plant.get('graft') or ''}"
                                   placeholder="Ej. Sin injerto, o Myrtillocactus"
                                   class="form-input" />
                        </div>

                        <div class="form-group">
                            <label class="form-label" for="edit-repotted">ÚLTIMO TRASPLANTE</label>
                            <input type="text"
                                   id="edit-repotted"
                                   name="last_repotted"
                                   value="{plant.get('last_repotted') or ''}"
                                   placeholder="Ej. 2025-02-18 (Sustrato mineral 80% pómice)"
                                   class="form-input" />
                        </div>

                        <div class="form-group full">
                            <label class="form-label" for="edit-pruned">ÚLTIMA PODA</label>
                            <input type="text"
                                   id="edit-pruned"
                                   name="last_pruned"
                                   value="{plant.get('last_pruned') or ''}"
                                   placeholder="Ej. 2025-11-04 (Limpieza raíces secundarias)"
                                   class="form-input" />
                        </div>

                        <!-- Section 04 -->
                        <div class="form-section-title">04 // TRATAMIENTOS & OBSERVACIONES</div>

                        <div class="form-group full">
                            <label class="form-label" for="edit-fert">FERTILIZANTE Y TRATAMIENTOS</label>
                            <textarea id="edit-fert"
                                      name="fertilizante"
                                      rows="3"
                                      placeholder="Tipos de fertilizantes aplicados, fechas, quelatos, tratamientos fitosanitarios..."
                                      class="form-textarea">{plant.get('fertilizante') or ''}</textarea>
                        </div>

                        <div class="form-group full">
                            <label class="form-label" for="edit-notes">COMENTARIOS & NOTAS CLÍNICAS</label>
                            <textarea id="edit-notes"
                                      name="comentarios"
                                      rows="3"
                                      placeholder="Observaciones de floración, velocidad de desarrollo, notas morfológicas..."
                                      class="form-textarea">{plant.get('comentarios') or ''}</textarea>
                        </div>

                        <!-- Section 05: Photos summary in edit view -->
                        <div class="form-group full">
                            <div class="form-section-title">05 // FOTOGRAFÍAS ADJUNTAS ({len(photos)})</div>
                            <div style="display: flex; gap: 8px; flex-wrap: wrap; margin-top: 6px;">
                                {photos_summary_html}
                            </div>
                            <span style="font-size: 10.5px; color: var(--text-dim); margin-top: 6px;">Para subir o eliminar fotos, use la zona de arrastre en el <strong>Expediente</strong>.</span>
                        </div>
                    </div>
                </div>

                <!-- Footer Pinned at Bottom with Prominent Save Button -->
                <div class="modal-footer-sticky">
                    <button type="button"
                            class="btn"
                            hx-get="/plants/{plant.get('name')}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        ← VOLVER AL EXPEDIENTE
                    </button>
                    <div style="display: flex; gap: 8px; align-items: center;">
                        <button type="button"
                                class="btn"
                                hx-get="/modal/close"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                title="Salir">
                            ✕ [EXIT]
                        </button>
                        <button type="submit"
                                class="btn btn-green"
                                style="font-size: 13px; font-weight: 700; padding: 8px 24px; box-shadow: 0 0 16px rgba(166, 227, 161, 0.3);">
                            💾 [GUARDAR CAMBIOS]
                        </button>
                    </div>
                </div>
            </form>
        </div>
    </div>
    """)


@router.post("/plants/{name}/edit", response_class=HTMLResponse)
def update_plant_submit(
    name: str,
    species: str = Form(...),
    aka: str = Form(""),
    location: str = Form(""),
    registration_date: str = Form(""),
    padres: str = Form(""),
    sowing_cutting_date: str = Form(""),
    graft: str = Form(""),
    last_pruned: str = Form(""),
    last_repotted: str = Form(""),
    fertilizante: str = Form(""),
    status: str = Form("OK"),
    comentarios: str = Form("")
):
    """Processes updates to plant record and directly returns updated view modal with live OOB card update."""
    data = {
        "species": species,
        "aka": aka,
        "location": location,
        "registration_date": registration_date,
        "padres": padres,
        "sowing_cutting_date": sowing_cutting_date,
        "graft": graft,
        "last_pruned": last_pruned,
        "last_repotted": last_repotted,
        "fertilizante": fertilizante,
        "status": status,
        "comentarios": comentarios
    }

    db.update_plant(name, data)
    updated = db.get_plant(name)
    if not updated:
        return HTMLResponse("<div class='modal-overlay'><div class='modal-dialog'><div class='modal-body'>Error al actualizar.</div></div></div>")

    # Render updated view modal content with prominent success banner
    updated_modal = render_view_plant_modal_content(updated, alert_msg=f"Cambios guardados con éxito en la ficha de '{name}'.")

    # Out-of-band updates: update the card in the main grid and stats bar
    oob_card = f'<div id="plant-card-{name}" hx-swap-oob="outerHTML">{render_card_html(updated)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    oob_admin = f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>' if admin_state.get("open") else ""

    return HTMLResponse(updated_modal + oob_card + oob_stats + oob_admin)


@router.delete("/plants/{name}", response_class=HTMLResponse)
def delete_plant_endpoint(name: str):
    """Deletes single plant and triggers automatic photo cleanup on disk."""
    success, photos_to_clean = db.delete_plant(name)
    if success:
        cleanup_plant_photos(photos_to_clean)
    plants = db.get_plants()
    oob_admin = f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>' if admin_state.get("open") else ""

    # Close modal if open and update stats bar
    return HTMLResponse(
        render_plants_grid(plants) +
        '<div id="modal-container" hx-swap-oob="innerHTML"></div>' +
        f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>' +
        oob_admin
    )


@router.post("/plants/{name}/photos", response_class=HTMLResponse)
async def upload_plant_photo(name: str, photo: UploadFile = File(...)):
    """Uploads, validates (<=10MB), converts to AVIF/WebP, saves to disk, and updates DB."""
    content = await photo.read()
    success, filename, msg = validate_and_save_photo(name, content, photo.filename or "")

    if not success:
        return HTMLResponse(f"""
            <div class="alert-box alert-error" style="margin-bottom: 8px;">{msg}</div>
        """)

    db.add_photo_to_plant(name, filename)
    plant = db.get_plant(name)
    photos = plant.get("photos", []) if plant else []

    photo_items = [render_photo_item_html(name, ph) for ph in photos]

    # Also update card in main grid OOB
    oob_card = f'<div id="plant-card-{name}" hx-swap-oob="outerHTML">{render_card_html(plant)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    oob_admin = f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>' if admin_state.get("open") else ""

    return HTMLResponse(f"""
        <div class="modal-photo-list">
            {''.join(photo_items)}
        </div>
        <div class="alert-box alert-success" style="margin-top: 8px; font-size: 11px;">
            ✓ Foto '{filename}' guardada correctamente en disco.
        </div>
    """ + oob_card + oob_stats + oob_admin)


@router.post("/plants/{name}/photos/{filename}/delete", response_class=HTMLResponse)
@router.delete("/plants/{name}/photos/{filename}", response_class=HTMLResponse)
def remove_plant_photo(name: str, filename: str):
    """Removes photo from plant record and deletes file from disk."""
    db.remove_photo_from_plant(name, filename)
    delete_photo_file(filename)

    plant = db.get_plant(name)
    photos = plant.get("photos", []) if plant else []

    photo_items = [render_photo_item_html(name, ph) for ph in photos]

    # Update main card and stats OOB
    oob_card = f'<div id="plant-card-{name}" hx-swap-oob="outerHTML">{render_card_html(plant)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    oob_admin = f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>' if admin_state.get("open") else ""

    empty_html = '<div style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 10px 0; text-align: center;">No hay fotografías adjuntas para este ejemplar. Puede arrastrar o seleccionar imágenes abajo.</div>'

    return HTMLResponse(f"""
        <div class="modal-photo-list">
            {''.join(photo_items) if photo_items else empty_html}
        </div>
        <div class="alert-box alert-success" style="margin-top: 8px; font-size: 11px;">
            ✓ Foto '{filename}' eliminada del expediente.
        </div>
    """ + oob_card + oob_stats + oob_admin)


# ==============================================================================
# ADMIN & INVENTORY MODULE: TOGGLEABLE, METRICS, EXPORTS & BULK MANAGEMENT
# ==============================================================================

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
        plants_to_show = [p for p in all_plants if p.get("status") in ("Diseaced", "Disease", "Extremely Ill")]
    else:
        plants_to_show = all_plants

    rows = []
    for p in plants_to_show:
        st = p.get("status", "Ok")
        status_cls = STATUS_BADGE_CLASSES.get(st, "status-Ok")
        status_es = STATUS_SPANISH.get(st, st)
        photos = p.get("photos", [])
        photo_badge = f'<span style="color: var(--blue-sky); font-weight: bold;">{len(photos)}</span>' if photos else '<span style="color: var(--text-dim);">0</span>'

        rows.append(f"""
            <tr>
                <td style="text-align: center;">
                    <input type="checkbox" name="keys" value="{p.get('name')}" class="admin-checkbox" />
                </td>
                <td style="font-weight: bold; color: var(--red-crimson);">{p.get('name')}</td>
                <td style="font-style: italic; color: var(--blue-sky); max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{p.get('species')}">{p.get('species')}</td>
                <td><span class="status-badge {status_cls}" style="font-size: 9.5px;">● {status_es}</span></td>
                <td>{p.get('location') or '—'}</td>
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
                            hx-confirm="¿Eliminar {p.get('name')} y sus fotos del disco?">
                        ELIMINAR
                    </button>
                </td>
            </tr>
        """)

    table_body = "".join(rows) if rows else """
        <tr>
            <td colspan="9" style="text-align: center; color: var(--text-dim); padding: 18px;">
                No hay ejemplares en esta categoría de inventario.
            </td>
        </tr>
    """

    disease_total = sc.get('Diseaced', 0) + sc.get('Disease', 0)

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

        <!-- Inventory Metrics Grid -->
        <div class="inventory-stats-grid">
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--red-crimson);">{inv['total']}</div>
                <div class="inventory-stat-lbl">EJEMPLARES TOTALES</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--green-sage);">{sc.get('Triving', 0)} / {sc.get('Ok', 0)}</div>
                <div class="inventory-stat-lbl">PRÓSPEROS / SALUDABLES</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--peach-orange);">{disease_total} / {sc.get('Extremely Ill', 0)}</div>
                <div class="inventory-stat-lbl">ENFERMOS / MUY ENF.</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--blue-sky);">{inv['with_photos']} <span style="font-size: 12px; color: var(--text-dim);">({inv['total_photos']} fotos)</span></div>
                <div class="inventory-stat-lbl">CON REGISTRO FOTO</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: { 'var(--red-crimson)' if inv['without_photos'] > 0 else 'var(--text-sub)' };">{inv['without_photos']}</div>
                <div class="inventory-stat-lbl">SIN FOTOGRAFÍA</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--text-main);">{inv['with_graft']} <span style="font-size: 12px; color: var(--text-dim);">({inv['own_roots']} r. propia)</span></div>
                <div class="inventory-stat-lbl">INJERTADOS</div>
            </div>
            <div class="inventory-stat-card">
                <div class="inventory-stat-val" style="color: var(--green-sage);">{len(inv['location_counts'])}</div>
                <div class="inventory-stat-lbl">UBICACIONES ACTIVAS</div>
            </div>
        </div>

        <!-- Inventory Actions & Filter Tabs -->
        <div class="inventory-toolbar">
            <div class="inventory-filter-tabs">
                <span style="font-size: 11px; color: var(--text-dim); line-height: 24px; margin-right: 4px;">FILTRO TABLA:</span>
                <button class="inv-tab-btn {'active' if filter_tag == 'ALL' else ''}"
                        hx-get="/admin/filter?tab=ALL"
                        hx-target="#admin-panel"
                        hx-swap="outerHTML">
                    TODOS ({inv['total']})
                </button>
                <button class="inv-tab-btn {'active' if filter_tag == 'NO_PHOTOS' else ''}"
                        hx-get="/admin/filter?tab=NO_PHOTOS"
                        hx-target="#admin-panel"
                        hx-swap="outerHTML">
                    SIN FOTO ({inv['without_photos']})
                </button>
                <button class="inv-tab-btn {'active' if filter_tag == 'GRAFTED' else ''}"
                        hx-get="/admin/filter?tab=GRAFTED"
                        hx-target="#admin-panel"
                        hx-swap="outerHTML">
                    INJERTOS ({inv['with_graft']})
                </button>
                <button class="inv-tab-btn {'active' if filter_tag == 'ILL' else ''}"
                        hx-get="/admin/filter?tab=ILL"
                        hx-target="#admin-panel"
                        hx-swap="outerHTML">
                    EN CUARENTENA ({disease_total + sc.get('Extremely Ill', 0)})
                </button>
            </div>

            <!-- Export Tools -->
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
                   title="Exportar inventario estructurado a archivo CSV para hojas de cálculo">
                    ⭳ [EXPORTAR CSV]
                </a>
            </div>
        </div>

        <!-- Bulk Deletion Form -->
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
                <div>
                    <button type="submit" class="btn btn-sm btn-red">
                        ⚠ [ELIMINAR SELECCIONADOS Y LIMPIAR FOTOS]
                    </button>
                </div>
            </div>

            <div style="max-height: 400px; overflow-y: auto; border: 1px solid var(--border-dim); border-radius: 3px;">
                <table class="admin-table">
                    <thead>
                        <tr>
                            <th style="width: 36px; text-align: center;">SEL</th>
                            <th>CLAVE</th>
                            <th>ESPECIE</th>
                            <th>ESTADO</th>
                            <th>UBICACIÓN</th>
                            <th>LINAJE / PADRES</th>
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


@router.get("/admin/toggle", response_class=HTMLResponse)
def admin_toggle():
    """Toggles admin drawer between open and closed state."""
    admin_state["open"] = not admin_state["open"]

    if admin_state["open"]:
        panel = render_admin_panel_content("ALL")
        btn = """
            <button class="btn btn-red" id="admin-nav-btn" hx-get="/admin/toggle" hx-target="#admin-container" hx-swap="innerHTML" hx-swap-oob="true">
                ✕ [CERRAR ADMIN]
            </button>
        """
        return HTMLResponse(panel + btn)
    else:
        btn = """
            <button class="btn" id="admin-nav-btn" hx-get="/admin/toggle" hx-target="#admin-container" hx-swap="innerHTML" hx-swap-oob="true">
                ⚙ [ADMINISTRACIÓN]
            </button>
        """
        return HTMLResponse(btn)


@router.get("/admin", response_class=HTMLResponse)
def admin_open():
    """Explicitly opens the admin panel."""
    admin_state["open"] = True
    panel = render_admin_panel_content("ALL")
    btn = """
        <button class="btn btn-red" id="admin-nav-btn" hx-get="/admin/toggle" hx-target="#admin-container" hx-swap="innerHTML" hx-swap-oob="true">
            ✕ [CERRAR ADMIN]
        </button>
    """
    return HTMLResponse(panel + btn)


@router.get("/admin/close", response_class=HTMLResponse)
def admin_close():
    """Explicitly closes admin panel."""
    admin_state["open"] = False
    btn = """
        <button class="btn" id="admin-nav-btn" hx-get="/admin/toggle" hx-target="#admin-container" hx-swap="innerHTML" hx-swap-oob="true">
            ⚙ [ADMINISTRACIÓN]
        </button>
    """
    return HTMLResponse(btn)


@router.get("/admin/filter", response_class=HTMLResponse)
def admin_filter_tab(tab: str = "ALL"):
    """Filters inventory table inside the admin panel."""
    return HTMLResponse(render_admin_panel_content(tab))


@router.post("/admin/bulk-delete", response_class=HTMLResponse)
def admin_bulk_delete(keys: List[str] = Form([])):
    """Bulk deletes selected plants and cleans up all associated photos from disk."""
    if not keys:
        return HTMLResponse(render_admin_panel_content("ALL"))

    deleted_count, photos_to_clean = db.bulk_delete_plants(keys)
    cleaned_photos_count = cleanup_plant_photos(photos_to_clean)

    plants = db.get_plants()
    oob_grid = f'<div id="plant-container" hx-swap-oob="innerHTML">{render_plants_grid(plants)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'

    # Return refreshed admin view with confirmation
    return HTMLResponse(f"""
        <div class="admin-tray">
            <div class="alert-box alert-success" style="margin-bottom: 14px;">
                ✓ Operación masiva exitosa: Se eliminaron {deleted_count} ejemplares de la base de datos SQLite y se purgaron {cleaned_photos_count} archivos de fotos en disco.
            </div>
            <div style="display: flex; justify-content: flex-end; gap: 8px;">
                <button class="btn btn-sm" hx-get="/admin" hx-target="#admin-container" hx-swap="innerHTML">
                    [VOLVER AL INVENTARIO]
                </button>
                <button class="btn btn-sm btn-red" hx-get="/admin/close" hx-target="#admin-container" hx-swap="innerHTML">
                    [CERRAR ADMIN ✕]
                </button>
            </div>
        </div>
    """ + oob_grid + oob_stats)


@router.get("/admin/inventory.csv")
def export_inventory_csv():
    """Generates and downloads a complete CSV spreadsheet of all plants in inventory."""
    plants = db.get_plants()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)

    # Header
    writer.writerow([
        "CLAVE",
        "ALIAS_AKA",
        "ESPECIE",
        "ESTADO_SANITARIO",
        "UBICACION",
        "FECHA_REGISTRO",
        "PADRES_LINAJE",
        "FECHA_SIEMBRA_ESQUEJE",
        "INJERTO",
        "ULTIMA_PODA",
        "ULTIMO_TRASPLANTE",
        "FERTILIZANTE_TRATAMIENTOS",
        "CANTIDAD_FOTOS",
        "COMENTARIOS_CLINICOS"
    ])

    for p in plants:
        writer.writerow([
            p.get("name", ""),
            p.get("aka", ""),
            p.get("species", ""),
            p.get("status", ""),
            p.get("location", ""),
            p.get("registration_date", ""),
            p.get("padres", ""),
            p.get("sowing_cutting_date", ""),
            p.get("graft", ""),
            p.get("last_pruned", ""),
            p.get("last_repotted", ""),
            p.get("fertilizante", ""),
            len(p.get("photos", [])),
            p.get("comentarios", "")
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="inventario_plantation.csv"'
        }
    )


# ==============================================================================
# PDF DOSSIER GENERATION (ON-DEMAND ONLY)
# ==============================================================================

@router.get("/pdf/plant/{name}")
def download_single_plant_pdf(name: str):
    """
    On-demand single plant PDF dossier generator.
    Creates PDF-1.4 printable document using WeasyPrint only when downloaded.
    """
    plant = db.get_plant(name)
    if not plant:
        raise HTTPException(status_code=404, detail="Ejemplar botánico no encontrado.")

    pdf_bytes = generate_single_plant_pdf(plant)
    filename = f"Plantation_Dossier_{plant.get('name')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/pdf/full-catalog")
def download_full_catalog_pdf():
    """
    On-demand general catalog dossier generator.
    Creates complete PDF-1.4 dossier with index summary and all plant cards only when downloaded.
    """
    plants = db.get_plants()
    pdf_bytes = generate_catalog_pdf(plants, title="CATÁLOGO GENERAL DE EJEMPLARES")
    filename = "Plantation_Dossier_General.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/images/{filename}")
def serve_image(filename: str):
    """
    Explicitly serves plant images with proper image/* media type and caching headers,
    preventing application/octet-stream fallback so all browsers display images.
    """
    safe_name = os.path.basename(filename)
    path = os.path.join(IMAGES_DIR, safe_name)
    if not os.path.exists(path) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    ext = os.path.splitext(safe_name)[1].lower()
    media_map = {
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".svg": "image/svg+xml"
    }
    media_type = media_map.get(ext, "image/jpeg")
    return FileResponse(
        path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        }
    )


@router.get("/modal/close", response_class=HTMLResponse)
def close_modal():
    """Clears modal drawer."""
    return HTMLResponse("")


@router.get("/plants/{name}/dossier", response_class=HTMLResponse)
def view_printable_dossier(name: str):
    """
    Renders a dedicated, printable botanical technical dossier.
    Optimized for browser printing and PDF generation with print CSS rules.
    """
    plant = db.get_plant(name)
    if not plant:
        raise HTTPException(status_code=404, detail="Ejemplar botánico no encontrado")

    status = plant.get("status", "Ok")
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-Ok")
    status_es = STATUS_SPANISH.get(status, status)
    photos = plant.get("photos", [])
    age_short, age_detailed = db.calculate_plant_age(plant.get("sowing_cutting_date"), plant.get("graft", ""))

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

    html = f'''<!DOCTYPE html>
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
                {f'<span>ALIAS / AKA: <strong style="color: var(--peach-orange);">"{plant.get("aka")}"</strong></span>' if plant.get("aka") else ''}
            </div>
        </div>

        <div class="dossier-section-title">DATOS & REGISTRO </div>
        <table class="dossier-table">
            <tbody>
                <tr>
                    <th>ALIAS / NOMBRE ESPECIAL (AKA)</th>
                    <td><strong>{plant.get('aka') or '—'}</strong></td>
                </tr>
                <tr>
                    <th>FECHA DE REGISTRO</th>
                    <td>{plant.get('registration_date') or '—'}</td>
                </tr>
                <tr>
                    <th>EDAD </th>
                    <td><strong>{age_detailed}</strong> </td>
                </tr>
                <tr>
                    <th>FECHA SIEMBRA/ESQUEJADO</th>
                    <td>{plant.get('sowing_cutting_date') or '—'}</td>
                </tr>
                <tr>
                    <th>LINAJE(PADRES)</th>
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
            <button type="button" class="btn btn-primary" onclick="window.print()">
                🖨 [IMPRIMIR EXPEDIENTE]
            </button>
            <a href="/pdf/plant/{plant.get('name')}" class="btn btn-red" target="_blank">
                🗎 [DESCARGAR PDF GENERADO]
            </a>
            <button type="button" class="btn" onclick="window.close(); if(!window.closed) window.location.href='/';">
                ✕ [CERRAR]
            </button>
        </div>
    </div>
</body>
</html>'''
    return HTMLResponse(html)

