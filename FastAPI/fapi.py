"""
Plantation - FastAPI Router & Controller Engine
Lightweight HTTP endpoints using SQLite, HTMX partial rendering, and modular templates.
"""

import csv
import html
import io
import os
import re
import tempfile
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, UploadFile, File, Query
from fastapi.responses import HTMLResponse, Response, FileResponse, RedirectResponse

import db
from img_conv import validate_and_save_photo, delete_photo_file, cleanup_plant_photos, IMAGES_DIR
from pdf_gen import generate_catalog_pdf, generate_single_plant_pdf
from .templates.components import (
    render_card_html,
    render_plants_grid,
    render_plants_page,
    render_stats_bar,
    render_photo_item_html
)
from .templates.modals import (
    render_view_plant_modal_content,
    render_new_plant_modal,
    render_edit_plant_modal,
    render_bulk_create_modal,
    render_bulk_delete_modal,
    render_bulk_keys_preview,
    render_import_db_modal
)
from .templates.admin import (
    render_admin_modal,
    render_admin_panel_content,
    render_admin_table_content,
    render_admin_stats_cards,
    render_db_health_card
)
from .templates.layout import render_index_html
from .templates.dossier import render_printable_dossier_html
import stats

router = APIRouter()
router.include_router(stats.router)


def is_admin_open(request: Request) -> bool:
    """Stateless check: verifies if admin tray is open for this client via cookie."""
    return request.cookies.get("plantation_admin") == "1"


def get_oob_admin(request: Request) -> str:
    """Returns out-of-band admin tray update if currently open for this client."""
    if is_admin_open(request):
        return f'<div id="admin-container" hx-swap-oob="innerHTML">{render_admin_panel_content()}</div>'
    return ""


# ==============================================================================
# MAIN PAGE & REACTIVE GRID
# ==============================================================================

@router.api_route("/healthz", methods=["GET", "HEAD"])
@router.api_route("/health", methods=["GET", "HEAD"])
def health_check(request: Request):
    return HTMLResponse("OK", status_code=200)


@router.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def index_view(request: Request):
    """Main application shell."""
    if request.method == "HEAD":
        return HTMLResponse(content="", status_code=200)
    plants = db.get_plants()
    return HTMLResponse(render_index_html(plants))


@router.get("/plants", response_class=HTMLResponse)
def list_plants_partial(
    search: Optional[str] = None,
    status: Optional[str] = None,
    age: Optional[str] = None,
    height: Optional[str] = None,
    page: int = 1
):
    """HTMX endpoint returning reactive filtered plants grid or infinite scroll card batch."""
    plants = db.get_plants(
        search_query=search,
        status_filter=status,
        age_filter=age,
        height_filter=height
    )
    if page > 1:
        return HTMLResponse(render_plants_page(
            plants,
            page=page,
            search=search,
            status=status,
            age=age,
            height=height
        ))
    return HTMLResponse(render_plants_grid(
        plants,
        page=1,
        search=search,
        status=status,
        age=age,
        height=height
    ))


# ==============================================================================
# SPECIMEN MODALS (VIEW, CREATE, EDIT)
# ==============================================================================

@router.get("/plants/validate-key", response_class=HTMLResponse)
def validate_key_endpoint(name: Optional[str] = None, key: Optional[str] = None):
    """Validates specimen key availability in real-time as the user types."""
    raw = name if isinstance(name, str) else (key if isinstance(key, str) else "")
    k = db.clean_key(raw)
    if not k:
        return HTMLResponse("""
            <script>
                var btn = document.getElementById('new-plant-submit-btn');
                var inp = document.getElementById('inp-name');
                if (btn) btn.disabled = false;
                if (inp) inp.style.borderColor = 'var(--border-dim)';
            </script>
        """)

    existing = db.get_plant(k)
    if existing:
        return HTMLResponse(f"""
            <span style="color: var(--red-crimson); font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                ✕ La clave '{k}' ya existe en el registro. Ingrese una clave única.
            </span>
            <script>
                var btn = document.getElementById('new-plant-submit-btn');
                var inp = document.getElementById('inp-name');
                if (btn) btn.disabled = true;
                if (inp) inp.style.borderColor = 'var(--red-crimson)';
            </script>
        """)
    else:
        return HTMLResponse(f"""
            <span style="color: var(--green-sage); font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
                ✓ Clave '{k}' disponible para registro.
            </span>
            <script>
                var btn = document.getElementById('new-plant-submit-btn');
                var inp = document.getElementById('inp-name');
                if (btn) btn.disabled = false;
                if (inp) inp.style.borderColor = 'var(--green-sage)';
            </script>
        """)


