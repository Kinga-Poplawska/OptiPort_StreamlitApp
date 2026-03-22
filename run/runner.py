# inbuilt libraries
import sys
from pathlib import Path
import json
import datetime
import types

# project libraries
from config import settings, paths
from pre_processing.orchestration.data_controller import get_instance_data
from optimization.integrated.compact.solve import solve_compact
from optimization.integrated.benders.solve import solve_benders
from optimization.integrated.m4k_algo import solve_m4k
from post_processing import pipeline
from optimization.two_stage import solve_two_stage
from optimization.state_heuristic import solve_state_heuristic


def runner(general_settings_dict):
    """
    Function that organizes the subscripts and runs optimizations for instances of an instance set or runs an optimization of a single instance for
    given specifications..

    """
    # check_and_persist_settings(general_settings_dict)  # TODO: deal with this later

    # solve the optimization problem
    # Each branch loads only the data it actually needs so that
    # get_instance_data() is never called more than necessary.

    # ---- Optional payoff-table normalization --------------------
    # When enabled, solve 3 single-objective compact models first to
    # determine objective value ranges.  The resulting normalization
    # factors are stored in settings and applied during model building.
    #
    # Skipped for state_heuristic mode: the heuristic pipeline computes
    # its own per-building (Phase 1) and portfolio-level (Phase 4½)
    # payoff tables internally, avoiding the intractable full-portfolio
    # compact model.
    if (
        settings.general_settings.optiport_model
        and settings.portfolio_settings.normalize_objectives
        and settings.portfolio_settings.normalization_factors is None
        and settings.general_settings.mode != "state_heuristic"
    ):
        from optimization.integrated.scaling_utils.payoff_table import compute_payoff_table

        norm_instance = get_instance_data()
        payoff = compute_payoff_table(norm_instance)
        if payoff:
            settings.portfolio_settings.normalization_factors = payoff
            print(f"Payoff-table normalization active — {len(payoff)} objectives normalized.")
        else:
            print("WARNING: payoff-table computation failed; proceeding without normalization.")

    if settings.general_settings.mode == "compact":
        instance_data = get_instance_data()
        solve_compact(
            instance_data
            )

    elif settings.general_settings.mode == "benders":
        instance_data = get_instance_data()
        solve_benders(
            instance_data
            )

    elif settings.general_settings.mode == "two_stage":
        instance_data = get_instance_data()
        solve_two_stage(
            phis_obj_two_stage=settings.portfolio_settings.phis_obj_two_stage,
            instance_data=instance_data,
        )

    elif settings.general_settings.mode == "m4k_algo":
        instance_data = get_instance_data()
        solve_m4k(
            instance_data=instance_data,
        )

    elif settings.general_settings.mode == "state_heuristic":
        # Both regular-TP (Phase 1) and all-TP (Phases 2-5) data are needed.
        # Generate them here so the pipeline does not have to call
        # get_instance_data() internally, avoiding a redundant third generation
        # when overwrite_portfolio_data=True.
        instance_data, to_compute = get_instance_data(return_meta=True)
        instance_data_all_tp, to_compute_all_tp = get_instance_data(all_time_periods=True, return_meta=True)

        # Determine which buildings must have their first-stage solutions re-solved
        # because their underlying pre-processing data was recomputed.
        if settings.general_settings.no_overwrite_results:
            # DEBUG mode: never re-solve existing solutions regardless of what changed
            force_recompute_buildings = set()
        else:
            # If portfolio data was recomputed, ALL buildings are affected.
            # If only specific building data changed, only those buildings are affected.
            if to_compute["portfolio_data"] or to_compute_all_tp["portfolio_data"]:
                force_recompute_buildings = set(instance_data["sets"]["buildings"])
            else:
                force_recompute_buildings = (
                    set(to_compute["buildings"]) | set(to_compute_all_tp["buildings"])
                )

        all_phase5_results = solve_state_heuristic(
            instance_data=instance_data,
            instance_data_all_tp=instance_data_all_tp,
            force_recompute_buildings=force_recompute_buildings,
        )

    else:
        raise ValueError("Unknown mode: {}".format(settings.general_settings.mode))

    # Post-processing: generate plots for the portfolio
    print("\n" + "=" * 80)
    print("Starting post-processing pipeline...")
    print("=" * 80)

    if settings.general_settings.mode == "state_heuristic":
        # Run post-processing for each weight combination
        from optimization.state_heuristic.path_utils import (
            get_solutions_dir as _sh_solutions_dir,
            get_processed_results_dir as _sh_processed_dir,
        )
        for (w_eq, w_em, w_warm), res in all_phase5_results.items():
            if res.get("solution_file") is None:
                print(f"  Skipping post-processing for φ=({w_eq},{w_em},{w_warm}) "
                      f"— no solution.")
                continue
            sol_file = _sh_solutions_dir(w_eq, w_em, w_warm) / "heuristic_results.sol"
            out_dir = _sh_processed_dir(w_eq, w_em, w_warm)
            print(f"\n  Post-processing φ=({w_eq},{w_em},{w_warm}) …")
            pipeline.run_post_processing_pipeline(
                general_settings_dict=general_settings_dict,
                output_folder_override=out_dir,
                sol_file_override=sol_file,
            )
    else:
        pipeline.run_post_processing_pipeline(general_settings_dict=general_settings_dict)



def _get_settings_snapshot() -> str:
    """Return a JSON string snapshot of all settings for comparison and persistence."""
    raw = {}
    for key, val in vars(settings).items():
        if key.startswith('_') or isinstance(val, (types.ModuleType, type, types.FunctionType)):
            continue
        try:
            raw[key] = json.loads(json.dumps(vars(val) if hasattr(val, '__dict__') else val, default=str))
        except Exception:
            raw[key] = str(val)
    return json.dumps(raw, indent=2, sort_keys=True, default=str)


def check_and_persist_settings(general_settings_dict: dict) -> None:
    model_mode_root: Path = paths.directories.model_mode_root
    current_snapshot = _get_settings_snapshot()

    # Collect all candidate folders: the base root + any timestamped siblings
    parent = model_mode_root.parent
    base_name = model_mode_root.name
    candidate_folders = [model_mode_root] + sorted(
        p for p in parent.iterdir()
        if p.is_dir() and p.name.startswith(f"{base_name}_")
    )

    # Check if any existing folder has a matching snapshot
    matching_folder = None
    for folder in candidate_folders:
        json_path = folder / "run_settings.json"
        if json_path.exists():
            previous_snapshot = json_path.read_text(encoding="utf-8")
            if previous_snapshot == current_snapshot:
                matching_folder = folder
                break

    if matching_folder is not None:
        print(f"[settings] Existing settings match – reusing folder: {matching_folder}")
        paths.directories.model_mode_root = matching_folder
        # No need to rewrite the JSON, it already matches
    else:
        # No matching folder found – check if base folder already has a settings file
        base_json = model_mode_root / "run_settings.json"
        if base_json.exists():
            # Base folder exists but differs → create a new timestamped folder
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            new_root = parent / f"{base_name}_{timestamp}"
            new_root.mkdir(parents=True, exist_ok=True)
            print(
                f"[settings] No matching settings found among existing folders.\n"
                f"           Results will be written to: {new_root}"
            )
            paths.directories.model_mode_root = new_root
            (new_root / "run_settings.json").write_text(current_snapshot, encoding="utf-8")
        else:
            # Base folder is fresh – use it as-is
            model_mode_root.mkdir(parents=True, exist_ok=True)
            print(f"[settings] No previous settings found. Saving to: {model_mode_root}")
            base_json.write_text(current_snapshot, encoding="utf-8")
