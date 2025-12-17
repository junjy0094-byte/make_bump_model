"""
Example script to run the Substrate + Bump + Chip model builder

Algorithm (Area Extrusion + Volume Meshing):
1. Create base areas with keypoints (chip region + surrounding)
2. Extrude areas into volumes (VOFFST)
3. Mesh volumes (VMESH)
4. Assign materials by z-location
5. Assign bump materials by x,y location
"""

from model_builder import BumpModelBuilder
import config


def run_default():
    """Run with default configuration"""
    print("Running with default configuration...")

    builder = BumpModelBuilder()

    try:
        builder.build_full_model(
            coordinate_file="bump_coordinates.txt",
            save=True
        )
    finally:
        builder.close()


def run_step_by_step():
    """Run step by step for debugging"""
    print("Running step-by-step...")

    builder = BumpModelBuilder()

    try:
        builder.clear_model()
        print("\n[1] Model cleared")

        builder.load_bump_coordinates("bump_coordinates.txt")
        print(f"\n[2] Loaded {len(builder.bump_coordinates)} bumps")

        builder.define_materials()
        print("\n[3] Materials defined")

        builder.set_element_type()
        print("\n[4] Element type set")

        builder.create_base_areas()
        print("\n[5] Base areas created")

        builder.extrude_substrate_layers()
        print(f"\n[6] Substrate extruded, z={builder.substrate_top_z:.4f}")

        builder.extrude_bump_layer()
        print(f"\n[7] Bump layer extruded, z={builder.bump_layer_top_z:.4f}")

        builder.extrude_chip()
        print("\n[8] Chip extruded")

        mesh_ok = builder.mesh_all_volumes()
        print(f"\n[9] Mesh: {'OK' if mesh_ok else 'FAILED'}")

        if mesh_ok:
            builder.merge_nodes()
            print("\n[10] Nodes merged")

            builder.assign_materials_by_location()
            print("\n[11] Materials assigned by z-location")

            builder.assign_bump_materials()
            print("\n[12] Bump materials assigned")

            builder.save_model("step_model")
            print("\n[13] Model saved")

        builder.get_model_summary()

    finally:
        builder.close()


def show_stackup():
    """Show PCB stackup"""
    print("=" * 50)
    print("PCB STACKUP")
    print("=" * 50)

    total = 0
    for i, layer in enumerate(config.SUBSTRATE["layers"]):
        print(f"{i+1}. {layer['name']:12s}: {layer['thickness']:.4f} mm ({layer['material']})")
        total += layer["thickness"]

    print("-" * 50)
    print(f"Total: {total:.4f} mm")
    print(f"Bump: {config.BUMP['height']} mm")
    print(f"Chip: {config.CHIP['thickness']} mm")


if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "default"

    if mode == "default":
        run_default()
    elif mode == "step":
        run_step_by_step()
    elif mode == "stackup":
        show_stackup()
    else:
        print(f"Unknown: {mode}")
        print("Modes: default, step, stackup")
