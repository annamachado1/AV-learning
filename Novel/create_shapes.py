import matplotlib.pyplot as plt
import numpy as np
import os
import random
import cv2
import pandas as pd
from PIL import Image

# Function to generate an irregular polygon with complexity adjustments 
def generate_max_complexity_polygon(num_sides=18, distortion=0.7, concavity=0.8, jaggedness=0.8, scale=0.75):
    """Generate a highly complex irregular polygon within a safe region (with padding)."""
    angles = np.sort(np.random.rand(num_sides) * 2 * np.pi)
    radii = 0.5 + np.random.rand(num_sides) * distortion
    points = [(0.5 + r*np.cos(a), 0.5 + r*np.sin(a)) for r, a in zip(radii, angles)]
    
    # Introduce concavities (pulling points inward)
    num_concave = int(num_sides * concavity)
    concave_indices = np.random.choice(num_sides, num_concave, replace=False)
    for i in concave_indices:
        points[i] = ((points[i][0] + 0.5) / 2, (points[i][1] + 0.5) / 2)

    # Introduce jaggedness (small random shifts in points)
    num_jagged = int(num_sides * jaggedness)
    jagged_indices = np.random.choice(num_sides, num_jagged, replace=False)
    for i in jagged_indices:
        points[i] = (points[i][0] + np.random.uniform(-0.05, 0.05), 
                     points[i][1] + np.random.uniform(-0.05, 0.05))
    
    # Scale down points to ensure they remain within a safe region (not touching edges)
    points = [(0.5 + (x - 0.5) * scale, 0.5 + (y - 0.5) * scale) for x, y in points]

    return points

# Function to compute RMS contrast
def compute_rms_contrast(image_path):
    """Compute RMS contrast of a shape image."""
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)  # Read image in grayscale
    mean_intensity = np.mean(img)
    contrast_rms = np.sqrt(np.mean((img - mean_intensity) ** 2))
    return contrast_rms

# Function to generate and save shapes while logging all parameters
def save_max_complexity_shapes(num_shapes=10, seed_value=42, scale=0.75):
    """Generate and save multiple shapes inside 'generated_shapes' directory, ensuring white borders."""
    
    # Set fixed random seed for reproducibility
    np.random.seed(seed_value)
    random.seed(seed_value)

    # Ensure the directory exists
    output_dir = "generated_shapes"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    shape_data = []  # Store parameters and contrast info

    for i in range(1, num_shapes + 1):
        num_sides = random.randint(12, 24)  # Randomize sides (between 12 and 24)
        distortion = random.uniform(0.5, 0.9)
        concavity = random.uniform(0.6, 0.9)
        jaggedness = random.uniform(0.6, 0.9)

        fig, ax = plt.subplots(figsize=(5, 5), dpi=300)  # High DPI for clarity
        points = generate_max_complexity_polygon(num_sides, distortion, concavity, jaggedness, scale)
        shape = plt.Polygon(points, fill=True, color='black')
        ax.add_patch(shape)

        # Define padding limits
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.axis('off')  # Hide axes

        # Save the shape ensuring padding
        filename = os.path.join(output_dir, f"shape_{i:02d}.png")
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.2)  # Ensures a white border
        plt.close()

        # Compute RMS contrast
        contrast = compute_rms_contrast(filename)
        
        # Iteratively adjust contrast until it falls within the desired range [115, 125]
        desired_contrast = 120  # midpoint of desired range
        max_iterations = 20  # increased further to help ensure proper adjustment
        iterations = 0
        while (contrast < 115 or contrast > 125) and iterations < max_iterations:
            img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
            mean_intensity = np.mean(img)  # use the image's current mean
            alpha = desired_contrast / contrast
            adjusted = np.clip((img - mean_intensity) * alpha + mean_intensity, 0, 255).astype(np.uint8)
            cv2.imwrite(filename, adjusted)
            contrast = compute_rms_contrast(filename)
            iterations += 1
        if iterations == max_iterations and (contrast < 115 or contrast > 125):
            print(f"Warning: {filename} remains out of desired range after {max_iterations} iterations.")

        # Store parameters and contrast
        shape_data.append({
            "Filename": filename,
            "Num Sides": num_sides,
            "Distortion": distortion,
            "Concavity": concavity,
            "Jaggedness": jaggedness,
            "Scale": scale,
            "RMS Contrast": contrast
        })

        print(f"Saved: {filename}, RMS Contrast: {contrast:.4f}")

    return shape_data

# Generate shapes and measure contrast
shape_data = save_max_complexity_shapes()

# Save all data to an Excel file
df = pd.DataFrame(shape_data)
excel_filename = "shape_data.xlsx"
df.to_excel(excel_filename, index=False)
print(f"Shape data saved to '{excel_filename}'")

# Plot histogram of contrast values
import matplotlib.pyplot as plt
df["RMS Contrast"].hist(bins=10)
plt.xlabel("RMS Contrast")
plt.ylabel("Frequency")
plt.title("Distribution of Shape Contrast")
plt.show()
