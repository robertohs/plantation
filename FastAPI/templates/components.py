"""
Plantation - Modular UI Components
Contains reusable cards, thumbnails, grid wrappers, and statistics ribbons.
"""

from typing import Any, Dict, List
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
    """Renders a photo card in the technical dossier with instant deletion."""
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
                {aka_html}
            </div>
            <span class="status-badge {status_cls}">● {status_es}</span>
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


def render_plants_grid(plants: List[Dict[str, Any]]) -> str:
    """Renders the plants cards grid or a friendly empty state."""
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
            <span style="color: var(--peach-orange);">● notOK: {not_ok_count}</span>
        </div>
    </div>
    """
