import matplotlib.pyplot as plt
import numpy as np
import os

def generate_max_complexity_polygon(num_sides=18, distortion=0.7, concavity=0.8, jaggedness=0.8):
    """Generate a highly complex irregular polygon."""
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
    
    return points

def save_max_complexity_shapes(num_shapes=10):
    """Generate and save multiple shapes inside 'generated_shapes' directory."""
    
    # Ensure the directory exists
    output_dir = "generated_shapes"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for i in range(1, num_shapes + 1):
        fig, ax = plt.subplots()
        points = generate_max_complexity_polygon()
        shape = plt.Polygon(points, fill=True, color='black')
        ax.add_patch(shape)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect('equal')
        ax.axis('off')

        # Save the shape inside the 'generated_shapes' folder
        filename = os.path.join(output_dir, f"shape_{i:02d}.png")
        plt.savefig(filename, bbox_inches='tight', pad_inches=0.1)
        plt.close()
        print(f"Saved: {filename}")

# Run script to generate and save 10 max complexity shapes
save_max_complexity_shapes()
