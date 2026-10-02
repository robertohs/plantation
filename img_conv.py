"""
Plantation - Photo Validation & AVIF Conversion Storage Logic
Handles multi-photo naming (<KEY>_<number>.<ext>), size validation (<=10MB),
PIL image verification, AVIF conversion, and disk cleanup.
"""

import io
import os
import re
from typing import List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
    HAS_PILLOW_HEIF = True
except Exception:
    HAS_PILLOW_HEIF = False

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Images")
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def ensure_images_dir() -> str:
    """Ensures Images directory exists and returns its absolute path."""
    os.makedirs(IMAGES_DIR, exist_ok=True)
    return IMAGES_DIR


def get_next_photo_filename(key: str, extension: str = "avif") -> str:
    """
    Finds the next sequential filename for a given plant key in the format:
    <KEY>_<number>.<ext>
    """
    ensure_images_dir()
    existing_files = os.listdir(IMAGES_DIR)
    pattern = re.compile(rf"^{re.escape(key)}_(\d+)\.[a-zA-Z0-9]+$", re.IGNORECASE)

    max_num = 0
    for f in existing_files:
        m = pattern.match(f)
        if m:
            try:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass

    next_num = max_num + 1
    return f"{key}_{next_num}.{extension}"


def validate_and_save_photo(
    key: str,
    file_bytes: bytes,
    original_filename: str = ""
) -> Tuple[bool, str, str]:
    """
    Validates uploaded photo bytes:
    1. Size <= 10MB
    2. Valid image format (JPEG, PNG, WEBP, AVIF, HEIC, TIFF)
    3. Converts and optimizes to AVIF (or WebP if AVIF writer unavailable)
    4. Saves to Images/<KEY>_<number>.avif

    Returns (success, filename_or_empty, status_message).
    """
    ensure_images_dir()

    # 1. File size check
    if len(file_bytes) > MAX_FILE_SIZE:
        return False, "", "La imagen supera el límite permitido de 10 MB."

    if len(file_bytes) == 0:
        return False, "", "El archivo de imagen está vacío."

    # 2. Image integrity verification & processing
    img_buffer = None
    img = None
    try:
        img_buffer = io.BytesIO(file_bytes)
        img = Image.open(img_buffer)
        img.verify()
        # Re-open after verify() because verify() exhausts file pointer
        img_buffer.seek(0)
        img = Image.open(img_buffer)

        # 3. Normalization (convert to RGB if RGBA/P/CMYK for compatibility)
        if img.mode in ("RGBA", "LA"):
            pass
        elif img.mode != "RGB":
            img = img.convert("RGB")

        # Resize if extremely large (preserve aspect ratio, max 2048x2048)
        max_dim = 2048
        if img.width > max_dim or img.height > max_dim:
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        # 4. Save to optimized WebP format with universal browser compatibility
        saved_filename = ""
        try:
            target_filename = get_next_photo_filename(key, "webp")
            target_path = os.path.join(IMAGES_DIR, target_filename)
            img.save(target_path, "WEBP", quality=88)
            saved_filename = target_filename
        except Exception:
            # Fallback to standard JPEG if WEBP fails
            try:
                target_filename = get_next_photo_filename(key, "jpg")
                target_path = os.path.join(IMAGES_DIR, target_filename)
                rgb_img = img.convert("RGB") if img.mode != "RGB" else img
                rgb_img.save(target_path, "JPEG", quality=90)
                saved_filename = target_filename
            except Exception as e2:
                return False, "", f"Error al guardar la imagen optimizada: {str(e2)}"

        return True, saved_filename, f"Foto '{saved_filename}' guardada correctamente."

    except Exception as e:
        return False, "", f"Error al procesar la imagen: {str(e)}"
    finally:
        if img is not None:
            try:
                img.close()
            except Exception:
                pass
        if img_buffer is not None:
            try:
                img_buffer.close()
            except Exception:
                pass


def delete_photo_file(filename: str) -> bool:
    """Removes a single photo file from the Images directory."""
    if not filename:
        return False
    # Sanitize to prevent path traversal
    safe_name = os.path.basename(filename)
    path = os.path.join(IMAGES_DIR, safe_name)
    if os.path.exists(path) and os.path.isfile(path):
        try:
            os.remove(path)
            return True
        except OSError:
            return False
    return False


def cleanup_plant_photos(filenames: List[str]) -> int:
    """Removes a list of photo filenames from disk. Returns count of deleted files."""
    count = 0
    for fn in filenames:
        if delete_photo_file(fn):
            count += 1
    return count


