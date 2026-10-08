"""
EA auto-updater — office NAS (SMB) first, then private GitHub Releases (HTTPS).

Place beside the .exe:
  ea_update.json     — NAS path and/or GitHub release settings
  version.txt        — installed version

Startup order:
  1. Probe NAS sync_folder with lan_timeout (default 30s) — skip if offline/slow
  2. Fall back to GitHub Releases (needs EA_GITHUB_TOKEN for private repos)

Off-site: set EA_GITHUB_TOKEN (read-only PAT) or https_auth.token_env in ea_update.json.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import base64
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote

CONFIG_NAME = "ea_update.json"
VERSION_NAME = "version.txt"
DEFAULT_MANIFEST = "manifest.json"

# Defaults: keep launch snappy — don't hang on unreachable UNC shares.
DEFAULT_LAN_TIMEOUT = 30
DEFAULT_CHECK_TIMEOUT = 30
DEFAULT_DOWNLOAD_TIMEOUT = 300


def _app_dir():
    from app_paths import exe_dir
    return exe_dir()


def _is_frozen():
    from app_paths import is_frozen
    return is_frozen()


def config_path():
    return os.path.join(_app_dir(), CONFIG_NAME)


def load_config() -> dict[str, Any]:
    path = config_path()
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    return {}


def read_local_version(fallback: str = "0.0.0") -> str:
    path = os.path.join(_app_dir(), VERSION_NAME)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
            if v:
                return v
    return fallback


def write_local_version(version: str):
    with open(os.path.join(_app_dir(), VERSION_NAME), "w", encoding="utf-8") as f:
        f.write(version.strip() + "\n")


def _version_key(version: str) -> tuple:
    parts: list[Any] = []
    for piece in re.split(r"[.\-]", str(version).strip()):
        if piece.isdigit():
            parts.append(int(piece))
        elif piece:
            parts.append(piece)
    return tuple(parts)


def is_newer(remote: str, local: str) -> bool:
    return _version_key(remote) > _version_key(local)


def _expand(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path.strip()))


def _load_json_file(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Manifest must be a JSON object: {path}")
    return data


def _lan_timeout_sec(config: dict[str, Any]) -> float:
    """Max seconds to wait for office NAS / UNC folder before GitHub fallback."""
    try:
        return max(1.0, float(config.get("lan_timeout", DEFAULT_LAN_TIMEOUT)))
    except (TypeError, ValueError):
        return float(DEFAULT_LAN_TIMEOUT)


def _check_timeout_sec(config: dict[str, Any]) -> int:
    """HTTPS / GitHub API timeout for manifest checks (not file downloads)."""
    try:
        return max(1, int(config.get("timeout", DEFAULT_CHECK_TIMEOUT)))
    except (TypeError, ValueError):
        return DEFAULT_CHECK_TIMEOUT


def _download_timeout_sec(config: dict[str, Any]) -> int:
    """Timeout for downloading update payloads (EXE can be large)."""
    try:
        if "download_timeout" in config:
            return max(30, int(config.get("download_timeout")))
    except (TypeError, ValueError):
        pass
    return DEFAULT_DOWNLOAD_TIMEOUT


def _call_with_timeout(fn, timeout_sec: float, default=None):
    """
    Run fn() in a daemon thread; return default if it does not finish in time.
    Used so unreachable UNC paths cannot block app startup for minutes.
    """
    box: list[Any] = [default]
    err: list[BaseException] = []

    def _worker():
        try:
            box[0] = fn()
        except BaseException as ex:  # noqa: BLE001 — surface to caller path as default
            err.append(ex)

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    t.join(timeout_sec)
    if t.is_alive():
        return default
    if err:
        return default
    return box[0]


def _isdir_timed(path: str, timeout_sec: float) -> bool:
    if not path:
        return False
    return bool(_call_with_timeout(lambda: os.path.isdir(path), timeout_sec, False))


def _isfile_timed(path: str, timeout_sec: float) -> bool:
    if not path:
        return False
    return bool(_call_with_timeout(lambda: os.path.isfile(path), timeout_sec, False))


def _https_token(config: dict[str, Any]) -> str:
    """Bearer / GitHub PAT from https_auth or github block."""
    for block_key in ("https_auth", "github"):
        auth = config.get(block_key) or {}
        if not isinstance(auth, dict):
            continue
        token = str(auth.get("token", "") or "").strip()
        if token:
            return token
        env_key = str(auth.get("token_env", "") or "").strip()
        if env_key:
            token = (os.environ.get(env_key, "") or "").strip()
            if token:
                return token
    return ""


def _https_credentials(config: dict[str, Any]) -> tuple[str, str]:
    auth = config.get("https_auth") or {}
    user = str(auth.get("username", "") or "").strip()
    password = str(auth.get("password", "") or "")
    if not password:
        env_key = str(auth.get("password_env", "") or "").strip()
        if env_key:
            password = os.environ.get(env_key, "")
    return user, password


def _build_request(url: str, config: dict[str, Any], *, accept: str | None = None) -> urllib.request.Request:
    headers = {"User-Agent": "EA-Updater/1.0"}
    if accept:
        headers["Accept"] = accept
    req = urllib.request.Request(url, headers=headers)
    token = _https_token(config)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
        return req
    user, password = _https_credentials(config)
    if user and password:
        basic = base64.b64encode(f"{user}:{password}".encode()).decode("ascii")
        req.add_header("Authorization", f"Basic {basic}")
    return req


def _urlopen(url: str, config: dict[str, Any], timeout: int, *, accept: str | None = None):
    return urllib.request.urlopen(
        _build_request(url, config, accept=accept), timeout=timeout
    )


def _fetch_json_url(url: str, config: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    with _urlopen(url, config, timeout=timeout) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Manifest URL did not return a JSON object: {url}")
    return data


def _github_block(config: dict[str, Any]) -> dict[str, Any] | None:
    gh = config.get("github")
    if not isinstance(gh, dict):
        return None
    owner = str(gh.get("owner", "") or "").strip()
    repo = str(gh.get("repo", "") or "").strip()
    tag = str(gh.get("tag", "") or "").strip()
    if owner and repo and tag:
        return gh
    return None


def _github_api_json(url: str, config: dict[str, Any], timeout: int) -> Any:
    with _urlopen(
        url, config, timeout, accept="application/vnd.github+json"
    ) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _github_release_assets(
    config: dict[str, Any], timeout: int
) -> tuple[dict[str, Any], dict[str, int], str] | None:
    """Return (release_json, name->asset_id, label) or None."""
    gh = _github_block(config)
    if not gh:
        return None
    if not _https_token(config):
        return None
    owner = str(gh["owner"]).strip()
    repo = str(gh["repo"]).strip()
    tag = str(gh["tag"]).strip()
    api = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{quote(tag, safe='')}"
    try:
        release = _github_api_json(api, config, timeout)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError, KeyError):
        return None
    if not isinstance(release, dict):
        return None
    assets: dict[str, int] = {}
    for item in release.get("assets") or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "")
        aid = item.get("id")
        if name and isinstance(aid, int):
            assets[name] = aid
    label = f"GitHub Releases ({owner}/{repo} @ {tag})"
    return release, assets, label


def _lookup_asset_id(assets: dict[str, int], filename: str) -> int | None:
    """Match release assets; GitHub may rewrite spaces to dots."""
    if filename in assets:
        return assets[filename]
    for alt in (
        filename.replace(" ", "."),
        filename.replace(" ", "-"),
        filename.replace(" ", "_"),
    ):
        if alt in assets:
            return assets[alt]
    return None


def _github_download_asset(
    owner: str,
    repo: str,
    asset_id: int,
    dest: str,
    config: dict[str, Any],
    timeout: int,
) -> None:
    # Private assets: API + Accept octet-stream (avoids auth drop on CDN redirect).
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
    with _urlopen(
        url, config, timeout, accept="application/octet-stream"
    ) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _sync_folder_candidates(config: dict[str, Any]) -> list[tuple[str, str]]:
    """Return [(folder_path, label), ...] in priority order."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    def _add(path: str, label: str):
        p = _expand(path)
        if not p:
            return
        key = os.path.normcase(os.path.normpath(p))
        if key in seen:
            return
        seen.add(key)
        out.append((p, label))

    folders = config.get("sync_folders")
    if isinstance(folders, list):
        for item in folders:
            if isinstance(item, str):
                _add(item, "network folder")
            elif isinstance(item, dict):
                _add(item.get("path", ""), item.get("label", "network folder"))

    if isinstance(folders, dict):
        for label, path in folders.items():
            _add(path, str(label))

    _add(config.get("sync_folder", ""), "NAS update folder")
    _add(config.get("sync_folder_lan", ""), "office LAN")

    return out


