#!/usr/bin/env python3
"""Generate logo.png and icon.ico for lecturer (UTM) and student editions."""
from __future__ import annotations

import os
import sys
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

try:
    from PIL import Image, ImageDraw
except ImportError:
    subprocess = __import__("subprocess")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pillow", "-q"])
    from PIL import Image, ImageDraw

BIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BIN not in sys.path:
    sys.path.insert(0, BIN)
BRAND = os.path.join(BIN, "branding")
ASSETS = os.path.join(BRAND, "assets")

UTM_URLS = {
    "utm_emblem.png": "https://upload.wikimedia.org/wikipedia/commons/8/81/UTM-LOGO.png",
    "utm_full.png": "https://upload.wikimedia.org/wikipedia/commons/c/cb/UTM-LOGO-FULL.png",
}

UTM_SAND = "#F0E6D3"
UTM_MAROON = "#880033"
NAVY = "#1F4E79"
GOLD = "#C9A227"
UTM_GOLD = "#D4AF37"

STUDENT_STYLE = dict(bg="#1565C0", accent="#66BB6A", title="COORDINATE WIZARD",
                     sub="Student Edition", ico_letter="S")


def _ensure_utm_assets():
    os.makedirs(ASSETS, exist_ok=True)
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EA_ASCII_branding/1.0"
    for name, url in UTM_URLS.items():
        path = os.path.join(ASSETS, name)
        if os.path.isfile(path) and os.path.getsize(path) > 10_000:
            continue
        print(f"  downloading {name} …")
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        with urllib.request.urlopen(req) as resp:
            with open(path, "wb") as f:
                f.write(resp.read())


def _load_ico_frames(path: str) -> list[Image.Image]:
    """All bitmap frames from a .ico file."""
    import struct
    import io

    frames: list[Image.Image] = []
    with open(path, "rb") as f:
        data = f.read()
    if len(data) >= 6 and data[:4] == b"\x00\x00\x01\x00":
        _, _, count = struct.unpack("<HHH", data[:6])
        off = 6
        entries = []
        for _ in range(count):
            entries.append(struct.unpack("<BBBBHHII", data[off:off + 16]))
            off += 16
        for _, _, _, _, _, _, nbytes, offset in entries:
            chunk = data[offset:offset + nbytes]
            frames.append(Image.open(io.BytesIO(chunk)).convert("RGBA"))
        if frames:
            return frames

    img = Image.open(path)
    img.load()
    for i in range(getattr(img, "n_frames", 1)):
        try:
            img.seek(i)
        except EOFError:
            break
        frames.append(img.copy().convert("RGBA"))
    return frames or [img.convert("RGBA")]


def make_ea_icon_transparent(path: str | None = None, *, threshold: int = 40) -> str:
    """Save bin/icon.ico with transparent background (black field → alpha)."""
    path = path or os.path.join(BIN, "icon.ico")
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    frames = [_transparent_black(f, threshold) for f in _load_ico_frames(path)]
    _save_multi_ico(path, frames)
    print(f"  wrote {path} (transparent background, {len(frames)} sizes)")
    win = os.path.join(BIN, "icon_win.png")
    best = max(frames, key=lambda f: f.width * f.height)
    thumb = best.copy()
    thumb.thumbnail((64, 64), _resample())
    thumb.save(win, "PNG")
    print(f"  wrote {win}")
    return path


def _transparent_black(img: Image.Image, threshold: int = 40) -> Image.Image:
    img = img.convert("RGBA")
    px = img.load()
    w, h = img.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if r <= threshold and g <= threshold and b <= threshold:
                px[x, y] = (r, g, b, 0)
    return img


def _resample():
    return getattr(Image, "Resampling", Image).LANCZOS


