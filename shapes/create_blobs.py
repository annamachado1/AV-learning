"""
blobs_standalone.py

Makes 6 clearly different, smooth, rounded black blobs on a white background,
saves each one as a PNG, and writes an Excel file listing the attributes of
every shape. All images have the same contrast (RMS ~120).

Needs only:  numpy   (and openpyxl if you want an .xlsx instead of a .csv)
No OpenCV, no Pillow, no matplotlib.
Run:         python blobs_standalone.py
"""
import csv
import os
import random
import struct
import zlib

import numpy as np

try:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False

# ───────────────────────── settings ─────────────────────────
OUTPUT_DIR = "blobs_output"
IMAGE_SIZE = 1500          # pixels, square image
TARGET_RMS = 120           # contrast every image should have
RMS_TOLERANCE = 0.5        # how close to the target is good enough
SEED = 42                  # same seed -> same blobs every run

# Each blob is a circle with gentle waves added to its edge.
# A wave is (number_of_bumps, strength). Bigger strength = deeper bumps.
# Bump counts 1 and 2 are avoided on purpose: they would shift the blob
# off-center or stretch it into an oval, which looks like it "points".
BLOB_DESIGNS = [
    [(4, 0.14)],                 # 4 broad, soft bumps
    [(5, 0.10)],                 # 5 bumps
    [(6, 0.055)],                # 6 small bumps
    [(7, 0.04)],                 # 7 gentle ripples
    [(3, 0.10), (5, 0.05)],      # broad bumps with smaller ones mixed in
    [(4, 0.07), (6, 0.04)],      # uneven bumps of different sizes
]

COLUMNS = [
    "Shape", "File", "Description", "Number_of_Waves",
    "Main_Wave_Bumps", "Main_Wave_Strength",
    "Second_Wave_Bumps", "Second_Wave_Strength",
    "Wave_Rotations_deg", "Blob_Size_px", "Width_px", "Height_px",
    "Black_Area_percent", "Elongation", "Sharpest_Bend", "RMS_Contrast",
    "Image_Size_px", "Shape_Color", "Background_Color", "Random_Seed",
]


def save_png(path, gray):
    """Write a grayscale uint8 array as a PNG using only the standard library."""
    height, width = gray.shape

    def chunk(kind, data):
        body = kind + data
        return (struct.pack(">I", len(data)) + body +
                struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF))

    rows = np.hstack([np.zeros((height, 1), dtype=np.uint8), gray])  # filter byte 0
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        f.write(chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)))
        f.write(chunk(b"IDAT", zlib.compress(rows.tobytes(), 6)))
        f.write(chunk(b"IEND", b""))


