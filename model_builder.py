"""
PyAnsys Model Builder for Substrate + Bump layer + Chip Structure
Uses bottom-up extrusion approach for robust mapped mesh generation

Algorithm:
1. Create bottom area and slice for chip region
2. Generate 2D mesh on bottom area
3. Extrude mesh upward layer by layer (substrate -> bump layer -> chip)
4. Assign materials to elements based on location
5. Merge nodes for connectivity

Author: Auto-generated
"""

import os
import numpy as np
from pathlib import Path

from ansys.mapdl.core import launch_mapdl

from config import SUBSTRATE, BUMP, CHIP, MESH, MATERIALS


class BumpModelBuilder:
    """
    Class to build a Substrate + Bump layer + Chip model using PyMAPDL
    with bottom-up extrusion for mapped mesh generation
    """

    def __init__(self, mapdl=None, working_dir=None):
        """
        Initialize the model builder
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

        # Ignore non-critical MAPDL warnings/errors
        self.mapdl.ignore_errors = True

        self.bump_coordinates = []
        self.material_ids = {}

        # Track z-coordinates
        self.current_z = 0.0
        self.substrate_top_z = 0.0
        self.bump_layer_top_z = 0.0

        # Chip region boundaries
        self.chip_x_min = CHIP["offset_x"]
        self.chip_x_max = CHIP["offset_x"] + CHIP["length_x"]
        self.chip_y_min = CHIP["offset_y"]
        self.chip_y_max = CHIP["offset_y"] + CHIP["length_y"]

    def clear_model(self):
        """Clear all existing geometry and start fresh"""
        self.mapdl.clear()
        self.mapdl.prep7()

    def load_bump_coordinates(self, filepath=None):
        """Load bump coordinates from a text file"""
        if filepath is None:
            filepath = BUMP["coordinate_file"]

        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Bump coordinates file not found: {filepath}")

        self.bump_coordinates = []

        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                parts = line.split(',')
                if len(parts) >= 2:
                    x = float(parts[0].strip())
                    y = float(parts[1].strip())
                    self.bump_coordinates.append((x, y))

        print(f"Loaded {len(self.bump_coordinates)} bump coordinates")
        return self.bump_coordinates

    def define_materials(self):
        """Define all material properties in MAPDL"""
        print("\n--- Defining Materials ---")
        mat_id = 1

        for mat_name, mat_props in MATERIALS.items():
            self.mapdl.mp("EX", mat_id, mat_props["E"])
            self.mapdl.mp("NUXY", mat_id, mat_props["nu"])
            self.mapdl.mp("DENS", mat_id, mat_props["density"])
            self.mapdl.mp("ALPX", mat_id, mat_props["CTE"])
            self.material_ids[mat_name] = mat_id
            print(f"  Material {mat_id}: {mat_name} (E={mat_props['E']} MPa)")
            mat_id += 1

        print(f"Total materials defined: {len(self.material_ids)}")

    def set_element_type(self):
        """Set element types for 2D and 3D meshing"""
        print("\n--- Setting Element Types ---")

        # 2D element for area mesh (will be deleted after extrusion)
        self.mapdl.et(1, "MESH200", 7)  # 2D quadrilateral for mesh seeding
        print("  ET 1: MESH200 (2D quad for meshing)")

        # 3D element for volume mesh
        element_type = MESH["element_type"]
        self.mapdl.et(2, element_type)
        print(f"  ET 2: {element_type} (3D hexahedral)")

    def create_base_area_with_chip_region(self):
        """
        Create bottom area (substrate footprint) with chip region sliced out
        This allows independent extrusion of chip area vs surrounding area
        """
        print("\n--- Creating Base Area with Chip Region ---")

        sub_lx = SUBSTRATE["length_x"]
        sub_ly = SUBSTRATE["length_y"]

        # Create full substrate area at z=0
        self.mapdl.rectng(0, sub_lx, 0, sub_ly)
        print(f"  Created substrate area: {sub_lx} x {sub_ly} mm")

        # Create chip region area (to be used for slicing)
        self.mapdl.rectng(self.chip_x_min, self.chip_x_max,
                         self.chip_y_min, self.chip_y_max)
        print(f"  Created chip region: [{self.chip_x_min}, {self.chip_x_max}] x "
              f"[{self.chip_y_min}, {self.chip_y_max}] mm")

        # Overlap/slice the areas to create shared boundaries
        self.mapdl.allsel()
        self.mapdl.aovlap("ALL")
        print("  Areas overlapped - chip region boundaries created")

        # Get resulting areas
        self.mapdl.allsel()

    def mesh_base_area(self):
        """Generate 2D mesh on the base area"""
        print("\n--- Meshing Base Area ---")

        elem_size = MESH["element_size"]

        self.mapdl.allsel()

        # Set element type to 2D mesh seeding element
        self.mapdl.type(1)

        # Set element size
        self.mapdl.esize(elem_size)
        print(f"  Element size: {elem_size} mm")

        # Set mapped mesh
        self.mapdl.mshape(0, "2D")  # Quad elements
        self.mapdl.mshkey(1)  # Mapped mesh

        # Mesh all areas
        self.mapdl.amesh("ALL")

        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node
        print(f"  2D mesh generated: {num_elements} elements, {num_nodes} nodes")

    def extrude_substrate_layers(self):
        """Extrude substrate layers from base mesh"""
        print("\n--- Extruding Substrate Layers ---")

        self.current_z = 0.0

        # Switch to 3D element type
        self.mapdl.type(2)

        for i, layer in enumerate(SUBSTRATE["layers"]):
            thickness = layer["thickness"]
            mat_name = layer["material"]
            mat_id = self.material_ids[mat_name]

            # Set material for this extrusion
            self.mapdl.mat(mat_id)

            # Calculate number of divisions based on element size
            elem_size = MESH["element_size"]
            n_div = max(1, int(round(thickness / elem_size)))

            # Select all elements at current z level
            self.mapdl.allsel()
            self.mapdl.esel("S", "CENT", "Z", self.current_z - 0.001, self.current_z + 0.001)

            # Extrude in z direction
            # VEXT: extrude selected elements
            self.mapdl.vext("ALL", dx=0, dy=0, dz=thickness)

            z_bottom = self.current_z
            self.current_z += thickness

            print(f"  {layer['name']}: Mat {mat_id}, z=[{z_bottom:.4f}, {self.current_z:.4f}] mm, "
                  f"{n_div} div")

        self.substrate_top_z = self.current_z
        print(f"  Substrate top z: {self.substrate_top_z:.4f} mm")

    def extrude_bump_layer(self):
        """Extrude bump layer only under chip area"""
        print("\n--- Extruding Bump Layer ---")

        height = BUMP["height"]
        air_mat_id = self.material_ids[BUMP["air_material"]]

        # Select elements in chip region at substrate top
        self.mapdl.allsel()
        self.mapdl.esel("S", "CENT", "Z", self.substrate_top_z - 0.001,
                       self.substrate_top_z + 0.001)
        self.mapdl.esel("R", "CENT", "X", self.chip_x_min, self.chip_x_max)
        self.mapdl.esel("R", "CENT", "Y", self.chip_y_min, self.chip_y_max)

        # Set air material (default for bump layer, will modify bump elements later)
        self.mapdl.mat(air_mat_id)

        # Extrude
        self.mapdl.vext("ALL", dx=0, dy=0, dz=height)

        self.bump_layer_top_z = self.substrate_top_z + height
        print(f"  Bump layer: z=[{self.substrate_top_z:.4f}, {self.bump_layer_top_z:.4f}] mm")
        print(f"  Initial material: Air (Mat {air_mat_id})")

    def extrude_chip(self):
        """Extrude chip on top of bump layer"""
        print("\n--- Extruding Chip ---")

        thickness = CHIP["thickness"]
        mat_name = CHIP["material"]
        mat_id = self.material_ids[mat_name]

        # Select elements in chip region at bump layer top
        self.mapdl.allsel()
        self.mapdl.esel("S", "CENT", "Z", self.bump_layer_top_z - 0.001,
                       self.bump_layer_top_z + 0.001)
        self.mapdl.esel("R", "CENT", "X", self.chip_x_min, self.chip_x_max)
        self.mapdl.esel("R", "CENT", "Y", self.chip_y_min, self.chip_y_max)

        # Set chip material
        self.mapdl.mat(mat_id)

        # Extrude
        self.mapdl.vext("ALL", dx=0, dy=0, dz=thickness)

        chip_top_z = self.bump_layer_top_z + thickness
        print(f"  Chip: Mat {mat_id} ({mat_name}), z=[{self.bump_layer_top_z:.4f}, {chip_top_z:.4f}] mm")

    def cleanup_2d_elements(self):
        """Remove 2D seed elements, keep only 3D elements"""
        print("\n--- Cleaning Up 2D Elements ---")

        # Select elements with ET=1 (2D elements)
        self.mapdl.esel("S", "TYPE", "", 1)
        num_2d = self.mapdl.mesh.n_elem

        if num_2d > 0:
            self.mapdl.edele("ALL")
            print(f"  Deleted {num_2d} 2D seed elements")

        self.mapdl.allsel()

    def merge_nodes(self):
        """Merge coincident nodes for connectivity"""
        print("\n--- Merging Nodes ---")

        self.mapdl.allsel()

        # Merge nodes with small tolerance
        self.mapdl.nummrg("NODE", 1e-6)
        self.mapdl.numcmp("NODE")  # Compress node numbering

        print("  Nodes merged and compressed")

    def assign_bump_materials(self):
        """Assign bump material to elements at bump coordinates"""
        print("\n--- Assigning Bump Materials by Element Location ---")

        if not self.bump_coordinates:
            print("  Warning: No bump coordinates loaded")
            return

        bump_mat_id = self.material_ids[BUMP["material"]]
        air_mat_id = self.material_ids[BUMP["air_material"]]

        z_bottom = self.substrate_top_z
        z_top = self.bump_layer_top_z

        # Get bump dimensions
        half_wx = BUMP["width_x"] / 2.0
        half_wy = BUMP["width_y"] / 2.0

        # Select 3D elements in bump layer by location
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)  # Only 3D elements
        self.mapdl.esel("R", "CENT", "Z", z_bottom + 0.001, z_top - 0.001)

        # Get element list
        bump_layer_elements = self.mapdl.mesh.enum.copy()
        print(f"  Total elements in bump layer: {len(bump_layer_elements)}")

        if len(bump_layer_elements) == 0:
            print("  Warning: No elements found in bump layer")
            return

        # Assign materials based on element centroid
        bump_elem_count = 0

        for elem_id in bump_layer_elements:
            # Get element centroid
            self.mapdl.esel("S", "ELEM", "", elem_id)

            cx = float(self.mapdl.get("cx", "ELEM", elem_id, "CENT", "X"))
            cy = float(self.mapdl.get("cy", "ELEM", elem_id, "CENT", "Y"))

            # Check if element centroid is within any bump region
            is_bump = False
            for (bx, by) in self.bump_coordinates:
                if (bx - half_wx <= cx <= bx + half_wx and
                    by - half_wy <= cy <= by + half_wy):
                    is_bump = True
                    break

            if is_bump:
                self.mapdl.emodif(elem_id, "MAT", bump_mat_id)
                bump_elem_count += 1

        air_elem_count = len(bump_layer_elements) - bump_elem_count
        self.mapdl.allsel()

        print(f"  Bump elements: {bump_elem_count}")
        print(f"  Air elements: {air_elem_count}")

    def save_model(self, filename="bump_model"):
        """Save the model database (.db) and CDB file (.cdb)"""
        print(f"\n--- Saving Model as '{filename}' ---")

        self.mapdl.allsel()

        # Save MAPDL database (.db)
        self.mapdl.save(filename)
        db_path = os.path.join(self.working_dir, filename + '.db')
        print(f"  Database: {db_path}")

        # Save CDB file
        self.mapdl.cdwrite("ALL", filename, "cdb")
        cdb_path = os.path.join(self.working_dir, filename + '.cdb')
        print(f"  CDB file: {cdb_path}")

        return db_path, cdb_path

    def get_model_summary(self):
        """Print a summary of the model"""
        print("\n" + "=" * 60)
        print("MODEL SUMMARY")
        print("=" * 60)

        # Mesh statistics
        self.mapdl.allsel()
        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node

        print(f"\nMesh Statistics:")
        print(f"  Total elements: {num_elements}")
        print(f"  Total nodes: {num_nodes}")

        print(f"\nSubstrate (PCB):")
        print(f"  Size: {SUBSTRATE['length_x']} x {SUBSTRATE['length_y']} mm")
        print(f"  Layers: {len(SUBSTRATE['layers'])}")
        total_thickness = sum(layer['thickness'] for layer in SUBSTRATE['layers'])
        print(f"  Total thickness: {total_thickness:.4f} mm")

        print(f"\nBump Layer:")
        print(f"  Size: {CHIP['length_x']} x {CHIP['length_y']} mm (under chip)")
        print(f"  Height: {BUMP['height']} mm")
        print(f"  Bump count: {len(self.bump_coordinates)}")
        print(f"  Bump size: {BUMP['width_x']} x {BUMP['width_y']} mm")

        print(f"\nChip:")
        print(f"  Size: {CHIP['length_x']} x {CHIP['length_y']} x {CHIP['thickness']} mm")

        print(f"\nZ-coordinates:")
        print(f"  Substrate: 0 to {self.substrate_top_z:.4f} mm")
        print(f"  Bump layer: {self.substrate_top_z:.4f} to {self.bump_layer_top_z:.4f} mm")
        chip_top = self.bump_layer_top_z + CHIP['thickness']
        print(f"  Chip: {self.bump_layer_top_z:.4f} to {chip_top:.4f} mm")
        print(f"  Total height: {chip_top:.4f} mm")

        print("\n" + "=" * 60)

    def build_full_model(self, coordinate_file=None, save=True):
        """Build the complete model using bottom-up extrusion"""
        print("=" * 60)
        print("BUILDING SUBSTRATE + BUMP LAYER + CHIP MODEL")
        print("(Bottom-up Extrusion Approach)")
        print("=" * 60)

        # Clear and initialize
        self.clear_model()

        # Load bump coordinates
        self.load_bump_coordinates(coordinate_file)

        # Define materials
        self.define_materials()

        # Set element types
        self.set_element_type()

        # Create base area with chip region marked
        self.create_base_area_with_chip_region()

        # Mesh base area (2D)
        self.mesh_base_area()

        # Extrude layers bottom-up
        self.extrude_substrate_layers()
        self.extrude_bump_layer()
        self.extrude_chip()

        # Cleanup 2D elements
        self.cleanup_2d_elements()

        # Merge nodes
        self.merge_nodes()

        # Assign bump/air materials
        self.assign_bump_materials()

        # Save if requested
        if save:
            self.save_model()

        # Print summary
        self.get_model_summary()

        return self.mapdl

    def close(self):
        """Close the MAPDL instance"""
        if self.mapdl is not None:
            self.mapdl.exit()
            print("MAPDL instance closed")


def main():
    """Main function to demonstrate model building"""

    builder = BumpModelBuilder()

    try:
        mapdl = builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            save=True
        )

        print("\nModel building complete!")

    except Exception as e:
        print(f"Error during model building: {e}")
        raise

    return builder


if __name__ == "__main__":
    builder = main()