def _rounded_rect_icon(emblem: Image.Image, sz: int, bg: str, outline: str) -> Image.Image:
    """Square icon — emblem fills most of the canvas for a larger title-bar look."""
    img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = max(1, sz // 24)
    radius = max(2, sz // 8)
    stroke = max(1, sz // 64)
    d.rounded_rectangle(
        [pad, pad, sz - pad - 1, sz - pad - 1],
        radius=radius, fill=bg, outline=outline, width=stroke,
    )
    inner = sz - 2 * pad - 2 * stroke - max(0, sz // 32)
    em = emblem.copy()
    em.thumbnail((inner, inner), _resample())
    x = (sz - em.width) // 2
    y = (sz - em.height) // 2
    img.paste(em, (x, y), em)
    return img


def _save_multi_ico(path: str, imgs: list[Image.Image]) -> None:
    imgs[0].save(
        path,
        format="ICO",
        sizes=[(im.width, im.height) for im in imgs],
        append_images=imgs[1:],
    )


def _lecturer_logo(path: str):
    """Header banner asset — tight sand patch around UTM signature."""
    from ui_theme import compose_utm_header_logo
    img = compose_utm_header_logo(UTM_SAND, pad=3, max_logo_h=52)
    if img is None:
        return
    img.save(path, "PNG")
    print(f"  wrote {path}")


def _lecturer_icon(path: str):
    """Window/exe icon: UTM emblem fills the frame (multi-size .ico + PNG for title bar)."""
    emblem_path = os.path.join(ASSETS, "utm_emblem.png")
    emblem = _transparent_black(Image.open(emblem_path))
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs = [_rounded_rect_icon(emblem, sz, UTM_MAROON, UTM_GOLD) for sz in sizes]
    _save_multi_ico(path, imgs)
    win_png = os.path.join(os.path.dirname(path), "icon_win.png")
    imgs[sizes.index(64)].save(win_png, "PNG")
    print(f"  wrote {path}")
    print(f"  wrote {win_png}")


def _student_logo(path: str, style: dict):
    w, h = 640, 128
    img = Image.new("RGB", (w, h), style["bg"])
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - 4, w, h], fill=style["accent"])
    d.text((24, 28), "EA", fill=style["accent"])
    d.text((80, 22), style["title"], fill="white")
    d.text((80, 68), style["sub"], fill="#BDD7EE")
    d.text((24, 68), "◆", fill=style["accent"])
    img.save(path, "PNG")
    print(f"  wrote {path}")


def _student_icon(path: str, style: dict):
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs = []
    for sz in sizes:
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pad = max(1, sz // 24)
        d.rounded_rectangle([pad, pad, sz - pad, sz - pad], radius=max(2, sz // 8),
                            fill=style["bg"], outline=style["accent"],
                            width=max(1, sz // 64))
        d.text((sz // 2, sz // 2), style["ico_letter"], fill=style["accent"], anchor="mm")
        imgs.append(img)
    _save_multi_ico(path, imgs)
    win_png = os.path.join(os.path.dirname(path), "icon_win.png")
    imgs[sizes.index(64)].save(win_png, "PNG")
    print(f"  wrote {path}")
    print(f"  wrote {win_png}")


EA_NAVY = "#1F4E79"
EA_GOLD = "#C9A227"
EA_LIGHT = "#BDD7EE"
EA_STYLE = dict(bg=EA_NAVY, accent=EA_GOLD, title="COORDINATE WIZARD",
                sub="Ezam & Associates", ico_letter="E")


def _ea_logo(path: str):
    w, h = 640, 128
    img = Image.new("RGB", (w, h), EA_NAVY)
    d = ImageDraw.Draw(img)
    d.rectangle([0, h - 4, w, h], fill=EA_GOLD)
    d.text((24, 22), "EA", fill=EA_GOLD)
    d.text((72, 18), EA_STYLE["title"], fill="white")
    d.text((72, 62), EA_STYLE["sub"], fill=EA_LIGHT)
    img.save(path, "PNG")
    print(f"  wrote {path}")


def _ea_icon(path: str):
    sizes = [256, 128, 64, 48, 32, 24, 16]
    imgs = []
    for sz in sizes:
        img = Image.new("RGBA", (sz, sz), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        pad = max(1, sz // 24)
        d.rounded_rectangle([pad, pad, sz - pad, sz - pad], radius=max(2, sz // 8),
                            fill=EA_NAVY, outline=EA_GOLD, width=max(1, sz // 64))
        d.text((sz // 2, sz // 2), "E", fill=EA_GOLD, anchor="mm")
        imgs.append(img)
    _save_multi_ico(path, imgs)
    win_png = os.path.join(os.path.dirname(path), "icon_win.png")
    imgs[sizes.index(64)].save(win_png, "PNG")
    print(f"  wrote {path}")
    print(f"  wrote {win_png}")


def _best_ico_frame(path: str) -> Image.Image:
    """Largest frame from a multi-resolution .ico (raw directory or PIL)."""
    import struct
    import io

    with open(path, "rb") as f:
        data = f.read()
    if len(data) >= 6 and data[:4] == b"\x00\x00\x01\x00":
        _, _, count = struct.unpack("<HHH", data[:6])
        off = 6
        best = None
        best_area = 0
        for _ in range(count):
            w, h, _, _, _, _, nbytes, offset = struct.unpack("<BBBBHHII", data[off:off + 16])
            off += 16
            wd, hd = (256 if w == 0 else w), (256 if h == 0 else h)
            area = wd * hd
            if area > best_area:
                chunk = data[offset:offset + nbytes]
                try:
                    frame = Image.open(io.BytesIO(chunk)).convert("RGBA")
                    best, best_area = frame, area
                except Exception:
                    pass
        if best is not None:
            return best

    img = Image.open(path)
    img.load()
    best, best_area = None, 0
    for i in range(getattr(img, "n_frames", 1)):
        try:
            img.seek(i)
        except EOFError:
            break
        frame = img.copy().convert("RGBA")
        area = frame.width * frame.height
        if area > best_area:
            best, best_area = frame, area
    return (best or img.copy()).convert("RGBA")


def _ea_emblem_for_exe_icon() -> Image.Image:
    """Full crosshair emblem from bin/icon.ico (never cropped from logo banner)."""
    icon = os.path.join(BIN, "icon.ico")
    if not os.path.isfile(icon):
        raise FileNotFoundError(icon)
    return _best_ico_frame(icon)


def _square_icon_from_emblem(
    emblem: Image.Image,
    sz: int,
    *,
    bg: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Fit the whole emblem inside a square canvas — scale down, never crop."""
    canvas = Image.new("RGBA", (sz, sz), bg)
    margin = max(1, sz // 64)
    inner = sz - 2 * margin
    em = emblem.copy()
    em.thumbnail((inner, inner), _resample())
    x = (sz - em.width) // 2
    y = (sz - em.height) // 2
    canvas.paste(em, (x, y), em)
    return canvas


_EXE_ICON_SIZES = (256, 128, 64, 48, 32, 16)


def build_ea_exe_icon(
    src: str | None = None,
    dest: str | None = None,
    *,
    force: bool = False,
) -> str:
    """
    Build square multi-size icon_exe.ico for PyInstaller / Windows Explorer.

    Uses the full emblem from bin/icon.ico (64×41), letterboxed on a transparent
    square. Does not modify bin/logo.png.
    """
    icon = src or os.path.join(BIN, "icon.ico")
    dest = dest or os.path.join(BIN, "icon_exe.ico")
    if not os.path.isfile(icon):
        raise FileNotFoundError("Need bin/icon.ico")
    newest = os.path.getmtime(icon)
    if not force and os.path.isfile(dest) and os.path.getmtime(dest) >= newest:
        return dest
    emblem = _ea_emblem_for_exe_icon()
    imgs = [_square_icon_from_emblem(emblem, sz) for sz in _EXE_ICON_SIZES]
    _save_multi_ico(dest, imgs)
    print(f"  wrote {dest} (full icon.ico emblem, {len(_EXE_ICON_SIZES)} square sizes)")
    return dest


def _icon_win_from_ico(ico_path: str, win_path: str) -> None:
    if os.path.isfile(win_path) or not os.path.isfile(ico_path):
        return
    img = Image.open(ico_path)
    img.load()
    if getattr(img, "n_frames", 1) > 1:
        best, best_sz = None, 0
        for i in range(img.n_frames):
            img.seek(i)
            frame = img.copy()
            if frame.width >= 32 and frame.width > best_sz:
                best, best_sz = frame, frame.width
        img = (best or img.copy()).convert("RGBA")
    else:
        img = img.convert("RGBA")
    resample = getattr(Image, "Resampling", Image).LANCZOS
    img.thumbnail((64, 64), resample)
    img.save(win_path, "PNG")
    print(f"  wrote {win_path} (from {os.path.basename(ico_path)})")


def ensure_ea_bin_assets(*, force: bool = False) -> None:
    """Refresh icon_win.png from bin/icon.ico only — never overwrite icon.ico or logo.png."""
    icon = os.path.join(BIN, "icon.ico")
    win = os.path.join(BIN, "icon_win.png")
    if not os.path.isfile(icon):
        print(f"  NOTE: {icon} missing — place your EA icon there (not auto-generated).")
        return
    if force:
        print("  NOTE: --force does not overwrite bin/icon.ico or bin/logo.png.")
    _icon_win_from_ico(icon, win)
    build_ea_exe_icon(force=force)


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--ea-bin", action="store_true",
                    help="Only refresh bin/icon_win.png from bin/icon.ico (never overwrites icon/logo)")
    ap.add_argument("--ea-icon-transparent", action="store_true",
                    help="Make bin/icon.ico background transparent (black → alpha)")
    ap.add_argument("--force", action="store_true", help="Overwrite existing EA bin assets")
    args = ap.parse_args()

    if args.ea_icon_transparent:
        print("EA icon transparent background …")
        make_ea_icon_transparent()
        build_ea_exe_icon(force=True)
        print("Done.")
        return

    if args.ea_bin:
        print("Generating EA bin assets …")
        ensure_ea_bin_assets(force=args.force)
        print("Done.")
        return

    print("Generating branding assets …")
    _ensure_utm_assets()

    lecturer = os.path.join(BRAND, "lecturer")
    student = os.path.join(BRAND, "student")
    os.makedirs(lecturer, exist_ok=True)
    os.makedirs(student, exist_ok=True)

    print("  Lecturer (UTM logo + framed emblem icon):")
    _lecturer_logo(os.path.join(lecturer, "logo.png"))
    _lecturer_icon(os.path.join(lecturer, "icon.ico"))

    print("  Student (placeholder):")
    _student_logo(os.path.join(student, "logo.png"), STUDENT_STYLE)
    _student_icon(os.path.join(student, "icon.ico"), STUDENT_STYLE)

    print("Done.")
    print("  Lecturer: UTM assets from bin/branding/assets/ (Wikimedia Commons)")
    print("  Replace utm_full.png / utm_emblem.png there to use a different UTM artwork.")


if __name__ == "__main__":
    main()
