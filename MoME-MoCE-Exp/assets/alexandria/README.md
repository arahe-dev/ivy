# Alexandria Brand Assets

This folder locks the first Alexandria dogfood brand direction:

- bold, tight serif wordmark;
- black / warm ivory / graphite palette;
- small amber fingerprint accent over the `i`;
- simple app icon and favicon;
- no Greek, temple, neural, sparkle, robot, or brain imagery.

## Files

| path | role |
|---|---|
| `build_assets.py` | deterministic asset generator |
| `svg/` | editable vector assets |
| `png/` | rendered PNG exports |

Generated assets:

- `alexandria-wordmark-primary`
- `alexandria-wordmark-monochrome`
- `alexandria-wordmark-dark`
- `alexandria-app-icon`
- `alexandria-favicon`
- `alexandria-brand-kit`

## Rebuild

```powershell
cd C:\ivy-worktrees\d-acca-dd-acca-librarian-supercharge\MoME-MoCE-Exp\assets\alexandria
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe build_assets.py
```

The script writes SVG assets first, then rasterizes PNGs through local Chrome or Edge in headless mode.

SVG-only:

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe build_assets.py --svg-only
```

PNG-only:

```powershell
C:\ivy\MoME-MoCE-Exp\.venv\Scripts\python.exe build_assets.py --png-only
```

## Palette

| token | hex |
|---|---|
| Ink Black | `#121214` |
| Warm Ivory | `#F6F4EF` |
| Fingerprint Amber | `#C98A2E` |
| Mist Gray | `#D8D4CC` |
| Graphite | `#2A2A2F` |

## Usage

Use the wordmark for brand surfaces and docs. Use the app icon or favicon for compact UI. In product UI, keep the serif logo small and pair it with a neutral sans-serif interface font.
