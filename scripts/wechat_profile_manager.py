#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WeChat profile manager for multi-account workflow.

Use this script to save/switch multiple official-account profiles while
keeping compatibility with existing single-file config (`wechat_config.json`).
"""

from __future__ import annotations

import argparse
import json
import shutil
import requests
from pathlib import Path
from typing import Dict, Any

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_FILE = DATA_DIR / "wechat_config.json"
PROFILES_DIR = DATA_DIR / "wechat_profiles"
ACTIVE_FILE = DATA_DIR / "wechat_active_profile.txt"

VALID_FIELDS = {
    "appid",
    "appsecret",
    "author",
    "images_dir",
    "topic",
    "audience",
    "style",
    "cta",
    "notes",
}
TOKEN_ENDPOINT = "https://api.weixin.qq.com/cgi-bin/token"


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def profile_path(name: str) -> Path:
    safe = name.strip().replace(" ", "_")
    return PROFILES_DIR / f"{safe}.json"


def mask_appid(appid: str) -> str:
    if not appid:
        return "(empty)"
    if len(appid) <= 12:
        return "****"
    return f"{appid[:8]}****{appid[-4:]}"


def get_active_profile_name() -> str:
    if ACTIVE_FILE.exists():
        return ACTIVE_FILE.read_text(encoding="utf-8").strip()
    return ""


def set_active_profile_name(name: str) -> None:
    ACTIVE_FILE.write_text(name, encoding="utf-8")


def cmd_list() -> int:
    ensure_dirs()
    active = get_active_profile_name()
    files = sorted(PROFILES_DIR.glob("*.json"))
    if not files:
        print("No profiles found. Save one with: save --name <profile>")
        return 0

    print("WeChat profiles:")
    for fp in files:
        name = fp.stem
        data = read_json(fp)
        appid = mask_appid(data.get("appid", ""))
        author = data.get("author", "")
        topic = data.get("topic", "")
        marker = "*" if name == active else " "
        print(f"{marker} {name:18} appid={appid} author={author} topic={topic}")
    return 0


def cmd_status() -> int:
    ensure_dirs()
    active = get_active_profile_name()
    current = read_json(CONFIG_FILE)
    print(f"Active profile: {active or '(none)'}")
    print(f"Current config: {CONFIG_FILE}")
    print(f"Current appid : {mask_appid(current.get('appid', ''))}")
    print(f"Current author: {current.get('author', '(empty)')}")
    print(f"Current topic : {current.get('topic', '(empty)')}")
    return 0


def cmd_save(name: str) -> int:
    ensure_dirs()
    current = read_json(CONFIG_FILE)
    if not current.get("appid") or not current.get("appsecret"):
        print("Current config is missing appid/appsecret. Configure first.")
        return 1
    fp = profile_path(name)
    write_json(fp, current)
    print(f"Saved profile: {fp}")
    return 0


def cmd_use(name: str) -> int:
    ensure_dirs()
    fp = profile_path(name)
    if not fp.exists():
        print(f"Profile not found: {name}")
        return 1
    shutil.copyfile(fp, CONFIG_FILE)
    set_active_profile_name(name)
    data = read_json(fp)
    print(f"Switched to profile: {name}")
    print(f"appid={mask_appid(data.get('appid', ''))} author={data.get('author', '')}")
    return 0


def cmd_new(args: argparse.Namespace) -> int:
    ensure_dirs()
    if not args.appid or not args.appsecret:
        print("new requires --appid and --appsecret")
        return 1

    payload = {
        "appid": args.appid.strip(),
        "appsecret": args.appsecret.strip(),
        "author": (args.author or "Author").strip(),
        "images_dir": (args.images_dir or "").strip(),
        "topic": (args.topic or "").strip(),
        "audience": (args.audience or "").strip(),
        "style": (args.style or "").strip(),
        "cta": (args.cta or "").strip(),
        "notes": (args.notes or "").strip(),
    }
    fp = profile_path(args.name)
    write_json(fp, payload)
    print(f"Created profile: {fp}")

    if args.activate:
        shutil.copyfile(fp, CONFIG_FILE)
        set_active_profile_name(args.name)
        print(f"Activated profile: {args.name}")
    return 0


def cmd_show(name: str) -> int:
    fp = profile_path(name)
    if not fp.exists():
        print(f"Profile not found: {name}")
        return 1
    data = read_json(fp)
    out = data.copy()
    if "appsecret" in out and out["appsecret"]:
        out["appsecret"] = "****"
    if "appid" in out:
        out["appid"] = mask_appid(out.get("appid", ""))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


def cmd_update(name: str, field: str, value: str) -> int:
    if field not in VALID_FIELDS:
        print(f"Invalid field: {field}")
        print(f"Valid fields: {', '.join(sorted(VALID_FIELDS))}")
        return 1
    fp = profile_path(name)
    if not fp.exists():
        print(f"Profile not found: {name}")
        return 1
    data = read_json(fp)
    data[field] = value
    write_json(fp, data)
    print(f"Updated profile '{name}': {field}={value}")

    if get_active_profile_name() == name:
        shutil.copyfile(fp, CONFIG_FILE)
        print("Active config updated.")
    return 0


def cmd_delete(name: str) -> int:
    fp = profile_path(name)
    if not fp.exists():
        print(f"Profile not found: {name}")
        return 1
    fp.unlink()
    print(f"Deleted profile: {name}")
    if get_active_profile_name() == name:
        ACTIVE_FILE.unlink(missing_ok=True)
        print("Active profile marker cleared.")
    return 0


def _verify_token(data: Dict[str, Any]) -> tuple[bool, str]:
    appid = (data.get("appid") or "").strip()
    appsecret = (data.get("appsecret") or "").strip()
    if not appid or not appsecret:
        return False, "missing appid/appsecret"
    try:
        r = requests.get(
            TOKEN_ENDPOINT,
            params={"grant_type": "client_credential", "appid": appid, "secret": appsecret},
            timeout=20,
        )
        j = r.json()
        if "access_token" in j:
            return True, "ok"
        return False, f"{j.get('errcode', 'N/A')} {j.get('errmsg', 'unknown')}"
    except Exception as e:
        return False, str(e)


def cmd_select(verify: bool = False) -> int:
    ensure_dirs()
    files = sorted(PROFILES_DIR.glob("*.json"))
    if not files:
        print("No profiles found. Create one first.")
        return 1
    active = get_active_profile_name()
    print("Choose WeChat profile:")
    for i, fp in enumerate(files, start=1):
        name = fp.stem
        data = read_json(fp)
        marker = "*" if name == active else " "
        print(f"{i}. {marker} {name} ({mask_appid(data.get('appid', ''))})")
    raw = input("Input number (or Enter to cancel): ").strip()
    if not raw:
        print("Cancelled.")
        return 0
    try:
        idx = int(raw)
        if idx < 1 or idx > len(files):
            raise ValueError
    except ValueError:
        print("Invalid selection.")
        return 1

    name = files[idx - 1].stem
    code = cmd_use(name)
    if code != 0:
        return code
    if verify:
        data = read_json(profile_path(name))
        ok, msg = _verify_token(data)
        if ok:
            print("Token verify: SUCCESS")
        else:
            print(f"Token verify: FAILED ({msg})")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Manage multiple WeChat account profiles")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="List saved profiles")
    sub.add_parser("status", help="Show active/current profile")

    sp = sub.add_parser("save", help="Save current wechat_config.json as a named profile")
    sp.add_argument("--name", required=True)

    up = sub.add_parser("use", help="Switch active profile (copy to wechat_config.json)")
    up.add_argument("--name", required=True)

    sel = sub.add_parser("select", help="Interactively choose and activate a profile")
    sel.add_argument("--verify", action="store_true", help="Verify token after switching")

    np = sub.add_parser("new", help="Create profile from parameters")
    np.add_argument("--name", required=True)
    np.add_argument("--appid", required=True)
    np.add_argument("--appsecret", required=True)
    np.add_argument("--author", default="Author")
    np.add_argument("--images-dir", default="")
    np.add_argument("--topic", default="")
    np.add_argument("--audience", default="")
    np.add_argument("--style", default="")
    np.add_argument("--cta", default="")
    np.add_argument("--notes", default="")
    np.add_argument("--activate", action="store_true")

    shp = sub.add_parser("show", help="Show one profile (masked)")
    shp.add_argument("--name", required=True)

    udp = sub.add_parser("update", help="Update one field in a profile")
    udp.add_argument("--name", required=True)
    udp.add_argument("--field", required=True)
    udp.add_argument("--value", required=True)

    dp = sub.add_parser("delete", help="Delete a profile")
    dp.add_argument("--name", required=True)
    return p


def main() -> int:
    args = build_parser().parse_args()
    if args.cmd == "list":
        return cmd_list()
    if args.cmd == "status":
        return cmd_status()
    if args.cmd == "save":
        return cmd_save(args.name)
    if args.cmd == "use":
        return cmd_use(args.name)
    if args.cmd == "select":
        return cmd_select(verify=args.verify)
    if args.cmd == "new":
        return cmd_new(args)
    if args.cmd == "show":
        return cmd_show(args.name)
    if args.cmd == "update":
        return cmd_update(args.name, args.field, args.value)
    if args.cmd == "delete":
        return cmd_delete(args.name)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
