"""
Configuration file for Substrate + Bump layer + Chip model
All dimensions in mm, material properties in SI units (MPa for modulus, etc.)
"""

# =============================================================================
# Substrate Configuration
# =============================================================================
SUBSTRATE = {
    "layers": [
        {
            "name": "substrate_core",
            "thickness": 0.4,  # mm
            "material": {
                "name": "FR4",
                "E": 22000,      # Young's modulus (MPa)
                "nu": 0.28,     # Poisson's ratio
                "density": 1.85e-9,  # kg/mm^3 (1850 kg/m^3)
                "CTE": 14e-6,   # Coefficient of thermal expansion (1/K)
            }
        },
        {
            "name": "substrate_metal",
            "thickness": 0.035,  # mm (35um copper layer)
            "material": {
                "name": "Copper",
                "E": 110000,     # Young's modulus (MPa)
                "nu": 0.34,
                "density": 8.96e-9,  # kg/mm^3
                "CTE": 17e-6,
            }
        },
    ],
    "length_x": 10.0,  # mm
    "length_y": 10.0,  # mm
}

# =============================================================================
# Bump Configuration
# =============================================================================
BUMP = {
    "diameter": 0.1,    # mm (100um)
    "height": 0.05,     # mm (50um)
    "material": {
        "name": "SAC305",  # Solder alloy
        "E": 40000,        # Young's modulus (MPa)
        "nu": 0.36,
        "density": 7.4e-9,  # kg/mm^3
        "CTE": 22e-6,
    },
    "coordinate_file": "bump_coordinates.txt",  # Path to bump coordinates
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
    "material": {
        "name": "Silicon",
        "E": 130000,       # Young's modulus (MPa)
        "nu": 0.28,
        "density": 2.33e-9,  # kg/mm^3
        "CTE": 2.6e-6,
    }
}

# =============================================================================
# Underfill Configuration (optional - fills space between bumps)
# =============================================================================
UNDERFILL = {
    "enabled": False,  # Set to True if underfill is needed
    "material": {
        "name": "Underfill_Epoxy",
        "E": 8000,        # Young's modulus (MPa)
        "nu": 0.35,
        "density": 1.2e-9,  # kg/mm^3
        "CTE": 30e-6,
    }
}

# =============================================================================
# Mesh Configuration
# =============================================================================
MESH = {
    "element_size": 0.2,  # mm (global element size)
    "bump_refinement": 0.02,  # mm (element size around bumps)
    "element_type": "SOLID186",  # 20-node hexahedral element
}

# =============================================================================
# Analysis Configuration
# =============================================================================
ANALYSIS = {
    "type": "static",  # "static", "modal", "thermal"
    "output_dir": "results",
}
