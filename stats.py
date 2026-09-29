"""
Plantation - Botanical Analytics & Statistics Engine
Consolidates all statistical logic, mathematical aggregations, SVG chart generators,
and dashboard templates for specimen analysis in a single isolated module.
"""

from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
import db

router = APIRouter()


# ==============================================================================
# DATA AGGREGATION & ANALYTICS COMPUTATION
# ==============================================================================

def compute_collection_stats() -> Dict[str, Any]:
    """Computes comprehensive botanical metrics and distributions across all specimens."""
    plants = db.get_plants()
    total = len(plants)

    if total == 0:
        return {
            "total": 0,
            "ok_count": 0,
            "notok_count": 0,
            "health_pct": 100.0,
            "genera": [],
            "age_cohorts": [],
            "height_tiers": [],
            "root_types": {"own": 0, "grafted": 0, "own_pct": 100.0, "grafted_pct": 0.0},
            "locations": [],
            "photos": {"total_photos": 0, "documented": 0, "coverage_pct": 0.0, "avg": 0.0},
            "oldest": None,
            "tallest": None,
            "quarantine": []
        }

    # 1. Health Status Breakdown
    ok_count = sum(1 for p in plants if db.normalize_status(p.get("status")) == "OK")
    notok_count = total - ok_count
    health_pct = round((ok_count / total) * 100, 1)

    # 2. Genus & Taxonomy Distribution
    genus_counts: Dict[str, int] = {}
    for p in plants:
        species = (p.get("species") or "").strip()
        genus = species.split()[0] if species else "Desconocido"
        genus_counts[genus] = genus_counts.get(genus, 0) + 1

    sorted_genera = sorted(genus_counts.items(), key=lambda x: x[1], reverse=True)
    genera_data: List[Dict[str, Any]] = [
        {"name": g, "count": c, "pct": round((c / total) * 100, 1)}
        for g, c in sorted_genera
    ]

    # 3. Root Architecture: Grafted vs Own Roots
    grafted_count = 0
    own_roots_count = 0
    for p in plants:
        graft_str = (p.get("graft") or "").lower()
        if graft_str and ("sin injerto" not in graft_str) and ("raíz propia" not in graft_str) and ("raiz propia" not in graft_str):
            grafted_count += 1
        else:
            own_roots_count += 1

    root_types = {
        "own": own_roots_count,
        "grafted": grafted_count,
        "own_pct": round((own_roots_count / total) * 100, 1),
        "grafted_pct": round((grafted_count / total) * 100, 1)
    }

    # 4. Age Cohorts & Chronological Records
    cohort_less_1 = 0
    cohort_1_to_2 = 0
    cohort_2_to_3 = 0
    cohort_3_plus = 0
    cohort_unknown = 0

    oldest_plant = None
    max_age_months = -1
    total_known_age_months = 0
    known_age_count = 0

    for p in plants:
        months = db.get_plant_age_months(p.get("sowing_cutting_date"), p.get("graft"))
        if months is None:
            cohort_unknown += 1
        else:
            known_age_count += 1
            total_known_age_months += months
            if months > max_age_months:
                max_age_months = months
                oldest_plant = {
                    "name": p.get("name"),
                    "species": p.get("species"),
                    "months": months,
                    "display": db.calculate_plant_age(p.get("sowing_cutting_date"), p.get("graft"))[0]
                }

            if months < 12:
                cohort_less_1 += 1
            elif months < 24:
                cohort_1_to_2 += 1
            elif months < 36:
                cohort_2_to_3 += 1
            else:
                cohort_3_plus += 1

    avg_age_str = "—"
    if known_age_count > 0:
        avg_m = total_known_age_months / known_age_count
        avg_years = avg_m / 12.0
        avg_age_str = f"{avg_years:.1f} años" if avg_years >= 1.0 else f"{int(avg_m)} meses"

    age_cohorts = [
        {"label": "< 1 año", "tag": "Plántulas", "count": cohort_less_1, "pct": round((cohort_less_1 / total) * 100, 1)},
        {"label": "1 - 2 años", "tag": "Juveniles", "count": cohort_1_to_2, "pct": round((cohort_1_to_2 / total) * 100, 1)},
        {"label": "2 - 3 años", "tag": "Desarrollo", "count": cohort_2_to_3, "pct": round((cohort_2_to_3 / total) * 100, 1)},
        {"label": "3+ años", "tag": "Adultos", "count": cohort_3_plus, "pct": round((cohort_3_plus / total) * 100, 1)},
        {"label": "S/D", "tag": "Sin fecha", "count": cohort_unknown, "pct": round((cohort_unknown / total) * 100, 1)}
    ]

    # 5. Height Distribution & Biometrics
    tier_mini = 0      # < 5 cm
    tier_juvenil = 0   # 5 - 15 cm
    tier_medium = 0    # 15 - 30 cm
    tier_giant = 0     # > 30 cm
    tier_unknown = 0

    tallest_plant = None
    max_height = -1.0
    total_height_cm = 0.0
    known_height_count = 0

    for p in plants:
        h = db.extract_height_cm(p.get("height"))
        if h is None:
            tier_unknown += 1
        else:
            known_height_count += 1
            total_height_cm += h
            if h > max_height:
                max_height = h
                tallest_plant = {
                    "name": p.get("name"),
                    "species": p.get("species"),
                    "height_cm": h
                }

            if h < 5.0:
                tier_mini += 1
            elif h < 15.0:
                tier_juvenil += 1
            elif h <= 30.0:
                tier_medium += 1
            else:
                tier_giant += 1

    avg_height_str = f"{(total_height_cm / known_height_count):.1f} cm" if known_height_count > 0 else "—"

    height_tiers = [
        {"label": "< 5 cm", "tag": "Miniatura", "count": tier_mini, "pct": round((tier_mini / total) * 100, 1)},
        {"label": "5 - 15 cm", "tag": "Juvenil", "count": tier_juvenil, "pct": round((tier_juvenil / total) * 100, 1)},
        {"label": "15 - 30 cm", "tag": "Desarrollado", "count": tier_medium, "pct": round((tier_medium / total) * 100, 1)},
        {"label": "> 30 cm", "tag": "Columnar/Ejemplar", "count": tier_giant, "pct": round((tier_giant / total) * 100, 1)},
        {"label": "S/D", "tag": "Sin medir", "count": tier_unknown, "pct": round((tier_unknown / total) * 100, 1)}
    ]

    # 6. Physical Space & Greenhouse Allocation
    loc_counts: Dict[str, int] = {}
    for p in plants:
        loc = (p.get("location") or "Sin asignar").strip()
        loc_counts[loc] = loc_counts.get(loc, 0) + 1

    sorted_locations = sorted(loc_counts.items(), key=lambda x: x[1], reverse=True)
    location_data = [
        {"name": loc, "count": c, "pct": round((c / total) * 100, 1)}
        for loc, c in sorted_locations
    ]

    # 7. Photographic Assets & Documentation Rate
    total_photos = 0
    plants_with_photos = 0
    for p in plants:
        photos = p.get("photos", [])
        if photos and len(photos) > 0:
            plants_with_photos += 1
            total_photos += len(photos)

    photo_metrics = {
        "total_photos": total_photos,
        "documented": plants_with_photos,
        "coverage_pct": round((plants_with_photos / total) * 100, 1),
        "avg": round(total_photos / total, 1)
    }

    # 8. Quarantine & Active Health Alerts
    quarantine_list = [
        {
            "name": p.get("name"),
            "species": p.get("species"),
            "aka": p.get("aka") or "",
            "location": p.get("location") or "Ubicación sin registrar",
            "comentarios": p.get("comentarios") or "Marcado en observación sanitaria."
        }
        for p in plants
        if db.normalize_status(p.get("status")) == "notOK"
    ]

    return {
        "total": total,
        "ok_count": ok_count,
        "notok_count": notok_count,
        "health_pct": health_pct,
        "genera": genera_data,
        "age_cohorts": age_cohorts,
        "height_tiers": height_tiers,
        "root_types": root_types,
        "locations": location_data,
        "photos": photo_metrics,
        "avg_age": avg_age_str,
        "oldest": oldest_plant,
        "avg_height": avg_height_str,
        "tallest": tallest_plant,
        "quarantine": quarantine_list
    }


