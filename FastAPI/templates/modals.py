"""
Plantation - Modal Templates
Consolidates View, Create, and Edit modals, eliminating duplicate form inputs.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import html
import json
import db
from .components import STATUS_BADGE_CLASSES, STATUS_SPANISH, render_photo_item_html, render_editable_photo_item_html


def render_form_fields(plant: Optional[Dict[str, Any]] = None, is_edit: bool = False) -> str:
    """Consolidated form fields generator for both New and Edit plant modals."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    plant_data = plant or {}
    name_val = html.escape(str(plant_data.get("name", "")))
    species_val = html.escape(str(plant_data.get("species", "")))
    if not is_edit and not species_val:
        species_val = "Adenium obesum"
    aka_val = html.escape(str(plant_data.get("aka", "")))
    loc_val = html.escape(str(plant_data.get("location", "")))
    status_val = db.normalize_status(plant_data.get("status"))

    def _sanitize_date(val: Optional[str]) -> str:
        if not val:
            return ""
        s = str(val).strip()
        dt = db.parse_plant_date(s)
        if dt:
            return dt.strftime("%Y-%m-%d")
        if len(s) >= 10 and s[4] == '-' and s[7] == '-':
            return s[:10]
        return ""

    height_val = html.escape(str(plant_data.get("height", "")))
    if not is_edit and not height_val:
        height_val = f"0 cm ({now_str})"

    sow_val = _sanitize_date(plant_data.get("sowing_cutting_date"))
    if not is_edit and not sow_val:
        sow_val = now_str

    graft_val = html.escape(str(plant_data.get("graft", "")))
    padres_val = (plant_data.get("padres") or "").strip()
    padre1_raw, padre2_raw = db.split_parents(padres_val)
    padre1_val = html.escape(padre1_raw)
    padre2_val = html.escape(padre2_raw)
    padres_val_esc = html.escape(padres_val)
    pruned_val = html.escape(str(plant_data.get("last_pruned", "")))
    repotted_val = html.escape(str(plant_data.get("last_repotted", "")))
    fert_val = html.escape(str(plant_data.get("fertilizante", "")))
    comm_val = html.escape(str(plant_data.get("comentarios", "")))
    indxw_val = int(plant_data.get("indxw", 0))

    existing_keys = db.get_all_keys()
    plants_list = db.get_plants()
    available_parents = [item for item in plants_list if item.get("name") != plant_data.get("name", "")]
    datalist_items = []
    for parent_item in available_parents:
        p_name = html.escape(str(parent_item.get("name", "")))
        p_spec = html.escape(str(parent_item.get("species", "")))
        p_aka = f" ({html.escape(str(parent_item.get('aka')))})" if parent_item.get("aka") else ""
        datalist_items.append(f'<option value="{p_name}">{p_name} — {p_spec}{p_aka}</option>')
    keys_datalist = "".join(datalist_items)

    def _initial_parent_feedback(k_val: str) -> str:
        clean = (k_val or "").strip()
        if not clean or clean.lower() in ("unknown", "desconocido"):
            return '<span style="color: var(--text-dim); font-size: 11px;">✓ Sin parental seleccionado (default: "unknown")</span>'
        pl = db.get_plant(clean)
        if pl:
            aka = f' ("{html.escape(str(pl.get("aka")))}")' if pl.get("aka") else ""
            return f'<span style="color: var(--green-sage); font-weight: 600; font-size: 11px;">✓ Clave existente: {html.escape(clean)} — {html.escape(str(pl.get("species", "")))}{aka}</span>'
        return f'<span style="color: var(--red-crimson); font-weight: 700; font-size: 11px;">✕ La clave \'{html.escape(clean)}\' no existe en la base de datos.</span>'

    padre1_feedback = _initial_parent_feedback(padre1_raw)
    padre2_feedback = _initial_parent_feedback(padre2_raw)

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
               hx-trigger="input changed delay:500ms, blur"
               hx-target="#key-validation-feedback"
               hx-swap="innerHTML" />
        <div id="key-validation-feedback" style="min-height: 18px; margin-top: 4px; font-size: 11px;"></div>
    """

    reg_date_val = plant_data.get("registration_date") or now_str

    return f"""
        <input type="hidden" id="inp-indxw" name="indxw" value="{indxw_val}" />
        <input type="hidden" id="inp-registration_date" name="registration_date" value="{reg_date_val}" />
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
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <label class="form-label" for="inp-height" style="margin-bottom: 0;">ALTURA (CM)</label>
                    <span style="font-size: 10px; color: var(--text-dim); font-family: var(--font-mono);">(Fecha actual añadida automáticamente)</span>
                </div>
                <input type="text"
                       id="inp-height"
                       name="height"
                       class="form-input"
                       value="{height_val}"
                       placeholder="Ej: 40 cm (o escribe 40)"
                       autocomplete="off"
                       onblur="autoFormatHeightInput(this)" />
                <div style="font-size: 10px; color: var(--text-dim); margin-top: 2px;">
                    Si introduces <strong style="color: var(--teal-accent);">40</strong> se guardará automáticamente como <strong style="color: var(--green-sage);">40 cm ({now_str})</strong>
                </div>
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
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <label class="form-label" for="inp-sowing_cutting_date" style="margin-bottom: 0;">FECHA SIEMBRA / ESQUEJADO</label>
                    <div style="display: flex; gap: 4px;">
                        <button type="button"
                                class="btn-today"
                                onclick="setSowingDateToday();"
                                title="Rellenar con la fecha de hoy ({now_str})">
                            [Hoy]
                        </button>
                        <button type="button"
                                class="btn-today"
                                onclick="clearSowingDate();"
                                style="color: var(--text-dim);"
                                title="Limpiar fecha de siembra (sin fecha / S/D)">
                            [Borrar]
                        </button>
                    </div>
                </div>
                <input type="date"
                       id="inp-sowing_cutting_date"
                       name="sowing_cutting_date"
                       class="form-input"
                       value="{sow_val}"
                       max="2100-12-31"
                       oninput="updateSowingDateAgePreview();"
                       onchange="updateSowingDateAgePreview();" />
                <div id="sowing-age-preview" style="font-size: 10.5px; margin-top: 3px; min-height: 16px;"></div>
            </div>

            <div class="form-group">
                <label class="form-label" for="inp-graft">TIPO (INJERTO, SEMILLA, CUTTING)</label>
                <input type="text"
                       id="inp-graft"
                       name="graft"
                       class="form-input"
                       value="{graft_val}"
                       list="cultivation-type-datalist"
                       placeholder="Ej: Semilla + Injerto, Semilla, Injerto, Cutting" />
                <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-top: 5px;">
                    <button type="button" class="btn-today" onclick="document.getElementById('inp-graft').value='Semilla + Injerto'">Semilla + Injerto</button>
                    <button type="button" class="btn-today" onclick="document.getElementById('inp-graft').value='Semilla'">Semilla</button>
                    <button type="button" class="btn-today" onclick="document.getElementById('inp-graft').value='Injerto'">Injerto</button>
                    <button type="button" class="btn-today" onclick="document.getElementById('inp-graft').value='Cutting'">Cutting</button>
                </div>
            </div>

            <div class="form-group full" style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 12px 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; flex-wrap: wrap; gap: 6px;">
                    <label class="form-label" style="color: var(--teal-accent); margin-bottom: 0; display: flex; align-items: center; gap: 6px;">
                        <span>🧬 LINAJE / CRUCE (CLAVES DE PARENTALES)</span>
                    </label>
                    <span style="font-size: 10px; color: var(--text-dim); font-family: var(--font-mono);">
                        2 claves de la colección • Si no se selecciona, valor por defecto: "unknown"
                    </span>
                </div>

                <div class="lineage-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 14px;">
                    <!-- Progenitor 1 Key -->
                    <div class="form-group" style="margin-bottom: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <label class="form-label" for="inp-padre1" style="font-size: 10px; color: var(--peach-orange); margin-bottom: 0;">
                                CLAVE PROGENITOR 1 (MADRE / SEMILLA)
                            </label>
                            <button type="button"
                                    class="btn-today"
                                    onclick="clearSingleParent(1);"
                                    title="Restablecer a unknown"
                                    style="padding: 1px 6px; font-size: 9px; color: var(--text-dim);">
                                [unknown]
                            </button>
                        </div>
                        <input type="text"
                               id="inp-padre1"
                               name="padre1"
                               class="form-input"
                               value="{padre1_val}"
                               list="existing-plant-keys"
                               placeholder="Ej: A1, 900 (o vacío para unknown)"
                               maxlength="20"
                               autocomplete="off"
                               hx-get="/plants/validate-parent-key?num=1&plant={name_val}"
                               hx-trigger="input changed delay:500ms, blur, change"
                               hx-target="#padre1-validation-feedback"
                               hx-swap="innerHTML"
                               oninput="updateCombinedPadres();" />
                        <div id="padre1-validation-feedback" style="min-height: 18px; margin-top: 4px; font-size: 11px;">
                            {padre1_feedback}
                        </div>
                    </div>

                    <!-- Progenitor 2 Key -->
                    <div class="form-group" style="margin-bottom: 0;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                            <label class="form-label" for="inp-padre2" style="font-size: 10px; color: var(--blue-sky); margin-bottom: 0;">
                                CLAVE PROGENITOR 2 (PADRE / POLEN)
                            </label>
                            <button type="button"
                                    class="btn-today"
                                    onclick="clearSingleParent(2);"
                                    title="Restablecer a unknown"
                                    style="padding: 1px 6px; font-size: 9px; color: var(--text-dim);">
                                [unknown]
                            </button>
                        </div>
                        <input type="text"
                               id="inp-padre2"
                               name="padre2"
                               class="form-input"
                               value="{padre2_val}"
                               list="existing-plant-keys"
                               placeholder="Ej: 900, K-12 (o vacío para unknown)"
                               maxlength="20"
                               autocomplete="off"
                               hx-get="/plants/validate-parent-key?num=2&plant={name_val}"
                               hx-trigger="input changed delay:500ms, blur, change"
                               hx-target="#padre2-validation-feedback"
                               hx-swap="innerHTML"
                               oninput="updateCombinedPadres();" />
                        <div id="padre2-validation-feedback" style="min-height: 18px; margin-top: 4px; font-size: 11px;">
                            {padre2_feedback}
                        </div>
                    </div>
                </div>

                <!-- Hidden combined input for direct form submission -->
                <input type="hidden" id="inp-padres" name="padres" value="{padres_val_esc or 'unknown'}" />

                <div id="padres-preview-box" style="margin-top: 8px; font-size: 11px; font-family: var(--font-mono); color: var(--text-sub); display: flex; align-items: center; justify-content: space-between; border-top: 1px dashed var(--border-dim); padding-top: 6px;">
                    <div style="display: flex; align-items: center; gap: 6px;">
                        <span style="color: var(--text-dim);">FÓRMULA GENÉTICA:</span>
                        <span id="padres-preview-text" style="color: var(--text-main); font-weight: 700;">{padres_val_esc or 'unknown'}</span>
                    </div>
                    <button type="button"
                            class="btn btn-sm"
                            onclick="clearParentsInputs()"
                            style="padding: 1px 8px; font-size: 9.5px; color: var(--text-dim);"
                            title="Restablecer ambos parentales a unknown">
                        ✕ Restablecer a "unknown"
                    </button>
                </div>
            </div>

            <div class="form-group">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <label class="form-label" for="inp-last_pruned" style="margin-bottom: 0;">ÚLTIMA PODA / LIMPIEZA</label>
                    <button type="button"
                            class="btn-today"
                            onclick="setCareFieldToday('inp-last_pruned')"
                            title="Rellenar con la fecha actual ({now_str})">
                        [Hoy]
                    </button>
                </div>
                <input type="text"
                       id="inp-last_pruned"
                       name="last_pruned"
                       class="form-input"
                       value="{pruned_val}"
                       placeholder="Ej: {now_str} (Poda de raíces)"
                       onblur="autoEnsureCareDate(this)"
                       autocomplete="off" />
            </div>

            <div class="form-group">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <label class="form-label" for="inp-last_repotted" style="margin-bottom: 0;">ÚLTIMO TRASPLANTE / SUSTRATO</label>
                    <button type="button"
                            class="btn-today"
                            onclick="setCareFieldToday('inp-last_repotted')"
                            title="Rellenar con la fecha actual ({now_str})">
                        [Hoy]
                    </button>
                </div>
                <input type="text"
                       id="inp-last_repotted"
                       name="last_repotted"
                       class="form-input"
                       value="{repotted_val}"
                       placeholder="Ej: {now_str} (Pómice 80%)"
                       onblur="autoEnsureCareDate(this)"
                       autocomplete="off" />
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

        <script>
            function updateSowingDateAgePreview() {{
                var el = document.getElementById('inp-sowing_cutting_date');
                var preview = document.getElementById('sowing-age-preview');
                if (!el || !preview) return;
                var val = (el.value || '').trim();
                if (!val) {{
                    preview.innerHTML = '<span style="color: var(--text-dim);">Sin fecha (edad indeterminada o S/D)</span>';
                    return;
                }}
                var parts = val.split('-');
                if (parts.length !== 3) {{
                    preview.innerHTML = '<span style="color: var(--peach-orange);">Formato esperado: AAAA-MM-DD</span>';
                    return;
                }}
                var y = parseInt(parts[0], 10);
                var m = parseInt(parts[1], 10);
                var d = parseInt(parts[2], 10);
                if (isNaN(y) || isNaN(m) || isNaN(d)) {{
                    preview.innerHTML = '<span style="color: var(--peach-orange);">Fecha no válida</span>';
                    return;
                }}
                var now = new Date();
                var birth = new Date(y, m - 1, d);
                if (birth > now) {{
                    preview.innerHTML = '<span style="color: var(--peach-orange);">Fecha futura: 0.0 años (0 meses)</span>';
                    return;
                }}
                var diffMonths = (now.getFullYear() - y) * 12 + (now.getMonth() - (m - 1));
                if (now.getDate() < d) diffMonths -= 1;
                if (diffMonths < 0) diffMonths = 0;
                var yearsDec = (diffMonths / 12.0).toFixed(1);
                var yFull = Math.floor(diffMonths / 12);
                var remM = diffMonths % 12;
                var detail = yearsDec + ' años (' + diffMonths + ' meses)';
                if (yFull > 0 && remM > 0) {{
                    detail += ' · ' + yFull + (yFull === 1 ? ' año' : ' años') + ', ' + remM + (remM === 1 ? ' mes' : ' meses');
                }}
                preview.innerHTML = '<span style="color: var(--green-sage); font-weight: 600;">✓ Edad calculada: ' + detail + '</span>';
            }}

            function setSowingDateToday() {{
                var el = document.getElementById('inp-sowing_cutting_date');
                if (el) {{
                    var now = new Date();
                    var pad = function(n) {{ return (n < 10 ? '0' : '') + n; }};
                    var today = now.getFullYear() + '-' + pad(now.getMonth() + 1) + '-' + pad(now.getDate());
                    el.value = today;
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    updateSowingDateAgePreview();
                }}
            }}

            function clearSowingDate() {{
                var el = document.getElementById('inp-sowing_cutting_date');
                if (el) {{
                    el.value = '';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    updateSowingDateAgePreview();
                }}
            }}

            setTimeout(function() {{
                updateSowingDateAgePreview();
                updateCombinedPadres();
            }}, 40);

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
    if photos:
        total_dp = len(photos)
        if total_dp > 1:
            d_slides = "".join(
                f'<div class="dossier-carousel-slide{" active" if i == total_dp - 1 else ""}" data-idx="{i}">'
                f'<a href="/images/{ph}" target="_blank" rel="noopener noreferrer" title="Abrir {ph} en alta resolución">'
                f'<img src="/images/{ph}" alt="{plant_name} - {ph}" />'
                f'</a>'
                f'<div class="dossier-carousel-caption">{ph} ({i + 1} / {total_dp})</div>'
                f'</div>'
                for i, ph in enumerate(photos)
            )
            d_dots = "".join(
                f'<button type="button" class="dossier-carousel-dot{" active" if i == total_dp - 1 else ""}" '
                f'onclick="goToDossierSlide({i});" title="{ph}">'
                f'<img src="/images/{ph}" alt="{ph}" />'
                f'</button>'
                for i, ph in enumerate(photos)
            )
            photos_html = f"""
                <div class="dossier-carousel" id="dossier-carousel" data-current="{total_dp - 1}" data-total="{total_dp}" style="grid-column: 1 / -1;">
                    <div class="dossier-carousel-stage">
                        {d_slides}
                        <button type="button" class="carousel-nav-btn carousel-prev" onclick="stepDossierSlide(-1);" title="Foto anterior">‹</button>
                        <button type="button" class="carousel-nav-btn carousel-next" onclick="stepDossierSlide(1);" title="Foto siguiente">›</button>
                    </div>
                    <div class="dossier-carousel-thumbs">
                        {d_dots}
                    </div>
                </div>
            """
        else:
            photos_html = "".join(photo_items)
    else:
        photos_html = """
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

    aka_val = html.escape((plant.get("aka") or "").strip())
    aka_badge = f'<strong style="color: var(--peach-orange); font-weight: 700;">"{aka_val}"</strong>' if aka_val else '<span style="color: var(--text-dim);">—</span>'

    padres_raw = (plant.get("padres") or "").strip()
    p1, p2 = db.split_parents(padres_raw)
    all_keys = db.get_all_keys()

    def _parent_link(k: str) -> str:
        clean_k = (k or "").strip()
        if not clean_k or clean_k.lower() in ("unknown", "desconocido"):
            return '<span style="color: var(--text-dim); font-style: italic;">unknown</span>'
        esc_k = html.escape(clean_k)
        if clean_k in all_keys:
            return f'<a href="#" hx-get="/plants/{esc_k}" hx-target="#modal-container" hx-swap="innerHTML" class="plant-key" style="color: #ff66cc; text-decoration: underline; font-weight: 700;" title="Abrir expediente del parental {esc_k}">{esc_k}</a>'
        return f'<span style="color: var(--text-main); font-weight: 600;">{esc_k}</span>'

    if p1 and p2:
        padres_display_html = f"{_parent_link(p1)} <span style='color: var(--teal-accent); font-weight: bold;'>×</span> {_parent_link(p2)}"
    elif p1:
        padres_display_html = f"{_parent_link(p1)} <span style='color: var(--teal-accent); font-weight: bold;'>×</span> <span style='color: var(--text-dim); font-style: italic;'>unknown</span>"
    elif p2:
        padres_display_html = f"<span style='color: var(--text-dim); font-style: italic;'>unknown</span> <span style='color: var(--teal-accent); font-weight: bold;'>×</span> {_parent_link(p2)}"
    elif padres_raw and padres_raw.lower() not in ("unknown", "desconocido"):
        padres_display_html = f"<span style='color: var(--text-main);'>{html.escape(padres_raw)}</span>"
    else:
        padres_display_html = '<span style="color: var(--text-dim); font-style: italic;">unknown</span>'

    info_fields = [
        ("Alias", aka_val or "—", False),
        ("Altura (Fecha - CM)", html.escape(str(plant.get("height") or "—")), False),
        ("Edad", html.escape(str(age_detailed)), False),
        ("Fecha Siembra / Esquejado", html.escape(str(plant.get("sowing_cutting_date") or "—")), False),
        ("Linaje (Padres)", padres_display_html, False),
        ("Injerto", html.escape(str(plant.get("graft") or "Sin injerto (Raíz propia)")), False),
        ("Última Poda", html.escape(str(plant.get("last_pruned") or "—")), False),
        ("Último Trasplante", html.escape(str(plant.get("last_repotted") or "—")), False),
        ("Fertilización & Tratamientos Aplicados", html.escape(str(plant.get("fertilizante") or "Sin tratamientos registrados")), True),
        ("Comentarios", html.escape(str(plant.get("comentarios") or "Sin observaciones")), True),
    ]

    fields_html = "\n".join(
        f"""<div class="form-group{' full' if is_full else ''}">
            <span class="form-label">{lbl}</span>
            <div class="form-input" style="background: var(--bg-mantle); color: var(--info-field-color);{' min-height: 50px; white-space: pre-wrap;' if is_full else ' font-weight: 600;' if lbl in ('Alias', 'Altura (Fecha - CM)', 'Edad', 'Linaje (Padres)') else ''}">{val}</div>
        </div>"""
        for lbl, val, is_full in info_fields
    )

    return f"""
    <div class="modal-overlay" id="plant-dossier-modal">
        <div class="modal-dialog">
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title">[KEY: <span class="plant-key" style="color: #ff66cc !important;">{plant.get('name')}</span>]</span>
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
                        <span>CLAVE: <strong class="plant-key" style="color: #ff66cc !important; font-weight: 700;">[{plant.get('name')}]</strong></span>
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
                <span class="modal-title">+ [REGISTRAR NUEVO EJEMPLAR]</span>
                <button type="button"
                        class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar ventana [ESC]"
                        aria-label="Cerrar modal">✕</button>
            </div>
            <form hx-post="/plants"
                  hx-target="#plant-container"
                  hx-swap="innerHTML"
                  hx-encoding="multipart/form-data"
                  class="modal-form-wrapper"
                  id="new-plant-form"
                  onsubmit="autoFormatHeightInput(document.getElementById('inp-height')); updateCombinedPadres();">
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
                <span class="modal-title">✏ [MODIFICAR DATOS: <span class="plant-key" style="color: #ff66cc !important;">{plant.get('name')}</span>]</span>
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
                  id="edit-plant-form"
                  onsubmit="autoFormatHeightInput(document.getElementById('inp-height')); updateCombinedPadres();">
                <div class="modal-body">
                    <div id="edit-plant-error-banner" style="display: none; margin-bottom: 14px;"></div>
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
                    <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                        <button type="button"
                                class="btn"
                                hx-get="/plants/{plant.get('name')}"
                                hx-target="#modal-container"
                                hx-swap="innerHTML">
                            [VOLVER AL EXPEDIENTE]
                        </button>
                        <button type="button"
                                class="btn btn-red"
                                hx-delete="/plants/{plant.get('name')}"
                                hx-target="#plant-container"
                                hx-swap="innerHTML"
                                hx-confirm="¿Eliminar definitivamente el ejemplar '{html.escape(str(plant.get('name', '')))}' y todas sus fotografías?"
                                title="Eliminar definitivamente este ejemplar">
                            🗑 [ELIMINAR]
                        </button>
                    </div>
                    <button type="submit"
                            id="edit-plant-submit-btn"
                            class="btn btn-green"
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


