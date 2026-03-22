"""
Optimization runner for testing both compact and Benders approaches.
"""

import sys
from pathlib import Path
import time
from typing import Dict, Optional
from dataclasses import dataclass
import pickle

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from gurobipy import GRB

from config import settings, paths
from pre_processing.orchestration.data_controller import get_instance_data
from optimization.integrated.compact.solve import solve_compact
from optimization.integrated.benders.solve import solve_benders
import run.testing.config as test_config
from run.testing.logger import get_logger


@dataclass
class OptimizationResult:
    """Store optimization results from a single run."""
    use_case_name: str
    mode: str
    status: Optional[int] = None
    status_name: Optional[str] = None
    objective_value: Optional[float] = None
    runtime: Optional[float] = None
    mip_gap: Optional[float] = None
    num_variables: Optional[int] = None
    num_constraints: Optional[int] = None
    error_message: Optional[str] = None
    solution_file: Optional[Path] = None
    
    def is_optimal(self) -> bool:
        """Check if the run terminated with optimal status."""
        return self.status == GRB.OPTIMAL
    
    def is_successful(self) -> bool:
        """Check if the run completed without errors."""
        return self.error_message is None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'use_case_name': self.use_case_name,
            'mode': self.mode,
            'status': self.status,
            'status_name': self.status_name,
            'objective_value': self.objective_value,
            'runtime': self.runtime,
            'mip_gap': self.mip_gap,
            'num_variables': self.num_variables,
            'num_constraints': self.num_constraints,
            'error_message': self.error_message,
            'solution_file': str(self.solution_file) if self.solution_file else None
        }


def _get_status_name(status_code: int) -> str:
    """Convert Gurobi status code to human-readable name."""
    status_names = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.CUTOFF: "CUTOFF",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        GRB.NODE_LIMIT: "NODE_LIMIT",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NUMERIC: "NUMERIC",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INPROGRESS: "INPROGRESS",
        GRB.USER_OBJ_LIMIT: "USER_OBJ_LIMIT",
    }
    return status_names.get(status_code, f"UNKNOWN({status_code})")


def _override_algorithm_settings():
    """Override algorithm settings with testing configuration."""
    if test_config.TIME_LIMIT is not None:
        settings.algorithm_settings.shared.timelimit = test_config.TIME_LIMIT
    else:
        settings.algorithm_settings.shared.timelimit = None
    
    settings.algorithm_settings.shared.MIPGap = test_config.MIP_GAP
    settings.algorithm_settings.shared.threads = test_config.THREADS
    
    settings.algorithm_settings.compact.save_lp = test_config.SAVE_LP_FILES
    settings.algorithm_settings.compact.save_ilp = test_config.SAVE_ILP_FILES
    
    if settings.algorithm_settings.benders.rmp:
        settings.algorithm_settings.benders.rmp.save_lp = test_config.SAVE_LP_FILES
        settings.algorithm_settings.benders.rmp.save_ilp = test_config.SAVE_ILP_FILES
    
    if settings.algorithm_settings.benders.sps:
        settings.algorithm_settings.benders.sps.save_lp = test_config.SAVE_LP_FILES
        settings.algorithm_settings.benders.sps.save_ilp = test_config.SAVE_ILP_FILES


def run_optimization(use_case_name: str, mode: str, benders_variant: str = None) -> OptimizationResult:
    """Run optimization for a specific use case and mode.

    Args:
        use_case_name: Name of the use case to optimize
        mode: Either "compact" or "benders"
        benders_variant: If mode is "benders", specifies which variant to use (e.g., "standard", "no_y")
    """
    logger = get_logger()
    mode_label = f"{mode}_{benders_variant}" if mode == "benders" and benders_variant else mode
    logger.info(f"Running {mode_label} optimization: {use_case_name}")

    result = OptimizationResult(use_case_name=use_case_name, mode=mode_label)

    general_settings_dict = {
        "name": mode_label,
        "mode": mode,
        "use_case": use_case_name,
        "overwrite_building_data": test_config.OVERWRITE_BUILDING_DATA,
        "overwrite_portfolio_data": test_config.OVERWRITE_PORTFOLIO_DATA,
        "threads": test_config.THREADS,
        "optiport_model": True,  # Default to OptiPort model for testing
    }
    
    benders_decomp_name = settings.derive_benders_decomp_name() if mode == "benders" else None
    paths.init_dirs(name=general_settings_dict["name"], use_case=use_case_name, benders_decomp_name=benders_decomp_name, optiport_model=general_settings_dict["optiport_model"])
    settings.init_settings(general_settings_dict=general_settings_dict)
    _override_algorithm_settings()
    
    logger.debug("Loading instance data")
    instance_data = get_instance_data()
    
    start_time = time.time()
    
    if mode == "compact":
        logger.verbose("Solving with compact model")
        model = solve_compact(instance_data)
    elif mode == "benders":
        logger.verbose("Solving with Benders decomposition")
        model = solve_benders(instance_data)
    else:
        raise ValueError(f"Unknown mode: {mode}")
    
    result.runtime = time.time() - start_time
    
    logger.debug("Extracting results from solution files")
    _extract_results(result, use_case_name, mode)
    
    logger.info(
        f"Completed {mode}: {result.status_name}, "
        f"{'obj=' + f'{result.objective_value:.2f}' if result.is_optimal() else ''} "
        f"runtime={result.runtime:.1f}s"
    )

    # try:
    #     general_settings_dict = {
    #         "mode": mode,
    #         "use_case": use_case_name,
    #         "overwrite_building_data": test_config.OVERWRITE_BUILDING_DATA,
    #         "overwrite_portfolio_data": test_config.OVERWRITE_PORTFOLIO_DATA,
    #         "threads": test_config.THREADS,
    #     }
        
    #     paths.init_dirs(use_case_name)
    #     settings.init_settings(general_settings_dict=general_settings_dict)
    #     _override_algorithm_settings()
        
    #     logger.debug("Loading instance data")
    #     instance_data = get_instance_data()
        
    #     start_time = time.time()
        
    #     if mode == "compact":
    #         logger.verbose("Solving with compact model")
    #         model = solve_compact(instance_data)
    #     elif mode == "benders":
    #         logger.verbose("Solving with Benders decomposition")
    #         model = solve_benders(instance_data)
    #     else:
    #         raise ValueError(f"Unknown mode: {mode}")
        
    #     result.runtime = time.time() - start_time
        
    #     logger.debug("Extracting results from solution files")
    #     _extract_results(result, use_case_name, mode)
        
    #     logger.info(
    #         f"Completed {mode}: {result.status_name}, "
    #         f"{'obj=' + f'{result.objective_value:.2f}' if result.is_optimal() else ''} "
    #         f"runtime={result.runtime:.1f}s"
    #     )
        
    # except Exception as e:
    #     result.error_message = str(e)
    #     logger.error(f"Failed {mode} optimization: {e}")
        
    #     if not test_config.CONTINUE_ON_ERROR:
    #         raise
    
    return result


