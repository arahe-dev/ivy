from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SVG_DIR = ROOT / "svg"
PNG_DIR = ROOT / "png"

INK = "#121214"
IVORY = "#F6F4EF"
AMBER = "#C98A2E"
GRAPHITE = "#2A2A2F"
MIST = "#D8D4CC"

FONT_STACK = "Georgia, 'Times New Roman', serif"
UI_STACK = "Inter, Arial, sans-serif"
WORDMARK = "Alexandr&#305;a"


def fingerprint(stroke: str = AMBER, *, scale: float = 1.0, x: float = 0, y: float = 0) -> str:
    width = 4.6 * scale
    return f"""
    <g transform="translate({x:.2f} {y:.2f}) scale({scale:.3f})"
       fill="none" stroke="{stroke}" stroke-width="{width:.2f}" stroke-linecap="round" stroke-linejoin="round">
      <path d="M40 8 C26 8 16 17 16 31" />
      <path d="M48 10 C63 15 72 29 69 45" />
      <path d="M25 30 C27 18 39 14 49 19 C60 24 63 35 60 49" />
      <path d="M34 35 C36 27 43 24 50 28 C57 32 58 41 55 52" />
      <path d="M43 42 C43 36 49 35 51 40 C53 45 48 56 45 64" />
      <path d="M19 43 C20 55 26 66 36 73" />
      <path d="M67 55 C61 70 50 79 36 82" />
      <path d="M30 50 C33 63 43 69 53 67" />
    </g>
    """


def svg_shell(width: int, height: int, body: str, *, background: str | None = None) -> str:
    bg = f'<rect width="{width}" height="{height}" fill="{background}"/>' if background else ""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <defs>
    <style>
      .wordmark {{
        font-family: {FONT_STACK};
        font-weight: 700;
        letter-spacing: -11px;
      }}
      .label {{
        font-family: {UI_STACK};
        font-weight: 700;
        letter-spacing: .08em;
      }}
      .ui {{
        font-family: {UI_STACK};
      }}
    </style>
  </defs>
  {bg}
  {body}
</svg>
"""


def wordmark(primary: bool = True, *, dark: bool = False) -> str:
    width, height = 1420, 360
    text_fill = IVORY if dark else INK
    fingerprint_fill = AMBER if primary else GRAPHITE
    body = f"""
  <text class="wordmark" x="55" y="250" font-size="220" fill="{text_fill}">{WORDMARK}</text>
  {fingerprint(fingerprint_fill, scale=0.72, x=1008, y=73)}
"""
    return svg_shell(width, height, body, background=INK if dark else None)


def app_icon(size: int = 1024, *, favicon: bool = False) -> str:
    radius = 205 if not favicon else 58
    a_size = 640 if not favicon else 160
    a_x = 292 if not favicon else 73
    a_y = 720 if not favicon else 184
    fp_scale = 1.65 if not favicon else 0.47
    fp_x = 655 if not favicon else 166
    fp_y = 205 if not favicon else 43
    body = f"""
  <rect x="0" y="0" width="{size}" height="{size}" rx="{radius}" fill="{INK}"/>
  <text class="wordmark" x="{a_x}" y="{a_y}" font-size="{a_size}" fill="{IVORY}" letter-spacing="-18">A</text>
  {fingerprint(AMBER, scale=fp_scale, x=fp_x, y=fp_y)}
