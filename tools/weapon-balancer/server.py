#!/usr/bin/env python3
"""Weapon balancer - local web tool for normalising Skyrim weapon stats.

Phase 1 is read-only with respect to the game: the tool scans the active MO2
load order, shows every weapon, lets you set per-category caps and per-weapon
overrides, and previews the resulting change list. Nothing is written back to
the plugins yet; the patch writer plugs in behind ``/api/write`` later.

Usage:
    python server.py --mo2 "C:/.../MO2" --data "C:/.../SkyrimSE/Data"
"""
from __future__ import annotations

import argparse
import gzip
import json
import mimetypes
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import plan as plan_module  # noqa: E402
import scan as scan_module  # noqa: E402
import write as write_module  # noqa: E402

# When frozen by PyInstaller the code sits in a temporary bundle directory
# (_MEIPASS) while writable files must live next to the executable.
FROZEN = bool(getattr(sys, "frozen", False))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", ROOT))
BASE_DIR = Path(sys.executable).resolve().parent if FROZEN else ROOT
DATA_ROOT = BASE_DIR / "武器平衡工具-data" if FROZEN else BASE_DIR

WEB_DIR = RESOURCE_DIR / "web"
STATE_PATH = DATA_ROOT / "state.json"
CACHE_PATH = DATA_ROOT / "cache" / "weapons.json"
OUTPUT_DIR = DATA_ROOT / "output"

DEFAULT_CONFIG = {
    "mo2_dir": r"C:\Users\linos\Desktop\games\+skyrim\MO2",
    "data_dir": r"C:\Users\linos\Desktop\games\+skyrim\SkyrimSE\Data",
    "profile": None,
}


def _default_config() -> dict:
    """Prefer the configured paths, otherwise look next to the executable."""
    config = dict(DEFAULT_CONFIG)
    if not Path(config["mo2_dir"]).exists():
        sibling = BASE_DIR.parent / "MO2"
        if sibling.exists():
            config["mo2_dir"] = str(sibling)
    if not Path(config["data_dir"]).exists():
        sibling = BASE_DIR.parent / "SkyrimSE" / "Data"
        if sibling.exists():
            config["data_dir"] = str(sibling)
    return config


def _merge_config(state_config: dict | None) -> dict:
    """Stored config wins only when it still points at an existing folder."""
    config = _default_config()
    stored = state_config or {}
    for key in ("mo2_dir", "data_dir"):
        if stored.get(key) and Path(stored[key]).exists():
            config[key] = stored[key]
    if stored.get("profile"):
        config["profile"] = stored["profile"]
    return config

CATALOG: dict = {"weapons": [], "plugins": []}
STATE_LOCK = threading.Lock()