def _extract_results(result: OptimizationResult, use_case_name: str, mode: str):
    """Extract results from solution files."""
    if mode == "compact":
        sol_file = paths.directories.compact_solution_file(use_case_name, format="sol")
        
        if sol_file.exists():
            result.solution_file = sol_file
            result.status = GRB.OPTIMAL
            result.status_name = "OPTIMAL"
            result.objective_value = _parse_sol_file_objective(sol_file)
        else:
            ilp_file = paths.directories.compact_model_file(format="ilp")
            if ilp_file.exists():
                result.status = GRB.INFEASIBLE
                result.status_name = "INFEASIBLE"
            else:
                result.status_name = "UNKNOWN"
    
    elif mode == "benders":
        benders_sol = paths.directories.benders_solution_file("benders_results")
        infeasible_sol = paths.directories.benders_solutions_dir / "infeasible.sol"
        
        if benders_sol.exists():
            result.solution_file = benders_sol
            result.status = GRB.OPTIMAL
            result.status_name = "OPTIMAL"
            result.objective_value = _parse_sol_file_objective(benders_sol)
        elif infeasible_sol.exists():
            result.status = GRB.INFEASIBLE
            result.status_name = "INFEASIBLE"
        else:
            result.status_name = "UNKNOWN"


def _parse_sol_file_objective(sol_file: Path) -> Optional[float]:
    """Parse Gurobi .sol file to extract objective value."""
    try:
        with open(sol_file, 'r') as f:
            for line in f:
                if line.startswith("# Objective value"):
                    parts = line.split("=")
                    if len(parts) == 2:
                        return float(parts[1].strip())
        return None
    except Exception as e:
        get_logger().warning(f"Could not parse objective from {sol_file}: {e}")
        return None


def run_all_approaches(use_case_name: str) -> Dict[str, OptimizationResult]:
    """Run compact (if configured) and all Benders variants for a use case.

    Returns:
        Dictionary mapping approach names to OptimizationResults.
        Keys are: "compact" (if enabled), "benders_standard", "benders_no_y", etc.
    """
    results = {}

    # Run compact if configured
    if test_config.compare_compact:
        results['compact'] = run_optimization(use_case_name, "compact")

    # Run all Benders variants
    for variant in test_config.benders_variants:
        variant_key = f"benders_{variant}"
        results[variant_key] = run_optimization(use_case_name, "benders", benders_variant=variant)

    return results


def run_both_approaches(use_case_name: str) -> Dict[str, OptimizationResult]:
    """Legacy function for backward compatibility. Runs compact and standard Benders."""
    return {
        'compact': run_optimization(use_case_name, "compact"),
        'benders': run_optimization(use_case_name, "benders", benders_variant="standard")
    }


def main():
    """Test the optimization runner on a single use case."""
    test_use_case = "synth_portfolio"
    results = run_both_approaches(test_use_case)
    
    logger = get_logger()
    logger.section("COMPARISON SUMMARY")
    for mode, result in results.items():
        logger.info(f"{mode.upper()}: {result.status_name}, runtime={result.runtime:.2f}s")
        if result.is_optimal():
            logger.info(f"  Objective: {result.objective_value:.6f}")
        if result.error_message:
            logger.error(f"  Error: {result.error_message}")


if __name__ == "__main__":
    main()
