"""
Plantation - High-performance, ink-friendly PDF generation using fpdf2.
Replaces all legacy HTML/WeasyPrint rendering with fast, vector-crisp PDF output.
"""

import os
from datetime import datetime
from fpdf import FPDF
from PIL import Image
import db

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images")

# Botanical ink-friendly palette
CLR_PRIMARY = (26, 71, 42)      # Deep Forest Green
CLR_PRIMARY_LIGHT = (240, 247, 241) # Very soft green tint
CLR_DARK = (15, 23, 42)          # Slate Charcoal
CLR_MUTED = (100, 116, 139)      # Slate Gray
CLR_BORDER = (203, 213, 225)     # Light Slate Border
CLR_ROW_ALT = (248, 250, 252)    # Subtle table alternate row
CLR_PEACH = (194, 65, 12)        # Terracotta / Peach accent for Alias
CLR_UNICORN_PINK = (255, 102, 204) # #ff66cc - Unicorn Pink for Plant Keys
CLR_OK_BG = (220, 252, 231)      # Soft green badge
CLR_OK_TXT = (22, 101, 52)
CLR_NOTOK_BG = (254, 226, 226)   # Soft red badge
CLR_NOTOK_TXT = (220, 38, 38)     # Bright crimson red text


def safe_text(val) -> str:
    """Sanitize strings to ensure complete compatibility with core FPDF fonts."""
    if val is None:
        return ""
    text = str(val).strip()
    replacements = {
        "—": "-", "–": "-", "―": "-", "“": '"', "”": '"', "‘": "'", "’": "'",
        "•": "*", "…": "...", "→": "->", "←": "<-", "✓": "OK", "✕": "X",
        "\u2014": "-", "\u2013": "-", "\u2012": "-", "\u2010": "-"
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        return text.encode("latin-1", "replace").decode("latin-1")


class BotanicalPDF(FPDF):
    """Custom FPDF document with official botanical header, footer, and utility components."""

    def __init__(self, title_text="EXPEDIENTE TÉCNICO BOTÁNICO", **kwargs):
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
        self.cell(100, 6, safe_text("[ PLANTATION ] SISTEMA BOTÁNICO"), border=0, ln=0, align="L")
        
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*CLR_MUTED)
        date_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cell(0, 6, safe_text(f"Emitido: {date_str}"), border=0, ln=1, align="R")

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

        self.set_font("Helvetica", "B", 7)
        self.set_text_color(*CLR_MUTED)
        self.cell(100, 5, safe_text(f"EXPEDIENTE TÉCNICO - {self.doc_title.upper()}"), border=0, ln=0, align="L")

        self.set_font("Helvetica", "", 7)
        self.cell(0, 5, safe_text(f"Página {self.page_no()} de {{nb}}"), border=0, ln=1, align="R")

    def draw_status_badge(self, x, y, status, w=22, h=6):
        """Draw an ink-friendly health status badge (OK or notOK)."""
        is_ok = (status or "").upper() == "OK"
        bg_col = CLR_OK_BG if is_ok else CLR_NOTOK_BG
        txt_col = CLR_OK_TXT if is_ok else CLR_NOTOK_TXT
        label = "● OK" if is_ok else "● notOK"

        self.set_fill_color(*bg_col)
        self.set_draw_color(*txt_col)
        self.set_line_width(0.2)
        self.rect(x, y, w, h, style="FD")

        self.set_xy(x, y)
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*txt_col)
        self.cell(w, h, safe_text(label), border=0, align="C")


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
    # Outer frame
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
                # Width constrained
                draw_w = inner_w
                draw_h = inner_w / ratio
                draw_x = x + 2
                draw_y = y + 2 + ((inner_h - draw_h) / 2)
            else:
                # Height constrained
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

    # Caption bar at bottom of box
    if caption:
        pdf.set_xy(x, y + h - caption_h)
        pdf.set_fill_color(*CLR_ROW_ALT)
        pdf.rect(x, y + h - caption_h, w, caption_h, style="F")
        pdf.set_xy(x + 2, y + h - caption_h)
        pdf.set_font("Helvetica", "I", 7)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(w - 4, caption_h, safe_text(caption), border=0, align="C")


