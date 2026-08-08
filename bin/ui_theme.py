"""Light / dark UI palettes, persistence, and UTM header logo composition."""
from __future__ import annotations

import os

UTM_SAND = "#F0E6D3"
UTM_MAROON = "#880033"
UTM_MAROON_DARK = "#6B0028"
UTM_GOLD = "#D4AF37"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "window": "#2A1018",
        "panel": "#3A1822",
        "card": "#451F28",
        "text": "#F5EDE6",
        "text_dim": "#C9A89E",
        "input_bg": "#351820",
        "input_fg": "#F5EDE6",
        "accent": UTM_GOLD,
        "accent2": "#8BC34A",
        "error": "#EF9A9A",
        "btn": UTM_MAROON,
        "btn_hov": "#A30040",
        "btn_sec": "#5C3040",
        "btn_sec_hov": "#704050",
        "sep": "#5C3040",
        "entry_hl": "#5C3040",
        "tree_sel": UTM_MAROON,
        "hdr": UTM_MAROON,
        "hdr_title": UTM_SAND,
        "hdr_sub": UTM_GOLD,
        "hdr_foot": UTM_SAND,
        "logo_bg": UTM_SAND,
        "chrome_btn": UTM_MAROON_DARK,
        "output_bg": "#451F28",
        "output_fg": UTM_SAND,
    },
    "light": {
        "window": "#EDE4D3",
        "panel": "#FAF6EF",
        "card": "#FFFFFF",
        "text": UTM_MAROON,
        "text_dim": "#7A3A4A",
        "input_bg": "#FFFFFF",
        "input_fg": UTM_MAROON,
        "accent": UTM_MAROON,
        "accent2": UTM_MAROON,
        "error": "#C62828",
        "btn": UTM_MAROON,
        "btn_hov": "#A30040",
        "btn_sec": "#C9B89A",
        "btn_sec_hov": "#B8A688",
        "sep": "#D4C4A8",
        "entry_hl": UTM_MAROON,
        "tree_sel": UTM_MAROON,
        "hdr": UTM_SAND,
        "hdr_title": UTM_MAROON,
        "hdr_sub": UTM_MAROON,
        "hdr_foot": "#5C4033",
        "logo_bg": UTM_SAND,
        "chrome_btn": "#D4C4A8",
        "output_bg": "#FFFDF8",
        "output_fg": UTM_MAROON,
    },
}

DEFAULT_MODE = "dark"


def ensure_win_app_user_model_id() -> None:
    """Use the built .exe identity on Windows so the taskbar shows our icon, not Python's."""
    try:
        import win_boot

        win_boot.apply()
    except Exception:
        pass


def _win_icon_path(icon_path: str) -> tuple[str, str | None]:
    """Return a filesystem .ico path (copy frozen bundle icons to a temp file on Windows)."""
    import shutil
    import sys
    import tempfile

    from app_paths import is_frozen

    if not icon_path or not os.path.isfile(icon_path):
        return icon_path, None
    if sys.platform != "win32" or not is_frozen():
        return icon_path, None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".ico")
        os.close(fd)
        shutil.copy2(icon_path, tmp)
        return tmp, tmp
    except Exception:
        return icon_path, None


def _apply_win32_hwnd_icon(tk_window, ico_path: str) -> None:
    """Set small/large HWND icons — required for Windows taskbar with Tkinter."""
    import sys

    if sys.platform != "win32" or not ico_path or not os.path.isfile(ico_path):
        return
    try:
        import ctypes

        hwnd = ctypes.windll.user32.GetParent(tk_window.winfo_id())
        if not hwnd:
            hwnd = tk_window.winfo_id()
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1
        for size, slot in ((16, ICON_SMALL), (32, ICON_SMALL), (48, ICON_BIG), (256, ICON_BIG)):
            hicon = ctypes.windll.user32.LoadImageW(
                0, ico_path, IMAGE_ICON, size, size, LR_LOADFROMFILE,
            )
            if hicon:
                ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, slot, hicon)
    except Exception:
        pass


def _best_ico_frame(img):
    from PIL import Image

    img.load()
    if getattr(img, "n_frames", 1) <= 1:
        return img.convert("RGBA")
    best, best_sz = None, 0
    for i in range(img.n_frames):
        img.seek(i)
        frame = img.copy()
        if frame.width >= 32 and frame.width > best_sz:
            best, best_sz = frame, frame.width
    return (best or img.copy()).convert("RGBA")


