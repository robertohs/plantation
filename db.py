"""
Plantation - Centralized Database Engine
Handles SQLite operations, table schema creation, migrations, and CRUD queries.
Database file stored in DB/plantation.db.
"""

import json
import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DB")
DB_PATH = os.path.join(DB_DIR, "plantation.db")

VALID_STATUSES = ["OK", "notOK"]


def get_connection() -> sqlite3.Connection:
    """Returns a thread-safe connection to SQLite with row_factory configured."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def normalize_status(val: Optional[str]) -> str:
    """Normalizes any status representation strictly to 'OK' or 'notOK'."""
    if not val:
        return "OK"
    s = str(val).strip().lower()
    return "OK" if s in ("ok", "triving", "saludable", "prospero", "próspero", "healthy", "good", "bien") else "notOK"


def clean_key(key: str) -> str:
    """Normalizes and validates plant key (alphanumeric, max 20 chars)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', (key or '')).strip().upper()[:20]


def parse_plant_date(s: Optional[str]) -> Optional[datetime]:
    """Parses a date string in ISO YYYY-MM-DD or standard formats."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    for pattern, group_order in [
        (r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', (1, 2, 3)),
        (r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', (3, 2, 1)),
        (r'(\d{4})[-/](\d{1,2})', (1, 2, None)),
    ]:
        m = re.search(pattern, s)
        if m:
            try:
                y = int(m.group(group_order[0]))
                mo = int(m.group(group_order[1]))
                d = int(m.group(group_order[2])) if group_order[2] else 1
                return datetime(y, mo, d)
            except ValueError:
                pass
    return None


def get_plant_age_months(sowing_cutting_date: Optional[str], graft: Optional[str] = "", now: Optional[datetime] = None) -> Optional[int]:
    """Returns the plant age in total integer months, or None if unknown."""
    d_start = parse_plant_date(sowing_cutting_date) or (parse_plant_date(graft) if graft else None)
    if not d_start:
        return None
    now = now or datetime.now()
    if d_start > now:
        return 0
    diff_months = (now.year - d_start.year) * 12 + (now.month - d_start.month)
    if now.day < d_start.day:
        diff_months -= 1
    return max(0, diff_months)


def calculate_plant_age(sowing_cutting_date: Optional[str], graft: Optional[str] = "", now: Optional[datetime] = None) -> Tuple[str, str]:
    """Returns (short_display, detailed_display) for plant age."""
    months = get_plant_age_months(sowing_cutting_date, graft, now)
    if months is None:
        return "—", "Sin fecha de siembra o injerto"
    if months == 0:
        return "0 meses", "0 meses (Recién sembrada / injertada)"
    if months < 12:
        m_lbl = f"{months} mes" if months == 1 else f"{months} meses"
        return m_lbl, f"{m_lbl} (Total: {months} meses)"
    y = months // 12
    rem = months % 12
    y_lbl = f"{y} año" if y == 1 else f"{y} años"
    if rem == 0:
        return f"{y_lbl} ({months} m)", f"{y_lbl} (Total: {months} meses)"
    rem_lbl = f"{rem} mes" if rem == 1 else f"{rem} meses"
    return f"{y_lbl}, {rem_lbl} ({months} m)", f"{y_lbl}, {rem_lbl} (Total: {months} meses)"


def calculate_age_display(sowing_cutting_date: Optional[str], graft: Optional[str] = "") -> str:
    """Returns the primary short string representation of plant age."""
    short, _ = calculate_plant_age(sowing_cutting_date, graft)
    return short


# ==============================================================================
# HEIGHT FILTER CONFIGURATION & HELPER FUNCTIONS
# Readable & easily extensible definitions for height filtering
# (< 15 cm, 15 > x < 35 [15 to 35 cm], 35+ cm)
# ==============================================================================

def extract_height_cm(height_str: Optional[str]) -> Optional[float]:
    """
    Extracts numerical height in centimeters from botanical strings such as:
      - '2025-06-15 - 4.8 cm'
      - '12.0 cm'
      - '28.5'
      - '42 cm'
    Returns float (in cm) or None if not measurable.
    """
    if not height_str or not isinstance(height_str, str):
        return None
    s = height_str.strip()
    if not s:
        return None

    # Format 1: Explicit 'cm' unit (e.g., '4.8 cm', '12cm', '28.5 cm')
    cm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*cm\b', s, re.IGNORECASE)
    if cm_match:
        try:
            return float(cm_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    # Format 2: Hyphenated record 'DATE - HEIGHT' (e.g. '2025-06-15 - 4.8')
    if '-' in s:
        last_chunk = s.split('-')[-1].strip()
        num_match = re.search(r'(\d+(?:[.,]\d+)?)', last_chunk)
        if num_match:
            try:
                return float(num_match.group(1).replace(',', '.'))
            except ValueError:
                pass

    # Format 3: Standalone number
    direct_match = re.search(r'^\s*(\d+(?:[.,]\d+)?)\s*$', s)
    if direct_match:
        try:
            return float(direct_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    return None


# Readable height filter ranges - easily adjusted or extended in the future
HEIGHT_FILTER_RANGES = {
    # Range 1: < 15 cm
    "less_15": {
        "label": "< 15 cm",
        "description": "Plantas menores a 15 cm",
        "predicate": lambda h: h < 15.0
    },
    # Range 2: 15 > x < 35 (Between 15 cm and 35 cm)
    "15_to_35": {
        "label": "15 - 35 cm",
        "description": "Plantas entre 15 cm y 35 cm",
        "predicate": lambda h: 15.0 <= h < 35.0
    },
    # Range 3: 35+ cm
    "35_plus": {
        "label": "35+ cm",
        "description": "Plantas de 35 cm o más",
        "predicate": lambda h: h >= 35.0
    }
}


def matches_height_filter(height_str: Optional[str], filter_key: str) -> bool:
    """
    Checks if a plant's height string matches the selected filter key.
    Accepts:
      - 'less_15', '<15', '< 15', '< 15 cm'
      - '15_to_35', '15-35', '15_35', '15 > x < 35'
      - '35_plus', '35+', '+35', '35+'
    """
    if not filter_key:
        return True
    key = filter_key.strip().lower()
    if key in ("all", "", "*", "todas", "todos"):
        return True

    h_cm = extract_height_cm(height_str)
    if h_cm is None:
        return False

    # Normalize aliases to canonical dictionary key
    if key in ("less_15", "<15", "< 15", "less_than_15", "menor_15", "<15cm", "< 15 cm"):
        canonical = "less_15"
    elif key in ("15_to_35", "15-35", "15_35", "15to35", "15_x_35", "15 > x < 35", "15>x<35"):
        canonical = "15_to_35"
    elif key in ("35_plus", "35+", "35plus", "mas_35", "+35", "35+cm", "35+ cm"):
        canonical = "35_plus"
    else:
        canonical = key

    range_cfg = HEIGHT_FILTER_RANGES.get(canonical)
    if range_cfg and "predicate" in range_cfg:
        return range_cfg["predicate"](h_cm)

    return True


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite row into a dict, deserializing photos and normalizing values."""
    d = dict(row)
    d["aka"] = d.get("aka") or ""
    d["height"] = d.get("height") or ""
    d["status"] = normalize_status(d.get("status"))
    try:
        d["photos"] = json.loads(d["photos"]) if d.get("photos") else []
    except Exception:
        d["photos"] = []
    return d


