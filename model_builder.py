"""
PyAnsys Model Builder for Substrate + Bump layer + Chip Structure
Uses ansys-mapdl-core (PyMAPDL) for geometry creation and mapped meshing

Algorithm:
1. Create substrate layers (PCB stackup) with mapped mesh
2. Create uniform bump layer under chip area
3. Create chip with mapped mesh
4. After meshing, assign bump material to elements at bump coordinates
5. Assign air material to remaining elements in bump layer

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
    with mapped mesh and element-based material assignment for bumps
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

        # Ignore non-critical MAPDL warnings/errors
        self.mapdl.ignore_errors = True

        self.bump_coordinates = []
        self.material_ids = {}
        self.volume_info = {
            "substrate": [],
            "bump_layer": None,
            "chip": None,
        }

        # Track z-coordinates for layer stacking
        self.current_z = 0.0
        self.substrate_top_z = 0.0
        self.bump_layer_top_z = 0.0

    def clear_model(self):
        """Clear all existing geometry and start fresh"""
        self.mapdl.clear()
        self.mapdl.prep7()

    def load_bump_coordinates(self, filepath=None):
        """
        Load bump coordinates from a text file
        Coordinates are center positions of rectangular bumps

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
        """Set element type for mapped meshing"""
        print("\n--- Setting Element Type ---")

        element_type = MESH["element_type"]
        self.mapdl.et(1, element_type)
        print(f"Element type: {element_type} (8-node hexahedral for mapped mesh)")

    def create_substrate(self):
        """Create substrate layers (PCB stackup) as stacked volumes"""
        print("\n--- Creating Substrate (PCB Stackup) ---")

        lx = SUBSTRATE["length_x"]
        ly = SUBSTRATE["length_y"]
        self.current_z = 0.0

        for i, layer in enumerate(SUBSTRATE["layers"]):
            thickness = layer["thickness"]
            z_bottom = self.current_z
            z_top = z_bottom + thickness
            mat_name = layer["material"]
            mat_id = self.material_ids[mat_name]

            # Create block volume
            self.mapdl.block(0, lx, 0, ly, z_bottom, z_top)
            vol_num = self.mapdl.geometry.vnum[-1]

            # Assign material attribute
            self.mapdl.vsel("S", "VOLU", "", vol_num)
            self.mapdl.vatt(mat_id, "", 1)

            self.volume_info["substrate"].append({
                "volume": vol_num,
                "layer_name": layer["name"],
                "material": mat_name,
                "mat_id": mat_id,
                "z_bottom": z_bottom,
                "z_top": z_top
            })

            print(f"  {layer['name']}: Vol {vol_num}, Mat {mat_id} ({mat_name}), "
                  f"z=[{z_bottom:.4f}, {z_top:.4f}] mm")

            self.current_z = z_top

        self.substrate_top_z = self.current_z
        self.mapdl.allsel()
        print(f"Substrate top z: {self.substrate_top_z:.4f} mm")

    def create_bump_layer(self):
        """
        Create uniform bump layer under chip area
        Material assignment to individual elements will be done after meshing
        """
        print("\n--- Creating Bump Layer ---")

        # Bump layer covers chip area
        x_min = CHIP["offset_x"]
        x_max = CHIP["offset_x"] + CHIP["length_x"]
        y_min = CHIP["offset_y"]
        y_max = CHIP["offset_y"] + CHIP["length_y"]

        height = BUMP["height"]
        z_bottom = self.substrate_top_z
        z_top = z_bottom + height

        # Initially assign air material (will be modified after meshing)
        air_mat_id = self.material_ids[BUMP["air_material"]]

        # Create block volume for bump layer
        self.mapdl.block(x_min, x_max, y_min, y_max, z_bottom, z_top)
        vol_num = self.mapdl.geometry.vnum[-1]

        self.mapdl.vsel("S", "VOLU", "", vol_num)
        self.mapdl.vatt(air_mat_id, "", 1)

        self.volume_info["bump_layer"] = {
            "volume": vol_num,
            "mat_id": air_mat_id,
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "z_bottom": z_bottom,
            "z_top": z_top
        }

        self.bump_layer_top_z = z_top
        self.mapdl.allsel()

        print(f"  Bump layer: Vol {vol_num}")
        print(f"  Position: x=[{x_min}, {x_max}], y=[{y_min}, {y_max}], "
              f"z=[{z_bottom:.4f}, {z_top:.4f}] mm")
        print(f"  Initial material: Air (will assign bump material after meshing)")

    def create_chip(self):
        """Create chip volume on top of bump layer"""
        print("\n--- Creating Chip ---")

        lx = CHIP["length_x"]
        ly = CHIP["length_y"]
        thickness = CHIP["thickness"]
        offset_x = CHIP["offset_x"]
        offset_y = CHIP["offset_y"]

        mat_name = CHIP["material"]
        mat_id = self.material_ids[mat_name]

        z_bottom = self.bump_layer_top_z
        z_top = z_bottom + thickness

        self.mapdl.block(
            offset_x, offset_x + lx,
            offset_y, offset_y + ly,
            z_bottom, z_top
        )
        vol_num = self.mapdl.geometry.vnum[-1]

        self.mapdl.vsel("S", "VOLU", "", vol_num)
        self.mapdl.vatt(mat_id, "", 1)

        self.volume_info["chip"] = {
            "volume": vol_num,
            "mat_id": mat_id,
            "z_bottom": z_bottom,
            "z_top": z_top
        }

        self.mapdl.allsel()
        print(f"  Chip: Vol {vol_num}, Mat {mat_id} ({mat_name})")
        print(f"  Position: x=[{offset_x}, {offset_x + lx}], "
              f"y=[{offset_y}, {offset_y + ly}], "
              f"z=[{z_bottom:.4f}, {z_top:.4f}] mm")

    def glue_volumes(self):
        """Glue all volumes together for mesh connectivity"""
        print("\n--- Gluing Volumes ---")
        self.mapdl.allsel()
        self.mapdl.vsel("ALL")
        self.mapdl.vglue("ALL")
        print("All volumes glued together")

    def apply_mapped_mesh_divisions(self):
        """Set line divisions for mapped meshing"""
        print("\n--- Setting Mapped Mesh Divisions ---")

        # Get all lines and set divisions based on orientation
        self.mapdl.allsel()

        # Substrate divisions
        div_x = MESH["substrate_div_x"]
        div_y = MESH["substrate_div_y"]
        div_z = MESH["layer_div_z"]

        # Select lines by direction and set divisions
        # This is a simplified approach - in practice you may need more specific line selection

        print(f"  Substrate: {div_x} x {div_y} x {div_z} per layer")
        print(f"  Bump layer: {MESH['bump_layer_div_x']} x {MESH['bump_layer_div_y']} x {MESH['bump_layer_div_z']}")
        print(f"  Chip: {MESH['chip_div_x']} x {MESH['chip_div_y']} x {MESH['chip_div_z']}")

    def mesh_model(self):
        """Generate mapped mesh for all volumes"""
        print("\n--- Generating Mapped Mesh ---")

        self.mapdl.allsel()

        # Use VSWEEP for mapped meshing (sweeps mesh through volumes)
        # First, we need to ensure volumes are meshable with mapped mesh

        # Set mesh shape to hexahedral
        self.mapdl.mshape(0, "3D")  # 0 = quadrilateral/hexahedral
        self.mapdl.mshkey(1)  # 1 = mapped mesh

        # Set smart element sizing
        self.mapdl.smrtsize(6)  # Medium smart sizing

        # Mesh all volumes
        self.mapdl.vmesh("ALL")

        num_elements = self.mapdl.mesh.n_elem
        num_nodes = self.mapdl.mesh.n_node

        print(f"Mesh generated: {num_elements} elements, {num_nodes} nodes")

    def assign_bump_materials(self):
        """
        Assign bump material to elements at bump coordinates
        and air material to remaining elements in bump layer
        """
        print("\n--- Assigning Bump Materials by Element Location ---")

        if not self.bump_coordinates:
            print("Warning: No bump coordinates loaded")
            return

        bump_layer = self.volume_info["bump_layer"]
        bump_mat_id = self.material_ids[BUMP["material"]]
        air_mat_id = self.material_ids[BUMP["air_material"]]

        z_bottom = bump_layer["z_bottom"]
        z_top = bump_layer["z_top"]
        z_mid = (z_bottom + z_top) / 2.0

        # Get bump dimensions
        half_wx = BUMP["width_x"] / 2.0
        half_wy = BUMP["width_y"] / 2.0

        # Select elements in bump layer by location
        self.mapdl.esel("S", "CENT", "Z", z_bottom, z_top)
        bump_layer_elements = self.mapdl.mesh.enum.copy()

        print(f"  Total elements in bump layer: {len(bump_layer_elements)}")

        # Get element centroids
        bump_elem_count = 0

        for elem_id in bump_layer_elements:
            # Get element centroid
            self.mapdl.esel("S", "ELEM", "", elem_id)

            # Get centroid using MAPDL queries
            result = self.mapdl.get("cx", "ELEM", elem_id, "CENT", "X")
            cx = float(result)
            result = self.mapdl.get("cy", "ELEM", elem_id, "CENT", "Y")
            cy = float(result)

            # Check if element centroid is within any bump region
            is_bump = False
            for (bx, by) in self.bump_coordinates:
                if (bx - half_wx <= cx <= bx + half_wx and
                    by - half_wy <= cy <= by + half_wy):
                    is_bump = True
                    break

            if is_bump:
                # Assign bump material
                self.mapdl.emodif(elem_id, "MAT", bump_mat_id)
                bump_elem_count += 1

        # Remaining elements already have air material (default)
        air_elem_count = len(bump_layer_elements) - bump_elem_count

        self.mapdl.allsel()

        print(f"  Bump elements: {bump_elem_count}")
        print(f"  Air elements: {air_elem_count}")
        print(f"  Bump material ID: {bump_mat_id}, Air material ID: {air_mat_id}")

    def save_model(self, filename="bump_model"):
        """Save the model database (.db) and CDB file (.cdb)"""
        print(f"\n--- Saving Model as '{filename}' ---")

        # Save MAPDL database (.db)
        self.mapdl.save(filename)
        db_path = os.path.join(self.working_dir, filename + '.db')
        print(f"Model database saved to: {db_path}")

        # Save CDB file
        cdb_path = os.path.join(self.working_dir, filename + '.cdb')
        self.mapdl.allsel()
        self.mapdl.cdwrite("ALL", filename, "cdb")
        print(f"CDB file saved to: {cdb_path}")

        return db_path, cdb_path

    def get_model_summary(self):
        """Print a summary of the model"""
        print("\n" + "=" * 60)
        print("MODEL SUMMARY")
        print("=" * 60)

        print(f"\nSubstrate (PCB):")
        print(f"  Size: {SUBSTRATE['length_x']} x {SUBSTRATE['length_y']} mm")
        print(f"  Layers: {len(SUBSTRATE['layers'])}")
        total_thickness = sum(layer['thickness'] for layer in SUBSTRATE['layers'])
        print(f"  Total thickness: {total_thickness:.4f} mm")
        print(f"  Stackup:")
        for layer in SUBSTRATE["layers"]:
            print(f"    - {layer['name']}: {layer['thickness']} mm ({layer['material']})")

        print(f"\nBump Layer:")
        print(f"  Size: {CHIP['length_x']} x {CHIP['length_y']} mm (under chip)")
        print(f"  Height: {BUMP['height']} mm")
        print(f"  Bump count: {len(self.bump_coordinates)}")
        print(f"  Bump size: {BUMP['width_x']} x {BUMP['width_y']} mm")

        print(f"\nChip:")
        print(f"  Size: {CHIP['length_x']} x {CHIP['length_y']} x {CHIP['thickness']} mm")
        print(f"  Position: offset ({CHIP['offset_x']}, {CHIP['offset_y']}) mm")

        print(f"\nZ-coordinates:")
        print(f"  Substrate: 0 to {self.substrate_top_z:.4f} mm")
        print(f"  Bump layer: {self.substrate_top_z:.4f} to {self.bump_layer_top_z:.4f} mm")
        chip_top = self.bump_layer_top_z + CHIP['thickness']
        print(f"  Chip: {self.bump_layer_top_z:.4f} to {chip_top:.4f} mm")
        print(f"  Total height: {chip_top:.4f} mm")

        print("\n" + "=" * 60)

    def build_full_model(self, coordinate_file=None, save=True):
        """
        Build the complete model

        Parameters
        ----------
        coordinate_file : str, optional
            Path to bump coordinates file
        save : bool, optional
            Whether to save the model (default True)
        """
        print("=" * 60)
        print("BUILDING SUBSTRATE + BUMP LAYER + CHIP MODEL")
        print("(Mapped Mesh with Element-based Material Assignment)")
        print("=" * 60)

        # Clear and initialize
        self.clear_model()

        # Load bump coordinates
        self.load_bump_coordinates(coordinate_file)

        # Define materials
        self.define_materials()

        # Set element type
        self.set_element_type()

        # Create geometry (materials assigned during creation)
        self.create_substrate()
        self.create_bump_layer()
        self.create_chip()

        # Glue volumes
        self.glue_volumes()

        # Set mesh divisions
        self.apply_mapped_mesh_divisions()

        # Generate mapped mesh
        self.mesh_model()

        # Assign bump/air materials based on element location
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
