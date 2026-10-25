"""Synthetic lab report generator.

Creates realistic-looking report images (several layouts, phone-photo degradation)
together with a ground-truth JSON file, so extraction accuracy can be measured
exactly without using any real patient data.

Usage (from backend/):
    python -m tools.generate_reports --count 20 --out ../data/synthetic --seed 42
"""
import argparse
import json
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

from app.normalizer import load_biomarkers
from app.rules import flag_value, parse_reference_range

LAYOUTS = ("grid", "compact", "range_first")
LAB_NAMES = ["Sample Diagnostics Laboratory", "Demo Clinical Lab", "Example Pathology Centre"]
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
PAGE = (1240, 1754)  # A4 at ~150 dpi


def _font(bold: bool, size: int) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REGULAR
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default(size)


def make_value(biomarker: dict, rng: random.Random, abnormal: bool) -> float:
    low, high = parse_reference_range(biomarker["typical_range"])
    if low is not None and high is not None:
        width = high - low
        if not abnormal:
            v = rng.uniform(low, high)
        elif rng.random() < 0.5:
            v = max(low - width * rng.uniform(0.05, 0.4), low * 0.4)
        else:
            v = high + width * rng.uniform(0.05, 0.4)
    elif high is not None:  # "< x"
        v = high * rng.uniform(1.05, 1.6) if abnormal else high * rng.uniform(0.4, 0.98)
    else:  # "> x"
        v = low * rng.uniform(0.6, 0.95) if abnormal else low * rng.uniform(1.02, 1.6)
    return round(v, biomarker["decimals"])


def build_rows(rng: random.Random, n_rows: int, abnormal_rate: float = 0.3) -> list[dict]:
    markers = rng.sample(list(load_biomarkers().values()), n_rows)
    markers.sort(key=lambda b: b["category"])
    rows = []
    for b in markers:
        value = make_value(b, rng, rng.random() < abnormal_rate)
        low, high = parse_reference_range(b["typical_range"])
        rows.append(
            {
                "biomarker_id": b["id"],
                "raw_name": rng.choice([b["name"], *b["aliases"]]),
                "value": value,
                "unit": b["unit"],
                "reference_range": b["typical_range"],
                "expected_flag": flag_value(value, low, high),
                "category": b["category"],
            }
        )
    return rows


def _fmt(row: dict, decimals_by_id: dict) -> str:
    return f"{row['value']:.{decimals_by_id[row['biomarker_id']]}f}"


def draw_report(rows: list[dict], layout: str, rng: random.Random) -> Image.Image:
    decimals = {b["id"]: b["decimals"] for b in load_biomarkers().values()}
    img = Image.new("RGB", PAGE, "white")
    d = ImageDraw.Draw(img)
    title_f, head_f, body_f, small_f = _font(True, 40), _font(True, 24), _font(False, 24), _font(False, 18)

    lab = rng.choice(LAB_NAMES)
    d.text((70, 60), lab, font=title_f, fill=(20, 40, 90))
    d.line([(70, 118), (PAGE[0] - 70, 118)], fill=(20, 40, 90), width=3)
    pid = f"TEST-{rng.randint(10000, 99999)}"
    d.text((70, 140), f"Patient: Test Patient   ID: {pid}", font=body_f, fill="black")
    d.text((70, 176), f"Age/Sex: {rng.randint(20, 70)} / {rng.choice('MF')}", font=body_f, fill="black")
    d.text((700, 140), f"Collected: 2026-0{rng.randint(1, 9)}-{rng.randint(10, 28)}", font=body_f, fill="black")
    d.text((700, 176), f"Sample No: {rng.randint(100000, 999999)}", font=body_f, fill="black")

    if layout == "grid":
        cols = [("Test", 70), ("Result", 560), ("Unit", 720), ("Reference Range", 880), ("Flag", 1110)]
    elif layout == "compact":
        cols = [("Investigation", 70), ("Observed Value", 560), ("Units", 800), ("Biological Ref. Interval", 940)]
    else:  # range_first
        cols = [("Parameter", 70), ("Ref. Interval", 520), ("Result", 780), ("Unit", 950), ("H/L", 1130)]

    y = 250
    d.rectangle([(60, y - 8), (PAGE[0] - 60, y + 40)], fill=(225, 232, 245))
    for title, x in cols:
        d.text((x, y), title, font=head_f, fill="black")
    y += 60
    row_h = 52
    for i, r in enumerate(rows):
        flag = {"low": "L", "high": "H"}.get(r["expected_flag"], "")
        value = _fmt(r, decimals)
        if layout == "compact" and i % 2 == 0:
            d.rectangle([(60, y - 8), (PAGE[0] - 60, y + row_h - 14)], fill=(245, 245, 245))
        if layout == "grid":
            cells = [r["raw_name"], value, r["unit"], r["reference_range"], flag]
        elif layout == "compact":
            cells = [r["raw_name"], value, r["unit"], r["reference_range"]]
        else:
            cells = [r["raw_name"], r["reference_range"], value, r["unit"], flag]
        for (title, x), text in zip(cols, cells, strict=False):
            bold = flag and title in ("Result", "Observed Value")
            d.text((x, y), str(text), font=_font(bool(bold), 24), fill="black")
        if layout == "grid":
            d.line([(60, y + row_h - 14), (PAGE[0] - 60, y + row_h - 14)], fill=(190, 190, 190), width=1)
        y += row_h

    footer = "SYNTHETIC SAMPLE - generated for software testing, not a real patient."
    d.text((70, PAGE[1] - 90), footer, font=small_f, fill=(120, 120, 120))
    return img


def degrade(img: Image.Image, rng: random.Random) -> Image.Image:
    """Make a clean page look like a phone photo: tilt, uneven light, blur, noise."""
    img = img.rotate(rng.uniform(-3, 3), expand=True, fillcolor=(228, 228, 228), resample=Image.BICUBIC)
    w, h = img.size
    shade = Image.linear_gradient("L").resize((w, h)).rotate(rng.choice([0, 90, 180, 270]))
    shade = shade.point(lambda p: 215 + int(p * 40 / 255))  # 215..255 brightness
    img = ImageChops.multiply(img, Image.merge("RGB", (shade, shade, shade)))
    img = img.filter(ImageFilter.GaussianBlur(rng.uniform(0.4, 1.2)))
    noise = Image.effect_noise((w, h), rng.uniform(4, 10)).convert("RGB")
    return Image.blend(img, ImageChops.multiply(img, noise.point(lambda p: 200 + p // 5)), 0.25)


def generate_report(seed: int, layout: str | None = None, n_rows: int | None = None,
                    degrade_image: bool = True) -> tuple[Image.Image, dict]:
    rng = random.Random(seed)
    layout = layout or rng.choice(LAYOUTS)
    n_rows = n_rows or rng.randint(10, 20)
    rows = build_rows(rng, n_rows)
    img = draw_report(rows, layout, rng)
    if degrade_image:
        img = degrade(img, rng)
    truth = {"seed": seed, "layout": layout, "rows": rows}
    return img, truth


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--count", type=int, default=10)
    p.add_argument("--out", type=Path, default=Path("../data/synthetic"))
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--clean", action="store_true", help="skip phone-photo degradation")
    args = p.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for i in range(args.count):
        img, truth = generate_report(args.seed + i, degrade_image=not args.clean)
        stem = args.out / f"report_{i:03d}"
        img.save(stem.with_suffix(".jpg"), quality=70)
        stem.with_suffix(".json").write_text(json.dumps(truth, indent=2), encoding="utf-8")
    print(f"Wrote {args.count} reports to {args.out}")


if __name__ == "__main__":
    main()