@router.get("/plants/validate-parent-key", response_class=HTMLResponse)
def validate_parent_key_endpoint(
    key: Optional[str] = None,
    padre1: Optional[str] = None,
    padre2: Optional[str] = None,
    num: int = 1,
    plant: str = ""
):
    """Validates that a parent key exists in the database and is not the plant itself."""
    val = key if isinstance(key, str) else (padre1 if isinstance(padre1, str) else (padre2 if isinstance(padre2, str) else ""))
    clean_k = (val or "").strip()
    clean_plant = (plant if isinstance(plant, str) else "").strip()
    inp_id = f"inp-padre{num}"

    # If empty or explicit 'unknown': valid default
    if not clean_k or clean_k.lower() in ("unknown", "desconocido", "--"):
        return HTMLResponse(f"""
            <span style="color: var(--text-dim); font-size: 11px;">
                ✓ Sin parental seleccionado (default: "unknown")
            </span>
            <script>
                var inp = document.getElementById('{inp_id}');
                if (inp) inp.style.borderColor = 'var(--border-dim)';
                updateCombinedPadres();
            </script>
        """)

    # Cannot be the plant itself
    if clean_plant and clean_k.lower() == clean_plant.lower():
        return HTMLResponse(f"""
            <span style="color: var(--red-crimson); font-weight: 700; font-size: 11px;">
                ✕ Un ejemplar no puede ser su propio parental.
            </span>
            <script>
                var inp = document.getElementById('{inp_id}');
                if (inp) inp.style.borderColor = 'var(--red-crimson)';
                var btn1 = document.getElementById('new-plant-submit-btn');
                var btn2 = document.getElementById('edit-plant-submit-btn');
                if (btn1) btn1.disabled = true;
                if (btn2) btn2.disabled = true;
                updateCombinedPadres();
            </script>
        """)

    # Must exist in DB
    existing = db.get_plant(clean_k)
    if existing:
        aka = f' ("{existing.get("aka")}")' if existing.get("aka") else ""
        sp = existing.get("species", "")
        clean_name = existing.get("name", clean_k)
        return HTMLResponse(f"""
            <span style="color: var(--green-sage); font-weight: 600; font-size: 11px;">
                ✓ Clave existente: {clean_name} — {sp}{aka}
            </span>
            <script>
                var inp = document.getElementById('{inp_id}');
                if (inp) inp.style.borderColor = 'var(--green-sage)';
                var btn1 = document.getElementById('new-plant-submit-btn');
                var btn2 = document.getElementById('edit-plant-submit-btn');
                if (btn1) btn1.disabled = false;
                if (btn2) btn2.disabled = false;
                updateCombinedPadres();
            </script>
        """)
    else:
        return HTMLResponse(f"""
            <span style="color: var(--red-crimson); font-weight: 700; font-size: 11px;">
                ✕ La clave '{clean_k}' no existe en la base de datos.
            </span>
            <script>
                var inp = document.getElementById('{inp_id}');
                if (inp) inp.style.borderColor = 'var(--red-crimson)';
                var btn1 = document.getElementById('new-plant-submit-btn');
                var btn2 = document.getElementById('edit-plant-submit-btn');
                if (btn1) btn1.disabled = true;
                if (btn2) btn2.disabled = true;
                updateCombinedPadres();
            </script>
        """)


@router.get("/plants/modal/new", response_class=HTMLResponse)
def new_plant_modal():
    """Renders New Plant registration modal."""
    return HTMLResponse(render_new_plant_modal())


@router.get("/plants/modal/bulk-new", response_class=HTMLResponse)
def bulk_new_plant_modal():
    """Renders the batch specimen creation modal."""
    return HTMLResponse(render_bulk_create_modal())


@router.get("/plants/modal/bulk-delete", response_class=HTMLResponse)
def bulk_delete_modal():
    """Renders the batch specimen deletion and photo purge modal."""
    return HTMLResponse(render_bulk_delete_modal())


@router.post("/plants/bulk-delete-modal-action", response_class=HTMLResponse)
async def bulk_delete_modal_action(
    keys_csv: Optional[str] = Form(None),
    keys: List[str] = Form([])
):
    """Processes batch removal of plants and disk photos from the modal."""
    final_keys_set = set()
    if keys_csv and keys_csv.strip():
        for k in keys_csv.split(","):
            clean = db.clean_key(k)
            if clean:
                final_keys_set.add(clean)
    for k in keys:
        clean = db.clean_key(k)
        if clean:
            final_keys_set.add(clean)

    final_keys = list(final_keys_set)
    deleted_count = 0
    cleaned_photos_count = 0
    if final_keys:
        deleted_count, photos_to_clean = db.bulk_delete_plants(final_keys)
        if photos_to_clean:
            cleaned_photos_count = len(photos_to_clean)
            cleanup_plant_photos(photos_to_clean)

    plants = db.get_plants()
    plants_grid = render_plants_grid(plants)
    stats_bar = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    close_modal_oob = '<div id="modal-container" hx-swap-oob="innerHTML"></div>'

    inv = db.get_inventory_stats()
    oob_admin_stats = f'<div id="admin-stats-summary" hx-swap-oob="innerHTML">{render_admin_stats_cards(inv)}</div>'
    oob_admin_table = f'<div id="admin-table-container" hx-swap-oob="innerHTML">{render_admin_table_content()}</div>'

    toast_banner = f"""
    <div id="bulk-del-toast-banner" style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; color: var(--red-crimson); font-size: 13px; font-weight: 600;">
        <span>🗑 <strong>Baja masiva completada:</strong> Se eliminaron {deleted_count} ejemplares de la base de datos y se purgaron {cleaned_photos_count} fotografías en disco.</span>
        <button type="button" onclick="this.parentElement.remove()" style="background: transparent; border: none; color: var(--red-crimson); font-weight: bold; cursor: pointer; font-size: 16px;">✕</button>
    </div>
    """

    return HTMLResponse(toast_banner + plants_grid + stats_bar + close_modal_oob + oob_admin_stats + oob_admin_table)


@router.get("/plants/validate-bulk-keys", response_class=HTMLResponse)
def validate_bulk_keys_endpoint(
    prefix: str = Query("k"),
    count: int = Query(10),
    start_num: int = Query(1),
    pad_zeros: Optional[str] = Query(None),
    skip_conflicts: Optional[str] = Query(None)
):
    """Real-time validation endpoint for sequential key generation."""
    clean_pfx = (prefix or "").strip()
    is_pad = bool(pad_zeros and pad_zeros.strip() in ("1", "true", "on"))
    is_skip = bool(skip_conflicts and skip_conflicts.strip() in ("1", "true", "on"))
    return HTMLResponse(render_bulk_keys_preview(
        prefix=clean_pfx,
        count=count,
        start_num=start_num,
        pad_zeros=is_pad,
        skip_conflicts=is_skip
    ))


