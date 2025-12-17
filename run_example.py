"""
Example script to run the Substrate + Bump + Chip model builder
This script demonstrates how to use the model builder with different configurations

New Algorithm:
- Substrate: PCB stackup (SR-Cu-Prepreg-Cu-Core-Cu-Prepreg-Cu-SR)
- Bump Layer: Uniform layer under chip, materials assigned by element location
- Chip: Silicon die on top of bump layer
- All structures use mapped mesh
"""

from model_builder import BumpModelBuilder
import config


def run_with_default_config():
    """Run model with default configuration from config.py"""
    print("Running with default configuration...")
    print("PCB Stackup: SR-Cu-Prepreg-Cu-Core-Cu-Prepreg-Cu-SR")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            save=True
        )
    finally:
        builder.close()


def run_with_custom_bump_size():
    """Run model with custom bump dimensions"""

    # Modify bump size at runtime
    config.BUMP["width_x"] = 0.15   # 150um
    config.BUMP["width_y"] = 0.15   # 150um
    config.BUMP["height"] = 0.08    # 80um

    print("Running with custom bump size: 0.15 x 0.15 x 0.08 mm")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            save=True
        )
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
        print(f"\n[Step 2] Loaded {len(builder.bump_coordinates)} bump coordinates")

        # Step 3: Define materials
        builder.define_materials()
        print(f"\n[Step 3] Materials defined: {list(builder.material_ids.keys())}")

        # Step 4: Set element type
        builder.set_element_type()
        print("\n[Step 4] Element type set (SOLID185 for mapped mesh)")

        # Step 5: Create substrate (PCB stackup)
        builder.create_substrate()
        print(f"\n[Step 5] Substrate (PCB) created, top z = {builder.substrate_top_z:.4f} mm")

        # Step 6: Create bump layer (uniform layer under chip)
        builder.create_bump_layer()
        print(f"\n[Step 6] Bump layer created, top z = {builder.bump_layer_top_z:.4f} mm")

        # Step 7: Create chip
        builder.create_chip()
        print("\n[Step 7] Chip created")

        # Step 8: Glue volumes
        builder.glue_volumes()
        print("\n[Step 8] Volumes glued")

        # Step 9: Apply mesh divisions
        builder.apply_mapped_mesh_divisions()
        print("\n[Step 9] Mesh divisions applied")

        # Step 10: Generate mapped mesh
        builder.mesh_model()
        print("\n[Step 10] Mapped mesh generated")

        # Step 11: Assign bump materials by element location
        builder.assign_bump_materials()
        print("\n[Step 11] Bump/Air materials assigned to elements")

        # Step 12: Save model
        builder.save_model("step_by_step_model")
        print("\n[Step 12] Model saved (.db and .cdb)")

        # Print summary
        builder.get_model_summary()

    finally:
        builder.close()


def show_pcb_stackup():
    """Display the PCB stackup configuration"""
    print("=" * 60)
    print("PCB STACKUP CONFIGURATION")
    print("=" * 60)

    total_thickness = 0
    for i, layer in enumerate(config.SUBSTRATE["layers"]):
        print(f"{i+1}. {layer['name']:15s} : {layer['thickness']:.4f} mm ({layer['material']})")
        total_thickness += layer["thickness"]

    print("-" * 60)
    print(f"   Total substrate thickness: {total_thickness:.4f} mm")
    print(f"   Substrate size: {config.SUBSTRATE['length_x']} x {config.SUBSTRATE['length_y']} mm")
    print()
    print(f"Bump layer height: {config.BUMP['height']} mm")
    print(f"Bump size: {config.BUMP['width_x']} x {config.BUMP['width_y']} mm")
    print()
    print(f"Chip size: {config.CHIP['length_x']} x {config.CHIP['length_y']} x {config.CHIP['thickness']} mm")
    print(f"Chip offset: ({config.CHIP['offset_x']}, {config.CHIP['offset_y']}) mm")
    print("=" * 60)


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "default"

    if mode == "default":
        run_with_default_config()
    elif mode == "custom":
        run_with_custom_bump_size()
    elif mode == "step":
        run_step_by_step()
    elif mode == "stackup":
        show_pcb_stackup()
    else:
        print(f"Unknown mode: {mode}")
        print("Available modes: default, custom, step, stackup")
        sys.exit(1)