# ==============================================================================
# SVG CHART GENERATORS (Crisp, Zero-Dependency, Theme-Aware)
# ==============================================================================

def render_health_donut_svg(ok_count: int, notok_count: int, health_pct: float) -> str:
    """Renders a responsive SVG circular ring gauge of collection health."""
    total = ok_count + notok_count
    if total == 0:
        return ""

    radius = 48
    circumference = 2 * 3.14159265 * radius  # ~301.59
    ok_stroke = round((ok_count / total) * circumference, 2)
    notok_stroke = round((notok_count / total) * circumference, 2)

    return f"""
    <div style="display: flex; align-items: center; justify-content: center; gap: 20px; flex-wrap: wrap;">
        <div style="position: relative; width: 140px; height: 140px; flex-shrink: 0;">
            <svg viewBox="0 0 120 120" width="140" height="140" style="transform: rotate(-90deg);">
                <!-- Background track -->
                <circle cx="60" cy="60" r="{radius}" fill="none" stroke="var(--bg-surface)" stroke-width="14" />
                <!-- OK arc -->
                <circle cx="60" cy="60" r="{radius}" fill="none"
                        stroke="var(--green-sage)" stroke-width="14"
                        stroke-dasharray="{ok_stroke} {circumference}"
                        stroke-linecap="round"
                        style="transition: stroke-dasharray 0.6s ease;" />
                <!-- notOK arc -->
                {f'''<circle cx="60" cy="60" r="{radius}" fill="none"
                            stroke="var(--red-crimson)" stroke-width="14"
                            stroke-dasharray="{notok_stroke} {circumference}"
                            stroke-dashoffset="-{ok_stroke}"
                            stroke-linecap="round"
                            style="transition: stroke-dasharray 0.6s ease;" />''' if notok_count > 0 else ''}
            </svg>
            <div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; pointer-events: none;">
                <span style="font-family: var(--font-mono); font-size: 22px; font-weight: 800; color: var(--text-main); line-height: 1;">
                    {health_pct:.0f}%
                </span>
                <span style="font-size: 9px; font-family: var(--font-mono); color: var(--text-dim); letter-spacing: 1px; margin-top: 2px;">
                    SALUD
                </span>
            </div>
        </div>
        <div style="display: flex; flex-direction: column; gap: 10px; font-family: var(--font-mono); font-size: 11px;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 2px; background: var(--green-sage); display: inline-block;"></span>
                <span style="color: var(--text-sub);">ESTADO OK:</span>
                <strong style="color: var(--green-sage); font-weight: 700;">{ok_count}</strong>
                <span style="color: var(--text-dim); font-size: 10px;">({health_pct}%)</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="width: 10px; height: 10px; border-radius: 2px; background: var(--red-crimson); display: inline-block;"></span>
                <span style="color: var(--text-sub);">EN OBSERVACIÓN:</span>
                <strong style="color: var(--red-crimson); font-weight: 700;">{notok_count}</strong>
                <span style="color: var(--text-dim); font-size: 10px;">({round(100 - health_pct, 1)}%)</span>
            </div>
            <div style="padding-top: 6px; border-top: 1px dashed var(--border-dim); color: var(--text-dim); font-size: 10px;">
                TOTAL CENSO: <strong style="color: var(--text-main);">{total} ejemplares</strong>
            </div>
        </div>
    </div>
    """