def init_db() -> None:
    """Initializes the database schema, indexes, and ensures default records."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                name TEXT PRIMARY KEY,
                species TEXT NOT NULL,
                aka TEXT DEFAULT '',
                location TEXT DEFAULT '',
                height TEXT DEFAULT '',
                registration_date TEXT DEFAULT '',
                padres TEXT DEFAULT '',
                sowing_cutting_date TEXT DEFAULT '',
                graft TEXT DEFAULT '',
                last_pruned TEXT DEFAULT '',
                last_repotted TEXT DEFAULT '',
                fertilizante TEXT DEFAULT '',
                photos TEXT DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'OK',
                comentarios TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        try:
            conn.execute("ALTER TABLE plants ADD COLUMN aka TEXT DEFAULT '';")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE plants ADD COLUMN height TEXT DEFAULT '';")
        except sqlite3.OperationalError:
            pass

        for col in ("species", "status", "location", "aka", "height"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_plants_{col} ON plants({col});")
        conn.commit()

    seed_default_data()


def seed_default_data() -> None:
    """Seeds default curated botanical records into the database."""
    default_plants = [
        {
            "name": "A1",
            "species": "Ariocarpus kotschoubeyanus",
            "aka": "estrella",
            "location": "Invernadero A - Banco 1",
            "height": "2025-06-15 - 4.8 cm",
            "registration_date": "2024-03-12",
            "padres": "Desconocido (Ejemplar Madre Silvestre)",
            "sowing_cutting_date": "2023-01-10",
            "graft": "Sin injerto (Raíz propia napiforme)",
            "last_pruned": "2025-11-04 (Limpieza raíces secundarias)",
            "last_repotted": "2025-02-18 (Sustrato mineral 80% pómice)",
            "fertilizante": "2025-06-01 NPK 4-10-15 dilución 25% + Quelato de Hierro",
            "photos": ["A1_1.webp", "A1_2.webp"],
            "status": "OK",
            "comentarios": "Floración rosa magenta observada en otoño. Crecimiento lento pero saludable con tubérculos bien definidos."
        },
        {
            "name": "900",
            "species": "Lophophora williamsii var. caespitosa",
            "aka": "golden",
            "location": "Invernadero A - Banco 3",
            "height": "2025-08-20 - 7.5 cm",
            "registration_date": "2024-05-20",
            "padres": "Clon C-89 x Semilla Autóctona",
            "sowing_cutting_date": "2023-04-15",
            "graft": "Sin injerto",
            "last_pruned": "2025-08-12 (Separación de hijuelos)",
            "last_repotted": "2025-01-05 (Maceta barro artesanal)",
            "fertilizante": "2025-05-15 Extracto de algas marinas bioestimulante",
            "photos": ["900_1.webp"],
            "status": "OK",
            "comentarios": "Muestra 14 cabezas compactas. Lana apical densa y sana."
        },
        {
            "name": "A2",
            "species": "Ariocarpus retusus subsp. trigonus",
            "aka": "ocaso",
            "location": "Invernadero A - Banco 1",
            "height": "2025-10-12 - 12.0 cm",
            "registration_date": "2024-09-01",
            "padres": "A1 + 900",
            "sowing_cutting_date": "2024-06-11",
            "graft": "Injerto sobre Myrtillocactus geometrizans",
            "last_pruned": "2025-10-15 (Poda de rebrotes del patrón)",
            "last_repotted": "2024-11-20 (Trasplante de patrón)",
            "fertilizante": "2025-07-20 Fertilizante cactus bajo en nitrógeno",
            "photos": ["A2_1.webp"],
            "status": "OK",
            "comentarios": "Cruce experimental exitoso entre A1 y 900. Velocidad de desarrollo acelerada gracias al injerto vigoroso."
        },
        {
            "name": "B12",
            "species": "Astrophytum asterias cv. Super Kabuto",
            "aka": "darkRed",
            "location": "Mesa de Cuarentena Este",
            "height": "2025-01-14 - 5.2 cm",
            "registration_date": "2025-01-14",
            "padres": "SK-White x Star Shape 4",
            "sowing_cutting_date": "2024-02-01",
            "graft": "Sin injerto",
            "last_pruned": "No aplica",
            "last_repotted": "2025-01-14 (Sustrato esterilizado)",
            "fertilizante": "Sin fertilizante reciente (Bajo tratamiento fúngico)",
            "photos": ["B12_1.webp"],
            "status": "notOK",
            "comentarios": "Mancha marrón sospechosa en la costilla apical 3. Tratado con oxicloruro de cobre preventivo en cuarentena."
        },
        {
            "name": "K7",
            "species": "Pachypodium namaquanum",
            "aka": "halfmens",
            "location": "Terraza Sur - Sector Árido",
            "height": "2024-11-05 - 28.5 cm",
            "registration_date": "2023-11-05",
            "padres": "Importación Namibia CITES 2021",
            "sowing_cutting_date": "2022-08-20",
            "graft": "Sin injerto",
            "last_pruned": "2024-12-01",
            "last_repotted": "2024-03-30 (Maceta profunda de gres)",
            "fertilizante": "2025-04-10 Microelementos y Calcio quelatado",
            "photos": ["K7_1.webp"],
            "status": "OK",
            "comentarios": "Follaje ondulado invernal en desarrollo. Orientación apical hacia el norte respetada."
        },
        {
            "name": "999",
            "species": "Euphorbia obesa var. crestada",
            "aka": "cristata",
            "location": "Laboratorio Clínico Botánico",
            "height": "2026-01-20 - 9.0 cm",
            "registration_date": "2025-08-01",
            "padres": "Desconocido",
            "sowing_cutting_date": "2025-03-10",
            "graft": "Injerto sobre Euphorbia canariensis",
            "last_pruned": "2026-01-20 (Corte de tejido necrosado)",
            "last_repotted": "2025-08-02",
            "fertilizante": "Ninguno",
            "photos": [],
            "status": "notOK",
            "comentarios": "Pudrición bacteriana avanzada en la unión del injerto. Aislado para intento de rescate de meristemo superior."
        },
        {
            "name": "C04",
            "species": "Echinocactus horizonthalonius",
            "aka": "solNaciente",
            "location": "Invernadero B - Germinador",
            "height": "2026-03-15 - 1.8 cm",
            "registration_date": "2026-03-15",
            "padres": "Autóctono Coahuila",
            "sowing_cutting_date": "2026-03-15",
            "graft": "Sin injerto",
            "last_pruned": "No aplica",
            "last_repotted": "2026-03-15",
            "fertilizante": "Solución nutritiva 10%",
            "photos": [],
            "status": "OK",
            "comentarios": "Plántula joven con espinación incipiente de color rojizo."
        },
        {
            "name": "M08",
            "species": "Mammillaria luethyi",
            "aka": "microClon",
            "location": "Mesa de Cuarentena Este",
            "height": "2026-07-01 - 3.4 cm",
            "registration_date": "2026-05-10",
            "padres": "Clon M-2",
            "sowing_cutting_date": "2026-05-10",
            "graft": "Injerto sobre Pereskiopsis",
            "last_pruned": "2026-07-01",
            "last_repotted": "2026-05-10",
            "fertilizante": "Fungicida sistémico preventivo",
            "photos": [],
            "status": "notOK",
            "comentarios": "Injerto joven con clorosis en tubérculos basales. Bajo observación."
        },
        {
            "name": "P40",
            "species": "Pachycereus pringlei",
            "aka": "cardon",
            "location": "Sector Exterior - Desierto",
            "height": "2025-11-20 - 42.0 cm",
            "registration_date": "2024-02-10",
            "padres": "Semilla silvestre Sonora",
            "sowing_cutting_date": "2020-04-12",
            "graft": "Sin injerto (Raíz propia)",
            "last_pruned": "2025-05-10",
            "last_repotted": "2024-03-15 (Contenedor terracota 50L)",
            "fertilizante": "2025-06-15 Fertilizante orgánico mineral",
            "photos": [],
            "status": "OK",
            "comentarios": "Ejemplar columnar robusto de 42 cm con espinación densa plateada."
        }
    ]

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        for p in default_plants:
            conn.execute("""
                INSERT OR IGNORE INTO plants (
                    name, species, aka, location, height, registration_date, padres,
                    sowing_cutting_date, graft, last_pruned, last_repotted,
                    fertilizante, photos, status, comentarios, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["name"], p["species"], p["aka"], p["location"], p["height"], p["registration_date"],
                p["padres"], p["sowing_cutting_date"], p["graft"], p["last_pruned"],
                p["last_repotted"], p["fertilizante"], json.dumps(p["photos"]),
                p["status"], p["comentarios"], now, now
            ))
        conn.commit()