def render_bulk_keys_preview(
    prefix: str = "K",
    count: int = 10,
    start_num: int = 1,
    pad_zeros: Any = 2,
    skip_conflicts: bool = True
) -> str:
    """Renders the real-time visual preview and validation badges for batch key generation."""
    keys = db.generate_bulk_keys(prefix, count, start_num, pad_zeros)
    avail, conf = db.check_keys_availability(keys)

    total_k = len(keys)
    avail_count = len(avail)
    conf_count = len(conf)

    if conf_count == 0:
        banner = f"""
        <div style="background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--green-sage); display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 14px;">✓</span>
            <div><strong>{total_k} claves disponibles:</strong> Ningún conflicto con registros existentes en la base de datos.</div>
        </div>
        """
    else:
        conf_samples = ", ".join(conf[:6]) + ("..." if len(conf) > 6 else "")
        if skip_conflicts:
            banner = f"""
            <div style="background: rgba(234, 179, 8, 0.12); border: 1px solid var(--peach-orange); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--peach-orange); display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 14px;">⚠️</span>
                <div>
                    <strong>{conf_count} clave{'s' if conf_count > 1 else ''} en uso en la BD:</strong> {html.escape(conf_samples)}.<br />
                    <span>Se omitirán los duplicados y se registrarán <strong>{avail_count} nuevos ejemplares</strong> disponibles.</span>
                </div>
            </div>
            """
        else:
            banner = f"""
            <div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson); display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 14px;">✕</span>
                <div>
                    <strong>CONFLICTO DE CLAVES:</strong> Las claves <strong>{html.escape(conf_samples)}</strong> ya están registradas. Marque "Omitir existentes" o cambie el número inicial.
                </div>
            </div>
            """

    chips = []
    conf_set = set(k.lower() for k in conf)
    for k in keys:
        if k.lower() in conf_set:
            chips.append(f"""
            <span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--red-crimson); color: var(--red-crimson); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px; text-decoration: line-through;" title="Ya existe en la base de datos">
                {html.escape(k)} ✕
            </span>
            """)
        else:
            chips.append(f"""
            <span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); color: var(--green-sage); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px;" title="Disponible para registro">
                {html.escape(k)} ✓
            </span>
            """)

    chips_html = "".join(chips) if chips else '<span style="color: var(--text-dim); font-size: 11px;">Indique un prefijo y cantidad válida.</span>'
    submit_disabled = (avail_count == 0 or (conf_count > 0 and not skip_conflicts))

    return f"""
    {banner}
    <div style="font-size: 11px; color: var(--text-dim); margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">
        <span>PREVISUALIZACIÓN DE CLAVES ({total_k} GENERADAS):</span>
        <span style="color: var(--text-main); font-weight: 700;">🟢 {avail_count} DISPONIBLES · 🔴 {conf_count} EN USO</span>
    </div>
    <div style="display: flex; flex-wrap: wrap; gap: 5px; max-height: 110px; overflow-y: auto; background: var(--bg-crust); border: 1px solid var(--border-dim); border-radius: 4px; padding: 8px;">
        {chips_html}
    </div>
    <script>
        (function() {{
            var btn = document.getElementById('bulk-submit-btn');
            if (btn) {{
                btn.disabled = {'true' if submit_disabled else 'false'};
                btn.style.opacity = {'0.5' if submit_disabled else '1'};
                btn.style.cursor = {'not-allowed' if submit_disabled else 'pointer'};
                btn.innerHTML = '➕ CREAR LOTE DE {avail_count} EJEMPLARES';
            }}
        }})();
    </script>
    """