def render_genus_bars_svg(genera: List[Dict[str, Any]]) -> str:
    """Renders horizontal taxonomic distribution bars."""
    if not genera:
        return "<div style='color: var(--text-dim); font-size: 11px;'>Sin datos taxonómicos registrados.</div>"

    max_count = max(g["count"] for g in genera) if genera else 1
    rows_html = []

    for g in genera[:8]:  # Show top 8 genera
        pct_width = max(4, round((g["count"] / max_count) * 100, 1))
        rows_html.append(f"""
        <div style="display: flex; flex-direction: column; gap: 3px; font-family: var(--font-mono);">
            <div style="display: flex; justify-content: space-between; font-size: 11px; align-items: baseline;">
                <span style="font-style: italic; color: var(--blue-sky); font-weight: 600;">{g['name']}</span>
                <span style="font-size: 10px; color: var(--text-dim);">
                    <strong style="color: var(--text-main);">{g['count']}</strong> ({g['pct']}%)
                </span>
            </div>
            <div style="height: 10px; background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 2px; overflow: hidden; position: relative;">
                <div style="height: 100%; width: {pct_width}%; background: linear-gradient(90deg, var(--blue-sky), var(--peach-orange)); border-radius: 1px; transition: width 0.4s ease;"></div>
            </div>
        </div>
        """)

    return f"""
    <div style="display: flex; flex-direction: column; gap: 8px;">
        {''.join(rows_html)}
    </div>
    """