def generate_single_plant_pdf(plant: dict) -> bytes:
    """Generate a single-plant technical dossier PDF using fpdf2.
    Ensures:
      1. General info (header, specifications, fertilization, observations) is ALWAYS on Page 1.
      2. All photos are rendered in standardized frames at the bottom of the dossier,
         fitting into Page 1 if possible, or gracefully expanding onto additional pages.
    """
    pdf = BotanicalPDF(title_text=f"EJEMPLAR {plant.get('name', 'N/A')}")
    pdf.add_page()

    name = safe_text(plant.get("name", "N/A"))
    aka = safe_text(plant.get("aka", ""))
    species = safe_text(plant.get("species", "Sin especie registrada"))
    status = plant.get("status", "OK")

    box_w = pdf.w - 30  # 180mm printable width

    # =========================================================================
    # 1. HEADER CARD (Always on Page 1)
    # =========================================================================
    start_y = pdf.get_y()
    pdf.set_fill_color(*CLR_PRIMARY_LIGHT)
    pdf.set_draw_color(*CLR_PRIMARY)
    pdf.set_line_width(0.4)
    pdf.rect(15, start_y, box_w, 24, style="FD")

    # Clave
    pdf.set_xy(20, start_y + 3)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*CLR_UNICORN_PINK)
    pdf.cell(50, 8, f"[{name}]", border=0, ln=0, align="L")

    # Alias prominently next to clave
    if aka:
        pdf.set_xy(65, start_y + 4)
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*CLR_PEACH)
        pdf.cell(75, 7, f'"{aka}"', border=0, ln=0, align="L")

    # Status Badge top right
    pdf.draw_status_badge(pdf.w - 45, start_y + 4, status, w=24, h=7)

    # Species subheader
    pdf.set_xy(20, start_y + 13)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*CLR_DARK)
    pdf.cell(box_w - 10, 6, species, border=0, ln=1, align="L")

    pdf.set_y(start_y + 27)

    # =========================================================================
    # 2. ESPECIFICACIONES  (Full-width 2-column grid, always on Page 1)
    # =========================================================================
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("ESPECIFICACIONES"), border=0, ln=1)

    col_w = (box_w - 4) / 2  # 88mm each
    row_h = 5.8
    specs_left = [
        ("Clave", name),
        ("Fecha Siembra / Esqueje", safe_text(plant.get("sowing_cutting_date") or "—")),
        ("Edad Registrada", safe_text(db.calculate_age_display(plant.get("sowing_cutting_date")))),
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
    for i in range(max(len(specs_left), len(specs_right))):
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
            pdf.cell(40, row_h, safe_text(lbl_l), border=0, ln=0)

            pdf.set_font("Helvetica", "B" if lbl_l == "Alias" and val_l != "—" else "", 8)
            pdf.set_text_color(*(CLR_PEACH if lbl_l == "Alias" and val_l != "—" else CLR_DARK))
            pdf.cell(col_w - 40, row_h, safe_text(val_l), border=0, ln=0)

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
            pdf.cell(38, row_h, safe_text(lbl_r), border=0, ln=0)

            pdf.set_font("Helvetica", "", 8)
            pdf.set_text_color(*CLR_DARK)
            pdf.cell(col_w - 38, row_h, safe_text(val_r), border=0, ln=1)

    pdf.set_y(table_y + (max(len(specs_left), len(specs_right)) * row_h) + 4)

    # =========================================================================
    # 3. FERTILIZACIÓN & TRATAMIENTOS (Always on Page 1)
    # =========================================================================
    fertilizante = safe_text(plant.get("fertilizante") or "").strip()
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("FERTILIZACIÓN & TRATAMIENTOS"), border=0, ln=1)

    fert_lines = max(1, len(fertilizante.split("\n"))) if fertilizante else 1
    fert_box_h = max(18, (fert_lines * 4.8) + 6)
    fert_box_y = pdf.get_y()
    pdf.set_draw_color(*CLR_BORDER)
    pdf.set_fill_color(*CLR_ROW_ALT)
    pdf.rect(15, fert_box_y, box_w, fert_box_h, style="FD")

    pdf.set_xy(18, fert_box_y + 3)
    pdf.set_font("Helvetica", "", 8.5)
    if fertilizante:
        pdf.set_text_color(*CLR_DARK)
        pdf.multi_cell(box_w - 6, 4.6, fertilizante)
    else:
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(box_w - 6, 6, safe_text("Sin tratamientos ni fertilización registrados para este ejemplar."), border=0)

    pdf.set_y(fert_box_y + fert_box_h + 4)

    # =========================================================================
    # 4. OBSERVACIONES (Always on Page 1)
    # =========================================================================
    comentarios = safe_text(plant.get("comentarios") or "").strip()
    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(box_w, 5.5, safe_text("OBSERVACIONES & NOTAS "), border=0, ln=1)

    obs_lines = max(1, len(comentarios.split("\n"))) if comentarios else 1
    obs_box_h = max(20, (obs_lines * 4.8) + 6)
    obs_box_y = pdf.get_y()
    pdf.set_draw_color(*CLR_BORDER)
    pdf.set_fill_color(*CLR_ROW_ALT)
    pdf.rect(15, obs_box_y, box_w, obs_box_h, style="FD")

    pdf.set_xy(18, obs_box_y + 3)
    pdf.set_font("Helvetica", "", 8.5)
    if comentarios:
        pdf.set_text_color(*CLR_DARK)
        pdf.multi_cell(box_w - 6, 4.6, comentarios)
    else:
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(box_w - 6, 6, safe_text("Sin observaciones registradas para este ejemplar."), border=0)

    pdf.set_y(obs_box_y + obs_box_h + 5)

    # =========================================================================
    # 5. REGISTRO FOTOGRÁFICO DE ARCHIVO (At the bottom of the file)
    # =========================================================================
    all_images = get_all_valid_images(plant)
    img_count = len(all_images)

    pdf.set_font("Helvetica", "B", 9.5)
    pdf.set_text_color(*CLR_PRIMARY)
    header_caption = f"REGISTRO FOTOGRÁFICO DE ARCHIVO ({img_count} FOTOGRAFÍA{'S' if img_count != 1 else ''})" if img_count > 0 else "REGISTRO FOTOGRÁFICO DE ARCHIVO"
    pdf.cell(box_w, 5.5, safe_text(header_caption), border=0, ln=1)

    current_y = pdf.get_y()
    space_left = 270 - current_y

    if img_count == 0:
        # Standard placeholder frame
        ph_h = 24
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_fill_color(*CLR_ROW_ALT)
        pdf.rect(15, current_y, box_w, ph_h, style="FD")
        pdf.set_xy(15, current_y + 8)
        pdf.set_font("Helvetica", "I", 8.5)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(box_w, 7, safe_text("Sin registro fotográfico adjunto para este ejemplar."), border=0, align="C")

    elif img_count == 1:
        # Single standardized centered image
        img_w = 110
        img_h = 75
        if space_left < (img_h + 10):
            pdf.add_page()
            current_y = pdf.get_y()
        img_x = 15 + (box_w - img_w) / 2
        caption_txt = f"{os.path.basename(all_images[0])} — Ejemplar [{name}]"
        draw_standardized_image_frame(pdf, all_images[0], img_x, current_y, img_w, img_h, caption_txt)

    elif img_count == 2:
        # Two standardized images side-by-side
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
        # 3 or more images: Standard 2-column grid
        col_gap = 6
        img_w = (box_w - col_gap) / 2  # 87mm each

        # Try to fit 3-4 images in remaining space if sufficient, else use standard 62mm height
        if img_count <= 4 and space_left >= (2 * 54 + col_gap + 8):
            img_h = 54
        else:
            img_h = 62

        for idx, img_p in enumerate(all_images):
            col = idx % 2
            # Check if starting a new row requires page break
            if col == 0 and idx > 0:
                current_y += img_h + 6

            if col == 0 and (current_y + img_h + 8 > 270):
                pdf.add_page()
                current_y = pdf.get_y()

            img_x = 15 + col * (img_w + col_gap)
            caption_txt = f"Foto {idx + 1}/{img_count}: {os.path.basename(img_p)}"
            draw_standardized_image_frame(pdf, img_p, img_x, current_y, img_w, img_h, caption_txt)

    return bytes(pdf.output())


