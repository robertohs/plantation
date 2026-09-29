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
BACKUPS_DIR = os.path.join(DB_DIR, "backups")
SEEDS_FILE = os.path.join(DB_DIR, "seeds.json")

VALID_STATUSES = ["OK", "notOK"]


def get_connection() -> sqlite3.Connection:
    """Returns a thread-safe connection to SQLite with WAL mode, busy timeout, and row_factory."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def normalize_status(val: Optional[str]) -> str:
    """Normalizes any status representation strictly to 'OK' or 'notOK'."""
    if not val:
        return "OK"
    s = str(val).strip().lower()
    return "OK" if s == "ok" else "notOK"


def clean_key(key: str) -> str:
    """Normalizes and validates plant key (alphanumeric, max 20 chars)."""
    return re.sub(r'[^a-zA-Z0-9_-]', '', (key or '')).strip().upper()[:20]


def parse_plant_date(s: Optional[str]) -> Optional[datetime]:
    """Parses a date string in ISO YYYY-MM-DD or standard formats."""
    if not s or not isinstance(s, str):
        return None
    m = re.search(r'(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?', s.strip())
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3) or 1))
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
        lbl = f"{months} mes" if months == 1 else f"{months} meses"
        return lbl, f"{lbl} (Total: {months} meses)"
    y, rem = divmod(months, 12)
    y_lbl = f"{y} año" if y == 1 else f"{y} años"
    if rem == 0:
        return f"{y_lbl} ({months} m)", f"{y_lbl} (Total: {months} meses)"
    rem_lbl = f"{rem} mes" if rem == 1 else f"{rem} meses"
    return f"{y_lbl}, {rem_lbl} ({months} m)", f"{y_lbl}, {rem_lbl} (Total: {months} meses)"


def calculate_age_display(sowing_cutting_date: Optional[str], graft: Optional[str] = "") -> str:
    """Returns the primary short string representation of plant age."""
    short, _ = calculate_plant_age(sowing_cutting_date, graft)
    return short


def matches_age_filter(months: Optional[int], filter_key: str) -> bool:
    """Checks if biological age in months matches age filter range."""
    if months is None:
        return False
    k = filter_key.strip().lower()
    if k in ("less_1", "<1", "less_than_1", "menor_1"):
        return months < 12
    if k in ("1_to_2", "1-2", "1_2", "1to2"):
        return 12 <= months < 36
    if k in ("3_plus", "3+", "3plus", "mas_3"):
        return months >= 36
    return True


def extract_height_cm(val: Optional[str]) -> Optional[float]:
    """
    Extracts numerical height in centimeters from botanical records.
    Examples:
      - '2025-06-15 - 4.8 cm' -> 4.8
      - '12.0 cm'             -> 12.0
      - '28.5'                -> 28.5
    """
    if not val or not isinstance(val, str):
        return None

    text = val.strip()
    if not text:
        return None

    # Case 1: Value with explicit 'cm' unit (e.g. '4.8 cm', '12cm')
    cm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*cm\b', text, re.IGNORECASE)
    if cm_match:
        try:
            return float(cm_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    # Case 2: Date-separated entry 'DATE - HEIGHT' (e.g. '2025-06-15 - 4.8')
    if '-' in text:
        last_segment = text.split('-')[-1].strip()
        num_match = re.search(r'(\d+(?:[.,]\d+)?)', last_segment)
        if num_match:
            try:
                return float(num_match.group(1).replace(',', '.'))
            except ValueError:
                pass

    # Case 3: Standalone numeric entry (e.g. '28.5')
    direct_match = re.match(r'^\s*(\d+(?:[.,]\d+)?)\s*$', text)
    if direct_match:
        try:
            return float(direct_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    return None


def matches_height_filter(height_str: Optional[str], filter_key: str) -> bool:
    """Checks if plant's height in cm matches selected filter range."""
    if not filter_key:
        return True

    key = filter_key.strip().lower()
    if key in ("all", "", "*", "todas", "todos"):
        return True

    height_cm = extract_height_cm(height_str)
    if height_cm is None:
        return False

    if key in ("less_15", "<15", "< 15", "less_than_15", "menor_15"):
        return height_cm < 15.0
    if key in ("15_to_35", "15-35", "15_35", "15to35"):
        return 15.0 <= height_cm < 35.0
    if key in ("35_plus", "35+", "35plus", "mas_35", "+35"):
        return height_cm >= 35.0

    return True