def render_age_pyramid_svg(cohorts: List[Dict[str, Any]]) -> str:
    """Renders vertical column histogram of botanical age cohorts."""
    if not cohorts:
        return ""

    max_count = max((c["count"] for c in cohorts), default=1)
    max_count = max(max_count, 1)

    cols_html = []
    for c in cohorts:
        height_px = max(6, int((c["count"] / max_count) * 85))
        cols_html.append(f"""
        <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 6px; font-family: var(--font-mono);">
            <span style="font-size: 10px; font-weight: 700; color: var(--text-main);">{c['count']}</span>
            <div style="width: 100%; max-width: 42px; height: 90px; display: flex; align-items: flex-end; justify-content: center; background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 3px 3px 0 0; padding: 2px;">
                <div style="width: 100%; height: {height_px}px; background: linear-gradient(180deg, var(--peach-orange), var(--red-dark)); border-radius: 2px 2px 0 0; border: 1px solid var(--peach-orange); box-sizing: border-box; transition: height 0.5s ease;"></div>
            </div>
            <div style="text-align: center; line-height: 1.1;">
                <div style="font-size: 10px; font-weight: 600; color: var(--text-sub); white-space: nowrap;">{c['label']}</div>
                <div style="font-size: 8.5px; color: var(--text-dim);">{c['tag']}</div>
            </div>
        </div>
        """)

    return f"""
    <div style="display: flex; align-items: flex-end; justify-content: space-between; gap: 6px; padding: 10px 4px 4px 4px;">
        {''.join(cols_html)}
    </div>
    """


