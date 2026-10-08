#!/usr/bin/env python3
"""
Publish the local updates/UTM_Coordinate_Wizard_Lecturer/ package to the stable
GitHub release tag on the UTM_Programs_Freeware repo.

  python bin/tools/publish_github_update.py
  python bin/tools/publish_github_update.py --notes "Fixed Cassini zone table"

Requires:
  - EA_GITHUB_TOKEN env var (classic or fine-grained PAT with Contents: write / releases)

Only run after the EXE was tested OK on a PC.
"""
from __future__ import annotations

import json
import mimetypes
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")

_TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(_TOOLS))  # UTM_Classroom/

GITHUB_OWNER = "trojanforce96"
GITHUB_REPO = "UTM_Programs_Freeware"
APP = "UTM_Coordinate_Wizard_Lecturer"
TAG = f"update-{APP}"
PACKAGE_DIR = os.path.join(ROOT, "updates", APP)

# Skip sidecars that are not needed on the release channel
SKIP_NAMES = {"ea_update.json", "ea_update.json.example", "version.txt"}


def _token() -> str:
    t = (os.environ.get("EA_GITHUB_TOKEN") or "").strip()
    if not t:
        raise SystemExit(
            "ERROR: Set environment variable EA_GITHUB_TOKEN "
            "(GitHub PAT with permission to upload releases)."
        )
    return t


def _request(
    method: str,
    url: str,
    token: str,
    *,
    data: bytes | None = None,
    content_type: str | None = None,
    accept: str = "application/vnd.github+json",
) -> tuple[int, Any]:
    headers = {
        "User-Agent": "UTM-Publish/1.0",
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            body = resp.read()
            code = resp.getcode() or 200
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"GitHub API {method} {url}\nHTTP {e.code}: {err}") from e
    if not body:
        return code, None
    try:
        return code, json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        return code, body


def _get_release(owner: str, repo: str, tag: str, token: str) -> dict | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{urllib.parse.quote(tag)}"
    try:
        _code, data = _request("GET", url, token)
        return data if isinstance(data, dict) else None
    except SystemExit as e:
        if "HTTP 404" in str(e):
            return None
        raise


def _create_release(
    owner: str, repo: str, tag: str, token: str, name: str, body: str
) -> dict:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases"
    payload = json.dumps(
        {
            "tag_name": tag,
            "name": name,
            "body": body,
            "draft": False,
            "prerelease": False,
        }
    ).encode("utf-8")
    _code, data = _request(
        "POST", url, token, data=payload, content_type="application/json"
    )
    if not isinstance(data, dict) or "id" not in data:
        raise SystemExit(f"Could not create release: {data}")
    return data


def _update_release(
    owner: str, repo: str, release_id: int, token: str, *, name: str, body: str
) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/{release_id}"
    payload = json.dumps({"name": name, "body": body}).encode("utf-8")
    _request("PATCH", url, token, data=payload, content_type="application/json")


def _read_version(folder: str) -> str:
    for name in ("version.txt", "manifest.json"):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if name == "version.txt":
            return open(path, encoding="utf-8").read().strip() or "unknown"
        with open(path, encoding="utf-8") as f:
            man = json.load(f)
        if isinstance(man, dict) and man.get("version"):
            return str(man["version"]).strip()
    return "unknown"


def _notes(version: str, notes_arg: str) -> tuple[str, str]:
    """Return (release_name, release_body)."""
    name = f"UTM Coordinate Wizard Lecturer {version}"
    if notes_arg.strip():
        return name, notes_arg.strip() + "\n"
    default = (
        f"## {name}\n\n"
        "Lecturer live auto-update channel. Overwritten when a tested build is published.\n"
    )
    return name, default


def _delete_asset(owner: str, repo: str, asset_id: int, token: str) -> None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
    _request("DELETE", url, token)


def _github_asset_name(name: str) -> str:
    """GitHub Releases rewrites spaces in asset names to dots — match that."""
    return name.replace(" ", ".")


def _upload_asset(
    upload_url_template: str, path: str, token: str, *, asset_name: str | None = None
) -> None:
    name = asset_name or _github_asset_name(os.path.basename(path))
    # upload_url looks like .../assets{?name,label}
    base = upload_url_template.split("{", 1)[0]
    url = base + "?" + urllib.parse.urlencode({"name": name})
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        data = f.read()
    _request(
        "POST",
        url,
        token,
        data=data,
        content_type=ctype,
        accept="application/vnd.github+json",
    )


