"""
Plantation - FastAPI Router & Controller Engine
Lightweight HTTP endpoints using SQLite, HTMX partial rendering, and modular templates.
"""

import csv
import io
import os
import re
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
    render_edit_plant_modal
)
from .templates.admin import render_admin_panel_content
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

@router.get("/", response_class=HTMLResponse)
def index_view(request: Request):
    """Main application shell."""
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
def validate_key_endpoint(name: str = Query("")):
    """Validates specimen key availability in real-time as the user types."""
    key = db.clean_key(name)
    if not key:
        return HTMLResponse("""
            <script>
                var btn = document.getElementById('new-plant-submit-btn');
                var inp = document.getElementById('inp-name');
                if (btn) btn.disabled = false;
                if (inp) inp.style.borderColor = 'var(--border-dim)';
            </script>
        """)

    existing = db.get_plant(key)
    if existing:
        return HTMLResponse(f"""
            <span style="color: var(--red-crimson); font-weight: 700; display: inline-flex; align-items: center; gap: 4px;">
                ✕ La clave '{key}' ya existe en el registro. Ingrese una clave única.
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
                ✓ Clave '{key}' disponible para registro.
            </span>
            <script>
                var btn = document.getElementById('new-plant-submit-btn');
                var inp = document.getElementById('inp-name');
                if (btn) btn.disabled = false;
                if (inp) inp.style.borderColor = 'var(--green-sage)';
            </script>
        """)


@router.get("/plants/modal/new", response_class=HTMLResponse)
def new_plant_modal():
    """Renders New Plant registration modal."""
    return HTMLResponse(render_new_plant_modal())


@router.get("/plants/{name}", response_class=HTMLResponse)
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

    now_str = datetime.now().strftime("%Y-%m-%d")
    plant_data = {
        "name": key,
        "species": species.strip() or "Adenium obesum",
        "aka": aka.strip(),
        "location": location.strip(),
        "status": status.strip() or "OK",
        "height": height.strip() or f"{now_str} - 0 cm",
        "registration_date": registration_date.strip() or now_str,
        "sowing_cutting_date": sowing_cutting_date.strip() or now_str,
        "graft": graft.strip(),
        "padres": padres.strip(),
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

    # 3. Update plant botanical metadata
    plant_data = {
        "species": species.strip(),
        "aka": aka.strip(),
        "location": location.strip(),
        "status": status.strip(),
        "height": height.strip(),
        "registration_date": registration_date.strip(),
        "sowing_cutting_date": sowing_cutting_date.strip(),
        "graft": graft.strip(),
        "padres": padres.strip(),
        "last_pruned": last_pruned.strip(),
        "last_repotted": last_repotted.strip(),
        "fertilizante": fertilizante.strip(),
        "comentarios": comentarios.strip()
    }
    if indxw is not None:
        plant_data["indxw"] = 1 if indxw.strip() in ("1", "true", "True", "on") else 0

    success, msg = db.update_plant(key, plant_data)
    if not success:
        return HTMLResponse(f"<div class='alert-box alert-error'>{msg}</div>", status_code=400)

    updated_plant = db.get_plant(key)
    if not updated_plant:
        return HTMLResponse("<div class='alert-box alert-error'>Error al recuperar ejemplar.</div>", status_code=500)

    # When saving changes in editar datos, take user back to the main page (close the modal)
    # and update the plant card, stats bar, and admin tray (if open) on the main page via OOB swaps
    close_modal = ""
    oob_card = render_card_html(updated_plant, oob=True)
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'
    oob_admin = get_oob_admin(request)

    return HTMLResponse(close_modal + oob_card + oob_stats + oob_admin)


@router.delete("/plants/{name}", response_class=HTMLResponse)
def delete_plant_endpoint(request: Request, name: str):
    """Deletes a plant and removes its photo files from disk."""
    success, photos = db.delete_plant(name)
    if success and photos:
        cleanup_plant_photos(photos)

    plants = db.get_plants()
    grid_html = render_plants_grid(plants)
    close_modal_oob = '<div id="modal-container" hx-swap-oob="innerHTML"></div>'
    admin_oob = get_oob_admin(request)

    return HTMLResponse(grid_html + close_modal_oob + admin_oob)


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

@router.get("/admin/toggle", response_class=HTMLResponse)
def admin_toggle(request: Request, is_open: Optional[str] = Query(None)):
    """Toggles visibility of the admin tray statelessly based on client request."""
    currently_open = (is_open == "true" or is_open == "1") if is_open is not None else is_admin_open(request)
    if not currently_open:
        resp = HTMLResponse(render_admin_panel_content())
        resp.set_cookie("plantation_admin", "1", max_age=86400, httponly=False)
        return resp
    resp = HTMLResponse("")
    resp.set_cookie("plantation_admin", "0", max_age=86400, httponly=False)
    return resp


@router.get("/admin", response_class=HTMLResponse)
def admin_open():
    """Opens admin panel."""
    resp = HTMLResponse(render_admin_panel_content())
    resp.set_cookie("plantation_admin", "1", max_age=86400, httponly=False)
    return resp


@router.get("/admin/close", response_class=HTMLResponse)
def admin_close():
    """Closes admin panel."""
    resp = HTMLResponse("")
    resp.set_cookie("plantation_admin", "0", max_age=86400, httponly=False)
    return resp


@router.get("/admin/filter", response_class=HTMLResponse)
def admin_filter_tab(tab: str = "ALL"):
    """Filters admin inventory table by category."""
    return HTMLResponse(render_admin_panel_content(filter_tag=tab))


@router.post("/admin/bulk-delete", response_class=HTMLResponse)
def admin_bulk_delete(keys: List[str] = Form([])):
    """Deletes selected specimens and purges their photos from disk."""
    if not keys:
        return HTMLResponse(render_admin_panel_content())

    deleted_count, photos_to_clean = db.bulk_delete_plants(keys)
    if photos_to_clean:
        cleanup_plant_photos(photos_to_clean)

    plants = db.get_plants()
    oob_grid = f'<div id="plant-container" hx-swap-oob="innerHTML">{render_plants_grid(plants)}</div>'
    oob_stats = f'<div id="stats-bar" hx-swap-oob="outerHTML">{render_stats_bar()}</div>'

    return HTMLResponse(render_admin_panel_content() + oob_grid + oob_stats)


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
    pdf_bytes = generate_catalog_pdf(plants, title="CATÁLOGO GENERAL DE EJEMPLARES")
    filename = "Plantation_Catalogo_General.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache"
        }
    )


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
