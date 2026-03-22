# inbuilt libraries
import sys

# installed libraries
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from multiprocessing import freeze_support

# project libraries
from run.runner import runner
from config import settings, paths
 

if __name__ == "__main__":  
    freeze_support()

    # general settings
    general_settings_dict = {
        "name": "Test", #name of the optimization run, used for naming results folders
        "mode": "state_heuristic",  # options: "compact", "benders", "two_stage", "m4k_algo", "state_heuristic"
        "use_case": "Optiport_test",
        "overwrite_building_data": False,   # should existing building data be overwritten?
        "overwrite_portfolio_data": False,  # should existing portfolio datas be overwritten? Also overwrites Benders data structures
        "threads": 8,  # number of parallel threads for multiprocessing  # TODO: dublication with global settings?
        "optiport_model": True,  # If True, use OptiPort financial model; if False, use M4K cost minimization
        "no_overwrite_results": True,  # DEBUG: if True, never re-solve first-stage solutions even if pre-processing data was recomputed
    }

    # Derive benders_decomp_name from algorithm config values (before full init)
    benders_decomp_name = settings.derive_benders_decomp_name()

    # Initialize paths first (needed to load use-case-specific portfolio settings)
    paths.init_dirs(
        name=general_settings_dict["name"],
        use_case=general_settings_dict["use_case"],
        benders_decomp_name=benders_decomp_name,
        optiport_model=general_settings_dict["optiport_model"]
    )

    # Initialize settings (building_settings, portfolio_settings, algorithm_settings, and debugging_settings loaded from config modules)
    settings.init_settings(
        general_settings_dict=general_settings_dict,
    )

    runner(general_settings_dict)
