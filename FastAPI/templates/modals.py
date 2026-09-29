"""
Plantation - Modal Templates
Consolidates View, Create, and Edit modals, eliminating duplicate form inputs.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH, render_photo_item_html, render_editable_photo_item_html


def render_form_fields(plant: Optional[Dict[str, Any]] = None, is_edit: bool = False) -> str:
    """Consolidated form fields generator for both New and Edit plant modals."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    p = plant or {}
    name_val = p.get("name", "")
    species_val = p.get("species", "")
    if not is_edit and not species_val:
        species_val = "Adenium obesum"
    aka_val = p.get("aka", "")
    loc_val = p.get("location", "")
    status_val = db.normalize_status(p.get("status"))

    def _sanitize_date(val: Optional[str]) -> str:
        if not val:
            return ""
        s = val.strip()
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            return s[:10]
        return ""

    height_val = p.get("height", "")
    if not is_edit and not height_val:
        height_val = f"{now_str} - 0 cm"

    sow_val = _sanitize_date(p.get("sowing_cutting_date"))
    if not is_edit and not sow_val:
        sow_val = now_str

    graft_val = p.get("graft", "")
    padres_val = p.get("padres", "")
    pruned_val = p.get("last_pruned", "")
    repotted_val = p.get("last_repotted", "")
    fert_val = p.get("fertilizante", "")
    comm_val = p.get("comentarios", "")
    indxw_val = int(p.get("indxw", 0))

    existing_keys = db.get_all_keys()
    keys_datalist = "".join([f'<option value="{k}">' for k in existing_keys if k != name_val])

    key_input = f"""
        <input type="text"
               id="inp-name"
               name="name"
               class="form-input"
               value="{name_val}"
               readonly
               style="background: var(--bg-mantle); cursor: not-allowed; color: var(--red-crimson); font-weight: bold;" />
    """ if is_edit else """
        <input type="text"
               id="inp-name"
               name="name"
               class="form-input"
               placeholder="Ej: A1, 900, K7, K-12"
               required
               pattern="[A-Za-z0-9_-]+"
               maxlength="20"
               autocomplete="off"
               hx-get="/plants/validate-key"
               hx-trigger="input changed delay:250ms, blur"
               hx-target="#key-validation-feedback"
               hx-swap="innerHTML" />
        <div id="key-validation-feedback" style="min-height: 18px; margin-top: 4px; font-size: 11px;"></div>
    """

    return f"""
        <input type="hidden" id="inp-indxw" name="indxw" value="{indxw_val}" />
        <datalist id="existing-plant-keys">
            {keys_datalist}
        </datalist>

        <div class="form-grid">
            <div class="form-group">
                <label class="form-label" for="inp-name">IDENTIFICADOR / CLAVE (KEY) *</label>
                {key_input}
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-species">ESPECIE BOTÁNICA / TAXONOMÍA *</label>
                <input type="text"
                       id="inp-species"
                       name="species"
                       class="form-input"
                       value="{species_val}"
                       placeholder="Ej: Ariocarpus kotschoubeyanus"
                       required
                       autocomplete="off" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-aka">ALIAS</label>
                <input type="text"
                       id="inp-aka"
                       name="aka"
                       class="form-input"
                       value="{aka_val}"
                       placeholder="Ej: ocaso, golden, darkRed, clon-A"
                       autocomplete="off" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-location">UBICACIÓN / BANCO / ESTANTE</label>
                <input type="text"
                       id="inp-location"
                       name="location"
                       class="form-input"
                       value="{loc_val}"
                       placeholder="Ej: Invernadero A - Banco 1"
                       autocomplete="off" />
            </div>

            <div class="form-group">
                <label class="form-label">ESTADO SANITARIO & VIGOR *</label>
                <div class="status-radio-group">
                    <label class="status-radio-label">
                        <input type="radio" name="status" value="OK" {'checked' if status_val == 'OK' else ''} />
                        <span class="status-badge status-OK" style="font-size: 11px;">● OK</span>
                    </label>
                    <label class="status-radio-label">
                        <input type="radio" name="status" value="notOK" {'checked' if status_val == 'notOK' else ''} />
                        <span class="status-badge status-notOK" style="font-size: 11px;">● notOK</span>
                    </label>
                </div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-height">ALTURA (FECHA - ALTURA CM)</label>
                <input type="text"
                       id="inp-height"
                       name="height"
                       class="form-input"
                       value="{height_val}"
                       placeholder="Ej: 2026-03-10 - 14.5 cm"
                       autocomplete="off" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-sowing_cutting_date">FECHA SIEMBRA / ESQUEJADO</label>
                <input type="date"
                       id="inp-sowing_cutting_date"
                       name="sowing_cutting_date"
                       class="form-input"
                       value="{sow_val}" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-graft">INJERTO / PORTAINJERTO</label>
                <input type="text"
                       id="inp-graft"
                       name="graft"
                       class="form-input"
                       value="{graft_val}"
                       list="existing-plant-keys"
                       placeholder="Ej: Sin injerto / Myrtillocactus" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-padres">LINAJE / CRUCE (PADRES)</label>
                <input type="text"
                       id="inp-padres"
                       name="padres"
                       class="form-input"
                       value="{padres_val}"
                       list="existing-plant-keys"
                       placeholder="Ej: A1 + 900, Clon silvestre..." />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-last_pruned">ÚLTIMA PODA / LIMPIEZA</label>
                <input type="text"
                       id="inp-last_pruned"
                       name="last_pruned"
                       class="form-input"
                       value="{pruned_val}"
                       placeholder="Ej: 2025-10-15 (Poda de raíces)" />
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-last_repotted">ÚLTIMO TRASPLANTE / SUSTRATO</label>
                <input type="text"
                       id="inp-last_repotted"
                       name="last_repotted"
                       class="form-input"
                       value="{repotted_val}"
                       placeholder="Ej: 2025-02-18 (Pómice 80%)" />
            </div>

            <div class="form-group full">
                <label class="form-label" for="inp-fertilizante">FERTILIZACIÓN, NUTRICIÓN & TRATAMIENTOS APLICADOS</label>
                <textarea id="inp-fertilizante"
                          name="fertilizante"
                          class="form-textarea"
                          rows="2"
                          placeholder="Registra dosis de fertilizante (NPK), quelatos de hierro, acaricidas o tratamientos fúngicos...">{fert_val}</textarea>
            </div>

            <div class="form-group full">
                <label class="form-label" for="inp-comentarios">NOTAS</label>
                <textarea id="inp-comentarios"
                          name="comentarios"
                          class="form-textarea"
                          rows="3"
                          placeholder="Anota periodos de reposo invernal, floración, evolución de costillas, esquejes obtenidos...">{comm_val}</textarea>
            </div>
        </div>
    """