def generate_seed_photos_if_missing() -> None:
    """
    Creates handsome botanical vector-style preview graphics in Images/
    for the initial seeded specimens if they do not yet exist on disk.
    """
    ensure_images_dir()

    seed_specs = [
        ("A1_1.webp", "A1", "Ariocarpus kotschoubeyanus", "#24273a", "#a6da95", "ROSE MAGENTA FLOWER"),
        ("A1_2.webp", "A1", "Ariocarpus kotschoubeyanus", "#1e1e2e", "#8aadf4", "TUBERCLE DETAIL"),
        ("A1_3.webp", "A1", "Ariocarpus kotschoubeyanus", "#24273a", "#f5bde6", "APICAL WOOLLY CROWN"),
        ("900_1.webp", "900", "Lophophora caespitosa", "#24273a", "#8aadf4", "14 APICAL CLUSTERS"),
        ("A2_1.webp", "A2", "Ariocarpus retusus x trigonus", "#24273a", "#a6da95", "GRAFTED SPECIMEN"),
        ("A33_1.webp", "A33", "Ariocarpus fissuratus", "#24273a", "#c6a0f6", "LIVING ROCK FOSSIL"),
        ("B12_1.webp", "B12", "Astrophytum 'Super Kabuto'", "#362629", "#eed49f", "ISOLATION QUARANTINE"),
        ("K7_1.webp", "K7", "Pachypodium namaquanum", "#24273a", "#8bd5ca", "ARID SUCCULENT STEM"),
        ("A22_1.webp", "A22", "Ariocarpus bravoanus hintonii", "#24273a", "#a6da95", "FLAT DISCOID TUBERCLES"),
        ("K-12_1.webp", "K-12", "Pachypodium brevicaule", "#1e1e2e", "#eed49f", "MADAGASCAR SILVER CUSHION"),
        ("C05_1.webp", "C05", "Copiapoa columna-alba", "#1e2030", "#eed49f", "WHITE-WAX PRUINOSE STEM"),
        ("E01_1.webp", "E01", "Euphorbia obesa", "#24273a", "#a6da95", "BASEBALL GEOMETRIC RIBS"),
        ("O08_1.webp", "O08", "Obregonia denegrii", "#1e1e2e", "#8aadf4", "ARTICHOKE SPIRAL TUBERCLES"),
        ("T14_1.webp", "T14", "Turbinicarpus valdezianus", "#24273a", "#c6a0f6", "FEATHERED SPINE COATING"),
        ("L02_1.webp", "L02", "Lophophora williamsii texana", "#362629", "#ed8796", "QUARANTINE OBSERVATION"),
        ("F09_1.webp", "F09", "Ferocactus pilosus", "#2a1e24", "#ee99a0", "RUBY RED SPINE CLUSTER"),
        ("M03_1.webp", "M03", "Mammillaria luethyi", "#1e1e2e", "#f5bde6", "MICROSCOPIC RADIAL ROSETTES"),
        ("S10_1.webp", "S10", "Strombocactus disciformis", "#24273a", "#8bd5ca", "DISCIFORM LIMESTONE SPECIMEN"),
    ]

    for filename, key, species, bg_color, accent_color, subtitle in seed_specs:
        path = os.path.join(IMAGES_DIR, filename)
        if not os.path.exists(path):
            try:
                # Create an 800x600 dark botanical card
                img = Image.new("RGB", (800, 600), color=bg_color)
                draw = ImageDraw.Draw(img)

                # Draw technical frame & crosshairs
                draw.rectangle([(20, 20), (780, 580)], outline="#494d64", width=2)
                draw.line([(400, 30), (400, 50)], fill=accent_color, width=2)
                draw.line([(400, 550), (400, 570)], fill=accent_color, width=2)
                draw.line([(30, 300), (50, 300)], fill=accent_color, width=2)
                draw.line([(750, 300), (770, 300)], fill=accent_color, width=2)

                # Specimen circular botanical badge
                draw.ellipse([(280, 140), (520, 380)], outline=accent_color, width=3)
                draw.ellipse([(300, 160), (500, 360)], outline="#5b6078", width=1)

                # Geometric botanical stylized star/rosette
                points = [
                    (400, 170), (420, 240), (490, 230), (440, 280),
                    (480, 340), (410, 320), (400, 370), (390, 320),
                    (320, 340), (360, 280), (310, 230), (380, 240)
                ]
                draw.polygon(points, fill=None, outline=accent_color, width=2)

                # Text annotations
                draw.text((40, 40), f"[KEY: {key}]", fill=accent_color)
                draw.text((40, 65), f"SPECIES: {species.upper()}", fill="#cdd6f4")
                draw.text((40, 530), f"SPECIMEN RECORD // {subtitle}", fill="#a5adcb")
                draw.text((640, 530), "PLANTATION", fill=accent_color)

                img.save(path, "WEBP", quality=90)
            except Exception:
                pass