def load_state() -> dict:
    state = {
        "config": _default_config(),
        "caps": {},
        "overrides": {},
        "filters": dict(plan_module.DEFAULT_FILTERS),
        "options": dict(plan_module.DEFAULT_OPTIONS),
        "limits": dict(plan_module.LIMITS),
    }
    if STATE_PATH.exists():
        try:
            stored = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            for key in ("config", "caps", "overrides", "filters", "options", "limits"):
                if key in stored:
                    if key == "config":
                        state["config"].update(stored[key] or {})
                    else:
                        state[key].update(stored[key] or {})
        except Exception as error:
            print(f"[state] could not read state.json: {error}")
    state["config"] = _merge_config(state["config"])
    return state


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def bootstrap() -> dict:
    state = load_state()
    return {
        "config": state["config"],
        "caps": {key: value for key, value in state["caps"].items() if value},
        "overrides": state["overrides"],
        "filters": plan_module.merge_filters(state["filters"]),
        "options": plan_module.merge_options(state["options"]),
        "limits": plan_module.validate_limits(state["limits"]),
        "categories": scan_module.CATEGORIES,
        "vanilla_ceiling": scan_module.VANILLA_CEILING,
        "vanilla_speed": scan_module.VANILLA_SPEED,
        "scan": {
            key: CATALOG.get(key)
            for key in (
                "generated",
                "elapsed",
                "profile",
                "language",
                "plugin_count",
                "enabled_count",
                "failure_count",
                "failures",
                "from_cache",
                "signature",
            )
        },
        "weapon_count": len(CATALOG.get("weapons", [])),
        "data_root": str(DATA_ROOT),
        "frozen": FROZEN,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "WeaponBalancer/0.1"

    def log_message(self, fmt, *args):  # quieter console
        if "/api/" in (self.path or ""):
            return
        super().log_message(fmt, *args)

    # ---------------------------------------------------------------- helpers
    def _send(self, status: int, payload, content_type="application/json"):
        if isinstance(payload, (dict, list)):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        elif isinstance(payload, str):
            body = payload.encode("utf-8")
        else:
            body = payload
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        # The weapon catalogue is a few megabytes; gzip keeps the page load fast.
        if len(body) > 65536 and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            body = gzip.compress(body, 5)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception:
            return {}

    def _static(self, relative: str):
        target = (WEB_DIR / relative).resolve()
        if not str(target).startswith(str(WEB_DIR.resolve())) or not target.is_file():
            self._send(404, {"error": "not found"})
            return
        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        if target.suffix in (".js", ".css", ".html"):
            content_type += "; charset=utf-8"
        self._send(200, target.read_bytes(), content_type)

    # -------------------------------------------------------------------- GET
    def do_GET(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._static("index.html")
        elif path == "/api/bootstrap":
            self._send(200, bootstrap())
        elif path == "/api/weapons":
            self._send(
                200,
                {
                    "categories": scan_module.CATEGORIES,
                    "weapons": CATALOG.get("weapons", []),
                },
            )
        elif path.startswith("/static/"):
            self._static(path[len("/static/") :])
        else:
            self._send(404, {"error": "not found"})

    # ------------------------------------------------------------------- POST
    def do_POST(self):  # noqa: N802
        path = self.path.split("?", 1)[0]
        body = self._body()
        if path == "/api/plan":
            state = load_state()
            caps = body.get("caps", state["caps"])
            overrides = body.get("overrides", state["overrides"])
            filters = body.get("filters", state["filters"])
            options = body.get("options", state["options"])
            limits = body.get("limits", state["limits"])
            result = plan_module.compute_plan(
                CATALOG.get("weapons", []), caps, overrides, filters, options, limits
            )
            self._send(200, result)
        elif path == "/api/state":
            with STATE_LOCK:
                state = load_state()
                for key in ("caps", "overrides", "filters", "options", "limits"):
                    if key in body:
                        if key in ("caps", "overrides"):
                            state[key] = body[key] or {}
                        else:
                            state[key].update(body[key] or {})
                if "config" in body:
                    state["config"].update(body["config"] or {})
                save_state(state)
            self._send(200, bootstrap())
        elif path == "/api/rescan":
            try:
                refresh_catalog(force=True)
                self._send(200, {"ok": True, **bootstrap()})
            except Exception as error:
                self._send(500, {"ok": False, "error": str(error)})
        elif path == "/api/export":
            try:
                state = load_state()
                result = plan_module.compute_plan(
                    CATALOG.get("weapons", []),
                    body.get("caps", state["caps"]),
                    body.get("overrides", state["overrides"]),
                    body.get("filters", state["filters"]),
                    body.get("options", state["options"]),
                    body.get("limits", state["limits"]),
                )
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y%m%d-%H%M%S")
                target = OUTPUT_DIR / f"weapon-balance-plan-{stamp}.csv"
                target.write_text(plan_module.plan_to_csv(result), encoding="utf-8-sig")
                self._send(200, {"ok": True, "path": str(target), "changed": len(result["changes"])})
            except Exception as error:
                self._send(500, {"ok": False, "error": str(error)})
        elif path == "/api/write":
            # Only ever creates/refreshes the balancer's own MO2 mod folder; the
            # original plugins are never touched.
            if not body.get("confirm"):
                self._send(400, {"ok": False, "error": "missing confirm flag"})
                return
            try:
                state = load_state()
                result = plan_module.compute_plan(
                    CATALOG.get("weapons", []),
                    body.get("caps", state["caps"]),
                    body.get("overrides", state["overrides"]),
                    body.get("filters", state["filters"]),
                    body.get("options", state["options"]),
                    body.get("limits", state["limits"]),
                )
                config = dict(state["config"])
                config.update(body.get("config") or {})
                report = write_module.build(
                    config,
                    result,
                    mod_name=body.get("mod_name", "武器平衡-WeaponRebalance"),
                    plugin_name=body.get("plugin_name", "WeaponRebalance.esp"),
                )
                self._send(200, report)
            except Exception as error:
                self._send(500, {"ok": False, "error": f"{type(error).__name__}: {error}"})
        else:
            self._send(404, {"error": "not found"})


def refresh_catalog(force: bool = False) -> dict:
    global CATALOG
    state = load_state()
    if force and CACHE_PATH.exists():
        CACHE_PATH.unlink(missing_ok=True)
    CATALOG = scan_module.scan_cached(state["config"], CACHE_PATH)
    return CATALOG


def main() -> int:
    parser = argparse.ArgumentParser(description="Skyrim weapon balancer (local web GUI)")
    parser.add_argument("--mo2", help="Mod Organizer 2 folder")
    parser.add_argument("--data", help="SkyrimSE/Data folder")
    parser.add_argument("--profile", help="MO2 profile name (default: selected profile)")
    parser.add_argument("--port", type=int, default=8752)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--rescan", action="store_true", help="ignore the scan cache")
    args = parser.parse_args()

    state = load_state()
    if args.mo2:
        state["config"]["mo2_dir"] = args.mo2
    if args.data:
        state["config"]["data_dir"] = args.data
    if args.profile:
        state["config"]["profile"] = args.profile
    with STATE_LOCK:
        save_state(state)

    print(f"[scan] profile={state['config'].get('profile') or 'auto'} ...")
    catalog = refresh_catalog(force=args.rescan)
    print(
        f"[scan] {catalog.get('plugin_count')} plugins, "
        f"{len(catalog.get('weapons', []))} weapon records, "
        f"{catalog.get('elapsed')}s, cache={'hit' if catalog.get('from_cache') else 'miss'}"
    )
    print(f"[data] {DATA_ROOT}")

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    url = f"http://127.0.0.1:{args.port}/"
    print(f"[web] {url}")
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[web] stopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
