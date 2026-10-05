"""
Plantation - Centralized Database Engine
Handles SQLite operations, table schema creation, migrations, and CRUD queries.
Database file stored in DB/plantation.db.
"""

import json
import os
import re
import sqlite3
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DB")
DB_PATH = os.path.join(DB_DIR, "plantation.db")
BACKUPS_DIR = os.path.join(DB_DIR, "backups")
SEEDS_FILE = os.path.join(DB_DIR, "seeds.json")

VALID_STATUSES = ["OK", "notOK"]

_db_lock = threading.Lock()


def _open_raw_connection(path: str = DB_PATH) -> sqlite3.Connection:
    """Low-level SQLite connection opener with WAL, timeouts, and row factory."""
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 10000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


_db_initialized = False


def ensure_db_ready() -> None:
    """
    CRITICAL: Guarantees that if the database file is missing, empty, or uninitialized
    at runtime (e.g. if a user deleted plantation.db while the app was running),
    it is IMMEDIATELY recreated and default specimens are seeded seamlessly.
    Optimized with a fast-path to prevent locking and query churning on high-frequency calls.
    """
    global _db_initialized
    if _db_initialized and os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
        return

    with _db_lock:
        if _db_initialized and os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) > 0:
            return

        needs_init = False
        if not os.path.exists(DB_PATH) or os.path.getsize(DB_PATH) == 0:
            needs_init = True
        else:
            try:
                test_conn = _open_raw_connection()
                try:
                    cur = test_conn.cursor()
                    cur.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='plants'")
                    if not cur.fetchone():
                        needs_init = True
                    else:
                        cur.execute("SELECT 1 FROM plants LIMIT 1")
                        if not cur.fetchone():
                            needs_init = True
                finally:
                    test_conn.close()
            except Exception:
                needs_init = True

        if needs_init:
            print("[DATABASE] DB file missing or empty. Auto-initializing and loading default specimens...")
            init_db()

        _db_initialized = True



def get_connection() -> sqlite3.Connection:
    """
    Returns a thread-safe connection to SQLite.
    Always checks that the DB file is initialized and populated before returning.
    """
    ensure_db_ready()
    return _open_raw_connection()


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
    """Parses a date string in ISO YYYY-MM-DD or standard formats (DD-MM-YYYY, YYYY/MM/DD, etc.)."""
    if not s or not isinstance(s, str):
        return None
    clean = s.strip()
    # Try YYYY-MM-DD or YYYY/MM/DD
    m1 = re.search(r'(\d{4})[-/](\d{1,2})(?:[-/](\d{1,2}))?', clean)
    if m1:
        try:
            return datetime(int(m1.group(1)), int(m1.group(2)), int(m1.group(3) or 1))
        except (ValueError, OverflowError):
            pass
    # Try DD-MM-YYYY or DD/MM/YYYY or DD.MM.YYYY
    m2 = re.search(r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})', clean)
    if m2:
        try:
            return datetime(int(m2.group(3)), int(m2.group(2)), int(m2.group(1)))
        except (ValueError, OverflowError):
            pass
    # Try YYYY only
    m3 = re.search(r'^\s*(\d{4})\s*$', clean)
    if m3:
        try:
            return datetime(int(m3.group(1)), 1, 1)
        except (ValueError, OverflowError):
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
    """
    Returns (short_display, detailed_display) for plant age using natural decimal years (Option C):
      - Strictly '{years:.1f} años' for all specimens with a known date (e.g. '0.0 años', '4.0 años', '4.5 años')
      - '—' for unknown / unregistered
      - Detailed breakdown in second return value for tooltips and technical dossiers
    """
    months = get_plant_age_months(sowing_cutting_date, graft, now)
    if months is None:
        return "—", "Sin fecha de siembra o injerto"

    y, rem = divmod(months, 12)
    if months == 0:
        det_lbl = "0 meses (Recién sembrada / injertada)"
    elif rem == 0:
        y_lbl = f"{y} año" if y == 1 else f"{y} años"
        det_lbl = f"{y_lbl} (Total: {months} meses)"
    else:
        y_lbl = f"{y} año" if y == 1 else f"{y} años"
        det_lbl = f"{y_lbl}, {rem} {'mes' if rem == 1 else 'meses'} (Total: {months} meses)"

    years_decimal = round(months / 12.0, 1)
    short_lbl = f"{years_decimal:.1f} años"

    return short_lbl, det_lbl


def calculate_age_display(sowing_cutting_date: Optional[str], graft: Optional[str] = "") -> str:
    """Returns the primary short string representation of plant age."""
    short, _ = calculate_plant_age(sowing_cutting_date, graft)
    return short