def set_tk_window_icon(tk_window) -> None:
    """Apply branded .ico to title bar and Windows taskbar (dev + frozen exe)."""
    from app_paths import resource

    ensure_win_app_user_model_id()

    icon_path = resource("icon.ico")
    win_icon = resource("icon_win.png")
    ico_path, ico_tmp = _win_icon_path(icon_path)
    tk_window._icon_tmp = ico_tmp

    if os.path.isfile(ico_path):
        try:
            tk_window.iconbitmap(default=ico_path)
        except Exception:
            try:
                tk_window.iconbitmap(ico_path)
            except Exception:
                pass

    try:
        from PIL import Image, ImageTk

        img = None
        if os.path.isfile(win_icon):
            img = Image.open(win_icon)
        elif os.path.isfile(icon_path):
            img = _best_ico_frame(Image.open(icon_path))
        if img is not None:
            img = img.convert("RGBA")
            resample = getattr(Image, "Resampling", Image).LANCZOS
            img.thumbnail((64, 64), resample)
            tk_window._win_icon_img = ImageTk.PhotoImage(img)
            tk_window.iconphoto(True, tk_window._win_icon_img)
    except Exception:
        pass

    def _finish():
        _apply_win32_hwnd_icon(tk_window, ico_path)

    try:
        tk_window.after_idle(_finish)
        tk_window.after(250, _finish)
    except Exception:
        _finish()


# Legacy dev constants still baked into widgets at first paint
_LEGACY = {
    "window": {"#1B2838", "#E8EDF2", "#EDE4D3"},
    "panel": {"#243447", "#F5F8FB", "#FAF6EF", "#3A1822"},
    "card": {"#1E3250", "#FFFFFF", "#451F28", "#FFFDF8"},
    "input_bg": {"#152238", "#351820", "#FFFFFF"},
    "input_fg": {"#E3F2FD", "#F5EDE6", "#1A2B3C", UTM_MAROON.upper()},
    "text": {"#E8F0FE", "#1A2B3C", "#F5EDE6", UTM_MAROON.upper()},
    "text_dim": {"#90A4AE", "#5A6B7C", "#C9A89E", "#7A3A4A"},
    "accent": {"#4FC3F7", "#1565C0", "#D4AF37", "#C9A227"},
    "accent2": {"#66BB6A", "#2E7D32", "#8BC34A"},
    "btn": {"#1565C0", "#1976D2", "#1F4E79", "#2E75B6", "#375623", "#880033"},
    "btn_sec": {"#37474F", "#4A5568", "#90A4AE", "#C9B89A", "#5C3040"},
    "hdr": {"#1F4E79", "#880033", "#F0E6D3", "#6B0028", "#D4C4A8"},
    "output_bg": {"#451F28", "#FFFDF8", "#1E3250"},
    "output_fg": {"#F5EDE6", "#880033", "#66BB6A"},
}


def _bucket(color: str, key: str) -> bool:
    c = (color or "").upper()
    if c in {v.upper() for v in THEMES["dark"].values()}:
        pass
    vals = {THEMES["dark"][key].upper(), THEMES["light"][key].upper()} | _LEGACY.get(key, set())
    return c in {v.upper() for v in vals}


def _collect_skip(root, skip: set) -> None:
    skip.add(id(root))
    for child in root.winfo_children():
        _collect_skip(child, skip)