@router.post("/plants/bulk-create", response_class=HTMLResponse)
async def bulk_create_plants_submit(
    request: Request,
    prefix: str = Form("K"),
    count: int = Form(10),
    start_num: int = Form(1),
    pad_zeros: Optional[str] = Form("2"),
    skip_conflicts: Optional[str] = Form("1"),
    key_mode: str = Form("seq"),
    manual_keys: str = Form(""),
    auto_number_alias: Optional[str] = Form(None),
    species: str = Form(...),
    aka: str = Form(""),
    location: str = Form(""),
    status: str = Form("OK"),
    height: str = Form(""),
    sowing_cutting_date: str = Form(""),
    graft: str = Form(""),
    padre1: Optional[str] = Form(None),
    padre2: Optional[str] = Form(None),
    fertilizante: str = Form(""),
    comentarios: str = Form(""),
    bulk_photo: Optional[UploadFile] = File(None)
):
    """Creates multiple specimens in a batch with shared metadata and validated sequential keys."""
    clean_pfx = (prefix or "").strip()
    is_skip = bool(skip_conflicts and str(skip_conflicts).strip() in ("1", "true", "on"))
    is_auto_alias = bool(auto_number_alias and str(auto_number_alias).strip() in ("1", "true", "on"))

    # Generate or parse candidate keys
    if key_mode == "manual" and manual_keys.strip():
        import re
        raw_parts = re.split(r'[, \n\r\t]+', manual_keys.strip())
        keys = []
        for p in raw_parts:
            ck = db.clean_key(p)
            if ck and ck not in keys:
                keys.append(ck)
        if not keys:
            return HTMLResponse("""
                <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                    <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                        ✕ No se encontraron claves alfanuméricas válidas en el texto manual ingresado.
                    </div>
                </div>
            """)
    else:
        if not clean_pfx:
            return HTMLResponse("""
                <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                    <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                        ✕ El prefijo o código clave no puede estar vacío.
                    </div>
                </div>
            """)
        pad_mode_val = 2
        try:
            pad_mode_val = int(pad_zeros) if pad_zeros is not None else 2
        except (ValueError, TypeError):
            pad_mode_val = 2
        keys = db.generate_bulk_keys(clean_pfx, count, start_num, pad_mode_val)
        if not keys:
            return HTMLResponse("""
                <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                    <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                        ✕ No se generaron claves válidas. Verifique el prefijo y cantidad.
                    </div>
                </div>
            """)

    # Validate parent keys
    all_keys = db.get_all_keys()
    all_keys_set = set(k.strip().lower() for k in all_keys)
    p1 = (padre1 or "").strip()
    p2 = (padre2 or "").strip()

    if p1 and p1.lower() not in ("unknown", "desconocido") and p1.lower() not in all_keys_set:
        return HTMLResponse(f"""
            <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                    ✕ El Progenitor 1 '{html.escape(p1)}' no existe en la base de datos.
                </div>
            </div>
        """)

    if p2 and p2.lower() not in ("unknown", "desconocido") and p2.lower() not in all_keys_set:
        return HTMLResponse(f"""
            <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                    ✕ El Progenitor 2 '{html.escape(p2)}' no existe en la base de datos.
                </div>
            </div>
        """)

    clean_sow = (sowing_cutting_date or "").strip()
    if clean_sow:
        dt_sow = db.parse_plant_date(clean_sow)
        if dt_sow:
            clean_sow = dt_sow.strftime("%Y-%m-%d")

    common_data = {
        "species": species.strip(),
        "aka": aka.strip(),
        "location": location.strip(),
        "status": status.strip() or "OK",
        "height": height.strip(),
        "registration_date": datetime.now().strftime("%Y-%m-%d"),
        "sowing_cutting_date": clean_sow,
        "graft": graft.strip(),
        "padres": db.combine_parents(p1, p2),
        "fertilizante": fertilizante.strip(),
        "comentarios": comentarios.strip(),
        "indxw": 0,
        "photos": []
    }

    # Handle batch photo assignment per individual plant
    plant_photos_map = {}
    if bulk_photo and bulk_photo.filename:
        file_bytes = await bulk_photo.read()
        if file_bytes and len(file_bytes) > 0:
            for k in keys:
                ok, saved_fn, _ = validate_and_save_photo(k, file_bytes, bulk_photo.filename)
                if ok and saved_fn:
                    plant_photos_map[k] = [saved_fn]

    success, msg, created, conflicts = db.create_plants_bulk(
        keys,
        common_data,
        skip_existing=is_skip,
        auto_number_alias=is_auto_alias,
        plant_photos_map=plant_photos_map
    )

    if not success:
        return HTMLResponse(f"""
            <div id="bulk-keys-preview-container" hx-swap-oob="innerHTML">
                <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 8px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson);">
                    ✕ {html.escape(msg)}
                </div>
            </div>
        """)

    plants = db.get_plants()
    plants_grid = render_plants_grid(plants)
    stats_bar = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    close_modal_oob = '<div id="modal-container" hx-swap-oob="innerHTML"></div>'
    
    toast_banner = f"""
    <div id="bulk-toast-banner" style="background: rgba(34, 197, 94, 0.15); border: 1px solid var(--green-sage); border-radius: 4px; padding: 12px 16px; margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; color: var(--green-sage); font-size: 13px; font-weight: 600;">
        <span>🌿 <strong>¡Registro masivo completado con éxito!</strong> {html.escape(msg)}</span>
        <button type="button" onclick="this.parentElement.remove()" style="background: transparent; border: none; color: var(--green-sage); font-weight: bold; cursor: pointer; font-size: 16px;">✕</button>
    </div>
    """

    return HTMLResponse(toast_banner + plants_grid + stats_bar + close_modal_oob)