def matches_age_filter(months: Optional[int], filter_key: str) -> bool:
    """Checks if biological age in months matches age filter range."""
    if not filter_key or filter_key in ("ALL", "", "*", "all", "todas", "todos"):
        return True
    k = filter_key.strip().lower()
    if months is None:
        return k in ("sd", "s/d", "sin_fecha", "unknown", "none")
    if k in ("less_1", "<1", "< 1", "less_than_1", "menor_1"):
        return months < 12
    if k in ("1_to_2", "1-2", "1_2", "1to2"):
        return 12 <= months < 24
    if k in ("2_to_3", "2-3", "2_3", "2to3"):
        return 24 <= months < 36
    if k in ("3_plus", "3+", "3plus", "mas_3", "3_o_mas"):
        return months >= 36
    if k in ("sd", "s/d", "sin_fecha"):
        return False
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

    # Case 1: Value with explicit 'cm' unit (e.g. '4.8 cm', '12cm', '40, cm')
    cm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*,?\s*cm\b', text, re.IGNORECASE)
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

    # Case 3: Standalone numeric entry (e.g. '28.5', '40')
    direct_match = re.search(r'^\s*(\d+(?:[.,]\d+)?)\s*(?:,|cm)?\s*$', text, re.IGNORECASE)
    if direct_match:
        try:
            return float(direct_match.group(1).replace(',', '.'))
        except ValueError:
            pass

    return None


def format_height_short(val: Optional[str]) -> str:
    """
    Extracts strictly the numerical 'cm' part for plant cards on the main page.
    Strips any date of measure (e.g. '2026-09-29 - 0 cm' -> '0 cm', '2025-06-15 - 4.8 cm' -> '4.8 cm').
    """
    if not val or not isinstance(val, str) or not val.strip():
        return "—"

    text = val.strip()

    # If explicit cm match after any date prefix
    cm_match = re.search(r'(\d+(?:[.,]\d+)?)\s*,?\s*cm\b', text, re.IGNORECASE)
    if cm_match:
        return f"{cm_match.group(1)} cm"

    num = extract_height_cm(text)
    if num is not None:
        if num == int(num) and ".0" not in text:
            return f"{int(num)} cm"
        return f"{num:g} cm"

    # If date prefix exists like 'YYYY-MM-DD - something', take the right segment
    if '-' in text:
        parts = text.split('-')
        last_seg = parts[-1].strip()
        if last_seg:
            return last_seg if 'cm' in last_seg.lower() else f"{last_seg} cm"

    return text


def format_height_entry(val: Optional[str], old_val: Optional[str] = None, force_date: bool = False) -> str:
    """
    Normalizes plant height and ensures current date is automatically recorded.
    Target format: '<dimension> cm (YYYY-MM-DD)'
    E.g. '40'       -> '40 cm (2026-09-30)'
         '40 cm'    -> '40 cm (2026-09-30)'
         '40, cm'   -> '40 cm (2026-09-30)'
         '15.5'     -> '15.5 cm (2026-09-30)'
    """
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""

    today_str = datetime.now().strftime("%Y-%m-%d")

    # If the user already provided format 'X cm (YYYY-MM-DD)'
    m_full = re.match(r"^([\d.,]+)\s*(?:cm)?\s*\(\s*(\d{4}-\d{2}-\d{2})\s*\)$", s, re.IGNORECASE)
    if m_full:
        num_str = m_full.group(1).replace(",", ".")
        dt = m_full.group(2)
        if old_val:
            old_num = extract_height_cm(old_val)
            new_num = extract_height_cm(num_str)
            if old_num is not None and new_num is not None and abs(old_num - new_num) > 1e-4:
                return f"{num_str} cm ({today_str})"
        return f"{num_str} cm ({dt})"

    # If legacy format 'YYYY-MM-DD - X cm'
    m_legacy = re.match(r"^(\d{4}-\d{2}-\d{2})\s*-\s*([\d.,]+)\s*(?:cm)?$", s, re.IGNORECASE)
    if m_legacy:
        dt = m_legacy.group(1)
        num_str = m_legacy.group(2).replace(",", ".")
        if old_val:
            old_num = extract_height_cm(old_val)
            new_num = extract_height_cm(num_str)
            if old_num is not None and new_num is not None and abs(old_num - new_num) > 1e-4:
                return f"{num_str} cm ({today_str})"
        return f"{num_str} cm ({dt})"

    # Clean accidental input such as '40, cm' -> '40 cm'
    cleaned = re.sub(r'(\d+)\s*,\s*cm\b', r'\1 cm', s, flags=re.IGNORECASE)

    # If numeric dimension is present, extract it
    num_val = extract_height_cm(cleaned)
    if num_val is not None:
        if num_val == int(num_val) and "." not in cleaned and ("," not in cleaned or "cm" in cleaned.lower()):
            num_display = str(int(num_val))
        else:
            num_display = f"{num_val:g}"

        # If updating and value hasn't changed, retain previous unless force_date
        if old_val and s.strip() == str(old_val).strip() and not force_date:
            return old_val

        return f"{num_display} cm ({today_str})"

    if old_val and s.strip() == str(old_val).strip() and not force_date:
        return old_val
    return f"{s} ({today_str})"


