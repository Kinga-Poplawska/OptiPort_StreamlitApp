"""
Consistent color mapping for technologies across all visualizations.

This module provides deterministic, consistent color assignments for all
technology types, organized by category:
  - Anlagentechnik (System Technology)
  - Gebäudehülle (Building Envelope)
  - Übergabesystem (Transfer/Distribution Systems)
"""

from typing import Dict

# ============================================================================
# CATEGORY: ANLAGENTECHNIK (System Technology)
# ============================================================================

# Heat Generators - Distinct, balanced palette (colorful but not too intense)
HEAT_GENERATOR_COLORS = {
    "boi_gas": "#c96b66",          # Gas boiler - muted brick red
    "boi_oil": "#b7863d",          # Oil boiler - muted amber
    "boi_wood": "#8b5e3c",         # Wood boiler - earthy brown
    "boi_pel": "#9a6a45",          # Pellet boiler - lighter wood brown
    "chp": "#a45b7a",              # CHP / BHKW - muted plum rose
    "dh": "#7f9a52",               # District heating - olive green
    "eh": "#5f8fb5",               # Electric heater - steel blue
    "eh_hp": "#4f82af",            # EH for HP - mid blue
    "eh_tes": "#44759f",           # EH for TES - deep blue
    "eh_dhw": "#38698f",           # EH for DHW - darker blue
    "hp_air": "#66a8b5",           # Heat pump air - muted turquoise
    "hp_ground": "#3f7f6f",        # Heat pump ground - deep teal green
    "hp_geo_col": "#4b8a6f",       # HP geo collector - green-teal
    "hp_geo_probe": "#356f78",     # HP geo probe - cool deep teal
    "dhw": "#7f7aa7",              # DHW heater - muted violet
}

# Solar - Warm gold family (aligned with wall tones)
SOLAR_COLORS = {
    "pv": "#e0b756",               # Photovoltaic - balanced gold
    "stc": "#cf8f2e",              # Solar thermal - deeper amber
    "stc_fp": "#cf8f2e",           # STC flat plate - alias of STC
    "stc_vt": "#b97d28",           # STC vacuum tube - slightly darker amber
}

# Storage - Teal/blue family (complementary to envelope orange)
STORAGE_COLORS = {
    "tes": "#79bbb5",              # Thermal energy storage - deep teal
    "tes_dhw": "#a8acca",          # TES for DHW - medium teal
    "bat": "#5b9fbf",              # Battery - muted cyan-blue
}

# ============================================================================
# CATEGORY: GEBÄUDEHÜLLE (Building Envelope)
# ============================================================================

BUILDING_ENVELOPE_COLORS = {
    # Roof - Blue family (light → dark by level)
    "roof_1": "#aed9f0",           # Level 1 - light blue
    "roof_2": "#4a9ad4",           # Level 2 - medium blue
    "roof_3": "#1f5f8b",           # Level 3 - dark blue
    
    # Wall - Orange family
    "wall_1": "#ffe0b8",           # Level 1 - light orange
    "wall_2": "#ffaa4d",           # Level 2 - medium orange
    "wall_3": "#cc6600",           # Level 3 - dark orange
    
    # Window - Green family
    "win_1": "#a8eba8",            # Level 1 - light green
    "win_2": "#4dc74d",            # Level 2 - medium green
    "win_3": "#1a7a1a",            # Level 3 - dark green
}

# ============================================================================
# CATEGORY: ÜBERGABESYSTEM (Transfer/Distribution Systems)
# ============================================================================


DISTRIBUTION_COLORS = {
    # Radiator-based systems - warm family with clear level steps
    "rad_11": "#d59a5f",           # Radiator level 1 - muted apricot
    "rad_22": "#c8704f",           # Radiator level 2 - terracotta
    "rad_33": "#9a5b43",           # Radiator level 3 - deep copper-brown

    # Underfloor heating - clearly distinct cool accent
    "ufh": "#cf4949",              # Underfloor heating - muted azure
}

# ============================================================================
# CATEGORY: ENERGIETRÄGER (Energy Carriers)
# ============================================================================

ENERGY_CARRIER_COLORS = {
    "gas": "#e07b39",               # Natural gas - warm orange
    "biogas": "#6aa84f",              # Biogas - green (renewable)
    "el_grid": "#3b82f6",           # Grid electricity - blue
    "el_hp_grid": "#60a5fa",        # HP electricity from grid - lighter blue
    "el_pv_grid": "#facc15",        # PV electricity to grid - solar yellow
    "el_chp_grid": "#a78bfa",       # CHP electricity to grid - violet
    "oil": "#6b7280",               # Oil - grey
    "pel": "#92400e",               # Pellets - dark brown
    "sol": "#f59e0b",               # Solar thermal - amber
    "th_dh": "#22c55e",             # District heating - green
}

# ============================================================================
# CONSOLIDATED MAPPINGS
# ============================================================================

# All technology color definitions
ALL_TECHNOLOGY_COLORS = {
    **HEAT_GENERATOR_COLORS,
    **SOLAR_COLORS,
    **STORAGE_COLORS,
    **BUILDING_ENVELOPE_COLORS,
    **DISTRIBUTION_COLORS,
}

