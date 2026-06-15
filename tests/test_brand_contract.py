from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "web" / "frontend"
ELECTRON_COPY = ROOT / "electron_version"


def test_primary_brand_entries_use_inkrest_name() -> None:
    expected = {
        FRONTEND / "src" / "App.vue": ("栖墨", "INKREST", "智能长篇写作空间"),
        FRONTEND / "index.html": ("栖墨 · INKREST",),
        FRONTEND / "package.json": ('"productName": "栖墨"',),
        FRONTEND / "electron" / "main.ts": ("title: '栖墨 · INKREST'", "app.setName('栖墨')"),
        FRONTEND / "electron" / "tray" / "tray-manager.ts": ("栖墨 · INKREST - 智能长篇写作空间", "退出栖墨"),
        FRONTEND / "electron" / "updater" / "auto-updater.ts": ("`栖墨 ${info.version} 已发布`",),
        FRONTEND / "src" / "api" / "client.ts": ("请输入栖墨远程访问令牌",),
    }

    for path, snippets in expected.items():
        source = path.read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in source, f"{path} is missing {snippet!r}"


def test_secondary_electron_source_copy_uses_inkrest_name() -> None:
    expected = {
        ELECTRON_COPY / "package.json": ('"productName": "栖墨"',),
        ELECTRON_COPY / "electron" / "main.ts": ("title: '栖墨 · INKREST'", "app.setName('栖墨')"),
        ELECTRON_COPY / "electron" / "tray" / "tray-manager.ts": ("栖墨 · INKREST - 智能长篇写作空间", "退出栖墨"),
        ELECTRON_COPY / "electron" / "updater" / "auto-updater.ts": ("`栖墨 ${info.version} 已发布`",),
    }

    for path, snippets in expected.items():
        source = path.read_text(encoding="utf-8")
        for snippet in snippets:
            assert snippet in source, f"{path} is missing {snippet!r}"


def test_inkrest_icon_assets_exist() -> None:
    favicon = FRONTEND / "public" / "favicon.svg"
    png = FRONTEND / "build" / "icon.png"
    ico = FRONTEND / "build" / "icon.ico"

    assert "viewBox=\"0 0 512 512\"" in favicon.read_text(encoding="utf-8")
    assert png.exists() and png.stat().st_size > 0
    assert ico.exists() and ico.stat().st_size > 0


def test_secondary_electron_source_copy_has_icon_assets() -> None:
    for name in ("icon.png", "icon.ico", "tray_icon.png"):
        path = ELECTRON_COPY / "build" / name
        assert path.exists(), f"missing icon asset: {path}"
        assert path.stat().st_size > 0


def test_secondary_electron_runtime_sources_match_primary_copy() -> None:
    primary_root = FRONTEND / "electron"
    secondary_root = ELECTRON_COPY / "electron"
    for primary_path in primary_root.rglob("*.ts"):
        relative = primary_path.relative_to(primary_root)
        secondary_path = secondary_root / relative
        assert secondary_path.exists(), f"missing secondary Electron source: {relative}"
        assert secondary_path.read_text(encoding="utf-8") == primary_path.read_text(encoding="utf-8"), (
            f"secondary Electron source is out of sync: {relative}"
        )


def test_desktop_icons_use_transparent_canvas_edges() -> None:
    for root in (FRONTEND, ELECTRON_COPY):
        for name in ("icon.png", "icon.ico"):
            image = Image.open(root / "build" / name).convert("RGBA")
            assert image.getpixel((0, 0))[3] == 0


def test_tray_png_transparent_pixels_do_not_carry_bright_rgb() -> None:
    for root in (FRONTEND, ELECTRON_COPY):
        image = Image.open(root / "build" / "icon.png").convert("RGBA")
        dirty_transparent_pixels = [
            (red, green, blue, alpha)
            for red, green, blue, alpha in image.getdata()
            if alpha == 0 and (red != 0 or green != 0 or blue != 0)
        ]
        assert not dirty_transparent_pixels, (
            f"{root / 'build' / 'icon.png'} has transparent pixels carrying RGB data; "
            "Windows tray scaling can reveal these as bright edge artifacts"
        )


def test_desktop_icon_corner_pixels_do_not_scale_into_white_dots() -> None:
    for root in (FRONTEND, ELECTRON_COPY):
        for name in ("icon.png", "icon.ico"):
            image = Image.open(root / "build" / name).convert("RGBA")
            width, height = image.size
            margin = max(1, round(width * 80 / 512))
            corner_boxes = (
                (0, 0, margin, margin),
                (width - margin, 0, width, margin),
                (0, height - margin, margin, height),
                (width - margin, height - margin, width, height),
            )
            bright_corner_pixels = []
            for left, top, right, bottom in corner_boxes:
                for y in range(top, bottom):
                    for x in range(left, right):
                        red, green, blue, alpha = image.getpixel((x, y))
                        if alpha > 0 and red > 220 and green > 220 and blue > 220:
                            bright_corner_pixels.append((x, y, red, green, blue, alpha))
            assert not bright_corner_pixels, (
                f"{root / 'build' / name} has bright opaque corner pixels; "
                "Windows tray downscaling can turn them into white dots"
            )


def test_tray_icon_uses_dedicated_no_white_small_asset() -> None:
    for root in (FRONTEND, ELECTRON_COPY):
        tray_icon = root / "build" / "tray_icon.png"
        assert tray_icon.exists(), f"missing tray icon asset: {tray_icon}"
        image = Image.open(tray_icon).convert("RGBA")
        assert image.size == (32, 32)
        small = image.resize((16, 16), Image.Resampling.LANCZOS)
        white_pixels = [
            (red, green, blue, alpha)
            for red, green, blue, alpha in small.getdata()
            if alpha > 32 and red > 220 and green > 220 and blue > 220
        ]
        assert not white_pixels, f"{tray_icon} scales to visible white tray pixels"

        tray_source = (root / "electron" / "tray" / "tray-manager.ts").read_text(encoding="utf-8")
        assert "tray_icon.png" in tray_source