def format_care_entry(val: Optional[str], old_val: Optional[str] = None, force_date: bool = False) -> str:
    """
    Normalizes pruning and repotting entries to ensure the date (YYYY-MM-DD) is automatically saved.
    E.g. ''                      -> '' (unmodified/blank)
         'Poda de raíces'        -> '2026-09-30 (Poda de raíces)'
         '2025-02-14'            -> '2025-02-14' (preserved if unchanged)
         '2026-09-30 (Pómice)'   -> '2026-09-30 (Pómice)'
    """
    if not val:
        return ""
    s = str(val).strip()
    if not s:
        return ""

    today_str = datetime.now().strftime("%Y-%m-%d")

    # If unchanged from old_val, keep as-is
    if old_val and s == str(old_val).strip() and not force_date:
        return old_val

    # Check if starts with a date YYYY-MM-DD
    m_date = re.match(r"^(\d{4}-\d{2}-\d{2})(?:\s*[-/(]\s*(.*?)\s*[)]?)?$", s)
    if m_date:
        dt = m_date.group(1)
        notes = (m_date.group(2) or "").strip()
        if notes:
            return f"{dt} ({notes})"
        return dt

    # Notes without a date -> prepend today's date
    return f"{today_str} ({s})"


def matches_height_filter(height_str: Optional[str], filter_key: str) -> bool:
    """Checks if plant's height in cm matches selected filter range."""
    if not filter_key:
        return True

    key = filter_key.strip().lower()
    if key in ("all", "", "*", "todas", "todos"):
        return True

    height_cm = extract_height_cm(height_str)
    if height_cm is None:
        return key in ("sd", "s/d", "sin_medir", "unknown", "none")

    if key in ("less_5", "<5", "< 5", "menor_5", "mini"):
        return height_cm < 5.0
    if key in ("5_to_15", "5-15", "5_15", "5to15"):
        return 5.0 <= height_cm < 15.0
    if key in ("less_15", "<15", "< 15", "less_than_15", "menor_15"):
        return height_cm < 15.0
    if key in ("15_to_30", "15-30", "15_30", "15to30"):
        return 15.0 <= height_cm < 30.0
    if key in ("30_plus", "30+", "30plus", "mas_30", "+30"):
        return height_cm >= 30.0
    if key in ("15_to_35", "15-35", "15_35", "15to35"):
        return 15.0 <= height_cm < 35.0
    if key in ("35_plus", "35+", "35plus", "mas_35", "+35"):
        return height_cm >= 35.0

    return True


def split_parents(padres: Optional[str]) -> Tuple[str, str]:
    """
    Splits a plant's lineage string into two individual parent keys:
    (Parent 1 / Mother, Parent 2 / Father).
    Returns clean keys; if a parent was 'unknown', returns empty string so the field can be edited.
    """
    if not padres:
        return "", ""
    s = str(padres).strip()
    if not s or s.lower() in ("unknown", "desconocido", "none", "null", "--"):
        return "", ""

    # Split on botanical cross notation
    match = re.split(r"\s+(?:[×xX]|\+|\/)\s+", s, maxsplit=1)
    if len(match) == 2:
        p1 = match[0].strip()
        p2 = match[1].strip()
        p1_clean = "" if p1.lower() in ("unknown", "desconocido") else p1
        p2_clean = "" if p2.lower() in ("unknown", "desconocido") else p2
        return p1_clean, p2_clean

    m_tight = re.match(r"^([A-Za-z0-9_-]+)\s*[×xX+]\s*([A-Za-z0-9_-]+)$", s)
    if m_tight:
        p1 = m_tight.group(1).strip()
        p2 = m_tight.group(2).strip()
        p1_clean = "" if p1.lower() in ("unknown", "desconocido") else p1
        p2_clean = "" if p2.lower() in ("unknown", "desconocido") else p2
        return p1_clean, p2_clean

    return s, ""


def combine_parents(parent1: Optional[str], parent2: Optional[str], fallback: Optional[str] = None) -> str:
    """
    Combines two parent keys into botanical cross notation: 'Parent1 × Parent2'.
    If a parent is not selected or empty, the default value is 'unknown'.
    - If neither is provided -> 'unknown'
    - If Parent 1 is provided and Parent 2 is empty -> 'Parent1 × unknown'
    - If Parent 1 is empty and Parent 2 is provided -> 'unknown × Parent2'
    - If both are provided -> 'Parent1 × Parent2'
    """
    p1 = (parent1 or "").strip()
    p2 = (parent2 or "").strip()

    is_p1_unknown = (not p1) or (p1.lower() in ("unknown", "desconocido", "--", "none", "null"))
    is_p2_unknown = (not p2) or (p2.lower() in ("unknown", "desconocido", "--", "none", "null"))

    if is_p1_unknown and is_p2_unknown:
        if fallback and fallback.strip() and fallback.strip().lower() not in ("unknown", "desconocido"):
            return fallback.strip()
        return "unknown"

    val1 = "unknown" if is_p1_unknown else p1
    val2 = "unknown" if is_p2_unknown else p2

    return f"{val1} × {val2}"


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