def apply_theme_widgets(root, theme: dict, skip: frozenset | None = None) -> None:
    """Apply maroon/sand theme by widget role (fixes Entry contrast on mode toggle)."""
    import tkinter as tk

    skip = skip or frozenset()
    t = theme

    def _visit(widget):
        if id(widget) in skip:
            return
        cls = widget.winfo_class()
        try:
            if cls == "Entry":
                widget.config(
                    bg=t["input_bg"],
                    fg=t["input_fg"],
                    insertbackground=t["accent"],
                    highlightbackground=t["entry_hl"],
                    highlightcolor=t["accent"],
                )
            elif cls == "Text":
                widget.config(
                    bg=t["panel"],
                    fg=t["text"],
                    insertbackground=t["accent"],
                )
            elif cls == "Radiobutton":
                widget.config(
                    bg=t["panel"],
                    fg=t["text_dim"],
                    selectcolor=t["input_bg"],
                    activebackground=t["panel"],
                    activeforeground=t["accent"],
                )
            elif cls == "Frame":
                bg = widget.cget("bg")
                if _bucket(bg, "window"):
                    widget.config(bg=t["window"])
                elif _bucket(bg, "panel"):
                    widget.config(bg=t["panel"])
                elif _bucket(bg, "card") or _bucket(bg, "output_bg"):
                    widget.config(bg=t.get("output_bg", t["card"])
                                if _bucket(bg, "output_bg") else t["card"])
            elif cls == "Label":
                bg = widget.cget("bg")
                fg = widget.cget("fg")
                if _bucket(bg, "hdr"):
                    pass
                elif _bucket(bg, "output_bg") or (
                    _bucket(bg, "card") and _bucket(fg, "output_fg")
                ):
                    out_bg = t.get("output_bg", t["card"])
                    out_fg = t.get("output_fg", t["accent2"])
                    dim = _bucket(fg, "text_dim")
                    widget.config(
                        bg=out_bg,
                        fg=t["text_dim"] if dim else out_fg,
                    )
                elif _bucket(bg, "panel") or _bucket(bg, "window"):
                    nfg = t["text_dim"] if _bucket(fg, "text_dim") else t["text"]
                    if _bucket(fg, "accent") or _bucket(fg, "accent2"):
                        nfg = t["accent"]
                    widget.config(bg=t["panel"], fg=nfg)
                elif _bucket(bg, "card"):
                    nfg = t["text_dim"] if _bucket(fg, "text_dim") else t["text"]
                    widget.config(bg=t["card"], fg=nfg)
            elif cls == "Button":
                bg = widget.cget("bg")
                if _bucket(bg, "btn"):
                    widget.config(bg=t["btn"], activebackground=t["btn_hov"])
                elif _bucket(bg, "btn_sec"):
                    widget.config(bg=t["btn_sec"], activebackground=t["btn_sec_hov"])
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            _visit(child)

    _visit(root)


def _pref_path() -> str:
    try:
        from app_paths import exe_dir
        return os.path.join(exe_dir(), "ea_theme.txt")
    except ImportError:
        return os.path.join(os.path.dirname(__file__), "ea_theme.txt")


def load_theme_mode() -> str:
    path = _pref_path()
    try:
        if os.path.isfile(path):
            mode = open(path, encoding="utf-8").read().strip().lower()
            if mode in THEMES:
                return mode
    except OSError:
        pass
    return DEFAULT_MODE


def save_theme_mode(mode: str) -> None:
    if mode not in THEMES:
        mode = DEFAULT_MODE
    try:
        with open(_pref_path(), "w", encoding="utf-8") as f:
            f.write(mode)
    except OSError:
        pass