# Category assignments for routing
TECHNOLOGY_CATEGORIES = {
    # Anlagentechnik
    "boi_gas": "anlagentechnik",
    "boi_oil": "anlagentechnik",
    "boi_wood": "anlagentechnik",
    "boi_pel": "anlagentechnik",
    "chp": "anlagentechnik",
    "dh": "anlagentechnik",
    "eh": "anlagentechnik",
    "eh_hp": "anlagentechnik",
    "eh_tes": "anlagentechnik",
    "eh_dhw": "anlagentechnik",
    "hp_air": "anlagentechnik",
    "hp_ground": "anlagentechnik",
    "hp_geo_col": "anlagentechnik",
    "hp_geo_probe": "anlagentechnik",
    "dhw": "anlagentechnik",
    "pv": "anlagentechnik",
    "stc": "anlagentechnik",
    "stc_fp": "anlagentechnik",
    "stc_vt": "anlagentechnik",
    "tes": "anlagentechnik",
    "tes_dhw": "anlagentechnik",
    "bat": "anlagentechnik",
    
    # Gebäudehülle
    "roof": "gebaeudehuelle",
    "wall": "gebaeudehuelle",
    "win": "gebaeudehuelle",
    
    # Übergabesystem
    "rad": "uebergabesystem",
    "ufh": "uebergabesystem",
}


def classify_technology(measure: str) -> str:
    """
    Classify a technology/measure into a category.
    
    Returns:
        "anlagentechnik", "gebaeudehuelle", "uebergabesystem", or "unknown"
    """
    # Check direct mapping first
    if measure in TECHNOLOGY_CATEGORIES:
        return TECHNOLOGY_CATEGORIES[measure]
    
    # Check prefixes
    for prefix in ("roof", "wall", "win"):
        if measure.startswith(prefix):
            return "gebaeudehuelle"
    
    for prefix in ("boi", "hp", "dhw", "pv", "stc", "tes", "bat", "chp", "dh", "eh"):
        if measure.startswith(prefix):
            return "anlagentechnik"
    
    for prefix in ("rad", "ufh"):
        if measure.startswith(prefix):
            return "uebergabesystem"
    
    return "unknown"


def get_technology_color(measure: str) -> str:
    """
    Get the color for a specific technology/measure.
    
    Requires explicit color definitions; raises an error if undefined.
    
    Args:
        measure: Technology/measure name (e.g., "boi_gas", "roof_2", "hp_air")
        
    Returns:
        Hex color code
    """
    # Direct lookup
    if measure in ALL_TECHNOLOGY_COLORS:
        return ALL_TECHNOLOGY_COLORS[measure]
    
    # Try to extract the base type and level
    # E.g., "roof_3" → "roof_3", "roof_1_extra" → "roof_1"
    if "_" in measure:
        parts = measure.split("_")
        # Try combinations of prefix + level
        for i in range(len(parts), 0, -1):
            candidate = "_".join(parts[:i])
            if candidate in ALL_TECHNOLOGY_COLORS:
                return ALL_TECHNOLOGY_COLORS[candidate]
    
    raise KeyError(f"No color defined for technology '{measure}'")


def get_category_color_palette() -> Dict[str, list]:
    """
    Return color palettes organized by category.
    
    Useful for charts that need multiple distinct colors within a category.
    """
    return {

        "anlagentechnik": [
            # Heat generators
            "#c96b66", "#b7863d", "#8b5e3c", "#9a6a45", "#a45b7a", "#7f9a52",
            # Electric heaters
            "#5f8fb5", "#4f82af", "#44759f", "#38698f",
            # Heat pumps
            "#66a8b5", "#3f7f6f", "#4b8a6f", "#356f78", "#7f7aa7",
            # Solar
            "#e0b756", "#cf8f2e", "#cf8f2e", "#b97d28",
            # Storage
            "#6aaca4", "#8c91b6", "#5b9fbf",
        ],
        "gebaeudehuelle": [
            # Roof
            "#aed9f0", "#4a9ad4", "#1f5f8b",
            # Wall
            "#ffe0b8", "#ffaa4d", "#cc6600",
            # Window
            "#a8eba8", "#4dc74d", "#1a7a1a",
        ],
        "uebergabesystem": [
            # Radiator
            "#d59a5f", "#c8704f", "#9a5b43",
            # UFH
            "#5f8ea8",
        ],
    }


def get_energy_carrier_color(carrier: str) -> str:
    """
    Get the color for a specific energy carrier.

    Falls back to a deterministic hash-based color if no explicit mapping exists.
    """
    if carrier in ENERGY_CARRIER_COLORS:
        return ENERGY_CARRIER_COLORS[carrier]
    # Deterministic fallback
    import hashlib
    h = int(hashlib.md5(carrier.encode()).hexdigest()[:6], 16)
    r = 60 + (h % 160)
    g = 60 + ((h >> 8) % 160)
    b = 60 + ((h >> 16) % 160)
    return f"#{r:02x}{g:02x}{b:02x}"