def check_database_integrity() -> Tuple[bool, str]:
    """
    Executes SQLite PRAGMA integrity_check to verify database file health and structure.
    Returns (True, 'OK') if healthy, or (False, error_details) if any corruption is found.
    """
    try:
        with _open_raw_connection() as conn:
            rows = conn.execute("PRAGMA integrity_check;").fetchall()
            messages = [r[0] for r in rows if r]
            if len(messages) == 1 and str(messages[0]).strip().lower() == "ok":
                return True, "OK"
            return False, "; ".join(str(m) for m in messages)
    except Exception as e:
        return False, str(e)


def _seed_default_data_conn(conn: sqlite3.Connection, insert_missing: bool = True) -> int:
    """
    Seeds default botanical records directly from DB/seeds.json into SQLite.
    DB/seeds.json is the sole source of truth for default specimens.
    """
    if not os.path.exists(SEEDS_FILE):
        print(f"[DATABASE] Seeds file {SEEDS_FILE} not found. No default seeds loaded.")
        return 0

    try:
        with open(SEEDS_FILE, "r", encoding="utf-8") as f:
            seeds = json.load(f)
    except Exception as e:
        print(f"[DATABASE] Error reading {SEEDS_FILE}: {e}")
        return 0

    if not seeds or not isinstance(seeds, list) or len(seeds) == 0:
        print(f"[DATABASE] Seeds file {SEEDS_FILE} is empty or invalid JSON array.")
        return 0

    inserted_count = 0
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for p in seeds:
        cursor = conn.execute("""
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
            normalize_status(p.get("status")), p.get("comentarios", ""), int(p.get("indxw", 0)), now, now
        ))
        if cursor.rowcount > 0:
            inserted_count += 1
    conn.commit()

    if inserted_count > 0:
        print(f"[DATABASE] Loaded {inserted_count} default botanical specimens from DB/seeds.json into SQLite.")

    try:
        import img_conv
        img_conv.generate_seed_photos_if_missing()
    except Exception:
        pass

    return inserted_count


def init_db() -> None:
    """Initializes database schema, indexes, verifies integrity, and seeds default records."""
    os.makedirs(DB_DIR, exist_ok=True)
    with _open_raw_connection() as conn:
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

        _seed_default_data_conn(conn, insert_missing=True)

    ok, msg = check_database_integrity()
    if ok:
        print("[DATABASE] SQLite integrity verified: OK")
    else:
        print(f"[DATABASE] SQLite integrity check WARNING: {msg}")


def seed_default_data(insert_missing: bool = True) -> int:
    """
    Seeds default curated botanical records into SQLite.
    Guarantees default specimen loading when no database is present or when new seeds are added.
    Uses INSERT OR IGNORE so existing customized plants are never overwritten.
    Returns the count of inserted plants.
    """
    with _open_raw_connection() as conn:
        return _seed_default_data_conn(conn, insert_missing=insert_missing)




def get_plants(
    search_query: Optional[str] = None,
    status_filter: Optional[str] = None,
    age_filter: Optional[str] = None,
    height_filter: Optional[str] = None,
    sort_by: str = "name"
) -> List[Dict[str, Any]]:
    """Fetches plants with optional search, status, age, and height filtering."""
    result: List[Dict[str, Any]] = []
    for attempt in range(2):
        try:
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
                break
        except sqlite3.OperationalError as e:
            if "no such table" in str(e).lower() and attempt == 0:
                init_db()
                continue
            raise

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
    try:
        indxw_val = int(indxw_raw)
    except (ValueError, TypeError):
        indxw_val = 1 if str(indxw_raw).strip() in ("1", "true", "True", "on") else 0

    raw_height = (data.get("height") or "").strip()
    height_val = format_height_entry(raw_height, force_date=True)

    raw_pruned = (data.get("last_pruned") or "").strip()
    pruned_val = format_care_entry(raw_pruned, force_date=True) if raw_pruned else ""

    raw_repotted = (data.get("last_repotted") or "").strip()
    repotted_val = format_care_entry(raw_repotted, force_date=True) if raw_repotted else ""

    raw_sow = (data.get("sowing_cutting_date") or "").strip()
    if raw_sow:
        dt_sow = parse_plant_date(raw_sow)
        sow_val = dt_sow.strftime("%Y-%m-%d") if dt_sow else raw_sow
    else:
        sow_val = ""

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
            height_val, reg_date, (data.get("padres") or "").strip(),
            sow_val, (data.get("graft") or "").strip(),
            pruned_val, repotted_val,
            (data.get("fertilizante") or "").strip(), photos_json,
            normalize_status(data.get("status")), (data.get("comentarios") or "").strip(), indxw_val, now, now
        ))
        conn.commit()

    return True, key


def check_keys_availability(keys: List[str]) -> Tuple[List[str], List[str]]:
    """
    Checks a list of proposed keys against the SQLite database.
    Case-insensitive matching to guarantee no duplicates.
    Returns (available_keys, conflict_keys).
    """
    if not keys:
        return [], []
    with get_connection() as conn:
        existing = set(r[0].lower() for r in conn.execute("SELECT LOWER(name) FROM plants").fetchall())

    available = []
    conflicts = []
    seen = set()
    for k in keys:
        ck = clean_key(k)
        if not ck:
            continue
        lower_ck = ck.lower()
        if lower_ck in seen:
            # Internal duplication in input list
            conflicts.append(ck)
            continue
        seen.add(lower_ck)
        if lower_ck in existing:
            conflicts.append(ck)
        else:
            available.append(ck)
    return available, conflicts


def get_distinct_locations() -> List[str]:
    """Returns sorted list of distinct non-empty locations from plants table."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT DISTINCT location FROM plants WHERE location IS NOT NULL AND TRIM(location) != '' ORDER BY location ASC")
        return [r["location"] for r in cursor.fetchall()]