@router.get("/plants/{name}", response_class=HTMLResponse)
@router.get("/plants/{name}/modal/view", response_class=HTMLResponse)
def view_plant_modal(name: str):
    """Renders comprehensive technical dossier modal."""
    plant = db.get_plant(name)
    if not plant:
        return HTMLResponse("<div class='modal-overlay'><div class='modal-dialog'><div class='modal-body'>Planta no encontrada.</div></div></div>")
    return HTMLResponse(render_view_plant_modal_content(plant))


@router.post("/plants", response_class=HTMLResponse)
async def create_plant_submit(
    request: Request,
    name: str = Form(...),
    species: str = Form(...),
    aka: str = Form(""),
    location: str = Form(""),
    status: str = Form("OK"),
    height: str = Form(""),
    registration_date: str = Form(""),
    sowing_cutting_date: str = Form(""),
    graft: str = Form(""),
    padres: str = Form(""),
    padre1: Optional[str] = Form(None),
    padre2: Optional[str] = Form(None),
    sel_padre1: Optional[str] = Form(None),
    sel_padre2: Optional[str] = Form(None),
    last_pruned: str = Form(""),
    last_repotted: str = Form(""),
    fertilizante: str = Form(""),
    comentarios: str = Form(""),
    indxw: Optional[str] = Form("0"),
    photos: List[UploadFile] = File(None)
):
    """Processes creation of a new plant record with photo uploads."""
    key = db.clean_key(name)
    if not key:
        return HTMLResponse("""
            <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                ✕ Error: El identificador (KEY) debe contener caracteres alfanuméricos válidos.
            </div>
            <script>
                var inp = document.getElementById('inp-name');
                if (inp) { inp.style.borderColor = 'var(--red-crimson)'; inp.focus(); }
            </script>
        """)

    if db.get_plant(key):
        return HTMLResponse(f"""
            <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                ✕ Error de registro: La clave '{key}' ya existe en la base de datos. Ingrese un identificador único.
            </div>
            <div id="key-validation-feedback" hx-swap-oob="innerHTML">
                <span style="color: var(--red-crimson); font-weight: 700;">
                    ✕ Clave duplicada: '{key}' ya está registrada.
                </span>
            </div>
            <script>
                var inp = document.getElementById('inp-name');
                var btn = document.getElementById('new-plant-submit-btn');
                if (inp) {{ inp.style.borderColor = 'var(--red-crimson)'; inp.focus(); }}
                if (btn) {{ btn.disabled = true; }}
            </script>
        """)

    # Save uploaded photos
    saved_photos: List[str] = []
    if photos:
        for file in photos:
            if file and file.filename:
                file_bytes = await file.read()
                if file_bytes and len(file_bytes) > 0:
                    ok, fn, _ = validate_and_save_photo(key, file_bytes, file.filename)
                    if ok and fn:
                        saved_photos.append(fn)

    all_keys = db.get_all_keys()
    all_keys_set = set(k.strip().lower() for k in all_keys)

    p1 = (padre1 or "").strip()
    p2 = (padre2 or "").strip()

    if p1 and p1.lower() not in ("unknown", "desconocido"):
        if p1.lower() == key.lower():
            return HTMLResponse(f"""
                <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ Un ejemplar no puede ser su propio progenitor ('{p1}').
                </div>
            """)
        if p1.lower() not in all_keys_set:
            return HTMLResponse(f"""
                <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ El Progenitor 1 '{p1}' no existe en la base de datos. Solo se pueden registrar claves existentes en la colección, o dejarlo vacío para 'unknown'.
                </div>
            """)

    if p2 and p2.lower() not in ("unknown", "desconocido"):
        if p2.lower() == key.lower():
            return HTMLResponse(f"""
                <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ Un ejemplar no puede ser su propio progenitor ('{p2}').
                </div>
            """)
        if p2.lower() not in all_keys_set:
            return HTMLResponse(f"""
                <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ El Progenitor 2 '{p2}' no existe en la base de datos. Solo se pueden registrar claves existentes en la colección, o dejarlo vacío para 'unknown'.
                </div>
            """)

    now_str = datetime.now().strftime("%Y-%m-%d")
    clean_sow = (sowing_cutting_date or "").strip()
    if clean_sow:
        dt_sow = db.parse_plant_date(clean_sow)
        if dt_sow:
            clean_sow = dt_sow.strftime("%Y-%m-%d")

    plant_data = {
        "name": key,
        "species": species.strip() or "Adenium obesum",
        "aka": aka.strip(),
        "location": location.strip(),
        "status": status.strip() or "OK",
        "height": height.strip(),
        "registration_date": registration_date.strip() or now_str,
        "sowing_cutting_date": clean_sow,
        "graft": graft.strip(),
        "padres": db.combine_parents(p1, p2, fallback=padres),
        "last_pruned": last_pruned.strip(),
        "last_repotted": last_repotted.strip(),
        "fertilizante": fertilizante.strip(),
        "comentarios": comentarios.strip(),
        "indxw": 1 if (indxw or "").strip() in ("1", "true", "True", "on") else 0,
        "photos": saved_photos
    }

    success, msg = db.create_plant(plant_data)
    if not success:
        return HTMLResponse(f"""
            <div id="new-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                ✕ {msg}
            </div>
        """)

    plants = db.get_plants()
    plants_grid = render_plants_grid(plants)
    stats_bar = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    close_modal_oob = '<div id="modal-container" hx-swap-oob="innerHTML"></div>'
    admin_oob = get_oob_admin(request)

    return HTMLResponse(plants_grid + stats_bar + close_modal_oob + admin_oob)