def _nas_download_folder(config: dict[str, Any]) -> str:
    for key in ("sync_folder", "sync_folder_lan"):
        p = _expand(str(config.get(key, "") or ""))
        if p:
            return p
    return ""


def _remote_hint(config: dict[str, Any], source: str = "") -> str:
    nas = _nas_download_folder(config)
    if nas:
        return nas
    gh = _github_block(config)
    if gh:
        return (
            f"GitHub release {gh.get('owner')}/{gh.get('repo')} "
            f"tag {gh.get('tag')}"
        )
    base = (config.get("https_base_url") or "").strip() or source
    return str(base or "").strip()


def _try_manifest_in_folder(
    folder: str, manifest_name: str, *, lan_timeout: float
) -> dict[str, Any] | None:
    if not folder:
        return None
    if not _isdir_timed(folder, lan_timeout):
        return None
    man_path = os.path.join(folder, manifest_name)
    # Remaining budget for the file read after the isdir probe.
    if not _isfile_timed(man_path, max(1.0, min(5.0, lan_timeout))):
        return None

    def _load():
        return _load_json_file(man_path)

    try:
        data = _call_with_timeout(_load, max(1.0, min(10.0, lan_timeout)), None)
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def load_remote_manifest(config: dict[str, Any] | None = None) -> tuple[dict[str, Any] | None, str | None, str]:
    """Return (manifest, source, source_label). source is folder path or 'github:' marker.

    NAS/UNC is probed with a single lan_timeout budget (default 30s). If the share
    is unreachable or too slow, skip immediately to GitHub / HTTPS — do not block launch.
    """
    import time

    config = config or load_config()
    manifest_name = config.get("manifest_file", DEFAULT_MANIFEST)
    lan_budget = _lan_timeout_sec(config)
    timeout = _check_timeout_sec(config)

    # 1) Office LAN / NAS first (one shared time budget)
    deadline = time.monotonic() + lan_budget
    for folder, label in _sync_folder_candidates(config):
        remaining = deadline - time.monotonic()
        if remaining <= 0.05:
            break
        manifest = _try_manifest_in_folder(
            folder, manifest_name, lan_timeout=remaining
        )
        if manifest:
            return manifest, folder, label

    # 2) Private GitHub Releases (API + token)
    gh_info = _github_release_assets(config, timeout)
    if gh_info:
        _release, assets, label = gh_info
        asset_id = _lookup_asset_id(assets, manifest_name)
        if asset_id:
            gh = _github_block(config)
            assert gh is not None
            fd, tmp = tempfile.mkstemp(suffix=".json")
            os.close(fd)
            try:
                _github_download_asset(
                    str(gh["owner"]).strip(),
                    str(gh["repo"]).strip(),
                    asset_id,
                    tmp,
                    config,
                    timeout,
                )
                manifest = _load_json_file(tmp)
                return manifest, "github:", label
            except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError):
                pass
            finally:
                try:
                    os.remove(tmp)
                except OSError:
                    pass

    # 3) Direct HTTPS manifest_url (public or token via https_auth)
    url = (config.get("manifest_url") or config.get("webdav_manifest_url") or "").strip()
    if url:
        try:
            manifest = _fetch_json_url(url, config, timeout=timeout)
            base = config.get("https_base_url", "").strip()
            if not base:
                base = url.rsplit("/", 1)[0] if "/" in url else url
            label = "HTTPS / WebDAV (remote)"
            if not _https_token(config) and not _https_credentials(config)[0]:
                label += " — set https_auth / github token_env in ea_update.json"
            return manifest, base, label
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            pass

    return None, None, ""


