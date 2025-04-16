import matplotlib.pyplot as plt
import numpy as np
import os
import cv2
import pandas as pd
import random

# Function to generate an irregular polygon with complexity parameters
def generate_complex_polygon(num_sides, distortion, concavity, jaggedness, scale=0.75):
    angles = np.sort(np.random.rand(num_sides) * 2 * np.pi)
    radii = 0.5 + np.random.rand(num_sides) * distortion
    points = [(0.5 + r*np.cos(a), 0.5 + r*np.sin(a)) for r, a in zip(radii, angles)]

    num_concave = int(num_sides * concavity)
    concave_indices = np.random.choice(num_sides, num_concave, replace=False)
    for i in concave_indices:
        points[i] = ((points[i][0] + 0.5) / 2, (points[i][1] + 0.5) / 2)

    num_jagged = int(num_sides * jaggedness)
    jagged_indices = np.random.choice(num_sides, num_jagged, replace=False)
    for i in jagged_indices:
        points[i] = (points[i][0] + np.random.uniform(-0.05, 0.05),
                     points[i][1] + np.random.uniform(-0.05, 0.05))

    points = [(0.5 + (x - 0.5) * scale, 0.5 + (y - 0.5) * scale) for x, y in points]
    return points

def compute_rms_contrast(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    mean_intensity = np.mean(img)
    return np.sqrt(np.mean((img - mean_intensity) ** 2))

def generate_incremental_shapes(n_shapes=10, output_dir="generated_shapes", scale=0.75):
    os.makedirs(output_dir, exist_ok=True)
    shape_data = []

    # Define linear increments for parameters
    sides_range = np.linspace(8, 24, n_shapes, dtype=int)
    distortion_range = np.linspace(0.2, 0.8, n_shapes)
    concavity_range = np.linspace(0.2, 0.9, n_shapes)
    jaggedness_range = np.linspace(0.2, 0.9, n_shapes)

    for i in range(n_shapes):
        num_sides = sides_range[i]
        distortion = distortion_range[i]
        concavity = concavity_range[i]
        jaggedness = jaggedness_range[i]

        fig, ax = plt.subplots(figsize=(5, 5), dpi=300)
        points = generate_complex_polygon(num_sides, distortion, concavity, jaggedness, scale)
        polygon = plt.Polygon(points, fill=True, color='black')
        ax.add_patch(polygon)

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')

        filename = os.path.join(output_dir, f"shape_{i+1:02d}.png")
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.2)
        plt.close()

        # Contrast adjustment
        contrast = compute_rms_contrast(filename)
        desired_contrast = 120
        max_iterations = 20
        iterations = 0

        while (contrast < 115 or contrast > 125) and iterations < max_iterations:
            img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            mean_intensity = np.mean(img)
            alpha = desired_contrast / contrast
            adjusted = np.clip((img - mean_intensity) * alpha + mean_intensity, 0, 255).astype(np.uint8)
            cv2.imwrite(filename, adjusted)
            contrast = compute_rms_contrast(filename)
            iterations += 1

        shape_data.append({
            "Filename": filename,
            "Num Sides": num_sides,
            "Distortion": round(distortion, 2),
            "Concavity": round(concavity, 2),
            "Jaggedness": round(jaggedness, 2),
            "RMS Contrast": round(contrast, 2)
        })

        print(f"Saved: {filename}, RMS Contrast: {contrast:.2f}")

    df = pd.DataFrame(shape_data)
    df.to_excel(os.path.join(output_dir, "shape_metadata.xlsx"), index=False)
    print("Metadata saved.")

if __name__ == "__main__":
    generate_incremental_shapes()