@router.get("/plants/{name}/modal/edit", response_class=HTMLResponse)
def edit_plant_modal(name: str):
    """Renders Edit Plant modal."""
    plant = db.get_plant(name)
    if not plant:
        return HTMLResponse("<div class='alert-box alert-error'>Ejemplar no encontrado.</div>", status_code=404)
    return HTMLResponse(render_edit_plant_modal(plant))


@router.post("/plants/{name}/edit", response_class=HTMLResponse)
async def update_plant_submit(
    request: Request,
    name: str,
    species: str = Form(...),
    aka: str = Form(""),
    location: str = Form(""),
    status: str = Form("OK"),
    height: str = Form(""),
    registration_date: str = Form(""),
    sowing_cutting_date: str = Form(""),
    graft: str = Form(""),
    padres: str = Form(""),
    padre1: Optional[str] = Form(None),
    padre2: Optional[str] = Form(None),
    sel_padre1: Optional[str] = Form(None),
    sel_padre2: Optional[str] = Form(None),
    last_pruned: str = Form(""),
    last_repotted: str = Form(""),
    fertilizante: str = Form(""),
    comentarios: str = Form(""),
    indxw: Optional[str] = Form(None),
    photos_to_delete: List[str] = Form([]),
    new_photos: List[UploadFile] = File(None)
):
    """Updates plant details and commits staged photo deletions and new uploads atomically."""
    key = db.clean_key(name)
    plant = db.get_plant(key)
    if not plant:
        return HTMLResponse("<div class='alert-box alert-error'>Ejemplar no encontrado.</div>", status_code=404)

    # 1. Process staged photo deletions
    if photos_to_delete:
        for ph in photos_to_delete:
            ph_clean = ph.strip()
            if ph_clean:
                db.remove_photo_from_plant(key, ph_clean)
                delete_photo_file(ph_clean)

    # 2. Process staged new photo uploads
    if new_photos:
        for file in new_photos:
            if file and file.filename:
                file_bytes = await file.read()
                if file_bytes and len(file_bytes) > 0:
                    ok, saved_fn, _ = validate_and_save_photo(key, file_bytes, file.filename)
                    if ok and saved_fn:
                        db.add_photo_to_plant(key, saved_fn)

    all_keys = db.get_all_keys()
    all_keys_set = set(k.strip().lower() for k in all_keys)

    p1 = (padre1 or "").strip()
    p2 = (padre2 or "").strip()

    if p1 and p1.lower() not in ("unknown", "desconocido"):
        if p1.lower() == key.lower():
            return HTMLResponse(f"""
                <div id="edit-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ Un ejemplar no puede ser su propio progenitor ('{p1}').
                </div>
            """)
        if p1.lower() not in all_keys_set:
            return HTMLResponse(f"""
                <div id="edit-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ El Progenitor 1 '{p1}' no existe en la base de datos. Solo se pueden registrar claves existentes en la colección, o dejarlo vacío para 'unknown'.
                </div>
            """)

    if p2 and p2.lower() not in ("unknown", "desconocido"):
        if p2.lower() == key.lower():
            return HTMLResponse(f"""
                <div id="edit-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ Un ejemplar no puede ser su propio progenitor ('{p2}').
                </div>
            """)
        if p2.lower() not in all_keys_set:
            return HTMLResponse(f"""
                <div id="edit-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                    ✕ El Progenitor 2 '{p2}' no existe en la base de datos. Solo se pueden registrar claves existentes en la colección, o dejarlo vacío para 'unknown'.
                </div>
            """)

    # 3. Update plant botanical metadata
    clean_sow = (sowing_cutting_date or "").strip()
    if clean_sow:
        dt_sow = db.parse_plant_date(clean_sow)
        if dt_sow:
            clean_sow = dt_sow.strftime("%Y-%m-%d")

    orig_reg_date = plant.get("registration_date") if plant else ""
    plant_data = {
        "species": species.strip(),
        "aka": aka.strip(),
        "location": location.strip(),
        "status": status.strip(),
        "height": height.strip(),
        "registration_date": registration_date.strip() or orig_reg_date,
        "sowing_cutting_date": clean_sow,
        "graft": graft.strip(),
        "padres": db.combine_parents(p1, p2, fallback=padres),
        "last_pruned": last_pruned.strip(),
        "last_repotted": last_repotted.strip(),
        "fertilizante": fertilizante.strip(),
        "comentarios": comentarios.strip()
    }
    if indxw is not None:
        try:
            plant_data["indxw"] = int(indxw.strip())
        except (ValueError, TypeError):
            plant_data["indxw"] = 1 if indxw.strip() in ("1", "true", "True", "on") else 0

    success, msg = db.update_plant(key, plant_data)
    if not success:
        return HTMLResponse(f"""
            <div id="edit-plant-error-banner" hx-swap-oob="outerHTML" class="alert-box alert-error" style="margin-bottom: 14px; display: block;">
                ✕ {msg}
            </div>
        """)

    updated_plant = db.get_plant(key)
    if not updated_plant:
        return HTMLResponse("<div class='alert-box alert-error'>Error al recuperar ejemplar.</div>", status_code=500)

    # Return updated technical dossier directly with success banner to #modal-container
    # and update the plant card, stats bar, and admin tray (if open) on the main page via OOB swaps
    updated_dossier = render_view_plant_modal_content(updated_plant, alert_msg=f"Cambios en el ejemplar '{key}' guardados correctamente.")
    oob_card = render_card_html(updated_plant, oob=True)
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    oob_admin = get_oob_admin(request)

    return HTMLResponse(updated_dossier + oob_card + oob_stats + oob_admin)