def check_for_update(local_version: str, config: dict[str, Any] | None = None) -> dict[str, Any] | None:
    config = config or load_config()
    if not config.get("check_on_startup", True):
        return None

    manifest, source, source_label = load_remote_manifest(config)
    if not manifest or not source:
        return None

    remote_version = str(manifest.get("version", "")).strip()
    if not remote_version or not is_newer(remote_version, local_version):
        return None

    return {
        "version": remote_version,
        "local_version": local_version,
        "manifest": manifest,
        "source": source,
        "source_label": source_label,
        "config": config,
    }


def _download_file(url: str, dest: str, config: dict[str, Any], timeout: int = 120):
    with _urlopen(url, config, timeout=timeout) as resp, open(dest, "wb") as out:
        shutil.copyfileobj(resp, out)


def _file_download_url(base: str, filename: str) -> str:
    base = base.rstrip("/")
    return f"{base}/{quote(filename)}"


def _resolve_update_file(manifest: dict[str, Any], source: str, filename: str,
                         config: dict[str, Any]) -> str:
    if source and not source.startswith("github:") and _isdir_timed(
        source, _lan_timeout_sec(config)
    ):
        path = os.path.join(source, filename)
        if _isfile_timed(path, _lan_timeout_sec(config)):
            return path
        raise FileNotFoundError(f"Update file not found in sync folder:\n{path}")

    timeout = _download_timeout_sec(config)
    fd, tmp = tempfile.mkstemp(suffix=os.path.splitext(filename)[1] or ".bin")
    os.close(fd)

    if source == "github:" or (isinstance(source, str) and source.startswith("github:")):
        gh = _github_block(config)
        if not gh:
            raise FileNotFoundError("GitHub update source configured incorrectly.")
        info = _github_release_assets(config, _check_timeout_sec(config))
        if not info:
            raise FileNotFoundError(f"Could not list GitHub release assets for {filename}")
        _release, assets, _label = info
        asset_id = _lookup_asset_id(assets, filename)
        if not asset_id:
            raise FileNotFoundError(f"Asset not found on GitHub release: {filename}")
        _github_download_asset(
            str(gh["owner"]).strip(),
            str(gh["repo"]).strip(),
            asset_id,
            tmp,
            config,
            timeout,
        )
        return tmp

    base = (source or "").rstrip("/")
    url = _file_download_url(base, filename)
    _download_file(url, tmp, config, timeout=timeout)
    return tmp