def get_distinct_species() -> List[str]:
    """Returns sorted list of distinct non-empty species from plants table."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT DISTINCT species FROM plants WHERE species IS NOT NULL AND TRIM(species) != '' ORDER BY species ASC")
        return [r["species"] for r in cursor.fetchall()]


def get_next_available_key_number(prefix: str) -> int:
    """
    Finds the highest integer suffix for keys matching the given prefix and returns highest + 1.
    e.g. if K1, K7 exist and prefix is K, returns 8.
    """
    clean_pfx = (prefix or "").strip().upper()
    all_keys = get_all_keys()
    max_num = 0
    pattern = re.compile(rf"^{re.escape(clean_pfx)}[-_]?(\d+)$", re.IGNORECASE)
    for k in all_keys:
        m = pattern.match(k.strip())
        if m:
            try:
                num = int(m.group(1))
                if num > max_num:
                    max_num = num
            except ValueError:
                pass
    return max_num + 1


def generate_bulk_keys(
    prefix: str,
    count: int,
    start_num: int = 1,
    pad_zeros: Any = 0
) -> List[str]:
    """Generates sequential keys: e.g. prefix='k', count=10, start=1 -> ['k1', ... 'k10']."""
    raw_pfx = (prefix or "").strip()
    clean_pfx = re.sub(r'[^a-zA-Z0-9_-]', '', raw_pfx).upper()
    keys = []
    count = max(1, min(count, 10000))
    start_num = max(1, start_num)
    
    pad_mode = 0
    if isinstance(pad_zeros, bool):
        pad_mode = 2 if pad_zeros else 0
    elif isinstance(pad_zeros, int):
        pad_mode = pad_zeros
    elif str(pad_zeros).strip() in ("1", "2", "true", "True"):
        pad_mode = 2
    elif str(pad_zeros).strip() in ("3",):
        pad_mode = 3

    for i in range(start_num, start_num + count):
        if pad_mode == 2:
            num_str = str(i).zfill(2)
        elif pad_mode == 3:
            num_str = str(i).zfill(3)
        else:
            num_str = str(i)
        keys.append(f"{clean_pfx}{num_str}")
    return keys


def create_plants_bulk(
    keys: List[str],
    common_data: Dict[str, Any],
    skip_existing: bool = True,
    auto_number_alias: bool = False,
    plant_photos_map: Optional[Dict[str, List[str]]] = None
) -> Tuple[bool, str, List[str], List[str]]:
    """
    Creates multiple plant specimens with identical metadata in an atomic, ultra-fast SQLite transaction.
    Alias is always stored as an exact alias without sequential numbering.
    Returns (success, message, created_keys, skipped_keys).
    """
    species = (common_data.get("species") or "").strip()
    if not species:
        return False, "La especie botánica o taxonomía es obligatoria para el lote.", [], []

    available, conflicts = check_keys_availability(keys)

    if conflicts and not skip_existing:
        conflict_list = ", ".join(conflicts[:10]) + ("..." if len(conflicts) > 10 else "")
        return False, f"Las siguientes claves ya existen en la base de datos: {conflict_list}. Marque la opción de omitir existentes o cambie el prefijo/rango.", [], conflicts

    if not available:
        return False, "Todas las claves generadas ya existen en la base de datos. Ningún ejemplar fue creado.", [], conflicts

    default_photos = common_data.get("photos", [])
    reg_date = (common_data.get("registration_date") or "").strip() or datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    indxw_raw = common_data.get("indxw", 0)
    try:
        indxw_val = int(indxw_raw)
    except (ValueError, TypeError):
        indxw_val = 1 if str(indxw_raw).strip() in ("1", "true", "True", "on") else 0

    raw_height = (common_data.get("height") or "").strip()
    height_val = format_height_entry(raw_height, force_date=True)

    raw_pruned = (common_data.get("last_pruned") or "").strip()
    pruned_val = format_care_entry(raw_pruned, force_date=True) if raw_pruned else ""

    raw_repotted = (common_data.get("last_repotted") or "").strip()
    repotted_val = format_care_entry(raw_repotted, force_date=True) if raw_repotted else ""

    raw_sow = (common_data.get("sowing_cutting_date") or "").strip()
    if raw_sow:
        dt_sow = parse_plant_date(raw_sow)
        sow_val = dt_sow.strftime("%Y-%m-%d") if dt_sow else raw_sow
    else:
        sow_val = ""

    # Alias is strictly an exact alias without ever appending sequential numbers
    aka_base = (common_data.get("aka") or "").strip()
    location = (common_data.get("location") or "").strip()
    graft = (common_data.get("graft") or "").strip()
    padres = (common_data.get("padres") or "").strip()
    fertilizante = (common_data.get("fertilizante") or "").strip()
    comentarios = (common_data.get("comentarios") or "").strip()
    status = normalize_status(common_data.get("status"))

    created_keys = []
    rows_to_insert = []
    for k in available:
        photos_for_k = default_photos
        if plant_photos_map and k in plant_photos_map:
            photos_for_k = plant_photos_map[k]
        photos_json = json.dumps(photos_for_k) if isinstance(photos_for_k, list) else "[]"

        rows_to_insert.append((
            k, species, aka_base, location, height_val, reg_date, padres,
            sow_val, graft, pruned_val, repotted_val,
            fertilizante, photos_json, status, comentarios, indxw_val, now, now
        ))
        created_keys.append(k)

    # Fast bulk insertion using executemany in a single transaction
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO plants (
                name, species, aka, location, height, registration_date, padres,
                sowing_cutting_date, graft, last_pruned, last_repotted,
                fertilizante, photos, status, comentarios, indxw, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows_to_insert)
        conn.commit()

    sample_keys = ", ".join(created_keys[:8]) + ("..." if len(created_keys) > 8 else "")
    msg = f"Se han creado exitosamente {len(created_keys)} ejemplares ({sample_keys})."
    if conflicts:
        msg += f" (Se omitieron {len(conflicts)} claves existentes)."

    return True, msg, created_keys, conflicts


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
        existing = conn.execute("SELECT registration_date, indxw, height, last_pruned, last_repotted FROM plants WHERE name = ?", (key,)).fetchone()
        if not existing:
            return False, f"Planta '{key}' no encontrada."

        reg_date = (data.get("registration_date") or "").strip() or (existing["registration_date"] or "")

        old_height = existing["height"] if "height" in existing.keys() else ""
        old_pruned = existing["last_pruned"] if "last_pruned" in existing.keys() else ""
        old_repotted = existing["last_repotted"] if "last_repotted" in existing.keys() else ""

        raw_height = (data.get("height") or "").strip()
        height_val = format_height_entry(raw_height, old_val=old_height)

        raw_pruned = (data.get("last_pruned") or "").strip()
        pruned_val = format_care_entry(raw_pruned, old_val=old_pruned) if raw_pruned else ""

        raw_repotted = (data.get("last_repotted") or "").strip()
        repotted_val = format_care_entry(raw_repotted, old_val=old_repotted) if raw_repotted else ""

        raw_sow = (data.get("sowing_cutting_date") or "").strip()
        if raw_sow:
            dt_sow = parse_plant_date(raw_sow)
            sow_val = dt_sow.strftime("%Y-%m-%d") if dt_sow else raw_sow
        else:
            sow_val = ""

        if "indxw" in data:
            try:
                indxw_val = int(data["indxw"])
            except (ValueError, TypeError):
                indxw_val = 1 if str(data["indxw"]).strip() in ("1", "true", "True", "on") else 0
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
            height_val, reg_date, (data.get("padres") or "").strip(),
            sow_val, (data.get("graft") or "").strip(),
            pruned_val, repotted_val,
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
    """Deletes multiple plants in one transaction. Automatically takes a hidden safety backup snapshot first."""
    clean_keys = [clean_key(k) for k in keys if clean_key(k)]
    if not clean_keys:
        return 0, []

    # Automated hidden safety backup immediately before performing mass removal
    create_pre_bulk_delete_backup()

    all_photos: List[str] = []
    deleted_count = 0
    chunk_size = 900
    with get_connection() as conn:
        for i in range(0, len(clean_keys), chunk_size):
            chunk = clean_keys[i:i + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            cursor = conn.execute(f"SELECT photos FROM plants WHERE name IN ({placeholders})", chunk)
            for row in cursor.fetchall():
                try:
                    p_list = json.loads(row["photos"]) if row["photos"] else []
                    all_photos.extend(p_list)
                except Exception:
                    pass

            cur_del = conn.execute(f"DELETE FROM plants WHERE name IN ({placeholders})", chunk)
            deleted_count += cur_del.rowcount
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


def is_grafted(val: Optional[str]) -> bool:
    """Returns True if the plant has a genuine rootstock graft, False if on own roots or ungrafted."""
    if not val or not isinstance(val, str):
        return False
    v = val.strip().lower()
    if not v or v in ("no", "ninguno", "none", "—", "-"):
        return False
    if "sin injerto" in v or "pie propio" in v or "raíz propia" in v or "raiz propia" in v or "propio" in v:
        return False
    return True


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

        if is_grafted(r["graft"]):
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


def backup_db(custom_target_path: Optional[str] = None, max_retention: int = 20) -> str:
    """
    Safely creates a consistent snapshot of the SQLite database using the native
    online backup API (non-blocking, zero lock contention, crash-proof).
    Retains the most recent snapshots (default: 20) to prevent disk exhaustion.
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

    # Prune old automated backups to keep exactly the latest `max_retention` snapshots
    try:
        backups = sorted([
            os.path.join(BACKUPS_DIR, f)
            for f in os.listdir(BACKUPS_DIR)
            if f.startswith("plantation_backup_") and f.endswith(".db")
        ])
        if len(backups) > max_retention:
            for old_bk in backups[:-max_retention]:
                try:
                    os.remove(old_bk)
                except OSError:
                    pass
    except Exception:
        pass

    return target_file