@router.delete("/plants/{name}", response_class=HTMLResponse)
def delete_plant_endpoint(request: Request, name: str):
    """Deletes a plant and removes its photo files from disk."""
    success, photos = db.delete_plant(name)
    if success and photos:
        cleanup_plant_photos(photos)

    plants = db.get_plants()
    grid_html = render_plants_grid(plants)
    stats_oob = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    close_modal_oob = '<div id="modal-container" hx-swap-oob="innerHTML"></div>'
    admin_oob = get_oob_admin(request)

    return HTMLResponse(grid_html + stats_oob + close_modal_oob + admin_oob)


# ==============================================================================
# PHOTO MANAGEMENT (FRIENDLY DRAG & DROP AND INSTANT PURGE)
# ==============================================================================

@router.post("/plants/{name}/photos", response_class=HTMLResponse)
async def upload_individual_plant_photo(
    request: Request,
    name: str,
    photo: UploadFile = File(...),
    source: str = Query("edit")
):
    """Handles single drag & drop photo upload into plant edit modal."""
    key = db.clean_key(name)
    plant = db.get_plant(key)
    if not plant:
        return HTMLResponse("<div class='alert-box alert-error'>Ejemplar no encontrado.</div>", status_code=404)

    file_bytes = await photo.read()
    if not file_bytes:
        return HTMLResponse("<div class='alert-box alert-error'>Archivo vacío o inválido.</div>", status_code=400)

    ok, saved_fn, err_msg = validate_and_save_photo(key, file_bytes, photo.filename)
    if not ok or not saved_fn:
        return HTMLResponse(f"<div class='alert-box alert-error'>{err_msg or 'No se pudo procesar la fotografía.'}</div>", status_code=400)

    db.add_photo_to_plant(key, saved_fn)
    updated_plant = db.get_plant(key)
    photos = updated_plant.get("photos", []) if updated_plant else []

    is_edit = (source == "edit")
    target_wrapper = "#edit-plant-photos-wrapper" if is_edit else "#plant-photos-wrapper"
    photo_items = [render_photo_item_html(key, ph, allow_delete=is_edit, target_wrapper=target_wrapper) for ph in photos]
    oob_card = render_card_html(updated_plant, oob=True)
    oob_admin = get_oob_admin(request)
    oob_count_edit = f'<span id="edit-plant-photos-count" class="form-label" style="color: var(--red-crimson);" hx-swap-oob="outerHTML">GESTIÓN DE FOTOGRAFÍAS ({len(photos)})</span>'
    oob_count_dossier = f'<span id="plant-photos-count" class="form-label" style="color: var(--red-crimson);" hx-swap-oob="outerHTML">ARCHIVOS FOTOGRÁFICOS ADJUNTOS ({len(photos)})</span>'

    return HTMLResponse(f"""
        <div class="modal-photo-list">
            {''.join(photo_items)}
        </div>
        <div class="alert-box alert-success" style="margin-top: 8px; font-size: 11px;">
            ✓ Nueva fotografía '{saved_fn}' añadida correctamente.
        </div>
    """ + oob_card + oob_admin + oob_count_edit + oob_count_dossier)


@router.delete("/plants/{name}/photos/{filename:path}", response_class=HTMLResponse)
@router.post("/plants/{name}/photos/{filename:path}/delete", response_class=HTMLResponse)
def remove_plant_photo(request: Request, name: str, filename: str, source: str = Query("edit")):
    """Removes a photo from plant record and purges file from disk."""
    key = db.clean_key(name)
    db.remove_photo_from_plant(key, filename)
    delete_photo_file(filename)

    plant = db.get_plant(key)
    photos = plant.get("photos", []) if plant else []
    is_edit = (source == "edit")
    target_wrapper = "#edit-plant-photos-wrapper" if is_edit else "#plant-photos-wrapper"
    photo_items = [render_photo_item_html(key, ph, allow_delete=is_edit, target_wrapper=target_wrapper) for ph in photos]

    oob_card = render_card_html(plant, oob=True)
    oob_admin = get_oob_admin(request)
    oob_count_edit = f'<span id="edit-plant-photos-count" class="form-label" style="color: var(--red-crimson);" hx-swap-oob="outerHTML">GESTIÓN DE FOTOGRAFÍAS ({len(photos)})</span>'
    oob_count_dossier = f'<span id="plant-photos-count" class="form-label" style="color: var(--red-crimson);" hx-swap-oob="outerHTML">ARCHIVOS FOTOGRÁFICOS ADJUNTOS ({len(photos)})</span>'

    empty_html = '<div style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 10px 0; text-align: center;">No hay fotografías adjuntas para este ejemplar. Arrastra o selecciona imágenes arriba para añadirlas.</div>' if is_edit else '<div style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 10px 0; text-align: center;">No hay fotografías adjuntas para este ejemplar. Para añadir o gestionar fotos, pulsa [EDITAR DATOS].</div>'

    return HTMLResponse(f"""
        <div class="modal-photo-list">
            {''.join(photo_items) if photo_items else empty_html}
        </div>
        <div class="alert-box alert-success" style="margin-top: 8px; font-size: 11px;">
            ✓ Foto '{filename}' eliminada del registro.
        </div>
    """ + oob_card + oob_admin + oob_count_edit + oob_count_dossier)


