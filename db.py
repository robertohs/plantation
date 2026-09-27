"""
Plantation - Centralized Database Engine
Handles all SQLite operations, table schema creation, migrations, and CRUD queries.
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
    """Returns a thread-safe connection to the SQLite database with row_factory configured."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    """Initializes the database schema, migrations, and indexes."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS plants (
                name TEXT PRIMARY KEY,
                species TEXT NOT NULL,
                aka TEXT DEFAULT '',
                location TEXT DEFAULT '',
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
        # Safe migration for aka column in existing database
        try:
            conn.execute("ALTER TABLE plants ADD COLUMN aka TEXT DEFAULT '';")
        except sqlite3.OperationalError:
            pass

        # Migrate all existing statuses to the 2 requested states: OK (green) or notOK (orange)
        conn.execute("UPDATE plants SET status = 'OK' WHERE status IN ('Ok', 'Triving', 'OK', 'Saludable', 'Próspero');")
        conn.execute("UPDATE plants SET status = 'notOK' WHERE status NOT IN ('OK');")

        # Set sample AKAs for grafted plants if empty
        conn.execute("UPDATE plants SET aka = 'ocaso' WHERE name = 'A2' AND (aka IS NULL OR aka = '');")
        conn.execute("UPDATE plants SET aka = 'golden' WHERE name = '900' AND (aka IS NULL OR aka = '');")
        conn.execute("UPDATE plants SET aka = 'darkRed' WHERE name = 'B12' AND (aka IS NULL OR aka = '');")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_plants_species ON plants(species);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plants_status ON plants(status);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_plants_location ON plants(location);")
        conn.commit()

    # Seed initial specimens if table is empty
    seed_default_data()


def normalize_status(val: Optional[str]) -> str:
    """Normalizes any status representation strictly to 'OK' or 'notOK'."""
    if not val:
        return "OK"
    s = str(val).strip().lower()
    if s in ("ok", "triving", "saludable", "prospero", "próspero", "healthy", "good", "bien"):
        return "OK"
    return "notOK"


def clean_key(key: str) -> str:
    """Normalizes and validates plant key (alphanumeric, max 20 chars)."""
    clean = re.sub(r'[^a-zA-Z0-9_-]', '', (key or '')).strip().upper()
    return clean[:20]


def parse_plant_date(s: Optional[str]) -> Optional[datetime]:
    """Parses a date string in ISO YYYY-MM-DD or other standard formats."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    m = re.search(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', s)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            pass
    m2 = re.search(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', s)
    if m2:
        try:
            return datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except ValueError:
            pass
    m3 = re.search(r'(\d{4})[-/](\d{1,2})', s)
    if m3:
        try:
            return datetime(int(m3.group(1)), int(m3.group(2)), 1)
        except ValueError:
            pass
    return None


def calculate_plant_age(
    sowing_cutting_date: Optional[str],
    graft: Optional[str] = "",
    now: Optional[datetime] = None
) -> Tuple[str, str]:
    """Calculates plant age where age 0 is when the plant was grafted or sowed.

    Returns a tuple of (short_display, detailed_display):
      - short_display: e.g. "3 años, 8 meses (44 m)", "8 meses", "0 meses", or "—"
      - detailed_display: e.g. "3 años, 8 meses (44 meses en total)", "0 meses (Recién sembrada / injertada)", or "—"
    """
    d_start = parse_plant_date(sowing_cutting_date)
    if not d_start and graft:
        d_start = parse_plant_date(graft)

    if not d_start:
        return "—", "Sin fecha de siembra o injerto"

    if now is None:
        now = datetime.now()

    if d_start > now:
        return "0 meses", "0 meses (Recién sembrada / injertada)"

    diff_years = now.year - d_start.year
    diff_months = now.month - d_start.month
    if now.day < d_start.day:
        diff_months -= 1

    total_months = diff_years * 12 + diff_months
    if total_months <= 0:
        return "0 meses", "0 meses (Recién sembrada / injertada)"

    if total_months < 12:
        m_lbl = "1 mes" if total_months == 1 else f"{total_months} meses"
        return m_lbl, f"{m_lbl} (Total: {total_months} meses)"

    y = total_months // 12
    rem = total_months % 12
    y_lbl = "1 año" if y == 1 else f"{y} años"

    if rem == 0:
        return f"{y_lbl} ({total_months} m)", f"{y_lbl} (Total: {total_months} meses)"

    rem_lbl = "1 mes" if rem == 1 else f"{rem} meses"
    return f"{y_lbl}, {rem_lbl} ({total_months} m)", f"{y_lbl}, {rem_lbl} (Total: {total_months} meses)"


def get_plant_age_months(
    sowing_cutting_date: Optional[str],
    graft: Optional[str] = "",
    now: Optional[datetime] = None
) -> Optional[int]:
    """Returns the plant age in total integer months, or None if unknown."""
    d_start = parse_plant_date(sowing_cutting_date)
    if not d_start and graft:
        d_start = parse_plant_date(graft)
    if not d_start:
        return None
    if now is None:
        now = datetime.now()
    if d_start > now:
        return 0
    diff_years = now.year - d_start.year
    diff_months = now.month - d_start.month
    if now.day < d_start.day:
        diff_months -= 1
    return max(0, diff_years * 12 + diff_months)


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite row into a serializable dict, parses photos JSON, and ensures aka string."""
    d = dict(row)
    if "aka" not in d or d["aka"] is None:
        d["aka"] = ""
    # Ensure status is normalized to 2-state OK or notOK
    if d.get("status") not in ("OK", "notOK"):
        d["status"] = "OK" if d.get("status") in ("Ok", "Triving", "Saludable", "Próspero") else "notOK"

    if "photos" in d:
        try:
            d["photos"] = json.loads(d["photos"]) if d["photos"] else []
        except Exception:
            d["photos"] = []
    else:
        d["photos"] = []
    return d


