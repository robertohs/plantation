"""
Plantation - Server Logic and Application Startup
Mounts FastAPI app, static assets, Images directory, and runs Uvicorn on port 3000.
"""

import argparse
import asyncio
import mimetypes
import os
import re
import subprocess
import sys
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

# Register critical image MIME types so browsers receive correct Content-Type
mimetypes.add_type("image/webp", ".webp")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/jpeg", ".jpg")
mimetypes.add_type("image/jpeg", ".jpeg")
mimetypes.add_type("image/png", ".png")
mimetypes.add_type("image/gif", ".gif")
mimetypes.add_type("image/svg+xml", ".svg")

from contextlib import asynccontextmanager
import db
import img_conv
from FastAPI.fapi import router as fapi_router

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "FastAPI", "static")
IMAGES_DIR = os.path.join(BASE_DIR, "Images")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "DB"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "DB", "backups"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "tmp"), exist_ok=True)


def patch_uvicorn_upgrade_handling():
    """
    Ensures Uvicorn does not fail with 400 'Unsupported upgrade request.' when a reverse
    proxy forwards 'Connection: upgrade' on regular HTTP requests without an 'Upgrade: websocket' header.
    """
    try:
        from uvicorn.protocols.http.h11_impl import H11Protocol, RequestResponseCycle

        orig_handle_upgrade = H11Protocol.handle_upgrade

        def safe_handle_upgrade(self, event):
            upgrade_value = None
            for name, value in self.headers:
                if name == b"upgrade":
                    upgrade_value = value.lower()
            if upgrade_value != b"websocket" or self.ws_protocol_class is None:
                # Handle as standard HTTP request instead of 400 Bad Request
                self.cycle = RequestResponseCycle(
                    scope=self.scope,
                    conn=self.conn,
                    transport=self.transport,
                    flow=self.flow,
                    logger=self.logger,
                    access_logger=self.access_logger,
                    access_log=self.access_log,
                    default_headers=self.default_headers,
                    message_event=asyncio.Event(),
                    on_response=self.on_response_complete,
                )
                task = self.loop.create_task(self.cycle.run_asgi(self.app))
                task.add_done_callback(self.tasks.discard)
                self.tasks.add(task)
                return
            return orig_handle_upgrade(self, event)

        H11Protocol.handle_upgrade = safe_handle_upgrade
    except Exception as e:
        print(f"[WARN] Could not patch Uvicorn upgrade handler: {e}")


def ensure_nginx_config():
    """Ensures nginx properly maps WebSocket upgrade headers without breaking standard HTTP."""
    for conf_path in ["/etc/nginx/nginx.conf", "/etc/nginx/nginx.conf.template"]:
        if not os.path.exists(conf_path):
            continue
        try:
            with open(conf_path, "r") as f:
                content = f.read()
            changed = False
            if 'map $http_upgrade $connection_upgrade' not in content:
                map_code = "\n    map $http_upgrade $connection_upgrade {\n        default upgrade;\n        '' close;\n    }\n"
                content = content.replace("http {", "http {" + map_code, 1)
                changed = True
            if 'proxy_set_header Connection "upgrade";' in content:
                content = content.replace('proxy_set_header Connection "upgrade";', 'proxy_set_header Connection $connection_upgrade;')
                changed = True
            if changed:
                with open(conf_path, "w") as f:
                    f.write(content)
                subprocess.run(["nginx", "-s", "reload"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Executes atomic startup initialization cleanly without duplicate imports."""
    db.init_db()
    db.start_backup_scheduler(interval_seconds=43200)
    img_conv.ensure_images_dir()
    img_conv.generate_seed_photos_if_missing()
    yield


app = FastAPI(
    title="Plantation",
    description="Welcome!",
    version="0.0.1",
    lifespan=lifespan
)


@app.middleware("http")
async def head_request_middleware(request: Request, call_next):
    """Handle HEAD requests (e.g. cloud health checks and probes) with 200 OK headers."""
    is_head = request.method == "HEAD"
    if is_head:
        request.scope["method"] = "GET"
    response = await call_next(request)
    if is_head:
        return Response(
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
    return response


# Mount Static CSS and Images folders
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/images", StaticFiles(directory=IMAGES_DIR), name="images")

# Mount HTMX routes
app.include_router(fapi_router)

# Apply proxy compatibility and protocol patches
patch_uvicorn_upgrade_handling()
ensure_nginx_config()


def main():
    parser = argparse.ArgumentParser(description="Plantation Server")
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=3000, help="Bind port (default: 3000)")
    parser.add_argument("--reload", action="store_true", help="Enable reload")
    args, unknown = parser.parse_known_args()

    patch_uvicorn_upgrade_handling()
    ensure_nginx_config()

    print(f"==================================================")
    print(f"  PLANTATION BOTANICAL ARCHIVE                   ")
    print(f"  Serving on: http://{args.host}:{args.port}      ")
    print(f"  Database:   DB/plantation.db                   ")
    print(f"  Images:     Images/                            ")
    print(f"==================================================")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=False,
        log_level="info",
        http="h11"
    )


if __name__ == "__main__":
    main()