def main():
    rng = random.Random(SEED)   # Python's own random numbers (not numpy's)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    rows = []

    # For every pixel: its distance from the image center and its angle.
    # (The blob is described by "how far is the edge at each angle", so a
    # pixel is black if it is closer to the center than the edge is.)
    middle = (IMAGE_SIZE - 1) / 2
    grid = np.arange(IMAGE_SIZE) - middle
    pixel_x, pixel_y = np.meshgrid(grid, grid)
    pixel_distance = np.hypot(pixel_x, pixel_y)
    pixel_angle = np.arctan2(pixel_y, pixel_x)

    # a ring of angles used for measuring the outline
    ring = np.linspace(0, 2 * np.pi, 720, endpoint=False)

    for number, waves in enumerate(BLOB_DESIGNS, start=1):
        # Pick a random turn for each wave, then describe the edge distance
        # (and how fast it changes) for any angle.
        rotations = [rng.uniform(0, 2 * np.pi) for _ in waves]

        def edge(angle):
            """Edge distance (circle = 1) plus its 1st and 2nd change rates."""
            r = np.ones_like(angle)
            slope = np.zeros_like(angle)
            curve = np.zeros_like(angle)
            for (bumps, strength), turn in zip(waves, rotations):
                phase = bumps * angle + turn
                r += strength * np.cos(phase)
                slope -= strength * bumps * np.sin(phase)
                curve -= strength * bumps**2 * np.cos(phase)
            return r, slope, curve

        edge_r, edge_slope, _ = edge(pixel_angle)
        # slant of the edge, used to get a smooth anti-aliased border
        tilt = np.sqrt(1 + (edge_slope / edge_r) ** 2)

        # Find the blob size that gives the target contrast.
        # (Bigger blob = more black = different contrast, so we search.)
        small, big = 100.0, 600.0
        for _ in range(40):
            size = (small + big) / 2
            inside_by = (size * edge_r - pixel_distance) / tilt   # pixels
            coverage = np.clip(inside_by + 0.5, 0, 1)             # 0 to 1
            picture = np.round(255 * (1 - coverage)).astype(np.uint8)

            rms = picture.std()
            if abs(rms - TARGET_RMS) < RMS_TOLERANCE:
                break
            if rms < TARGET_RMS:
                small = size      # too little black -> grow the blob
            else:
                big = size        # too much black -> shrink the blob

        file_name = os.path.join(OUTPUT_DIR, f"blob_{number:02d}.png")
        save_png(file_name, picture)

        # ── measure the finished shape ──
        black = picture < 128
        ys, xs = np.where(black)
        width = int(xs.max() - xs.min() + 1)
        height = int(ys.max() - ys.min() + 1)
        black_percent = 100 * black.mean()

        # 1.0 = equally spread in every direction (no stretching)
        spread = np.linalg.eigvalsh(np.cov(np.vstack([xs, ys])))
        elongation = np.sqrt(spread[1] / spread[0])

        # how sharply the edge bends at its tightest spot (circle = 1.0)
        r, r1, r2 = edge(ring)
        sharpest = np.max(np.abs(r**2 + 2 * r1**2 - r * r2) / (r**2 + r1**2) ** 1.5)

        # plain-English description, e.g. "4 bumps (strength 0.14)"
        description = " + ".join(f"{b} bumps (strength {s})" for b, s in waves)
        second = waves[1] if len(waves) > 1 else (None, None)

        rows.append({
            "Shape": number,
            "File": os.path.basename(file_name),
            "Description": description,
            "Number_of_Waves": len(waves),
            "Main_Wave_Bumps": waves[0][0],
            "Main_Wave_Strength": waves[0][1],
            "Second_Wave_Bumps": second[0],
            "Second_Wave_Strength": second[1],
            "Wave_Rotations_deg": ", ".join(
                str(round(float(np.degrees(t)), 1)) for t in rotations),
            "Blob_Size_px": round(size, 1),
            "Width_px": width,
            "Height_px": height,
            "Black_Area_percent": round(float(black_percent), 2),
            "Elongation": round(float(elongation), 3),
            "Sharpest_Bend": round(float(sharpest), 2),
            "RMS_Contrast": round(float(rms), 2),
            "Image_Size_px": f"{IMAGE_SIZE} x {IMAGE_SIZE}",
            "Shape_Color": "black",
            "Background_Color": "white",
            "Random_Seed": SEED,
        })
        print(f"saved {file_name}   contrast = {rms:.1f}")

    # ── write the attribute table ──
    if HAVE_OPENPYXL:
        path = os.path.join(OUTPUT_DIR, "blob_attributes.xlsx")
        book = Workbook()
        sheet = book.active
        sheet.title = "Shape attributes"
        sheet.append(COLUMNS)
        for cell in sheet[1]:
            cell.font = Font(bold=True)
        for row in rows:
            sheet.append([row[c] for c in COLUMNS])
        for column in sheet.columns:                    # tidy column widths
            longest = max(len(str(c.value)) for c in column if c.value is not None)
            sheet.column_dimensions[column[0].column_letter].width = longest + 2
        book.save(path)
    else:
        path = os.path.join(OUTPUT_DIR, "blob_attributes.csv")
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=COLUMNS)
            writer.writeheader()
            writer.writerows(rows)
        print("\n(openpyxl is not installed, so a CSV was saved instead; "
              "Excel can open CSV files too.)")
    print("\nAttributes saved ->", path)


if __name__ == "__main__":
    main()