"""
    return svg_shell(size, size, body)


def brand_kit() -> str:
    width, height = 1800, 1260
    body = f"""
  <rect width="{width}" height="{height}" fill="{IVORY}"/>
  <line x1="20" y1="350" x2="1780" y2="350" stroke="{MIST}" stroke-width="2"/>
  <line x1="20" y1="665" x2="1780" y2="665" stroke="{MIST}" stroke-width="2"/>
  <line x1="20" y1="965" x2="1780" y2="965" stroke="{MIST}" stroke-width="2"/>
  <line x1="1120" y1="20" x2="1120" y2="350" stroke="{MIST}" stroke-width="2"/>
  <line x1="1508" y1="20" x2="1508" y2="350" stroke="{MIST}" stroke-width="2"/>
  <line x1="900" y1="370" x2="900" y2="965" stroke="{MIST}" stroke-width="2"/>

  <text class="label" x="22" y="45" font-size="18" fill="{INK}">1. PRIMARY HORIZONTAL WORDMARK</text>
  <text class="wordmark" x="120" y="270" font-size="190" fill="{INK}">{WORDMARK}</text>
  {fingerprint(AMBER, scale=0.62, x=928, y=106)}

  <text class="label" x="1165" y="45" font-size="18" fill="{INK}">2. APP ICON</text>
  <rect x="1195" y="88" width="250" height="250" rx="50" fill="{INK}"/>
  <text class="wordmark" x="1272" y="268" font-size="160" fill="{IVORY}">A</text>
  {fingerprint(AMBER, scale=0.62, x=1359, y=126)}

  <text class="label" x="1540" y="45" font-size="18" fill="{INK}">3. FAVICON</text>
  <rect x="1608" y="132" width="86" height="86" rx="16" fill="{INK}"/>
  <text class="wordmark" x="1632" y="198" font-size="58" fill="{IVORY}">A</text>
  {fingerprint(AMBER, scale=0.22, x=1673, y=149)}

  <text class="label" x="22" y="395" font-size="18" fill="{INK}">4. MONOCHROME VERSION</text>
  <text class="wordmark" x="140" y="585" font-size="142" fill="{INK}">{WORDMARK}</text>
  {fingerprint(GRAPHITE, scale=0.43, x=724, y=458)}

  <text class="label" x="925" y="395" font-size="18" fill="{INK}">5. DARK-MODE VERSION</text>
  <rect x="928" y="438" width="835" height="195" rx="12" fill="{INK}"/>
  <text class="wordmark" x="1068" y="575" font-size="130" fill="{IVORY}">{WORDMARK}</text>
  {fingerprint(AMBER, scale=0.42, x=1536, y=466)}

  <text class="label" x="22" y="710" font-size="18" fill="{INK}">6. COLOR PALETTE</text>
  {palette_square(40, 745, INK, "Ink Black", "#121214")}
  {palette_square(210, 745, IVORY, "Warm Ivory", "#F6F4EF")}
  {palette_square(380, 745, AMBER, "Fingerprint Amber", "#C98A2E")}
  {palette_square(550, 745, MIST, "Mist Gray", "#D8D4CC")}
  {palette_square(720, 745, GRAPHITE, "Graphite", "#2A2A2F")}

  <text class="label" x="925" y="710" font-size="18" fill="{INK}">7. TYPOGRAPHY PAIRINGS</text>
  <text class="ui" x="925" y="750" font-size="17" fill="{INK}">Display / Custom Alexandria Wordmark</text>
  <text class="wordmark" x="925" y="858" font-size="72" fill="{INK}">{WORDMARK}</text>
  {fingerprint(AMBER, scale=0.22, x=1206, y=797)}
  <text class="ui" x="1280" y="750" font-size="17" fill="{INK}">UI Sans / Inter</text>
  <text class="ui" x="1280" y="850" font-size="72" fill="{INK}">Aa</text>
  <text class="ui" x="1540" y="750" font-size="17" fill="{INK}">Editorial Support / Source Serif 4</text>
  <text x="1540" y="850" font-family="Georgia, serif" font-size="72" fill="{INK}">Aa</text>

  <text class="label" x="22" y="1010" font-size="18" fill="{INK}">8. DASHBOARD HEADER EXAMPLE</text>
  <rect x="22" y="1048" width="1756" height="118" rx="14" fill="#FFFFFF" stroke="{MIST}" stroke-width="1.5"/>
  <text class="wordmark" x="60" y="1128" font-size="72" fill="{INK}">{WORDMARK}</text>
  {fingerprint(AMBER, scale=0.21, x=298, y=1076)}
  <line x1="335" y1="1075" x2="335" y2="1140" stroke="{MIST}" stroke-width="2"/>
  <rect x="386" y="1072" width="650" height="72" rx="16" fill="#FAFAFA" stroke="{MIST}" stroke-width="1.5"/>
  <circle cx="424" cy="1108" r="12" fill="none" stroke="{GRAPHITE}" stroke-width="3"/>
  <line x1="434" y1="1118" x2="445" y2="1129" stroke="{GRAPHITE}" stroke-width="3" stroke-linecap="round"/>
  <text class="ui" x="470" y="1115" font-size="22" fill="#7A7770">Ask anything or search your memory...</text>
  <rect x="1100" y="1072" width="138" height="72" rx="22" fill="{INK}"/>
  <text class="ui" x="1150" y="1115" font-size="21" font-weight="700" fill="{IVORY}">Memory</text>
  <text class="ui" x="1290" y="1115" font-size="21" fill="{INK}">Context</text>
  <text class="ui" x="1425" y="1115" font-size="21" fill="{INK}">Sources</text>
  <text class="ui" x="1560" y="1115" font-size="21" fill="{INK}">Recall</text>
  <circle cx="1717" cy="1108" r="30" fill="{INK}"/>
  <text class="wordmark" x="1699" y="1128" font-size="44" fill="{IVORY}">A</text>