def _write_replace_bat(staging: str, target: str, version: str, *, restart: bool = True):
    bat = os.path.join(tempfile.gettempdir(), "ea_apply_update.bat")
    ver_file = os.path.join(_app_dir(), VERSION_NAME)
    bat_lines = [
        "@echo off",
        "ping 127.0.0.1 -n 3 >nul",
        f'copy /y "{staging}" "{target}"',
        f'echo {version}> "{ver_file}"',
    ]
    if restart:
        bat_lines.append(f'start "" "{target}"')
    bat_lines.append('del "%~f0"')
    with open(bat, "w", encoding="utf-8", newline="\r\n") as f:
        f.write("\r\n".join(bat_lines) + "\r\n")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    subprocess.Popen(["cmd", "/c", bat], creationflags=flags)


def stage_update(info: dict[str, Any]) -> str:
    """Prefetch update payload to a temp staging path. Stores path on info['_staging_path']."""
    existing = str(info.get("_staging_path") or "")
    if existing and os.path.isfile(existing):
        return existing

    if not _is_frozen():
        # Dev/script mode: no EXE to stage; script apply copies files on demand.
        info["_staging_path"] = ""
        return ""

    manifest = info["manifest"]
    source = info["source"]
    config = info["config"]
    exe_name = manifest.get("exe_name") or os.path.basename(sys.executable)

    staging_src = _resolve_update_file(manifest, source, exe_name, config)
    # Avoid spaces in staging filename (safer for bat); keep extension.
    safe = re.sub(r"[^\w.\-]+", "_", exe_name)
    staging = os.path.join(tempfile.gettempdir(), f"ea_update_{safe}")
    shutil.copy2(staging_src, staging)

    if staging_src != staging and str(staging_src).startswith(tempfile.gettempdir()):
        try:
            os.remove(staging_src)
        except OSError:
            pass

    info["_staging_path"] = staging
    return staging