def get_plants(
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
    age_filter: Optional[str] = None,
    sort_by: str = "name"
) -> List[Dict[str, Any]]:
    """Fetches plants with optional search, 2-state status filtering (OK / notOK), and age filtering."""
    with get_connection() as conn:
        query = "SELECT * FROM plants WHERE 1=1"
        params: List[Any] = []

        # Robust 2-state status filtering (OK vs notOK)
        if status_filter:
            s_clean = status_filter.strip().lower()
            if s_clean in ("all", "", "none", "null", "undefined", "*"):
                pass  # Show all statuses
            elif s_clean in ("ok", "triving", "saludable", "prospero", "próspero"):
                query += " AND (status = 'OK' OR LOWER(status) IN ('ok', 'triving', 'saludable', 'prospero', 'próspero'))"
            elif s_clean in ("notok", "not_ok", "not ok", "disease", "diseaced", "ill", "extremely ill", "enfermo"):
                query += " AND (status = 'notOK' OR LOWER(status) NOT IN ('ok', 'triving', 'saludable', 'prospero', 'próspero'))"

        if search_query and search_query.strip():
            sq = f"%{search_query.strip()}%"
            query += " AND (name LIKE ? OR aka LIKE ? OR species LIKE ? OR location LIKE ? OR padres LIKE ? OR graft LIKE ? OR comentarios LIKE ?)"
            params.extend([sq, sq, sq, sq, sq, sq, sq])

        # Alphanumeric sorting (lengths first then natural order for keys like 1, 2, A1, A2, 999)
        if sort_by == "name":
            query += " ORDER BY LENGTH(name) ASC, name ASC"
        elif sort_by == "species":
            query += " ORDER BY species COLLATE NOCASE ASC"
        elif sort_by == "status":
            query += " ORDER BY status ASC"
        elif sort_by == "date":
            query += " ORDER BY registration_date DESC"
        else:
            query += " ORDER BY LENGTH(name) ASC, name ASC"

        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        result = [row_to_dict(r) for r in rows]

        # Filter by Age if specified
        if age_filter:
            a_clean = age_filter.strip().lower()
            if a_clean in ("all", "", "none", "null", "undefined", "*"):
                pass  # Show all ages
            else:
                filtered = []
                for p in result:
                    m = get_plant_age_months(p.get("sowing_cutting_date"), p.get("graft", ""))
                    if a_clean in ("less_1", "<1", "less_than_1", "menor_1"):
                        # Menos de 1 año (< 12 meses)
                        if m is not None and m < 12:
                            filtered.append(p)
                    elif a_clean in ("1_to_2", "1-2", "1_2", "1to2"):
                        # 1 a 2 años (12 a < 36 meses)
                        if m is not None and 12 <= m < 36:
                            filtered.append(p)
                    elif a_clean in ("3_plus", "3+", "3plus", "mas_3"):
                        # 3 o más años (>= 36 meses)
                        if m is not None and m >= 36:
                            filtered.append(p)
                    else:
                        filtered.append(p)
                return filtered

        return result


