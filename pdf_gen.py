"""
Plantation - High-performance, ink-friendly PDF generation using fpdf2.
Replaces all legacy HTML/WeasyPrint rendering with fast, vector-crisp PDF output.
"""

import os
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from PIL import Image, ImageFile
import db

# Allow loading of slightly corrupted or truncated images without hard crashing
ImageFile.LOAD_TRUNCATED_IMAGES = True

# Register HEIC opener if available (e.g. for iPhone camera uploads)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:
    pass

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images")

# Botanical ink-friendly palette
CLR_PRIMARY = (26, 71, 42)          # Deep Forest Green (#1a472a)
CLR_PRIMARY_LIGHT = (240, 247, 241) # Very soft green tint
CLR_DARK = (15, 23, 42)              # Slate Charcoal
CLR_MUTED = (100, 116, 139)          # Slate Gray
CLR_BORDER = (203, 213, 225)         # Light Slate Border
CLR_ROW_ALT = (248, 250, 252)        # Subtle table alternate row
CLR_PEACH = (194, 65, 12)            # Terracotta / Peach accent for Alias
CLR_UNICORN_PINK = (255, 102, 204)   # #ff66cc - Unicorn Pink for Plant Keys
CLR_OK_BG = (220, 252, 231)          # Soft green badge
CLR_OK_TXT = (22, 101, 52)
CLR_NOTOK_BG = (254, 226, 226)       # Soft red badge
CLR_NOTOK_TXT = (220, 38, 38)         # Bright crimson red text


