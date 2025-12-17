"""
Example script to run the Substrate + Bump + Chip model builder

New Algorithm (Bottom-up Extrusion):
1. Create base area with chip region sliced
2. Mesh base area (2D mapped mesh)
3. Extrude substrate layers
4. Extrude bump layer (chip area only)
5. Extrude chip
6. Merge nodes
7. Assign bump/air materials by element location
"""

from model_builder import BumpModelBuilder
import config


def run_with_default_config():
    """Run model with default configuration from config.py"""
    print("Running with default configuration...")
    print("Using bottom-up extrusion approach")

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
        print(f"\n[Step 3] Materials defined")

        # Step 4: Set element types
        builder.set_element_type()
        print("\n[Step 4] Element types set (MESH200 + SOLID185)")

        # Step 5: Create base area with chip region
        builder.create_base_area_with_chip_region()
        print("\n[Step 5] Base area created with chip region sliced")

        # Step 6: Mesh base area (2D)
        builder.mesh_base_area()
        print("\n[Step 6] 2D base mesh generated")

        # Step 7: Extrude substrate layers
        builder.extrude_substrate_layers()
        print(f"\n[Step 7] Substrate extruded, top z = {builder.substrate_top_z:.4f} mm")

        # Step 8: Extrude bump layer
        builder.extrude_bump_layer()
        print(f"\n[Step 8] Bump layer extruded, top z = {builder.bump_layer_top_z:.4f} mm")

        # Step 9: Extrude chip
        builder.extrude_chip()
        print("\n[Step 9] Chip extruded")

        # Step 10: Cleanup 2D elements
        builder.cleanup_2d_elements()
        print("\n[Step 10] 2D elements cleaned up")

        # Step 11: Merge nodes
        builder.merge_nodes()
        print("\n[Step 11] Nodes merged")

        # Step 12: Assign bump materials
        builder.assign_bump_materials()
        print("\n[Step 12] Bump/Air materials assigned")

        # Step 13: Save model
        builder.save_model("step_by_step_model")
        print("\n[Step 13] Model saved (.db and .cdb)")

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
    elif mode == "step":
        run_step_by_step()
    elif mode == "stackup":
        show_pcb_stackup()
    else:
        print(f"Unknown mode: {mode}")
        print("Available modes: default, step, stackup")
        sys.exit(1)
