"""
Plantation - Modular UI Components
Contains reusable cards, thumbnails, grid wrappers, and statistics ribbons.
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import db

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


def render_photo_item_html(plant_name: str, ph: str) -> str:
    """Renders a photo card in the technical dossier with confirmation before deletion."""
    return f"""
        <div class="modal-photo-item">
            <button type="button"
                    class="photo-delete-badge"
                    hx-delete="/plants/{plant_name}/photos/{ph}"
                    hx-target="#plant-photos-wrapper"
                    hx-swap="innerHTML"
                    hx-confirm="¿Está seguro de eliminar de forma permanente la fotografía '{ph}' del ejemplar {plant_name}?"
                    onclick="event.stopPropagation();"
                    title="Eliminar foto del ejemplar">✕</button>
            <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" title="Abrir fotografía en nueva pestaña (alta resolución)">
                <img class="modal-photo-thumb" src="/images/{ph}" alt="{ph}" />
            </a>
            <div style="font-size: 10px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="{ph}">
                <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">{ph}</a>
            </div>
            <button type="button"
                    class="photo-delete-btn"
                    hx-delete="/plants/{plant_name}/photos/{ph}"
                    hx-target="#plant-photos-wrapper"
                    hx-swap="innerHTML"
                    hx-confirm="¿Está seguro de eliminar de forma permanente la fotografía '{ph}' del ejemplar {plant_name}?"
                    onclick="event.stopPropagation();"
                    title="Eliminar foto permanentemente">
                🗑 [ELIMINAR]
            </button>
        </div>
    """


def render_card_html(p: Dict[str, Any]) -> str:
    """Renders a single plant card with bounded headers, concise Alias badge, and thumbnail preview."""
    status = db.normalize_status(p.get("status"))
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-OK")
    status_es = STATUS_SPANISH.get(status, status)

    photos = p.get("photos", [])
    if photos and len(photos) > 0:
        first_img = photos[0]
        thumb_img = f"""
            <div class="card-thumbnail-box plant-thumb-wrapper">
                <img class="card-thumbnail-img plant-thumb"
                     src="/images/{first_img}"
                     alt="{p.get('name')}"
                     loading="lazy"
                     onerror="this.style.display='none'; this.nextElementSibling.style.display='flex';" />
                <div class="card-thumbnail-placeholder" style="display: none;">
                    <div class="placeholder-icon">🌱</div>
                    <div class="placeholder-text">IMAGEN NO DISPONIBLE</div>
                </div>
                <span class="thumbnail-badge-count photo-count-pill">{len(photos)} FOTO{'S' if len(photos) > 1 else ''}</span>
            </div>
        """
    else:
        thumb_img = f"""
            <div class="card-thumbnail-box plant-thumb-wrapper no-photo">
                <div class="card-thumbnail-placeholder">
                    <div class="placeholder-icon">🌱</div>
                    <div class="placeholder-text">SIN FOTOGRAFÍA</div>
                    <div class="placeholder-sub">CLAVE: {p.get('name')}</div>
                </div>
            </div>
        """

    age_short, _ = db.calculate_plant_age(p.get("sowing_cutting_date"), p.get("graft", ""))

    aka = (p.get("aka") or "").strip()
    aka_html = f'<span class="plant-aka" title=\'Alias: "{aka}"\'>"{aka}"</span>' if aka else ""

    return f"""
    <div class="plant-card" id="plant-card-{p.get('name')}">
        <div class="card-head">
            <div class="card-head-left">
                <span class="plant-key" title="Clave de ejemplar">{p.get('name')}</span>
                <span class="status-badge {status_cls}">● {status_es}</span>
                {aka_html}
            </div>
        </div>

        {thumb_img}

        <div class="plant-species" title="{p.get('species')}">{p.get('species')}</div>

        <div class="plant-meta">
            <div>
                <span class="meta-label">EDAD:</span>
                <span class="meta-val age-highlight">{age_short}</span>
            </div>
            <div>
                <span class="meta-label">UBI:</span>
                <span class="meta-val">{p.get('location') or '—'}</span>
            </div>
            <div>
                <span class="meta-label">INJERTO:</span>
                <span class="meta-val">{p.get('graft') or 'Raíz propia'}</span>
            </div>
            <div>
                <span class="meta-label">ALTURA:</span>
                <span class="meta-val" style="color: var(--green-sage);">{p.get('height') or '—'}</span>
            </div>
        </div>

        <div class="card-actions">
            <button class="btn btn-sm"
                    hx-get="/plants/{p.get('name')}"
                    hx-target="#modal-container"
                    hx-swap="innerHTML"
                    title="Ver expediente técnico">
                [EXPEDIENTE]
            </button>
        </div>
    </div>
    """


PAGE_SIZE = 4


def build_plants_scroll_qs(
    page: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None,
    height: Optional[str] = None,
) -> str:
    """Builds query string preserving active filters for infinite scroll page requests."""
    parts = [f"page={page}"]
    if search and search.strip():
        parts.append(f"search={quote_plus(search.strip())}")
    if status and status.strip() not in ("ALL", "", "*"):
        parts.append(f"status={quote_plus(status.strip())}")
    if age and age.strip() not in ("ALL", "", "*"):
        parts.append(f"age={quote_plus(age.strip())}")
    if height and height.strip() not in ("ALL", "", "*", "todas", "todos"):
        parts.append(f"height={quote_plus(height.strip())}")
    return "&".join(parts)


def render_infinite_scroll_trigger(
    next_page: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None,
    height: Optional[str] = None,
) -> str:
    """Renders the revealed HTMX sentinel that requests the next page of cards upon scrolling."""
    qs = build_plants_scroll_qs(next_page, search, status, age, height)
    return f"""
    <div class="infinite-scroll-trigger"
         id="infinite-scroll-trigger"
         hx-get="/plants?{qs}"
         hx-trigger="revealed"
         hx-swap="outerHTML"
         style="grid-column: 1 / -1; width: 100%;">
        <div class="scroll-loader" style="display: flex; align-items: center; justify-content: center; gap: 8px; padding: 20px 0; color: var(--text-dim); font-size: 11.5px; letter-spacing: 0.5px;">
            <span class="cursor-blink" style="color: var(--blue-sky);">▋</span>
            <span>CARGANDO MÁS EJEMPLARES...</span>
        </div>
    </div>
    """


def render_infinite_scroll_end(total_count: int) -> str:
    """Renders a clean footer note when all cards in collection/filter have been loaded."""
    return f"""
    <div class="infinite-scroll-end" style="grid-column: 1 / -1; text-align: center; padding: 20px 0 10px 0; color: var(--text-dim); font-size: 11px; letter-spacing: 0.8px;">
        ── TODOS LOS EJEMPLARES CARGADOS ({total_count}) ──
    </div>
    """


def render_plants_grid(
    plants: List[Dict[str, Any]],
    page: int = 1,
    page_size: int = PAGE_SIZE,
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None,
    height: Optional[str] = None,
) -> str:
    """Renders page 1 of plants cards grid with lazy-load infinite scroll trigger for subsequent cards."""
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
    total = len(plants)
    page_plants = plants[:page_size]
    cards = [render_card_html(p) for p in page_plants]

    sentinel_html = ""
    if total > page_size:
        sentinel_html = render_infinite_scroll_trigger(2, search, status, age, height)
    elif total > 0:
        sentinel_html = render_infinite_scroll_end(total)

    return f"""<div class="plants-grid" id="plants-grid">{''.join(cards)}{sentinel_html}</div>"""


def render_plants_page(
    plants: List[Dict[str, Any]],
    page: int,
    page_size: int = PAGE_SIZE,
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None,
    height: Optional[str] = None,
) -> str:
    """Renders subsequent batch of cards for infinite scroll (swapped via outerHTML)."""
    total = len(plants)
    start = (page - 1) * page_size
    end = start + page_size
    page_plants = plants[start:end]

    cards = [render_card_html(p) for p in page_plants]

    if total > end:
        sentinel = render_infinite_scroll_trigger(page + 1, search, status, age, height)
    else:
        sentinel = render_infinite_scroll_end(total)

    return "".join(cards) + sentinel


def render_stats_bar() -> str:
    """Renders catalog stats counters with 2-state health and alias count."""
    stats = db.get_stats()
    sc = stats.get("status_counts", {})
    ok_count = sc.get('OK', 0)
    not_ok_count = sc.get('notOK', 0)
    with_alias = stats.get("with_alias", 0)

    return f"""
    <div class="stats-summary" id="stats-bar">
        <div>
            TOTAL EJEMPLARES: <span class="stats-count-tag">{stats.get('total', 0)}</span> |
            FOTOS EN DISCO: <span style="color: var(--blue-sky); font-weight: bold;">{stats.get('total_photos', 0)}</span> |
            UBICACIONES: <span style="color: var(--text-main); font-weight: bold;">{stats.get('locations_count', 0)}</span> |
            CON ALIAS: <span style="color: var(--peach-orange); font-weight: bold;">{with_alias}</span>
        </div>
        <div style="display: flex; gap: 14px; font-size: 11.5px; font-weight: 600;">
            <span style="color: var(--green-sage);">● OK: {ok_count}</span>
            <span style="color: #ef4444; font-weight: bold;">● notOK: {not_ok_count}</span>
        </div>
    </div>
    """
