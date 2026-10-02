"""
Plantation - Modular UI Components
Contains reusable cards, thumbnails, grid wrappers, and statistics ribbons.
"""

import html
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
import db

STATUS_BADGE_CLASSES = {"OK": "status-OK", "notOK": "status-notOK"}
STATUS_SPANISH = {"OK": "OK", "notOK": "notOK"}


def render_photo_item_html(plant_name: str, ph: str, allow_delete: bool = False, target_wrapper: str = "#edit-plant-photos-wrapper") -> str:
    """Renders a photo card in dossier (read-only) or simple preview."""
    delete_btn = f"""
        <button type="button"
                class="photo-delete-badge"
                hx-delete="/plants/{plant_name}/photos/{ph}?source=edit"
                hx-target="{target_wrapper}"
                hx-swap="innerHTML"
                onclick="event.stopPropagation();"
                title="Eliminar foto del ejemplar">✕</button>
    """ if allow_delete else ""

    return f"""
        <div class="modal-photo-item">
            {delete_btn}
            <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" title="Abrir fotografía en nueva pestaña (alta resolución)">
                <img class="modal-photo-thumb" src="/images/{ph}" alt="{ph}" />
            </a>
            <div style="font-size: 10px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="{ph}">
                <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">{ph}</a>
            </div>
        </div>
    """


def render_editable_photo_item_html(plant_name: str, ph: str, idx: int) -> str:
    """Renders a photo card in edit modal with staged deletion and instant undo (no confirmation dialog)."""
    return f"""
        <div class="modal-photo-item" id="existing-photo-card-{idx}" style="position: relative; transition: all 0.2s ease;">
            <button type="button"
                    class="photo-delete-badge"
                    id="del-btn-{idx}"
                    onclick="markPhotoForDeletion('{ph}', {idx});"
                    title="Marcar fotografía para eliminar (se aplicará al guardar)">✕</button>
            <div id="undo-container-{idx}" style="display: none; position: absolute; top: 4px; right: 4px; z-index: 5;">
                <button type="button"
                        onclick="unmarkPhotoForDeletion('{ph}', {idx});"
                        class="btn btn-sm"
                        style="padding: 2px 6px; font-size: 10px; background: var(--bg-surface); border: 1px solid var(--accent); color: var(--accent); font-weight: 700; cursor: pointer; border-radius: 3px;"
                        title="Deshacer eliminación">↶ Deshacer</button>
            </div>
            <div id="deletion-badge-{idx}" style="display: none; position: absolute; bottom: 18px; left: 4px; right: 4px; background: rgba(180, 40, 40, 0.95); color: #fff; font-size: 8.5px; font-weight: 700; text-align: center; padding: 2px 4px; border-radius: 2px; text-transform: uppercase; z-index: 4; pointer-events: none;">
                🗑 Eliminación pendiente
            </div>
            <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" title="Abrir fotografía en nueva pestaña (alta resolución)">
                <img class="modal-photo-thumb" id="photo-thumb-{idx}" src="/images/{ph}" alt="{ph}" style="transition: opacity 0.2s;" />
            </a>
            <div style="font-size: 10px; color: var(--text-dim); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px;" title="{ph}">
                <a href="/images/{ph}" target="_blank" rel="noopener noreferrer" style="color: inherit; text-decoration: none;">{ph}</a>
            </div>
        </div>
    """


def render_card_html(p: Dict[str, Any], oob: bool = False) -> str:
    """Renders a streamlined, performant plant card."""
    name = html.escape(str(p.get("name") or ""))
    species = html.escape(str(p.get("species") or ""))
    aka = html.escape(str(p.get("aka") or "").strip())
    status = db.normalize_status(p.get("status"))
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-OK")
    status_es = STATUS_SPANISH.get(status, status)

    # Photos: latest cover image + count pill
    photos = p.get("photos") or []
    if photos:
        cover_img = html.escape(str(photos[-1]))
        total_p = len(photos)
        count_pill = f'<span class="thumbnail-badge-count photo-count-pill">{total_p} {"FOTO" if total_p == 1 else "FOTOS"}</span>'
        thumb_html = f"""<div class="card-thumbnail-box plant-thumb-wrapper">
            <img class="card-thumbnail-img plant-thumb" src="/images/{cover_img}" alt="{name}" loading="lazy" />
            <div class="card-thumbnail-placeholder" style="display: none;">
                <div class="placeholder-icon">🌱</div>
                <div class="placeholder-text">IMAGEN NO DISPONIBLE</div>
            </div>
            {count_pill}
        </div>"""
    else:
        thumb_html = f"""<div class="card-thumbnail-box plant-thumb-wrapper no-photo">
            <div class="card-thumbnail-placeholder">
                <div class="placeholder-icon">🌱</div>
                <div class="placeholder-text">SIN FOTOGRAFÍA</div>
                <div class="placeholder-sub">CLAVE: {name}</div>
            </div>
        </div>"""

    # Formatted age and height
    age_short, age_detailed = db.calculate_plant_age(p.get("sowing_cutting_date"), p.get("graft", ""))
    raw_height = p.get("height") or ""
    height_short = db.format_height_short(raw_height)

    aka_html = f'<span class="plant-aka" title=\'Alias: "{aka}"\'>"{aka}"</span>' if aka else ""
    oob_attr = ' hx-swap-oob="outerHTML"' if oob else ""

    loc = html.escape(str(p.get("location") or "—"))
    graft = html.escape(str(p.get("graft") or "Raíz propia"))
    raw_h_esc = html.escape(str(raw_height or "Sin registrar"))
    det_age_esc = html.escape(str(age_detailed))

    return f"""<article class="plant-card" id="plant-card-{name}"{oob_attr}
         hx-get="/plants/{name}"
         hx-target="#modal-container"
         hx-swap="innerHTML"
         role="button"
         tabindex="0"
         title="Abrir expediente de {name}">
        <div class="card-head">
            <div class="card-head-left">
                <span class="plant-key" title="Clave de ejemplar">{name}</span>
                <span class="status-badge {status_cls}">● {status_es}</span>
                {aka_html}
            </div>
        </div>
        {thumb_html}
        <div class="plant-species" title="{species}">{species}</div>
        <div class="plant-meta">
            <div title="Edad biológica: {det_age_esc}">
                <span class="meta-label">EDAD:</span>
                <span class="meta-val age-highlight">{age_short}</span>
            </div>
            <div title="Ubicación: {loc}">
                <span class="meta-label">UBI:</span>
                <span class="meta-val">{loc}</span>
            </div>
            <div title="Injerto: {graft}">
                <span class="meta-label">INJERTO:</span>
                <span class="meta-val">{graft}</span>
            </div>
            <div title="Registro completo de altura: {raw_h_esc}">
                <span class="meta-label">ALTURA:</span>
                <span class="meta-val height-highlight">{height_short}</span>
            </div>
        </div>
    </article>"""


PAGE_SIZE = 16


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