def row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Converts a SQLite row into a dict, deserializing photos and normalizing values."""
    d = dict(row)
    d["aka"] = d.get("aka") or ""
    d["height"] = d.get("height") or ""
    d["status"] = normalize_status(d.get("status"))
    d["indxw"] = int(d.get("indxw") or 0)
    try:
        d["photos"] = json.loads(d["photos"]) if d.get("photos") else []
    except Exception:
        d["photos"] = []
    return d


def init_db() -> None:
    """Initializes database schema, indexes, and seeds default records."""
    os.makedirs(DB_DIR, exist_ok=True)
    with get_connection() as conn:
        conn.execute("PRAGMA journal_mode = WAL;")
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
                indxw INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Ensure indxw column exists on existing databases
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(plants);").fetchall()]
        if "indxw" not in cols:
            conn.execute("ALTER TABLE plants ADD COLUMN indxw INTEGER NOT NULL DEFAULT 0;")

        for col in ("species", "status", "location", "aka", "height"):
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_plants_{col} ON plants({col});")
        conn.commit()

    seed_default_data()


def seed_default_data() -> None:
    """Seeds default curated botanical records from DB/seeds.json if empty."""
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM plants LIMIT 1").fetchone():
            return
        if not os.path.exists(SEEDS_FILE):
            return
        try:
            with open(SEEDS_FILE, "r", encoding="utf-8") as f:
                seeds = json.load(f)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for p in seeds:
                conn.execute("""
                    INSERT OR IGNORE INTO plants (
                        name, species, aka, location, height, registration_date, padres,
                        sowing_cutting_date, graft, last_pruned, last_repotted,
                        fertilizante, photos, status, comentarios, indxw, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    p["name"], p["species"], p.get("aka", ""), p.get("location", ""), p.get("height", ""),
                    p.get("registration_date", ""), p.get("padres", ""), p.get("sowing_cutting_date", ""),
                    p.get("graft", ""), p.get("last_pruned", ""), p.get("last_repotted", ""),
                    p.get("fertilizante", ""), json.dumps(p.get("photos", [])),
                    p.get("status", "OK"), p.get("comentarios", ""), int(p.get("indxw", 0)), now, now
                ))
            conn.commit()
        except Exception:
            pass


def get_plants(
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
    age_filter: Optional[str] = None,
    height_filter: Optional[str] = None,
    sort_by: str = "name"
) -> List[Dict[str, Any]]:
    """Fetches plants with optional search, status, age, and height filtering."""
    with get_connection() as conn:
        query = "SELECT * FROM plants WHERE 1=1"
        params: List[Any] = []

        if status_filter:
            s_clean = status_filter.strip().lower()
            if s_clean not in ("all", "", "*"):
                query += " AND status = ?"
                params.append(normalize_status(s_clean))

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

        if age_filter and age_filter.strip().lower() not in ("all", "", "*"):
            result = [
                p for p in result
                if matches_age_filter(get_plant_age_months(p.get("sowing_cutting_date"), p.get("graft", "")), age_filter)
            ]

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

    photos = data.get("photos", [])
    photos_json = json.dumps(photos) if isinstance(photos, list) else "[]"
    reg_date = (data.get("registration_date") or "").strip() or datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    indxw_raw = data.get("indxw", 0)
    indxw_val = 1 if indxw_raw in (1, "1", True, "true", "True", "on") else 0

    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM plants WHERE name = ?", (key,)).fetchone():
            return False, f"La clave '{key}' ya existe en la base de datos."

        conn.execute("""
            INSERT INTO plants (
                name, species, aka, location, height, registration_date, padres,
                sowing_cutting_date, graft, last_pruned, last_repotted,
                fertilizante, photos, status, comentarios, indxw, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key, species, (data.get("aka") or "").strip(), (data.get("location") or "").strip(),
            (data.get("height") or "").strip(), reg_date, (data.get("padres") or "").strip(),
            (data.get("sowing_cutting_date") or "").strip(), (data.get("graft") or "").strip(),
            (data.get("last_pruned") or "").strip(), (data.get("last_repotted") or "").strip(),
            (data.get("fertilizante") or "").strip(), photos_json,
            normalize_status(data.get("status")), (data.get("comentarios") or "").strip(), indxw_val, now, now
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

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        existing = conn.execute("SELECT registration_date, indxw FROM plants WHERE name = ?", (key,)).fetchone()
        if not existing:
            return False, f"Planta '{key}' no encontrada."

        reg_date = (data.get("registration_date") or "").strip() or (existing["registration_date"] or "")

        if "indxw" in data:
            indxw_val = 1 if data["indxw"] in (1, "1", True, "true", "True", "on") else 0
        else:
            indxw_val = int(existing["indxw"] if "indxw" in existing.keys() else 0)

        conn.execute("""
            UPDATE plants SET
                species = ?, aka = ?, location = ?, height = ?, registration_date = ?, padres = ?,
                sowing_cutting_date = ?, graft = ?, last_pruned = ?, last_repotted = ?,
                fertilizante = ?, status = ?, comentarios = ?, indxw = ?, updated_at = ?
            WHERE name = ?
        """, (
            species, (data.get("aka") or "").strip(), (data.get("location") or "").strip(),
            (data.get("height") or "").strip(), reg_date, (data.get("padres") or "").strip(),
            (data.get("sowing_cutting_date") or "").strip(), (data.get("graft") or "").strip(),
            (data.get("last_pruned") or "").strip(), (data.get("last_repotted") or "").strip(),
            (data.get("fertilizante") or "").strip(), normalize_status(data.get("status")),
            (data.get("comentarios") or "").strip(), indxw_val, now, key
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


def _update_plant_photos(name: str, modifier_fn) -> bool:
    """Helper to update a plant's photos list safely in a transaction."""
    plant = get_plant(name)
    if not plant:
        return False
    photos = modifier_fn(plant.get("photos", []))
    with get_connection() as conn:
        conn.execute(
            "UPDATE plants SET photos = ?, updated_at = ? WHERE name = ?",
            (json.dumps(photos), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), plant["name"])
        )
        conn.commit()
    return True


