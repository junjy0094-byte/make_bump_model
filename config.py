"""
Configuration file for Substrate + Bump layer + Chip model
All dimensions in mm, material properties in SI units (MPa for modulus, etc.)

PCB Stackup (bottom to top):
  SR (bottom) - Cu - Prepreg - Cu - Core - Cu - Prepreg - Cu - SR (top)
"""

# =============================================================================
# Material Definitions
# =============================================================================
MATERIALS = {
    "FR4_Core": {
        "name": "FR4_Core",
        "E": 22000,        # Young's modulus (MPa)
        "nu": 0.28,        # Poisson's ratio
        "density": 1.85e-9,  # kg/mm^3
        "CTE": 14e-6,      # Coefficient of thermal expansion (1/K)
    },
    "FR4_Prepreg": {
        "name": "FR4_Prepreg",
        "E": 20000,        # Young's modulus (MPa)
        "nu": 0.28,
        "density": 1.80e-9,
        "CTE": 15e-6,
    },
    "Copper": {
        "name": "Copper",
        "E": 110000,       # Young's modulus (MPa)
        "nu": 0.34,
        "density": 8.96e-9,
        "CTE": 17e-6,
    },
    "Solder_Resist": {
        "name": "Solder_Resist",
        "E": 3500,         # Young's modulus (MPa)
        "nu": 0.35,
        "density": 1.4e-9,
        "CTE": 30e-6,
    },
    "SAC305": {
        "name": "SAC305",  # Solder bump material
        "E": 40000,        # Young's modulus (MPa)
        "nu": 0.36,
        "density": 7.4e-9,
        "CTE": 22e-6,
    },
    "Silicon": {
        "name": "Silicon",
        "E": 130000,       # Young's modulus (MPa)
        "nu": 0.28,
        "density": 2.33e-9,
        "CTE": 2.6e-6,
    },
    "Air": {
        "name": "Air",
        "E": 0.001,        # Very low stiffness (MPa)
        "nu": 0.0,
        "density": 1.2e-12,  # kg/mm^3
        "CTE": 0.0,
    },
}

# =============================================================================
# Substrate Configuration (PCB Stackup: bottom to top)
# SR - Cu - Prepreg - Cu - Core - Cu - Prepreg - Cu - SR
# =============================================================================
SUBSTRATE = {
    "layers": [
        # Bottom solder resist
        {"name": "SR_bottom", "thickness": 0.02, "material": "Solder_Resist"},
        # Bottom copper
        {"name": "Cu_L1", "thickness": 0.035, "material": "Copper"},
        # Prepreg
        {"name": "Prepreg_1", "thickness": 0.1, "material": "FR4_Prepreg"},
        # Inner copper layer 1
        {"name": "Cu_L2", "thickness": 0.035, "material": "Copper"},
        # Core
        {"name": "Core", "thickness": 0.4, "material": "FR4_Core"},
        # Inner copper layer 2
        {"name": "Cu_L3", "thickness": 0.035, "material": "Copper"},
        # Prepreg
        {"name": "Prepreg_2", "thickness": 0.1, "material": "FR4_Prepreg"},
        # Top copper
        {"name": "Cu_L4", "thickness": 0.035, "material": "Copper"},
        # Top solder resist
        {"name": "SR_top", "thickness": 0.02, "material": "Solder_Resist"},
    ],
    "length_x": 10.0,  # mm
    "length_y": 10.0,  # mm
}

# =============================================================================
# Bump Layer Configuration
# - Bump layer is a uniform layer under the chip
# - Elements at bump coordinates get bump material
# - Remaining elements get air material
# =============================================================================
BUMP = {
    "width_x": 0.1,     # mm (bump width in x direction)
    "width_y": 0.1,     # mm (bump width in y direction)
    "height": 0.05,     # mm (50um bump height)
    "material": "SAC305",
    "air_material": "Air",
    "coordinate_file": "bump_coordinates.txt",  # Path to bump coordinates (x, y centers)
}

# =============================================================================
# Chip Configuration
# =============================================================================
CHIP = {
    "length_x": 8.0,    # mm
    "length_y": 8.0,    # mm
    "thickness": 0.3,   # mm
    "offset_x": 1.0,    # mm (offset from substrate corner)
    "offset_y": 1.0,    # mm
    "material": "Silicon",
}

# =============================================================================
# Mesh Configuration
# =============================================================================
MESH = {
    "element_size": 0.1,        # Global element size in mm
    "element_type": "SOLID185",  # 8-node hexahedral element
}

# =============================================================================
# Analysis Configuration
# =============================================================================
ANALYSIS = {
    "type": "static",  # "static", "modal", "thermal"
    "output_dir": "results",
}