"""
    return svg_shell(width, height, body)


def palette_square(x: int, y: int, color: str, name: str, value: str) -> str:
    return f"""
  <rect x="{x}" y="{y}" width="145" height="145" fill="{color}" stroke="{MIST}" stroke-width="1"/>
  <text class="ui" x="{x}" y="{y + 175}" font-size="17" fill="{INK}">{name}</text>
  <text class="ui" x="{x}" y="{y + 203}" font-size="16" fill="{INK}">{value}</text>
"""


ASSETS = {
    "alexandria-wordmark-primary": (1420, 360, lambda: wordmark(primary=True, dark=False)),
    "alexandria-wordmark-monochrome": (1420, 360, lambda: wordmark(primary=False, dark=False)),
    "alexandria-wordmark-dark": (1420, 360, lambda: wordmark(primary=True, dark=True)),
    "alexandria-app-icon": (1024, 1024, lambda: app_icon(1024, favicon=False)),
    "alexandria-favicon": (256, 256, lambda: app_icon(256, favicon=True)),
    "alexandria-brand-kit": (1800, 1260, brand_kit),
}


def write_svgs() -> list[Path]:
    SVG_DIR.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, (_, _, factory) in ASSETS.items():
        path = SVG_DIR / f"{name}.svg"
        path.write_text(factory(), encoding="utf-8")
        paths.append(path)
    return paths


def chrome_candidates() -> list[Path]:
    candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    ]
    return [path for path in candidates if path.exists()]


def export_pngs(chrome: Path | None = None) -> list[Path]:
    if chrome is None:
        candidates = chrome_candidates()
        if not candidates:
            raise RuntimeError("Chrome/Edge not found. SVGs were generated, but PNG export needs a headless browser.")
        chrome = candidates[0]
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="alexandria_assets_") as tmp:
        tmp_dir = Path(tmp)
        profile = tmp_dir / "profile"
        for name, (width, height, _) in ASSETS.items():
            svg_path = SVG_DIR / f"{name}.svg"
            png_path = PNG_DIR / f"{name}.png"
            html_path = tmp_dir / f"{name}.html"
            html_path.write_text(
                f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {{
      margin: 0;
      width: {width}px;
      height: {height}px;
      overflow: hidden;
      background: transparent;
    }}
    svg {{
      width: {width}px;
      height: {height}px;
      display: block;
    }}
  </style>
</head>
<body>
{svg_path.read_text(encoding="utf-8")}
</body>
</html>
""",
                encoding="utf-8",
            )
            subprocess.run(
                [
                    str(chrome),
                    "--headless=new",
                    "--disable-gpu",
                    "--hide-scrollbars",
                    "--allow-file-access-from-files",
                    "--default-background-color=00000000",
                    f"--user-data-dir={profile}",
                    f"--window-size={width},{height}",
                    f"--screenshot={png_path}",
                    html_path.as_uri(),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            exported.append(png_path)
    return exported


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Alexandria SVG and PNG assets.")
    parser.add_argument("--svg-only", action="store_true", help="only write SVG assets")
    parser.add_argument("--png-only", action="store_true", help="only export PNGs from existing SVG assets")
    parser.add_argument("--chrome", type=Path, default=None, help="path to chrome/msedge executable for PNG export")
    args = parser.parse_args()

    if not args.png_only:
        svg_paths = write_svgs()
        for path in svg_paths:
            print(f"wrote {path}")

    if not args.svg_only:
        png_paths = export_pngs(args.chrome)
        for path in png_paths:
            print(f"wrote {path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
