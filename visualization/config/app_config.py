"""
Configuration settings for the OptiPort Visualization Application
"""
from pathlib import Path

# Application settings
APP_TITLE = "OptiPort WebApp Prototyp"
APP_ICON = "🏭"
LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
USE_CASES_PATH = PROJECT_ROOT / "run" / "use_cases"


def get_processed_results_path(use_case: str, scenario: str = None, mode: str = None) -> Path:
    """Return the processed_results directory for a given use case.

    Structure: results/optiport/{scenario}/{mode}/processed_results/
    If no scenario/mode given, falls back to results/optiport/processed_results/.
    """
    if scenario and mode:
        return USE_CASES_PATH / use_case / "results" / "optiport" / scenario / mode / "processed_results"
    if scenario:
        return USE_CASES_PATH / use_case / "results" / "optiport" / scenario / "processed_results"
    return USE_CASES_PATH / use_case / "results" / "optiport" / "processed_results"


def get_scenarios_root(use_case: str) -> Path:
    """Return the root folder containing all scenario subfolders for a use case."""
    return USE_CASES_PATH / use_case / "results" / "optiport"


def get_input_path(use_case: str) -> Path:
    """Return the input data folder for a use case."""
    return USE_CASES_PATH / use_case / "data" / "input"


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