def get_plants(
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
    age_filter: Optional[str] = None,
    height_filter: Optional[str] = None,
    sort_by: str = "name"
) -> List[Dict[str, Any]]:
    """Fetches plants with optional search, 2-state status filtering, age filtering, and height filtering."""
    with get_connection() as conn:
        query = "SELECT * FROM plants WHERE 1=1"
        params: List[Any] = []

        if status_filter:
            s_clean = status_filter.strip().lower()
            if s_clean not in ("all", "", "*"):
                norm = normalize_status(s_clean)
                query += " AND status = ?"
                params.append(norm)

        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            query += " AND (name LIKE ? OR aka LIKE ? OR species LIKE ? OR location LIKE ? OR height LIKE ? OR padres LIKE ? OR graft LIKE ? OR comentarios LIKE ?)"
            params.extend([sq] * 8)

        sort_map = {
            "name": "ORDER BY LENGTH(name) ASC, name ASC",
            "species": "ORDER BY species COLLATE NOCASE ASC",
            "status": "ORDER BY status ASC",
            "date": "ORDER BY registration_date DESC"
        }
        query += f" {sort_map.get(sort_by, sort_map['name'])}"

        rows = conn.execute(query, params).fetchall()
        result = [row_to_dict(r) for r in rows]

        # Biological Age filtering (< 1 year, 1 - 2 years, 3+ years)
        if age_filter and age_filter.strip().lower() not in ("all", "", "*"):
            a_clean = age_filter.strip().lower()
            filtered = []
            for p in result:
                m = get_plant_age_months(p.get("sowing_cutting_date"), p.get("graft", ""))
                if m is not None:
                    if a_clean in ("less_1", "<1", "less_than_1", "menor_1") and m < 12:
                        filtered.append(p)
                    elif a_clean in ("1_to_2", "1-2", "1_2", "1to2") and 12 <= m < 36:
                        filtered.append(p)
                    elif a_clean in ("3_plus", "3+", "3plus", "mas_3") and m >= 36:
                        filtered.append(p)
            result = filtered

        # Height range filtering (< 15 cm, 15 > x < 35, 35+ cm)
        if height_filter and height_filter.strip().lower() not in ("all", "", "*", "todas", "todos"):
            result = [p for p in result if matches_height_filter(p.get("height"), height_filter)]

        return result


