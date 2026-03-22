"""
Use-case management: discover use cases and load processed JSON results.

Folder structure:
    results/optiport/{scenario}/{mode}/processed_results/portfolio_results.json

where {mode} is e.g. state_heuristic, compact, benders_mixed_y, benders_standard, …
"""
import json
import logging
from typing import Dict, List, Optional

from .data_models import UseCaseMetadata, ProcessedBuildingResult, ProcessedPortfolioResult
from config.app_config import (
    USE_CASES_PATH,
    get_processed_results_path,
    get_scenarios_root,
    get_input_path,
)

logger = logging.getLogger(__name__)

# Preferred mode order for auto-detection
_MODE_PRIORITY = ["state_heuristic", "compact"]


class UseCaseManager:
    """Discovers and loads processed JSON results for optiport runs."""

    # ------------------------------------------------------------------
    # Use-case discovery
    # ------------------------------------------------------------------

    def discover_use_cases(self) -> List[UseCaseMetadata]:
        """
        Scan USE_CASES_PATH for subdirectories that contain data/input/.
        Returns all use cases alphabetically — no results check.
        Raises RuntimeError if USE_CASES_PATH does not exist.
        """
        if not USE_CASES_PATH.exists():
            raise RuntimeError(f"use_cases directory not found: {USE_CASES_PATH}")

        found: List[UseCaseMetadata] = []
        for candidate in sorted(USE_CASES_PATH.iterdir()):
            if not candidate.is_dir() or candidate.name.startswith("."):
                continue
            if not (candidate / "data" / "input").exists():
                continue
            found.append(UseCaseMetadata(
                name=candidate.name,
                path=candidate,
                results_path=get_scenarios_root(candidate.name),
                building_ids=[],
            ))
        return found

    # ------------------------------------------------------------------
    # Scenario discovery
    # ------------------------------------------------------------------

    def discover_scenarios(self, use_case_name: str) -> List[str]:
        """
        Return sorted list of scenario names under results/optiport/.

        A subfolder qualifies when it contains run_settings.json
        OR any {mode}/processed_results/portfolio_results.json
        OR any {mode}/{weight_dir}/processed_results/portfolio_results.json.
        """
        root = get_scenarios_root(use_case_name)
        if not root.exists():
            return []

        names: List[str] = []
        for candidate in sorted(root.iterdir()):
            if not candidate.is_dir() or candidate.name.startswith("."):
                continue

            # Has run_settings.json → it's a scenario folder
            if (candidate / "run_settings.json").exists():
                names.append(candidate.name)
                continue

            # Has any {mode}/processed_results/portfolio_results.json
            # or {mode}/{weight}/processed_results/portfolio_results.json
            found = False
            for mode_dir in sorted(candidate.iterdir()):
                if not mode_dir.is_dir():
                    continue
                if (mode_dir / "processed_results" / "portfolio_results.json").exists():
                    found = True
                    break
                # Check weight subdirectories
                for weight_dir in sorted(mode_dir.iterdir()):
                    if not weight_dir.is_dir():
                        continue
                    if (weight_dir / "processed_results" / "portfolio_results.json").exists():
                        found = True
                        break
                if found:
                    break
            if found:
                names.append(candidate.name)

        return sorted(names)

    def find_processed_mode(self, use_case_name: str, scenario: str) -> Optional[str]:
        """
        Auto-detect which mode subfolder has processed results.
        Checks both direct processed_results/ and weight-subfolder layouts.
        Priority: state_heuristic → compact → any other (alphabetical).
        Returns mode name or None.
        """
        root = get_scenarios_root(use_case_name)
        scenario_dir = root / scenario

        if not scenario_dir.exists():
            return None

        def _has_processed(mode_path):
            """Check direct or weight-subfolder processed results."""
            if (mode_path / "processed_results" / "portfolio_results.json").exists():
                return True
            # Check weight subdirs
            if mode_path.exists():
                for child in mode_path.iterdir():
                    if child.is_dir() and (child / "processed_results" / "portfolio_results.json").exists():
                        return True
            return False

        # Check priority modes first
        for mode in _MODE_PRIORITY:
            if _has_processed(scenario_dir / mode):
                return mode

        # Fall back to any other subfolder alphabetically
        for d in sorted(scenario_dir.iterdir()):
            if not d.is_dir():
                continue
            if _has_processed(d):
                return d.name

        return None

    def has_results(self, use_case_name: str, scenario: str) -> bool:
        """Return True if any mode subfolder has processed results for this scenario."""
        return self.find_processed_mode(use_case_name, scenario) is not None

    # ------------------------------------------------------------------
    # Weight variant discovery (state_heuristic multi-weight support)
    # ------------------------------------------------------------------

    def discover_weight_variants(
        self, use_case_name: str, scenario: str, mode: str = None,
    ) -> List[Dict]:
        """
        Discover weight-encoded subdirectories under a mode folder.

        Returns a list of dicts with keys: phi_eq, phi_em, phi_warm, dirname.
        Empty list if no weight variants found (e.g. compact mode or legacy layout).
        """
        if mode is None:
            mode = self.find_processed_mode(use_case_name, scenario)
        if mode is None:
            return []

        mode_dir = get_scenarios_root(use_case_name) / scenario / mode
        if not mode_dir.exists():
            return []

        variants = []
        for child in sorted(mode_dir.iterdir()):
            if not child.is_dir():
                continue
            parts = child.name.split("_")
            if len(parts) != 3:
                continue
            try:
                phi_eq = float(parts[0])
                phi_em = float(parts[1])
                phi_warm = float(parts[2])
            except ValueError:
                continue
            if (child / "processed_results" / "portfolio_results.json").exists():
                variants.append({
                    "phi_eq": phi_eq,
                    "phi_em": phi_em,
                    "phi_warm": phi_warm,
                    "dirname": child.name,
                })
        return variants

    # ------------------------------------------------------------------
    # run_settings.json helpers
    # ------------------------------------------------------------------

    def load_run_settings(self, use_case_name: str, scenario: str) -> Dict:
        """Load run_settings.json for a scenario. Returns {} if not found."""
        path = get_scenarios_root(use_case_name) / scenario / "run_settings.json"
        if not path.exists():
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning("Could not load run_settings.json for '%s/%s': %s", use_case_name, scenario, e)
            return {}

    def save_run_settings(self, use_case_name: str, scenario: str, data: Dict) -> None:
        """Write run_settings.json for a scenario."""
        path = get_scenarios_root(use_case_name) / scenario / "run_settings.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Result loaders
    # ------------------------------------------------------------------

    def load_portfolio_results(
        self,
        use_case_name: str,
        scenario: str = None,
        mode: str = None,
        weight_dirname: str = None,
    ) -> ProcessedPortfolioResult:
        """Load portfolio_results.json for the given use case, scenario and mode.

        Args:
            weight_dirname: Optional weight subfolder (e.g. "0.5_0.25_0.25").
                When provided, results are loaded from {mode}/{weight_dirname}/processed_results/.
        """
        # Auto-detect mode if not supplied
        if scenario and mode is None:
            mode = self.find_processed_mode(use_case_name, scenario)
            if mode is None:
                raise FileNotFoundError(
                    f"No processed results found for scenario '{scenario}' in use case '{use_case_name}'"
                )

        results_path = get_processed_results_path(use_case_name, scenario, mode)
        if weight_dirname:
            # Adjust: go up from processed_results, into weight subdir
            results_path = results_path.parent / weight_dirname / "processed_results"
        portfolio_file = results_path / "portfolio_results.json"

        if not portfolio_file.exists():
            # Fallback: try the first available weight subfolder
            if not weight_dirname:
                variants = self.discover_weight_variants(use_case_name, scenario, mode)
                if variants:
                    results_path = results_path.parent / variants[0]["dirname"] / "processed_results"
                    portfolio_file = results_path / "portfolio_results.json"

        if not portfolio_file.exists():
            raise FileNotFoundError(f"portfolio_results.json not found: {portfolio_file}")

        with open(portfolio_file, "r", encoding="utf-8") as f:
            d = json.load(f)

        return ProcessedPortfolioResult(
            total_buildings=d["total_buildings"],
            building_ids=d["building_ids"],
            capacity_available_total=d["capacity_available_total"],
            capacity_installed_total=d["capacity_installed_total"],
            capacity_available_count=d["capacity_available_count"],
            capacity_installed_count=d["capacity_installed_count"],
            investment_by_measure_total=d.get("investment_by_measure_total", {}),
            costs_investment=d["costs_investment"],
            costs_operational=d["costs_operational"],
            costs_total=d["costs_total"],
            emissions_embodied=d["emissions_embodied"],
            emissions_operational=d["emissions_operational"],
            emissions_total=d["emissions_total"],
            thermal_demand=d["thermal_demand"],
            rent_total=d.get("rent_total", {}),
            energy_costs_total=d.get("energy_costs_total", {}),
            modernization_costs_total=d.get("modernization_costs_total", {}),
            emissions_energy_total=d.get("emissions_energy_total", {}),
            emissions_fossil_total=d.get("emissions_fossil_total", {}),
            liquidity=d.get("liquidity", {}),
            liquidity_critical=d.get("liquidity_critical", {}),
            equity=d.get("equity", {}),
            debt=d.get("debt", {}),
            total_emissions_optiport=d.get("total_emissions_optiport", 0.0),
            credits_total=d.get("credits_total", {}),
            warm_rent_total=d.get("warm_rent_total", {}),
            costs_investment_total=d["costs_investment_total"],
            costs_operational_total=d["costs_operational_total"],
            costs_total_all=d["costs_total_all"],
            emissions_embodied_total=d["emissions_embodied_total"],
            emissions_operational_total=d["emissions_operational_total"],
            emissions_total_all=d["emissions_total_all"],
            thermal_demand_total=d["thermal_demand_total"],
            constraint_params=d.get("constraint_params", {}),
        )

    def load_building_result(
        self,
        use_case_name: str,
        building_id: int,
        scenario: str = None,
        mode: str = None,
        weight_dirname: str = None,
    ) -> ProcessedBuildingResult:
        """Load building_{building_id}_results.json."""
        if scenario and mode is None:
            mode = self.find_processed_mode(use_case_name, scenario)

        results_path = get_processed_results_path(use_case_name, scenario, mode)
        if weight_dirname:
            results_path = results_path.parent / weight_dirname / "processed_results"
        building_file = results_path / f"building_{building_id}_results.json"

        if not building_file.exists():
            # Fallback: try the first available weight subfolder
            if not weight_dirname:
                variants = self.discover_weight_variants(use_case_name, scenario, mode)
                if variants:
                    results_path = results_path.parent / variants[0]["dirname"] / "processed_results"
                    building_file = results_path / f"building_{building_id}_results.json"

        if not building_file.exists():
            raise FileNotFoundError(f"building_{building_id}_results.json not found: {building_file}")

        with open(building_file, "r", encoding="utf-8") as f:
            d = json.load(f)

        return ProcessedBuildingResult(
            building_id=d["building_id"],
            building_type=d["building_type"],
            construction_year=d["construction_year"],
            transformation_pathway=d["transformation_pathway"],
            operational_data=d["operational_data"],
            totals=d["totals"],
            optiport_data=d.get("optiport_data", {}),
        )

    def load_all_building_results(
        self,
        use_case_name: str,
        scenario: str = None,
        mode: str = None,
        weight_dirname: str = None,
    ) -> List[ProcessedBuildingResult]:
        """Load all building JSON files for a scenario, auto-detecting mode."""
        # Detect mode once, reuse for all building loads
        if scenario and mode is None:
            mode = self.find_processed_mode(use_case_name, scenario)

        portfolio = self.load_portfolio_results(use_case_name, scenario, mode, weight_dirname=weight_dirname)
        return [
            self.load_building_result(use_case_name, bid, scenario, mode, weight_dirname=weight_dirname)
            for bid in sorted(portfolio.building_ids)
        ]