# ==============================================================================
# ADMIN TRAY & INVENTORY
# ==============================================================================

@router.get("/admin/modal", response_class=HTMLResponse)
@router.get("/admin", response_class=HTMLResponse)
@router.get("/admin/toggle", response_class=HTMLResponse)
def admin_modal_view():
    """Renders the comprehensive admin & inventory management modal popup."""
    return HTMLResponse(render_admin_modal())


@router.get("/admin/close", response_class=HTMLResponse)
def admin_close():
    """Closes admin panel modal."""
    return HTMLResponse("")


@router.get("/admin/filter", response_class=HTMLResponse)
def admin_filter_tab(tab: str = "ALL", search: Optional[str] = None):
    """Filters admin inventory table by category tab or search query."""
    return HTMLResponse(render_admin_table_content(filter_tag=tab, search_q=search or ""))


@router.post("/admin/bulk-delete", response_class=HTMLResponse)
def admin_bulk_delete(keys: List[str] = Form([])):
    """Deletes selected specimens and purges their photos from disk."""
    if keys:
        deleted_count, photos_to_clean = db.bulk_delete_plants(keys)
        if photos_to_clean:
            cleanup_plant_photos(photos_to_clean)

    plants = db.get_plants()
    oob_grid = f'<div id="plant-container" hx-swap-oob="innerHTML">{render_plants_grid(plants)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    inv = db.get_inventory_stats()
    oob_admin_stats = f'<div id="admin-stats-summary" hx-swap-oob="innerHTML">{render_admin_stats_cards(inv)}</div>'

    return HTMLResponse(render_admin_table_content() + oob_grid + oob_stats + oob_admin_stats)


@router.delete("/admin/plant/{name}", response_class=HTMLResponse)
def admin_delete_single_plant(name: str):
    """Deletes a single plant from within the admin modal and updates grid & stats."""
    key = db.clean_key(name)
    plant = db.get_plant(key)
    if plant:
        photos = plant.get("photos", [])
        db.delete_plant(key)
        if photos:
            cleanup_plant_photos(photos)

    plants = db.get_plants()
    oob_grid = f'<div id="plant-container" hx-swap-oob="innerHTML">{render_plants_grid(plants)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    inv = db.get_inventory_stats()
    oob_admin_stats = f'<div id="admin-stats-summary" hx-swap-oob="innerHTML">{render_admin_stats_cards(inv)}</div>'
    return HTMLResponse("" + oob_grid + oob_stats + oob_admin_stats)


@router.get("/admin/inventory.csv")
def export_inventory_csv():
    """Exports structured botanical inventory to CSV."""
    plants = db.get_plants()
    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    writer.writerow([
        "KEY", "ALIAS", "ESPECIE", "ESTADO", "UBICACION", "ALTURA_FECHA_CM",
        "LINAJE_PADRES", "FECHA_SIEMBRA_ESQUEJE",
        "INJERTO", "ULTIMA_PODA", "ULTIMO_TRASPLANTE", "FERTILIZANTE",
        "FOTOS_TOTAL", "OBSERVACIONES", "INDXW"
    ])

    for p in plants:
        photos = p.get("photos", [])
        writer.writerow([
            p.get("name", ""),
            p.get("aka", ""),
            p.get("species", ""),
            p.get("status", "OK"),
            p.get("location", ""),
            p.get("height", ""),
            p.get("padres", ""),
            p.get("sowing_cutting_date", ""),
            p.get("graft", ""),
            p.get("last_pruned", ""),
            p.get("last_repotted", ""),
            p.get("fertilizante", ""),
            len(photos),
            p.get("comentarios", "").replace("\n", " "),
            int(p.get("indxw", 0))
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="inventario_botanico_plantation.csv"',
            "Cache-Control": "no-cache"
        }
    )


# ==============================================================================
# PDF EXPORT (ON-DEMAND)
# ==============================================================================

@router.get("/pdf/plant/{name}")
def download_single_plant_pdf(name: str):
    """On-demand single plant PDF dossier generator."""
    plant = db.get_plant(name)
    if not plant:
        raise HTTPException(status_code=404, detail="Ejemplar botánico no encontrado")

    pdf_bytes = generate_single_plant_pdf(plant)
    aka_clean = re.sub(r'[^a-zA-Z0-9_-]', '', plant.get('aka', '') or '')
    filename = f"Plantation_Expediente_{plant.get('name')}_{aka_clean}.pdf" if aka_clean else f"Plantation_Expediente_{plant.get('name')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/pdf/full-catalog")
def download_full_catalog_pdf():
    """Creates complete PDF dossier with index summary and all specimen cards."""
    plants = db.get_plants()
    pdf_bytes = generate_catalog_pdf(plants, title="DOSSIER GENERAL DE EJEMPLARES")
    filename = "Plantation_Dossier_General.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/admin/check-integrity", response_class=HTMLResponse)
def admin_check_integrity():
    """Runs on-demand SQLite PRAGMA integrity_check and returns updated health card."""
    ok, msg = db.check_database_integrity()
    display_msg = "INTEGRIDAD OK (0 anomalías detectadas)" if ok else f"FALLO: {msg}"
    from .templates.admin import render_db_health_card
    return HTMLResponse(render_db_health_card(integrity_result_msg=display_msg))


@router.post("/admin/create-backup", response_class=HTMLResponse)
def admin_create_backup():
    """Forces an immediate online SQLite backup and returns updated health card."""
    bk_path = db.backup_db()
    from .templates.admin import render_db_health_card
    return HTMLResponse(render_db_health_card(integrity_result_msg=f"RESPALDO CREADO ({os.path.basename(bk_path)})"))


