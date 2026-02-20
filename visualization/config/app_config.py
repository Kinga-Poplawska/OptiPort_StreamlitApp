"""
Configuration settings for the OptiPort Visualization Application
"""
from pathlib import Path
from typing import Dict, List, Any

# Application settings
APP_TITLE = "OptiPort WebApp Prototyp"
APP_ICON = "🏭"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
USE_CASES_PATH = PROJECT_ROOT / "run" / "use_cases"
DATA_PATH = PROJECT_ROOT / "data"
INSTANCES_PATH = DATA_PATH / "instances"

# File patterns
SOLUTION_FILE_PATTERN = "*.sol"
INSTANCE_CONFIG_FILES = [
    "building_constraints.csv",
    "financial_properties.csv", 
    "general_finances.json",
    "portfolio_caps.csv",
    "portfolio_caps.json",
    "stock_properties.csv"
]

# Variable categories for MILP solution 
VARIABLE_CATEGORIES = {
    "X": "Binäre Installationsentscheidungen",
    "E": "Energiekapazitätsvariablen", 
    "P": "Energiefluss-Variablen",
    "Q": "Betriebsvariablen",
    "Y": "Zusätzliche binäre Variablen",
    "Z": "Kontinuierliche Betriebsvariablen"
}

# Technology mappings (will be expanded based on actual data)
TECHNOLOGY_CATEGORIES = {
    "Heizung": ["boi_gas", "boi_oil", "boi_pel", "hp_air", "hp_geo_probe", "hp_geo_col", "chp", "eh", "dh"],
    "Gebäudehülle": ["wall_1", "wall_2", "wall_3", "roof_1", "roof_2", "roof_3", "win_1", "win_2", "win_3"],
    "Verteilung": ["rad_11", "rad_22", "rad_33", "ufh"],
    "Speicher": ["tes", "tes_dhw", "bat"],
    "Erneuerbare": ["pv_0", "stc_vt_0", "stc_fp_0"],
    "Anschlüsse": ["_connection"]
}

# Color schemes for visualizations
COLOR_SCHEMES = {
    "technology": {
        "heating": "#FF6B6B",
        "envelope": "#4ECDC4", 
        "distribution": "#45B7D1",
        "storage": "#96CEB4",
        "renewable": "#FECA57",
        "connection": "#DDA0DD"
    },
    "status": {
        "installed": "#2ECC71",
        "not_installed": "#E74C3C",
        "existing": "#F39C12"
    }
}
