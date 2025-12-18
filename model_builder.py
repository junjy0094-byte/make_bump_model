"""
PyAnsys Model Builder for Substrate + Bump layer + Chip Structure
Uses Area Mesh + Extrude approach for proper element connectivity

Algorithm:
1. Create base areas with chip region sliced
2. Generate 2D area mesh (AMESH) on base areas
3. Extrude 2D mesh layer by layer using VEXT
4. Assign materials based on layer and location
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
    Uses area mesh + extrude approach for proper element connectivity
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

        # Store area info for selective extrusion
        self.chip_area_num = None
        self.substrate_area_nums = []

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

    def set_element_types(self):
        """Set element types for meshing"""
        print("\n--- Setting Element Types ---")

        # ET 1: 3D solid element for final mesh
        element_type = MESH["element_type"]
        self.mapdl.et(1, element_type)
        print(f"  ET 1: {element_type} (3D hexahedral for extrusion)")

        # ET 2: 2D mesh generation element (MESH200 with QUAD option)
        # MESH200 is a "mesh-only" element used for mesh generation
        # KEYOPT(1)=6 for QUAD4 (4-node quadrilateral)
        self.mapdl.et(2, "MESH200", 6)
        print(f"  ET 2: MESH200 (2D quad for area meshing)")

    def create_base_areas(self):
        """Create base areas at z=0 with chip region sliced"""
        print("\n--- Creating Base Areas ---")

        sub_lx = SUBSTRATE["length_x"]
        sub_ly = SUBSTRATE["length_y"]

        # Create keypoints for substrate boundary
        self.mapdl.k(1, 0, 0, 0)
        self.mapdl.k(2, sub_lx, 0, 0)
        self.mapdl.k(3, sub_lx, sub_ly, 0)
        self.mapdl.k(4, 0, sub_ly, 0)

        # Create keypoints for chip region
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

        # Create chip region area (center) - Area 1
        self.mapdl.a(5, 6, 7, 8)
        self.chip_area_num = 1
        print(f"  Created chip region area (A{self.chip_area_num})")

        # Create surrounding areas (Area 2-9)
        self.mapdl.a(1, 9, 5, 16)   # bottom-left
        self.mapdl.a(9, 10, 6, 5)   # bottom-center
        self.mapdl.a(10, 2, 11, 6)  # bottom-right
        self.mapdl.a(6, 11, 12, 7)  # right
        self.mapdl.a(7, 12, 3, 13)  # top-right
        self.mapdl.a(8, 7, 13, 14)  # top-center
        self.mapdl.a(15, 8, 14, 4)  # top-left
        self.mapdl.a(16, 5, 8, 15)  # left

        self.mapdl.allsel()
        all_areas = list(self.mapdl.geometry.anum)
        self.substrate_area_nums = [a for a in all_areas if a != self.chip_area_num]

        print(f"  Total areas created: {len(all_areas)}")
        print(f"  Chip area: A{self.chip_area_num}")
        print(f"  Surrounding areas: {self.substrate_area_nums}")
        print(f"  Substrate: {sub_lx} x {sub_ly} mm")
        print(f"  Chip region: [{self.chip_x_min}, {self.chip_x_max}] x [{self.chip_y_min}, {self.chip_y_max}] mm")

    def mesh_base_areas(self):
        """Generate 2D mesh on base areas using MESH200"""
        print("\n--- Meshing Base Areas (2D) ---")

        elem_size = MESH["element_size"]

        # Select all base areas
        self.mapdl.allsel()
        self.mapdl.asel("S", "LOC", "Z", -0.0001, 0.0001)

        # Set element type to MESH200 for 2D meshing
        self.mapdl.type(2)

        # Set element size
        self.mapdl.esize(elem_size)
        print(f"  Element size: {elem_size} mm")

        # Set mesh shape to quadrilateral
        self.mapdl.mshape(0, "2D")  # 0 = quad
        self.mapdl.mshkey(0)  # Free mesh

        # Mesh all base areas
        self.mapdl.amesh("ALL")

        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node
        print(f"  2D mesh generated: {num_elements} elements, {num_nodes} nodes")

        return num_elements > 0

    def extrude_all_layers(self):
        """Extrude 2D mesh to create all layers at once with different heights"""
        print("\n--- Extruding All Layers ---")

        self.layer_z_ranges = []

        # Calculate total substrate thickness
        substrate_thickness = sum(layer["thickness"] for layer in SUBSTRATE["layers"])
        bump_height = BUMP["height"]
        chip_thickness = CHIP["thickness"]

        # Store substrate layer info
        z_current = 0.0
        for layer in SUBSTRATE["layers"]:
            thickness = layer["thickness"]
            mat_name = layer["material"]
            mat_id = self.material_ids[mat_name]

            self.layer_z_ranges.append({
                "name": layer["name"],
                "mat_id": mat_id,
                "z_bottom": z_current,
                "z_top": z_current + thickness
            })
            z_current += thickness
            print(f"  Substrate layer {layer['name']}: z=[{z_current-thickness:.4f}, {z_current:.4f}] mm")

        self.substrate_top_z = substrate_thickness

        # Store bump layer info
        self.layer_z_ranges.append({
            "name": "bump_layer",
            "mat_id": self.material_ids[BUMP["air_material"]],
            "z_bottom": substrate_thickness,
            "z_top": substrate_thickness + bump_height,
            "is_bump_layer": True
        })
        self.bump_layer_top_z = substrate_thickness + bump_height
        print(f"  Bump layer: z=[{substrate_thickness:.4f}, {self.bump_layer_top_z:.4f}] mm")

        # Store chip layer info
        chip_top_z = self.bump_layer_top_z + chip_thickness
        self.layer_z_ranges.append({
            "name": "chip",
            "mat_id": self.material_ids[CHIP["material"]],
            "z_bottom": self.bump_layer_top_z,
            "z_top": chip_top_z
        })
        print(f"  Chip: z=[{self.bump_layer_top_z:.4f}, {chip_top_z:.4f}] mm")

        # Set element type to 3D solid
        self.mapdl.type(1)

        # ===== Extrude substrate-only region (outside chip area) =====
        print("\n  Extruding substrate-only region...")
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)  # MESH200 elements

        # Deselect chip region
        self.mapdl.esel("U", "CENT", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)

        # Also need to handle Y range - reselect and properly exclude chip region
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)

        # Select elements OUTSIDE chip region (by excluding chip X and Y)
        # This is tricky - we need elements NOT in chip region
        # Approach: select all, then for chip region elements, unselect them
        all_2d_count = self.mapdl.mesh.n_elem
        print(f"    Total 2D elements: {all_2d_count}")

        # Get chip region elements
        self.mapdl.esel("R", "CENT", "X", self.chip_x_min - 0.001, self.chip_x_max + 0.001)
        self.mapdl.esel("R", "CENT", "Y", self.chip_y_min - 0.001, self.chip_y_max + 0.001)
        chip_2d_count = self.mapdl.mesh.n_elem
        print(f"    Chip region 2D elements: {chip_2d_count}")

        # Select substrate-only elements (outside chip region)
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)
        self.mapdl.esel("U", "CENT", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)

        # Re-add elements outside chip Y range
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)
        # Complex selection - let's use a different approach

        # Simpler approach: select chip region, invert selection
        self.mapdl.esel("R", "CENT", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)
        self.mapdl.esel("R", "CENT", "Y", self.chip_y_min + 0.001, self.chip_y_max - 0.001)
        chip_elems = list(self.mapdl.mesh.enum)

        # Now select all 2D and unselect chip elements
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)
        for elem in chip_elems:
            self.mapdl.esel("U", "ELEM", "", elem)

        substrate_only_count = self.mapdl.mesh.n_elem
        print(f"    Substrate-only 2D elements: {substrate_only_count}")

        if substrate_only_count > 0:
            substrate_divisions = max(1, int(round(substrate_thickness / MESH["element_size"])))
            self.mapdl.vext("ALL", "", "", 0, 0, substrate_thickness, 1, 1, substrate_divisions)
            print(f"    Extruded substrate: thickness={substrate_thickness:.4f}, divisions={substrate_divisions}")

        # ===== Extrude chip region (substrate + bump + chip) =====
        print("\n  Extruding chip region (full stack)...")
        self.mapdl.allsel()
        self.mapdl.esel("S", "TYPE", "", 2)
        self.mapdl.esel("R", "CENT", "X", self.chip_x_min + 0.001, self.chip_x_max - 0.001)
        self.mapdl.esel("R", "CENT", "Y", self.chip_y_min + 0.001, self.chip_y_max - 0.001)

        chip_region_count = self.mapdl.mesh.n_elem
        print(f"    Chip region 2D elements: {chip_region_count}")

        if chip_region_count > 0:
            total_chip_height = substrate_thickness + bump_height + chip_thickness
            total_divisions = max(1, int(round(total_chip_height / MESH["element_size"])))
            self.mapdl.vext("ALL", "", "", 0, 0, total_chip_height, 1, 1, total_divisions)
            print(f"    Extruded chip stack: thickness={total_chip_height:.4f}, divisions={total_divisions}")

        # ===== Assign materials based on z-location =====
        print("\n  Assigning materials to layers...")
        for layer_info in self.layer_z_ranges:
            z_bottom = layer_info["z_bottom"]
            z_top = layer_info["z_top"]
            mat_id = layer_info["mat_id"]
            name = layer_info["name"]

            self.mapdl.allsel()
            self.mapdl.esel("S", "TYPE", "", 1)  # 3D elements only
            self.mapdl.esel("R", "CENT", "Z", z_bottom + 0.0001, z_top - 0.0001)

            n_elem = self.mapdl.mesh.n_elem
            if n_elem > 0:
                self.mapdl.emodif("ALL", "MAT", mat_id)
                print(f"    {name}: {n_elem} elements, Mat={mat_id}")

        self.mapdl.allsel()
        total_3d = self.mapdl.mesh.n_elem
        print(f"\n  Total 3D elements created: {total_3d}")

    def delete_2d_elements(self):
        """Delete the original 2D MESH200 elements"""
        print("\n--- Cleaning up 2D elements ---")

        self.mapdl.allsel()
        # Select elements by type (MESH200 is type 2)
        self.mapdl.esel("S", "TYPE", "", 2)
        n_2d = self.mapdl.mesh.n_elem

        if n_2d > 0:
            self.mapdl.edele("ALL")
            print(f"  Deleted {n_2d} 2D elements")
        else:
            print("  No 2D elements to delete")

        self.mapdl.allsel()

    def merge_nodes(self):
        """Merge coincident nodes"""
        print("\n--- Merging Nodes ---")
        self.mapdl.allsel()
        self.mapdl.nummrg("NODE", 1e-6)
        self.mapdl.numcmp("ALL")
        print("  Nodes merged and compressed")

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

        bump_layer_elements = list(self.mapdl.mesh.enum)
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
        """Build the complete model using area mesh + extrude approach"""
        print("=" * 60)
        print("BUILDING SUBSTRATE + BUMP LAYER + CHIP MODEL")
        print("(Area Mesh + Extrude Approach)")
        print("=" * 60)

        self.clear_model()
        self.load_bump_coordinates(coordinate_file)
        self.define_materials()
        self.set_element_types()

        # Step 1: Create base areas with chip region
        self.create_base_areas()

        # Step 2: Generate 2D mesh on base areas
        mesh_success = self.mesh_base_areas()
        if not mesh_success:
            print("ERROR: Failed to generate 2D mesh!")
            return self.mapdl

        # Step 3: Extrude all layers at once
        # - Substrate-only region: substrate thickness
        # - Chip region: substrate + bump + chip thickness
        self.extrude_all_layers()

        # Step 4: Clean up and finalize
        self.delete_2d_elements()
        self.merge_nodes()
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