def render_bulk_create_modal() -> str:
    """Renders the comprehensive, intuitive Bulk Specimen Creation modal."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    all_keys = db.get_all_keys()
    existing_keys_json = json.dumps([k.upper() for k in all_keys])
    
    # Existing species and locations
    distinct_species = db.get_distinct_species()
    distinct_locations = db.get_distinct_locations()

    # Datalists
    species_options = "".join(f'<option value="{html.escape(s)}">{html.escape(s)}</option>' for s in distinct_species)
    location_options = "".join(f'<option value="{html.escape(loc)}">{html.escape(loc)}</option>' for loc in distinct_locations)
    
    # Parent datalist
    plants_list = db.get_plants()
    parent_options = "".join(
        f'<option value="{html.escape(str(p.get("name", "")))}">{html.escape(str(p.get("name", "")))} — {html.escape(str(p.get("species", "")))}</option>'
        for p in plants_list
    )

    return f"""
    <div class="modal-overlay" id="bulk-plant-modal" role="dialog" aria-modal="true" style="display: flex;">
        <div class="modal-dialog" style="max-width: 960px; width: 95vw; max-height: 92vh; display: flex; flex-direction: column;">
            
            <!-- MODAL HEADER -->
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title" style="color: var(--green-sage);">
                        🌿 [ALTA MASIVA DE EJEMPLARES // BATCH REGISTRATION]
                    </span>
                    <span style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-dim); background: var(--bg-surface); padding: 2px 8px; border-radius: 2px; border: 1px solid var(--border-dim);">
                        GENERADOR SECUENCIAL & CONDICIONES COMUNES
                    </span>
                </div>
                <button type="button"
                        class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar ventana [ESC]"
                        aria-label="Cerrar modal">
                    ✕
                </button>
            </div>

            <!-- MODAL FORM -->
            <form id="bulk-plant-form"
                  hx-post="/plants/bulk-create"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  hx-indicator="#bulk-submit-spinner"
                  enctype="multipart/form-data"
                  style="display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; overflow: hidden;">

                <input type="hidden" id="bulk-key-mode" name="key_mode" value="seq" />

                <!-- SCROLLABLE BODY -->
                <div class="modal-body" style="padding: 16px 20px 20px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;">
                    
                    <!-- 1. KEY GENERATOR PANEL -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--green-sage); border-radius: 6px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px dashed var(--border-dim); padding-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 12px; font-weight: 700; color: var(--green-sage); letter-spacing: 0.5px;">
                                    ⚙ IDENTIFICADORES Y CLAVES DEL LOTE
                                </span>
                            </div>

                            <!-- Mode Selector Switch -->
                            <div style="display: flex; gap: 4px; background: var(--bg-crust); padding: 2px; border-radius: 4px; border: 1px solid var(--border-dim);">
                                <button type="button"
                                        id="tab-btn-seq"
                                        class="inv-tab-btn active"
                                        onclick="setBulkKeyMode('seq')"
                                        style="font-size: 10.5px; padding: 3px 10px;">
                                    ● GENERADOR SECUENCIAL
                                </button>
                                <button type="button"
                                        id="tab-btn-manual"
                                        class="inv-tab-btn"
                                        onclick="setBulkKeyMode('manual')"
                                        style="font-size: 10.5px; padding: 3px 10px;">
                                    ● LISTA MANUAL / PEGAR CLAVES
                                </button>
                            </div>
                        </div>

                        <!-- Panel: Sequential Mode -->
                        <div id="bulk-seq-panel">
                            <div class="bulk-seq-grid" style="display: grid; grid-template-columns: 1.5fr 1fr 1fr 1.2fr; gap: 12px; margin-bottom: 12px;">
                                
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="bulk-prefix" style="color: var(--text-main);">
                                        PREFIJO / CÓDIGO *
                                    </label>
                                    <input type="text"
                                           id="bulk-prefix"
                                           name="prefix"
                                           class="form-input"
                                           value="K"
                                           placeholder="Ej: K, A, OB-, 2026-"
                                           maxlength="15"
                                           style="text-transform: uppercase; font-weight: 700; color: #ff66cc;"
                                           oninput="this.value = this.value.toUpperCase(); onBulkInputsChanged();"
                                           autocomplete="off" />
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Código base (ej: <code>K</code>, <code>A-</code>)
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="bulk-start" style="color: var(--text-main);">
                                        NÚMERO INICIAL *
                                    </label>
                                    <div style="display: flex; gap: 6px; align-items: stretch;">
                                        <input type="number"
                                               id="bulk-start"
                                               name="start_num"
                                               class="form-input"
                                               value="1"
                                               min="1"
                                               style="flex: 1; min-width: 0;"
                                               oninput="onBulkInputsChanged();" />
                                        <button type="button"
                                                onclick="suggestNextFreeNumber()"
                                                class="btn btn-sm btn-green"
                                                style="height: auto; padding: 0 10px; font-size: 10px; font-weight: 700; white-space: nowrap; flex-shrink: 0;"
                                                title="Calcular el siguiente número libre para este prefijo en la BD">
                                            ⚡ SIGUIENTE
                                        </button>
                                    </div>
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Primer número de secuencia
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="bulk-count" style="color: var(--text-main);">
                                        CANTIDAD (x) *
                                    </label>
                                    <input type="number"
                                           id="bulk-count"
                                           name="count"
                                           class="form-input"
                                           value="10"
                                           min="1"
                                           max="10000"
                                           oninput="onBulkInputsChanged();" />
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Total de plantas a crear (hasta 10.000)
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="bulk-pad-zeros" style="color: var(--text-main);">
                                        FORMATO DE NÚMERO
                                    </label>
                                    <select id="bulk-pad-zeros"
                                            name="pad_zeros"
                                            class="form-input"
                                            onchange="onBulkInputsChanged();">
                                        <option value="0">Sin ceros (K1, K2...)</option>
                                        <option value="2" selected>2 dígitos (K01, K02...)</option>
                                        <option value="3">3 dígitos (K001, K002...)</option>
                                    </select>
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Relleno de ceros
                                    </div>
                                </div>

                            </div>
                        </div>

                        <!-- Panel: Manual Keys List Mode -->
                        <div id="bulk-manual-panel" style="display: none; margin-bottom: 12px;">
                            <label class="form-label" for="bulk-manual-keys" style="color: var(--text-main);">
                                LISTA DE CLAVES INDIVIDUALES (SEPARADAS POR COMA, ESPACIO O SALTO DE LÍNEA)
                            </label>
                            <textarea id="bulk-manual-keys"
                                      name="manual_keys"
                                      class="form-textarea"
                                      style="height: 65px; font-family: var(--font-mono); font-size: 12px;"
                                      placeholder="Ej: K-20, K-21, K-22, K-25, A10, A11"
                                      oninput="onBulkInputsChanged();"></textarea>
                            <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                Pegue las etiquetas o códigos exactos de las macetas.
                            </div>
                        </div>

                        <!-- Conflict Behavior Toggle -->
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; font-size: 11.5px; flex-wrap: wrap; gap: 8px;">
                            <label style="display: inline-flex; align-items: center; gap: 6px; cursor: pointer; color: var(--peach-orange);">
                                <input type="checkbox"
                                       id="bulk-skip-conflicts"
                                       name="skip_conflicts"
                                       value="1"
                                       checked
                                       onchange="onBulkInputsChanged();" />
                                <span>Omitir claves que ya existan en la BD (crear solo las disponibles)</span>
                            </label>
                            <span id="bulk-quick-hint" style="font-size: 11px; color: var(--text-dim);">
                                Cálculo y validación en tiempo real (0ms)
                            </span>
                        </div>

                        <!-- Dynamic Visual Keys Preview Container -->
                        <div id="bulk-keys-preview-container">
                            <!-- Populated instantly by JavaScript -->
                        </div>

                    </div>

                    <!-- 2. COMMON METADATA & CONDITIONS FORM -->
                    <datalist id="bulk-species-datalist">{species_options}</datalist>
                    <datalist id="bulk-locations-datalist">{location_options}</datalist>
                    <datalist id="bulk-parent-keys-datalist">{parent_options}</datalist>
                    <datalist id="cultivation-type-datalist">
                        <option value="Semilla + Injerto">
                        <option value="Semilla">
                        <option value="Injerto">
                        <option value="Cutting">
                        <option value="Pie franco">
                    </datalist>

                    <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 6px; padding: 14px 16px;">
                        <div style="font-size: 12px; font-weight: 700; color: var(--blue-sky); margin-bottom: 12px; border-bottom: 1px dashed var(--border-dim); padding-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <span>🌱 DATOS BOTÁNICOS & CONDICIONES COMUNES PARA EL LOTE</span>
                            <span style="font-size: 10.5px; color: var(--text-dim); font-weight: normal;">* Campos recomendados</span>
                        </div>

                        <div class="form-grid">
                            
                            <!-- Species Input with quick click suggestions -->
                            <div class="form-group full">
                                <label class="form-label" for="bulk-species">ESPECIE BOTÁNICA / TAXONOMÍA *</label>
                                <input type="text"
                                       id="bulk-species"
                                       name="species"
                                       class="form-input"
                                       value="Adenium obesum"
                                       list="bulk-species-datalist"
                                       placeholder="Ej: Ariocarpus retusus, Adenium obesum, Astrophytum asterias"
                                       required
                                       autocomplete="off" />
                                <div style="display: flex; gap: 6px; flex-wrap: wrap; margin-top: 5px; align-items: center;">
                                    <span style="font-size: 10px; color: var(--text-dim);">Sugerencias rápidas:</span>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-species').value='Adenium obesum'">Adenium obesum</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-species').value='Ariocarpus retusus'">Ariocarpus retusus</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-species').value='Astrophytum asterias'">Astrophytum asterias</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-species').value='Lophophora williamsii'">Lophophora williamsii</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-species').value='Copiapoa cinerea'">Copiapoa cinerea</button>
                                </div>
                            </div>

                            <!-- Alias (Exact Botanical Alias) -->
                            <div class="form-group">
                                <label class="form-label" for="bulk-aka">ALIAS (OPCIONAL)</label>
                                <input type="text"
                                       id="bulk-aka"
                                       name="aka"
                                       class="form-input"
                                       placeholder="alias.."
                                       autocomplete="off" />
                                <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                    Alias botánico idéntico para todos los ejemplares del lote (sin numeración secuencial).
                                </div>
                            </div>

                            <!-- Location -->
                            <div class="form-group">
                                <label class="form-label" for="bulk-location">UBICACIÓN / BANCO / ESTANTE</label>
                                <input type="text"
                                       id="bulk-location"
                                       name="location"
                                       class="form-input"
                                       list="bulk-locations-datalist"
                                       placeholder="Ej: Invernadero A - Banco 1"
                                       autocomplete="off" />
                            </div>

                            <!-- Sanitary Status -->
                            <div class="form-group">
                                <label class="form-label">ESTADO SANITARIO & VIGOR *</label>
                                <div class="status-radio-group">
                                    <label class="status-radio-label">
                                        <input type="radio" name="status" value="OK" checked />
                                        <span class="status-badge status-OK" style="font-size: 11px;">● Ok (Saludable)</span>
                                    </label>
                                    <label class="status-radio-label">
                                        <input type="radio" name="status" value="notOK" />
                                        <span class="status-badge status-notOK" style="font-size: 11px;">● notOK (Cuarentena)</span>
                                    </label>
                                </div>
                            </div>

                            <!-- Cultivation Type / Graft -->
                            <div class="form-group">
                                <label class="form-label" for="bulk-graft">TIPO (INJERTO, SEMILLA, CUTTING)</label>
                                <input type="text"
                                       id="bulk-graft"
                                       name="graft"
                                       class="form-input"
                                       value="Semilla + Injerto"
                                       list="cultivation-type-datalist"
                                       placeholder="Ej: Semilla + Injerto" />
                                <div style="display: flex; gap: 5px; flex-wrap: wrap; margin-top: 5px;">
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-graft').value='Semilla + Injerto'">Semilla + Injerto</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-graft').value='Semilla'">Semilla</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-graft').value='Injerto'">Injerto</button>
                                    <button type="button" class="btn-today" onclick="document.getElementById('bulk-graft').value='Cutting'">Cutting</button>
                                </div>
                            </div>

                            <!-- Dates: Sowing / Cutting -->
                            <div class="form-group">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <label class="form-label" for="bulk-sow">FECHA SIEMBRA / ESQUEJE</label>
                                    <button type="button"
                                            class="btn-today"
                                            onclick="document.getElementById('bulk-sow').value = '{now_str}'">
                                        [HOY]
                                    </button>
                                </div>
                                <input type="date"
                                       id="bulk-sow"
                                       name="sowing_cutting_date"
                                       class="form-input"
                                       value="{now_str}" />
                            </div>

                            <!-- Initial Height -->
                            <div class="form-group">
                                <label class="form-label" for="bulk-height">ALTURA INICIAL REGISTRADA</label>
                                <input type="text"
                                       id="bulk-height"
                                       name="height"
                                       class="form-input"
                                       value="0 cm ({now_str})"
                                       placeholder="Ej: 5 cm ({now_str})" />
                            </div>

                            <!-- Parents / Lineage -->
                            <div class="form-group full">
                                <label class="form-label">PROGENITORES / LINAJE (MADRE & PADRE)</label>
                                <div class="lineage-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                                    <div>
                                        <input type="text"
                                               id="bulk-padre1"
                                               name="padre1"
                                               class="form-input"
                                               list="bulk-parent-keys-datalist"
                                               placeholder="Madre (o unknown)" />
                                        <div style="font-size: 9.5px; color: var(--text-dim); margin-top: 2px;">Progenitor 1 (Clave o unknown)</div>
                                    </div>
                                    <div>
                                        <input type="text"
                                               id="bulk-padre2"
                                               name="padre2"
                                               class="form-input"
                                               list="bulk-parent-keys-datalist"
                                               placeholder="Padre (o unknown)" />
                                        <div style="font-size: 9.5px; color: var(--text-dim); margin-top: 2px;">Progenitor 2 (Clave o unknown)</div>
                                    </div>
                                </div>
                            </div>

                            <!-- Treatments and Observations -->
                            <div class="form-group">
                                <label class="form-label" for="bulk-fert">FERTILIZACIÓN & TRATAMIENTOS</label>
                                <textarea id="bulk-fert"
                                          name="fertilizante"
                                          class="form-textarea"
                                          style="height: 52px;"
                                          placeholder="Pauta de nutrición o abono para el lote..."></textarea>
                            </div>

                            <div class="form-group">
                                <label class="form-label" for="bulk-comm">OBSERVACIONES & NOTAS</label>
                                <textarea id="bulk-comm"
                                          name="comentarios"
                                          class="form-textarea"
                                          style="height: 52px;"
                                          placeholder="Observaciones de cultivo, número de bandeja..."></textarea>
                            </div>

                            <!-- Optional Shared Photo -->
                            <div class="form-group full" style="margin-top: 4px; margin-bottom: 0;">
                                <label class="form-label" for="bulk-photo">FOTOGRAFÍA COMPARTIDA PARA EL LOTE (OPCIONAL)</label>
                                <input type="file"
                                       id="bulk-photo"
                                       name="bulk_photo"
                                       class="form-input"
                                       accept="image/jpeg,image/png,image/webp,image/avif,image/heic,image/heif" />
                                <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                    Si adjunta una foto, se guardará y asignará automáticamente como registro inicial de cada ejemplar del lote.
                                </div>
                            </div>

                        </div>
                    </div>

                </div>

                <!-- STICKY FOOTER ACTIONS -->
                <div class="modal-footer-sticky" style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button type="button"
                                class="btn"
                                hx-get="/modal/close"
                                hx-target="#modal-container"
                                hx-swap="innerHTML">
                            CANCELAR [ESC]
                        </button>
                        <span id="bulk-submit-spinner" class="htmx-indicator" style="color: var(--green-sage); font-size: 11.5px; font-weight: bold;">
                            ⏳ [REGISTRANDO LOTE EN BASE DE DATOS...]
                        </span>
                    </div>

                    <button type="submit"
                            id="bulk-submit-btn"
                            class="btn btn-green"
                            style="font-weight: 700; padding: 9px 24px; font-size: 12.5px;">
                        ➕ CREAR LOTE DE 10 EJEMPLARES
                    </button>
                </div>

            </form>
        </div>
    </div>

    <!-- CLIENT-SIDE FAST BATCH GENERATOR SCRIPT -->
    <script>
        window.EXISTING_PLANT_KEYS = new Set({existing_keys_json});

        function setBulkKeyMode(mode) {{
            var hid = document.getElementById('bulk-key-mode');
            var pSeq = document.getElementById('bulk-seq-panel');
            var pMan = document.getElementById('bulk-manual-panel');
            var bSeq = document.getElementById('tab-btn-seq');
            var bMan = document.getElementById('tab-btn-manual');
            if (hid) hid.value = mode;

            if (mode === 'manual') {{
                if (pSeq) pSeq.style.display = 'none';
                if (pMan) pMan.style.display = 'block';
                if (bSeq) bSeq.classList.remove('active');
                if (bMan) bMan.classList.add('active');
            }} else {{
                if (pSeq) pSeq.style.display = 'block';
                if (pMan) pMan.style.display = 'none';
                if (bSeq) bSeq.classList.add('active');
                if (bMan) bMan.classList.remove('active');
            }}
            onBulkInputsChanged();
        }}

        function suggestNextFreeNumber() {{
            var pfxEl = document.getElementById('bulk-prefix');
            var startEl = document.getElementById('bulk-start');
            if (!pfxEl || !startEl) return;
            var pfx = (pfxEl.value || '').trim().toUpperCase();
            var maxNum = 0;
            var reg = new RegExp('^' + pfx.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&') + '[-_]?(\\\\d+)$', 'i');
            window.EXISTING_PLANT_KEYS.forEach(function(k) {{
                var m = k.match(reg);
                if (m) {{
                    var n = parseInt(m[1], 10);
                    if (!isNaN(n) && n > maxNum) maxNum = n;
                }}
            }});
            startEl.value = String(maxNum + 1);
            onBulkInputsChanged();
        }}

        function onBulkInputsChanged() {{
            var mode = document.getElementById('bulk-key-mode')?.value || 'seq';
            var skipEl = document.getElementById('bulk-skip-conflicts');
            var skipConflicts = skipEl ? skipEl.checked : true;
            var generatedKeys = [];

            if (mode === 'manual') {{
                var manText = document.getElementById('bulk-manual-keys')?.value || '';
                var parts = manText.split(/[,\\n\\s]+/);
                parts.forEach(function(p) {{
                    var clean = p.replace(/[^a-zA-Z0-9_-]/g, '').toUpperCase().trim();
                    if (clean && generatedKeys.indexOf(clean) === -1) {{
                        generatedKeys.push(clean);
                    }}
                }});
            }} else {{
                var pfx = (document.getElementById('bulk-prefix')?.value || '').trim().replace(/[^a-zA-Z0-9_-]/g, '').toUpperCase();
                var startNum = parseInt(document.getElementById('bulk-start')?.value || '1', 10);
                if (isNaN(startNum) || startNum < 1) startNum = 1;
                var count = parseInt(document.getElementById('bulk-count')?.value || '10', 10);
                if (isNaN(count) || count < 1) count = 1;
                if (count > 10000) count = 10000;
                var padMode = parseInt(document.getElementById('bulk-pad-zeros')?.value || '2', 10);

                for (var i = startNum; i < startNum + count; i++) {{
                    var sNum = String(i);
                    if (padMode === 2 && sNum.length < 2) sNum = '0' + sNum;
                    else if (padMode === 3) {{
                        while (sNum.length < 3) sNum = '0' + sNum;
                    }}
                    generatedKeys.push(pfx + sNum);
                }}
            }}

            var avail = [];
            var conf = [];
            generatedKeys.forEach(function(k) {{
                if (window.EXISTING_PLANT_KEYS.has(k)) {{
                    conf.push(k);
                }} else {{
                    avail.push(k);
                }}
            }});

            var total = generatedKeys.length;
            var totalAvail = avail.length;
            var totalConf = conf.length;

            // Render Preview DOM
            var container = document.getElementById('bulk-keys-preview-container');
            if (container) {{
                var bannerHtml = '';
                if (total === 0) {{
                    bannerHtml = '<div style="color: var(--text-dim); font-size: 11px;">Indique un prefijo o ingrese claves manuales.</div>';
                }} else if (totalConf === 0) {{
                    bannerHtml = '<div style="background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--green-sage); display: flex; align-items: center; gap: 8px;"><span>✓</span><div><strong>' + total.toLocaleString() + ' claves listas y disponibles:</strong> Cero conflictos en la BD.</div></div>';
                }} else if (skipConflicts) {{
                    bannerHtml = '<div style="background: rgba(234, 179, 8, 0.12); border: 1px solid var(--peach-orange); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--peach-orange); display: flex; align-items: center; gap: 8px;"><span>⚠️</span><div><strong>' + totalConf.toLocaleString() + ' clave(s) en uso:</strong> Se registrarán solo las <strong>' + totalAvail.toLocaleString() + ' claves disponibles</strong> (omitiendo existentes).</div></div>';
                }} else {{
                    bannerHtml = '<div style="background: rgba(239, 68, 68, 0.14); border: 1px solid var(--red-crimson); border-radius: 4px; padding: 7px 12px; margin-bottom: 8px; font-size: 11.5px; color: var(--red-crimson); display: flex; align-items: center; gap: 8px;"><span>✕</span><div><strong>CONFLICTO:</strong> ' + totalConf.toLocaleString() + ' clave(s) ya existen. Marque "Omitir existentes" o cambie el número inicial.</div></div>';
                }}

                var chipsHtml = '';
                var confSet = new Set(conf);
                var maxRender = 60;
                var hasTruncation = (generatedKeys.length > maxRender);
                var renderList = hasTruncation ? generatedKeys.slice(0, 50) : generatedKeys;

                renderList.forEach(function(k) {{
                    if (confSet.has(k)) {{
                        chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--red-crimson); color: var(--red-crimson); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px; text-decoration: line-through;" title="Ya existe en la BD">' + k + ' ✕</span> ';
                    }} else {{
                        chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); color: var(--green-sage); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px;" title="Disponible para registro">' + k + ' ✓</span> ';
                    }}
                }});

                if (hasTruncation) {{
                    chipsHtml += '<span style="color: var(--peach-orange); font-size: 11px; padding: 2px 6px; font-weight: 600; align-self: center;">... y ' + (generatedKeys.length - 60).toLocaleString() + ' claves más en secuencia ...</span> ';
                    generatedKeys.slice(-10).forEach(function(k) {{
                        if (confSet.has(k)) {{
                            chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--red-crimson); color: var(--red-crimson); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px; text-decoration: line-through;" title="Ya existe en la BD">' + k + ' ✕</span> ';
                        }} else {{
                            chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 3px; background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); color: var(--green-sage); font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; padding: 2px 7px; border-radius: 3px;" title="Disponible para registro">' + k + ' ✓</span> ';
                        }}
                    }});
                }}

                container.innerHTML = bannerHtml +
                    '<div style="font-size: 11px; color: var(--text-dim); margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;">' +
                    '<span>PREVISUALIZACIÓN DE CLAVES (' + total.toLocaleString() + '):</span>' +
                    '<span style="color: var(--text-main); font-weight: 700;">🟢 ' + totalAvail.toLocaleString() + ' DISPONIBLES · 🔴 ' + totalConf.toLocaleString() + ' EN USO</span>' +
                    '</div>' +
                    '<div style="display: flex; flex-wrap: wrap; gap: 5px; max-height: 110px; overflow-y: auto; background: var(--bg-crust); border: 1px solid var(--border-dim); border-radius: 4px; padding: 8px;">' +
                    (chipsHtml || '<span style="color: var(--text-dim); font-size: 11px;">Indique claves válidas.</span>') +
                    '</div>';
            }}

            var submitBtn = document.getElementById('bulk-submit-btn');
            if (submitBtn) {{
                var countToCreate = skipConflicts ? totalAvail : (totalConf > 0 ? 0 : total);
                var isBlocked = (countToCreate === 0);
                submitBtn.disabled = isBlocked;
                submitBtn.style.opacity = isBlocked ? '0.45' : '1';
                submitBtn.style.cursor = isBlocked ? 'not-allowed' : 'pointer';
                submitBtn.innerHTML = '➕ CREAR LOTE DE ' + countToCreate.toLocaleString() + ' EJEMPLARES';
            }}
        }}

        // Run initial calculation right away
        setTimeout(onBulkInputsChanged, 30);
    </script>
    """


def render_bulk_create_success_modal(
    created_count: int,
    created_keys: List[str],
    conflicts: List[str],
    species: str,
    graft: str,
    aka: str = "",
    photos_count: int = 0
) -> str:
    """Renders an intuitive, crystal-clear completion modal when batch creation finishes."""
    key_range_str = ""
    if created_keys:
        if len(created_keys) == 1:
            key_range_str = created_keys[0]
        else:
            key_range_str = f"{created_keys[0]} ... {created_keys[-1]} ({len(created_keys)} ejemplares)"

    sample_chips = "".join(
        f'<span style="background: rgba(34, 197, 94, 0.12); border: 1px solid var(--green-sage); color: var(--green-sage); font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 3px;">{k}</span> '
        for k in created_keys[:30]
    )
    if len(created_keys) > 30:
        sample_chips += f'<span style="color: var(--text-dim); font-size: 11px; align-self: center;">... y {len(created_keys) - 30} más</span>'

    conflicts_banner = ""
    if conflicts:
        conflicts_banner = f"""
        <div style="background: rgba(234, 179, 8, 0.12); border: 1px solid var(--peach-orange); border-radius: 4px; padding: 8px 12px; margin-top: 10px; font-size: 11.5px; color: var(--peach-orange);">
            ⚠️ <strong>Se omitieron {len(conflicts)} claves existentes</strong> que ya se encontraban en el catálogo.
        </div>
        """

    photo_note = ""
    if photos_count > 0:
        photo_note = f"""
        <div style="display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--blue-sky); margin-top: 6px;">
            <span>📸</span>
            <span>Fotografía compartida procesada una sola vez en memoria y vinculada a los {photos_count} ejemplares del lote.</span>
        </div>
        """

    aka_display = f'<span style="color: var(--peach-orange); font-weight: 600;">{html.escape(aka)}</span>' if aka else '<span style="color: var(--text-dim); font-style: italic;">Sin alias</span>'

    return f"""
    <div class="modal-overlay" id="bulk-plant-success-modal" role="dialog" aria-modal="true" style="display: flex;">
        <div class="modal-dialog" style="max-width: 680px; width: 95vw; display: flex; flex-direction: column;">
            
            <!-- HEADER -->
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="modal-title" style="color: var(--green-sage);">
                        🌿 [ALTA MASIVA COMPLETADA CON ÉXITO]
                    </span>
                </div>
                <button type="button"
                        class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar ventana [ESC]"
                        aria-label="Cerrar modal">
                    ✕
                </button>
            </div>

            <!-- BODY -->
            <div class="modal-body" style="padding: 24px; display: flex; flex-direction: column; gap: 16px;">
                
                <!-- SUCCESS HIGHLIGHT BOX -->
                <div style="background: rgba(166, 227, 161, 0.12); border: 1px solid var(--green-sage); border-radius: 6px; padding: 16px; display: flex; flex-direction: column; gap: 6px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-size: 16px; font-weight: 700; color: var(--green-sage);">
                            ✓ {created_count} Ejemplares Registrados
                        </span>
                        <span style="font-size: 12px; font-family: var(--font-mono); color: var(--text-main); background: var(--bg-surface); padding: 3px 8px; border-radius: 3px; border: 1px solid var(--border-dim);">
                            {key_range_str}
                        </span>
                    </div>
                    <div style="font-size: 12.5px; color: var(--text-main); line-height: 1.4; margin-top: 4px;">
                        Los nuevos ejemplares han sido indexados en la base de datos y ya se encuentran visibles en el catálogo general y en las estadísticas.
                    </div>
                    {photo_note}
                    {conflicts_banner}
                </div>

                <!-- BATCH DETAILS GRID -->
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 12px;">
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px 12px;">
                        <div style="font-size: 10px; color: var(--text-dim); text-transform: uppercase;">Especie botánica:</div>
                        <div style="font-weight: 600; color: var(--text-main); font-style: italic;">{html.escape(species)}</div>
                    </div>
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px 12px;">
                        <div style="font-size: 10px; color: var(--text-dim); text-transform: uppercase;">Tipo de cultivo:</div>
                        <div style="font-weight: 600; color: var(--blue-sky);">{html.escape(graft or 'Semilla + Injerto')}</div>
                    </div>
                    <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px 12px; grid-column: span 2;">
                        <div style="font-size: 10px; color: var(--text-dim); text-transform: uppercase;">Alias botánico asignado:</div>
                        <div>{aka_display}</div>
                    </div>
                </div>

                <!-- KEYS PREVIEW CHIPS -->
                <div>
                    <div style="font-size: 11px; font-weight: 700; color: var(--text-dim); text-transform: uppercase; margin-bottom: 6px;">
                        Claves generadas ({created_count}):
                    </div>
                    <div style="display: flex; flex-wrap: wrap; gap: 5px; max-height: 120px; overflow-y: auto; background: var(--bg-crust); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px;">
                        {sample_chips}
                    </div>
                </div>

            </div>

            <!-- FOOTER -->
            <div class="modal-footer-sticky" style="display: flex; justify-content: space-between; align-items: center;">
                <button type="button"
                        class="btn btn-green"
                        hx-get="/plants/modal/bulk-new"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        style="font-weight: 700;">
                    ➕ REGISTRAR OTRO LOTE
                </button>

                <div style="display: flex; gap: 8px;">
                    <button type="button"
                            class="btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        ✕ VER CATÁLOGO Y CERRAR [ESC]
                    </button>
                </div>
            </div>

        </div>
    </div>
    """


def render_bulk_delete_modal() -> str:
    """Renders the comprehensive Bulk Specimen Removal and Photo Purge modal."""
    all_plants = db.get_plants()
    plants_summary = [
        {
            "name": p["name"],
            "species": p.get("species", ""),
            "aka": p.get("aka", ""),
            "status": db.normalize_status(p.get("status")),
            "location": p.get("location", "") or "",
            "photos_count": len(p.get("photos") or [])
        }
        for p in all_plants
    ]
    plants_json = json.dumps(plants_summary)
    distinct_locations = db.get_distinct_locations()
    loc_options = "".join(f'<option value="{html.escape(l)}">{html.escape(l)}</option>' for l in distinct_locations)

    return f"""
    <div class="modal-overlay" id="bulk-delete-modal" role="dialog" aria-modal="true" style="display: flex;">
        <div class="modal-dialog" style="max-width: 960px; width: 95vw; max-height: 92vh; display: flex; flex-direction: column;">
            
            <!-- MODAL HEADER -->
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px; flex-wrap: wrap;">
                    <span class="modal-title" style="color: var(--red-crimson);">
                        🗑 [BAJA MASIVA DE EJEMPLARES // BATCH REMOVAL]
                    </span>
                    <span style="font-size: 10.5px; font-family: var(--font-mono); color: var(--text-dim); background: var(--bg-surface); padding: 2px 8px; border-radius: 2px; border: 1px solid var(--border-dim);">
                        PURGA SELECTIVA & ELIMINACIÓN DE ARCHIVOS
                    </span>
                </div>
                <button type="button"
                        class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar ventana [ESC]"
                        aria-label="Cerrar modal">
                    ✕
                </button>
            </div>

            <!-- MODAL FORM -->
            <form id="bulk-delete-form"
                  hx-post="/plants/bulk-delete-modal-action"
                  hx-target="#plant-container"
                  hx-swap="innerHTML"
                  style="display: flex; flex-direction: column; flex: 1 1 auto; min-height: 0; overflow: hidden;">

                <input type="hidden" id="bulk-del-mode" name="del_mode" value="range" />
                <input type="hidden" id="bulk-del-keys-csv" name="keys_csv" value="" />

                <!-- SCROLLABLE BODY -->
                <div class="modal-body" style="padding: 16px 20px 20px 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;">
                    
                    <!-- 1. SELECTION METHOD SELECTOR -->
                    <div style="background: var(--bg-mantle); border: 1px solid var(--red-crimson); border-radius: 6px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px dashed var(--border-dim); padding-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 12px; font-weight: 700; color: var(--red-crimson); letter-spacing: 0.5px;">
                                    ⚙ CRITERIO DE SELECCIÓN PARA BAJA MASIVA
                                </span>
                            </div>

                            <!-- Mode Switcher -->
                            <div style="display: flex; gap: 4px; background: var(--bg-crust); padding: 2px; border-radius: 4px; border: 1px solid var(--border-dim);">
                                <button type="button"
                                        id="del-tab-range"
                                        class="inv-tab-btn active"
                                        onclick="setBulkDelMode('range')"
                                        style="font-size: 10.5px; padding: 3px 10px;">
                                    ● RANGO / PREFIJO
                                </button>
                                <button type="button"
                                        id="del-tab-manual"
                                        class="inv-tab-btn"
                                        onclick="setBulkDelMode('manual')"
                                        style="font-size: 10.5px; padding: 3px 10px;">
                                    ● PEGAR LISTA MANUAL
                                </button>
                                <button type="button"
                                        id="del-tab-filter"
                                        class="inv-tab-btn"
                                        onclick="setBulkDelMode('filter')"
                                        style="font-size: 10.5px; padding: 3px 10px;">
                                    ● FILTRO POR CRITERIO
                                </button>
                            </div>
                        </div>

                        <!-- Panel 1: Range & Prefix Mode -->
                        <div id="del-panel-range">
                            <div class="bulk-seq-grid" style="display: grid; grid-template-columns: 1.5fr 1fr 1fr 1.2fr; gap: 12px; margin-bottom: 8px;">
                                
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-prefix" style="color: var(--text-main);">
                                        PREFIJO / CÓDIGO
                                    </label>
                                    <input type="text"
                                           id="del-prefix"
                                           class="form-input"
                                           value="K"
                                           placeholder="Ej: K, A, TEST"
                                           maxlength="15"
                                           style="text-transform: uppercase; font-weight: 700; color: #ff66cc;"
                                           oninput="this.value = this.value.toUpperCase(); onBulkDelInputsChanged();"
                                           autocomplete="off" />
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Código base de la secuencia
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-start" style="color: var(--text-main);">
                                        DESDE NÚMERO
                                    </label>
                                    <input type="number"
                                           id="del-start"
                                           class="form-input"
                                           value="1"
                                           min="1"
                                           oninput="onBulkDelInputsChanged();" />
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Número inicial del rango
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-end" style="color: var(--text-main);">
                                        HASTA NÚMERO
                                    </label>
                                    <input type="number"
                                           id="del-end"
                                           class="form-input"
                                           value="10"
                                           min="1"
                                           max="10000"
                                           oninput="onBulkDelInputsChanged();" />
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Número final del rango (hasta 10.000)
                                    </div>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-pad-zeros" style="color: var(--text-main);">
                                        FORMATO DE NÚMERO
                                    </label>
                                    <select id="del-pad-zeros"
                                            class="form-input"
                                            onchange="onBulkDelInputsChanged();">
                                        <option value="both" selected>Flexible (K1 y K01)</option>
                                        <option value="0">Sin ceros (K1, K2...)</option>
                                        <option value="2">2 dígitos (K01, K02...)</option>
                                        <option value="3">3 dígitos (K001, K002...)</option>
                                    </select>
                                    <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                        Relleno de ceros
                                    </div>
                                </div>

                            </div>
                        </div>

                        <!-- Panel 2: Manual Textarea Mode -->
                        <div id="del-panel-manual" style="display: none; margin-bottom: 8px;">
                            <label class="form-label" for="del-manual-keys" style="color: var(--text-main);">
                                PEGAR CLAVES A ELIMINAR (SEPARADAS POR COMA, ESPACIO O SALTO DE LÍNEA)
                            </label>
                            <textarea id="del-manual-keys"
                                      class="form-textarea"
                                      style="height: 65px; font-family: var(--font-mono); font-size: 12px;"
                                      placeholder="Ej: K01, K02, K03, A10, B-02"
                                      oninput="onBulkDelInputsChanged();"></textarea>
                            <div style="font-size: 10px; color: var(--text-dim); margin-top: 3px;">
                                Ingrese las claves exactas de los ejemplares a dar de baja.
                            </div>
                        </div>

                        <!-- Panel 3: Filter by Criteria Mode -->
                        <div id="del-panel-filter" style="display: none; margin-bottom: 8px;">
                            <div class="bulk-filter-grid" style="display: grid; grid-template-columns: 1fr 1.5fr 1fr; gap: 12px;">
                                
                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-filter-status">ESTADO SANITARIO</label>
                                    <select id="del-filter-status" class="form-input" onchange="onBulkDelInputsChanged();">
                                        <option value="ALL">Cualquier estado</option>
                                        <option value="notOK">Solo en cuarentena (● notOK)</option>
                                        <option value="OK">Solo saludables (● Ok)</option>
                                    </select>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-filter-location">UBICACIÓN / BANCO</label>
                                    <select id="del-filter-location" class="form-input" onchange="onBulkDelInputsChanged();">
                                        <option value="ALL">Cualquier ubicación</option>
                                        {loc_options}
                                    </select>
                                </div>

                                <div class="form-group" style="margin-bottom: 0;">
                                    <label class="form-label" for="del-filter-photos">FOTOGRAFÍAS</label>
                                    <select id="del-filter-photos" class="form-input" onchange="onBulkDelInputsChanged();">
                                        <option value="ALL">Con o sin fotos</option>
                                        <option value="NO_PHOTOS">Solo sin fotografías</option>
                                        <option value="WITH_PHOTOS">Solo con fotografías</option>
                                    </select>
                                </div>

                            </div>
                        </div>

                    </div>

                    <!-- 2. LIVE SELECTION PREVIEW & IMPACT SUMMARY -->
                    <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 6px; padding: 14px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; border-bottom: 1px dashed var(--border-dim); padding-bottom: 8px; flex-wrap: wrap; gap: 8px;">
                            <span style="font-size: 12px; font-weight: 700; color: var(--peach-orange);">
                                👁 PREVISUALIZACIÓN DE EJEMPLARES A ELIMINAR
                            </span>
                            <span id="del-impact-badge" style="font-size: 11px; font-weight: 700; color: var(--red-crimson);">
                                0 ejemplares seleccionados
                            </span>
                        </div>

                        <!-- Candidates Container -->
                        <div id="bulk-del-preview-container">
                            <!-- Populated dynamically by JavaScript -->
                        </div>
                    </div>

                    <!-- 3. SAFETY CONFIRMATION CARD -->
                    <div style="background: rgba(239, 68, 68, 0.08); border: 1px solid var(--red-crimson); border-radius: 6px; padding: 12px 16px;">
                        <label style="display: flex; align-items: flex-start; gap: 10px; cursor: pointer; user-select: none;">
                            <input type="checkbox"
                                   id="bulk-del-confirm-checkbox"
                                   style="margin-top: 3px; accent-color: var(--red-crimson); transform: scale(1.15);"
                                   onchange="onBulkDelInputsChanged();" />
                            <div style="font-size: 12px; color: var(--text-main); line-height: 1.4;">
                                <strong style="color: var(--red-crimson);">CONFIRMACIÓN OBLIGATORIA DE PURGA DEFINITIVA:</strong><br />
                                Entiendo que esta operación eliminará de forma irreversible los registros seleccionados en la base de datos SQLite y purgará permanentemente sus archivos fotográficos.
                            </div>
                        </label>
                    </div>

                </div>

                <!-- STICKY FOOTER ACTIONS -->
                <div class="modal-footer-sticky" style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button type="button"
                                class="btn"
                                hx-get="/modal/close"
                                hx-target="#modal-container"
                                hx-swap="innerHTML">
                            CANCELAR [ESC]
                        </button>
                        <span id="bulk-del-spinner" class="htmx-indicator" style="color: var(--red-crimson); font-size: 11.5px; font-weight: bold;">
                            ⏳ [ELIMINANDO Y PURGANDO ARCHIVOS...]
                        </span>
                    </div>

                    <button type="submit"
                            id="bulk-del-submit-btn"
                            class="btn btn-red"
                            style="font-weight: 700; padding: 9px 24px; font-size: 12.5px;"
                            disabled>
                        🗑 ELIMINAR 0 EJEMPLARES
                    </button>
                </div>

            </form>
        </div>
    </div>

    <!-- CLIENT-SIDE BATCH REMOVAL SCRIPT -->
    <script>
        window.ALL_CATALOG_PLANTS = {plants_json};

        function setBulkDelMode(mode) {{
            var hid = document.getElementById('bulk-del-mode');
            var pRange = document.getElementById('del-panel-range');
            var pMan = document.getElementById('del-panel-manual');
            var pFilt = document.getElementById('del-panel-filter');

            var bRange = document.getElementById('del-tab-range');
            var bMan = document.getElementById('del-tab-manual');
            var bFilt = document.getElementById('del-tab-filter');

            if (hid) hid.value = mode;

            if (pRange) pRange.style.display = (mode === 'range') ? 'block' : 'none';
            if (pMan) pMan.style.display = (mode === 'manual') ? 'block' : 'none';
            if (pFilt) pFilt.style.display = (mode === 'filter') ? 'block' : 'none';

            if (bRange) bRange.classList.toggle('active', mode === 'range');
            if (bMan) bMan.classList.toggle('active', mode === 'manual');
            if (bFilt) bFilt.classList.toggle('active', mode === 'filter');

            onBulkDelInputsChanged();
        }}

        function onBulkDelInputsChanged() {{
            var mode = document.getElementById('bulk-del-mode')?.value || 'range';
            var matched = [];

            if (mode === 'range') {{
                var pfx = (document.getElementById('del-prefix')?.value || '').trim().toUpperCase();
                var s = parseInt(document.getElementById('del-start')?.value || '1', 10);
                var e = parseInt(document.getElementById('del-end')?.value || '10', 10);
                var padMode = document.getElementById('del-pad-zeros')?.value || 'both';

                if (!isNaN(s) && !isNaN(e) && s <= e) {{
                    var targetKeySet = new Set();
                    for (var i = s; i <= e; i++) {{
                        var sNum = String(i);
                        if (padMode === 'both') {{
                            targetKeySet.add(pfx + sNum);
                            targetKeySet.add(pfx + (sNum.length < 2 ? '0' + sNum : sNum));
                            targetKeySet.add(pfx + '-' + sNum);
                            targetKeySet.add(pfx + '-' + (sNum.length < 2 ? '0' + sNum : sNum));
                        }} else if (padMode === '2') {{
                            targetKeySet.add(pfx + (sNum.length < 2 ? '0' + sNum : sNum));
                        }} else if (padMode === '3') {{
                            while (sNum.length < 3) sNum = '0' + sNum;
                            targetKeySet.add(pfx + sNum);
                        }} else {{
                            targetKeySet.add(pfx + sNum);
                        }}
                    }}

                    window.ALL_CATALOG_PLANTS.forEach(function(p) {{
                        if (targetKeySet.has(p.name.toUpperCase())) {{
                            matched.push(p);
                        }}
                    }});
                }}
            }} else if (mode === 'manual') {{
                var txt = (document.getElementById('del-manual-keys')?.value || '').trim();
                var rawParts = txt.split(/[,\\n\\s]+/);
                var targetSet = new Set();
                rawParts.forEach(function(item) {{
                    var clean = item.replace(/[^a-zA-Z0-9_-]/g, '').toUpperCase().trim();
                    if (clean) targetSet.add(clean);
                }});

                window.ALL_CATALOG_PLANTS.forEach(function(p) {{
                    if (targetSet.has(p.name.toUpperCase())) {{
                        matched.push(p);
                    }}
                }});
            }} else if (mode === 'filter') {{
                var st = document.getElementById('del-filter-status')?.value || 'ALL';
                var loc = document.getElementById('del-filter-location')?.value || 'ALL';
                var ph = document.getElementById('del-filter-photos')?.value || 'ALL';

                window.ALL_CATALOG_PLANTS.forEach(function(p) {{
                    var stOk = (st === 'ALL') || (p.status === st);
                    var locOk = (loc === 'ALL') || (p.location === loc);
                    var phOk = true;
                    if (ph === 'NO_PHOTOS') phOk = (p.photos_count === 0);
                    else if (ph === 'WITH_PHOTOS') phOk = (p.photos_count > 0);

                    if (stOk && locOk && phOk) {{
                        matched.push(p);
                    }}
                }});
            }}

            // Calculate impact
            var totalPhotos = 0;
            var keysList = [];
            var chipsHtml = '';
            var maxRender = 60;
            var hasTruncation = (matched.length > maxRender);
            var renderList = hasTruncation ? matched.slice(0, 50) : matched;

            matched.forEach(function(p) {{
                totalPhotos += (p.photos_count || 0);
                keysList.push(p.name);
            }});

            renderList.forEach(function(p) {{
                var akaSpan = p.aka ? ' <span style="color: var(--peach-orange);">"' + p.aka + '"</span>' : '';
                var photoTag = (p.photos_count > 0) ? ' · 📸 ' + p.photos_count : '';
                chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 4px; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--red-crimson); color: var(--red-crimson); font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 3px;" title="' + p.species + '">' +
                    p.name + akaSpan + photoTag + '</span> ';
            }});

            if (hasTruncation) {{
                chipsHtml += '<span style="color: var(--peach-orange); font-size: 11px; padding: 2px 8px; font-weight: 600; align-self: center;">... y ' + (matched.length - 60).toLocaleString() + ' ejemplares más en el lote ...</span> ';
                matched.slice(-10).forEach(function(p) {{
                    var akaSpan = p.aka ? ' <span style="color: var(--peach-orange);">"' + p.aka + '"</span>' : '';
                    var photoTag = (p.photos_count > 0) ? ' · 📸 ' + p.photos_count : '';
                    chipsHtml += '<span style="display: inline-flex; align-items: center; gap: 4px; background: rgba(239, 68, 68, 0.15); border: 1px solid var(--red-crimson); color: var(--red-crimson); font-family: var(--font-mono); font-size: 11px; font-weight: 700; padding: 3px 8px; border-radius: 3px;" title="' + p.species + '">' +
                        p.name + akaSpan + photoTag + '</span> ';
                }});
            }}

            var keysCsvInput = document.getElementById('bulk-del-keys-csv');
            if (keysCsvInput) keysCsvInput.value = keysList.join(',');

            var badgeEl = document.getElementById('del-impact-badge');
            if (badgeEl) {{
                badgeEl.textContent = matched.length.toLocaleString() + ' ejemplares identificados · ' + totalPhotos.toLocaleString() + ' fotos ';
            }}

            var container = document.getElementById('bulk-del-preview-container');
            if (container) {{
                if (matched.length === 0) {{
                    container.innerHTML = '<div style="color: var(--text-dim); font-size: 11.5px; padding: 12px; text-align: center; border: 1px dashed var(--border-dim); border-radius: 4px;">' +
                        'No hay ejemplares en la base de datos que coincidan con los criterios seleccionados.' +
                        '</div>';
                }} else {{
                    container.innerHTML = '<div style="display: flex; flex-wrap: wrap; gap: 6px; max-height: 140px; overflow-y: auto; background: var(--bg-crust); border: 1px solid var(--border-dim); border-radius: 4px; padding: 10px;">' +
                        chipsHtml +
                        '</div>';
                }}
            }}

            var chkConfirm = document.getElementById('bulk-del-confirm-checkbox');
            var isConfirmed = chkConfirm ? chkConfirm.checked : false;

            var submitBtn = document.getElementById('bulk-del-submit-btn');
            if (submitBtn) {{
                var canSubmit = (matched.length > 0 && isConfirmed);
                submitBtn.disabled = !canSubmit;
                submitBtn.style.opacity = canSubmit ? '1' : '0.45';
                submitBtn.style.cursor = canSubmit ? 'pointer' : 'not-allowed';
                submitBtn.innerHTML = '🗑 ELIMINAR LOTE DE ' + matched.length + ' EJEMPLARES';
            }}
        }}

        // Initialize calculation
        setTimeout(onBulkDelInputsChanged, 30);
    </script>
    """


def render_import_db_modal(error_msg: Optional[str] = None, success_info: Optional[Dict[str, Any]] = None) -> str:
    """Renders the Import / Restore Previous Database modal with rigorous validation and safety guarantees."""

    error_banner = ""
    if error_msg:
        error_banner = f"""
        <div style="background: rgba(239, 68, 68, 0.12); border: 1px solid var(--red-crimson); border-radius: 6px; padding: 14px 16px; margin-bottom: 16px; display: flex; flex-direction: column; gap: 6px;">
            <div style="color: var(--red-crimson); font-weight: 700; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                <span>⚠️ RECHAZADO POR SEGURIDAD E INCOMPATIBILIDAD</span>
            </div>
            <div style="color: var(--text-main); font-size: 12px; line-height: 1.4;">
                {html.escape(error_msg)}
            </div>
            <div style="color: var(--text-dim); font-size: 11px; margin-top: 4px; border-top: 1px dashed rgba(239, 68, 68, 0.3); padding-top: 6px;">
                Su catálogo actual NO ha sido modificado y se mantiene 100% íntegro y protegido.
            </div>
        </div>
        """

    if success_info:
        return f"""
        <div class="modal-overlay" id="import-db-modal" role="dialog" aria-modal="true" style="display: flex;">
            <div class="modal-dialog" style="max-width: 680px; width: 95vw; display: flex; flex-direction: column;">
                
                <!-- HEADER -->
                <div class="modal-header">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <span class="modal-title" style="color: var(--green-sage);">
                            📥 [IMPORTACIÓN DE BASE DE DATOS COMPLETADA]
                        </span>
                    </div>
                    <button type="button"
                            class="modal-close-btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            title="Cerrar ventana [ESC]"
                            aria-label="Cerrar modal">
                        ✕
                    </button>
                </div>

                <!-- BODY -->
                <div class="modal-body" style="padding: 24px; display: flex; flex-direction: column; gap: 18px;">
                    <div style="background: rgba(166, 227, 161, 0.12); border: 1px solid var(--green-sage); border-radius: 6px; padding: 16px; display: flex; flex-direction: column; gap: 10px;">
                        <div style="color: var(--green-sage); font-weight: 700; font-size: 14px;">
                            ✓ BASE DE DATOS VALIDADA, MIGRADA E IMPORTADA CON ÉXITO
                        </div>
                        <div style="color: var(--text-main); font-size: 12.5px; line-height: 1.5;">
                            El archivo SQLite ha superado todas las pruebas criptográficas y de integridad (PRAGMA integrity_check). Sus índices y columnas han sido sincronizados perfectamente con la versión actual del sistema.
                        </div>
                    </div>

                    <!-- METRICS GRID -->
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                        <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 12px 14px;">
                            <div style="font-size: 20px; font-weight: 700; color: var(--green-sage); font-family: var(--font-mono);">
                                {success_info['total_plants']}
                            </div>
                            <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">
                                Ejemplares botánicos importados
                            </div>
                        </div>

                        <div style="background: var(--bg-mantle); border: 1px solid var(--border-dim); border-radius: 4px; padding: 12px 14px;">
                            <div style="font-size: 20px; font-weight: 700; color: var(--blue-sky); font-family: var(--font-mono);">
                                {success_info['total_photos_referenced']}
                            </div>
                            <div style="font-size: 11px; color: var(--text-dim); text-transform: uppercase;">
                                Referencias fotográficas asociadas
                            </div>
                        </div>
                    </div>

                    <!-- SAFETY ROLLBACK NOTICE -->
                    <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 4px; padding: 12px 14px; font-size: 11.5px; color: var(--text-sub); display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-weight: 700; color: var(--peach-orange);">🛡️ SNAPSHOT DE ROLLBACK PREVENTIVO GENERADO:</span>
                        <span style="font-family: var(--font-mono); color: var(--text-main); word-break: break-all;">
                            DB/backups/{html.escape(success_info['safety_backup'])}
                        </span>
                        <span style="font-size: 10.5px; color: var(--text-dim);">
                            Si en cualquier momento desea revertir este cambio, su snapshot previo se encuentra seguro y disponible (retención de hasta 20 rollbacks).
                        </span>
                    </div>
                </div>

                <!-- FOOTER -->
                <div class="modal-footer-sticky" style="display: flex; justify-content: flex-end; gap: 10px;">
                    <button type="button"
                            class="btn"
                            hx-get="/modal/close"
                            hx-target="#modal-container"
                            hx-swap="innerHTML">
                        ✕ CERRAR [ESC]
                    </button>
                    <button type="button"
                            class="btn btn-green"
                            hx-get="/admin/modal"
                            hx-target="#modal-container"
                            hx-swap="innerHTML"
                            style="font-weight: 700;">
                        ⚙ IR AL PANEL DE ADMINISTRACIÓN
                    </button>
                </div>

            </div>
        </div>
        """

    return f"""
    <div class="modal-overlay" id="import-db-modal" role="dialog" aria-modal="true" style="display: flex;">
        <div class="modal-dialog" style="max-width: 680px; width: 95vw; display: flex; flex-direction: column;">
            
            <!-- HEADER -->
            <div class="modal-header">
                <div style="display: flex; align-items: center; gap: 10px;">
                    <span class="modal-title" style="color: var(--peach-orange);">
                        📥 [IMPORTAR / RESTAURAR BASE DE DATOS SQLITE]
                    </span>
                </div>
                <button type="button"
                        class="modal-close-btn"
                        hx-get="/modal/close"
                        hx-target="#modal-container"
                        hx-swap="innerHTML"
                        title="Cerrar ventana [ESC]"
                        aria-label="Cerrar modal">
                    ✕
                </button>
            </div>

            <!-- FORM -->
            <form id="import-db-form"
                  hx-post="/admin/import-db"
                  hx-encoding="multipart/form-data"
                  hx-target="#modal-container"
                  hx-swap="innerHTML"
                  hx-indicator="#import-db-spinner"
                  style="display: flex; flex-direction: column; flex: 1 1 auto; overflow: hidden;">

                <!-- BODY -->
                <div class="modal-body" style="padding: 20px 24px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px;">
                    
                    {error_banner}

                    <!-- INSTRUCTIONS & DESCRIPTION -->
                    <div style="font-size: 12.5px; color: var(--text-sub); line-height: 1.5;">
                        Esta herramienta le permite restaurar una copia de seguridad previa de Plantation o importar un archivo de base de datos SQLite (<code style="color: var(--peach-orange); font-family: var(--font-mono);">.db</code>).
                    </div>

                    <!-- FILE INPUT DROPZONE -->
                    <div style="background: var(--bg-mantle); border: 2px dashed var(--border-dim); border-radius: 6px; padding: 22px; text-align: center; display: flex; flex-direction: column; align-items: center; gap: 10px;">
                        <div style="font-size: 28px;">🗄️</div>
                        <div style="font-size: 13px; font-weight: 700; color: var(--text-main);">
                            SELECCIONE EL ARCHIVO SQLITE (.DB / .SQLITE)
                        </div>
                        <input type="file"
                               name="db_file"
                               id="import-db-file-input"
                               accept=".db,.sqlite,.sqlite3"
                               required
                               class="form-input"
                               style="max-width: 380px; cursor: pointer;"
                               onchange="checkImportReady();" />
                        <div style="font-size: 10.5px; color: var(--text-dim);">
                            Archivos admitidos: <strong>plantation.db</strong>, copias de seguridad de <strong>DB/backups/</strong> o exports SQLite compatibles.
                        </div>
                    </div>

                    <!-- SECURITY & COMPATIBILITY CHECKLIST -->
                    <div style="background: var(--bg-surface); border: 1px solid var(--border-dim); border-radius: 6px; padding: 14px 16px;">
                        <div style="font-size: 11px; font-weight: 700; color: var(--blue-sky); text-transform: uppercase; margin-bottom: 8px; letter-spacing: 0.5px;">
                            🛡️ GARANTÍAS DE COMPATIBILIDAD Y SEGURIDAD AUTOMÁTICAS:
                        </div>
                        <ul style="margin: 0; padding-left: 18px; font-size: 11.5px; color: var(--text-sub); line-height: 1.6;">
                            <li><strong>Verificación de cabecera:</strong> Comprobación criptográfica del número mágico SQLite 3.</li>
                            <li><strong>Integridad física:</strong> Ejecución de <code style="font-family: var(--font-mono); color: var(--green-sage);">PRAGMA integrity_check</code> para descartar corrupción b-tree.</li>
                            <li><strong>Compatibilidad de esquema:</strong> Inspección de la tabla <code style="font-family: var(--font-mono); color: var(--green-sage);">plants</code> y sus campos obligatorios.</li>
                            <li><strong>Migración retrocompatible:</strong> Incorporación automática de columnas modernas ausentes en versiones anteriores.</li>
                            <li><strong>Rollback preventivo:</strong> Generación automática de un snapshot de su base de datos actual antes de reemplazarla (retención de hasta 20 rollbacks).</li>
                        </ul>
                    </div>

                    <!-- MANDATORY CONFIRMATION CHECKBOX -->
                    <div style="background: rgba(245, 169, 127, 0.08); border: 1px solid var(--peach-orange); border-radius: 6px; padding: 12px 16px;">
                        <label style="display: flex; align-items: flex-start; gap: 10px; cursor: pointer; user-select: none;">
                            <input type="checkbox"
                                   id="import-db-confirm"
                                   name="confirm_replace"
                                   value="yes"
                                   style="margin-top: 3px; accent-color: var(--peach-orange); transform: scale(1.15);"
                                   onchange="checkImportReady();" />
                            <div style="font-size: 12px; color: var(--text-main); line-height: 1.4;">
                                <strong style="color: var(--peach-orange);">CONFIRMACIÓN DE SUSTITUCIÓN:</strong><br />
                                He verificado el archivo y autorizo la sustitución del catálogo activo. Entiendo que se generará un snapshot de rollback preventivo en <code style="font-family: var(--font-mono);">DB/backups/</code>.
                            </div>
                        </label>
                    </div>

                </div>

                <!-- FOOTER -->
                <div class="modal-footer-sticky" style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button type="button"
                                class="btn"
                                hx-get="/modal/close"
                                hx-target="#modal-container"
                                hx-swap="innerHTML">
                            CANCELAR [ESC]
                        </button>
                        <span id="import-db-spinner" class="htmx-indicator" style="color: var(--peach-orange); font-size: 11.5px; font-weight: bold;">
                            ⏳ [VALIDANDO INTEGRIDAD Y ESTRUCTURA...]
                        </span>
                    </div>

                    <button type="submit"
                            id="import-db-submit-btn"
                            class="btn btn-primary"
                            style="font-weight: 700; padding: 9px 24px;"
                            disabled>
                        📥 [VERIFICAR E IMPORTAR BASE DE DATOS]
                    </button>
                </div>

            </form>
        </div>
    </div>

    <script>
        function checkImportReady() {{
            var fileInput = document.getElementById('import-db-file-input');
            var chk = document.getElementById('import-db-confirm');
            var submitBtn = document.getElementById('import-db-submit-btn');
            
            var hasFile = fileInput && fileInput.files && fileInput.files.length > 0;
            var isConfirmed = chk && chk.checked;
            
            if (submitBtn) {{
                var ready = hasFile && isConfirmed;
                submitBtn.disabled = !ready;
                submitBtn.style.opacity = ready ? '1' : '0.45';
                submitBtn.style.cursor = ready ? 'pointer' : 'not-allowed';
            }}
        }}
    </script>
    """