def render_root_types_bar(root_types: Dict[str, Any]) -> str:
    """Renders segmented comparison between grafted plants and own-root specimens."""
    own = root_types["own"]
    grafted = root_types["grafted"]
    own_pct = root_types["own_pct"]
    graft_pct = root_types["grafted_pct"]

    return f"""
    <div style="display: flex; flex-direction: column; gap: 10px; font-family: var(--font-mono);">
        <div style="height: 18px; display: flex; border-radius: 3px; overflow: hidden; border: 1px solid var(--border-dim); background: var(--bg-surface);">
            {f'<div style="width: {own_pct}%; background: var(--green-sage); height: 100%; display: flex; align-items: center; justify-content: center; color: var(--bg-crust); font-size: 9.5px; font-weight: bold; overflow: hidden;" title="Raíz Propia: {own_pct}%">{own_pct:.0f}%</div>' if own_pct > 10 else ''}
            {f'<div style="width: {graft_pct}%; background: var(--blue-sky); height: 100%; display: flex; align-items: center; justify-content: center; color: var(--bg-crust); font-size: 9.5px; font-weight: bold; overflow: hidden;" title="Injertado: {graft_pct}%">{graft_pct:.0f}%</div>' if graft_pct > 10 else ''}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 11px;">
            <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 3px; padding: 8px 10px;">
                <div style="display: flex; align-items: center; gap: 6px; color: var(--green-sage); font-weight: 700; margin-bottom: 2px;">
                    <span style="font-size: 14px;">🌱</span> RAÍZ PROPIA
                </div>
                <div style="font-size: 16px; font-weight: 800; color: var(--text-main);">{own} <span style="font-size: 10.5px; color: var(--text-dim); font-weight: normal;">({own_pct}%)</span></div>
                <div style="font-size: 9.5px; color: var(--text-dim); margin-top: 2px;">Napiforme / Fasciculada</div>
            </div>
            <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 3px; padding: 8px 10px;">
                <div style="display: flex; align-items: center; gap: 6px; color: var(--blue-sky); font-weight: 700; margin-bottom: 2px;">
                    <span style="font-size: 14px;">⚡</span> INJERTADO
                </div>
                <div style="font-size: 16px; font-weight: 800; color: var(--text-main);">{grafted} <span style="font-size: 10.5px; color: var(--text-dim); font-weight: normal;">({graft_pct}%)</span></div>
                <div style="font-size: 9.5px; color: var(--text-dim); margin-top: 2px;">Sobre portainjerto vigoroso</div>
            </div>
        </div>
    </div>
    """


def render_height_tiers_chart(height_tiers: List[Dict[str, Any]]) -> str:
    """Renders horizontal biometrics distribution for plant heights."""
    rows = []
    max_count = max((t["count"] for t in height_tiers), default=1)
    max_count = max(max_count, 1)

    for t in height_tiers:
        pct_width = max(3, int((t["count"] / max_count) * 100))
        rows.append(f"""
        <div style="display: flex; flex-direction: column; gap: 2px; font-family: var(--font-mono); font-size: 11px;">
            <div style="display: flex; justify-content: space-between; align-items: baseline;">
                <span style="color: var(--text-main); font-weight: 600;">{t['label']} <span style="color: var(--text-dim); font-size: 9.5px; font-weight: normal;">({t['tag']})</span></span>
                <span style="color: var(--text-dim); font-size: 10px;"><strong style="color: var(--peach-orange);">{t['count']}</strong> ({t['pct']}%)</span>
            </div>
            <div style="height: 8px; background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 2px; overflow: hidden;">
                <div style="height: 100%; width: {pct_width}%; background: var(--peach-orange); border-radius: 1px;"></div>
            </div>
        </div>
        """)

    return f"<div style='display: flex; flex-direction: column; gap: 8px;'>{''.join(rows)}</div>"