@router.get("/admin/backup.db")
def download_database_backup():
    """Generates an instantaneous, non-blocking SQLite snapshot and streams it to the user."""
    backup_file = db.backup_db()
    filename = os.path.basename(backup_file)
    return FileResponse(
        backup_file,
        media_type="application/octet-stream",
        filename=filename,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/admin/archive.zip")
def download_full_archive():
    """Generates an all-in-one ZIP archive containing the SQLite database backup and all registered plant photos."""
    import tempfile
    import zipfile

    backup_file = db.backup_db()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_filename = f"plantation_full_archive_{timestamp}.zip"

    temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    temp_zip_path = temp_zip.name
    temp_zip.close()

    with zipfile.ZipFile(temp_zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(backup_file, arcname="plantation.db")
        if os.path.exists(IMAGES_DIR):
            for img_name in sorted(os.listdir(IMAGES_DIR)):
                img_path = os.path.join(IMAGES_DIR, img_name)
                if os.path.isfile(img_path) and not img_name.startswith("."):
                    zf.write(img_path, arcname=f"Images/{img_name}")

    return FileResponse(
        temp_zip_path,
        media_type="application/zip",
        filename=archive_filename,
        headers={
            "Content-Disposition": f'attachment; filename="{archive_filename}"',
            "Cache-Control": "no-cache"
        }
    )


@router.get("/admin/modal/import-db", response_class=HTMLResponse)
def admin_import_db_modal():
    """Renders the safe SQLite database import and integrity verification modal."""
    return HTMLResponse(render_import_db_modal())


@router.post("/admin/import-db", response_class=HTMLResponse)
async def admin_import_db_action(
    db_file: UploadFile = File(...),
    confirm_replace: Optional[str] = Form(None)
):
    """
    Validates and restores a previously backed-up SQLite database.
    Guarantees integrity check, backward compatibility migrations,
    and automatic safety rollback snapshot.
    """
    if not confirm_replace or confirm_replace.lower() not in ("yes", "1", "true", "on"):
        return HTMLResponse(render_import_db_modal(
            error_msg="Debe marcar la casilla de confirmación para autorizar la sustitución de la base de datos."
        ))

    if not db_file or not db_file.filename:
        return HTMLResponse(render_import_db_modal(
            error_msg="No se seleccionó ningún archivo para importar."
        ))

    # Save to a temporary file
    temp_target = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_path = temp_target.name
    try:
        content = await db_file.read()
        if not content:
            temp_target.close()
            try:
                os.remove(temp_path)
            except OSError:
                pass
            return HTMLResponse(render_import_db_modal(
                error_msg="El archivo subido está vacío (0 bytes)."
            ))

        temp_target.write(content)
        temp_target.close()

        # Validate, auto-migrate, create rollback snapshot, and restore
        success, message, metadata = db.validate_and_restore_db(temp_path)
        if not success:
            return HTMLResponse(render_import_db_modal(error_msg=message))

        # Re-render updated grids and components via OOB
        plants = db.get_plants()
        plants_grid = f'<div id="plant-container" hx-swap-oob="innerHTML">{render_plants_grid(plants)}</div>'
        stats_bar = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'

        inv = db.get_inventory_stats()
        admin_stats = f'<div id="admin-stats-summary" hx-swap-oob="innerHTML">{render_admin_stats_cards(inv)}</div>'
        admin_table = f'<div id="admin-table-container" hx-swap-oob="innerHTML">{render_admin_table_content()}</div>'
        db_card = f'<div id="db-health-card" hx-swap-oob="outerHTML">{render_db_health_card()}</div>'

        modal_success = render_import_db_modal(success_info=metadata)

        return HTMLResponse(modal_success + plants_grid + stats_bar + admin_stats + admin_table + db_card)

    except Exception as e:
        return HTMLResponse(render_import_db_modal(
            error_msg=f"Ocurrió un error inesperado durante la importación: {e}"
        ))
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


# ==============================================================================
# IMAGES, MODAL CLOSE & PRINTABLE DOSSIER
# ==============================================================================

@router.get("/images/{filename}")
def serve_image(filename: str):
    """Serves an optimized image with strict path traversal prevention."""
    clean_name = os.path.basename(filename)
    path = os.path.join(IMAGES_DIR, clean_name)
    if not os.path.exists(path) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    ext = os.path.splitext(clean_name)[1].lower()
    media_map = {
        ".webp": "image/webp",
        ".avif": "image/avif",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg"
    }
    return FileResponse(
        path,
        media_type=media_map.get(ext, "image/jpeg"),
        headers={
            "Cache-Control": "public, max-age=86400",
            "Accept-Ranges": "bytes",
        }
    )


@router.get("/modal/close", response_class=HTMLResponse)
def close_modal():
    """Clears modal drawer."""
    return HTMLResponse("")


@router.get("/plants/{name}/dossier")
def view_printable_dossier(name: str):
    """Redirects to the official single plant PDF dossier generator."""
    plant = db.get_plant(name)
    if not plant:
        raise HTTPException(status_code=404, detail="Ejemplar botánico no encontrado")
    return RedirectResponse(url=f"/pdf/plant/{name}", status_code=302)


@router.get("/plants/{name}/print", response_class=HTMLResponse)
@router.get("/plants/{name}/dossier/html", response_class=HTMLResponse)
def view_printable_dossier_html(name: str):
    """Printable standalone HTML technical dossier."""
    plant = db.get_plant(name)
    if not plant:
        raise HTTPException(status_code=404, detail="Ejemplar botánico no encontrado")
    return HTMLResponse(render_printable_dossier_html(plant))
