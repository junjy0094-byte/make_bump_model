"""
Example script to run the Substrate + Bump + Chip model builder
This script demonstrates how to use the model builder with different configurations
"""

from model_builder import BumpModelBuilder
from config import SUBSTRATE, BUMP, CHIP


def run_with_default_config():
    """Run model with default configuration from config.py"""
    print("Running with default configuration...")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            mesh=True,
            save=True,
            plot=False
        )
    finally:
        builder.close()


def run_with_custom_config():
    """Run model with custom configuration (modify values at runtime)"""
    import config

    # Modify substrate size
    config.SUBSTRATE["length_x"] = 12.0
    config.SUBSTRATE["length_y"] = 12.0

    # Modify chip size to fit
    config.CHIP["length_x"] = 10.0
    config.CHIP["length_y"] = 10.0
    config.CHIP["offset_x"] = 1.0
    config.CHIP["offset_y"] = 1.0

    # Modify bump parameters
    config.BUMP["diameter"] = 0.15  # 150um
    config.BUMP["height"] = 0.08   # 80um

    print("Running with custom configuration...")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            mesh=True,
            save=True,
            plot=False
        )
    finally:
        builder.close()


def run_geometry_only():
    """Create geometry without meshing (for visualization/verification)"""
    print("Running geometry creation only (no mesh)...")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            mesh=False,  # Skip meshing
            save=True,
            plot=False
        )

        # Access the MAPDL instance for custom operations
        mapdl = builder.mapdl

        # Example: List all volumes
        print("\nVolume list:")
        print(mapdl.vlist())

    finally:
        builder.close()


def run_step_by_step():
    """Run model building step by step for debugging"""
    print("Running step-by-step model building...")

    builder = BumpModelBuilder()

    try:
        # Step 1: Initialize
        builder.clear_model()
        print("\n[Step 1] Model cleared")

        # Step 2: Load bump coordinates
        builder.load_bump_coordinates("bump_coordinates.txt")
        print(f"\n[Step 2] Loaded {len(builder.bump_coordinates)} bumps")

        # Step 3: Define materials
        builder.define_materials()
        print(f"\n[Step 3] Materials defined: {list(builder.material_ids.keys())}")

        # Step 4: Set element type
        builder.set_element_type()
        print("\n[Step 4] Element type set")

        # Step 5: Create substrate
        builder.create_substrate()
        print(f"\n[Step 5] Substrate created, top z = {builder.substrate_top_z}")

        # Step 6: Create bumps
        builder.create_bumps()
        print(f"\n[Step 6] Bumps created, count = {len(builder.volume_ids['bump'])}")

        # Step 7: Create chip
        builder.create_chip()
        print("\n[Step 7] Chip created")

        # Step 8: Glue volumes
        builder.glue_volumes()
        print("\n[Step 8] Volumes glued")

        # Step 9: Assign materials
        builder.assign_materials_to_volumes()
        print("\n[Step 9] Materials assigned to volumes")

        # Step 10: Mesh
        builder.mesh_model()
        print("\n[Step 10] Mesh generated")

        # Step 11: Save
        builder.save_model("step_by_step_model")
        print("\n[Step 11] Model saved")

        # Print summary
        builder.get_model_summary()

    finally:
        builder.close()


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "default"

    if mode == "default":
        run_with_default_config()
    elif mode == "custom":
        run_with_custom_config()
    elif mode == "geometry":
        run_geometry_only()
    elif mode == "step":
        run_step_by_step()
    else:
        print(f"Unknown mode: {mode}")
        print("Available modes: default, custom, geometry, step")
        sys.exit(1)