def safe_text(val) -> str:
    """Sanitize strings to ensure complete compatibility with core FPDF fonts."""
    if val is None:
        return ""
    text = str(val).strip()
    replacements = {
        "—": "-", "–": "-", "―": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
        "‚": ",", "„": '"', "•": "*", "●": "*", "…": "...", "→": "->", "←": "<-",
        "✓": "OK", "✕": "x", "✖": "x", "×": "x", "♀": "(f)", "♂": "(m)",
        "°": "o", "±": "+/-", "µ": "u", "™": "(TM)", "®": "(R)", "©": "(C)",
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2010": "-", "\u2015": "-",
        "\u00a0": " ", "\u200b": ""
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("latin-1", "replace").decode("latin-1")


def truncate_to_width(pdf: FPDF, text: str, max_w: float, padding: float = 1.0) -> str:
    """
    Truncates text with ellipsis if its rendered width exceeds available space.
    Prevents text overlapping between neighboring table columns and bounded cards.
    """
    if not text:
        return ""
    text = safe_text(text)
    avail_w = max_w - padding
    if avail_w <= 0:
        return ""
    if pdf.get_string_width(text) <= avail_w:
        return text
    ellipsis = "..."
    ell_w = pdf.get_string_width(ellipsis)
    if ell_w >= avail_w:
        return ""
    while text and (pdf.get_string_width(text) + ell_w) > avail_w:
        text = text[:-1]
    return text.rstrip() + ellipsis


def fit_text_to_width(pdf: FPDF, text: str, max_w: float, font_family: str = "Helvetica", font_style: str = "", initial_size: float = 7.5, min_size: float = 6.2, padding: float = 1.0) -> tuple[str, float]:
    """
    Fits text within max_w by first slightly scaling font size down to min_size,
    and only truncating with ellipsis if still overflowing.
    Returns (fitted_text, final_font_size).
    """
    if not text:
        return "", initial_size
    text = safe_text(text)
    avail_w = max_w - padding
    if avail_w <= 0:
        return "", min_size

    pdf.set_font(font_family, font_style, initial_size)
    if pdf.get_string_width(text) <= avail_w:
        return text, initial_size

    cur_size = initial_size - 0.3
    while cur_size >= min_size:
        pdf.set_font(font_family, font_style, cur_size)
        if pdf.get_string_width(text) <= avail_w:
            return text, round(cur_size, 1)
        cur_size -= 0.3

    pdf.set_font(font_family, font_style, min_size)
    truncated = truncate_to_width(pdf, text, max_w, padding=padding)
    return truncated, min_size


class BotanicalPDF(FPDF):
    """Custom FPDF document with official botanical header, footer, and utility components."""

    def __init__(self, title_text="EXPEDIENTE", **kwargs):
        super().__init__(format="A4", unit="mm", **kwargs)
        self.doc_title = title_text
        self.set_margins(15, 15, 15)
        self.set_auto_page_break(auto=True, margin=15)
        self.alias_nb_pages()

    def normalize_text(self, text):
        return super().normalize_text(safe_text(text))

    def header(self):
        # Top banner with botanical logo & title
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*CLR_PRIMARY)
        self.cell(100, 6, safe_text("[ PLANTATION ] SISTEMA BOTÁNICO"), border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*CLR_MUTED)
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 6, safe_text(f"Emitido: {date_str}"), border=0, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_draw_color(*CLR_PRIMARY)
        self.set_line_width(0.6)
        self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-12)
        self.set_draw_color(*CLR_BORDER)
        self.set_line_width(0.3)
        self.line(15, self.get_y(), self.w - 15, self.get_y())
        self.ln(2)

        avail_title_w = self.w - 30 - 35  # Reserved space for page number on right
        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*CLR_MUTED)
        footer_title = truncate_to_width(self, f"EXPEDIENTE TÉCNICO - {self.doc_title.upper()}", avail_title_w)
        self.cell(avail_title_w, 5, safe_text(footer_title), border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

        self.set_font("Helvetica", "", 7)
        self.cell(0, 5, safe_text(f"Página {self.page_no()} de {{nb}}"), border=0, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def draw_status_badge(self, x, y, status, w=22, h=6):
        """Draw an ink-friendly health status badge (OK or notOK) with a crisp vector indicator."""
        is_ok = (status or "").upper() == "OK"
        bg_col = CLR_OK_BG if is_ok else CLR_NOTOK_BG
        txt_col = CLR_OK_TXT if is_ok else CLR_NOTOK_TXT
        label = "OK" if is_ok else "notOK"

        self.set_fill_color(*bg_col)
        self.set_draw_color(*txt_col)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, style="FD")

        # Crisp vector indicator dot (never dependent on font encoding)
        dot_r = min(h * 0.18, 1.0)
        dot_x = x + (2.5 if w <= 16 else 3.2)
        dot_y = y + (h / 2)
        self.set_fill_color(*txt_col)
        self.circle(dot_x, dot_y, radius=dot_r, style="F")

        # Text label
        label_offset = dot_x + dot_r + 1.2
        label_w = (x + w) - label_offset - 1.0
        self.set_xy(label_offset, y)
        font_size = 7.5 if h >= 5.5 else 6.5
        self.set_font("Helvetica", "B", font_size)
        self.set_text_color(*txt_col)
        self.cell(label_w, h, safe_text(label), border=0, align="C")


def get_all_valid_images(plant: dict) -> list[str]:
    """Retrieves all existing and valid image file paths registered for a plant."""
    photos = plant.get("photos")
    if not photos:
        return []
    if isinstance(photos, str):
        import json
        try:
            photos = json.loads(photos)
        except Exception:
            photos = [photos]
    valid_paths = []
    if isinstance(photos, list):
        for ph in photos:
            if ph and isinstance(ph, str):
                full_path = os.path.join(IMAGES_DIR, ph)
                if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                    valid_paths.append(full_path)
    return valid_paths


def get_first_valid_image(plant: dict) -> str | None:
    """Find the path of the first existing photo for a plant."""
    imgs = get_all_valid_images(plant)
    return imgs[0] if imgs else None


def draw_standardized_image_frame(pdf, img_path: str, x: float, y: float, w: float, h: float, caption: str = ""):
    """Draws an image within a standard box frame maintaining original aspect ratio."""
    pdf.set_draw_color(*CLR_BORDER)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(x, y, w, h, style="FD")

    caption_h = 7 if caption else 0
    inner_w = w - 4
    inner_h = h - caption_h - 4

    try:
        with Image.open(img_path) as im:
            orig_w, orig_h = im.size
            ratio = orig_w / max(orig_h, 1)
            target_ratio = inner_w / max(inner_h, 1)

            if ratio >= target_ratio:
                draw_w = inner_w
                draw_h = inner_w / ratio
                draw_x = x + 2
                draw_y = y + 2 + ((inner_h - draw_h) / 2)
            else:
                draw_h = inner_h
                draw_w = inner_h * ratio
                draw_x = x + 2 + ((inner_w - draw_w) / 2)
                draw_y = y + 2

        pdf.image(img_path, x=draw_x, y=draw_y, w=draw_w, h=draw_h)
    except Exception:
        pdf.set_xy(x + 2, y + (h / 2) - 3)
        pdf.set_font("Helvetica", "I", 7.5)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(w - 4, 6, safe_text("Error al cargar imagen"), border=0, align="C")

    # Caption bar at bottom of box with clean clipping
    if caption:
        pdf.set_xy(x, y + h - caption_h)
        pdf.set_fill_color(*CLR_ROW_ALT)
        pdf.rect(x, y + h - caption_h, w, caption_h, style="F")
        pdf.set_xy(x + 2, y + h - caption_h)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(*CLR_MUTED)
        safe_cap = truncate_to_width(pdf, caption, w - 4, padding=1.0)
        pdf.cell(w - 4, caption_h, safe_text(safe_cap), border=0, align="C")


def draw_plant_dossier_content(pdf: BotanicalPDF, plant: dict) -> None:
    """Renders the complete botanical technical dossier content for a specimen into the given PDF."""
    raw_name = safe_text(plant.get("name", "N/A"))
    name = raw_name
    aka = safe_text(plant.get("aka", ""))
    species = safe_text(plant.get("species", "Sin especie registrada"))
    status = plant.get("status", "OK")

    box_w = pdf.w - 30  # 180mm printable width

    # =========================================================================
    # 1. HEADER CARD
    # =========================================================================
    start_y = pdf.get_y()
    pdf.set_fill_color(*CLR_PRIMARY_LIGHT)
    pdf.set_draw_color(*CLR_PRIMARY)
    pdf.set_line_width(0.4)
    pdf.rect(15, start_y, box_w, 24, style="FD")

    # Status Badge top right (fixed at right margin)
    badge_w = 24
    badge_h = 7
    badge_x = (pdf.w - 15) - badge_w - 4
    pdf.draw_status_badge(badge_x, start_y + 4, status, w=badge_w, h=badge_h)

    # Clave and Alias calculation with dynamic scaling
    avail_title_w = badge_x - 20 - 4
    clave_str = f"[{name}]"
    if aka:
        pdf.set_font("Helvetica", "B", 16)
        clave_w = pdf.get_string_width(clave_str)
        if clave_w > (avail_title_w * 0.52):
            pdf.set_font("Helvetica", "B", 13)
            clave_w = pdf.get_string_width(clave_str)

        pdf.set_xy(20, start_y + 3.5)
        pdf.set_text_color(*CLR_UNICORN_PINK)
        pdf.cell(clave_w + 1, 8, clave_str, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

        aka_x = 20 + clave_w + 4
        avail_aka_w = max(10.0, badge_x - aka_x - 3)
        fitted_aka, aka_sz = fit_text_to_width(pdf, f'"{aka}"', avail_aka_w, font_family="Helvetica", font_style="B", initial_size=12.5, min_size=9.0, padding=1.0)
        pdf.set_xy(aka_x, start_y + 4)
        pdf.set_font("Helvetica", "B", aka_sz)
        pdf.set_text_color(*CLR_PEACH)
        pdf.cell(avail_aka_w, 7, fitted_aka, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
    else:
        fitted_clave, c_sz = fit_text_to_width(pdf, clave_str, avail_title_w, font_family="Helvetica", font_style="B", initial_size=18, min_size=12, padding=1.0)
        pdf.set_xy(20, start_y + 3)
        pdf.set_font("Helvetica", "B", c_sz)
        pdf.set_text_color(*CLR_UNICORN_PINK)
        pdf.cell(avail_title_w, 8, fitted_clave, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # Species subheader (bounded to card width, italics)
    fitted_species, sp_sz = fit_text_to_width(pdf, species, box_w - 12, font_family="Helvetica", font_style="I", initial_size=10, min_size=8.0, padding=1.0)
    pdf.set_xy(20, start_y + 13.5)
    pdf.set_font("Helvetica", "I", sp_sz)
    pdf.set_text_color(*CLR_DARK)
    pdf.cell(box_w - 12, 6, fitted_species, border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(start_y + 27)

    # =========================================================================
    # 2. ESPECIFICACIONES (Full-width 2-column grid)
    # =========================================================================
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("ESPECIFICACIONES"), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    col_w = (box_w - 4) / 2  # 88mm each
    row_h = 5.8
    specs_left = [
        ("Clave", name),
        ("Fecha Siembra / Esqueje", safe_text(plant.get("sowing_cutting_date") or "—")),
        ("Edad Registrada", safe_text(db.calculate_age_display(plant.get("sowing_cutting_date"), plant.get("graft", "")))),
        ("Injerto", safe_text(plant.get("graft") or "—")),
        ("Linaje (Padres)", safe_text(plant.get("padres") or "—")),
        ("Ubicación", safe_text(plant.get("location") or "Sin registrar")),
    ]
    specs_right = [
        ("Alias", aka or "—"),
        ("Altura (Fecha - CM)", safe_text(plant.get("height") or "—")),
        ("Último Trasplante", safe_text(plant.get("last_repotted") or "—")),
        ("Última Poda", safe_text(plant.get("last_pruned") or "—")),
    ]

    table_y = pdf.get_y()
    max_rows = max(len(specs_left), len(specs_right))
    for i in range(max_rows):
        cur_row_y = table_y + (i * row_h)

        # Left Column Row
        if i < len(specs_left):
            lbl_l, val_l = specs_left[i]
            if i % 2 == 1:
                pdf.set_fill_color(*CLR_ROW_ALT)
                pdf.rect(15, cur_row_y, col_w, row_h, style="F")
            pdf.set_xy(15, cur_row_y)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*CLR_MUTED)
            pdf.cell(40, row_h, safe_text(lbl_l), border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

            # Prevent long values (e.g. parents/location) from bleeding into right column
            avail_val_l = col_w - 40 - 1.0
            pdf.set_font("Helvetica", "B" if lbl_l == "Alias" and val_l != "—" else "", 8)
            pdf.set_text_color(*(CLR_PEACH if lbl_l == "Alias" and val_l != "—" else CLR_DARK))
            val_l_fit = truncate_to_width(pdf, val_l, avail_val_l, padding=0.5)
            pdf.cell(avail_val_l, row_h, val_l_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Right Column Row
        if i < len(specs_right):
            lbl_r, val_r = specs_right[i]
            col2_x = 15 + col_w + 4
            if i % 2 == 1:
                pdf.set_fill_color(*CLR_ROW_ALT)
                pdf.rect(col2_x, cur_row_y, col_w, row_h, style="F")
            pdf.set_xy(col2_x, cur_row_y)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*CLR_MUTED)
            pdf.cell(38, row_h, safe_text(lbl_r), border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)

            avail_val_r = col_w - 38 - 1.0
            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*CLR_DARK)
            val_r_fit = truncate_to_width(pdf, val_r, avail_val_r, padding=0.5)
            pdf.cell(avail_val_r, row_h, val_r_fit, border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(table_y + (max_rows * row_h) + 4)

    # =========================================================================
    # 3. FERTILIZACIÓN & TRATAMIENTOS (Dynamic Height to avoid overlapping)
    # =========================================================================
    fertilizante = safe_text(plant.get("fertilizante") or "").strip()
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("FERTILIZACIÓN & TRATAMIENTOS"), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8.5)
    inner_box_w = box_w - 6
    if fertilizante:
        fert_calc_h = pdf.multi_cell(inner_box_w, 4.6, fertilizante, dry_run=True, output="HEIGHT")
        fert_box_h = max(16.0, fert_calc_h + 6.0)
    else:
        fert_box_h = 16.0

    fert_box_y = pdf.get_y()
    pdf.set_draw_color(*CLR_BORDER)
    pdf.set_fill_color(*CLR_ROW_ALT)
    pdf.rect(15, fert_box_y, box_w, fert_box_h, style="FD")

    pdf.set_xy(18, fert_box_y + 3)
    if fertilizante:
        pdf.set_text_color(*CLR_DARK)
        pdf.multi_cell(inner_box_w, 4.6, fertilizante)
    else:
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(inner_box_w, 6, safe_text("Sin tratamientos ni fertilización registrados para este ejemplar."), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(fert_box_y + fert_box_h + 4)

    # =========================================================================
    # 4. OBSERVACIONES & NOTAS (Dynamic Height to avoid overlapping)
    # =========================================================================
    comentarios = safe_text(plant.get("comentarios") or "").strip()
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("OBSERVACIONES & NOTAS"), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("Helvetica", "", 8.5)
    if comentarios:
        obs_calc_h = pdf.multi_cell(inner_box_w, 4.6, comentarios, dry_run=True, output="HEIGHT")
        obs_box_h = max(16.0, obs_calc_h + 6.0)
    else:
        obs_box_h = 16.0

    obs_box_y = pdf.get_y()
    pdf.set_draw_color(*CLR_BORDER)
    pdf.set_fill_color(*CLR_ROW_ALT)
    pdf.rect(15, obs_box_y, box_w, obs_box_h, style="FD")

    pdf.set_xy(18, obs_box_y + 3)
    if comentarios:
        pdf.set_text_color(*CLR_DARK)
        pdf.multi_cell(inner_box_w, 4.6, comentarios)
    else:
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(inner_box_w, 6, safe_text("Sin observaciones registradas para este ejemplar."), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_y(obs_box_y + obs_box_h + 5)

    # =========================================================================
    # 5. REGISTRO FOTOGRÁFICO DE ARCHIVO (Standardized & Protected Layout)
    # =========================================================================
    all_images = get_all_valid_images(plant)
    img_count = len(all_images)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    header_caption = f"REGISTRO FOTOGRÁFICO DE ARCHIVO ({img_count} FOTOGRAFÍA{'S' if img_count != 1 else ''})" if img_count > 0 else "REGISTRO FOTOGRÁFICO DE ARCHIVO"
    pdf.cell(box_w, 5.5, safe_text(header_caption), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    current_y = pdf.get_y()
    space_left = 270 - current_y

    if img_count == 0:
        ph_h = 24
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_fill_color(*CLR_ROW_ALT)
        pdf.rect(15, current_y, box_w, ph_h, style="FD")
        pdf.set_xy(15, current_y + 8)
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(box_w, 7, safe_text("Sin registro fotográfico adjunto para este ejemplar."), border=0, align="C")

    elif img_count == 1:
        img_w = 110
        img_h = 75
        if space_left < (img_h + 10):
            pdf.add_page()
            current_y = pdf.get_y()
        img_x = 15 + (box_w - img_w) / 2
        caption_txt = f"{os.path.basename(all_images[0])} - Ejemplar [{name}]"
        draw_standardized_image_frame(pdf, all_images[0], img_x, current_y, img_w, img_h, caption_txt)

    elif img_count == 2:
        col_gap = 6
        img_w = (box_w - col_gap) / 2  # 87mm each
        img_h = 65
        if space_left < (img_h + 10):
            pdf.add_page()
            current_y = pdf.get_y()
        for idx, img_p in enumerate(all_images):
            img_x = 15 + idx * (img_w + col_gap)
            caption_txt = f"Foto {idx + 1}/{img_count}: {os.path.basename(img_p)}"
            draw_standardized_image_frame(pdf, img_p, img_x, current_y, img_w, img_h, caption_txt)

    else:
        col_gap = 6
        img_w = (box_w - col_gap) / 2  # 87mm each
        if img_count <= 4 and space_left >= (2 * 54 + col_gap + 8):
            img_h = 54
        else:
            img_h = 62

        for idx, img_p in enumerate(all_images):
            col = idx % 2
            if col == 0 and idx > 0:
                current_y += img_h + 6

            if col == 0 and (current_y + img_h + 8 > 270):
                pdf.add_page()
                current_y = pdf.get_y()

            img_x = 15 + col * (img_w + col_gap)
            caption_txt = f"Foto {idx + 1}/{img_count}: {os.path.basename(img_p)}"
            draw_standardized_image_frame(pdf, img_p, img_x, current_y, img_w, img_h, caption_txt)


def generate_single_plant_pdf(plant: dict) -> bytes:
    """Generate a single-plant technical dossier PDF using fpdf2."""
    raw_name = safe_text(plant.get("name", "N/A"))
    pdf = BotanicalPDF(title_text=f"EJEMPLAR {raw_name}")
    pdf.add_page()
    draw_plant_dossier_content(pdf, plant)
    return bytes(pdf.output())


def generate_catalog_pdf(plants: list, title: str = "DOSSIER GENERAL DE EJEMPLARES") -> bytes:
    """
    Generate a complete catalog / general dossier PDF using fpdf2.
    Renders ALL elements in the DB:
      1. Summary statistics ribbon
      2. Comprehensive Master Index Table with all essential columns
      3. Complete individual technical dossier sheets with care log, botanical specs, and photos!
    """
    pdf = BotanicalPDF(title_text=title)
    pdf.add_page()

    total_count = len(plants)
    ok_count = sum(1 for p in plants if (p.get("status") or "").upper() == "OK")
    not_ok_count = total_count - ok_count
    with_alias_count = sum(1 for p in plants if (p.get("aka") or "").strip())

    # =========================================================================
    # Summary Statistics Ribbon
    # =========================================================================
    start_y = pdf.get_y()
    card_w = (pdf.w - 30 - 9) / 4  # 4 equal cards across 180mm
    stats = [
        ("TOTAL EJEMPLARES", str(total_count), CLR_PRIMARY),
        ("ESTADO OK", str(ok_count), CLR_OK_TXT),
        ("ESTADO notOK", str(not_ok_count), CLR_NOTOK_TXT),
        ("CON ALIAS", str(with_alias_count), CLR_PEACH),
    ]

    for i, (st_title, val, val_col) in enumerate(stats):
        cx = 15 + (i * (card_w + 3))
        pdf.set_fill_color(*CLR_PRIMARY_LIGHT)
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(cx, start_y, card_w, 14, style="FD")

        pdf.set_xy(cx, start_y + 2)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(card_w, 3.5, safe_text(st_title), border=0, align="C")

        pdf.set_xy(cx, start_y + 6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*val_col)
        pdf.cell(card_w, 6, safe_text(val), border=0, align="C")

    pdf.set_y(start_y + 18)

    # =========================================================================
    # Comprehensive Master Index Table
    # Columns cover all botanical specifications from the DB:
    # Clave (15) | Alias (28) | Especie (32) | Estado (14) | Ubicación (20) |
    # Altura (18) | Linaje (25) | Injerto (16) | Fotos (12) = 180mm
    # =========================================================================
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(0, 6, safe_text("ÍNDICE MAESTRO DE COLECCIÓN (TODOS LOS REGISTROS)"), border=0, align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    cols = [
        ("Clave", 15),
        ("Alias", 28),
        ("Especie Botánica", 32),
        ("Estado", 14),
        ("Ubicación", 20),
        ("Altura", 18),
        ("Linaje Padres", 25),
        ("Injerto", 16),
        ("Fotos", 12),
    ]

    def draw_table_header():
        h_y = pdf.get_y()
        pdf.set_fill_color(*CLR_PRIMARY)
        pdf.rect(15, h_y, pdf.w - 30, 6.5, style="F")

        pdf.set_xy(15, h_y)
        pdf.set_font("Helvetica", "B", 7.0)
        pdf.set_text_color(255, 255, 255)
        for c_title, w in cols:
            align = "C" if c_title in ["Clave", "Estado", "Fotos"] else "L"
            if align == "L":
                pdf.set_x(pdf.get_x() + 1.2)
                pdf.cell(w - 1.2, 6.5, safe_text(c_title), border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
            else:
                pdf.cell(w, 6.5, safe_text(c_title), border=0, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6.5)

    draw_table_header()

    row_h = 6.2
    pdf.set_draw_color(*CLR_BORDER)

    for i, plant in enumerate(plants):
        if pdf.get_y() + row_h > (pdf.h - 18):
            pdf.add_page()
            draw_table_header()

        row_y = pdf.get_y()
        if i % 2 == 1:
            pdf.set_fill_color(*CLR_ROW_ALT)
            pdf.rect(15, row_y, pdf.w - 30, row_h, style="F")

        p_name = safe_text(plant.get("name", ""))
        p_aka = safe_text(plant.get("aka", ""))
        p_species = safe_text(plant.get("species", ""))
        p_status = (plant.get("status") or "OK").upper()
        p_loc = safe_text(plant.get("location", ""))
        p_height = safe_text(plant.get("height", ""))
        p_padres = safe_text(plant.get("padres", ""))
        p_graft = safe_text(plant.get("graft", ""))
        p_photos = plant.get("photos", [])
        photos_count_str = str(len(p_photos)) if isinstance(p_photos, list) else "0"

        cur_x = 15.0

        # 1. Clave (15mm)
        pdf.set_xy(cur_x, row_y)
        pdf.set_text_color(*CLR_UNICORN_PINK)
        c_fit, c_sz = fit_text_to_width(pdf, p_name, cols[0][1], font_family="Helvetica", font_style="B", initial_size=7.5, min_size=5.5, padding=1.0)
        pdf.set_font("Helvetica", "B", c_sz)
        pdf.cell(cols[0][1], row_h, c_fit, border=0, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[0][1]

        # 2. Alias (28mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_PEACH if p_aka else CLR_MUTED)
        aka_display = p_aka if p_aka else "-"
        a_fit, a_sz = fit_text_to_width(pdf, aka_display, cols[1][1] - 2.0, font_family="Helvetica", font_style="B" if p_aka else "", initial_size=7.0, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "B" if p_aka else "", a_sz)
        pdf.cell(cols[1][1] - 1.0, row_h, a_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[1][1]

        # 3. Especie (32mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_DARK)
        sp_display = p_species if p_species else "-"
        sp_fit, sp_sz = fit_text_to_width(pdf, sp_display, cols[2][1] - 2.0, font_family="Helvetica", font_style="I", initial_size=7.0, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "I", sp_sz)
        pdf.cell(cols[2][1] - 1.0, row_h, sp_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[2][1]

        # 4. Estado (14mm)
        badge_w = 11.5
        badge_h = 4.2
        bx = cur_x + ((cols[3][1] - badge_w) / 2)
        by = row_y + ((row_h - badge_h) / 2)
        pdf.draw_status_badge(bx, by, p_status, w=badge_w, h=badge_h)
        cur_x += cols[3][1]

        # 5. Ubicación (20mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_DARK)
        loc_display = p_loc if p_loc else "-"
        loc_fit, l_sz = fit_text_to_width(pdf, loc_display, cols[4][1] - 2.0, font_family="Helvetica", font_style="", initial_size=7.0, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "", l_sz)
        pdf.cell(cols[4][1] - 1.0, row_h, loc_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[4][1]

        # 6. Altura (18mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_DARK)
        h_display = p_height if p_height else "-"
        h_fit, h_sz = fit_text_to_width(pdf, h_display, cols[5][1] - 2.0, font_family="Helvetica", font_style="", initial_size=6.8, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "", h_sz)
        pdf.cell(cols[5][1] - 1.0, row_h, h_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[5][1]

        # 7. Linaje (25mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_DARK)
        pad_display = p_padres if p_padres else "-"
        pad_fit, pad_sz = fit_text_to_width(pdf, pad_display, cols[6][1] - 2.0, font_family="Helvetica", font_style="", initial_size=6.8, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "", pad_sz)
        pdf.cell(cols[6][1] - 1.0, row_h, pad_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[6][1]

        # 8. Injerto (16mm)
        pdf.set_xy(cur_x + 1.0, row_y)
        pdf.set_text_color(*CLR_DARK)
        gr_display = p_graft if p_graft else "-"
        gr_fit, gr_sz = fit_text_to_width(pdf, gr_display, cols[7][1] - 2.0, font_family="Helvetica", font_style="", initial_size=6.8, min_size=5.5, padding=0.5)
        pdf.set_font("Helvetica", "", gr_sz)
        pdf.cell(cols[7][1] - 1.0, row_h, gr_fit, border=0, align="L", new_x=XPos.RIGHT, new_y=YPos.TOP)
        cur_x += cols[7][1]

        # 9. Fotos (12mm)
        pdf.set_xy(cur_x, row_y)
        pdf.set_text_color(*CLR_PRIMARY if photos_count_str != "0" else CLR_MUTED)
        pdf.set_font("Helvetica", "B" if photos_count_str != "0" else "", 7.2)
        pdf.cell(cols[8][1], row_h, photos_count_str, border=0, align="C", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Bottom row line
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_line_width(0.15)
        pdf.line(15, row_y + row_h, pdf.w - 15, row_y + row_h)
        pdf.set_y(row_y + row_h)

    # =========================================================================
    # Individual Plant Technical Dossiers
    # Append the detailed dossier sheet for each specimen
    # =========================================================================
    if len(plants) <= 150:
        for plant in plants:
            pdf.add_page()
            draw_plant_dossier_content(pdf, plant)
    else:
        # For ultra-large collections (>150), add informational notice page
        pdf.add_page()
        pdf.set_y(50)
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(*CLR_PRIMARY)
        pdf.cell(0, 10, safe_text("ÍNDICE GENERAL COMPLETO REGISTRADO"), border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(0, 8, safe_text(f"Se han indexado los {len(plants)} ejemplares de la base de datos con todos sus atributos."), border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.cell(0, 8, safe_text("Los expedientes con galería de fotos en alta resolución pueden descargarse individualmente desde el catálogo."), border=0, align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())
