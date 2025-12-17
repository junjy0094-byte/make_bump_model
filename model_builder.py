"""
PyAnsys Model Builder for Substrate + Bump layer + Chip Structure
Uses area extrusion (VOFFST/VEXT) approach for volume creation and meshing

Algorithm:
1. Create base areas with chip region sliced
2. Extrude areas into volumes layer by layer (VOFFST)
3. Mesh volumes with VMESH
4. Assign materials based on element z-location
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
    """

    def __init__(self, mapdl=None, working_dir=None):
        """Initialize the model builder"""
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

        # Store layer info for material assignment
        self.layer_z_ranges = []

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
        """Set element type for 3D meshing"""
        print("\n--- Setting Element Type ---")
        element_type = MESH["element_type"]
        self.mapdl.et(1, element_type)
        print(f"  ET 1: {element_type} (3D hexahedral)")

    def create_base_areas(self):
        """Create base areas at z=0 with chip region"""
        print("\n--- Creating Base Areas ---")

        sub_lx = SUBSTRATE["length_x"]
        sub_ly = SUBSTRATE["length_y"]

        # Method: Create 5 areas (4 surrounding + 1 chip region) using keypoints
        # This avoids aovlap issues

        # Define keypoints for substrate boundary
        self.mapdl.k(1, 0, 0, 0)
        self.mapdl.k(2, sub_lx, 0, 0)
        self.mapdl.k(3, sub_lx, sub_ly, 0)
        self.mapdl.k(4, 0, sub_ly, 0)

        # Define keypoints for chip region
        self.mapdl.k(5, self.chip_x_min, self.chip_y_min, 0)
        self.mapdl.k(6, self.chip_x_max, self.chip_y_min, 0)
        self.mapdl.k(7, self.chip_x_max, self.chip_y_max, 0)
        self.mapdl.k(8, self.chip_x_min, self.chip_y_max, 0)

        # Additional keypoints for surrounding areas
        self.mapdl.k(9, self.chip_x_min, 0, 0)
        self.mapdl.k(10, self.chip_x_max, 0, 0)
        self.mapdl.k(11, sub_lx, self.chip_y_min, 0)
        self.mapdl.k(12, sub_lx, self.chip_y_max, 0)
        self.mapdl.k(13, self.chip_x_max, sub_ly, 0)
        self.mapdl.k(14, self.chip_x_min, sub_ly, 0)
        self.mapdl.k(15, 0, self.chip_y_max, 0)
        self.mapdl.k(16, 0, self.chip_y_min, 0)

        # Create chip region area (center)
        self.mapdl.a(5, 6, 7, 8)
        print(f"  Created chip region area")

        # Create surrounding areas (bottom, right, top, left)
        self.mapdl.a(1, 9, 5, 16)   # bottom-left
        self.mapdl.a(9, 10, 6, 5)   # bottom-center
        self.mapdl.a(10, 2, 11, 6)  # bottom-right
        self.mapdl.a(6, 11, 12, 7)  # right
        self.mapdl.a(7, 12, 3, 13)  # top-right
        self.mapdl.a(8, 7, 13, 14)  # top-center
        self.mapdl.a(15, 8, 14, 4)  # top-left
        self.mapdl.a(16, 5, 8, 15)  # left

        self.mapdl.allsel()
        area_count = len(self.mapdl.geometry.anum)
        print(f"  Total areas created: {area_count}")
        print(f"  Substrate: {sub_lx} x {sub_ly} mm")
        print(f"  Chip region: [{self.chip_x_min}, {self.chip_x_max}] x [{self.chip_y_min}, {self.chip_y_max}] mm")

    def extrude_substrate_layers(self):
        """Extrude substrate layers from base areas"""
        print("\n--- Extruding Substrate Layers ---")

        self.current_z = 0.0
        self.layer_z_ranges = []

        for i, layer in enumerate(SUBSTRATE["layers"]):
            thickness = layer["thickness"]
            mat_name = layer["material"]
            mat_id = self.material_ids[mat_name]

            z_bottom = self.current_z
            z_top = z_bottom + thickness

            # Store layer info
            self.layer_z_ranges.append({
                "name": layer["name"],
                "mat_id": mat_id,
                "z_bottom": z_bottom,
                "z_top": z_top
            })

            # Select areas at current z level
            self.mapdl.allsel()
            self.mapdl.asel("S", "LOC", "Z", self.current_z - 0.0001, self.current_z + 0.0001)

            # Extrude areas to create volumes (VOFFST)
            self.mapdl.voffst("ALL", thickness)

            self.current_z = z_top
            print(f"  {layer['name']}: Mat {mat_id}, z=[{z_bottom:.4f}, {z_top:.4f}] mm")

        self.substrate_top_z = self.current_z
        print(f"  Substrate top z: {self.substrate_top_z:.4f} mm")

    def extrude_bump_layer(self):
        """Extrude bump layer from chip region areas"""
        print("\n--- Extruding Bump Layer ---")

        height = BUMP["height"]
        air_mat_id = self.material_ids[BUMP["air_material"]]

        z_bottom = self.substrate_top_z
        z_top = z_bottom + height

        # Store layer info
        self.layer_z_ranges.append({
            "name": "bump_layer",
            "mat_id": air_mat_id,
            "z_bottom": z_bottom,
            "z_top": z_top,
            "is_bump_layer": True
        })

        # Select only chip region area at substrate top
        self.mapdl.allsel()
        self.mapdl.asel("S", "LOC", "Z", self.substrate_top_z - 0.0001, self.substrate_top_z + 0.0001)
        self.mapdl.asel("R", "LOC", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)
        self.mapdl.asel("R", "LOC", "Y", self.chip_y_min + 0.001, self.chip_y_max - 0.001)

        # Extrude
        self.mapdl.voffst("ALL", height)

        self.bump_layer_top_z = z_top
        print(f"  Bump layer: z=[{z_bottom:.4f}, {z_top:.4f}] mm")

    def extrude_chip(self):
        """Extrude chip from bump layer top"""
        print("\n--- Extruding Chip ---")

        thickness = CHIP["thickness"]
        mat_name = CHIP["material"]
        mat_id = self.material_ids[mat_name]

        z_bottom = self.bump_layer_top_z
        z_top = z_bottom + thickness

        # Store layer info
        self.layer_z_ranges.append({
            "name": "chip",
            "mat_id": mat_id,
            "z_bottom": z_bottom,
            "z_top": z_top
        })

        # Select chip region area at bump layer top
        self.mapdl.allsel()
        self.mapdl.asel("S", "LOC", "Z", self.bump_layer_top_z - 0.0001, self.bump_layer_top_z + 0.0001)
        self.mapdl.asel("R", "LOC", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)
        self.mapdl.asel("R", "LOC", "Y", self.chip_y_min + 0.001, self.chip_y_max - 0.001)

        # Extrude
        self.mapdl.voffst("ALL", thickness)

        print(f"  Chip: Mat {mat_id}, z=[{z_bottom:.4f}, {z_top:.4f}] mm")

    def mesh_all_volumes(self):
        """Mesh all volumes"""
        print("\n--- Meshing Volumes ---")

        elem_size = MESH["element_size"]

        self.mapdl.allsel()

        # Set element type
        self.mapdl.type(1)

        # Set element size
        self.mapdl.esize(elem_size)
        print(f"  Element size: {elem_size} mm")

        # Set mesh preferences
        self.mapdl.mshape(0, "3D")  # Hex elements preferred
        self.mapdl.mshkey(0)  # Free mesh

        # Mesh all volumes
        self.mapdl.vmesh("ALL")

        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node
        print(f"  Mesh generated: {num_elements} elements, {num_nodes} nodes")

        return num_elements > 0

    def merge_nodes(self):
        """Merge coincident nodes"""
        print("\n--- Merging Nodes ---")
        self.mapdl.allsel()
        self.mapdl.nummrg("NODE", 1e-6)
        self.mapdl.numcmp("ALL")
        print("  Nodes merged and compressed")

    def assign_materials_by_location(self):
        """Assign materials to elements based on z-location"""
        print("\n--- Assigning Materials by Location ---")

        self.mapdl.allsel()

        for layer_info in self.layer_z_ranges:
            z_bottom = layer_info["z_bottom"]
            z_top = layer_info["z_top"]
            mat_id = layer_info["mat_id"]
            name = layer_info["name"]

            # Select elements in this z range
            self.mapdl.esel("S", "CENT", "Z", z_bottom + 0.0001, z_top - 0.0001)

            # Modify material
            self.mapdl.emodif("ALL", "MAT", mat_id)

            n_elem = self.mapdl.mesh.n_elem
            print(f"  {name}: {n_elem} elements, Mat {mat_id}")

        self.mapdl.allsel()

    def assign_bump_materials(self):
        """Assign bump material to elements at bump coordinates"""
        print("\n--- Assigning Bump Materials ---")

        if not self.bump_coordinates:
            print("  Warning: No bump coordinates loaded")
            return

        bump_mat_id = self.material_ids[BUMP["material"]]
        z_bottom = self.substrate_top_z
        z_top = self.bump_layer_top_z

        half_wx = BUMP["width_x"] / 2.0
        half_wy = BUMP["width_y"] / 2.0

        # Select elements in bump layer
        self.mapdl.allsel()
        self.mapdl.esel("S", "CENT", "Z", z_bottom + 0.0001, z_top - 0.0001)

        bump_layer_elements = self.mapdl.mesh.enum.copy()
        print(f"  Total elements in bump layer: {len(bump_layer_elements)}")

        if len(bump_layer_elements) == 0:
            print("  Warning: No elements in bump layer")
            return

        bump_elem_count = 0

        for elem_id in bump_layer_elements:
            self.mapdl.esel("S", "ELEM", "", elem_id)

            cx = float(self.mapdl.get("cx", "ELEM", elem_id, "CENT", "X"))
            cy = float(self.mapdl.get("cy", "ELEM", elem_id, "CENT", "Y"))

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
        """Save the model database and CDB file"""
        print(f"\n--- Saving Model as '{filename}' ---")

        self.mapdl.allsel()
        self.mapdl.save(filename)
        db_path = os.path.join(self.working_dir, filename + '.db')
        print(f"  Database: {db_path}")

        self.mapdl.cdwrite("ALL", filename, "cdb")
        cdb_path = os.path.join(self.working_dir, filename + '.cdb')
        print(f"  CDB file: {cdb_path}")

        return db_path, cdb_path

    def get_model_summary(self):
        """Print a summary of the model"""
        print("\n" + "=" * 60)
        print("MODEL SUMMARY")
        print("=" * 60)

        self.mapdl.allsel()
        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node

        print(f"\nMesh Statistics:")
        print(f"  Total elements: {num_elements}")
        print(f"  Total nodes: {num_nodes}")

        print(f"\nSubstrate (PCB):")
        print(f"  Size: {SUBSTRATE['length_x']} x {SUBSTRATE['length_y']} mm")
        print(f"  Layers: {len(SUBSTRATE['layers'])}")

        print(f"\nBump Layer:")
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

        print("\n" + "=" * 60)

    def build_full_model(self, coordinate_file=None, save=True):
        """Build the complete model"""
        print("=" * 60)
        print("BUILDING SUBSTRATE + BUMP LAYER + CHIP MODEL")
        print("(Area Extrusion + Volume Meshing)")
        print("=" * 60)

        self.clear_model()
        self.load_bump_coordinates(coordinate_file)
        self.define_materials()
        self.set_element_type()

        # Create geometry by extrusion
        self.create_base_areas()
        self.extrude_substrate_layers()
        self.extrude_bump_layer()
        self.extrude_chip()

        # Mesh
        mesh_success = self.mesh_all_volumes()

        if mesh_success:
            self.merge_nodes()
            self.assign_materials_by_location()
            self.assign_bump_materials()

            if save:
                self.save_model()

        self.get_model_summary()

        return self.mapdl

    def close(self):
        """Close the MAPDL instance"""
        if self.mapdl is not None:
            self.mapdl.exit()
            print("MAPDL instance closed")


def main():
    builder = BumpModelBuilder()

    try:
        mapdl = builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            save=True
        )
        print("\nModel building complete!")

    except Exception as e:
        print(f"Error during model building: {e}")
        import traceback
        traceback.print_exc()

    return builder


if __name__ == "__main__":
    builder = main()