def render_location_meters(locations: List[Dict[str, Any]]) -> str:
    """Renders location occupancy breakdown."""
    if not locations:
        return "<div style='color: var(--text-dim); font-size: 11px;'>Sin ubicaciones registradas.</div>"

    rows = []
    for loc in locations[:6]:
        rows.append(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; font-family: var(--font-mono); font-size: 11px; padding: 5px 8px; background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 2px;">
            <span style="color: var(--text-sub); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 65%;">
                📍 {loc['name']}
            </span>
            <span style="font-weight: 700; color: var(--text-main);">
                {loc['count']} <span style="font-size: 10px; color: var(--text-dim); font-weight: normal;">({loc['pct']}%)</span>
            </span>
        </div>
        """)

    return f"<div style='display: flex; flex-direction: column; gap: 6px;'>{''.join(rows)}</div>"


# ==============================================================================
# STATS MODAL DASHBOARD TEMPLATE
# ==============================================================================

def render_stats_modal() -> str:
    """Renders the comprehensive stats and analytics modal dialog."""
    s = compute_collection_stats()

    # Oldest and tallest badge strings
    oldest_str = f"[{s['oldest']['name']}] {s['oldest']['display']}" if s['oldest'] else "—"
    tallest_str = f"[{s['tallest']['name']}] {s['tallest']['height_cm']} cm" if s['tallest'] else "—"

    # Quarantine alert card
    quarantine_section = ""
    if s["quarantine"]:
        q_rows = "".join(
            f"""
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 6px 10px; background: rgba(239, 68, 68, 0.08); border-left: 3px solid var(--red-crimson); margin-bottom: 6px; font-family: var(--font-mono); font-size: 11px;">
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <button type="button"
                                class="btn btn-red btn-sm"
                                hx-get="/plants/{q['name']}/modal/view"
                                hx-target="#modal-container"
                                hx-swap="innerHTML"
                                title="Abrir expediente técnico">
                            VER [{q['name']}]
                        </button>
                        <span style="font-weight: 700; color: var(--text-main);">{q['species']}</span>
                        {f'<span style="color: var(--text-dim); font-size: 10px;">"{q["aka"]}"</span>' if q["aka"] else ''}
                    </div>
                    <div style="color: var(--text-sub); font-size: 10.5px; margin-top: 3px;">
                        ⚠️ {q['comentarios']}
                    </div>
                </div>
                <div style="font-size: 10px; color: var(--text-dim); white-space: nowrap;">
                    {q['location']}
                </div>
            </div>
            """
            for q in s["quarantine"]
        )

        quarantine_section = f"""
        <div style="margin-bottom: 20px; border: 1px solid var(--red-crimson); background: var(--bg-mantle); border-radius: 4px; padding: 12px 14px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 800; color: var(--red-crimson); letter-spacing: 1px; display: flex; align-items: center; gap: 6px;">
                    <span>⚠️ ALERTA FITOSANITARIA // CUARENTENA ACTIVA</span>
                    <span style="background: var(--red-crimson); color: var(--bg-crust); padding: 1px 6px; border-radius: 2px; font-size: 10px;">{len(s['quarantine'])} EJEMPLARES</span>
                </div>
                <span style="font-size: 10px; color: var(--text-dim); font-family: var(--font-mono);">Requieren revisión o tratamiento</span>
            </div>
            <div>{q_rows}</div>
        </div>
        """

    return f"""
    <div class="modal-overlay" id="stats-dashboard-modal" style="display: flex;">
        <div class="modal-dialog" style="max-width: 980px; width: 95vw; max-height: 92vh;">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title" style="color: var(--peach-orange);">[ANALÍTICA BOTÁNICA & MÉTRICAS DE COLECCIÓN]</span>
                    <span style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-dim); background: var(--bg-surface); padding: 2px 8px; border-radius: 2px; border: 1px solid var(--border-dim);">
                        TOTAL: {s['total']} EJEMPLARES
                    </span>
                </div>
                <div style="display: flex; align-items: center; gap: 8px;">
                    <button class="btn btn-sm"
                            hx-get="/stats/modal"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Recalcular métricas"
                            aria-label="Actualizar">
                        ↻ ACTUALIZAR
                    </button>
                    <button class="modal-close-btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Cerrar modal">✕</button>
                </div>
            </div>

            <div class="modal-body" style="padding: 16px 20px 24px 20px; overflow-y: auto;">
                
                {quarantine_section}

                <!-- TOP KPI RIBBON -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 20px;">
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 10px 12px; font-family: var(--font-mono);">
                        <div style="font-size: 9.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px;">EJEMPLARES TOTALES</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--text-main); margin-top: 2px;">{s['total']}</div>
                        <div style="font-size: 10px; color: var(--text-sub); margin-top: 2px;">100% inventariados</div>
                    </div>

                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 10px 12px; font-family: var(--font-mono);">
                        <div style="font-size: 9.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px;">TASA FITOSANITARIA</div>
                        <div style="font-size: 24px; font-weight: 800; color: {'var(--green-sage)' if s['health_pct'] >= 70 else 'var(--red-crimson)'}; margin-top: 2px;">{s['health_pct']}%</div>
                        <div style="font-size: 10px; color: var(--text-sub); margin-top: 2px;">{s['ok_count']} OK · {s['notok_count']} Alerta</div>
                    </div>

                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 10px 12px; font-family: var(--font-mono);">
                        <div style="font-size: 9.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px;">EDAD PROMEDIO</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--blue-sky); margin-top: 2px;">{s['avg_age']}</div>
                        <div style="font-size: 10px; color: var(--text-sub); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Más longevo: {oldest_str}">Max: {oldest_str}</div>
                    </div>

                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 10px 12px; font-family: var(--font-mono);">
                        <div style="font-size: 9.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px;">ALTURA MEDIA</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--peach-orange); margin-top: 2px;">{s['avg_height']}</div>
                        <div style="font-size: 10px; color: var(--text-sub); margin-top: 2px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="Más alto: {tallest_str}">Max: {tallest_str}</div>
                    </div>

                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 10px 12px; font-family: var(--font-mono);">
                        <div style="font-size: 9.5px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px;">FOTOS ARCHIVADAS</div>
                        <div style="font-size: 24px; font-weight: 800; color: var(--red-crimson); margin-top: 2px;">{s['photos']['total_photos']}</div>
                        <div style="font-size: 10px; color: var(--text-sub); margin-top: 2px;">{s['photos']['coverage_pct']}% cobertura ({s['photos']['documented']}/{s['total']})</div>
                    </div>
                </div>

                <!-- MAIN CHARTS GRID -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px;">
                    
                    <!-- PANEL 1: HEALTH RING -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● BALANCE SANITARIO</span>
                            <span style="color: var(--text-dim); font-size: 10px;">ESTADO</span>
                        </div>
                        {render_health_donut_svg(s['ok_count'], s['notok_count'], s['health_pct'])}
                    </div>

                    <!-- PANEL 2: TAXONOMIC GENUS DISTRIBUTION -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● DIVERSIDAD TAXONÓMICA</span>
                            <span style="color: var(--text-dim); font-size: 10px;">{len(s['genera'])} GÉNEROS</span>
                        </div>
                        {render_genus_bars_svg(s['genera'])}
                    </div>

                    <!-- PANEL 3: AGE COHORTS PYRAMID -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● COHORTES CRONOLÓGICAS</span>
                            <span style="color: var(--text-dim); font-size: 10px;">EDAD</span>
                        </div>
                        {render_age_pyramid_svg(s['age_cohorts'])}
                    </div>

                    <!-- PANEL 4: ROOT ARCHITECTURE -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● ARQUITECTURA RADICULAR</span>
                            <span style="color: var(--text-dim); font-size: 10px;">INJERTO VS RAÍZ</span>
                        </div>
                        {render_root_types_bar(s['root_types'])}
                    </div>

                    <!-- PANEL 5: HEIGHT BIOMETRICS -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● BIOMETRÍA & ESTRATOS DE ALTURA</span>
                            <span style="color: var(--text-dim); font-size: 10px;">ALTURA (CM)</span>
                        </div>
                        {render_height_tiers_chart(s['height_tiers'])}
                    </div>

                    <!-- PANEL 6: FACILITY & GREENHOUSE SPACE -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 14px 16px;">
                        <div style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: var(--text-main); margin-bottom: 12px; display: flex; justify-content: space-between;">
                            <span>● DISTRIBUCIÓN POR UBICACIÓN</span>
                            <span style="color: var(--text-dim); font-size: 10px;">ESPACIO</span>
                        </div>
                        {render_location_meters(s['locations'])}
                    </div>

                </div>

            </div>

            <div class="modal-footer" style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-size: 11px; font-family: var(--font-mono); color: var(--text-dim);">
                    Plantation Analytics Engine v1.0 · Cálculos basados en SQLite
                </span>
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
    """


# ==============================================================================
# FASTAPI ENDPOINTS
# ==============================================================================

@router.get("/stats/modal", response_class=HTMLResponse)
def get_stats_modal():
    """Renders the statistics modal for HTMX injection."""
    return HTMLResponse(render_stats_modal())


@router.get("/stats/data.json")
def get_stats_json():
    """Returns raw aggregated collection statistics in JSON format."""
    return JSONResponse(compute_collection_stats())