def get_plant(name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single plant by its alphanumeric key."""
    clean_name = clean_key(name)
    if not clean_name:
        return None
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM plants WHERE name = ?", (clean_name,)).fetchone()
        return row_to_dict(row) if row else None


def create_plant(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Creates a new plant record. Returns (success, message_or_key)."""
    key = clean_key(data.get("name", ""))
    if not key:
        return False, "El identificador (KEY) debe contener letras o números (máx 20 caracteres)."

    species = (data.get("species") or "").strip()
    if not species:
        return False, "La especie botánica o nombre común es obligatoria."

    status = normalize_status(data.get("status"))
    aka = (data.get("aka") or "").strip()
    height = (data.get("height") or "").strip()
    photos = data.get("photos", [])
    photos_json = json.dumps(photos) if isinstance(photos, list) else "[]"
    # Registration date is retained as an internal record
    reg_date = (data.get("registration_date") or "").strip() or datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM plants WHERE name = ?", (key,)).fetchone():
            return False, f"La clave '{key}' ya existe en la base de datos."

        conn.execute("""
            INSERT INTO plants (
                name, species, aka, location, height, registration_date, padres,
                sowing_cutting_date, graft, last_pruned, last_repotted,
                fertilizante, photos, status, comentarios, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key, species, aka, (data.get("location") or "").strip(), height, reg_date,
            (data.get("padres") or "").strip(), (data.get("sowing_cutting_date") or "").strip(),
            (data.get("graft") or "").strip(), (data.get("last_pruned") or "").strip(),
            (data.get("last_repotted") or "").strip(), (data.get("fertilizante") or "").strip(),
            photos_json, status, (data.get("comentarios") or "").strip(), now, now
        ))
        conn.commit()

    return True, key


def update_plant(name: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Updates an existing plant record."""
    key = clean_key(name)
    if not key:
        return False, "Clave no válida."

    species = (data.get("species") or "").strip()
    if not species:
        return False, "La especie botánica o nombre común es obligatoria."

    status = normalize_status(data.get("status"))
    aka = (data.get("aka") or "").strip()
    height = (data.get("height") or "").strip()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        existing = conn.execute("SELECT registration_date FROM plants WHERE name = ?", (key,)).fetchone()
        if not existing:
            return False, f"Planta '{key}' no encontrada."

        # Keep existing registration_date as internal record unless provided
        reg_date = (data.get("registration_date") or "").strip() or (existing["registration_date"] or "")

        conn.execute("""
            UPDATE plants SET
                species = ?, aka = ?, location = ?, height = ?, registration_date = ?, padres = ?,
                sowing_cutting_date = ?, graft = ?, last_pruned = ?, last_repotted = ?,
                fertilizante = ?, status = ?, comentarios = ?, updated_at = ?
            WHERE name = ?
        """, (
            species, aka, (data.get("location") or "").strip(), height,
            reg_date, (data.get("padres") or "").strip(),
            (data.get("sowing_cutting_date") or "").strip(), (data.get("graft") or "").strip(),
            (data.get("last_pruned") or "").strip(), (data.get("last_repotted") or "").strip(),
            (data.get("fertilizante") or "").strip(), status, (data.get("comentarios") or "").strip(),
            now, key
        ))
        conn.commit()

    return True, f"Ejemplar '{key}' actualizado correctamente."


def delete_plant(name: str) -> Tuple[bool, List[str]]:
    """Deletes a single plant from DB. Returns (success, list_of_photo_filenames)."""
    key = clean_key(name)
    plant = get_plant(key)
    if not plant:
        return False, []
    with get_connection() as conn:
        conn.execute("DELETE FROM plants WHERE name = ?", (key,))
        conn.commit()
    return True, plant.get("photos", [])


def bulk_delete_plants(keys: List[str]) -> Tuple[int, List[str]]:
    """Deletes multiple plants in one transaction. Returns (deleted_count, all_photos)."""
    clean_keys = [clean_key(k) for k in keys if clean_key(k)]
    if not clean_keys:
        return 0, []

    all_photos: List[str] = []
    with get_connection() as conn:
        placeholders = ",".join("?" for _ in clean_keys)
        cursor = conn.execute(f"SELECT photos FROM plants WHERE name IN ({placeholders})", clean_keys)
        for row in cursor.fetchall():
            try:
                p_list = json.loads(row["photos"]) if row["photos"] else []
                all_photos.extend(p_list)
            except Exception:
                pass

        cursor = conn.execute(f"DELETE FROM plants WHERE name IN ({placeholders})", clean_keys)
        deleted_count = cursor.rowcount
        conn.commit()

    return deleted_count, all_photos


def add_photo_to_plant(name: str, filename: str) -> bool:
    """Appends a new photo filename to the plant's photo list."""
    plant = get_plant(name)
    if not plant:
        return False
    photos = plant.get("photos", [])
    if filename not in photos:
        photos.append(filename)
    with get_connection() as conn:
        conn.execute(
            "UPDATE plants SET photos = ?, updated_at = ? WHERE name = ?",
            (json.dumps(photos), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), plant["name"])
        )
        conn.commit()
    return True


def remove_photo_from_plant(name: str, filename: str) -> bool:
    """Removes a photo filename from the plant's photo list."""
    plant = get_plant(name)
    if not plant:
        return False
    photos = [p for p in plant.get("photos", []) if p != filename]
    with get_connection() as conn:
        conn.execute(
            "UPDATE plants SET photos = ?, updated_at = ? WHERE name = ?",
            (json.dumps(photos), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), plant["name"])
        )
        conn.commit()
    return True


