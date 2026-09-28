"""
Plantation - Application Shell & Main Layout Template
"""

from typing import List, Dict, Any
from .components import render_plants_grid, render_stats_bar


def render_index_html(plants: List[Dict[str, Any]]) -> str:
    """Renders the main page HTML layout."""
    stats_bar_html = render_stats_bar()
    grid_html = render_plants_grid(plants)

    return f"""<!DOCTYPE html>
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
                            <span class="theme-desc">藍染 Aizome · Índigo & cielo</span>
                        </span>
                        <span class="theme-check">✓</span>
                    </button>
                    <button type="button" class="theme-option-btn" data-theme-name="catpuchin" onclick="selectTheme('catpuchin')">
                        <span class="theme-swatch" style="background: #181926; border-color: #ed8796;">
                            <span class="theme-swatch-dot" style="background: #ed8796; box-shadow: 0 0 6px #ed8796;"></span>
                        </span>
                        <span class="theme-info">
                            <span class="theme-name">Catppuccin</span>
                            <span class="theme-desc">Mocha & Carmesí original</span>
                        </span>
                        <span class="theme-check">✓</span>
                    </button>
                    <button type="button" class="theme-option-btn" data-theme-name="golden" onclick="selectTheme('golden')">
                        <span class="theme-swatch" style="background: #17130e; border-color: #f1b343;">
                            <span class="theme-swatch-dot" style="background: #f1b343; box-shadow: 0 0 6px #f1b343;"></span>
                        </span>
                        <span class="theme-info">
                            <span class="theme-name">Golden</span>
                            <span class="theme-desc">Kintsugi · Oro & ámbar</span>
                        </span>
                        <span class="theme-check">✓</span>
                    </button>
                    <button type="button" class="theme-option-btn" data-theme-name="darkerthanblack" onclick="selectTheme('darkerthanblack')">
                        <span class="theme-swatch" style="background: #000000; border-color: #ff334b;">
                            <span class="theme-swatch-dot" style="background: #ff334b; box-shadow: 0 0 6px #ff334b;"></span>
                        </span>
                        <span class="theme-info">
                            <span class="theme-name">Darker Than Black</span>
                            <span class="theme-desc">OLED Noir · Negro & neón</span>
                        </span>
                        <span class="theme-check">✓</span>
                    </button>
                </div>
            </div>
        </div>
    </header>

    <div id="admin-container"></div>

    <main class="app-layout">
        <div class="control-toolbar">
            <div class="search-line">
                <span class="input-prompt">Buscar&gt;</span>
                <input type="text"
                       id="search-input"
                       class="search-input"
                       placeholder="..."
                       oninput="onSearchFilterInput(this.value)"
                       autocomplete="off" />
                <span id="search-spinner" class="htmx-indicator" style="color: var(--red-crimson); font-size: 11px;">[BUSCANDO...]</span>
            </div>

            <input type="hidden" id="current-status-filter" value="ALL" />
            <input type="hidden" id="current-age-filter" value="ALL" />
            <input type="hidden" id="current-height-filter" value="ALL" />

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

                <div style="display: inline-block; width: 1px; height: 18px; background: var(--border-dim); margin: 0 4px;"></div>

                <div style="display: flex; align-items: center; gap: 6px; flex-wrap: wrap;">
                    <span class="filter-label">ALTURA:</span>
                    <button type="button"
                            class="status-pill height-filter-btn active"
                            onclick="applyPlantFilter('height', 'ALL', this)">
                        TODAS
                    </button>
                    <button type="button"
                            class="status-pill status-pill-height height-filter-btn"
                            onclick="applyPlantFilter('height', 'less_15', this)">
                        &lt; 15 cm
                    </button>
                    <button type="button"
                            class="status-pill status-pill-height height-filter-btn"
                            onclick="applyPlantFilter('height', '15_to_35', this)">
                        15 - 35 cm
                    </button>
                    <button type="button"
                            class="status-pill status-pill-height height-filter-btn"
                            onclick="applyPlantFilter('height', '35_plus', this)">
                        35+ cm
                    </button>
                </div>
            </div>
        </div>

        {stats_bar_html}

        <div id="plant-container">
            {grid_html}
        </div>
    </main>

    <div id="modal-container"></div>

    <footer class="cli-footer">
        <div>
            PLANTATION -- <code style="color: var(--red-crimson);">DB-plantation</code>
        </div>
        <div>
            HTMX 
        </div>
    </footer>

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
            var heightVal = document.getElementById('current-height-filter') ? document.getElementById('current-height-filter').value : 'ALL';

            var params = new URLSearchParams();
            if (search) params.set('search', search);
            if (statusVal && statusVal !== 'ALL') params.set('status', statusVal);
            if (ageVal && ageVal !== 'ALL') params.set('age', ageVal);
            if (heightVal && heightVal !== 'ALL') params.set('height', heightVal);

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
            }} else if (type === 'height') {{
                var el = document.getElementById('current-height-filter');
                if (el) el.value = value;
                document.querySelectorAll('.height-filter-btn').forEach(function(b) {{
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
</html>"""