def create_pre_bulk_delete_backup() -> Optional[str]:
    """
    Creates an automatic, seamless hidden backup snapshot of the SQLite database
    immediately prior to performing a bulk deletion (baja masiva).
    Guarantees that accidental mass removals can always be safely audited or restored.
    """
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_file = os.path.join(BACKUPS_DIR, f"plantation_pre_bulk_delete_{timestamp}.db")

        with get_connection() as src_conn:
            dest_conn = sqlite3.connect(target_file)
            with dest_conn:
                src_conn.backup(dest_conn)
            dest_conn.close()

        # Prune old pre-bulk-delete backups to keep the latest 20 safety rollbacks
        try:
            pre_backups = sorted([
                os.path.join(BACKUPS_DIR, f)
                for f in os.listdir(BACKUPS_DIR)
                if f.startswith("plantation_pre_bulk_delete_") and f.endswith(".db")
            ])
            if len(pre_backups) > 20:
                for old_bk in pre_backups[:-20]:
                    try:
                        os.remove(old_bk)
                    except OSError:
                        pass
        except Exception:
            pass

        print(f"[BACKUP] Hidden pre-bulk-delete snapshot created: {target_file}")
        return target_file
    except Exception as e:
        print(f"[BACKUP] Error creating hidden pre-bulk-delete backup: {e}")
        return None