def get_all_keys() -> List[str]:
    """Returns all plant keys for lineage and graft autocompletion."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT name FROM plants ORDER BY LENGTH(name) ASC, name ASC")
        return [r["name"] for r in cursor.fetchall()]


def get_stats() -> Dict[str, Any]:
    """Computes overall catalog statistics."""
    with get_connection() as conn:
        rows = conn.execute("SELECT status, location, photos, aka FROM plants").fetchall()
        total = len(rows)
        status_counts = {"OK": 0, "notOK": 0}
        locations = set()
        total_photos = 0
        with_alias = 0

        for r in rows:
            st = normalize_status(r["status"])
            status_counts[st] = status_counts.get(st, 0) + 1
            if r["location"]:
                locations.add(r["location"])
            if r["aka"]:
                with_alias += 1
            try:
                plist = json.loads(r["photos"]) if r["photos"] else []
                total_photos += len(plist)
            except Exception:
                pass

        return {
            "total": total,
            "status_counts": status_counts,
            "locations_count": len(locations),
            "total_photos": total_photos,
            "with_alias": with_alias
        }


def get_inventory_stats() -> Dict[str, Any]:
    """Detailed inventory breakdown for the Admin inventory module."""
    with get_connection() as conn:
        rows = conn.execute("SELECT name, species, aka, status, location, graft, photos FROM plants").fetchall()
        total = len(rows)
        status_counts = {"OK": 0, "notOK": 0}
        with_photos, without_photos = 0, 0
        with_graft, own_roots = 0, 0
        location_counts: Dict[str, int] = {}
        total_photos = 0

        for r in rows:
            st = normalize_status(r["status"])
            status_counts[st] = status_counts.get(st, 0) + 1

            p_list = []
            try:
                p_list = json.loads(r["photos"]) if r["photos"] else []
            except Exception:
                pass
            p_len = len(p_list)
            total_photos += p_len
            if p_len > 0:
                with_photos += 1
            else:
                without_photos += 1

            graft_str = (r["graft"] or "").strip().lower()
            if graft_str and "sin injerto" not in graft_str and graft_str not in ("no", "ninguno"):
                with_graft += 1
            else:
                own_roots += 1

            loc = (r["location"] or "Sin Ubicación").strip()
            location_counts[loc] = location_counts.get(loc, 0) + 1

        return {
            "total": total,
            "status_counts": status_counts,
            "with_photos": with_photos,
            "without_photos": without_photos,
            "with_graft": with_graft,
            "own_roots": own_roots,
            "location_counts": location_counts,
            "total_photos": total_photos
        }
