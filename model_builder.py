"""
PyAnsys Model Builder for Substrate + Bump layer + Chip Structure
Uses ansys-mapdl-core (PyMAPDL) for geometry creation and meshing

Author: Auto-generated
Date: 2024
"""

import os
import numpy as np
from pathlib import Path

# PyAnsys imports
from ansys.mapdl.core import launch_mapdl

# Local configuration
from config import SUBSTRATE, BUMP, CHIP, UNDERFILL, MESH, ANALYSIS


class BumpModelBuilder:
    """
    Class to build a Substrate + Bump layer + Chip model using PyMAPDL
    """

    def __init__(self, mapdl=None, working_dir=None):
        """
        Initialize the model builder

        Parameters
        ----------
        mapdl : ansys.mapdl.core.Mapdl, optional
            Existing MAPDL instance. If None, a new one will be launched.
        working_dir : str, optional
            Working directory for MAPDL files
        """
        self.working_dir = working_dir or os.path.join(os.getcwd(), "mapdl_files")
        os.makedirs(self.working_dir, exist_ok=True)

        if mapdl is None:
            self.mapdl = launch_mapdl(
                run_location=self.working_dir,
                override=True,
                loglevel="WARNING"
            )
        else:
            self.mapdl = mapdl

        self.bump_coordinates = []
        self.material_ids = {}
        self.volume_ids = {
            "substrate": [],
            "bump": [],
            "chip": [],
            "underfill": []
        }

        # Track z-coordinates for layer stacking
        self.current_z = 0.0
        self.substrate_top_z = 0.0
        self.bump_top_z = 0.0

    def clear_model(self):
        """Clear all existing geometry and start fresh"""
        self.mapdl.clear()
        self.mapdl.prep7()

    def load_bump_coordinates(self, filepath=None):
        """
        Load bump coordinates from a text file

        Parameters
        ----------
        filepath : str, optional
            Path to bump coordinates file. Uses config default if not specified.
        """
        if filepath is None:
            filepath = BUMP["coordinate_file"]

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Bump coordinates file not found: {filepath}")

        self.bump_coordinates = []

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue

                # Parse x, y coordinates
                parts = line.split(',')
                if len(parts) >= 2:
                    x = float(parts[0].strip())
                    y = float(parts[1].strip())
                    self.bump_coordinates.append((x, y))

        print(f"Loaded {len(self.bump_coordinates)} bump coordinates")
        return self.bump_coordinates

    def define_materials(self):
        """Define all material properties in MAPDL"""
        mat_id = 1

        # Substrate layer materials
        for layer in SUBSTRATE["layers"]:
            mat = layer["material"]
            self.mapdl.mp("EX", mat_id, mat["E"])
            self.mapdl.mp("NUXY", mat_id, mat["nu"])
            self.mapdl.mp("DENS", mat_id, mat["density"])
            self.mapdl.mp("ALPX", mat_id, mat["CTE"])
            self.material_ids[mat["name"]] = mat_id
            print(f"Material {mat_id}: {mat['name']} (E={mat['E']} MPa)")
            mat_id += 1

        # Bump material
        mat = BUMP["material"]
        if mat["name"] not in self.material_ids:
            self.mapdl.mp("EX", mat_id, mat["E"])
            self.mapdl.mp("NUXY", mat_id, mat["nu"])
            self.mapdl.mp("DENS", mat_id, mat["density"])
            self.mapdl.mp("ALPX", mat_id, mat["CTE"])
            self.material_ids[mat["name"]] = mat_id
            print(f"Material {mat_id}: {mat['name']} (E={mat['E']} MPa)")
            mat_id += 1

        # Chip material
        mat = CHIP["material"]
        if mat["name"] not in self.material_ids:
            self.mapdl.mp("EX", mat_id, mat["E"])
            self.mapdl.mp("NUXY", mat_id, mat["nu"])
            self.mapdl.mp("DENS", mat_id, mat["density"])
            self.mapdl.mp("ALPX", mat_id, mat["CTE"])
            self.material_ids[mat["name"]] = mat_id
            print(f"Material {mat_id}: {mat['name']} (E={mat['E']} MPa)")
            mat_id += 1

        # Underfill material (if enabled)
        if UNDERFILL["enabled"]:
            mat = UNDERFILL["material"]
            if mat["name"] not in self.material_ids:
                self.mapdl.mp("EX", mat_id, mat["E"])
                self.mapdl.mp("NUXY", mat_id, mat["nu"])
                self.mapdl.mp("DENS", mat_id, mat["density"])
                self.mapdl.mp("ALPX", mat_id, mat["CTE"])
                self.material_ids[mat["name"]] = mat_id
                print(f"Material {mat_id}: {mat['name']} (E={mat['E']} MPa)")
                mat_id += 1

        print(f"\nTotal materials defined: {len(self.material_ids)}")

    def create_substrate(self):
        """Create substrate layers as stacked volumes"""
        print("\n--- Creating Substrate ---")

        lx = SUBSTRATE["length_x"]
        ly = SUBSTRATE["length_y"]

        self.current_z = 0.0

        for i, layer in enumerate(SUBSTRATE["layers"]):
            thickness = layer["thickness"]
            z_bottom = self.current_z
            z_top = z_bottom + thickness

            # Create a block volume for the layer
            # BLOCK: x1, x2, y1, y2, z1, z2
            self.mapdl.block(0, lx, 0, ly, z_bottom, z_top)
            vol_num = self.mapdl.geometry.vnum[-1]  # Get the last created volume number

            self.volume_ids["substrate"].append({
                "volume": vol_num,
                "layer_name": layer["name"],
                "material": layer["material"]["name"],
                "z_bottom": z_bottom,
                "z_top": z_top
            })

            print(f"  Layer '{layer['name']}': Volume {vol_num}, "
                  f"z=[{z_bottom:.4f}, {z_top:.4f}] mm, thickness={thickness} mm")

            self.current_z = z_top

        self.substrate_top_z = self.current_z
        print(f"Substrate top z: {self.substrate_top_z} mm")

    def create_bumps(self):
        """Create cylindrical bumps at specified coordinates"""
        print("\n--- Creating Bumps ---")

        if not self.bump_coordinates:
            print("Warning: No bump coordinates loaded. Call load_bump_coordinates() first.")
            return

        diameter = BUMP["diameter"]
        radius = diameter / 2.0
        height = BUMP["height"]

        z_bottom = self.substrate_top_z
        z_top = z_bottom + height

        for i, (x, y) in enumerate(self.bump_coordinates):
            # Check if bump is within chip area (bumps should be under the chip)
            chip_x_min = CHIP["offset_x"]
            chip_x_max = CHIP["offset_x"] + CHIP["length_x"]
            chip_y_min = CHIP["offset_y"]
            chip_y_max = CHIP["offset_y"] + CHIP["length_y"]

            if not (chip_x_min <= x <= chip_x_max and chip_y_min <= y <= chip_y_max):
                print(f"  Warning: Bump {i+1} at ({x}, {y}) is outside chip area, skipping")
                continue

            # Create cylinder: CYLIND, rad1, rad2, z1, z2, theta1, theta2
            # We use a working plane approach for positioning
            # Move to bump center and create cylinder
            self.mapdl.wpoffs(x, y, z_bottom)
            self.mapdl.cylind(radius, 0, 0, height, 0, 360)
            self.mapdl.wpoffs(-x, -y, -z_bottom)  # Reset working plane

            vol_num = self.mapdl.geometry.vnum[-1]

            self.volume_ids["bump"].append({
                "volume": vol_num,
                "x": x,
                "y": y,
                "z_bottom": z_bottom,
                "z_top": z_top
            })

            if (i + 1) % 10 == 0 or i == len(self.bump_coordinates) - 1:
                print(f"  Created {i + 1}/{len(self.bump_coordinates)} bumps")

        self.bump_top_z = z_top
        print(f"Total bumps created: {len(self.volume_ids['bump'])}")
        print(f"Bump top z: {self.bump_top_z} mm")

    def create_chip(self):
        """Create the chip volume on top of bumps"""
        print("\n--- Creating Chip ---")

        lx = CHIP["length_x"]
        ly = CHIP["length_y"]
        thickness = CHIP["thickness"]
        offset_x = CHIP["offset_x"]
        offset_y = CHIP["offset_y"]

        z_bottom = self.bump_top_z
        z_top = z_bottom + thickness

        # Create chip block
        self.mapdl.block(
            offset_x, offset_x + lx,
            offset_y, offset_y + ly,
            z_bottom, z_top
        )

        vol_num = self.mapdl.geometry.vnum[-1]

        self.volume_ids["chip"].append({
            "volume": vol_num,
            "z_bottom": z_bottom,
            "z_top": z_top
        })

        print(f"  Chip: Volume {vol_num}")
        print(f"  Position: x=[{offset_x}, {offset_x + lx}], "
              f"y=[{offset_y}, {offset_y + ly}], "
              f"z=[{z_bottom:.4f}, {z_top:.4f}] mm")

    def glue_volumes(self):
        """Glue all volumes together for proper mesh connectivity"""
        print("\n--- Gluing Volumes ---")

        # Select all volumes
        self.mapdl.allsel()
        self.mapdl.vsel("ALL")

        # Glue volumes (VGLUE creates shared areas between touching volumes)
        self.mapdl.vglue("ALL")

        print("All volumes glued together")

    def assign_materials_to_volumes(self):
        """Assign material properties to each volume"""
        print("\n--- Assigning Materials to Volumes ---")

        # Substrate layers
        for vol_info in self.volume_ids["substrate"]:
            mat_id = self.material_ids[vol_info["material"]]
            self.mapdl.vsel("S", "VOLU", "", vol_info["volume"])
            self.mapdl.vatt(mat_id)
            print(f"  Substrate layer '{vol_info['layer_name']}': Material ID {mat_id}")

        # Bumps
        bump_mat_id = self.material_ids[BUMP["material"]["name"]]
        for vol_info in self.volume_ids["bump"]:
            self.mapdl.vsel("S", "VOLU", "", vol_info["volume"])
            self.mapdl.vatt(bump_mat_id)
        print(f"  Bumps: Material ID {bump_mat_id}")

        # Chip
        chip_mat_id = self.material_ids[CHIP["material"]["name"]]
        for vol_info in self.volume_ids["chip"]:
            self.mapdl.vsel("S", "VOLU", "", vol_info["volume"])
            self.mapdl.vatt(chip_mat_id)
        print(f"  Chip: Material ID {chip_mat_id}")

        self.mapdl.allsel()

    def set_element_type(self):
        """Set element type for meshing"""
        print("\n--- Setting Element Type ---")

        element_type = MESH["element_type"]

        if element_type == "SOLID186":
            self.mapdl.et(1, "SOLID186")
            print(f"Element type: SOLID186 (20-node hexahedral)")
        elif element_type == "SOLID187":
            self.mapdl.et(1, "SOLID187")
            print(f"Element type: SOLID187 (10-node tetrahedral)")
        else:
            self.mapdl.et(1, element_type)
            print(f"Element type: {element_type}")

    def mesh_model(self):
        """Generate mesh for the model"""
        print("\n--- Meshing Model ---")

        # Set global element size
        global_size = MESH["element_size"]
        self.mapdl.esize(global_size)
        print(f"Global element size: {global_size} mm")

        # Refine mesh around bumps if specified
        if MESH.get("bump_refinement"):
            refine_size = MESH["bump_refinement"]
            print(f"Bump refinement size: {refine_size} mm")

            # Select bump volumes and refine
            for vol_info in self.volume_ids["bump"]:
                self.mapdl.vsel("S", "VOLU", "", vol_info["volume"])
                self.mapdl.lesize("ALL", refine_size)

        # Select all and mesh
        self.mapdl.allsel()
        self.mapdl.vmesh("ALL")

        # Get mesh statistics
        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node

        print(f"Mesh generated: {num_elements} elements, {num_nodes} nodes")

    def save_model(self, filename="bump_model"):
        """Save the model database"""
        print(f"\n--- Saving Model as '{filename}' ---")

        self.mapdl.save(filename)
        print(f"Model saved to: {os.path.join(self.working_dir, filename + '.db')}")

    def plot_model(self, show_mesh=False):
        """Plot the model geometry"""
        print("\n--- Plotting Model ---")

        if show_mesh:
            self.mapdl.eplot(
                vtk=True,
                show_edges=True,
                title="Substrate + Bump + Chip Model (Mesh)"
            )
        else:
            self.mapdl.vplot(
                vtk=True,
                show_edges=True,
                title="Substrate + Bump + Chip Model (Geometry)"
            )

    def get_model_summary(self):
        """Print a summary of the model"""
        print("\n" + "=" * 60)
        print("MODEL SUMMARY")
        print("=" * 60)

        print(f"\nSubstrate:")
        print(f"  Size: {SUBSTRATE['length_x']} x {SUBSTRATE['length_y']} mm")
        print(f"  Layers: {len(SUBSTRATE['layers'])}")
        total_thickness = sum(layer['thickness'] for layer in SUBSTRATE['layers'])
        print(f"  Total thickness: {total_thickness} mm")

        print(f"\nBumps:")
        print(f"  Total count: {len(self.volume_ids['bump'])}")
        print(f"  Diameter: {BUMP['diameter']} mm")
        print(f"  Height: {BUMP['height']} mm")

        print(f"\nChip:")
        print(f"  Size: {CHIP['length_x']} x {CHIP['length_y']} x {CHIP['thickness']} mm")
        print(f"  Position: offset ({CHIP['offset_x']}, {CHIP['offset_y']}) mm")

        print(f"\nZ-coordinates:")
        print(f"  Substrate: 0 to {self.substrate_top_z} mm")
        print(f"  Bumps: {self.substrate_top_z} to {self.bump_top_z} mm")
        if self.volume_ids['chip']:
            chip_top = self.bump_top_z + CHIP['thickness']
            print(f"  Chip: {self.bump_top_z} to {chip_top} mm")
            print(f"  Total height: {chip_top} mm")

        print("\n" + "=" * 60)

    def build_full_model(self, coordinate_file=None, mesh=True, save=True, plot=False):
        """
        Build the complete model in one call

        Parameters
        ----------
        coordinate_file : str, optional
            Path to bump coordinates file
        mesh : bool, optional
            Whether to mesh the model (default True)
        save : bool, optional
            Whether to save the model (default True)
        plot : bool, optional
            Whether to plot the model (default False)
        """
        print("=" * 60)
        print("BUILDING SUBSTRATE + BUMP + CHIP MODEL")
        print("=" * 60)

        # Clear and initialize
        self.clear_model()

        # Load bump coordinates
        self.load_bump_coordinates(coordinate_file)

        # Define materials
        self.define_materials()

        # Set element type
        self.set_element_type()

        # Create geometry
        self.create_substrate()
        self.create_bumps()
        self.create_chip()

        # Glue volumes
        self.glue_volumes()

        # Assign materials
        self.assign_materials_to_volumes()

        # Mesh if requested
        if mesh:
            self.mesh_model()

        # Save if requested
        if save:
            self.save_model()

        # Print summary
        self.get_model_summary()

        # Plot if requested
        if plot:
            self.plot_model(show_mesh=mesh)

        return self.mapdl

    def close(self):
        """Close the MAPDL instance"""
        if self.mapdl is not None:
            self.mapdl.exit()
            print("MAPDL instance closed")


def main():
    """Main function to demonstrate model building"""

    # Create model builder
    builder = BumpModelBuilder()

    try:
        # Build the full model
        mapdl = builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            mesh=True,
            save=True,
            plot=False  # Set to True if you have VTK visualization available
        )

        # The MAPDL instance can be used for further analysis
        print("\nModel building complete!")
        print("You can now use the mapdl instance for analysis.")

    except Exception as e:
        print(f"Error during model building: {e}")
        raise

    finally:
        # Optionally close MAPDL
        # builder.close()
        pass

    return builder


if __name__ == "__main__":
    builder = main()
