"""
Plantation - Application Shell & Main Layout Template
"""

from typing import List, Dict, Any
from .components import render_plants_grid


THEMES = [
    {"id": "japanese indigo", "icon": "🌊", "name": "Indigo", "desc": "藍染 Aizome · Índigo & cielo", "bg": "#0b1120", "accent": "#38bdf8"},
    {"id": "golden", "icon": "🏺", "name": "Golden", "desc": "Kintsugi · Oro & ámbar", "bg": "#17130e", "accent": "#f1b343"},
    {"id": "darkerthanblack", "icon": "🌑", "name": "Black", "desc": "OLED Noir · Negro & neón", "bg": "#000000", "accent": "#ff334b"},
    {"id": "unicorn", "icon": "🦄", "name": "Unicorn", "desc": "Pastel Synthwave · Lavanda, turquesa & neón", "bg": "#131124", "accent": "#ff66cc"},
]


def render_index_html(plants: List[Dict[str, Any]]) -> str:
    """Renders the main page HTML layout."""
    grid_html = render_plants_grid(plants)

    theme_buttons = "\n".join(
        f"""<button type="button" class="theme-option-btn" data-theme-name="{t['id']}" onclick="selectTheme('{t['id']}')">
            <span class="theme-swatch" style="background: {t['bg']}; border-color: {t['accent']};">
                <span class="theme-swatch-dot" style="background: {t['accent']}; box-shadow: 0 0 6px {t['accent']};"></span>
            </span>
            <span class="theme-info">
                <span class="theme-name">{t['icon']} {t['name']}</span>
                <span class="theme-desc">{t['desc']}</span>
            </span>
            <span class="theme-check">✓</span>
        </button>"""
        for t in THEMES
    )

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Plantation - Registro Botánico & Dossier PDF</title>
    <meta name="description" content="Gestor botánico y dossiers técnicos con SQLite, HTMX y exportación PDF." />
    <link rel="stylesheet" href="/static/style.css?v=20260930_4" />
    <script src="/static/htmx.min.js"></script>
    <script>
        (function() {{
            try {{
                var t = localStorage.getItem('plantation_theme') || 'japanese indigo';
                if (['catpuchin', 'catppuccin', 'green olive', 'green-olive', 'adenium power', 'adenium-power'].indexOf(t.toLowerCase()) !== -1) {{
                    t = 'japanese indigo';
                }}
                document.documentElement.setAttribute('data-theme', t);
            }} catch(e) {{}}
        }})();

        function updateHeaderOffset() {{
            var h = document.querySelector('.cli-header');
            if (h) {{
                document.documentElement.style.setProperty('--header-height', h.offsetHeight + 'px');
            }}
        }}
        window.addEventListener('resize', updateHeaderOffset);
        document.addEventListener('DOMContentLoaded', updateHeaderOffset);

        function autoFormatHeightInput(el) {{
            if (!el) return;
            var raw = el.value.trim();
            if (!raw) return;
            var today = new Date().toISOString().slice(0, 10);
            var fullMatch = raw.match(/^([\d.,]+)\s*(?:cm)?\s*\(\s*(\d{4}-\d{2}-\d{2})\s*\)$/i);
            if (fullMatch) {{
                var n = fullMatch[1].replace(',', '.');
                el.value = n + ' cm (' + fullMatch[2] + ')';
                return;
            }}
            var legMatch = raw.match(/^(\d{4}-\d{2}-\d{2})\s*-\s*([\d.,]+)\s*(?:cm)?$/i);
            if (legMatch) {{
                var n = legMatch[2].replace(',', '.');
                el.value = n + ' cm (' + legMatch[1] + ')';
                return;
            }}
            var numMatch = raw.match(/(\d+(?:[.,]\d+)?)/);
            if (numMatch) {{
                var n = numMatch[1].replace(',', '.');
                el.value = n + ' cm (' + today + ')';
            }} else {{
                el.value = raw + ' (' + today + ')';
            }}
        }}

        function setCareFieldToday(inputId) {{
            var el = document.getElementById(inputId);
            if (!el) return;
            var today = new Date().toISOString().slice(0, 10);
            var raw = el.value.trim();
            if (!raw) {{
                el.value = today;
            }} else {{
                var match = raw.match(/^(\d{4}-\d{2}-\d{2})?\s*(?:[-/(]\s*(.*?)\s*[)]?)?$/);
                if (match && match[2]) {{
                    el.value = today + ' (' + match[2] + ')';
                }} else if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) {{
                    el.value = today;
                }} else {{
                    el.value = today + ' (' + raw + ')';
                }}
            }}
            el.focus();
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
        }}

        function autoEnsureCareDate(el) {{
            if (!el) return;
            var raw = el.value.trim();
            if (!raw) return;
            var today = new Date().toISOString().slice(0, 10);
            var dateMatch = raw.match(/^\d{4}-\d{2}-\d{2}/);
            if (!dateMatch) {{
                el.value = today + ' (' + raw + ')';
            }}
        }}

        function updateCombinedPadres() {{
            var p1 = document.getElementById('inp-padre1');
            var p2 = document.getElementById('inp-padre2');
            var target = document.getElementById('inp-padres');
            var preview = document.getElementById('padres-preview-text');
            if (!p1 || !p2 || !target || !preview) return;

            var v1 = (p1.value || '').trim();
            var v2 = (p2.value || '').trim();

            var isUnk1 = (!v1) || (v1.toLowerCase() === 'unknown') || (v1.toLowerCase() === 'desconocido');
            var isUnk2 = (!v2) || (v2.toLowerCase() === 'unknown') || (v2.toLowerCase() === 'desconocido');

            var combined = '';
            if (isUnk1 && isUnk2) {{
                combined = 'unknown';
            }} else {{
                var part1 = isUnk1 ? 'unknown' : v1;
                var part2 = isUnk2 ? 'unknown' : v2;
                combined = part1 + ' × ' + part2;
            }}

            target.value = combined;
            preview.textContent = combined;
        }}

        function clearSingleParent(num) {{
            var inp = document.getElementById('inp-padre' + num);
            var feedback = document.getElementById('padre' + num + '-validation-feedback');
            if (inp) {{
                inp.value = '';
                inp.style.borderColor = 'var(--border-dim)';
            }}
            if (feedback) {{
                feedback.innerHTML = '<span style="color: var(--text-dim); font-size: 11px;">✓ Sin parental seleccionado (default: "unknown")</span>';
            }}
            var btn1 = document.getElementById('new-plant-submit-btn');
            var btn2 = document.getElementById('edit-plant-submit-btn');
            if (btn1) btn1.disabled = false;
            if (btn2) btn2.disabled = false;
            updateCombinedPadres();
        }}

        function clearParentsInputs() {{
            clearSingleParent(1);
            clearSingleParent(2);
        }}
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
                    id="new-plant-btn"
                    hx-get="/plants/modal/new"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    title="Nuevo Ejemplar"
                    aria-label="Nuevo Ejemplar">
                <span style="font-size: 16px; font-weight: bold; line-height: 1; display: inline-flex; align-items: center; justify-content: center;">+</span>
            </button>
            <div id="admin-nav-slot">
                <button class="btn"
                        id="admin-nav-btn"
                        hx-get="/admin/toggle"
                        hx-vals='js:{{is_open: document.getElementById("admin-panel") !== null}}'
                        hx-target="#admin-container"
                        hx-swap="innerHTML"
                        title="Administración"
                        aria-label="Administración">
                    <span style="font-size: 15px; line-height: 1; display: inline-flex; align-items: center; justify-content: center;">⚙</span>
                </button>
            </div>
            <button class="btn"
                    id="stats-nav-btn"
                    hx-get="/stats/modal"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    title="Estadísticas y Analítica Botánica"
                    aria-label="Estadísticas">
                <span style="font-size: 12px; font-weight: 700; line-height: 1; display: inline-flex; align-items: center; gap: 4px;">📊 STATS</span>
            </button>
            <div class="theme-dropdown-container" id="theme-switcher-container">
                <button type="button"
                        class="btn"
                        id="theme-toggle-btn"
                        onclick="toggleThemeDropdown(event)"
                        aria-haspopup="true"
                        aria-expanded="false"
                        title="Esquema de color">
                    <span id="theme-btn-icon" style="font-size: 15px; display: inline-flex; align-items: center; justify-content: center; line-height: 1;">🌊</span>
                </button>
                <div id="theme-dropdown-menu" class="theme-dropdown-menu" style="display: none;">
                    <div class="theme-dropdown-header">ESQUEMA DE COLOR // PALETA</div>
                    {theme_buttons}
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

            <div class="filter-bar">
                <div class="filter-group">
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

                <div class="filter-divider"></div>

                <div class="filter-group">
                    <span class="filter-label">EDAD (años):</span>
                    <button type="button"
                            class="status-pill age-filter-btn active"
                            onclick="applyPlantFilter('age', 'ALL', this)">
                        TODAS
                    </button>
                    <button type="button"
                            class="status-pill status-pill-age age-filter-btn"
                            onclick="applyPlantFilter('age', 'less_1', this)">
                        &lt; 1 
                    </button>
                    <button type="button"
                            class="status-pill status-pill-age age-filter-btn"
                            onclick="applyPlantFilter('age', '1_to_2', this)">
                        1 - 2 
                    </button>
                    <button type="button"
                            class="status-pill status-pill-age age-filter-btn"
                            onclick="applyPlantFilter('age', '2_to_3', this)">
                        2 - 3 
                    </button>
                    <button type="button"
                            class="status-pill status-pill-age age-filter-btn"
                            onclick="applyPlantFilter('age', '3_plus', this)">
                        3+ 
                    </button>
                    <button type="button"
                            class="status-pill status-pill-age age-filter-btn"
                            onclick="applyPlantFilter('age', 'sd', this)"
                            title="Ejemplares sin fecha registrada de siembra o esquejado">
                        S/D
                    </button>
                </div>

                <div class="filter-divider"></div>

                <div class="filter-group">
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
                    <button type="button"
                            class="status-pill status-pill-height height-filter-btn"
                            onclick="applyPlantFilter('height', 'sd', this)"
                            title="Ejemplares sin medición de altura registrada">
                        S/D
                    </button>
                </div>
            </div>
        </div>

        <div id="plant-container">
            {grid_html}
        </div>
    </main>

    <div id="modal-container"></div>

    <!-- In-App Confirmation Modal (Safe for iframes, no window.confirm blocker) -->
    <div id="app-confirm-modal" class="modal-overlay" style="display: none; z-index: 100050;">
        <div class="modal-dialog" style="max-width: 440px; border-color: #ef4444; box-shadow: 0 10px 40px rgba(0,0,0,0.85);">
            <div class="modal-header" style="border-bottom-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.1);">
                <div style="display: flex; align-items: center; gap: 8px; font-weight: bold; color: #ef4444; font-size: 13px;">
                    <span>⚠️</span>
                    <span>CONFIRMACIÓN REQUERIDA</span>
                </div>
                <button type="button" class="modal-close-btn" onclick="closeAppConfirmModal()" title="Cancelar acción">✕</button>
            </div>
            <div class="modal-body" style="padding: 18px 20px; font-size: 13px; color: var(--text-main); line-height: 1.5;">
                <p id="app-confirm-text" style="margin: 0 0 16px 0; word-break: break-word;"></p>
                <div style="display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px;">
                    <button type="button" class="btn" onclick="closeAppConfirmModal()">
                        CANCELAR
                    </button>
                    <button type="button" class="btn btn-red" id="app-confirm-btn" style="background-color: #ef4444; border-color: #ef4444; color: #fff;">
                        SÍ, CONFIRMAR
                    </button>
                </div>
            </div>
        </div>
    </div>

    <footer class="cli-footer">
        <div>
            PLANTATION -- <code style="color: var(--red-crimson);">DB-plantation</code>
        </div>
        <div>
            HTMX 
        </div>
    </footer>

    <script>
        var THEMES = {{
            'japanese indigo': {{ icon: '🌊', name: 'Japanese Indigo' }},
            'golden': {{ icon: '🏺', name: 'Golden' }},
            'darkerthanblack': {{ icon: '🌑', name: 'Darker Than Black' }},
            'unicorn': {{ icon: '🦄', name: 'Unicorn' }},
            'unicorn lover pro max': {{ icon: '🦄', name: 'Unicorn' }}
        }};

        function selectTheme(themeName) {{
            try {{
                localStorage.setItem('plantation_theme', themeName);
            }} catch(e) {{}}
            applyTheme(themeName);
            closeThemeDropdown();
        }}

        function applyTheme(themeName) {{
            var key = (themeName || '').toLowerCase().replace(/-/g, ' ');
            if (['catpuchin', 'catppuccin', 'green olive', 'adenium power'].indexOf(key) !== -1 || !THEMES[key]) {{
                key = 'japanese indigo';
            }}
            document.documentElement.setAttribute('data-theme', key);
            var cfg = THEMES[key] || {{ icon: '🌊', name: 'Japanese Indigo' }};
            var iconEl = document.getElementById('theme-btn-icon');
            var btnEl = document.getElementById('theme-toggle-btn');
            if (iconEl) iconEl.textContent = cfg.icon;
            if (btnEl) {{
                btnEl.setAttribute('title', 'Esquema de color: ' + cfg.name);
                btnEl.setAttribute('aria-label', 'Esquema de color: ' + cfg.name);
            }}
            document.querySelectorAll('.theme-option-btn').forEach(function(btn) {{
                var t = (btn.getAttribute('data-theme-name') || '').toLowerCase().replace(/-/g, ' ');
                btn.classList.toggle('active', t === key);
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
            var saved = 'japanese indigo';
            try {{
                saved = localStorage.getItem('plantation_theme') || 'japanese indigo';
                if (['catpuchin', 'catppuccin', 'green olive', 'adenium power'].indexOf(saved.toLowerCase()) !== -1) {{
                    saved = 'japanese indigo';
                    localStorage.setItem('plantation_theme', saved);
                }}
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

        var _appConfirmCallback = null;

        function showAppConfirmModal(message, onConfirm) {{
            _appConfirmCallback = onConfirm;
            var modal = document.getElementById('app-confirm-modal');
            var textEl = document.getElementById('app-confirm-text');
            var okBtn = document.getElementById('app-confirm-btn');
            if (!modal || !textEl || !okBtn) {{
                if (onConfirm) onConfirm();
                return;
            }}
            textEl.textContent = message;
            modal.style.display = 'flex';
            okBtn.focus();
        }}

        function closeAppConfirmModal() {{
            var modal = document.getElementById('app-confirm-modal');
            if (modal) modal.style.display = 'none';
            _appConfirmCallback = null;
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            var okBtn = document.getElementById('app-confirm-btn');
            if (okBtn) {{
                okBtn.addEventListener('click', function(e) {{
                    e.stopPropagation();
                    var cb = _appConfirmCallback;
                    closeAppConfirmModal();
                    if (cb) cb();
                }});
            }}

            var modal = document.getElementById('app-confirm-modal');
            if (modal) {{
                modal.addEventListener('click', function(e) {{
                    if (e.target === modal) {{
                        closeAppConfirmModal();
                    }}
                }});
            }}
        }});

        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Escape') {{
                var confirmModal = document.getElementById('app-confirm-modal');
                if (confirmModal && confirmModal.style.display !== 'none') {{
                    closeAppConfirmModal();
                    return;
                }}
                var mc = document.getElementById('modal-container');
                if (mc && mc.children.length > 0) {{
                    var editModal = document.getElementById('edit-plant-modal');
                    if (editModal) {{
                        var keyEl = editModal.querySelector('.plant-key');
                        var k = keyEl ? keyEl.textContent.trim() : '';
                        if (k) {{
                            htmx.ajax('GET', '/plants/' + encodeURIComponent(k), {{ target: '#modal-container', swap: 'innerHTML' }});
                            return;
                        }}
                    }}
                    mc.innerHTML = '';
                }}
            }}
        }});

        // Close modals when clicking directly on overlay backdrop
        document.addEventListener('click', function(e) {{
            if (e.target && e.target.classList && e.target.classList.contains('modal-overlay')) {{
                if (e.target.id === 'app-confirm-modal') {{
                    closeAppConfirmModal();
                    return;
                }}
                if (e.target.id === 'edit-plant-modal') {{
                    var keyEl = e.target.querySelector('.plant-key');
                    var k = keyEl ? keyEl.textContent.trim() : '';
                    if (k) {{
                        htmx.ajax('GET', '/plants/' + encodeURIComponent(k), {{ target: '#modal-container', swap: 'innerHTML' }});
                        return;
                    }}
                }}
                var mc = document.getElementById('modal-container');
                if (mc) mc.innerHTML = '';
            }}
        }});

        // Intercept all HTMX requests requiring confirmation
        document.addEventListener('htmx:confirm', function(evt) {{
            if (evt.detail && evt.detail.question) {{
                evt.preventDefault();
                showAppConfirmModal(evt.detail.question, function() {{
                    evt.detail.issueRequest(true);
                }});
            }}
        }});

        // Plant card keyboard accessibility (Enter/Space opens dossier)
        document.addEventListener('keydown', function(e) {{
            if (e.key === 'Enter' || e.key === ' ') {{
                var card = e.target.closest && e.target.closest('.plant-card');
                if (card && e.target === card) {{
                    e.preventDefault();
                    card.click();
                }}
            }}
        }});

        // Global delegated image error handler for plant thumbnails
        document.addEventListener('error', function(e) {{
            if (e.target && e.target.classList && e.target.classList.contains('card-thumbnail-img')) {{
                e.target.style.display = 'none';
                var placeholder = e.target.nextElementSibling;
                if (placeholder && placeholder.classList.contains('card-thumbnail-placeholder')) {{
                    placeholder.style.display = 'flex';
                }}
            }}
        }}, true);
    </script>
</body>
</html>"""