def apply_exe_update(info: dict[str, Any], *, restart: bool = True) -> None:
    staging = str(info.get("_staging_path") or "")
    if not staging or not os.path.isfile(staging):
        staging = stage_update(info)
    if not staging or not os.path.isfile(staging):
        raise FileNotFoundError("Staged update EXE not found.")

    _write_replace_bat(staging, sys.executable, info["version"], restart=restart)
    if restart:
        sys.exit(0)


def apply_script_update(info: dict[str, Any]) -> list[str]:
    """Copy listed files from sync folder or download from URL / GitHub."""
    manifest = info["manifest"]
    source = info["source"]
    config = info["config"]
    from_url = not (
        source
        and not str(source).startswith("github:")
        and _isdir_timed(str(source), _lan_timeout_sec(config))
    )

    updated: list[str] = []
    root = _app_dir()
    for entry in manifest.get("files", []):
        if isinstance(entry, str):
            name, dest = entry, "bin"
        else:
            name = entry.get("name", "")
            dest = entry.get("dest", "bin")
        if not name or name.lower().endswith(".exe"):
            continue
        if from_url:
            try:
                src = _resolve_update_file(manifest, source, name, config)
            except (urllib.error.URLError, OSError, FileNotFoundError):
                continue
        else:
            src = os.path.join(source, name)
            if not os.path.isfile(src):
                continue
        dst_dir = root if dest in (".", "") else os.path.join(root, dest)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, name)
        shutil.copy2(src, dst)
        updated.append(dst)
        if from_url and src.startswith(tempfile.gettempdir()):
            try:
                os.remove(src)
            except OSError:
                pass

    if updated:
        write_local_version(info["version"])
    return updated


def apply_update(info: dict[str, Any], *, restart: bool = True) -> None:
    if _is_frozen():
        apply_exe_update(info, restart=restart)
    else:
        updated = apply_script_update(info)
        if not updated:
            hint = _remote_hint(info.get("config") or {}, str(info.get("source") or ""))
            raise FileNotFoundError(
                "No updatable files found.\n"
                f"Download manually from:\n{hint}"
            )


def format_update_message(info: dict[str, Any]) -> str:
    manifest = info["manifest"]
    config = info.get("config") or {}
    lines = [
        f"A newer version is available: {info['version']}",
        f"Installed version: {info['local_version']}",
    ]
    label = info.get("source_label", "").strip()
    if label:
        lines.append(f"Source: {label}")
    download = _remote_hint(config, str(info.get("source", "") or ""))
    if download:
        lines.append("")
        lines.append("Update location (manual copy if needed):")
        lines.append(download)
    lines.append("")
    changelog = manifest.get("changelog", "").strip()
    if changelog:
        lines.append(changelog)
        lines.append("")
    lines.append("Install update now?")
    lines.append("(The app will restart after updating.)")
    return "\n".join(lines)


_PENDING_ATTR = "_ea_pending_update"
_BANNER_ATTR = "_ea_update_banner"
_QUIT_ARMED_ATTR = "_ea_update_quit_armed"
_PREV_CLOSE_ATTR = "_ea_prev_wm_delete"


def _banner_colors(parent) -> tuple[str, str, str]:
    """Return (bg, fg, accent) suited to parent theme."""
    bg = ""
    try:
        bg = str(parent.cget("bg") or "")
    except Exception:
        bg = ""
    dark = False
    if bg.startswith("#") and len(bg) >= 7:
        try:
            r, g, b = int(bg[1:3], 16), int(bg[3:5], 16), int(bg[5:7], 16)
            dark = (r + g + b) / 3 < 80
        except ValueError:
            dark = False
    if dark:
        return "#313244", "#cdd6f4", "#89b4fa"
    return "#1F4E79", "#FFFFFF", "#BDD7EE"


def dismiss_update_banner(parent) -> None:
    banner = getattr(parent, _BANNER_ATTR, None)
    if banner is not None:
        try:
            banner.destroy()
        except Exception:
            pass
    setattr(parent, _BANNER_ATTR, None)