def add_photo_to_plant(name: str, filename: str) -> bool:
    """Appends a new photo filename to the plant's photo list."""
    return _update_plant_photos(name, lambda ph: ph if filename in ph else ph + [filename])


def remove_photo_from_plant(name: str, filename: str) -> bool:
    """Removes a photo filename from the plant's photo list."""
    return _update_plant_photos(name, lambda ph: [p for p in ph if p != filename])


def get_all_keys() -> List[str]:
    """Returns all plant keys for lineage and graft autocompletion."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT name FROM plants ORDER BY LENGTH(name) ASC, name ASC")
        return [r["name"] for r in cursor.fetchall()]


def get_inventory_stats() -> Dict[str, Any]:
    """Detailed inventory breakdown for catalog and admin modules."""
    with get_connection() as conn:
        rows = conn.execute("SELECT name, status, location, graft, photos, aka FROM plants").fetchall()

    stats: Dict[str, Any] = {
        "total": len(rows),
        "status_counts": {"OK": 0, "notOK": 0},
        "with_photos": 0,
        "without_photos": 0,
        "with_graft": 0,
        "own_roots": 0,
        "location_counts": {},
        "total_photos": 0,
        "with_alias": 0,
    }

    for r in rows:
        st = normalize_status(r["status"])
        stats["status_counts"][st] += 1
        if r["aka"]:
            stats["with_alias"] += 1

        photos = []
        try:
            photos = json.loads(r["photos"]) if r["photos"] else []
        except Exception:
            pass

        n_ph = len(photos)
        stats["total_photos"] += n_ph
        if n_ph > 0:
            stats["with_photos"] += 1
        else:
            stats["without_photos"] += 1

        graft_val = (r["graft"] or "").strip().lower()
        if graft_val and "sin injerto" not in graft_val and graft_val not in ("no", "ninguno"):
            stats["with_graft"] += 1
        else:
            stats["own_roots"] += 1

        loc = (r["location"] or "Sin Ubicación").strip()
        stats["location_counts"][loc] = stats["location_counts"].get(loc, 0) + 1

    return stats


def get_stats() -> Dict[str, Any]:
    """Computes overall catalog statistics."""
    inv = get_inventory_stats()
    return {
        "total": inv["total"],
        "status_counts": inv["status_counts"],
        "locations_count": len(inv["location_counts"]),
        "total_photos": inv["total_photos"],
        "with_alias": inv.get("with_alias", 0),
    }


def backup_db(custom_target_path: Optional[str] = None) -> str:
    """
    Safely creates a consistent snapshot of the SQLite database using the native
    online backup API (non-blocking, zero lock contention).
    Retains the most recent 14 snapshots (~7 days at 2 backups/day).
    """
    os.makedirs(BACKUPS_DIR, exist_ok=True)
    if custom_target_path:
        target_file = custom_target_path
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = os.path.join(BACKUPS_DIR, f"plantation_backup_{timestamp}.db")

    with get_connection() as src_conn:
        dest_conn = sqlite3.connect(target_file)
        with dest_conn:
            src_conn.backup(dest_conn)
        dest_conn.close()

    # Prune old automated backups (keep last 14)
    try:
        backups = sorted([
            os.path.join(BACKUPS_DIR, f)
            for f in os.listdir(BACKUPS_DIR)
            if f.startswith("plantation_backup_") and f.endswith(".db")
        ])
        if len(backups) > 14:
            for old_bk in backups[:-14]:
                try:
                    os.remove(old_bk)
                except OSError:
                    pass
    except Exception:
        pass

    return target_file


_scheduler_started = False


def start_backup_scheduler(interval_seconds: int = 43200) -> None:
    """
    Spawns a background daemon thread that executes an online database backup periodically (default: 12h / 43200s).
    Safe to call multiple times (idempotent).
    """
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    import threading
    import time

    def _backup_loop():
        # Brief pause on boot before taking the first initial snapshot
        time.sleep(10)
        while True:
            try:
                bk_path = backup_db()
                print(f"[BACKUP] Periodic database snapshot created: {bk_path}")
            except Exception as e:
                print(f"[BACKUP] Error running scheduled backup: {e}")
            time.sleep(interval_seconds)

    thread = threading.Thread(target=_backup_loop, daemon=True, name="sqlite-backup-scheduler")
    thread.start()


