import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Circle, Rectangle
from matplotlib.path import Path
from skimage.color import rgb2lab, lab2rgb
import os

# Create output directory
output_dir = "stimuli_images"
os.makedirs(output_dir, exist_ok=True)

# --- Helper Functions ---
def adjust_luminance(rgb_color, target_lum=60):
    """Adjusts luminance (L*) in LAB color space."""
    lab = rgb2lab(np.array([[rgb_color]]))
    lab[0, 0, 0] = target_lum
    return lab2rgb(lab)[0, 0]

from scipy.interpolate import splprep, splev

def generate_blob_path(center=(0.5, 0.5), radius=0.3, seed=123, n_points=20):
    """Generate a smooth, paint-splatter-like blob shape."""
    np.random.seed(seed)
    angles = np.linspace(0, 2 * np.pi, n_points, endpoint=False)
    radii = radius * (1 + 0.35 * (np.random.rand(n_points) - 0.5))
    x = center[0] + radii * np.cos(angles)
    y = center[1] + radii * np.sin(angles)

    # Ensure the shape is closed by repeating first points
    x = np.r_[x, x[:3]]
    y = np.r_[y, y[:3]]

    # Fit smooth spline (B-spline interpolation)
    tck, _ = splprep([x, y], s=0, per=True)
    smooth_pts = splev(np.linspace(0, 1, 200), tck)
    verts = list(zip(smooth_pts[0], smooth_pts[1]))
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 1) + [Path.CLOSEPOLY]
    verts.append(verts[0])  # closing the shape
    return Path(verts, codes)

# --- Define and adjust 6 base colors (with yellow instead of green) ---
base_colors = [
    (1.0, 0.0, 0.0),  # red
    (1.0, 1.0, 0.0),  # yellow (replaces green)
    (0.0, 0.0, 1.0),  # blue
    (1.0, 0.0, 1.0),  # magenta
    (0.0, 1.0, 1.0),  # cyan
    (1.0, 0.5, 0.0),  # orange
]
colors = [adjust_luminance(c, target_lum=60) for c in base_colors]

# Generate the blob shape once
fixed_blob_path = generate_blob_path(seed=123)

# --- Drawing function ---
def draw_shape(color, shape_type, shape_id):
    fig, ax = plt.subplots(figsize=(2, 2), dpi=128)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if shape_type == "circle":
        ax.add_patch(Circle((0.5, 0.5), 0.3, color=color))

    elif shape_type == "square":
        ax.add_patch(Rectangle((0.2, 0.2), 0.6, 0.6, color=color))

    elif shape_type == "blob":
        ax.add_patch(PathPatch(fixed_blob_path, facecolor=color))

    filename = f"{shape_type}_{shape_id + 1}.png"
    fig.savefig(
        os.path.join(output_dir, filename),
        bbox_inches="tight",
        pad_inches=0,
        transparent=True
    )
    plt.close(fig)

# --- Generate images ---
for shape_type in ["circle", "square", "blob"]:
    for i, color in enumerate(colors):
        draw_shape(color, shape_type, i)

print(f"✅ Done! Images saved in '{output_dir}'")