def get_plant(name: str) -> Optional[Dict[str, Any]]:
    """Retrieves a single plant by its alphanumeric KEY."""
    clean_name = clean_key(name)
    if not clean_name:
        return None
    with get_connection() as conn:
        cursor = conn.execute("SELECT * FROM plants WHERE name = ?", (clean_name,))
        row = cursor.fetchone()
        return row_to_dict(row) if row else None


def create_plant(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Creates a new plant record. Returns (success, message_or_key)."""
    raw_name = data.get("name", "")
    key = clean_key(raw_name)
    if not key:
        return False, "El identificador (KEY) debe contener letras o números (máx 20 caracteres)."

    species = (data.get("species") or "").strip()
    if not species:
        return False, "La especie botánica o nombre común es obligatoria."

    raw_status = (data.get("status") or "OK").strip()
    status = "OK" if raw_status in ("OK", "Ok", "Triving", "Saludable", "Próspero") else "notOK"

    aka = (data.get("aka") or "").strip()

    photos = data.get("photos", [])
    if isinstance(photos, list):
        photos_json = json.dumps(photos)
    else:
        photos_json = "[]"

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reg_date = (data.get("registration_date") or "").strip()
    if not reg_date:
        reg_date = datetime.now().strftime("%Y-%m-%d")

    with get_connection() as conn:
        # Check uniqueness
        existing = conn.execute("SELECT name FROM plants WHERE name = ?", (key,)).fetchone()
        if existing:
            return False, f"La clave '{key}' ya existe en la base de datos."

        conn.execute("""
            INSERT INTO plants (
                name, species, aka, location, registration_date, padres,
                sowing_cutting_date, graft, last_pruned, last_repotted,
                fertilizante, photos, status, comentarios, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            species,
            aka,
            (data.get("location") or "").strip(),
            reg_date,
            (data.get("padres") or "").strip(),
            (data.get("sowing_cutting_date") or "").strip(),
            (data.get("graft") or "").strip(),
            (data.get("last_pruned") or "").strip(),
            (data.get("last_repotted") or "").strip(),
            (data.get("fertilizante") or "").strip(),
            photos_json,
            status,
            (data.get("comentarios") or "").strip(),
            now,
            now
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

    raw_status = (data.get("status") or "OK").strip()
    status = "OK" if raw_status in ("OK", "Ok", "Triving", "Saludable", "Próspero") else "notOK"

    aka = (data.get("aka") or "").strip()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        existing = conn.execute("SELECT name FROM plants WHERE name = ?", (key,)).fetchone()
        if not existing:
            return False, f"Planta '{key}' no encontrada."

        conn.execute("""
            UPDATE plants SET
                species = ?,
                aka = ?,
                location = ?,
                registration_date = ?,
                padres = ?,
                sowing_cutting_date = ?,
                graft = ?,
                last_pruned = ?,
                last_repotted = ?,
                fertilizante = ?,
                status = ?,
                comentarios = ?,
                updated_at = ?
            WHERE name = ?
        """, (
            species,
            aka,
            (data.get("location") or "").strip(),
            (data.get("registration_date") or "").strip(),
            (data.get("padres") or "").strip(),
            (data.get("sowing_cutting_date") or "").strip(),
            (data.get("graft") or "").strip(),
            (data.get("last_pruned") or "").strip(),
            (data.get("last_repotted") or "").strip(),
            (data.get("fertilizante") or "").strip(),
            status,
            (data.get("comentarios") or "").strip(),
            now,
            key
        ))
        conn.commit()

    return True, f"Ejemplar '{key}' actualizado correctamente."


def delete_plant(name: str) -> Tuple[bool, List[str]]:
    """
    Deletes a single plant from the DB.
    Returns (success, list_of_photo_filenames_to_cleanup).
    """
    key = clean_key(name)
    plant = get_plant(key)
    if not plant:
        return False, []

    photos_to_clean = plant.get("photos", [])

    with get_connection() as conn:
        conn.execute("DELETE FROM plants WHERE name = ?", (key,))
        conn.commit()

    return True, photos_to_clean


def bulk_delete_plants(keys: List[str]) -> Tuple[int, List[str]]:
    """
    Deletes multiple plants in one transaction.
    Returns (deleted_count, all_photos_to_cleanup).
    """
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
    key = clean_key(name)
    plant = get_plant(key)
    if not plant:
        return False

    photos = plant.get("photos", [])
    if filename not in photos:
        photos.append(filename)

    with get_connection() as conn:
        conn.execute(
            "UPDATE plants SET photos = ?, updated_at = ? WHERE name = ?",
            (json.dumps(photos), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key)
        )
        conn.commit()
    return True


def remove_photo_from_plant(name: str, filename: str) -> bool:
    """Removes a photo filename from the plant's photo list."""
    key = clean_key(name)
    plant = get_plant(key)
    if not plant:
        return False

    photos = [p for p in plant.get("photos", []) if p != filename]

    with get_connection() as conn:
        conn.execute(
            "UPDATE plants SET photos = ?, updated_at = ? WHERE name = ?",
            (json.dumps(photos), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), key)
        )
        conn.commit()
    return True


def get_all_keys() -> List[str]:
    """Returns all existing plant keys for lineage and graft autocompletion."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT name FROM plants ORDER BY LENGTH(name) ASC, name ASC")
        return [r["name"] for r in cursor.fetchall()]


def get_stats() -> Dict[str, Any]:
    """Computes overall catalog statistics."""
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) as c FROM plants").fetchone()["c"]
        status_counts = {"OK": 0, "notOK": 0}
        cursor = conn.execute("SELECT status FROM plants")
        for r in cursor.fetchall():
            st = normalize_status(r["status"])
            status_counts[st] = status_counts.get(st, 0) + 1

        locations_count = conn.execute("SELECT COUNT(DISTINCT location) as c FROM plants WHERE location != ''").fetchone()["c"]

        total_photos = 0
        p_cursor = conn.execute("SELECT photos FROM plants")
        for r in p_cursor.fetchall():
            try:
                plist = json.loads(r["photos"]) if r["photos"] else []
                total_photos += len(plist)
            except Exception:
                pass

        return {
            "total": total,
            "status_counts": status_counts,
            "locations_count": locations_count,
            "total_photos": total_photos
        }


def get_inventory_stats() -> Dict[str, Any]:
    """Detailed inventory breakdown for the Admin inventory module."""
    with get_connection() as conn:
        rows = conn.execute("SELECT name, species, status, location, graft, photos FROM plants").fetchall()
        
        total = len(rows)
        status_counts = {"OK": 0, "notOK": 0}
        with_photos = 0
        without_photos = 0
        with_graft = 0
        own_roots = 0
        location_counts: Dict[str, int] = {}
        total_photos = 0

        for r in rows:
            st = normalize_status(r["status"])
            status_counts[st] = status_counts.get(st, 0) + 1

            # Photos
            p_list = []
            try:
                if r["photos"]:
                    p_list = json.loads(r["photos"])
            except Exception:
                pass
            p_len = len(p_list)
            total_photos += p_len
            if p_len > 0:
                with_photos += 1
            else:
                without_photos += 1

            # Graft
            graft_str = (r["graft"] or "").strip().lower()
            if graft_str and "sin injerto" not in graft_str and graft_str != "no" and graft_str != "ninguno":
                with_graft += 1
            else:
                own_roots += 1

            # Location
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


def seed_default_data() -> None:
    """Seeds initial botanical records if database is empty."""
    with get_connection() as conn:
        c = conn.execute("SELECT COUNT(*) as cnt FROM plants").fetchone()["cnt"]
        if c > 0:
            return

        initial_plants = [
            {
                "name": "A1",
                "species": "Ariocarpus kotschoubeyanus",
                "location": "Invernadero A - Banco 1",
                "registration_date": "2024-03-12",
                "padres": "Desconocido (Ejemplar Madre Silvestre)",
                "sowing_cutting_date": "2023-01-10",
                "graft": "Sin injerto (Raíz propia napiforme)",
                "last_pruned": "2025-11-04 (Limpieza raíces secundarias)",
                "last_repotted": "2025-02-18 (Sustrato mineral 80% pómice)",
                "fertilizante": "2025-06-01 NPK 4-10-15 dilución 25% + Quelato de Hierro",
                "photos": ["A1_1.webp", "A1_2.webp"],
                "status": "Triving",
                "comentarios": "Floración rosa magenta observada en otoño. Crecimiento lento pero saludable con tubérculos bien definidos."
            },
            {
                "name": "900",
                "species": "Lophophora williamsii var. caespitosa",
                "location": "Invernadero A - Banco 3",
                "registration_date": "2024-05-20",
                "padres": "Clon C-89 x Semilla Autóctona",
                "sowing_cutting_date": "2023-04-15",
                "graft": "Sin injerto",
                "last_pruned": "2025-08-12 (Separación de hijuelos)",
                "last_repotted": "2025-01-05 (Maceta barro artesanal)",
                "fertilizante": "2025-05-15 Extracto de algas marinas bioestimulante",
                "photos": ["900_1.webp"],
                "status": "Ok",
                "comentarios": "Muestra 14 cabezas compactas. Lana apical densa y sana."
            },
            {
                "name": "A2",
                "species": "Ariocarpus retusus subsp. trigonus",
                "location": "Invernadero A - Banco 1",
                "registration_date": "2024-09-01",
                "padres": "A1 + 900",
                "sowing_cutting_date": "2024-06-11",
                "graft": "Injerto sobre Myrtillocactus geometrizans",
                "last_pruned": "2025-10-15 (Poda de rebrotes del patrón)",
                "last_repotted": "2024-11-20 (Trasplante de patrón)",
                "fertilizante": "2025-07-20 Fertilizante cactus bajo en nitrógeno",
                "photos": ["A2_1.webp"],
                "status": "Triving",
                "comentarios": "Cruce experimental exitoso entre A1 y 900. Velocidad de desarrollo acelerada gracias al injerto vigoroso."
            },
            {
                "name": "B12",
                "species": "Astrophytum asterias cv. Super Kabuto",
                "location": "Mesa de Cuarentena Este",
                "registration_date": "2025-01-14",
                "padres": "SK-White x Star Shape 4",
                "sowing_cutting_date": "2024-02-01",
                "graft": "Sin injerto",
                "last_pruned": "No aplica",
                "last_repotted": "2025-01-14 (Sustrato esterilizado)",
                "fertilizante": "Sin fertilizante reciente (Bajo tratamiento fúngico)",
                "photos": ["B12_1.webp"],
                "status": "Diseaced",
                "comentarios": "Mancha marrón sospechosa en la costilla apical 3. Tratado con oxicloruro de cobre preventivo en cuarentena."
            },
            {
                "name": "K7",
                "species": "Pachypodium namaquanum",
                "location": "Terraza Sur - Sector Árido",
                "registration_date": "2023-11-05",
                "padres": "Importación Namibia CITES 2021",
                "sowing_cutting_date": "2022-08-20",
                "graft": "Sin injerto",
                "last_pruned": "2024-12-01",
                "last_repotted": "2024-03-30 (Maceta profunda de gres)",
                "fertilizante": "2025-04-10 Microelementos y Calcio quelatado",
                "photos": ["K7_1.webp"],
                "status": "Ok",
                "comentarios": "Follaje ondulado invernal en desarrollo. Orientación apical hacia el norte respetada."
            },
            {
                "name": "999",
                "species": "Euphorbia obesa var. crestada",
                "location": "Laboratorio Clínico Botánico",
                "registration_date": "2025-08-01",
                "padres": "Desconocido",
                "sowing_cutting_date": "2025-03-10",
                "graft": "Injerto sobre Euphorbia canariensis",
                "last_pruned": "2026-01-20 (Corte de tejido necrosado)",
                "last_repotted": "2025-08-02",
                "fertilizante": "Ninguno",
                "photos": [],
                "status": "Extremely Ill",
                "comentarios": "Pudrición bacteriana avanzada en la unión del injerto. Aislado para intento de rescate de meristemo superior."
            }
        ]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for p in initial_plants:
            aka_val = p.get("aka", "")
            raw_st = p.get("status", "OK")
            st_val = "OK" if raw_st in ("OK", "Ok", "Triving", "Saludable", "Próspero") else "notOK"
            conn.execute("""
                INSERT INTO plants (
                    name, species, aka, location, registration_date, padres,
                    sowing_cutting_date, graft, last_pruned, last_repotted,
                    fertilizante, photos, status, comentarios, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                p["name"],
                p["species"],
                aka_val,
                p["location"],
                p["registration_date"],
                p["padres"],
                p["sowing_cutting_date"],
                p["graft"],
                p["last_pruned"],
                p["last_repotted"],
                p["fertilizante"],
                json.dumps(p["photos"]),
                st_val,
                p["comentarios"],
                now,
                now
            ))
        conn.commit()