def validate_and_restore_db(source_db_path: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Validates an uploaded SQLite database file for strict compatibility and structure,
    performs automated migrations if needed, creates a pre-restore rollback snapshot
    of the active database, and performs an atomic online backup replacement.

    Returns:
        (is_valid, message, metadata_dict)
    """
    if not os.path.exists(source_db_path) or os.path.getsize(source_db_path) < 100:
        return False, "El archivo está vacío o no es un archivo de base de datos válido.", {}

    # 1. Check SQLite 3 magic header (first 16 bytes: 'SQLite format 3\\x00')
    try:
        with open(source_db_path, "rb") as f:
            header = f.read(16)
            if header != b"SQLite format 3\x00":
                return False, "Cabecera no válida: El archivo no es una base de datos SQLite versión 3.", {}
    except Exception as e:
        return False, f"Error al leer la cabecera del archivo: {e}", {}

    # 2. Open connection to candidate database and check integrity
    try:
        cand_conn = sqlite3.connect(source_db_path)
        cand_conn.row_factory = sqlite3.Row
        cur = cand_conn.cursor()

        # PRAGMA integrity_check
        cur.execute("PRAGMA integrity_check;")
        res = cur.fetchone()
        if not res or res[0] != "ok":
            cand_conn.close()
            return False, f"Integridad corrupta: SQLite integrity_check falló ({res[0] if res else 'desconocido'}).", {}

        # 3. Check for existence of essential 'plants' table
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='plants';")
        if not cur.fetchone():
            cand_conn.close()
            return False, "Incompatible: El archivo no contiene la tabla obligatoria 'plants' requerida por Plantation.", {}

        # 4. Check mandatory columns in 'plants'
        cur.execute("PRAGMA table_info(plants);")
        col_rows = cur.fetchall()
        col_names = [r["name"] for r in col_rows]

        if "name" not in col_names or "species" not in col_names:
            cand_conn.close()
            return False, "Incompatible: La tabla 'plants' carece de las columnas clave ('name' y 'species').", {}

        # 5. Backward compatibility auto-migration: Add any missing modern columns
        expected_cols = {
            "aka": "TEXT DEFAULT ''",
            "location": "TEXT DEFAULT ''",
            "height": "TEXT DEFAULT ''",
            "registration_date": "TEXT DEFAULT ''",
            "padres": "TEXT DEFAULT ''",
            "sowing_cutting_date": "TEXT DEFAULT ''",
            "graft": "TEXT DEFAULT ''",
            "last_pruned": "TEXT DEFAULT ''",
            "last_repotted": "TEXT DEFAULT ''",
            "fertilizante": "TEXT DEFAULT ''",
            "photos": "TEXT DEFAULT '[]'",
            "status": "TEXT NOT NULL DEFAULT 'OK'",
            "comentarios": "TEXT DEFAULT ''",
            "indxw": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TEXT DEFAULT CURRENT_TIMESTAMP",
            "updated_at": "TEXT DEFAULT CURRENT_TIMESTAMP"
        }
        for col, col_def in expected_cols.items():
            if col not in col_names:
                cand_conn.execute(f"ALTER TABLE plants ADD COLUMN {col} {col_def};")

        # 6. Normalize and repair data
        cand_conn.execute("UPDATE plants SET status = 'OK' WHERE status IS NULL OR lower(trim(status)) = 'ok';")
        cand_conn.execute("UPDATE plants SET status = 'notOK' WHERE status != 'OK';")

        # Ensure indexes exist
        for col in ("species", "status", "location", "aka", "height"):
            cand_conn.execute(f"CREATE INDEX IF NOT EXISTS idx_plants_{col} ON plants({col});")
        cand_conn.commit()

        # 7. Collect metadata statistics
        cur.execute("SELECT count(*) FROM plants;")
        total_plants = cur.fetchone()[0]

        cur.execute("SELECT photos FROM plants;")
        total_photos_count = 0
        for row in cur.fetchall():
            try:
                p_list = json.loads(row[0]) if row[0] else []
                total_photos_count += len(p_list)
            except Exception:
                pass

        cand_conn.close()

    except Exception as e:
        return False, f"Error durante la validación del esquema de la base de datos: {e}", {}

    # 8. Create automatic safety rollback snapshot of the ACTIVE database before replacement
    safety_backup_name = None
    try:
        os.makedirs(BACKUPS_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        safety_path = os.path.join(BACKUPS_DIR, f"plantation_pre_restore_{ts}.db")
        with get_connection() as active_conn:
            dest_backup = sqlite3.connect(safety_path)
            with dest_backup:
                active_conn.backup(dest_backup)
            dest_backup.close()
        safety_backup_name = os.path.basename(safety_path)
        print(f"[RESTORE] Created pre-restore rollback backup: {safety_path}")

        # Prune old pre-restore safety rollbacks to keep the latest 20 snapshots
        try:
            restore_backups = sorted([
                os.path.join(BACKUPS_DIR, f)
                for f in os.listdir(BACKUPS_DIR)
                if f.startswith("plantation_pre_restore_") and f.endswith(".db")
            ])
            if len(restore_backups) > 20:
                for old_bk in restore_backups[:-20]:
                    try:
                        os.remove(old_bk)
                    except OSError:
                        pass
        except Exception:
            pass
    except Exception as e:
        print(f"[RESTORE] Warning: Could not create pre-restore snapshot: {e}")

    # 9. Atomic online replacement of active DB
    try:
        with _db_lock:
            with sqlite3.connect(source_db_path) as src_conn:
                dest_conn = _open_raw_connection()
                try:
                    dest_conn.execute("PRAGMA journal_mode = WAL;")
                    src_conn.backup(dest_conn)
                finally:
                    dest_conn.close()

            # Re-run init_db to set WAL, verify integrity, and prime caches
            init_db()

    except Exception as e:
        return False, f"Error crítico al sustituir la base de datos: {e}", {}

    metadata = {
        "total_plants": total_plants,
        "total_photos_referenced": total_photos_count,
        "safety_backup": safety_backup_name or "plantation_pre_restore.db",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    return True, "Base de datos verificada, migrada e importada con éxito.", metadata


def get_database_health() -> Dict[str, Any]:
    """Returns database health metrics, integrity status, and backup snapshot details."""
    integrity_ok, integrity_msg = check_database_integrity()
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0

    backups = []
    if os.path.exists(BACKUPS_DIR):
        for f in os.listdir(BACKUPS_DIR):
            if (f.startswith("plantation_backup_") or f.startswith("plantation_pre_bulk_delete_") or f.startswith("plantation_pre_restore_")) and f.endswith(".db"):
                fp = os.path.join(BACKUPS_DIR, f)
                try:
                    mtime = os.path.getmtime(fp)
                    size = os.path.getsize(fp)
                    is_pre_del = "pre_bulk_delete" in f or "pre_restore" in f
                    backups.append({"filename": f, "path": fp, "mtime": mtime, "size": size, "is_pre_delete": is_pre_del})
                except OSError:
                    pass
    backups.sort(key=lambda x: x["mtime"], reverse=True)

    latest_time_str = "Ninguno"
    if backups:
        latest_time_str = datetime.fromtimestamp(backups[0]["mtime"]).strftime("%Y-%m-%d %H:%M:%S")

    size_formatted = f"{db_size / 1024:.1f} KB" if db_size < 1024 * 1024 else f"{db_size / (1024 * 1024):.2f} MB"

    return {
        "integrity_ok": integrity_ok,
        "integrity_message": integrity_msg,
        "total_backups": len(backups),
        "latest_backup_time": latest_time_str,
        "latest_backup_filename": backups[0]["filename"] if backups else None,
        "database_size_bytes": db_size,
        "database_size_formatted": size_formatted,
        "backups_list": backups[:20],
    }


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



