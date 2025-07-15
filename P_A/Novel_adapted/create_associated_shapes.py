import numpy as np
import matplotlib.pyplot as plt
import os
import json
from scipy.interpolate import CubicSpline  # Replace interp1d
import pandas as pd

# ---------------- SETTINGS -----------------
SAVE_DIR = "generated_associated_shapes"
os.makedirs(SAVE_DIR, exist_ok=True)

RANDOM_SEED = 42  # <<<<<<<< Add this line for reproducibility

n_shapes = 6
image_size = 4
resolution = 600
color = "black"
FREEZE = True  # <<<<<<<<<<<<<< CHANGE THIS TO TRUE TO FREEZE SHAPES

shape_params = [
    {"lobes": 10, "amp": 0.60},
    {"lobes": 15, "amp": 0.45},
    {"lobes": 20, "amp": 0.30},
    {"lobes": 25, "amp": 0.35},
    {"lobes": 30, "amp": 0.50},
    {"lobes": 35, "amp": 0.65},
]

def generate_blob(n_lobes, amp, seed=None):
    if seed is not None:
        np.random.seed(seed)

    base_angles = np.linspace(0, 2 * np.pi, n_lobes, endpoint=False)
    base_radii = 1 + np.random.uniform(-amp, amp, size=n_lobes)

    # Use periodic cubic spline for smooth, looping shape
    base_angles = np.append(base_angles, 2 * np.pi)
    base_radii = np.append(base_radii, base_radii[0])  # Close the loop

    spline = CubicSpline(base_angles, base_radii, bc_type='periodic')
    theta = np.linspace(0, 2 * np.pi, resolution)
    r = spline(theta)

    x = r * np.cos(theta)
    y = r * np.sin(theta)
    return x, y

# ------------ MAIN LOOP -------------
shape_data = []  # Collect all shape info here

for i, p in enumerate(shape_params):
    shape_json = os.path.join(SAVE_DIR, f"shape_{i+1:02d}.json")

    if FREEZE and os.path.exists(shape_json):
        # Load frozen shape
        with open(shape_json, "r") as f:
            data = json.load(f)
        x = np.array(data["x"])
        y = np.array(data["y"])
    else:
        # Generate new random shape
        # Use a different seed for each shape for diversity, but deterministic
        x, y = generate_blob(p["lobes"], p["amp"], seed=RANDOM_SEED + i)
        if FREEZE:
            with open(shape_json, "w") as f:
                json.dump({"x": x.tolist(), "y": y.tolist()}, f)

    # Draw and save PNG
    fig, ax = plt.subplots(figsize=(image_size, image_size), dpi=100)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.fill(x, y, color=color)
    ax.set_xlim(-2, 2)
    ax.set_ylim(-2, 2)

    fname = f"associated_shape_{i+1:02d}.png"
    fig.savefig(os.path.join(SAVE_DIR, fname), transparent=False, facecolor='white')
    plt.close(fig)

    # Collect summary info for Excel
    shape_data.append({
        "shape_index": i+1,
        "lobes": p["lobes"],
        "amp": p["amp"],
        "image_file": f"associated_shape_{i+1:02d}.png"
    })

# Save summary Excel file
excel_path = os.path.join(SAVE_DIR, "associated_shapes_summary.xlsx")
df = pd.DataFrame(shape_data)
df.to_excel(excel_path, index=False)

print(f"✅ Shapes {'loaded' if FREEZE else 'generated'} and saved in '{SAVE_DIR}'")
print(f"📄 Excel summary saved at '{excel_path}'")