def generate_catalog_pdf(plants: list, title: str = "CATÁLOGO GENERAL DE EJEMPLARES") -> bytes:
    """Generate a complete catalog PDF using fpdf2."""
    pdf = BotanicalPDF(title_text=title)
    pdf.add_page()

    total_count = len(plants)
    ok_count = sum(1 for p in plants if (p.get("status") or "").upper() == "OK")
    not_ok_count = total_count - ok_count
    with_alias_count = sum(1 for p in plants if (p.get("aka") or "").strip())

    # Summary Statistics Ribbon
    start_y = pdf.get_y()
    card_w = (pdf.w - 30 - 9) / 4  # 4 cards
    stats = [
        ("TOTAL EJEMPLARES", str(total_count), CLR_PRIMARY),
        ("ESTADO OK", str(ok_count), CLR_OK_TXT),
        ("ESTADO notOK", str(not_ok_count), CLR_NOTOK_TXT),
        ("CON ALIAS", str(with_alias_count), CLR_PEACH),
    ]

    for i, (title, val, val_col) in enumerate(stats):
        cx = 15 + (i * (card_w + 3))
        pdf.set_fill_color(*CLR_PRIMARY_LIGHT)
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(cx, start_y, card_w, 14, style="FD")

        pdf.set_xy(cx, start_y + 2)
        pdf.set_font("Helvetica", "B", 6.5)
        pdf.set_text_color(*CLR_MUTED)
        pdf.cell(card_w, 3.5, safe_text(title), border=0, align="C")

        pdf.set_xy(cx, start_y + 6)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*val_col)
        pdf.cell(card_w, 6, safe_text(val), border=0, align="C")

    pdf.set_y(start_y + 18)

    # Index Table Section
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(*CLR_PRIMARY)
    pdf.cell(0, 6, safe_text("ÍNDICE DE COLECCIÓN"), border=0, ln=1)

    # Table Headers
    cols = [
        ("Clave", 22),
        ("Alias", 32),
        ("Especie Botánica", 54),
        ("Estado", 20),
        ("Ubicación", 28),
        ("Siembra / Esqueje", 24)
    ]
    
    header_y = pdf.get_y()
    pdf.set_fill_color(*CLR_PRIMARY)
    pdf.rect(15, header_y, pdf.w - 30, 6.5, style="F")

    pdf.set_xy(15, header_y)
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(255, 255, 255)
    for title, w in cols:
        pdf.cell(w, 6.5, safe_text(title), border=0, ln=0, align="C" if title in ["Clave", "Estado"] else "L")
    pdf.ln(6.5)

    # Table Rows
    pdf.set_draw_color(*CLR_BORDER)
    for i, plant in enumerate(plants):
        # Auto-page break handled gracefully by FPDF
        if pdf.get_y() > pdf.h - 22:
            pdf.add_page()
            # Redraw mini table header
            h_y = pdf.get_y()
            pdf.set_fill_color(*CLR_PRIMARY)
            pdf.rect(15, h_y, pdf.w - 30, 6.5, style="F")
            pdf.set_xy(15, h_y)
            pdf.set_font("Helvetica", "B", 7.5)
            pdf.set_text_color(255, 255, 255)
            for title, w in cols:
                pdf.cell(w, 6.5, safe_text(title), border=0, ln=0, align="C" if title in ["Clave", "Estado"] else "L")
            pdf.ln(6.5)

        row_y = pdf.get_y()
        if i % 2 == 1:
            pdf.set_fill_color(*CLR_ROW_ALT)
            pdf.rect(15, row_y, pdf.w - 30, 5.8, style="F")

        p_name = safe_text(plant.get("name", ""))
        p_aka = safe_text(plant.get("aka", ""))
        p_species = safe_text(plant.get("species", ""))
        p_status = (plant.get("status") or "OK").upper()
        p_loc = safe_text(plant.get("location", ""))
        p_date = safe_text(plant.get("sowing_cutting_date", ""))

        pdf.set_font("Helvetica", "B", 7.5)
        pdf.set_text_color(*CLR_UNICORN_PINK)
        pdf.cell(cols[0][1], 5.8, p_name, border=0, ln=0, align="C")

        pdf.set_font("Helvetica", "B" if p_aka else "", 7.5)
        pdf.set_text_color(*CLR_PEACH if p_aka else CLR_MUTED)
        pdf.cell(cols[1][1], 5.8, p_aka or "—", border=0, ln=0, align="L")

        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*CLR_DARK)
        pdf.cell(cols[2][1], 5.8, p_species[:32], border=0, ln=0, align="L")

        # Estado cell
        is_ok = p_status == "OK"
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(*(CLR_OK_TXT if is_ok else CLR_NOTOK_TXT))
        pdf.cell(cols[3][1], 5.8, "OK" if is_ok else "notOK", border=0, ln=0, align="C")

        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*CLR_DARK)
        pdf.cell(cols[4][1], 5.8, p_loc[:16] or "—", border=0, ln=0, align="L")
        pdf.cell(cols[5][1], 5.8, p_date or "—", border=0, ln=1, align="L")

        # Subtle row line
        pdf.set_draw_color(*CLR_BORDER)
        pdf.set_line_width(0.15)
        pdf.line(15, pdf.get_y(), pdf.w - 15, pdf.get_y())

    return bytes(pdf.output())