def render_view_plant_modal_content(plant: Dict[str, Any], alert_msg: str = "") -> str:
    """Renders full technical dossier modal content for a plant."""
    status = db.normalize_status(plant.get("status"))
    status_cls = STATUS_BADGE_CLASSES.get(status, "status-OK")
    status_es = STATUS_SPANISH.get(status, status)
    photos = plant.get("photos", [])
    plant_name = plant.get("name", "")
    _, age_detailed = db.calculate_plant_age(plant.get("sowing_cutting_date"), plant.get("graft", ""))

    photo_items = [render_photo_item_html(plant_name, ph, allow_delete=False) for ph in photos]
    photos_html = "".join(photo_items) if photo_items else """
        <div style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 12px 0; text-align: center;">
            No hay fotografías adjuntas para este ejemplar. Para añadir o gestionar fotos, pulsa [EDITAR DATOS].
        </div>
    """

    alert_banner = ""
    if alert_msg:
        alert_banner = f"""
            <div class="alert-box alert-success" style="margin-bottom: 12px; font-size: 12px;">
                ✓ {alert_msg}
            </div>
        """

    aka_val = (plant.get("aka") or "").strip()
    aka_badge = f'<strong style="color: var(--peach-orange); font-weight: 700;">"{aka_val}"</strong>' if aka_val else '<span style="color: var(--text-dim);">—</span>'

    info_fields = [
        ("Alias", aka_val or "—", False),
        ("Altura (Fecha - CM)", plant.get("height") or "—", False),
        ("Edad", age_detailed, False),
        ("Fecha Siembra / Esquejado", plant.get("sowing_cutting_date") or "—", False),
        ("Linaje (Padres)", plant.get("padres") or "Desconocido", False),
        ("Injerto", plant.get("graft") or "Sin injerto (Raíz propia)", False),
        ("Última Poda", plant.get("last_pruned") or "—", False),
        ("Último Trasplante", plant.get("last_repotted") or "—", False),
        ("Fertilización & Tratamientos Aplicados", plant.get("fertilizante") or "Sin tratamientos registrados", True),
        ("Comentarios", plant.get("comentarios") or "Sin observaciones", True),
    ]

    fields_html = "\n".join(
        f"""<div class="form-group{' full' if is_full else ''}">
            <span class="form-label">{lbl}</span>
            <div class="form-input" style="background: var(--bg-mantle); color: var(--info-field-color);{' min-height: 50px; white-space: pre-wrap;' if is_full else ' font-weight: 600;' if lbl in ('Alias', 'Altura (Fecha - CM)', 'Edad') else ''}">{val}</div>
        </div>"""
        for lbl, val, is_full in info_fields
    )

    return f"""
    <div class="modal-overlay" id="plant-dossier-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title">[EXPEDIENTE TÉCNICO: {plant.get('name')}]</span>
                    <span class="status-badge {status_cls}">● {status_es}</span>
                </div>
                <button class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar expediente">✕</button>
            </div>

            <div class="modal-body">
                {alert_banner}

                <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 3px; padding: 12px 14px;">
                    <div style="font-size: 11px; color: var(--red-crimson); font-weight: bold; letter-spacing: 1px;">IDENTIFICADOR & TAXONOMÍA</div>
                    <div style="font-size: 16px; font-style: italic; color: var(--blue-sky); margin: 3px 0 6px 0; word-break: break-word;">
                        {plant.get('species')}
                    </div>
                    <div style="font-size: 12px; color: var(--text-sub); display: flex; gap: 14px; flex-wrap: wrap; align-items: center;">
                        <span>CLAVE: <strong style="color: var(--text-main); font-weight: 700;">[{plant.get('name')}]</strong></span>
                        <span>ALIAS: {aka_badge}</span>
                        <span>UBICACIÓN: <span style="color: var(--text-main); font-weight: 600;">{plant.get('location') or 'Sin registrar'}</span></span>
                    </div>
                </div>

                <div class="form-grid">
                    {fields_html}
                </div>

                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span id="plant-photos-count" class="form-label" style="color: var(--red-crimson);">ARCHIVOS FOTOGRÁFICOS ADJUNTOS ({len(photos)})</span>
                        <span style="font-size: 10.5px; color: var(--text-dim);">Haz clic en cualquier imagen para abrirla en alta resolución</span>
                    </div>

                    <div id="plant-photos-wrapper">
                        <div class="modal-photo-list">
                            {photos_html}
                        </div>
                    </div>
                </div>
            </div>

            <div class="modal-footer-sticky">
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <a class="btn btn-red"
                       href="/pdf/plant/{plant.get('name')}"
                       target="_blank"
                       title="Descargar dossier técnico en PDF">
                        🗎 [DESCARGAR PDF]
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


def render_new_plant_modal() -> str:
    """Renders the New Plant registration modal with unified form fields."""
    return f"""
    <div class="modal-overlay" id="new-plant-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <span class="modal-title">+ [REGISTRO DE NUEVO EJEMPLAR BOTÁNICO]</span>
                <button class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cancelar y cerrar">✕</button>
            </div>

            <form hx-post="/plants"
                  hx-target="#plant-container"
                  hx-swap="innerHTML"
                  hx-encoding="multipart/form-data"
                  class="modal-form-wrapper"
                  id="new-plant-form">
                <div class="modal-body">
                    <div id="new-plant-error-banner" style="display: none; margin-bottom: 14px;"></div>
                    {render_form_fields(is_edit=False)}

                    <div style="margin-top: 16px;">
                        <label class="form-label" style="color: var(--red-crimson);">FOTOGRAFÍAS DEL EJEMPLAR (OPCIONAL)</label>
                        <div class="drop-zone"
                             id="new-drop-zone"
                             ondragover="event.preventDefault(); this.classList.add('drag-active');"
                             ondragleave="this.classList.remove('drag-active');"
                             ondrop="event.preventDefault(); this.classList.remove('drag-active'); if (event.dataTransfer.files && event.dataTransfer.files.length) {{ handleNewPhotosSelected(event.dataTransfer.files); }}"
                             onclick="document.getElementById('new-photos-input').click();">
                            <input type="file"
                                   id="new-photos-input"
                                   name="photos"
                                   multiple
                                   accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/tiff"
                                   style="display:none;"
                                   onclick="event.stopPropagation(); this.value=null;"
                                   onchange="handleNewPhotosSelected(this.files)" />
                            <div class="drop-icon">📷</div>
                            <div class="drop-title">Arrastra fotografías aquí o <span class="drop-link">explora tus archivos</span></div>
                            <div class="drop-subtitle">Formatos: JPG, PNG, WEBP, AVIF, HEIC. Puedes añadir fotos de una en una o en lote.</div>
                            <div id="new-photos-feedback" style="display:none; margin-top: 8px; font-weight: bold; color: var(--green-sage); font-size: 11.5px;"></div>
                        </div>

                        <div id="new-photos-preview-section" style="display: none; margin-top: 14px;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px dashed var(--border-line);">
                                <span id="new-photos-count-badge" class="form-label" style="color: var(--green-sage); margin: 0; font-size: 11px; font-weight: 700;">
                                    ✓ FOTOGRAFÍAS LISTAS PARA SUBIR (0)
                                </span>
                                <button type="button"
                                        onclick="clearAllNewPhotos()"
                                        class="btn btn-sm"
                                        style="padding: 2px 8px; font-size: 10px; color: var(--text-dim);"
                                        title="Quitar todas las fotos seleccionadas">
                                    ✕ Quitar todas
                                </button>
                            </div>
                            <div id="new-photos-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(115px, 1fr)); gap: 10px;">
                            </div>
                        </div>
                    </div>
                </div>

                <div class="modal-footer-sticky">
                    <button type="button"
                            class="btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        [CANCELAR]
                    </button>
                    <button type="submit"
                            id="new-plant-submit-btn"
                            class="btn btn-red"
                            style="font-weight: 700; padding: 8px 24px;">
                        ✓ [GUARDAR EJEMPLAR]
                    </button>
                </div>
            </form>
        </div>
    </div>
    <script>
        var currentNewPhotosDT = new DataTransfer();

        function formatFileSize(bytes) {{
            if (!bytes || bytes <= 0) return '0 B';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }}

        function handleNewPhotosSelected(files) {{
            if (!files || files.length === 0) return;
            // Accumulate photos incrementally, avoiding duplicates by name and size
            for (var i = 0; i < files.length; i++) {{
                var file = files[i];
                var exists = false;
                for (var j = 0; j < currentNewPhotosDT.files.length; j++) {{
                    if (currentNewPhotosDT.files[j].name === file.name && currentNewPhotosDT.files[j].size === file.size) {{
                        exists = true;
                        break;
                    }}
                }}
                if (!exists) {{
                    currentNewPhotosDT.items.add(file);
                }}
            }}
            syncAndRenderNewPhotos();
        }}

        function removeNewPhoto(idx) {{
            var newDT = new DataTransfer();
            for (var i = 0; i < currentNewPhotosDT.files.length; i++) {{
                if (i !== idx) {{
                    newDT.items.add(currentNewPhotosDT.files[i]);
                }}
            }}
            currentNewPhotosDT = newDT;
            syncAndRenderNewPhotos();
        }}

        function clearAllNewPhotos() {{
            currentNewPhotosDT = new DataTransfer();
            syncAndRenderNewPhotos();
        }}

        function syncAndRenderNewPhotos() {{
            var input = document.getElementById('new-photos-input');
            if (input) {{
                input.files = currentNewPhotosDT.files;
            }}

            var feedbackEl = document.getElementById('new-photos-feedback');
            var previewSec = document.getElementById('new-photos-preview-section');
            var countBadge = document.getElementById('new-photos-count-badge');
            var gridEl = document.getElementById('new-photos-grid');

            var count = currentNewPhotosDT.files.length;

            if (count > 0) {{
                if (feedbackEl) {{
                    feedbackEl.style.display = 'block';
                    feedbackEl.textContent = (count === 1) ? '✓ 1 fotografía lista para subir' : ('✓ ' + count + ' fotografías listas para subir');
                }}
                if (previewSec) previewSec.style.display = 'block';
                if (countBadge) countBadge.textContent = '✓ FOTOGRAFÍAS LISTAS PARA SUBIR (' + count + ')';

                if (gridEl) {{
                    gridEl.innerHTML = '';
                    for (var i = 0; i < currentNewPhotosDT.files.length; i++) {{
                        (function(file, index) {{
                            var card = document.createElement('div');
                            card.className = 'preview-thumb-card';
                            card.style.cssText = 'position: relative; background: var(--bg-mantle); border: 1px solid var(--border-line); border-radius: 4px; overflow: hidden; display: flex; flex-direction: column; transition: border-color 0.15s;';
                            card.onmouseover = function() {{ card.style.borderColor = 'var(--accent)'; }};
                            card.onmouseout = function() {{ card.style.borderColor = 'var(--border-line)'; }};

                            var thumbWrap = document.createElement('div');
                            thumbWrap.style.cssText = 'position: relative; width: 100%; aspect-ratio: 1 / 1; background: var(--bg-base); overflow: hidden; display: flex; align-items: center; justify-content: center;';

                            var img = document.createElement('img');
                            img.style.cssText = 'width: 100%; height: 100%; object-fit: cover; display: block;';
                            img.alt = file.name;
                            try {{
                                img.src = URL.createObjectURL(file);
                            }} catch (e) {{
                                img.src = '';
                            }}

                            var removeBtn = document.createElement('button');
                            removeBtn.type = 'button';
                            removeBtn.title = 'Quitar esta fotografía';
                            removeBtn.textContent = '✕';
                            removeBtn.style.cssText = 'position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%; background: rgba(0,0,0,0.75); color: #fff; border: 1px solid var(--border-line); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; z-index: 2; transition: background 0.15s;';
                            removeBtn.onmouseover = function() {{ removeBtn.style.background = 'var(--red-crimson)'; }};
                            removeBtn.onmouseout = function() {{ removeBtn.style.background = 'rgba(0,0,0,0.75)'; }};
                            removeBtn.onclick = function(e) {{
                                e.stopPropagation();
                                removeNewPhoto(index);
                            }};

                            var sizeBadge = document.createElement('span');
                            sizeBadge.style.cssText = 'position: absolute; bottom: 4px; left: 4px; background: rgba(0,0,0,0.75); color: var(--green-sage); font-size: 9.5px; font-weight: 600; padding: 1px 5px; border-radius: 2px; z-index: 2; font-family: var(--font-mono);';
                            sizeBadge.textContent = formatFileSize(file.size);

                            var meta = document.createElement('div');
                            meta.style.cssText = 'padding: 5px 6px; font-size: 10px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-family: var(--font-mono); border-top: 1px solid var(--border-line);';
                            meta.title = file.name;
                            meta.textContent = file.name;

                            thumbWrap.appendChild(img);
                            thumbWrap.appendChild(removeBtn);
                            thumbWrap.appendChild(sizeBadge);
                            card.appendChild(thumbWrap);
                            card.appendChild(meta);

                            gridEl.appendChild(card);
                        }})(currentNewPhotosDT.files[i], i);
                    }}
                }}
            }} else {{
                if (feedbackEl) {{
                    feedbackEl.style.display = 'none';
                    feedbackEl.textContent = '';
                }}
                if (previewSec) previewSec.style.display = 'none';
                if (gridEl) gridEl.innerHTML = '';
            }}
        }}
    </script>
    """


def render_edit_plant_modal(plant: Dict[str, Any]) -> str:
    """Renders the Edit Plant modal using unified form fields and staged photo management."""
    photos = plant.get("photos", [])
    plant_name = plant.get("name", "")
    photo_items = [render_editable_photo_item_html(plant_name, ph, idx) for idx, ph in enumerate(photos)]
    photos_html = "".join(photo_items) if photo_items else """
        <div id="edit-no-photos-msg" style="color: var(--text-dim); font-size: 12px; grid-column: 1 / -1; padding: 10px 0; text-align: center;">
            No hay fotografías adjuntas para este ejemplar. Puede añadir nuevas fotografías abajo.
        </div>
    """

    return f"""
    <div class="modal-overlay" id="edit-plant-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <span class="modal-title">✏ [MODIFICAR DATOS: {plant.get('name')}]</span>
                <button class="modal-close-btn"
                        hx-get="/plants/{plant.get('name')}"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Volver al expediente">✕</button>
            </div>

            <form hx-post="/plants/{plant.get('name')}/edit"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  hx-encoding="multipart/form-data"
                  class="modal-form-wrapper"
                  id="edit-plant-form">
                <div class="modal-body">
                    {render_form_fields(plant=plant, is_edit=True)}

                    <!-- Hidden inputs for staged photo deletions -->
                    <div id="staged-deletions-container"></div>

                    <!-- Unified photo management with staged deletions and staged new additions -->
                    <div style="margin-top: 20px; border-top: 1px dashed var(--border-line); padding-top: 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; flex-wrap: wrap; gap: 8px;">
                            <span id="edit-plant-photos-count" class="form-label" style="color: var(--red-crimson);">
                                GESTIÓN DE FOTOGRAFÍAS ({len(photos)})
                            </span>
                            <span id="edit-deletion-status" style="font-size: 11px; color: var(--peach-orange); font-weight: 600;"></span>
                        </div>
                        <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 10px;">
                            Pulsa ✕ en fotos existentes para marcarlas para eliminar (rojo). Las fotos nuevas añadidas (verde) se anexan aquí. Todos los cambios se aplicarán al pulsar [GUARDAR CAMBIOS].
                        </div>

                        <div id="edit-plant-photos-wrapper">
                            <div class="modal-photo-list" id="edit-plant-photos-list">
                                {photos_html}
                                <div id="edit-staged-new-photos-wrapper" style="display: contents;"></div>
                            </div>
                        </div>

                        <!-- Dropzone for staging new photos into the unified gallery -->
                        <div class="drop-zone"
                             id="edit-drop-zone"
                             style="margin-top: 14px;"
                             ondragover="event.preventDefault(); this.classList.add('drag-active');"
                             ondragleave="this.classList.remove('drag-active');"
                             ondrop="event.preventDefault(); this.classList.remove('drag-active'); if (event.dataTransfer.files && event.dataTransfer.files.length) {{ handleEditNewPhotosSelected(event.dataTransfer.files); }}"
                             onclick="document.getElementById('edit-new-photos-input').click();">
                            <input type="file"
                                   id="edit-new-photos-input"
                                   name="new_photos"
                                   multiple
                                   accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/tiff"
                                   style="display:none;"
                                   onclick="event.stopPropagation(); this.value=null;"
                                   onchange="handleEditNewPhotosSelected(this.files)" />
                            <div class="drop-icon">📷</div>
                            <div class="drop-title">Arrastra nuevas fotografías aquí o <span class="drop-link">explora tus archivos</span></div>
                            <div class="drop-subtitle">Aparecerán inmediatamente en la galería de arriba con distintivo verde tenue, pendientes de guardar.</div>
                            <div id="edit-new-photos-feedback" style="display:none; margin-top: 8px; font-weight: bold; color: var(--green-sage); font-size: 11.5px;"></div>
                        </div>
                    </div>
                </div>

                <div class="modal-footer-sticky">
                    <button type="button"
                            class="btn"
                            hx-get="/plants/{plant.get('name')}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        [VOLVER AL EXPEDIENTE]
                    </button>
                    <button type="submit"
                            id="edit-plant-submit-btn"
                            class="btn btn-red"
                            style="font-weight: 700; padding: 8px 24px;">
                        ✓ [GUARDAR CAMBIOS]
                    </button>
                </div>
            </form>
        </div>
    </div>
    <script>
        var stagedDeletions = new Set();
        var editNewPhotosDT = new DataTransfer();

        function formatFileSize(bytes) {{
            if (!bytes || bytes <= 0) return '0 B';
            if (bytes < 1024) return bytes + ' B';
            if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(0) + ' KB';
            return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
        }}

        function updateDeletionStatusText() {{
            var el = document.getElementById('edit-deletion-status');
            var delCount = stagedDeletions.size;
            var newCount = editNewPhotosDT.files.length;
            var notices = [];
            if (delCount > 0) {{
                notices.push('<span style="color: var(--peach-orange);">🗑 ' + delCount + ' a eliminar</span>');
            }}
            if (newCount > 0) {{
                notices.push('<span style="color: var(--green-sage);">+ ' + newCount + ' nueva(s) añadida(s)</span>');
            }}
            if (el) {{
                el.innerHTML = notices.join(' · ');
            }}
        }}

        function markPhotoForDeletion(photoName, idx) {{
            stagedDeletions.add(photoName);
            var card = document.getElementById('existing-photo-card-' + idx);
            var delBtn = document.getElementById('del-btn-' + idx);
            var undoBox = document.getElementById('undo-container-' + idx);
            var badge = document.getElementById('deletion-badge-' + idx);
            var thumb = document.getElementById('photo-thumb-' + idx);
            var container = document.getElementById('staged-deletions-container');

            if (card) {{
                card.style.borderColor = 'var(--red-crimson)';
                card.style.backgroundColor = 'rgba(224, 75, 75, 0.12)';
            }}
            if (delBtn) delBtn.style.display = 'none';
            if (undoBox) undoBox.style.display = 'block';
            if (badge) badge.style.display = 'block';
            if (thumb) thumb.style.opacity = '0.35';

            if (container && !document.getElementById('del-inp-' + idx)) {{
                var inp = document.createElement('input');
                inp.type = 'hidden';
                inp.name = 'photos_to_delete';
                inp.value = photoName;
                inp.id = 'del-inp-' + idx;
                container.appendChild(inp);
            }}
            updateDeletionStatusText();
        }}

        function unmarkPhotoForDeletion(photoName, idx) {{
            stagedDeletions.delete(photoName);
            var card = document.getElementById('existing-photo-card-' + idx);
            var delBtn = document.getElementById('del-btn-' + idx);
            var undoBox = document.getElementById('undo-container-' + idx);
            var badge = document.getElementById('deletion-badge-' + idx);
            var thumb = document.getElementById('photo-thumb-' + idx);
            var inp = document.getElementById('del-inp-' + idx);

            if (card) {{
                card.style.borderColor = '';
                card.style.backgroundColor = '';
            }}
            if (delBtn) delBtn.style.display = 'flex';
            if (undoBox) undoBox.style.display = 'none';
            if (badge) badge.style.display = 'none';
            if (thumb) thumb.style.opacity = '1';
            if (inp) inp.remove();
            updateDeletionStatusText();
        }}

        function handleEditNewPhotosSelected(files) {{
            if (!files || files.length === 0) return;
            for (var i = 0; i < files.length; i++) {{
                var file = files[i];
                var exists = false;
                for (var j = 0; j < editNewPhotosDT.files.length; j++) {{
                    if (editNewPhotosDT.files[j].name === file.name && editNewPhotosDT.files[j].size === file.size) {{
                        exists = true;
                        break;
                    }}
                }}
                if (!exists) {{
                    editNewPhotosDT.items.add(file);
                }}
            }}
            syncAndRenderEditNewPhotos();
        }}

        function removeEditNewPhoto(idx) {{
            var newDT = new DataTransfer();
            for (var i = 0; i < editNewPhotosDT.files.length; i++) {{
                if (i !== idx) {{
                    newDT.items.add(editNewPhotosDT.files[i]);
                }}
            }}
            editNewPhotosDT = newDT;
            syncAndRenderEditNewPhotos();
        }}

        function clearAllEditNewPhotos() {{
            editNewPhotosDT = new DataTransfer();
            syncAndRenderEditNewPhotos();
        }}

        function syncAndRenderEditNewPhotos() {{
            var input = document.getElementById('edit-new-photos-input');
            if (input) {{
                input.files = editNewPhotosDT.files;
            }}

            var feedbackEl = document.getElementById('edit-new-photos-feedback');
            var wrapper = document.getElementById('edit-staged-new-photos-wrapper');
            var noPhotosMsg = document.getElementById('edit-no-photos-msg');

            var count = editNewPhotosDT.files.length;

            if (noPhotosMsg) {{
                noPhotosMsg.style.display = (count > 0) ? 'none' : 'block';
            }}

            if (feedbackEl) {{
                if (count > 0) {{
                    feedbackEl.style.display = 'block';
                    feedbackEl.textContent = (count === 1)
                        ? '✓ 1 fotografía añadida a la cuadrícula superior (verde tenue, pendiente de guardar)'
                        : ('✓ ' + count + ' fotografías añadidas a la cuadrícula superior (verde tenue, pendientes de guardar)');
                }} else {{
                    feedbackEl.style.display = 'none';
                    feedbackEl.textContent = '';
                }}
            }}

            if (wrapper) {{
                wrapper.innerHTML = '';
                for (var i = 0; i < editNewPhotosDT.files.length; i++) {{
                    (function(file, index) {{
                        var card = document.createElement('div');
                        card.className = 'modal-photo-item staged-new-photo-card';
                        card.id = 'staged-new-photo-' + index;
                        card.style.cssText = 'position: relative; background: rgba(163, 190, 140, 0.12); border: 1px solid var(--green-sage); border-top: 2px solid var(--green-sage); border-radius: 3px; padding: 6px; display: flex; flex-direction: column; gap: 4px; transition: all 0.2s ease;';

                        // Individual remove button
                        var removeBtn = document.createElement('button');
                        removeBtn.type = 'button';
                        removeBtn.className = 'photo-delete-badge';
                        removeBtn.style.cssText = 'position: absolute; top: 4px; right: 4px; z-index: 5; background: rgba(0, 0, 0, 0.85); color: #fff; width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--border-dim); font-size: 11px; cursor: pointer; display: flex; align-items: center; justify-content: center; line-height: 1; transition: background 0.15s;';
                        removeBtn.title = 'Quitar esta nueva fotografía';
                        removeBtn.textContent = '✕';
                        removeBtn.onmouseover = function() {{ removeBtn.style.background = 'var(--red-crimson)'; }};
                        removeBtn.onmouseout = function() {{ removeBtn.style.background = 'rgba(0, 0, 0, 0.85)'; }};
                        removeBtn.onclick = function(e) {{
                            e.stopPropagation();
                            removeEditNewPhoto(index);
                        }};

                        // Thumbnail container with soft dimmed green wash overlay
                        var thumbWrap = document.createElement('div');
                        thumbWrap.style.cssText = 'position: relative; width: 100%; height: 95px; border-radius: 2px; overflow: hidden; background: var(--bg-crust); display: flex; align-items: center; justify-content: center;';

                        var img = document.createElement('img');
                        img.className = 'modal-photo-thumb';
                        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover; display: block;';
                        img.alt = file.name;
                        try {{
                            img.src = URL.createObjectURL(file);
                        }} catch (e) {{
                            img.src = '';
                        }}

                        // Dimmed green overlay wash
                        var greenOverlay = document.createElement('div');
                        greenOverlay.style.cssText = 'position: absolute; inset: 0; background: rgba(163, 190, 140, 0.22); pointer-events: none;';

                        // Staged addition badge
                        var sizeBadge = document.createElement('div');
                        sizeBadge.style.cssText = 'position: absolute; bottom: 4px; left: 4px; right: 4px; background: rgba(15, 35, 20, 0.92); color: var(--green-sage); font-size: 8.5px; font-weight: 700; text-align: center; padding: 2px 4px; border-radius: 2px; text-transform: uppercase; z-index: 4; pointer-events: none; border: 1px solid rgba(163, 190, 140, 0.4); font-family: var(--font-mono); letter-spacing: 0.5px;';
                        sizeBadge.textContent = '+ NUEVA · ' + formatFileSize(file.size);

                        // Filename
                        var meta = document.createElement('div');
                        meta.style.cssText = 'font-size: 10px; color: var(--green-sage); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; font-family: var(--font-mono); font-weight: 600;';
                        meta.title = file.name;
                        meta.textContent = file.name;

                        thumbWrap.appendChild(img);
                        thumbWrap.appendChild(greenOverlay);
                        thumbWrap.appendChild(sizeBadge);
                        card.appendChild(removeBtn);
                        card.appendChild(thumbWrap);
                        card.appendChild(meta);

                        wrapper.appendChild(card);
                    }})(editNewPhotosDT.files[i], i);
                }}
            }}
            updateDeletionStatusText();
        }}
    </script>
    """