def _manifest_for_github(folder: str) -> bytes:
    """Rewrite exe_name / files[] to GitHub asset naming (spaces → dots)."""
    man_path = os.path.join(folder, "manifest.json")
    with open(man_path, encoding="utf-8") as f:
        man = json.load(f)
    if not isinstance(man, dict):
        raise SystemExit(f"Invalid manifest: {man_path}")
    orig_exe = str(man.get("exe_name", "") or "")
    if orig_exe:
        new_exe = _github_asset_name(orig_exe)
        man["exe_name"] = new_exe
        files = man.get("files") or []
        if isinstance(files, list):
            for i, entry in enumerate(files):
                if isinstance(entry, dict) and entry.get("name") == orig_exe:
                    files[i] = {**entry, "name": new_exe}
                elif isinstance(entry, str) and entry == orig_exe:
                    files[i] = new_exe
            man["files"] = files
    return (json.dumps(man, indent=2) + "\n").encode("utf-8")


def _files_to_upload(folder: str) -> list[str]:
    """Collect files to upload; one asset per basename (spaces→dots)."""
    by_asset: dict[str, str] = {}
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if name in SKIP_NAMES or name.startswith("."):
            continue
        by_asset[_github_asset_name(name)] = path
    return [by_asset[k] for k in sorted(by_asset)]


def publish(notes: str = "") -> None:
    folder = PACKAGE_DIR
    if not os.path.isdir(folder):
        raise SystemExit(f"ERROR: Missing folder: {folder}\nBuild the EXE first.")
    man = os.path.join(folder, "manifest.json")
    if not os.path.isfile(man):
        raise SystemExit(f"ERROR: Missing {man} — build first.")

    version = _read_version(folder)
    rel_name, rel_body = _notes(version, notes)

    token = _token()
    owner, repo, tag = GITHUB_OWNER, GITHUB_REPO, TAG
    print(f"Publishing {APP} v{version} → {owner}/{repo} tag {tag}")

    release = _get_release(owner, repo, tag, token)
    if not release:
        print("Creating release…")
        release = _create_release(owner, repo, tag, token, name=rel_name, body=rel_body)
    else:
        print(f"Updating existing release id={release.get('id')}")
        _update_release(
            owner, repo, int(release["id"]), token, name=rel_name, body=rel_body
        )

    existing = {
        str(a.get("name")): int(a["id"])
        for a in (release.get("assets") or [])
        if isinstance(a, dict) and a.get("name") and a.get("id") is not None
    }
    upload_url = str(release.get("upload_url") or "")
    if not upload_url:
        raise SystemExit("Release has no upload_url")

    files = _files_to_upload(folder)
    if not files:
        raise SystemExit(f"No files to upload in {folder}")

    for path in files:
        local_name = os.path.basename(path)
        asset_name = _github_asset_name(local_name)
        # Prefer deleting under both local and GitHub-sanitized names
        for key in dict.fromkeys([asset_name, local_name]):
            if key in existing:
                print(f"  replace {key}")
                _delete_asset(owner, repo, existing[key], token)
                existing.pop(key, None)
                break
        else:
            print(f"  upload  {asset_name}")
        if local_name == "manifest.json":
            data = _manifest_for_github(folder)
            base = upload_url.split("{", 1)[0]
            url = base + "?" + urllib.parse.urlencode({"name": "manifest.json"})
            _request(
                "POST",
                url,
                token,
                data=data,
                content_type="application/json",
                accept="application/vnd.github+json",
            )
        else:
            _upload_asset(upload_url, path, token, asset_name=asset_name)

    print()
    print("Done. Lecturer live auto-update channel updated (users need EA_GITHUB_TOKEN).")


def main():
    argv = sys.argv[1:]
    notes = ""
    if "--notes" in argv:
        i = argv.index("--notes")
        raw = " ".join(argv[i + 1 :]) if i + 1 < len(argv) else ""
        if raw and os.path.isfile(raw):
            notes = open(raw, encoding="utf-8").read()
        else:
            notes = raw
    publish(notes=notes)


if __name__ == "__main__":
    main()
