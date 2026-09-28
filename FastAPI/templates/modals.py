"""
Plantation - Modal Templates
Consolidates View, Create, and Edit modals, eliminating duplicate form inputs.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH, render_photo_item_html


def render_form_fields(plant: Optional[Dict[str, Any]] = None, is_edit: bool = False) -> str:
    """Consolidated form fields generator for both New and Edit plant modals."""
    p = plant or {}
    name_val = p.get("name", "")
    species_val = p.get("species", "")
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

    raw_reg = p.get("registration_date")
    reg_val = _sanitize_date(raw_reg) or (datetime.now().strftime("%Y-%m-%d") if not is_edit else "")
    sow_val = _sanitize_date(p.get("sowing_cutting_date"))
    graft_val = p.get("graft", "")
    padres_val = p.get("padres", "")
    pruned_val = p.get("last_pruned", "")
    repotted_val = p.get("last_repotted", "")
    fert_val = p.get("fertilizante", "")
    comm_val = p.get("comentarios", "")

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
               autocomplete="off" />
    """

    return f"""
        <datalist id="existing-plant-keys">
            {keys_datalist}
        </datalist>

        <div class="form-grid">
            <div class="form-group">
                <label class="form-label" for="inp-name">IDENTIFICADOR / CLAVE (KEY) *</label>
                {key_input}
                <div class="form-help">Alfanumérico único (máx 20 caracteres).</div>
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
                <div class="form-help">Nombre botánico en cursiva según normas taxonómicas.</div>
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
                <div class="form-help">Nombre informal o apodo del ejemplar.</div>
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
                <div class="form-help">Localización física en el vivero o invernadero.</div>
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
                <div class="form-help">Vigor general / cuarentena o enfermedad.</div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-registration_date">FECHA DE REGISTRO EN SISTEMA</label>
                <input type="date"
                       id="inp-registration_date"
                       name="registration_date"
                       class="form-input"
                       value="{reg_val}" />
                <div class="form-help">Fecha de incorporación al fichero de Plantation.</div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-sowing_cutting_date">FECHA SIEMBRA / ESQUEJADO</label>
                <input type="date"
                       id="inp-sowing_cutting_date"
                       name="sowing_cutting_date"
                       class="form-input"
                       value="{sow_val}" />
                <div class="form-help">Punto cero para cálculo biológico de edad del ejemplar.</div>
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
                <div class="form-help">Patrón o portainjerto utilizado.</div>
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
                <div class="form-help">Progenitores o procedencia genética.</div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-last_pruned">ÚLTIMA PODA / LIMPIEZA</label>
                <input type="text"
                       id="inp-last_pruned"
                       name="last_pruned"
                       class="form-input"
                       value="{pruned_val}"
                       placeholder="Ej: 2025-10-15 (Poda de raíces)" />
                <div class="form-help">Fecha y descripción del último mantenimiento.</div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-last_repotted">ÚLTIMO TRASPLANTE / SUSTRATO</label>
                <input type="text"
                       id="inp-last_repotted"
                       name="last_repotted"
                       class="form-input"
                       value="{repotted_val}"
                       placeholder="Ej: 2025-02-18 (Pómice 80%)" />
                <div class="form-help">Fecha de mudanza y composición del sustrato.</div>
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
                <label class="form-label" for="inp-comentarios">NOTAS, FLORACIÓN & OBSERVACIONES CLÍNICAS</label>
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

    aka_val = (plant.get("aka") or "").strip()
    aka_badge = f'<strong style="color: var(--peach-orange); font-weight: 700;">"{aka_val}"</strong>' if aka_val else '<span style="color: var(--text-dim);">—</span>'

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
                    <div class="form-group">
                        <span class="form-label">Alias</span>
                        <div class="form-input" style="background: var(--bg-mantle); font-weight: 700; color: var(--peach-orange);">{aka_val or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Fecha de Registro</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('registration_date') or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Edad</span>
                        <div class="form-input" style="background: var(--bg-mantle); font-weight: 600;">{age_detailed}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Fecha Siembra / Esquejado</span>
                        <div class="form-input" style="background: var(--bg-mantle);">{plant.get('sowing_cutting_date') or '—'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Linaje (Padres)</span>
                        <div class="form-input" style="background: var(--bg-mantle); word-break: break-word;">{plant.get('padres') or 'Desconocido'}</div>
                    </div>
                    <div class="form-group">
                        <span class="form-label">Injerto</span>
                        <div class="form-input" style="background: var(--bg-mantle); word-break: break-word;">{plant.get('graft') or 'Sin injerto (Raíz propia)'}</div>
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

                <div>
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="form-label" style="color: var(--red-crimson);">ARCHIVOS FOTOGRÁFICOS ADJUNTOS ({len(photos)})</span>
                        <span style="font-size: 10.5px; color: var(--text-dim);">Formato auto-convertido a AVIF/WebP (&lt;KEY&gt;_&lt;n&gt;)</span>
                    </div>

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
                    {render_form_fields(is_edit=False)}

                    <div style="margin-top: 16px;">
                        <label class="form-label" style="color: var(--red-crimson);">FOTOGRAFÍAS DEL EJEMPLAR (OPCIONAL)</label>
                        <div class="drop-zone"
                             id="new-drop-zone"
                             ondragover="event.preventDefault(); this.classList.add('drag-active');"
                             ondragleave="this.classList.remove('drag-active');"
                             ondrop="event.preventDefault(); this.classList.remove('drag-active'); if (event.dataTransfer.files.length) {{ document.getElementById('new-photos-input').files = event.dataTransfer.files; updateNewPhotosFeedback(event.dataTransfer.files); }}"
                             onclick="document.getElementById('new-photos-input').click();">
                            <input type="file"
                                   id="new-photos-input"
                                   name="photos"
                                   multiple
                                   accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/tiff"
                                   style="display:none;"
                                   onchange="updateNewPhotosFeedback(this.files)" />
                            <div class="drop-icon">📷</div>
                            <div class="drop-title">Arrastra una o varias fotos aquí o <span class="drop-link">explora tus archivos</span></div>
                            <div class="drop-subtitle">Formatos: JPG, PNG, WEBP, AVIF, HEIC. Se optimizarán a &lt;CLAVE&gt;_&lt;n&gt;.</div>
                            <div id="new-photos-feedback" style="display:none; margin-top: 8px; font-weight: bold; color: var(--green-sage); font-size: 11.5px;"></div>
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
                    <button type="submit" class="btn btn-red" style="font-weight: 700; padding: 8px 24px;">
                        ✓ [GUARDAR EJEMPLAR]
                    </button>
                </div>
            </form>
        </div>
    </div>
    <script>
        function updateNewPhotosFeedback(files) {{
            var el = document.getElementById('new-photos-feedback');
            if (!el) return;
            if (files && files.length > 0) {{
                el.style.display = 'block';
                el.textContent = '✓ ' + files.length + ' archivo(s) seleccionado(s) listos para subir';
            }} else {{
                el.style.display = 'none';
            }}
        }}
    </script>
    """


def render_edit_plant_modal(plant: Dict[str, Any]) -> str:
    """Renders the Edit Plant modal using unified form fields."""
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
                  class="modal-form-wrapper"
                  id="edit-plant-form">
                <div class="modal-body">
                    {render_form_fields(plant=plant, is_edit=True)}
                </div>

                <div class="modal-footer-sticky">
                    <button type="button"
                            class="btn"
                            hx-get="/plants/{plant.get('name')}"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        [VOLVER AL EXPEDIENTE]
                    </button>
                    <button type="submit" class="btn btn-red" style="font-weight: 700; padding: 8px 24px;">
                        ✓ [GUARDAR CAMBIOS]
                    </button>
                </div>
            </form>
        </div>
    </div>
    """