def show_update_banner(parent, info: dict[str, Any]) -> None:
    """Non-modal top banner: Update / Later. Does not block the UI."""
    import tkinter as tk

    if getattr(parent, _BANNER_ATTR, None) is not None:
        return

    bg, fg, accent = _banner_colors(parent)
    banner = tk.Frame(parent, bg=bg, padx=10, pady=6)
    setattr(parent, _BANNER_ATTR, banner)

    ver = str(info.get("version", "") or "")
    local = str(info.get("local_version", "") or "")
    msg = f"Update available: v{ver}"
    if local:
        msg += f"  (you have v{local})"
    changelog = ""
    try:
        changelog = str((info.get("manifest") or {}).get("changelog", "") or "").strip()
    except Exception:
        changelog = ""
    if changelog:
        # One short line only
        one = changelog.splitlines()[0].strip()
        if len(one) > 80:
            one = one[:77] + "..."
        if one:
            msg += f"  —  {one}"

    tk.Label(banner, text=msg, bg=bg, fg=fg, anchor="w").pack(side="left", fill="x", expand=True)

    def _later():
        dismiss_update_banner(parent)

    def _update_now():
        dismiss_update_banner(parent)
        import tkinter.messagebox as mb
        try:
            apply_update(info, restart=True)
        except Exception as ex:
            mb.showerror("Update failed", str(ex), parent=parent)

    btn_bg = accent
    btn_fg = "#1a1a1a" if accent.lower() in ("#bdd7ee", "#89b4fa") else fg
    tk.Button(
        banner, text="Later", command=_later,
        bg=bg, fg=fg, relief="flat", padx=10, activebackground=bg, activeforeground=fg,
    ).pack(side="right", padx=(4, 0))
    tk.Button(
        banner, text="Update", command=_update_now,
        bg=btn_bg, fg=btn_fg, relief="flat", padx=12, activebackground=btn_bg,
    ).pack(side="right")

    slaves = []
    try:
        slaves = list(parent.pack_slaves())
    except Exception:
        slaves = []
    if slaves:
        banner.pack(side="top", fill="x", before=slaves[0])
    else:
        try:
            banner.place(x=0, y=0, relwidth=1)
            banner.lift()
        except Exception:
            banner.pack(side="top", fill="x")


def install_pending_on_quit(parent) -> bool:
    """If a staged update is pending, install without restarting. Returns True if started."""
    info = getattr(parent, _PENDING_ATTR, None)
    if not info:
        return False
    try:
        if _is_frozen():
            apply_exe_update(info, restart=False)
            # EXE is locked until this process exits; bat waits then copies.
            setattr(parent, _PENDING_ATTR, None)
            return True
        apply_script_update(info)
        setattr(parent, _PENDING_ATTR, None)
        return True
    except Exception:
        return False


def arm_update_on_quit(parent, info: dict[str, Any]) -> None:
    """Keep pending update; install runs on successful close (X or Exit)."""
    setattr(parent, _PENDING_ATTR, info)
    if getattr(parent, _QUIT_ARMED_ATTR, False):
        return
    setattr(parent, _QUIT_ARMED_ATTR, True)

    # Apps with _on_close should call install_pending_on_quit() after destroy
    # (so File→Exit and the window X both work). Only wrap destroy when absent.
    if hasattr(parent, "_on_close") and callable(getattr(parent, "_on_close")):
        parent.protocol("WM_DELETE_WINDOW", parent._on_close)
        return

    def _close_then_install(*_a, **_k):
        try:
            parent.destroy()
        except Exception:
            return
        if install_pending_on_quit(parent) and _is_frozen():
            os._exit(0)

    parent.protocol("WM_DELETE_WINDOW", _close_then_install)


def present_update(parent, info: dict[str, Any]) -> None:
    """Arm quit-install and show the non-modal banner (UI thread)."""
    arm_update_on_quit(parent, info)
    show_update_banner(parent, info)


def prompt_and_apply(parent, info: dict[str, Any], *, auto_apply: bool | None = None) -> bool:
    """Cursor-style: banner + apply-on-quit. auto_apply still installs immediately."""
    import tkinter.messagebox as mb

    if auto_apply is None:
        auto_apply = bool(info.get("config", {}).get("auto_apply", False))

    if auto_apply:
        try:
            if not info.get("_staging_path"):
                try:
                    stage_update(info)
                except Exception:
                    pass
            apply_update(info, restart=True)
            return True
        except Exception as ex:
            mb.showerror("Update failed", str(ex), parent=parent)
            return False

    present_update(parent, info)
    return True
