"""
Plantation - Server Logic and Application Startup
Mounts FastAPI app, static assets, Images directory, and runs Uvicorn on port 3000.
"""

import argparse
import mimetypes
import os
import sys
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Register critical image MIME types so browsers receive correct Content-Type
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpeg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/gif", ".gif")
mimetypes.add_type("image/svg+xml", ".svg")

import db
import img_conv
from FastAPI.fapi import router as fapi_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "FastAPI", "static")
IMAGES_DIR = os.path.join(BASE_DIR, "Images")

# Initialize database schema and default seeds
db.init_db()

# Start background backup scheduler (every 12 hours)
db.start_backup_scheduler(interval_seconds=43200)

# Ensure images directory and sample illustrations
img_conv.ensure_images_dir()
img_conv.generate_seed_photos_if_missing()

app = FastAPI(
    title="Plantation",
    description="Welcome!",
    version="0.0.1"
)

# Mount Static CSS and Images folders
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# Mount HTMX routes
app.include_router(fapi_router)


def main():
    parser = argparse.ArgumentParser(description="Plantation Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="Bind port (default: 3000)")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    args, unknown = parser.parse_known_args()

    print(f"==================================================")
    print(f"  PLANTATION -       ")
    print(f"  Serving on: http://{args.host}:{args.port}      ")
    print(f"  Database:   DB/plantation.db                   ")
    print(f"  Images:     Images/                            ")
    print(f"==================================================")

    uvicorn.run(
        "server:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info"
    )


if __name__ == "__main__":
    main()