def palette_map(from_theme: dict[str, str], to_theme: dict[str, str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for key in from_theme:
        if key in to_theme:
            old = from_theme[key].upper()
            new = to_theme[key]
            mapping[old] = new
    # Legacy module-level dark constants still present in widgets
    legacy = {
        "#1B2838": to_theme["window"],
        "#243447": to_theme["panel"],
        "#1E3250": to_theme["card"],
        "#E8F0FE": to_theme["text"],
        "#90A4AE": to_theme["text_dim"],
        "#152238": to_theme["input_bg"],
        "#E3F2FD": to_theme["input_fg"],
        "#4FC3F7": to_theme["accent"],
        "#66BB6A": to_theme["accent2"],
        "#EF9A9A": to_theme["error"],
        "#1565C0": to_theme["btn"],
        "#1976D2": to_theme["btn_hov"],
        "#FFFDF8": to_theme.get("output_bg", to_theme["card"]),
        "#2E75B6": to_theme["btn"],
        "#375623": to_theme["btn"],
        "#1A2B3C": to_theme["text"],
        "#FFFFFF": to_theme["input_bg"],
        "#F5F8FB": to_theme["panel"],
        "#E8EDF2": to_theme["window"],
        "#CFD8DC": to_theme["sep"],
        "#37474F": to_theme["btn_sec"],
        "#4A5568": to_theme["btn_sec_hov"],
        "#1F4E79": to_theme["hdr"],
        "#880033": to_theme["hdr"],
        "#6B0028": to_theme["chrome_btn"],
        "#BDD7EE": to_theme["hdr_foot"],
        "#C9A227": to_theme["hdr_sub"],
        "#F0E6D3": to_theme["logo_bg"],
    }
    for k, v in legacy.items():
        mapping[k.upper()] = v
    return mapping


def _transparent_black(img, threshold: int = 40):
    from PIL import Image
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r <= threshold and g <= threshold and b <= threshold:
                px[x, y] = (r, g, b, 0)
    return img


def _utm_full_path() -> str | None:
    candidates = []
    try:
        from app_paths import bin_dir, resource, is_frozen
        if is_frozen():
            candidates.append(resource("utm_full.png"))
        candidates.append(os.path.join(bin_dir(), "branding", "assets", "utm_full.png"))
        candidates.append(os.path.join(os.path.dirname(bin_dir()), "bin", "branding", "assets", "utm_full.png"))
    except ImportError:
        base = os.path.dirname(os.path.abspath(__file__))
        candidates.append(os.path.join(base, "branding", "assets", "utm_full.png"))
    for p in candidates:
        if p and os.path.isfile(p):
            return p
    return None


def _resample():
    from PIL import Image
    return getattr(Image, "Resampling", Image).LANCZOS


def compose_utm_header_logo(bg_hex: str | None = None, pad: int = 3, max_logo_h: int = 52):
    """UTM signature cropped tightly on a small sand patch (fits 64px header)."""
    from PIL import Image

    src = _utm_full_path()
    if not src:
        return None
    sand = bg_hex or UTM_SAND
    full = _transparent_black(Image.open(src))
    scale = max_logo_h / full.height
    new_w = max(1, int(full.width * scale))
    full = full.resize((new_w, max_logo_h), _resample())
    w, h = new_w + 2 * pad, max_logo_h + 2 * pad
    canvas = Image.new("RGB", (w, h), sand)
    canvas.paste(full, (pad, pad), full)
    return canvas


def header_logo_image(bg_hex: str, fallback_path: str | None, max_w: int = 260, max_h: int = 56):
    """Return PIL Image for header — tight sand patch around UTM logo."""
    from PIL import Image
    composed = compose_utm_header_logo(UTM_SAND)
    if composed is not None:
        img = composed
    elif fallback_path and os.path.isfile(fallback_path):
        img = Image.open(fallback_path).convert("RGBA")
        sand = Image.new("RGB", img.size, UTM_SAND)
        if img.mode == "RGBA":
            sand.paste(img, mask=img.split()[3])
        else:
            sand.paste(img)
        img = sand
    else:
        return None
    ratio = min(max_w / img.width, max_h / img.height, 1.0)
    if ratio < 1.0:
        img = img.resize((max(1, int(img.width * ratio)), max(1, int(img.height * ratio))), _resample())
    return img.convert("RGB")


EA_NAVY = "#1F4E79"
EA_GOLD = "#C9A227"
EA_LIGHT = "#BDD7EE"


def ea_header_logo_image(
    logo_path: str | None = None,
    icon_path: str | None = None,
    max_h: int = 52,
):
    """EA header — gold-framed emblem (visible on navy) plus optional banner strip."""
    from PIL import Image, ImageDraw

    emblem = None
    if icon_path and os.path.isfile(icon_path):
        raw = _best_ico_frame(Image.open(icon_path))
        sz = max_h
        emblem = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        draw = ImageDraw.Draw(emblem)
        pad = max(2, sz // 16)
        draw.rounded_rectangle(
            [pad, pad, sz - pad - 1, sz - pad - 1],
            radius=max(4, sz // 8),
            fill=EA_GOLD,
            outline=EA_LIGHT,
            width=max(1, sz // 32),
        )
        inner = sz - 2 * pad - max(2, sz // 32)
        em = raw.copy()
        em.thumbnail((inner, inner), _resample())
        emblem.paste(em, ((sz - em.width) // 2, (sz - em.height) // 2), em)

    banner = None
    if logo_path and os.path.isfile(logo_path):
        img = Image.open(logo_path).convert("RGBA")
        target_h = max_h - 6
        scale = target_h / max(img.height, 1)
        new_w = max(1, int(img.width * scale))
        img = img.resize((new_w, target_h), _resample())
        strip_h = target_h + 8
        strip = Image.new("RGB", (img.width + 12, strip_h), EA_LIGHT)
        draw = ImageDraw.Draw(strip)
        draw.rectangle([0, strip_h - 3, strip.width, strip_h], fill=EA_GOLD)
        strip.paste(img, (6, 4), img)
        banner = strip

    if emblem is not None and banner is not None:
        gap = 8
        out = Image.new("RGB", (emblem.width + gap + banner.width, max(emblem.height, banner.height)), EA_NAVY)
        out.paste(emblem.convert("RGB"), (0, (out.height - emblem.height) // 2), emblem)
        out.paste(banner, (emblem.width + gap, (out.height - banner.height) // 2))
        return out
    if emblem is not None:
        return emblem.convert("RGB")
    if banner is not None:
        return banner
    return None
