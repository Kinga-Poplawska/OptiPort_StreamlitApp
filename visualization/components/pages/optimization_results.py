"""
Optimization results visualization page.

Fully migrated to the JSON-based architecture:
  - UseCaseManager  (core/instance_manager.py)
  - ProcessedPortfolioResult / ProcessedBuildingResult  (core/data_models.py)
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from core.data_models import ProcessedBuildingResult, ProcessedPortfolioResult
from core.instance_manager import UseCaseManager
from config.translations import get_technology_translation, get_energy_carrier_translation
from config.technology_colors import get_technology_color, classify_technology, get_energy_carrier_color
from utils.data_processing import parse_period_dict, get_energy_axis_config, get_power_axis_config, get_currency_axis_config
from visualizations.investment_analysis import InvestmentAnalysis
from visualizations.technology_mix import TechnologyMix

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_measure_period_keys(flat: dict) -> Dict[str, Dict[int, float]]:
    """Convert flat measure×period dict {"eh_t0": 1.0} → {measure: {period: value}}."""
    result: Dict[str, Dict[int, float]] = {}
    for key, value in flat.items():
        idx = key.rfind("_t")
        if idx == -1:
            continue
        measure = key[:idx]
        period_str = key[idx + 2:]
        try:
            period = int(period_str)
        except ValueError:
            continue
        result.setdefault(measure, {})[period] = value
    return result


def _parse_investment_by_measure(flat: dict) -> Dict[str, Dict[int, float]]:
    """
    Parse transformation_pathway.investment_by_measure keys.
    Keys have the form "c_inv_{measure}_t{period}": strip the "c_inv_" prefix,
    then split on the last "_t{int}".
    Example: "c_inv_boi_pel_t5" → measure="boi_pel", period=5
    """
    result: Dict[str, Dict[int, float]] = {}
    for key, value in flat.items():
        k = key[6:] if key.startswith("c_inv_") else key
        idx = k.rfind("_t")
        if idx == -1:
            continue
        measure = k[:idx]
        try:
            period = int(k[idx + 2:])
        except ValueError:
            continue
        result.setdefault(measure, {})[period] = float(value)
    return result


def _parse_embodied_by_measure(flat: dict) -> Dict[str, Dict[int, float]]:
    """
    Parse transformation_pathway.embodied_by_measure keys.
    Keys have the form "f_emb_{measure}_t{period}": strip the "f_emb_" prefix,
    then split on the last "_t{int}".
    Example: "f_emb_boi_pel_t5" → measure="boi_pel", period=5
    """
    result: Dict[str, Dict[int, float]] = {}
    for key, value in flat.items():
        k = key[6:] if key.startswith("f_emb_") else key
        idx = k.rfind("_t")
        if idx == -1:
            continue
        measure = k[:idx]
        try:
            period = int(k[idx + 2:])
        except ValueError:
            continue
        result.setdefault(measure, {})[period] = float(value)
    return result


def _full_periods(dense_period_dict: dict) -> List[int]:
    """
    Extract the complete sorted period list from a dense period-keyed dict
    (e.g. costs_investment {"t0": 0, "t1": 0, …}).
    Ensures bar charts always show every year of the planning horizon,
    even when sparse measure-keyed dicts only contain years where something happened.
    """
    result = []
    for k in dense_period_dict:
        if isinstance(k, str) and k.startswith("t"):
            try:
                result.append(int(k[1:]))
            except ValueError:
                pass
        elif isinstance(k, int):
            result.append(k)
    return sorted(result)


def _safe_parse(raw: dict) -> Dict[int, float]:
    """parse_period_dict with silent fallback to {}."""
    try:
        return parse_period_dict(raw) if raw else {}
    except (ValueError, KeyError):
        return {}


def _is_excluded_measure(measure: str) -> bool:
    """Return True for measures that should never appear in charts."""
    return "el_converter" in measure


_STORAGE_PREFIXES = ("tes", "bat")

def _is_storage_measure(measure: str) -> bool:
    """Return True for storage measures (tes, tes_dhw, bat)."""
    return measure.startswith(_STORAGE_PREFIXES)


_SOLAR_PREFIXES = ("pv", "stc")

def _is_solar_measure(measure: str) -> bool:
    """Return True for solar measures (PV, PV connection, solar thermal)."""
    return measure.startswith(_SOLAR_PREFIXES)


def _is_heat_generator(measure: str) -> bool:
    """Return True for heat-generator measures (not storage, not solar, not hull/fix/distribution)."""
    if _is_excluded_measure(measure):
        return False
    if _is_storage_measure(measure):
        return False
    if _is_solar_measure(measure):
        return False
    for prefix in ("roof", "wall", "win", "rad"):
        if measure.startswith(prefix):
            return False
    if measure == "ufh":
        return False
    return True


def _is_distribution_measure(measure: str) -> bool:
    """Return True for distribution/heating-system measures (rad, ufh)."""
    return measure.startswith("rad") or measure == "ufh"


def _load_co2_prices(use_case_name: str, opt_years: Optional[List[int]]) -> Dict[int, float]:
    """Load CO2 prices (€/kg) from yearly_inputs.xlsx, mapped to optimization periods."""
    try:
        import pandas as pd
        xlsx_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data" / "general" / "yearly_inputs.xlsx"
        )
        if not xlsx_path.exists():
            return {}
        df = pd.read_excel(xlsx_path, sheet_name="general")
        if "year" not in df.columns or "co2_price" not in df.columns:
            return {}
        # Drop rows with non-numeric year (e.g. unit rows)
        df = df.dropna(subset=["year"])
        df = df[pd.to_numeric(df["year"], errors="coerce").notna()]
        df = df[pd.to_numeric(df["co2_price"], errors="coerce").notna()]
        year_to_price = dict(zip(df["year"].astype(int), df["co2_price"].astype(float)))
        if not opt_years:
            return {}
        return {i: year_to_price.get(y, 0.0) for i, y in enumerate(opt_years)}
    except Exception:
        return {}


def _autoscale_currency_figure(fig: go.Figure, yaxis_title: str) -> Tuple[str, dict, str]:
    """Autoscale all y-values in a figure from € to k€/M€/G€ with readable ticks."""
    y_values: List[float] = []
    for trace in fig.data:
        if hasattr(trace, "y") and trace.y is not None:
            for val in trace.y:
                if val is not None:
                    y_values.append(float(val))

    axis_config = get_currency_axis_config(y_values, "€")
    scale_factor = axis_config["scale_factor"]
    unit = axis_config["unit"]

    for trace in fig.data:
        if hasattr(trace, "y") and trace.y is not None:
            raw_vals = [float(v) if v is not None else None for v in trace.y]
            if getattr(trace, "customdata", None) is None:
                trace.customdata = raw_vals
            if scale_factor != 1.0:
                trace.y = [float(v) / scale_factor if v is not None else v for v in trace.y]

        if hasattr(trace, "hovertemplate"):
            if trace.hovertemplate:
                hover = trace.hovertemplate
                if "%{y" in hover:
                    hover = re.sub(r"%\{y:[^}]*\}", "%{customdata:,.0f}", hover)
                    hover = hover.replace("%{y}", "%{customdata:,.0f}")
                hover = hover.replace(" Mrd €", " €")
                hover = hover.replace(" Mio €", " €")
                hover = hover.replace(" k€", " €")
                trace.hovertemplate = hover
            else:
                trace.hovertemplate = (
                    f"<b>%{{fullData.name}}</b><br>"
                    f"Jahr: %{{x}}<br>"
                    "Betrag: %{customdata:,.0f} €<extra></extra>"
                )

    display_title = yaxis_title.replace("k€", unit).replace("€", unit)
    yaxis_dict = dict(rangemode="tozero", tickformat=axis_config["tickformat"])
    return display_title, yaxis_dict, unit


def _load_co2_alpha() -> Dict[int, float]:
    """Load landlord CO2 share (alpha) per group from CO2_distribution.json."""
    import json
    try:
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "data" / "general" / "CO2_distribution.json"
        )
        if not path.exists():
            return {}
        with open(path, "r") as f:
            data = json.load(f)
        # Extract alpha values per group
        classes = data.get("classes", data)
        result = {}
        for group_key, group_data in classes.items():
            try:
                gid = int(group_key)
                result[gid] = float(group_data.get("landlord_share", 0.0))
            except (ValueError, TypeError):
                continue
        return result
    except Exception:
        return {}


def _load_area_map(use_case_name: str) -> Dict[int, float]:
    """Load building floor areas (m²) from stock_properties.csv.

    Returns {building_index: area_m2} using 0-based row position as key
    (matching the optimization's internal building IDs).
    """
    try:
        import pandas as pd
        stock_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input" / "stock_properties.csv"
        )
        if not stock_path.exists():
            return {}
        try:
            df = pd.read_csv(stock_path, sep=None, engine="python")
        except Exception:
            try:
                df = pd.read_csv(stock_path, sep=";")
            except Exception:
                df = pd.read_csv(stock_path, sep=",", encoding="latin1")
        if "area" not in df.columns:
            return {}
        return dict(enumerate(df["area"].astype(float)))
    except Exception:
        return {}


def _has_nonzero(d: dict) -> bool:
    """Return True if any value in a dict is truthy / nonzero."""
    if not d:
        return False
    for v in d.values():
        if isinstance(v, dict):
            if _has_nonzero(v):
                return True
        elif v:
            return True
    return False


def _get_phi_weights(use_case_name: str) -> Optional[Dict[str, float]]:
    """Read phi_eq / phi_em / phi_warm from use case portfolio_settings.py."""
    try:
        portfolio_settings_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "config" / "portfolio_settings.py"
        )
        if not portfolio_settings_path.exists():
            return None
        content = portfolio_settings_path.read_text(encoding="utf-8")
        phi_eq   = re.search(r'"phi_eq"\s*:\s*([\d\.]+)', content)
        phi_em   = re.search(r'"phi_em"\s*:\s*([\d\.]+)', content)
        phi_warm = re.search(r'"phi_warm"\s*:\s*([\d\.]+)', content)
        if phi_eq and phi_em:
            return {
                "phi_eq":   float(phi_eq.group(1)),
                "phi_em":   float(phi_em.group(1)),
                "phi_warm": float(phi_warm.group(1)) if phi_warm else 0.0,
            }
    except Exception:
        pass
    return None


def _get_optimization_years(use_case_name: str) -> Optional[List[int]]:
    """Read optimization_years list from use case portfolio_settings.py."""
    try:
        portfolio_settings_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "config" / "portfolio_settings.py"
        )
        if not portfolio_settings_path.exists():
            return None
        content = portfolio_settings_path.read_text(encoding="utf-8")
        match = re.search(r'"optimization_years"\s*:\s*\[([^\]]+)\]', content)
        if match:
            years = [int(y.strip()) for y in match.group(1).split(",") if y.strip().isdigit()]
            return years if years else None
    except Exception:
        pass
    return None


def _periods_to_years(periods: List[int], opt_years: Optional[List[int]]) -> List:
    """Map period offsets to calendar years using a dict lookup.

    Period values are year offsets from the base year (min of opt_years),
    not sequential indices.
    """
    if not opt_years:
        return periods
    base = min(opt_years)
    period_to_year = {year - base: year for year in opt_years}
    result = []
    for p in periods:
        if p not in period_to_year:
            raise ValueError(
                f"Period {p} not in optimization years. "
                f"Known period offsets: {sorted(period_to_year)}"
            )
        result.append(period_to_year[p])
    return result


def _load_initial_finance_values_from_input(
    use_case_name: str,
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """Load initial equity, debt and liquidity from use case input general_finances.json."""
    try:
        import json
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input" / "general_finances.json"
        )
        if not path.exists():
            return None, None, None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        equity_val = (data.get("equity") or {}).get("initial_equity")
        debt_val = (data.get("liabilities") or {}).get("initial_liabilities")
        liquidity_val = (data.get("liquidity") or {}).get("initial_liquidity")

        initial_equity = float(equity_val) if equity_val is not None else None
        initial_debt = float(debt_val) if debt_val is not None else None
        initial_liquidity = float(liquidity_val) if liquidity_val is not None else None
        return initial_equity, initial_debt, initial_liquidity
    except Exception:
        return None, None, None


def _load_preexisting_credit_components_from_input(
    use_case_name: str,
    periods: List[int],
) -> Tuple[Dict[int, float], Dict[int, float]]:
    """Load and aggregate pre-existing debt interest/repayment per optimization period.

    Mirrors model logic for c_int_pre/c_rep_pre aggregation:
    sum over yearly k in range(previous_period + 1, current_period + 1).
    """
    try:
        import json
        path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "run" / "use_cases" / use_case_name / "data" / "input" / "general_finances.json"
        )
        if not path.exists():
            return {}, {}

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        liabilities = data.get("liabilities") or {}
        d_init_raw = liabilities.get("initial_liabilities")
        remain_raw = liabilities.get("remaining_credit_years")
        d_int_raw = liabilities.get("debt_interest_rate")

        if d_init_raw is None or remain_raw is None or d_int_raw is None:
            return {}, {}

        d_init = float(d_init_raw)
        remain_credit_years = int(remain_raw)
        d_int = float(d_int_raw)

        if d_init <= 0 or remain_credit_years <= 0:
            return {}, {}

        yearly_repay = d_init / remain_credit_years

        sorted_periods = sorted(p for p in periods if p >= 0)
        if not sorted_periods:
            return {}, {}

        pre_interest: Dict[int, float] = {}
        pre_repayment: Dict[int, float] = {}

        for idx, period in enumerate(sorted_periods):
            previous_period = sorted_periods[idx - 1] if idx > 0 else -1
            rep_value = 0.0
            int_value = 0.0

            for k in range(previous_period + 1, period + 1):
                if k < remain_credit_years:
                    rep_value += yearly_repay
                if k <= remain_credit_years:
                    outstanding = max(d_init - k * yearly_repay, 0.0)
                    int_value += outstanding * d_int

            pre_repayment[period] = round(rep_value, 2)
            pre_interest[period] = round(int_value, 2)

        return pre_interest, pre_repayment
    except Exception:
        return {}, {}


# ---------------------------------------------------------------------------
# Main page class
# ---------------------------------------------------------------------------

class OptimizationResultsPage:
    """Page for visualizing optimization results from processed JSON files."""

    def __init__(self, use_case_manager: UseCaseManager):
        self.use_case_manager = use_case_manager
        self.investment_viz = InvestmentAnalysis()
        self.technology_viz = TechnologyMix()

    # -----------------------------------------------------------------------
    # Entry point
    # -----------------------------------------------------------------------

    def render(self, use_case_name: Optional[str] = None):
        st.markdown(
            """
            <style>
            .block-container { padding-top: 1rem !important; }
            div[data-baseweb="select"] span[data-baseweb="tag"] {
                background-color: #dbeafe !important;
                border: 1px solid #93c5fd !important;
                color: #1e3a8a !important;
                max-width: 100% !important;
                height: auto !important;
                white-space: normal !important;
                line-height: 1.3 !important;
            }
            div[data-baseweb="select"] span[data-baseweb="tag"] > span {
                white-space: normal !important;
                overflow-wrap: anywhere !important;
            }
            div[data-baseweb="menu"] [role="option"][aria-selected="true"] {
                background-color: #e0f2fe !important;
                color: #0c4a6e !important;
            }

            /* ---- Sub-tabs: visually distinct from top-level tabs ---- */
            [data-testid="stTabsContent"] [data-baseweb="tab-list"] {
                background-color: #f1f5f9;
                border-radius: 6px 6px 0 0;
                padding: 0 4px;
                gap: 2px;
                border-bottom: 2px solid #cbd5e1 !important;
            }
            [data-testid="stTabsContent"] button[data-baseweb="tab"] {
                font-size: 0.875rem !important;
                font-weight: 500 !important;
                color: #475569 !important;
                background-color: transparent !important;
                border-radius: 4px 4px 0 0 !important;
                padding: 6px 14px !important;
                border-bottom: 2px solid transparent !important;
                margin-bottom: -2px !important;
            }
            [data-testid="stTabsContent"] button[data-baseweb="tab"]:hover {
                color: #1e40af !important;
                background-color: #e2e8f0 !important;
            }
            [data-testid="stTabsContent"] button[data-baseweb="tab"][aria-selected="true"] {
                color: #1d4ed8 !important;
                background-color: #ffffff !important;
                border-bottom: 2px solid #1d4ed8 !important;
                font-weight: 600 !important;
            }
            </style>
            <h2 style="margin-top:1rem; margin-bottom:0.5rem;">Optimierungsergebnisse</h2>
            """,
            unsafe_allow_html=True,
        )

        if not use_case_name:
            st.warning(
                "Bitte wählen Sie auf der Seite **Portfolio-Übersicht** einen Use Case aus."
            )
            return

        # --- Scenario discovery & selection ---
        all_scenarios = self.use_case_manager.discover_scenarios(use_case_name)
        scenarios = [s for s in all_scenarios if self.use_case_manager.has_results(use_case_name, s)]
        if not scenarios:
            st.warning("Keine verarbeiteten Ergebnisse für diesen Use Case vorhanden.")
            st.info("Bitte führen Sie process_results.py für mindestens ein Szenario aus.")
            return

        # Reset scenario when use case changes
        if st.session_state.get("_last_uc_results") != use_case_name:
            st.session_state["selected_scenario"] = scenarios[0]
            st.session_state["_last_uc_results"] = use_case_name

        current_scenario = st.session_state.get("selected_scenario", scenarios[0])
        scenario_index = scenarios.index(current_scenario) if current_scenario in scenarios else 0

        selected_scenario = st.selectbox(
            "Szenario:",
            scenarios,
            index=scenario_index,
            key="results_scenario_selector",
        )
        st.session_state["selected_scenario"] = selected_scenario

        # Check if processed results exist for this scenario
        if not self.use_case_manager.has_results(use_case_name, selected_scenario):
            st.warning(f"Keine verarbeiteten Ergebnisse für Szenario '{selected_scenario}' gefunden.")
            st.info("Bitte führen Sie process_results.py für dieses Szenario aus.")
            return

        # --- Weight variant discovery ("Optimierungsfokus") ---
        weight_variants = self.use_case_manager.discover_weight_variants(
            use_case_name, selected_scenario
        )

        dirname_to_variant = {v["dirname"]: v for v in weight_variants} if weight_variants else {}

        if weight_variants:
            def _weight_label(v):
                return (
                    f"Eigenkapital: {v['phi_eq']:.0%} | "
                    f"Emissionen: {v['phi_em']:.0%} | "
                    f"Warmmiete: {v['phi_warm']:.0%}"
                )

        # Load building list once for portfolio/building selector
        selector_weight_dirname = weight_variants[0]["dirname"] if weight_variants else None
        building_results: List[ProcessedBuildingResult] = []
        try:
            with st.spinner(f"Lade Ergebnisse für '{selected_scenario}' ..."):
                building_results = self.use_case_manager.load_all_building_results(
                    use_case_name, selected_scenario, weight_dirname=selector_weight_dirname)
        except FileNotFoundError as e:
            st.error(f"Ergebnisdatei nicht gefunden: {e}")
            st.info("Bitte stellen Sie sicher, dass process_results.py für diesen Use Case ausgeführt wurde.")
            return
        except Exception as e:
            st.error(f"Fehler beim Laden der Ergebnisse: {e}")
            logger.exception("Error loading results for use case '%s'", use_case_name)
            return

        # Building / Portfolio view selector
        view_mode, selected_building = self._render_view_selector(building_results, use_case_name)

        st.markdown("---")

        opt_years = _get_optimization_years(use_case_name)

        tabs = st.tabs([
            "📊 Übersicht Optimierungsfokusse",
            "🔎 Detailanalyse",
        ])
        with tabs[0]:
            self._render_overview_comparison(
                use_case_name, selected_scenario, opt_years, view_mode,
                selected_building, building_results,
            )
        with tabs[1]:
            if weight_variants:
                dirnames = [v["dirname"] for v in weight_variants]
                focus_options = [None] + dirnames
                weight_dirname = st.selectbox(
                    "Optimierungsfokus:",
                    focus_options,
                    format_func=lambda d: "Bitte Optimierungsfokus auswählen" if d is None else _weight_label(dirname_to_variant[d]),
                    index=0,
                    key="results_detail_weight_selector",
                )
                if weight_dirname is None:
                    st.info("Bitte zuerst einen Optimierungsfokus auswählen, um die Detailanalyse anzuzeigen.")
                    return
            else:
                weight_dirname = None

            portfolio_result: Optional[ProcessedPortfolioResult] = None
            detail_building_results: List[ProcessedBuildingResult] = []
            try:
                with st.spinner(f"Lade Detailanalyse für '{selected_scenario}' ..."):
                    portfolio_result = self.use_case_manager.load_portfolio_results(
                        use_case_name, selected_scenario, weight_dirname=weight_dirname)
                    detail_building_results = self.use_case_manager.load_all_building_results(
                        use_case_name, selected_scenario, weight_dirname=weight_dirname)
            except FileNotFoundError as e:
                st.error(f"Ergebnisdatei nicht gefunden: {e}")
                st.info("Bitte stellen Sie sicher, dass process_results.py für diesen Use Case ausgeführt wurde.")
                return
            except Exception as e:
                st.error(f"Fehler beim Laden der Detailanalyse: {e}")
                logger.exception("Error loading detailed results for use case '%s'", use_case_name)
                return

            if portfolio_result is None:
                st.error("Portfolioergebnisse konnten nicht geladen werden.")
                return

            detail_selected_building = None
            if view_mode == "building" and selected_building is not None:
                detail_selected_building = next(
                    (br for br in detail_building_results if br.building_id == selected_building.building_id),
                    None,
                )
                if detail_selected_building is None:
                    st.warning(
                        f"Gebäude {selected_building.building_id} ist im ausgewählten Optimierungsfokus nicht verfügbar."
                    )
                    view_mode = "portfolio"

            detail_tabs = st.tabs([
                "💰 Finanzanalyse",
                "🌍 Ökologische Analyse",
                "⚙️ Technische Analyse",
            ])
            with detail_tabs[0]:
                self._render_finanzanalyse(
                    portfolio_result,
                    detail_building_results,
                    opt_years,
                    view_mode,
                    detail_selected_building,
                    use_case_name,
                    weight_dirname,
                )
            with detail_tabs[1]:
                self._render_oekologische_analyse(
                    portfolio_result,
                    detail_building_results,
                    opt_years,
                    view_mode,
                    detail_selected_building,
                )
            with detail_tabs[2]:
                self._render_technische_analyse(
                    portfolio_result,
                    detail_building_results,
                    opt_years,
                    view_mode,
                    detail_selected_building,
                )

    # =======================================================================
    # Tab: Übersicht — cross-weight-variant comparison
    # =======================================================================

    def _render_overview_comparison(
        self,
        use_case_name: str,
        selected_scenario: str,
        opt_years: Optional[List[int]],
        view_mode: str = "portfolio",
        selected_building: Optional[ProcessedBuildingResult] = None,
        building_results: Optional[List[ProcessedBuildingResult]] = None,
    ):
        """Line charts comparing weight variants (Optimierungsfokusse) within the
        selected scenario: emissions, equity, warm rent.
        Respects the portfolio / single-building view selector."""

        weight_variants = self.use_case_manager.discover_weight_variants(
            use_case_name, selected_scenario
        )

        def _wv_label(v: Dict) -> str:
            return (
                f"EK: {v['phi_eq']:.0%} | "
                f"Em: {v['phi_em']:.0%} | "
                f"WM: {v['phi_warm']:.0%}"
            )

        is_building = view_mode == "building" and selected_building is not None
        bid = selected_building.building_id if is_building else None
        view_label = f"(Gebäude {bid})" if is_building else "(Portfolio)"

        # --- Weight variant multiselect (or single-entry fallback) ----------
        if weight_variants:
            all_dirnames = [v["dirname"] for v in weight_variants]
            dirname_to_variant = {v["dirname"]: v for v in weight_variants}

            _unit_combos = {(1, 0, 0), (0, 1, 0), (0, 0, 1)}
            _default_dirnames = [
                d for d in all_dirnames
                if (
                    dirname_to_variant[d]["phi_eq"],
                    dirname_to_variant[d]["phi_em"],
                    dirname_to_variant[d]["phi_warm"],
                ) in _unit_combos
            ] or all_dirnames

            selected_dirnames = st.multiselect(
                "Optimierungsfokusse auswählen:",
                options=all_dirnames,
                default=_default_dirnames,
                format_func=lambda d: _wv_label(dirname_to_variant[d]),
                key="overview_weight_multiselect",
            )
            if not selected_dirnames:
                st.info("Bitte mindestens einen Optimierungsfokus auswählen.")
                return
        else:
            # No weight variants → single entry (whole scenario)
            selected_dirnames = [None]
            dirname_to_variant = {}

        # --- Load data per selected weight variant -------------------------
        emissions_op_by_variant:  Dict[str, Dict[int, float]] = {}
        emissions_emb_by_variant: Dict[str, Dict[int, float]] = {}
        equity_by_variant:        Dict[str, Dict[int, float]] = {}
        warm_rent_by_variant:     Dict[str, Dict[int, float]] = {}

        # Scalar totals for the grouped bar chart
        scalar_equity: Dict[str, float] = {}
        scalar_emissions: Dict[str, float] = {}
        scalar_warm_rent: Dict[str, float] = {}

        for wdir in selected_dirnames:
            label = _wv_label(dirname_to_variant[wdir]) if wdir else selected_scenario
            try:
                if is_building:
                    br = self.use_case_manager.load_building_result(
                        use_case_name, bid, selected_scenario,
                        weight_dirname=wdir,
                    )
                    emissions_op_by_variant[label] = _safe_parse(
                        br.operational_data.get("emissions_operational", {})
                    )
                    emissions_emb_by_variant[label] = _safe_parse(
                        br.transformation_pathway.get("emissions_embodied", {})
                    )
                    opti = br.optiport_data or {}
                    rent = _safe_parse(opti.get("rent", {}))
                    energy_ten = _safe_parse(opti.get("energy_costs_tenant", {}))
                    avail = _safe_parse(opti.get("availability_costs", {}))
                    avail_ll = _safe_parse(opti.get("availability_costs_ll", {}))
                    co2_ll = _safe_parse(opti.get("co2_costs", {}))
                    fossil = _safe_parse(opti.get("emissions_fossil", {}))
                    co2_prices = _load_co2_prices(use_case_name, opt_years)
                    all_p = sorted(set(list(rent) + list(energy_ten) + list(avail)))
                    wm: Dict[int, float] = {}
                    for p in all_p:
                        co2_ten = max(
                            fossil.get(p, 0) * co2_prices.get(p, 0) - co2_ll.get(p, 0), 0
                        )
                        wm[p] = (
                            rent.get(p, 0)
                            + energy_ten.get(p, 0)
                            + avail.get(p, 0) - avail_ll.get(p, 0)
                            + co2_ten
                        )
                    warm_rent_by_variant[label] = wm

                    # Scalar totals for building
                    eq_data = _safe_parse(opti.get("equity", {}))
                    if eq_data:
                        last_p = max(p for p in eq_data if p >= 0)
                        scalar_equity[label] = eq_data[last_p]
                    scalar_emissions[label] = opti.get("total_emissions_optiport", 0.0)
                    scalar_warm_rent[label] = sum(v for p, v in wm.items() if p >= 0)
                else:
                    pr = self.use_case_manager.load_portfolio_results(
                        use_case_name, selected_scenario,
                        weight_dirname=wdir,
                    )
                    emissions_op_by_variant[label] = _safe_parse(pr.emissions_operational)
                    emissions_emb_by_variant[label] = _safe_parse(pr.emissions_embodied)
                    equity_by_variant[label]        = _safe_parse(pr.equity)
                    warm_rent_by_variant[label]      = _safe_parse(pr.warm_rent_total)

                    # Scalar totals for portfolio
                    eq_data = _safe_parse(pr.equity)
                    if eq_data:
                        last_p = max(p for p in eq_data if p >= 0)
                        scalar_equity[label] = eq_data[last_p]
                    scalar_emissions[label] = pr.total_emissions_optiport
                    scalar_warm_rent[label] = sum(
                        v for p, v in _safe_parse(pr.warm_rent_total).items() if p >= 0
                    )
            except Exception:
                continue

        palette = [
            "#2563eb", "#16a34a", "#ca8a04", "#dc2626",
            "#7c3aed", "#0891b2", "#ea580c", "#4d7c0f",
        ]

        def _line_chart(data_by_variant, title, y_label, chart_key, divisor=1.0):
            fig = go.Figure()
            all_years_union = []
            currency_scaling = None
            if "€" in y_label and "€/" not in y_label:
                all_vals_currency = []
                for period_data in data_by_variant.values():
                    periods = sorted(p for p in period_data.keys() if p >= 0)
                    all_vals_currency.extend([period_data.get(p, 0) / divisor for p in periods])
                currency_scaling = get_currency_axis_config(all_vals_currency, "€")

            for idx, (variant_label, period_data) in enumerate(data_by_variant.items()):
                periods = sorted(p for p in period_data.keys() if p >= 0)
                years   = _periods_to_years(periods, opt_years)
                all_years_union = years
                values_raw  = [period_data.get(p, 0) / divisor for p in periods]
                values = values_raw
                if currency_scaling:
                    values = [v / currency_scaling["scale_factor"] for v in values]
                fig.add_trace(go.Scatter(
                    x=years, y=values,
                    customdata=values_raw if currency_scaling else None,
                    mode="lines+markers",
                    name=variant_label,
                    line=dict(color=palette[idx % len(palette)], width=2),
                    marker=dict(size=7),
                    hovertemplate=(
                        f"<b>{variant_label}</b><br>"
                        "Jahr: %{x}<br>"
                        "Betrag: %{customdata:,.0f} €<extra></extra>"
                    ) if currency_scaling else None,
                ))

            display_y_label = y_label
            yaxis_dict = dict(rangemode="tozero")
            if currency_scaling:
                display_y_label = y_label.replace("€", currency_scaling["unit"])
                yaxis_dict["tickformat"] = currency_scaling["tickformat"]

            fig.update_layout(
                xaxis_title="Jahr",
                yaxis_title=display_y_label,
                yaxis=yaxis_dict,
                height=380,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
                xaxis=dict(tickmode="array", tickvals=all_years_union),
            )
            st.plotly_chart(fig, use_container_width=True, key=chart_key)

        st.subheader(f"Vergleich Optimierungsfokusse {view_label}")
        st.markdown("#### Zielgrößen")

        # --- Pareto plot: Equity (y) vs Emissions (x) ---
        if scalar_equity and scalar_emissions:
            variant_labels = list(scalar_equity.keys())
            x_vals = [scalar_emissions.get(v, 0) / 1_000 for v in variant_labels]
            y_vals = [scalar_equity.get(v, 0) / 1_000 for v in variant_labels]

            # Sort by emissions for the Pareto front line
            sorted_pts = sorted(zip(x_vals, y_vals, variant_labels))

            fig_pareto = go.Figure()

            # Pareto front line (connecting sorted points)
            fig_pareto.add_trace(go.Scatter(
                x=[p[0] for p in sorted_pts],
                y=[p[1] for p in sorted_pts],
                mode="lines",
                line=dict(color="#94a3b8", width=1.5, dash="dot"),
                showlegend=False,
                hoverinfo="skip",
            ))

            # Individual points
            for idx, (x, y, vlabel) in enumerate(sorted_pts):
                color = palette[idx % len(palette)]
                fig_pareto.add_trace(go.Scatter(
                    x=[x], y=[y],
                    mode="markers+text",
                    marker=dict(size=12, color=color),
                    text=[vlabel],
                    textposition="top center",
                    textfont=dict(size=9),
                    name=vlabel,
                    hovertemplate=(
                        f"<b>{vlabel}</b><br>"
                        "Emissionen: %{x:,.1f} t CO₂<br>"
                        "Eigenkapital: %{y:,.1f} k€"
                        "<extra></extra>"
                    ),
                ))

            fig_pareto.update_layout(
                xaxis_title="Emissionen (t CO₂)",
                yaxis_title="Eigenkapital (k€)",
                height=480,
                margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(
                    orientation="h", yanchor="bottom", y=-0.25,
                    xanchor="center", x=0.5,
                ),
                showlegend=False,
            )
            st.plotly_chart(fig_pareto, use_container_width=True, key="overview_pareto")
            st.markdown("---")

        st.markdown("#### Emissionsentwicklung")
        fig_em = go.Figure()
        all_years_em = []
        palette_op = [
            "#2563eb", "#16a34a", "#ca8a04", "#dc2626",
            "#7c3aed", "#0891b2", "#ea580c", "#4d7c0f",
        ]
        for idx, variant_label in enumerate(emissions_op_by_variant):
            op_data = emissions_op_by_variant.get(variant_label, {})
            emb_data = emissions_emb_by_variant.get(variant_label, {})
            periods = sorted(p for p in set(list(op_data) + list(emb_data)) if p >= 0)
            years = _periods_to_years(periods, opt_years)
            all_years_em = years
            total_vals = [(op_data.get(p, 0) + emb_data.get(p, 0)) / 1_000 for p in periods]
            suffix = f" ({variant_label})" if len(emissions_op_by_variant) > 1 else ""
            fig_em.add_trace(go.Scatter(
                x=years, y=total_vals,
                mode="lines+markers", name=f"Gesamtemissionen{suffix}",
                line=dict(color=palette_op[idx % len(palette_op)], width=2),
                marker=dict(size=7),
            ))
        fig_em.update_layout(
            xaxis_title="Jahr",
            yaxis_title="CO₂-Emissionen in t CO₂ / Jahr",
            yaxis=dict(rangemode="tozero"),
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(tickmode="array", tickvals=all_years_em),
        )
        st.plotly_chart(fig_em, use_container_width=True, key="overview_emissions")

        if not is_building:
            st.markdown("#### Eigenkapitalentwicklung")
            _line_chart(equity_by_variant, "Eigenkapitalentwicklung",
                        "Eigenkapital in €", "overview_equity")

        st.markdown("#### Warmmietenentwicklung")
        area_map = _load_area_map(use_case_name)
        if is_building:
            total_area = area_map.get(bid, 0)
        else:
            total_area = sum(area_map.values())
        wm_divisor = total_area * 12 if total_area > 0 else 1.0
        wm_unit = "€/(m²·Monat)" if total_area > 0 else "€"
        _line_chart(warm_rent_by_variant, "Warmmiete",
                    f"Warmmiete in {wm_unit}", "overview_warm_rent", divisor=wm_divisor)

    # =======================================================================
    # Building / Portfolio view selector
    # =======================================================================

    def _render_view_selector(
        self,
        building_results: List[ProcessedBuildingResult],
        use_case_name: str,
    ):
        """Render 'Anzeigen für:' dropdown. Returns (view_mode, selected_building)."""
        options = ["Portfolio (Alle Gebäude)"]
        bldg_map: Dict[str, ProcessedBuildingResult] = {}
        for br in sorted(building_results, key=lambda b: b.building_id):
            bid = br.building_id
            label = f"Gebäude {bid} (Max-Mustermann-Straße {bid}, 12345 Musterstadt)"
            options.append(label)
            bldg_map[label] = br

        selected = st.selectbox("Anzeigen für:", options, key="view_selector")

        if selected == options[0]:
            return "portfolio", None
        return "building", bldg_map[selected]

    # =======================================================================
    # Tab: Finanzanalyse
    # =======================================================================

    def _render_finanzanalyse(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        use_case_name: str,
        weight_dirname: Optional[str] = None,
    ):
        # st.markdown(
        #     '<div style="margin:0.5rem 0 0 0; padding:5px 12px; background:#fef9ec; '
        #     'border-left:4px solid #f59e0b; border-radius:0 4px 4px 0;">'
        #     '<span style="font-size:0.78rem; color:#92400e; font-weight:600; '
        #     'letter-spacing:0.04em;">💰 FINANZANALYSE — Übersicht</span></div>',
        #     unsafe_allow_html=True,
        # )
        subtabs = st.tabs(["Allgemein", "Investition", "Finanzierung", "Mieten und Betrieb"])

        with subtabs[0]:
            self._render_finanzuebersicht(
                portfolio_result,
                building_results,
                opt_years,
                view_mode,
                selected_building,
                use_case_name,
                weight_dirname,
            )
        with subtabs[1]:
            self._render_investition_subtab(portfolio_result, opt_years, view_mode, selected_building)
        with subtabs[2]:
            self._render_finanzierung_subtab(
                portfolio_result,
                building_results,
                opt_years,
                view_mode,
                selected_building,
                use_case_name,
            )
        with subtabs[3]:
            self._render_mieten_betrieb_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)

    # --- Finanzübersicht ---------------------------------------------------

    def _render_finanzuebersicht(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        use_case_name: str,
        weight_dirname: Optional[str] = None,
    ):
        if view_mode == "building" and selected_building:
            view_label = f"(Gebäude {selected_building.building_id})"
        else:
            view_label = "(Portfolio)"

        # 1. Eigenkapital und Schuldenverlauf (Portfolio only)
        if view_mode == "portfolio":
            st.subheader(f"Eigenkapital und Schuldenverlauf {view_label}")
            initial_equity, initial_debt, initial_liquidity = _load_initial_finance_values_from_input(use_case_name)
            focus_suffix = weight_dirname or "default"
            self.investment_viz.render(
                portfolio_result, building_results,
                key=f"fa_equity_debt_{focus_suffix}", opt_years=opt_years,
                initial_equity=initial_equity,
                initial_debt=initial_debt,
                initial_liquidity=initial_liquidity,
            )
            st.markdown("---")

        # Abschreibungen pro Maßnahme
        st.subheader(f"Abschreibungen pro Maßnahme {view_label}")
        if view_mode == "portfolio":
            self._render_portfolio_depreciation(building_results, opt_years)
        else:
            opti = selected_building.optiport_data if selected_building else {}
            if opti:
                self._render_building_depreciation_chart(
                    opti.get("depreciation_per_measure", {}),
                    opti.get("depreciation_existing_per_measure", {}),
                    opt_years,
                )
            else:
                st.info("Keine Abschreibungsdaten für dieses Gebäude vorhanden.")

    def _render_portfolio_depreciation(
        self,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
    ):
        """Aggregate depreciation from all buildings and render."""
        agg_per_measure: Dict[str, Dict[int, float]] = {}
        agg_existing_per_measure: Dict[str, Dict[int, float]] = {}
        agg_flat_total: Dict[int, float] = {}
        for br in building_results:
            opti = br.optiport_data
            if not opti:
                continue
            dep_pm = opti.get("depreciation_per_measure", {})
            dep_pm_existing = opti.get("depreciation_existing_per_measure", {})
            nested = _parse_measure_period_keys(dep_pm)
            nested_existing = _parse_measure_period_keys(dep_pm_existing)
            if nested:
                for measure, periods in nested.items():
                    agg_per_measure.setdefault(measure, {})
                    for p, v in periods.items():
                        agg_per_measure[measure][p] = agg_per_measure[measure].get(p, 0) + v
            else:
                # Old-format flat keys (e.g. "t0") — aggregate as total
                for p, v in _safe_parse(dep_pm).items():
                    agg_flat_total[p] = agg_flat_total.get(p, 0) + v
            if nested_existing:
                for measure, periods in nested_existing.items():
                    agg_existing_per_measure.setdefault(measure, {})
                    for p, v in periods.items():
                        agg_existing_per_measure[measure][p] = agg_existing_per_measure[measure].get(p, 0) + v
        # Reconstruct flat dicts to reuse existing method
        flat_pm: dict = {}
        if agg_per_measure:
            for measure, periods in agg_per_measure.items():
                for p, v in periods.items():
                    flat_pm[f"{measure}_t{p}"] = v
        elif agg_flat_total:
            # Fallback: pass flat totals through (will show single total chart)
            for p, v in agg_flat_total.items():
                flat_pm[f"t{p}"] = v
        flat_pm_existing: dict = {}
        for measure, periods in agg_existing_per_measure.items():
            for p, v in periods.items():
                flat_pm_existing[f"{measure}_t{p}"] = v
        if not flat_pm and not flat_pm_existing:
            st.info("Keine Abschreibungsdaten im Portfolio vorhanden.")
            return
        self._render_building_depreciation_chart(flat_pm, flat_pm_existing, opt_years)

    # --- Investition -------------------------------------------------------

    def _render_investition_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        if view_mode == "building" and selected_building:
            view_label = f"(Gebäude {selected_building.building_id})"
        else:
            view_label = "(Portfolio)"

        st.subheader(f"Investitionen nach Maßnahme {view_label}")
        if view_mode == "portfolio":
            self._render_portfolio_investment_by_measure_chart(portfolio_result, opt_years)
        else:
            br = selected_building
            full_periods = _full_periods(br.transformation_pathway.get("costs_investment", {}))
            inv_raw = br.transformation_pathway.get("investment_by_measure", {})
            uninst_raw = br.optiport_data.get("uninstallation_costs", {}) if br.optiport_data else {}
            self._render_building_investment_chart(inv_raw, uninst_raw, full_periods, opt_years)

    # --- Finanzierung ------------------------------------------------------

    def _render_finanzierung_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        use_case_name: str,
    ):
        if view_mode == "building" and selected_building:
            view_label = f"(Gebäude {selected_building.building_id})"
        else:
            view_label = "(Portfolio)"

        if view_mode == "portfolio":
            # 1. Kredite
            st.subheader(f"Kredite {view_label}")
            self._render_portfolio_credits_chart(portfolio_result, building_results, opt_years)
            st.markdown("---")

            # 2. Zinsen, Tilgung
            st.subheader(f"Zinsen und Tilgung {view_label}")
            self._render_portfolio_credit_chart(building_results, opt_years, use_case_name)
            st.markdown("---")

        # 3. Förderübersicht (both)
        st.subheader(f"Förderübersicht {view_label}")
        if view_mode == "portfolio":
            self._render_portfolio_subsidies_chart(building_results, opt_years)
        else:
            opti = selected_building.optiport_data if selected_building else {}
            if opti:
                self._render_building_subsidies_line_chart(opti.get("subsidies", {}), opt_years)
            else:
                st.info("Keine Förderdaten für dieses Gebäude vorhanden.")

    def _render_portfolio_credits_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
    ):
        """Stacked bar: credits per measure (residual values).
        NOTE: C_cred_{i}_{m} is a portfolio-level variable (no building index).
        process_results.py copies the same values into every building's
        optiport_data and then sums them into credits_total, causing N× over-
        counting for N buildings. We take credits from the first building only.
        """
        raw = {}
        for br in sorted(building_results, key=lambda b: b.building_id):
            opti = br.optiport_data
            if opti and opti.get("credits"):
                raw = opti["credits"]
                break
        if not raw:
            # Fallback to portfolio-level (single-building cases are correct)
            raw = portfolio_result.credits_total
        if not raw:
            st.info("Keine Kreditdaten verfügbar.")
            return
        nested = _parse_measure_period_keys(raw)
        measures = sorted(
            m for m, periods in nested.items()
            if any(v > 0 for v in periods.values()) and not _is_excluded_measure(m)
        )
        if not measures:
            st.info("Keine Kredite in Anspruch genommen.")
            return
        all_periods = sorted({p for periods in nested.values() for p in periods})
        all_years = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        for measure in measures:
            values = [nested[measure].get(p, 0) for p in all_periods]
            translated = get_technology_translation(measure)
            color = get_technology_color(measure)
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kredit: %{{y:,.2f}} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Kreditbetrag in €")
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key="fa_credits")

    # --- Constraint Params Helper -------------------------------------------

    def _get_constraint_params(
        self,
        portfolio_result: ProcessedPortfolioResult,
        selected_building: Optional[ProcessedBuildingResult],
        view_mode: str,
    ) -> dict:
        """Return constraint params dict for the current view mode.

        For building view: use per-building constraint_params from optiport_data.
        For portfolio view: use aggregated constraint_params from portfolio result.
        """
        if view_mode == "building" and selected_building and selected_building.optiport_data:
            return selected_building.optiport_data.get("constraint_params", {})
        return getattr(portfolio_result, "constraint_params", {}) or {}

    # --- Mieten und Betrieb ------------------------------------------------

    def _render_mieten_betrieb_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        if view_mode == "portfolio":
            opti_list = [br.optiport_data for br in building_results if br.optiport_data]
        else:
            opti_list = [selected_building.optiport_data] if (selected_building and selected_building.optiport_data) else []

        if view_mode == "building" and selected_building:
            view_label = f"(Gebäude {selected_building.building_id})"
        else:
            view_label = "(Portfolio)"

        if not opti_list:
            st.info("Keine Miet- und Betriebsdaten verfügbar.")
            return

        use_case_name = st.session_state.get("selected_use_case", "")

        # Aggregate data from optiport_data dicts
        rent_agg:        Dict[int, float] = {}
        energy_ten_agg:  Dict[int, float] = {}
        avail_agg:       Dict[int, float] = {}
        avail_ll_agg:    Dict[int, float] = {}
        co2_ll_agg:      Dict[int, float] = {}
        fossil_agg:      Dict[int, float] = {}
        rev_ll_agg:      Dict[int, float] = {}
        mod_agg:         Dict[int, float] = {}
        mod_heat_agg:    Dict[int, float] = {}

        for opti in opti_list:
            for k, v in _safe_parse(opti.get("rent", {})).items():
                rent_agg[k] = rent_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("energy_costs_tenant", {})).items():
                energy_ten_agg[k] = energy_ten_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("availability_costs", {})).items():
                avail_agg[k] = avail_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("availability_costs_ll", {})).items():
                avail_ll_agg[k] = avail_ll_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("co2_costs", {})).items():
                co2_ll_agg[k] = co2_ll_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("emissions_fossil", {})).items():
                fossil_agg[k] = fossil_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("energy_revenue_landlord", {})).items():
                rev_ll_agg[k] = rev_ll_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("modernization_costs", {})).items():
                mod_agg[k] = mod_agg.get(k, 0) + v
            for k, v in _safe_parse(opti.get("modernization_costs_heat", {})).items():
                mod_heat_agg[k] = mod_heat_agg.get(k, 0) + v

        # Compute tenant CO2 costs: emissions_fossil * c_co2 - co2_costs(landlord)
        co2_prices = _load_co2_prices(use_case_name, opt_years)
        co2_ten_agg: Dict[int, float] = {}
        all_p = sorted(set(list(fossil_agg) + list(co2_ll_agg)))
        for p in all_p:
            total_co2 = fossil_agg.get(p, 0) * co2_prices.get(p, 0)
            co2_ten_agg[p] = max(total_co2 - co2_ll_agg.get(p, 0), 0)

        all_periods = sorted(set(
            list(rent_agg) + list(energy_ten_agg) + list(avail_agg) + list(co2_ten_agg)
        ))
        all_periods = [p for p in all_periods if p >= 0]
        if not all_periods:
            st.info("Keine Zeitreihen für Mieten und Betrieb vorhanden.")
            return
        all_years = _periods_to_years(all_periods, opt_years)

        # Load area for €/(m²·month) conversion
        area_map = _load_area_map(use_case_name)
        if view_mode == "building" and selected_building:
            total_area = area_map.get(selected_building.building_id, 0)
        else:
            total_area = sum(area_map.get(br.building_id, 0) for br in building_results)
        area_factor = (total_area * 12) if total_area > 0 else 0  # annual € → €/(m²·month)

        # 1. Warmmiete stacked
        st.subheader(f"Warmmiete {view_label}")
        fig_wm = go.Figure()
        wm_unit = "€/(m²·Monat)" if area_factor > 0 else "€"
        for data, name, color in [
            (rent_agg,       "Kaltmiete",              "#1f77b4"),
            (energy_ten_agg, "Energiekosten Mieter",    "#ff7f0e"),
            ({p: avail_agg.get(p, 0) - avail_ll_agg.get(p, 0) for p in all_periods}, "Wartung", "#9467bd"),
            (co2_ten_agg,    "CO₂-Kosten Mieter",       "#d62728"),
        ]:
            raw_vals = [data.get(p, 0) for p in all_periods]
            y_vals = [v / area_factor for v in raw_vals] if area_factor > 0 else raw_vals
            fig_wm.add_trace(go.Bar(
                name=name,
                x=[str(y) for y in all_years],
                y=y_vals,
                hovertemplate=f"<b>{name}</b><br>Jahr: %{{x}}<br>Betrag: %{{y:,.2f}} {wm_unit}<extra></extra>",
                marker_color=color,
            ))
        fig_wm.update_layout(
            xaxis_title="Jahr", yaxis_title=f"Warmmiete in {wm_unit}",
            barmode="stack", height=420, showlegend=True,
            yaxis=dict(rangemode="tozero"),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        # Reference lines: only in building view (per-building caps don't aggregate meaningfully)
        cp = self._get_constraint_params(portfolio_result, selected_building, view_mode)
        if view_mode == "building":
            # Max warm rent line
            warm_max_vals = [cp.get(f"c_warm_max_t{p}") for p in all_periods]
            if any(v is not None for v in warm_max_vals):
                raw_vals_max = [v if v is not None else 0 for v in warm_max_vals]
                y_ref = [v / area_factor for v in raw_vals_max] if area_factor > 0 else raw_vals_max
                fig_wm.add_trace(go.Scatter(
                    x=[str(y) for y in all_years], y=y_ref,
                    mode="lines", name="Max. Warmmiete",
                    line=dict(color="red", width=2, dash="dash"),
                    hovertemplate="Max. Warmmiete: %{y:,.2f} " + wm_unit + "<extra></extra>",
                ))
            # Comparison rent line (Vergleichsmiete)
            comp_vals = [cp.get(f"c_comp_t{p}") for p in all_periods]
            if any(v is not None for v in comp_vals):
                raw_vals_comp = [v if v is not None else 0 for v in comp_vals]
                y_ref_comp = [v / area_factor for v in raw_vals_comp] if area_factor > 0 else raw_vals_comp
                fig_wm.add_trace(go.Scatter(
                    x=[str(y) for y in all_years], y=y_ref_comp,
                    mode="lines", name="Max. Vergleichsmiete (kalt)",
                    line=dict(color="#1f77b4", width=2, dash="dash"),
                    hovertemplate="Max. Vergleichsmiete (kalt): %{y:,.2f} " + wm_unit + "<extra></extra>",
                ))
        st.plotly_chart(fig_wm, use_container_width=True, key="fa_warmmiete")

        st.markdown("---")

        # 2. Einnahmen Vermieter stacked
        st.subheader(f"Einnahmen Vermieter {view_label}")
        fig_ein = go.Figure()
        for data, name, color in [
            (rent_agg,  "Kaltmiete",                "#1f77b4"),
            (rev_ll_agg, "PV und KWK Einnahmen",    "#2ca02c"),
        ]:
            fig_ein.add_trace(go.Bar(
                name=name,
                x=[str(y) for y in all_years],
                y=[data.get(p, 0) for p in all_periods],
                hovertemplate=f"<b>{name}</b><br>Jahr: %{{x}}<br>Betrag: %{{y:,.0f}} €<extra></extra>",
                marker_color=color,
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig_ein, "Betrag in € / Jahr")
        fig_ein.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_title,
            barmode="stack", height=420, showlegend=True,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_ein, use_container_width=True, key="fa_einnahmen")

        st.markdown("---")

        # 3. Modernisierungsumlagen Vermieter
        st.subheader(f"Modernisierungsumlagen Vermieter {view_label}")
        
        mod_heat_vals = [mod_heat_agg.get(p, 0) for p in all_periods]
        sonstige_mod_vals = [mod_agg.get(p, 0) - mod_heat_agg.get(p, 0) for p in all_periods]
        
        # Check if there's any modernization levy data
        has_mod_data = any(v != 0 for v in mod_heat_vals) or any(v != 0 for v in sonstige_mod_vals)
        
        if has_mod_data:
            fig_mod = go.Figure()
            
            if any(v != 0 for v in mod_heat_vals):
                fig_mod.add_trace(go.Bar(
                    name="Heizungsmodernisierungsumlage",
                    x=[str(y) for y in all_years],
                    y=mod_heat_vals,
                    hovertemplate="<b>Heizungsmodernisierungsumlage</b><br>Jahr: %{x}<br>Betrag: %{y:,.0f} €<extra></extra>",
                    marker_color="#e377c2",
                ))

            if any(v != 0 for v in sonstige_mod_vals):
                fig_mod.add_trace(go.Bar(
                    name="Sonstige Umlage",
                    x=[str(y) for y in all_years],
                    y=sonstige_mod_vals,
                    hovertemplate="<b>Sonstige Umlage</b><br>Jahr: %{x}<br>Betrag: %{y:,.0f} €<extra></extra>",
                    marker_color="#ff7f0e",
                ))

            display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig_mod, "Betrag in € / Jahr")

            fig_mod.update_layout(
                xaxis_title="Jahr", yaxis_title=display_y_title,
                barmode="stack", height=420, showlegend=True,
                yaxis=yaxis_dict,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_mod, use_container_width=True, key="fa_modernisierungsumlagen")
        else:
            st.info("Keine Modernisierungsumlagen vorhanden.")

        st.markdown("---")

        # 4. Ausgaben Vermieter stacked
        st.subheader(f"Ausgaben Vermieter {view_label}")
        ausgaben_series = [
            (avail_agg,  "Instandhaltung",         "#9467bd"),
            (co2_ll_agg, "CO₂-Kosten Vermieter",   "#d62728"),
        ]
        fig_aus = go.Figure()
        for data, name, color in ausgaben_series:
            vals = [data.get(p, 0) for p in all_periods]
            if any(v != 0 for v in vals):
                fig_aus.add_trace(go.Bar(
                    name=name,
                    x=[str(y) for y in all_years],
                    y=vals,
                    customdata=vals,
                    hovertemplate=f"<b>{name}</b><br>Jahr: %{{x}}<br>Betrag: %{{customdata:,.0f}}€<extra></extra>",
                    marker_color=color,
                ))
        # KWK-Gaskosten placeholder (not separately available in current data)
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig_aus, "Betrag in € / Jahr")
        fig_aus.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_title,
            barmode="stack", height=420, showlegend=True,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig_aus, use_container_width=True, key="fa_ausgaben")

    # =======================================================================
    # Tab: Ökologische Analyse
    # =======================================================================

    def _render_oekologische_analyse(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        # st.markdown(
        #     '<div style="margin:0.5rem 0 0 0; padding:5px 12px; background:#f0fdf4; '
        #     'border-left:4px solid #22c55e; border-radius:0 4px 4px 0;">'
        #     '<span style="font-size:0.78rem; color:#14532d; font-weight:600; '
        #     'letter-spacing:0.04em;">🌍 ÖKOLOGISCHE ANALYSE — Übersicht</span></div>',
        #     unsafe_allow_html=True,
        # )
        subtabs = st.tabs(["Emissionen", "Weitere LCA Parameter"])

        with subtabs[0]:
            self._render_emissionen_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)
        with subtabs[1]:
            st.info("Weitere LCA-Parameter werden in einer zukünftigen Version ergänzt.")

    def _render_emissionen_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        if view_mode == "building" and selected_building:
            view_label = f"(Gebäude {selected_building.building_id})"
        else:
            view_label = "(Portfolio)"

        if view_mode == "portfolio":
            op_data = _safe_parse(portfolio_result.emissions_operational)
            emb_data = _safe_parse(portfolio_result.emissions_embodied)
            fossil_op_data = _safe_parse(getattr(portfolio_result, "emissions_fossil_total", {}))
            if not fossil_op_data and building_results:
                for br in building_results:
                    opti_fossil = _safe_parse(br.optiport_data.get("emissions_fossil", {}))
                    for p, v in opti_fossil.items():
                        fossil_op_data[p] = fossil_op_data.get(p, 0.0) + v
        else:
            br = selected_building
            op_data = _safe_parse(br.operational_data.get("emissions_operational", {}))
            emb_data = _safe_parse(br.transformation_pathway.get("emissions_embodied", {}))
            fossil_op_data = _safe_parse(
                br.operational_data.get(
                    "emissions_operational_fossil",
                    br.optiport_data.get("emissions_fossil", {}),
                )
            )

        # 1. Betriebsemissionen
        st.subheader(f"Betriebsemissionen {view_label}")
        if op_data:
            periods = sorted(op_data)
            years = _periods_to_years(periods, opt_years)
            op_total = [op_data.get(p, 0) / 1_000 for p in periods]
            fig_op = go.Figure()
            fossil_vals = [
                max(0.0, min(fossil_op_data.get(p, 0) / 1_000, op_total[idx]))
                for idx, p in enumerate(periods)
            ]
            non_fossil_vals = [
                max(op_total[idx] - fossil_vals[idx], 0.0)
                for idx in range(len(periods))
            ]

            fig_op.add_trace(go.Scatter(
                x=years,
                y=fossil_vals,
                name="Fossile Betriebsemissionen",
                mode="lines",
                line=dict(color="rgba(249,115,22,0.5)", width=2),
                stackgroup="op_emissions",
                fillcolor="rgba(249,115,22,0.5)",
                hovertemplate="<b>Fossile Betriebsemissionen</b><br>Jahr: %{x}<br>CO₂: %{y:,.2f} t<extra></extra>",
            ))
            fig_op.add_trace(go.Scatter(
                x=years,
                y=non_fossil_vals,
                name="Nicht-fossile Betriebsemissionen",
                mode="lines",
                line=dict(color="rgba(250,204,21,0.5)", width=2),
                stackgroup="op_emissions",
                fillcolor="rgba(250,204,21,0.5)",
                hovertemplate="<b>Nicht-fossile Betriebsemissionen</b><br>Jahr: %{x}<br>CO₂: %{y:,.2f} t<extra></extra>",
            ))
            fig_op.add_trace(go.Scatter(
                x=years,
                y=op_total,
                mode="lines+markers",
                name="Gesamte Betriebsemissionen",
                line=dict(color="#ff7f0e", width=3),
                marker=dict(size=8),
                hovertemplate="<b>Gesamte Betriebsemissionen</b><br>Jahr: %{x}<br>CO₂: %{y:,.2f} t<extra></extra>",
            ))
            fig_op.update_layout(
                xaxis_title="Jahr", yaxis_title="CO₂-Emissionen in t CO₂ / Jahr",
                yaxis=dict(rangemode="tozero"), height=420, hovermode="x unified",
                xaxis=dict(tickmode="array", tickvals=years),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            # Reference line: portfolio emission cap (only in portfolio view)
            if view_mode == "portfolio":
                cp = getattr(portfolio_result, "constraint_params", None) or {}
                em_cap_raw = [(p, cp.get(f"q_em_t{p}")) for p in periods]
                em_cap_defined = [(p, v) for p, v in em_cap_raw if v is not None]
                if em_cap_defined:
                    cap_x = [_periods_to_years([p], opt_years)[0] for p, _ in em_cap_defined]
                    cap_y = [v / 1_000 for _, v in em_cap_defined]
                    n_defined = len(em_cap_defined)
                    n_total = len(periods)
                    if n_defined == n_total:
                        cap_mode = "lines"
                    elif n_defined == 1:
                        cap_mode = "markers"
                    else:
                        cap_mode = "lines+markers"
                    fig_op.add_trace(go.Scatter(
                        x=cap_x,
                        y=cap_y,
                        mode=cap_mode,
                        name="Emissionsgrenze",
                        line=dict(color="red", width=2, dash="dash"),
                        marker=dict(color="red", size=10, symbol="x"),
                        hovertemplate="Emissionsgrenze: %{y:,.1f} t CO₂<extra></extra>",
                    ))
            st.plotly_chart(fig_op, use_container_width=True, key="oa_operational_emissions")
        else:
            st.info("Keine Betriebsemissionsdaten verfügbar.")

        st.markdown("---")

        # 2. Gebundene Emissionen
        st.subheader(f"Gebundene Emissionen {view_label}")
        embodied_by_measure_agg: Dict[str, Dict[int, float]] = {}
        if view_mode == "portfolio":
            all_periods = _full_periods(portfolio_result.costs_investment)
            for br in building_results:
                emb_raw = br.transformation_pathway.get("embodied_by_measure", {})
                parsed = _parse_embodied_by_measure(emb_raw) if emb_raw else {}
                for measure, period_values in parsed.items():
                    if _is_excluded_measure(measure):
                        continue
                    for period, value in period_values.items():
                        embodied_by_measure_agg.setdefault(measure, {})
                        embodied_by_measure_agg[measure][period] = embodied_by_measure_agg[measure].get(period, 0.0) + value
        else:
            emb_raw = selected_building.transformation_pathway.get("embodied_by_measure", {})
            embodied_by_measure_agg = _parse_embodied_by_measure(emb_raw) if emb_raw else {}
            embodied_by_measure_agg = {
                measure: period_values
                for measure, period_values in embodied_by_measure_agg.items()
                if not _is_excluded_measure(measure)
            }
            all_periods = _full_periods(selected_building.transformation_pathway.get("costs_investment", {}))

        if embodied_by_measure_agg:
            if not all_periods:
                all_periods = sorted({p for periods in embodied_by_measure_agg.values() for p in periods})
            years = _periods_to_years(all_periods, opt_years)

            measures = sorted(
                m for m, period_values in embodied_by_measure_agg.items()
                if any(v != 0 for v in period_values.values())
            )
            if not measures:
                st.info("Keine Daten zu gebundenen Emissionen nach Maßnahme verfügbar.")
                return

            fig_emb = go.Figure()
            for measure in measures:
                translated = get_technology_translation(measure)
                color = get_technology_color(measure)
                values = [embodied_by_measure_agg[measure].get(p, 0) / 1_000 for p in all_periods]
                fig_emb.add_trace(go.Bar(
                    name=translated,
                    x=[str(y) for y in years],
                    y=values,
                    marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Gebundene Emissionen: %{{y:,.2f}} t CO₂<extra></extra>",
                ))

            fig_emb.update_layout(
                xaxis_title="Jahr", yaxis_title="CO₂-Emissionen in t CO₂ / Jahr",
                yaxis=dict(rangemode="tozero"),
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in years]),
                barmode="stack", height=420, showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_emb, use_container_width=True, key="oa_embodied_emissions")
        elif emb_data:
            periods = sorted(emb_data)
            years = _periods_to_years(periods, opt_years)
            fig_emb = go.Figure()
            fig_emb.add_trace(go.Scatter(
                x=years, y=[emb_data.get(p, 0) / 1_000 for p in periods],
                mode="lines+markers", name="Gebundene Emissionen",
                line=dict(color="#8c564b", width=3), marker=dict(size=8),
            ))
            fig_emb.update_layout(
                xaxis_title="Jahr", yaxis_title="CO₂-Emissionen in t CO₂ / Jahr",
                yaxis=dict(rangemode="tozero"), height=400, hovermode="x unified",
                xaxis=dict(tickmode="array", tickvals=years),
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st.plotly_chart(fig_emb, use_container_width=True, key="oa_embodied_emissions")
        else:
            st.info("Keine Daten zu gebundenen Emissionen verfügbar.")

    # =======================================================================
    # Tab: Technische Analyse
    # =======================================================================

    def _render_technische_analyse(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        # st.markdown(
        #     '<div style="margin:0.5rem 0 0 0; padding:5px 12px; background:#f0f9ff; '
        #     'border-left:4px solid #0ea5e9; border-radius:0 4px 4px 0;">'
        #     '<span style="font-size:0.78rem; color:#0c4a6e; font-weight:600; '
        #     'letter-spacing:0.04em;">⚙️ TECHNISCHE ANALYSE — Übersicht</span></div>',
        #     unsafe_allow_html=True,
        # )
        subtabs = st.tabs(["Anlagentechnik", "Sanierungsstand", "Übergabesystem", "Energie und Betrieb"])

        with subtabs[0]:
            self._render_anlagentechnik_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)
        with subtabs[1]:
            self._render_gebaeudehulle_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)
        with subtabs[2]:
            self._render_uebergabesystem_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)
        with subtabs[3]:
            self._render_energie_betrieb_subtab(portfolio_result, building_results, opt_years, view_mode, selected_building)

    def _render_anlagentechnik_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        view_label = "(Portfolio)" if view_mode == "portfolio" else f"(Gebäude {selected_building.building_id})"
        # 1. Wärmeerzeuger
        st.subheader(f"Wärmeerzeuger {view_label}")
        st.markdown("#### Verfügbar")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_heat_generator, y_label="Kapazität in W",
            chart_key="ta_heat_gen_avail", data_key="available",
        )
        st.markdown("#### Neuinstallation")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_heat_generator, y_label="Kapazität in W",
            chart_key="ta_heat_gen_inst", data_key="installed",
        )
        st.markdown("---")

        # 2. Speicher
        st.subheader(f"Speicher {view_label}")
        st.markdown("#### Verfügbar")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_storage_measure, y_label="Kapazität in Wh",
            chart_key="ta_storage_avail", data_key="available",
        )
        st.markdown("#### Neuinstallation")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_storage_measure, y_label="Kapazität in Wh",
            chart_key="ta_storage_inst", data_key="installed",
        )
        st.markdown("---")

        # 3. Solaranlage
        st.subheader(f"Solaranlage {view_label}")
        st.markdown("#### Verfügbar")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_solar_measure, y_label="Kapazität in W",
            chart_key="ta_solar_avail", data_key="available",
        )
        st.markdown("#### Neuinstallation")
        self._render_filtered_capacity_chart(
            portfolio_result, opt_years, view_mode, selected_building,
            measure_filter=_is_solar_measure, y_label="Kapazität in W",
            chart_key="ta_solar_inst", data_key="installed",
        )

    def _render_filtered_capacity_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        measure_filter,
        y_label: str,
        chart_key: str,
        data_key: str,
    ):
        """Generic capacity chart filtered by measure_filter function."""
        if view_mode == "portfolio":
            raw = (portfolio_result.capacity_available_total
                   if data_key == "available"
                   else portfolio_result.capacity_installed_total)
            nested = _parse_measure_period_keys(raw)
            all_periods = _full_periods(portfolio_result.costs_investment)
        else:
            br = selected_building
            key = "available_measures" if data_key == "available" else "installed_measures"
            raw = br.transformation_pathway.get(key, {})
            nested = _parse_measure_period_keys(raw)
            all_periods = _full_periods(br.transformation_pathway.get("costs_investment", {}))

        if not nested:
            st.info("Keine Kapazitätsdaten gefunden.")
            return
        if not all_periods:
            all_periods = sorted({p for periods in nested.values() for p in periods})
        all_years = _periods_to_years(all_periods, opt_years)

        measures = sorted(
            m for m, periods in nested.items()
            if not _is_excluded_measure(m)
            and measure_filter(m)
        )
        if not measures:
            st.info("Keine Maßnahmen vorhanden.")
            return

        # Check if autoscaling is needed (for Wh or W values)
        base_unit = None
        if "Wh" in y_label:
            base_unit = "Wh"
        elif re.search(r"\bW\b", y_label):
            base_unit = "W"

        use_autoscale = base_unit is not None
        axis_config = None
        display_unit = None
        if use_autoscale:
            # Collect all values for autoscaling
            all_values = []
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in all_periods]
                all_values.extend(values)
            if base_unit == "Wh":
                axis_config = get_energy_axis_config(all_values, "Wh")
            else:
                axis_config = get_power_axis_config(all_values, "W")
            display_unit = axis_config["unit"]
        else:
            display_unit = y_label.split(" in ")[-1] if " in " in y_label else ""

        fig = go.Figure()
        for measure in measures:
            raw_values = [nested[measure].get(p, 0) for p in all_periods]
            values = raw_values
            if use_autoscale and axis_config:
                values = [v / axis_config["scale_factor"] for v in values]
            translated = get_technology_translation(measure)
            color = get_technology_color(measure)
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                customdata=raw_values if use_autoscale and axis_config else None,
                marker_color=color,
                hovertemplate=(
                    f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kapazität: %{{customdata:,.0f}} {base_unit}<extra></extra>"
                    if use_autoscale and axis_config
                    else f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kapazität: %{{y:{axis_config['tickformat'] if axis_config else ',.0f'}}} {display_unit}<extra></extra>"
                ),
            ))
        
        # Update y_label with autoscaled unit if applicable
        display_y_label = y_label
        yaxis_dict = dict(rangemode="tozero")
        if use_autoscale and axis_config:
            display_y_label = f"Kapazität in {axis_config['unit']}"
            yaxis_dict["tickformat"] = axis_config["tickformat"]
        
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_label,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

    def _render_gebaeudehulle_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        view_label = "(Portfolio)" if view_mode == "portfolio" else f"(Gebäude {selected_building.building_id})"
        # Verfügbar
        st.subheader(f"Sanierungsstand {view_label}")
        st.markdown("#### Verfügbar")
        if view_mode == "building" and selected_building:
            self._render_hull_measures_chart(selected_building, opt_years)
        else:
            self._render_hull_chart(
                portfolio_result, building_results, opt_years,
                view_mode, selected_building,
                include_hull=True, include_distribution=False,
                chart_key="ta_hull_avail",
            )
        # Neuinstallation
        st.markdown("#### Neuinstallation")
        self._render_hull_installed_chart(
            portfolio_result, building_results, opt_years,
            view_mode, selected_building,
            include_hull=True, include_distribution=False,
            chart_key="ta_hull_inst",
        )

    def _render_uebergabesystem_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        view_label = "(Portfolio)" if view_mode == "portfolio" else f"(Gebäude {selected_building.building_id})"
        st.subheader(f"Übergabesystem {view_label}")
        st.markdown("#### Verfügbar")
        if view_mode == "building" and selected_building:
            self._render_dis_measures_chart(selected_building, opt_years)
        else:
            self._render_hull_chart(
                portfolio_result, building_results, opt_years,
                view_mode, selected_building,
                include_hull=False, include_distribution=True,
                chart_key="ta_dis_avail",
            )
        st.markdown("#### Neuinstallation")
        self._render_hull_installed_chart(
            portfolio_result, building_results, opt_years,
            view_mode, selected_building,
            include_hull=False, include_distribution=True,
            chart_key="ta_dis_inst",
        )

    def _render_energie_betrieb_subtab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
    ):
        view_label = "(Portfolio)" if view_mode == "portfolio" else f"(Gebäude {selected_building.building_id})"
        st.subheader(f"Energie und Betrieb {view_label}")

        if view_mode == "building" and selected_building:
            brs = [selected_building]
        else:
            brs = building_results

        # --- Collect all energy data across buildings ---
        import_agg: Dict[str, Dict[int, float]] = {}   # fuel -> {period -> Wh}
        export_agg: Dict[str, Dict[int, float]] = {}
        heat_agg: Dict[str, Dict[int, float]] = {}     # measure -> {period -> Wh}
        dhw_agg: Dict[str, Dict[int, float]] = {}      # measure -> {period -> Wh}
        elec_agg: Dict[str, Dict[int, float]] = {}

        def _parse_fuel_period_keys(raw: dict, agg: Dict[str, Dict[int, float]]):
            """Parse '{name}_t{period}' keys and aggregate into nested dict."""
            for key, val in (raw or {}).items():
                parts = key.rsplit("_", 1)
                if len(parts) != 2 or not parts[1].startswith("t"):
                    continue
                name = parts[0]
                try:
                    period = int(parts[1][1:])
                except ValueError:
                    continue
                agg.setdefault(name, {})
                agg[name][period] = agg[name].get(period, 0.0) + float(val)

        for br in brs:
            op = br.operational_data or {}
            _parse_fuel_period_keys(op.get("import_by_fuel", {}), import_agg)
            _parse_fuel_period_keys(op.get("export_by_fuel", {}), export_agg)
            _parse_fuel_period_keys(op.get("heat_output_by_measure", {}), heat_agg)
            _parse_fuel_period_keys(op.get("dhw_output_by_measure", {}), dhw_agg)
            _parse_fuel_period_keys(op.get("elec_output_by_measure", {}), elec_agg)

        has_energy_flows = bool(import_agg or export_agg)
        has_component_data = bool(heat_agg or dhw_agg or elec_agg)

        if not has_energy_flows and not has_component_data:
            st.info("Keine Energieflussdaten verfügbar. "
                    "Diese Daten werden nur nach der Evaluierung der Betriebszustände erzeugt.")
            return

        all_periods = sorted(set(
            p
            for data_dict in [import_agg, export_agg, heat_agg, dhw_agg, elec_agg]
            for item_data in data_dict.values()
            for p in item_data
        ))
        all_years = _periods_to_years(all_periods, opt_years)

        # --- 1. Wärmebereitstellung (heat output by component) ---
        if heat_agg:
            st.markdown("#### Wärmebereitstellung")
            fig_heat = go.Figure()
            measures_heat = sorted(
                m for m, periods in heat_agg.items()
                if any(v > 0 for v in periods.values())
                and not _is_excluded_measure(m)
            )
            
            # Collect all values for autoscaling
            all_heat_values = []
            for m in measures_heat:
                vals = [heat_agg[m].get(p, 0.0) for p in all_periods]
                all_heat_values.extend(vals)
            
            # Get autoscaling configuration
            axis_config = get_energy_axis_config(all_heat_values, "Wh")
            scale_factor = axis_config["scale_factor"]
            unit = axis_config["unit"]
            
            for m in measures_heat:
                vals = [heat_agg[m].get(p, 0.0) for p in all_periods]
                scaled_vals = [v / scale_factor for v in vals]
                translated = get_technology_translation(m)
                try:
                    color = get_technology_color(m)
                except KeyError:
                    color = get_energy_carrier_color(m)
                fig_heat.add_trace(go.Bar(
                    x=[str(y) for y in all_years], y=scaled_vals,
                    customdata=vals,
                    name=translated, marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Energie: %{{customdata:,.0f}} Wh<extra></extra>",
                ))
            fig_heat.update_layout(
                barmode="stack", xaxis_title="Jahr", yaxis_title=f"Wärmebereitstellung ({unit})",
                yaxis=dict(rangemode="tozero", tickformat=axis_config["tickformat"]), height=420,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True,
            )
            st.plotly_chart(fig_heat, use_container_width=True, key="eb_heat_output")
            st.markdown("---")


        # --- 1b. Trinkwarmwasserbereitstellung (DHW output by component) ---
        if dhw_agg:
            st.markdown("#### Trinkwarmwasserbereitstellung")
            fig_dhw = go.Figure()
            measures_dhw = sorted(
                m for m, periods in dhw_agg.items()
                if any(v > 0 for v in periods.values())
                and not _is_excluded_measure(m)
            )
            
            # Collect all values for autoscaling
            all_dhw_values = []
            for m in measures_dhw:
                vals = [dhw_agg[m].get(p, 0.0) for p in all_periods]
                all_dhw_values.extend(vals)
            
            # Get autoscaling configuration
            axis_config = get_energy_axis_config(all_dhw_values, "Wh")
            scale_factor = axis_config["scale_factor"]
            unit = axis_config["unit"]
            
            for m in measures_dhw:
                vals = [dhw_agg[m].get(p, 0.0) for p in all_periods]
                scaled_vals = [v / scale_factor for v in vals]
                translated = get_technology_translation(m)
                try:
                    color = get_technology_color(m)
                except KeyError:
                    color = get_energy_carrier_color(m)
                fig_dhw.add_trace(go.Bar(
                    x=[str(y) for y in all_years], y=scaled_vals,
                    customdata=vals,
                    name=translated, marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Energie: %{{customdata:,.0f}} Wh<extra></extra>",
                ))
            fig_dhw.update_layout(
                barmode="stack", xaxis_title="Jahr", yaxis_title=f"Trinkwarmwasserbereitstellung ({unit})",
                yaxis=dict(rangemode="tozero", tickformat=axis_config["tickformat"]), height=420,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True,
            )
            st.plotly_chart(fig_dhw, use_container_width=True, key="eb_dhw_output")
            st.markdown("---")

        # --- 2. Stromerzeugung (electricity production by component) ---
        st.markdown("#### Stromerzeugung")
        if elec_agg:
            fig_elec = go.Figure()
            measures_elec = sorted(
                m for m, periods in elec_agg.items()
                if any(v > 0 for v in periods.values())
                and not _is_excluded_measure(m)
            )
            if measures_elec:
                # Collect all values for autoscaling
                all_elec_values = []
                for m in measures_elec:
                    vals = [elec_agg[m].get(p, 0.0) for p in all_periods]
                    all_elec_values.extend(vals)
                
                # Get autoscaling configuration
                axis_config = get_energy_axis_config(all_elec_values, "Wh")
                scale_factor = axis_config["scale_factor"]
                unit = axis_config["unit"]
                
                for m in measures_elec:
                    vals = [elec_agg[m].get(p, 0.0) for p in all_periods]
                    scaled_vals = [v / scale_factor for v in vals]
                    translated = get_technology_translation(m)
                    try:
                        color = get_technology_color(m)
                    except KeyError:
                        color = get_energy_carrier_color(m)
                    fig_elec.add_trace(go.Bar(
                        x=[str(y) for y in all_years], y=scaled_vals,
                        customdata=vals,
                        name=translated, marker_color=color,
                        hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Energie: %{{customdata:,.0f}} Wh<extra></extra>",
                    ))
                fig_elec.update_layout(
                    barmode="stack", xaxis_title="Jahr", yaxis_title=f"Stromerzeugung ({unit})",
                    yaxis=dict(rangemode="tozero", tickformat=axis_config["tickformat"]), height=420,
                    xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    showlegend=True,
                )
                st.plotly_chart(fig_elec, use_container_width=True, key="eb_elec_output")
            else:
                st.info("Keine Stromerzeugung im Gebäude vorhanden.")
        else:
            st.info("Keine Stromerzeugung im Gebäude vorhanden.")
        st.markdown("---")

        # --- 3. Importierte Energie nach Energieträger ---
        if import_agg:
            st.markdown("#### Importierte Energie nach Energieträger")
            fig_imp = go.Figure()
            fuels_imp = sorted(import_agg.keys())
            
            # Collect all values for autoscaling
            all_import_values = []
            for fuel in fuels_imp:
                vals = [import_agg[fuel].get(p, 0.0) for p in all_periods]
                all_import_values.extend(vals)
            
            # Get autoscaling configuration
            axis_config = get_energy_axis_config(all_import_values, "Wh")
            scale_factor = axis_config["scale_factor"]
            unit = axis_config["unit"]
            
            for fuel in fuels_imp:
                vals = [import_agg[fuel].get(p, 0.0) for p in all_periods]
                scaled_vals = [v / scale_factor for v in vals]
                translated = get_energy_carrier_translation(fuel)
                color = get_energy_carrier_color(fuel)
                fig_imp.add_trace(go.Bar(
                    x=[str(y) for y in all_years], y=scaled_vals,
                    customdata=vals,
                    name=translated, marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Energie: %{{customdata:,.0f}} Wh<extra></extra>",
                ))
            fig_imp.update_layout(
                barmode="stack", xaxis_title="Jahr", yaxis_title=f"Importierte Energie ({unit})",
                yaxis=dict(rangemode="tozero", tickformat=axis_config["tickformat"]), height=420,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True,
            )
            st.plotly_chart(fig_imp, use_container_width=True, key="eb_import")

        # --- 4. Exportierte Energie nach Energieträger ---
        st.markdown("#### Exportierte Energie nach Energieträger")
        if export_agg:
            fig_exp = go.Figure()
            fuels_exp = sorted(export_agg.keys())
            
            # Collect all values for autoscaling
            all_export_values = []
            for fuel in fuels_exp:
                vals = [export_agg[fuel].get(p, 0.0) for p in all_periods]
                all_export_values.extend(vals)
            
            # Get autoscaling configuration
            axis_config = get_energy_axis_config(all_export_values, "Wh")
            scale_factor = axis_config["scale_factor"]
            unit = axis_config["unit"]
            
            for fuel in fuels_exp:
                vals = [export_agg[fuel].get(p, 0.0) for p in all_periods]
                scaled_vals = [v / scale_factor for v in vals]
                translated = get_energy_carrier_translation(fuel)
                color = get_energy_carrier_color(fuel)
                fig_exp.add_trace(go.Bar(
                    x=[str(y) for y in all_years], y=scaled_vals,
                    customdata=vals,
                    name=translated, marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Energie: %{{customdata:,.0f}} Wh<extra></extra>",
                ))
            fig_exp.update_layout(
                barmode="stack", xaxis_title="Jahr", yaxis_title=f"Exportierte Energie ({unit})",
                yaxis=dict(rangemode="tozero", tickformat=axis_config["tickformat"]), height=420,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                showlegend=True,
            )
            st.plotly_chart(fig_exp, use_container_width=True, key="eb_export")
        else:
            st.info("Keine exportierten Energieflüsse vorhanden.")

    # --- Generic hull / distribution charts --------------------------------

    def _render_hull_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        include_hull: bool = True,
        include_distribution: bool = True,
        chart_key: str = "hull_chart",
    ):
        """Grouped stacked bar for hull (roof/wall/win) and/or distribution (rad/ufh)."""
        all_periods = _full_periods(portfolio_result.costs_investment)
        if not all_periods:
            st.info("Keine Periodendaten verfügbar.")
            return

        type_counts: Dict[str, Dict[int, int]] = {}
        brs = [selected_building] if view_mode == "building" else building_results

        for br in brs:
            if include_hull:
                hull_raw = br.transformation_pathway.get("available_hull_measures", {})
                for key, level in hull_raw.items():
                    parts = key.rsplit("_", 1)
                    if len(parts) != 2:
                        continue
                    category, period_str = parts
                    if category not in ("roof", "wall", "win"):
                        continue
                    try:
                        period = int(period_str)
                    except ValueError:
                        continue
                    type_key = f"{category}_{level}"
                    type_counts.setdefault(type_key, {})
                    type_counts[type_key][period] = type_counts[type_key].get(period, 0) + 1

            if include_distribution:
                dis_raw = br.transformation_pathway.get("available_dis_measures", {})
                for key, val in dis_raw.items():
                    idx = key.rfind("_")
                    if idx == -1:
                        continue
                    measure = key[:idx]
                    try:
                        period = int(key[idx + 1:])
                    except ValueError:
                        continue
                    type_counts.setdefault(measure, {})
                    type_counts[measure][period] = type_counts[measure].get(period, 0) + 1

        if not type_counts:
            lbl = "Gebäudehülle" if include_hull else "Übergabesystem"
            st.info(f"Keine {lbl}-Daten verfügbar.")
            return

        building_count = len(brs)
        y_tick_step = 10 if view_mode == "portfolio" and building_count > 20 else 1

        all_years = _periods_to_years(all_periods, opt_years)
        ordered = []
        if include_hull:
            ordered += [
                f"{cat}_{lvl}"
                for cat in ("roof", "wall", "win")
                for lvl in (3, 2, 1)
                if f"{cat}_{lvl}" in type_counts
            ]
        if include_distribution:
            ordered += sorted(
                (k for k in type_counts if k.startswith("rad") or k == "ufh"),
                reverse=True,
            )

        fig = go.Figure()
        for type_key in ordered:
            translated = get_technology_translation(type_key)
            color = self._hull_fix_color(type_key)
            cat = self._classify_hull_fix(type_key) or type_key.rsplit("_", 1)[0]
            values = [type_counts[type_key].get(p, 0) for p in all_periods]
            y_lbl = "Anzahl Gebäude" if view_mode == "portfolio" else "Aktive Maßnahmen"
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color, offsetgroup=cat, legendgroup=cat,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>{y_lbl}: %{{y}}<extra></extra>",
            ))
        fig.update_layout(
            xaxis_title="Jahr",
            yaxis_title="Anzahl Gebäude" if view_mode == "portfolio" else "Aktive Maßnahmen",
            barmode="stack", height=420, showlegend=True,
            bargroupgap=0.2,
            yaxis=dict(dtick=y_tick_step, rangemode="tozero"),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

    def _render_hull_installed_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        view_mode: str,
        selected_building: Optional[ProcessedBuildingResult],
        include_hull: bool = True,
        include_distribution: bool = True,
        chart_key: str = "hull_inst_chart",
    ):
        """Stacked bar: investment costs for hull / distribution installed measures."""
        if view_mode == "portfolio":
            inv_data = portfolio_result.investment_by_measure_total
        else:
            inv_data = selected_building.transformation_pathway.get("investment_by_measure", {})

        if not inv_data:
            lbl = "Gebäudehülle" if include_hull else "Übergabesystem"
            st.info(f"Keine Modernisierungen für {lbl} vorhanden.")
            return

        type_costs: Dict[str, Dict[int, float]] = {}
        for key, cost in inv_data.items():
            k = key[6:] if key.startswith("c_inv_") else key
            idx = k.rfind("_t")
            if idx == -1:
                continue
            measure = k[:idx]
            try:
                period = int(k[idx + 2:])
            except ValueError:
                continue
            is_hull = self._classify_hull_fix(measure) in ("roof", "wall", "win")
            is_dis = _is_distribution_measure(measure)
            if include_hull and is_hull:
                pass  # include
            elif include_distribution and is_dis:
                pass  # include
            else:
                continue
            type_costs.setdefault(measure, {})
            type_costs[measure][period] = type_costs[measure].get(period, 0) + cost

        if not type_costs:
            lbl = "Gebäudehülle" if include_hull else "Übergabesystem"
            st.info(f"Keine Modernisierungen für {lbl} vorhanden.")
            return

        all_periods = _full_periods(portfolio_result.costs_investment)
        all_years = _periods_to_years(all_periods, opt_years)

        def _sort_key(m):
            if m.startswith("roof"): return (0, m)
            if m.startswith("wall"): return (1, m)
            if m.startswith("win"):  return (2, m)
            return (3, m)
        ordered = sorted(type_costs.keys(), key=_sort_key, reverse=True)

        fig = go.Figure()
        for measure in ordered:
            translated = get_technology_translation(measure)
            color = self._hull_fix_color(measure)
            category = self._classify_hull_fix(measure)
            values = [type_costs[measure].get(p, 0) for p in all_periods]
            if all(v == 0 for v in values):
                continue
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color, offsetgroup=category, legendgroup=category,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kosten: %{{y:,.0f}} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Investitionskosten in €")
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=chart_key)

    def _render_objective_weights_chart(self, weights: Dict[str, float]):
        labels = ["Eigenkapital", "Emissionen", "Warmmieten-Puffer"]
        values = [
            weights.get("phi_eq", 0),
            weights.get("phi_em", 0),
            weights.get("phi_warm", 0),
        ]
        colors = ["#87CEEB", "#EC7063", "#F0B27A"]
        total = sum(values)
        if total == 0:
            st.warning("Keine Zielfunktionsgewichtung definiert.")
            return
        custom_text = []
        for i, v in enumerate(values):
            if v > 0:
                pct = (v / total) * 100
                custom_text.append(f"{labels[i]}<br>{pct:.1f}%")
            else:
                custom_text.append("")
        fig = go.Figure(data=[go.Pie(
            labels=labels, values=values, text=custom_text, hole=0.4,
            marker_colors=colors, texttemplate='%{text}', textposition='auto',
            hovertemplate='<b>%{label}</b><br>Gewichtung: %{value:.2f}<br>Anteil: %{percent}<extra></extra>'
        )])
        fig.update_layout(
            title=dict(text="Gewichtung der Zielfunktion für die Optimierung des Gebäudeportfolios", x=0.5, xanchor="center"),
            height=420, margin=dict(l=20, r=20, t=90, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            showlegend=True,
        )
        st.plotly_chart(fig, use_container_width=True, key="obj_weights")

    def _render_kpi_cards(self, portfolio_result: ProcessedPortfolioResult):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Gesamtinvestitionen",  f"{portfolio_result.costs_investment_total / 1_000:,.0f} k€")
        col2.metric("Gesamtbetriebskosten", f"{portfolio_result.costs_operational_total / 1_000:,.0f} k€")
        col3.metric("Gesamtkosten",         f"{portfolio_result.costs_total_all / 1_000:,.0f} k€")
        col4.metric("Gesamtemissionen",     f"{portfolio_result.emissions_total_all / 1_000:,.1f} t CO₂")

    def _render_emission_timeline(self, portfolio_result: ProcessedPortfolioResult):
        emb_data = _safe_parse(portfolio_result.emissions_embodied)
        op_data  = _safe_parse(portfolio_result.emissions_operational)
        tot_data = _safe_parse(portfolio_result.emissions_total)
        all_periods = sorted(set(list(emb_data) + list(op_data) + list(tot_data)))
        if not all_periods:
            st.info("Keine Zeitreihendaten für Emissionen gefunden.")
            return
        fig = go.Figure()
        if emb_data:
            fig.add_trace(go.Scatter(x=all_periods, y=[emb_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gebundene Emissionen in t CO₂", line=dict(color="#8c564b", width=3), marker=dict(size=8)))
        if op_data:
            fig.add_trace(go.Scatter(x=all_periods, y=[op_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Betriebsemissionen in t CO₂", line=dict(color="#ff7f0e", width=3), marker=dict(size=8)))
        if tot_data:
            fig.add_trace(go.Scatter(x=all_periods, y=[tot_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gesamtemissionen in t CO₂", line=dict(color="#d62728", width=3, dash="dash"), marker=dict(size=8)))
        fig.update_layout(xaxis_title="Jahr", yaxis_title="CO₂-Emissionen in  t CO₂ / Jahr",
            yaxis=dict(rangemode="tozero"), height=420, hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key="overview_emissions")

    # =======================================================================
    # Tab: Finanzen
    # =======================================================================

    def _render_finance_tab(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
    ):
        self.investment_viz.render(portfolio_result, building_results, key="investment_finance", opt_years=opt_years)
        st.markdown("---")

        st.subheader("Investitionen nach Maßnahme")
        self._render_portfolio_investment_by_measure_chart(portfolio_result, opt_years)
        st.markdown("---")

        st.subheader("Jährliche Mieteinnahmen des Gebäudeportfolios")
        self._render_portfolio_rent_chart(portfolio_result, opt_years)
        st.markdown("---")

        st.subheader("Modernisierungsumlagen des Portfolios")
        self._render_portfolio_cmod_chart(portfolio_result, opt_years)
        st.markdown("---")

        st.subheader("Förderübersicht")
        self._render_portfolio_subsidies_chart(building_results, opt_years)
        st.markdown("---")

        st.subheader("Portfolio-Kreditanalyse: Zinsen & Tilgung")
        self._render_portfolio_credit_chart(building_results, opt_years)

    def _render_portfolio_investment_by_measure_chart(self, portfolio_result: ProcessedPortfolioResult, opt_years: Optional[List[int]]):
        """Stacked bar: investment_by_measure_total aggregated in portfolio JSON."""
        raw = portfolio_result.investment_by_measure_total
        agg = _parse_investment_by_measure(raw) if raw else {}
        if not agg:
            st.info("Keine Investitionsdaten nach Maßnahme verfügbar.")
            return
        # Use dense costs_investment to get every year of the planning horizon
        all_periods = _full_periods(portfolio_result.costs_investment)
        if not all_periods:
            all_periods = sorted({p for periods in agg.values() for p in periods})
        all_years = _periods_to_years(all_periods, opt_years)
        measures = sorted(
            m for m, periods in agg.items()
            if any(v != 0 for v in periods.values()) and not _is_excluded_measure(m)
        )
        if not measures:
            st.info("Keine Maßnahmen mit Investitionskosten gefunden.")
            return
        fig = go.Figure()
        for measure in measures:
            values = [agg[measure].get(p, 0) for p in all_periods]
            translated = get_technology_translation(measure)
            color = get_technology_color(measure)
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Investition: %{{y:,.1f}} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Investition in €")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key="finance_investments_by_measure")

    def _render_portfolio_rent_chart(self, portfolio_result: ProcessedPortfolioResult, opt_years: Optional[List[int]]):
        rent_data = _safe_parse(portfolio_result.rent_total)
        if not rent_data:
            st.info("Keine Mieteinnahmen-Daten verfügbar.")
            return
        periods = sorted(rent_data)
        years   = _periods_to_years(periods, opt_years)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=[rent_data[p] for p in periods],
            mode="lines+markers", name="Kaltmiete in €", fill="tozeroy",
            fillcolor="rgba(46,139,87,0.1)", line=dict(color="#2E8B57", width=3), marker=dict(size=8),
        ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Mieteinnahmen in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified", showlegend=False,
            xaxis=dict(tickmode="array", tickvals=years))
        st.plotly_chart(fig, use_container_width=True, key="finance_rent")

    def _render_portfolio_cmod_chart(self, portfolio_result: ProcessedPortfolioResult, opt_years: Optional[List[int]]):
        cmod_data = _safe_parse(portfolio_result.modernization_costs_total)
        if not cmod_data:
            st.info("Keine Modernisierungsumlage-Daten verfügbar.")
            return
        periods = sorted(cmod_data)
        years   = _periods_to_years(periods, opt_years)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=[cmod_data[p] for p in periods],
            mode="lines+markers", name="Modernisierungsumlage",
            line=dict(color="#d62728", width=3), marker=dict(size=8),
        ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Modernisierungsumlage in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified", showlegend=False,
            xaxis=dict(tickmode="array", tickvals=years))
        st.plotly_chart(fig, use_container_width=True, key="finance_cmod")

    def _render_portfolio_subsidies_chart(self, building_results: List[ProcessedBuildingResult], opt_years: Optional[List[int]]):
        """Total subsidies as line chart (sum over all buildings)."""
        subsidies_agg: Dict[int, float] = {}
        for br in building_results:
            opti = br.optiport_data
            if not opti:
                continue
            for k, v in _safe_parse(opti.get("subsidies", {})).items():
                subsidies_agg[k] = subsidies_agg.get(k, 0) + v
        if not subsidies_agg or not any(abs(v) > 0 for v in subsidies_agg.values()):
            st.info("Keine Förderungen in Anspruch genommen")
            return
        all_periods = sorted(subsidies_agg)
        all_years   = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=all_years, y=[subsidies_agg.get(p, 0) for p in all_periods],
            mode="lines+markers", name="Förderungen", fill="tozeroy",
            fillcolor="rgba(255,215,0,0.15)", line=dict(color="#FFD700", width=3), marker=dict(size=8),
        ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Betrag in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified", showlegend=False,
            xaxis=dict(tickmode="array", tickvals=all_years))
        st.plotly_chart(fig, use_container_width=True, key="finance_subsidies")

    def _render_portfolio_credit_chart(
        self,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
        use_case_name: str,
    ):
        # NOTE: interest (C_int_{i}) and repayment (C_rep_{i}) are portfolio-level
        # variables (no building index). process_results.py stores the same values
        # in every building's optiport_data. We must NOT sum across buildings;
        # instead take from the first building that has data.
        interest_agg:  Dict[int, float] = {}
        repayment_agg: Dict[int, float] = {}
        for br in building_results:
            opti = br.optiport_data
            if not opti:
                continue
            interest_agg = _safe_parse(opti.get("interest", {}))
            repayment_agg = _safe_parse(opti.get("repayment", {}))
            break  # portfolio-level values — take from first building only

        base_periods = sorted(set(list(interest_agg) + list(repayment_agg)))
        pre_interest, pre_repayment = _load_preexisting_credit_components_from_input(
            use_case_name,
            base_periods,
        )

        all_periods = sorted(
            set(list(interest_agg) + list(repayment_agg) + list(pre_interest) + list(pre_repayment))
        )
        if not all_periods:
            st.info("Keine Kreditdaten verfügbar.")
            return

        interest_total = {
            p: interest_agg.get(p, 0.0) + pre_interest.get(p, 0.0)
            for p in all_periods
        }
        repayment_total = {
            p: repayment_agg.get(p, 0.0) + pre_repayment.get(p, 0.0)
            for p in all_periods
        }

        all_years   = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        if any(abs(repayment_total[p]) > 0 for p in all_periods):
            fig.add_trace(go.Scatter(
                x=all_years, y=[repayment_total.get(p, 0) for p in all_periods],
                mode="lines+markers", name="Tilgung (inkl. Bestandskredit)",
                line=dict(color="#FF6B6B", width=3), marker=dict(size=8),
            ))
        if any(abs(interest_total[p]) > 0 for p in all_periods):
            fig.add_trace(go.Scatter(
                x=all_years, y=[interest_total.get(p, 0) for p in all_periods],
                mode="lines+markers", name="Zinsen (inkl. Bestandskredit)",
                line=dict(color="#E4AC33", width=3), marker=dict(size=8),
            ))

        if any(abs(pre_repayment.get(p, 0.0)) > 0 for p in all_periods):
            fig.add_trace(go.Scatter(
                x=all_years, y=[pre_repayment.get(p, 0.0) for p in all_periods],
                mode="lines", name="davon Tilgung Bestandskredit",
                line=dict(color="#FF6B6B", width=2, dash="dot"),
            ))

        if any(abs(pre_interest.get(p, 0.0)) > 0 for p in all_periods):
            fig.add_trace(go.Scatter(
                x=all_years, y=[pre_interest.get(p, 0.0) for p in all_periods],
                mode="lines", name="davon Zinsen Bestandskredit",
                line=dict(color="#E4AC33", width=2, dash="dot"),
            ))

        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Betrag in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=all_years),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key="finance_credit")

    # =======================================================================
    # Tab: Gebäude-Analyse
    # =======================================================================

    def _render_building_analysis(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]],
    ):
        st.subheader("Analyse von Technologiepfaden und Kosten/Emissionen für einzelne Gebäude.")
        #st.markdown("Analyse von Technologiepfaden und Kosten/Emissionen für einzelne Gebäude.")
        if not building_results:
            st.warning("Keine Gebäudedaten verfügbar.")
            return
        building_ids = sorted(br.building_id for br in building_results)
        selected_id = st.selectbox(
            "Gebäude-Wahl:", building_ids,
            format_func=lambda x: f"Gebäude {x}", key="building_selector",
        )
        if selected_id is None:
            return
        selected_br = next((br for br in building_results if br.building_id == selected_id), None)
        if selected_br is None:
            st.error(f"Gebäude {selected_id} nicht gefunden.")
            return
        st.markdown("---")
        self._render_building_details(selected_br, opt_years)

    def _render_building_details(self, br: ProcessedBuildingResult, opt_years: Optional[List[int]]):
        st.subheader("Gebäudeübersicht")
        col1, col2, col3 = st.columns(3)
        col1.metric("Gebäude-ID", br.building_id)
        col2.metric("Gebäudetyp", br.building_type)
        col3.metric("Baujahr",    br.construction_year)

        # Derive the full roadmap period list once from the dense costs_investment series
        full_periods = _full_periods(br.transformation_pathway.get("costs_investment", {}))

        st.markdown("---")
        st.subheader("Verfügbare Kapazitäten")
        st.markdown("#### Energietransformatoren")
        self._render_building_capacity_chart(br, "available_measures", "Kapazität in W", full_periods, opt_years, storage=False)
        st.markdown("#### Speicher")
        self._render_building_capacity_chart(br, "available_measures", "Kapazität in Wh", full_periods, opt_years, storage=True)
        st.markdown("#### Effizienzmaßnahmen")
        self._render_hull_available_chart(br, full_periods, opt_years)

        st.markdown("---")
        st.subheader("Neuinstallationen")
        st.markdown("#### Energietransformatoren")
        self._render_building_capacity_chart(br, "installed_measures", "Kapazität in W", full_periods, opt_years, storage=False)
        st.markdown("#### Speicher")
        self._render_building_capacity_chart(br, "installed_measures", "Kapazität in Wh", full_periods, opt_years, storage=True)
        st.markdown("#### Effizienzmaßnahmen")
        self._render_hull_fix_installed_chart(br, full_periods, opt_years)

        st.markdown("---")
        st.subheader("Maßnahmen an der Gebäudehülle")
        self._render_hull_measures_chart(br, opt_years)

        st.markdown("---")
        st.subheader("Kostenverlauf")
        self._render_building_cost_chart(br, opt_years)

        st.markdown("---")
        st.subheader("Emissionsverlauf")
        self._render_building_emission_chart(br, opt_years)

        if br.optiport_data:
            st.markdown("---")
            self._render_building_optiport_data(br, full_periods, opt_years)

    # ---- Building capacity charts -----------------------------------------

    def _render_building_capacity_chart(self, br: ProcessedBuildingResult, key: str, y_label: str, full_periods: List[int], opt_years: Optional[List[int]], storage: Optional[bool] = None):
        nested = _parse_measure_period_keys(br.transformation_pathway.get(key, {}))
        if not nested:
            st.info(f"Keine Daten für '{key}' für dieses Gebäude gefunden.")
            return
        measures = sorted(
            m for m, periods in nested.items()
            if any(v > 0 for v in periods.values())
            and not _is_excluded_measure(m)
            and (storage is None or _is_storage_measure(m) == storage)
        )
        if not measures:
            lbl = "Speicher" if storage else "Energietransformatoren"
            st.info(f"Keine {lbl} > 0 gefunden.")
            return
        all_years = _periods_to_years(full_periods, opt_years)
        
        # Check if autoscaling is needed (for Wh or W values)
        base_unit = None
        if "Wh" in y_label:
            base_unit = "Wh"
        elif re.search(r"\bW\b", y_label):
            base_unit = "W"

        use_autoscale = base_unit is not None
        axis_config = None
        display_unit = None
        if use_autoscale:
            # Collect all values for autoscaling
            all_values = []
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in full_periods]
                all_values.extend(values)
            if base_unit == "Wh":
                axis_config = get_energy_axis_config(all_values, "Wh")
            else:
                axis_config = get_power_axis_config(all_values, "W")
            display_unit = axis_config["unit"]
        else:
            display_unit = y_label.split(" in ")[-1] if " in " in y_label else ""
        
        fig = go.Figure()
        for measure in measures:
            raw_values = [nested[measure].get(p, 0) for p in full_periods]
            values = raw_values
            if use_autoscale and axis_config:
                values = [v / axis_config["scale_factor"] for v in values]
            translated = get_technology_translation(measure)
            color = get_technology_color(measure)
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                customdata=raw_values if use_autoscale and axis_config else None,
                marker_color=color,
                hovertemplate=(
                    f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kapazität: %{{customdata:,.0f}} {base_unit}<extra></extra>"
                    if use_autoscale and axis_config
                    else f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kapazität: %{{y:{axis_config['tickformat'] if axis_config else ',.0f'}}} {display_unit}<extra></extra>"
                ),
            ))
        
        # Update y_label with autoscaled unit if applicable
        display_y_label = y_label
        yaxis_dict = dict(rangemode="tozero")
        if use_autoscale and axis_config:
            display_y_label = f"Kapazität in {axis_config['unit']}"
            yaxis_dict["tickformat"] = axis_config["tickformat"]
        
        sto_suffix = "_sto" if storage else "_tra"
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_label,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=400, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_capacity_{key}{sto_suffix}_{br.building_id}")

    # ---- Hull / fix measure charts ----------------------------------------

    @staticmethod
    def _classify_hull_fix(measure: str) -> Optional[str]:
        for prefix in ("roof", "wall", "win", "rad"):
            if measure.startswith(prefix):
                return prefix
        if measure == "ufh":
            return "rad"
        return None

    @classmethod
    def _hull_fix_color(cls, measure_type: str) -> str:
        """Return the color for a specific hull/fix measure type using centralized colors."""
        return get_technology_color(measure_type)

    def _render_hull_available_chart(self, br: ProcessedBuildingResult, full_periods: List[int], opt_years: Optional[List[int]]):
        """Grouped stacked bar: disaggregated hull types + heating distribution
        active for this building.

        Hull types (roof/wall/win) come from ``available_hull_measures``.
        Heating distribution (rad/ufh) comes from ``available_dis_measures``.
        """
        # type_active[type_key][period] = 1 if that type is active
        type_active: Dict[str, Dict[int, int]] = {}

        # --- Hull measures (roof, wall, win) ---
        hull_raw = br.transformation_pathway.get("available_hull_measures", {})
        for key, level in hull_raw.items():
            parts = key.rsplit("_", 1)
            if len(parts) != 2:
                continue
            category, period_str = parts
            if category not in ("roof", "wall", "win"):
                continue
            try:
                period = int(period_str)
            except ValueError:
                continue
            type_key = f"{category}_{level}"
            type_active.setdefault(type_key, {})[period] = 1

        # --- Heating distribution (rad, ufh) from available_dis_measures ---
        dis_raw = br.transformation_pathway.get("available_dis_measures", {})
        for key, val in dis_raw.items():
            idx = key.rfind("_")
            if idx == -1:
                continue
            measure = key[:idx]
            try:
                period = int(key[idx + 1:])
            except ValueError:
                continue
            type_active.setdefault(measure, {})[period] = 1

        if not type_active:
            return

        all_years = _periods_to_years(full_periods, opt_years)
        # Best efficiency at bottom: highest number first within each category
        ordered = [
            f"{cat}_{lvl}"
            for cat in ("roof", "wall", "win")
            for lvl in (3, 2, 1)
            if f"{cat}_{lvl}" in type_active
        ] + sorted((k for k in type_active if k.startswith("rad") or k == "ufh"), reverse=True)

        fig = go.Figure()
        for type_key in ordered:
            translated = get_technology_translation(type_key)
            color = self._hull_fix_color(type_key)
            category = self._classify_hull_fix(type_key) or type_key.rsplit("_", 1)[0]
            values = [type_active[type_key].get(p, 0) for p in full_periods]
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                offsetgroup=category,
                legendgroup=category,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<extra></extra>",
            ))
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title="Aktive Maßnahmen",
            barmode="stack", height=400, showlegend=True,
            yaxis=dict(dtick=1, rangemode="tozero"),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_hull_avail_{br.building_id}")

    def _render_hull_fix_installed_chart(self, br: ProcessedBuildingResult, full_periods: List[int], opt_years: Optional[List[int]]):
        """Stacked bar: investment costs for newly installed hull/fix measures,
        disaggregated by specific type."""
        inv_raw = br.transformation_pathway.get("investment_by_measure", {})
        if not inv_raw:
            return
        type_costs: Dict[str, Dict[int, float]] = {}
        for key, cost in inv_raw.items():
            k = key[6:] if key.startswith("c_inv_") else key
            idx = k.rfind("_t")
            if idx == -1:
                continue
            measure = k[:idx]
            try:
                period = int(k[idx + 2:])
            except ValueError:
                continue
            if self._classify_hull_fix(measure) is None:
                continue
            type_costs.setdefault(measure, {})
            type_costs[measure][period] = type_costs[measure].get(period, 0) + cost
        if not type_costs:
            return
        all_years = _periods_to_years(full_periods, opt_years)
        # Best efficiency at bottom: highest number first
        def _sort_key(m):
            if m.startswith("roof"): return (0, m)
            if m.startswith("wall"): return (1, m)
            if m.startswith("win"):  return (2, m)
            return (3, m)
        ordered = sorted(type_costs.keys(), key=_sort_key, reverse=True)
        fig = go.Figure()
        for measure in ordered:
            translated = get_technology_translation(measure)
            color = self._hull_fix_color(measure)
            category = self._classify_hull_fix(measure)
            values = [type_costs[measure].get(p, 0) for p in full_periods]
            if all(v == 0 for v in values):
                continue
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                offsetgroup=category,
                legendgroup=category,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kosten: %{{y:,.0f}} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Investitionskosten in €")
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=400, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_hull_fix_inst_{br.building_id}")

    def _render_hull_measures_chart(self, br: ProcessedBuildingResult, opt_years: Optional[List[int]]):
        hull_raw = br.transformation_pathway.get("available_hull_measures", {})
        if not hull_raw:
            st.info("Keine Gebäudehüllendaten gefunden.")
            return
        hull_data: Dict[str, Dict[int, float]] = {}
        for key, level in hull_raw.items():
            parts = key.rsplit("_", 1)
            if len(parts) != 2:
                continue
            component, period_str = parts
            try:
                period = int(period_str)
            except ValueError:
                continue
            hull_data.setdefault(component, {})[period] = level
        if not hull_data:
            st.info("Keine Gebäudehüllendaten (valides Format) gefunden.")
            return
        components = sorted(hull_data.keys())
        component_labels = {"roof": "Dach", "wall": "Wand", "win": "Fenster"}
        colors_map = {"roof": "#ff7f0e", "wall": "#1f77b4", "win": "#2ca02c"}
        fig = make_subplots(rows=len(components), cols=1,
            subplot_titles=[component_labels.get(c, c.title()) for c in components],
            vertical_spacing=0.08, shared_xaxes=True)
        for row_idx, comp in enumerate(components, 1):
            periods_for_comp = sorted(hull_data[comp].keys())
            years_for_comp   = _periods_to_years(periods_for_comp, opt_years)
            levels = [hull_data[comp][p] for p in periods_for_comp]
            label = component_labels.get(comp, comp.title())
            color = colors_map.get(comp, "#9467bd")
            fig.add_trace(go.Scatter(
                x=years_for_comp, y=levels, mode="markers+lines", name=label,
                marker=dict(color=color, size=12), line=dict(color=color, width=3),
                hovertemplate=f"<b>{label}</b><br>Jahr: %{{x}}<br>Klasse: %{{y}}<extra></extra>",
                showlegend=False,
            ), row=row_idx, col=1)
            fig.update_yaxes(title_text=f"{label}klasse", tickmode="linear",
                tick0=1, dtick=1, range=[0.5, 3.5], row=row_idx, col=1)
            fig.update_xaxes(tickmode="array", tickvals=years_for_comp, row=row_idx, col=1)
        fig.update_xaxes(title_text="Jahr", row=len(components), col=1)
        fig.update_layout(height=250 * len(components), hovermode="closest")
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_hull_{br.building_id}")

    def _render_dis_measures_chart(self, br: ProcessedBuildingResult, opt_years: Optional[List[int]]):
        """Single chart for distribution system showing 11/22/33/FH over time."""
        dis_raw = br.transformation_pathway.get("available_dis_measures", {})
        if not dis_raw:
            st.info("Keine Übergabesystem-Daten gefunden.")
            return

        # Parse: key = "{measure}_{period}", value = 1 (active)
        # Build unified series: period → label string (e.g. "11", "22", "33", "FH")
        period_label: Dict[int, str] = {}
        for key, val in dis_raw.items():
            idx = key.rfind("_")
            if idx == -1:
                continue
            measure = key[:idx]
            try:
                period = int(key[idx + 1:])
            except ValueError:
                continue
            if measure.startswith("rad"):
                num_str = measure.replace("rad_", "")
                try:
                    int(num_str)
                except ValueError:
                    continue
                period_label[period] = num_str
            elif measure == "ufh":
                period_label[period] = "FH"

        if not period_label:
            st.info("Keine Übergabesystem-Daten (valides Format) gefunden.")
            return

        # Categorical y-axis: map labels to numeric positions for plotting
        y_categories = ["11", "22", "33", "FH"]
        y_pos = {label: idx for idx, label in enumerate(y_categories)}

        periods = sorted(period_label.keys())
        years = _periods_to_years(periods, opt_years)
        labels = [period_label[p] for p in periods]
        y_vals = [y_pos.get(l, 0) for l in labels]

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=y_vals, mode="markers+lines",
            marker=dict(color="#c8704f", size=12),
            line=dict(color="#c8704f", width=3),
            hovertemplate="<b>Übergabesystem</b><br>Jahr: %{x}<br>Typ: %{text}<extra></extra>",
            text=labels, showlegend=False,
        ))
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title="Übergabesystem",
            yaxis=dict(
                tickmode="array",
                tickvals=list(range(len(y_categories))),
                ticktext=y_categories,
                range=[-0.5, len(y_categories) - 0.5],
            ),
            xaxis=dict(tickmode="array", tickvals=years),
            height=350, hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_dis_{br.building_id}")

    def _render_building_cost_chart(self, br: ProcessedBuildingResult, opt_years: Optional[List[int]]):
        inv_data = _safe_parse(br.transformation_pathway.get("costs_investment", {}))
        op_data  = _safe_parse(br.operational_data.get("costs_operational", {}))
        tot_data = _safe_parse(br.totals.get("costs_total", {}))
        all_periods = sorted(set(list(inv_data) + list(op_data) + list(tot_data)))
        if not all_periods:
            st.info("Keine Kostenzeitreihe für dieses Gebäude gefunden.")
            return
        all_years = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        if inv_data:
            fig.add_trace(go.Scatter(x=all_years, y=[inv_data.get(p, 0) for p in all_periods],
                mode="lines+markers", name="Investitionen", line=dict(color="#2563eb", width=3), marker=dict(size=8)))
        if op_data:
            fig.add_trace(go.Scatter(x=all_years, y=[op_data.get(p, 0) for p in all_periods],
                mode="lines+markers", name="Betriebskosten", line=dict(color="#ff7f0e", width=3), marker=dict(size=8)))
        if tot_data:
            fig.add_trace(go.Scatter(x=all_years, y=[tot_data.get(p, 0) for p in all_periods],
                mode="lines+markers", name="Gesamtkosten", line=dict(color="#d62728", width=3, dash="dash"), marker=dict(size=8)))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Kosten in €")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=400, hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=all_years),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_cost_{br.building_id}")

    def _render_building_emission_chart(self, br: ProcessedBuildingResult, opt_years: Optional[List[int]]):
        emb_data = _safe_parse(br.transformation_pathway.get("emissions_embodied", {}))
        op_data  = _safe_parse(br.operational_data.get("emissions_operational", {}))
        tot_data = _safe_parse(br.totals.get("emissions_total", {}))
        all_periods = sorted(set(list(emb_data) + list(op_data) + list(tot_data)))
        if not all_periods:
            st.info("Keine Emissionszeitreihe für dieses Gebäude gefunden.")
            return
        all_years = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        if emb_data:
            fig.add_trace(go.Scatter(x=all_years, y=[emb_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gebundene Emissionen", line=dict(color="#8c564b", width=3), marker=dict(size=8)))
        if op_data:
            fig.add_trace(go.Scatter(x=all_years, y=[op_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Betriebsemissionen", line=dict(color="#ff7f0e", width=3), marker=dict(size=8)))
        if tot_data:
            fig.add_trace(go.Scatter(x=all_years, y=[tot_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gesamtemissionen", line=dict(color="#d62728", width=3, dash="dash"), marker=dict(size=8)))
        fig.update_layout(xaxis_title="Jahr", yaxis_title="CO₂-Emissionen in t CO₂ / Jahr",
            yaxis=dict(rangemode="tozero"), height=400, hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=all_years),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key=f"bldg_emission_{br.building_id}")

    # ---- optiport_data section -------------------------------------------

    def _render_building_optiport_data(self, br: ProcessedBuildingResult, full_periods: List[int], opt_years: Optional[List[int]]):
        opti = br.optiport_data
        if not opti:
            st.info("Keine OptiPort-Finanzdaten für dieses Gebäude vorhanden.")
            return

        st.subheader("Finanzen – Kaltmiete, Energiekosten und CO₂-Kosten")
        self._render_building_finance_overview(opti, opt_years)
        st.markdown("---")

        credits_raw = opti.get("credits", {})
        if _has_nonzero(credits_raw):
            st.subheader("Kreditanalyse per Maßnahme")
            self._render_building_credit_chart(credits_raw, opt_years)
            st.markdown("---")

        dep_per_measure = opti.get("depreciation_per_measure", {})
        dep_existing_pm = opti.get("depreciation_existing_per_measure", {})
        if _has_nonzero(dep_per_measure) or _has_nonzero(dep_existing_pm):
            st.subheader("Abschreibungsen")
            self._render_building_depreciation_chart(dep_per_measure, dep_existing_pm, opt_years)
            st.markdown("---")

        inv_by_measure_raw = br.transformation_pathway.get("investment_by_measure", {})
        uninst_raw = opti.get("uninstallation_costs", {})
        if _has_nonzero(inv_by_measure_raw) or _has_nonzero(uninst_raw):
            st.subheader("Investitionen nach Maßnahme")
            self._render_building_investment_chart(inv_by_measure_raw, uninst_raw, full_periods, opt_years)
            st.markdown("---")

        subsidies = opti.get("subsidies", {})
        if _has_nonzero(subsidies):
            st.subheader("Förderungen")
            self._render_building_subsidies_line_chart(subsidies, opt_years)
            st.markdown("---")

        co2_data = _safe_parse(opti.get("co2_costs", {}))
        if co2_data:
            st.subheader("CO₂-Kosten (Vermieteranteil)")
            self._render_building_co2_costs_chart(co2_data, opt_years)

    def _render_building_finance_overview(self, opti: dict, opt_years: Optional[List[int]]):
        rent_data   = _safe_parse(opti.get("rent", {}))
        energy_data = _safe_parse(opti.get("energy_costs", {}))
        co2_data    = _safe_parse(opti.get("co2_costs", {}))
        avail_data  = _safe_parse(opti.get("availability_costs", {}))
        all_periods = sorted(set(list(rent_data) + list(energy_data) + list(co2_data) + list(avail_data)))
        all_periods = [p for p in all_periods if p >= 0]
        if not all_periods:
            st.info("Keine Finanzdaten für dieses Gebäude gefunden.")
            return
        all_years = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        for data, name, color in [
            (rent_data,   "Kaltmiete",              "#1f77b4"),
            (energy_data, "Energiekosten",           "#ff7f0e"),
            (co2_data,    "CO₂-Kosten",              "#d62728"),
            (avail_data,  "Wartung & Instandhaltung", "#9467bd"),
        ]:
            if data:
                fig.add_trace(go.Scatter(
                    x=all_years, y=[data.get(p, 0) for p in all_periods],
                    mode="lines+markers", name=name,
                    line=dict(color=color, width=3), marker=dict(size=8),
                ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Betrag in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=400, hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=all_years),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key="bldg_finance_overview")

    def _render_building_investment_chart(self, net_costs_raw: dict, uninst_raw: dict, full_periods: List[int], opt_years: Optional[List[int]]):
        """Stacked bar by measure for investment costs (c_inv_ prefix) + deinstallation bar."""
        nested = _parse_investment_by_measure(net_costs_raw)
        measures = sorted(
            m for m, periods in nested.items()
            if any(v != 0 for v in periods.values()) and not _is_excluded_measure(m)
        )
        uninst_data = _safe_parse(uninst_raw)
        if not measures and not uninst_data:
            st.info("Keine Investitionsdaten verfügbar.")
            return
        sparse = sorted({p for periods in nested.values() for p in periods} | set(uninst_data.keys()))
        all_periods = full_periods if full_periods else sparse
        all_years   = _periods_to_years(all_periods, opt_years)
        fig = go.Figure()
        for measure in measures:
            values = [nested[measure].get(p, 0) for p in all_periods]
            translated = get_technology_translation(measure)
            color = get_technology_color(measure)
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kosten: %{{y:,.0f}} €<extra></extra>",
            ))
        if uninst_data:
            fig.add_trace(go.Bar(
                name="Deinstallationskosten",
                x=[str(y) for y in all_years],
                y=[uninst_data.get(p, 0) for p in all_periods],
                marker_color="#dc2626",
                hovertemplate="Deinstallationskosten<br>Jahr: %{x}<br>Kosten: %{y:,.0f} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Kosten in €")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True, key="bldg_investments")

    def _render_building_subsidies_line_chart(self, subsidies: dict, opt_years: Optional[List[int]]):
        """Total subsidies as line chart."""
        sub_data = _safe_parse(subsidies)
        if not sub_data or not any(abs(v) > 0 for v in sub_data.values()):
            st.info("Keine Förderungen in Anspruch genommen")
            return
        periods = sorted(sub_data)
        years   = _periods_to_years(periods, opt_years)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=[sub_data[p] for p in periods],
            mode="lines+markers", name="Förderungen", fill="tozeroy",
            fillcolor="rgba(255,215,0,0.15)", line=dict(color="#FFD700", width=3), marker=dict(size=10),
            hovertemplate="Jahr: %{x}<br>Förderungen: %{y:,.0f} €<extra></extra>",
        ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Förderungen in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified", showlegend=False,
            xaxis=dict(tickmode="array", tickvals=years))
        st.plotly_chart(fig, use_container_width=True, key="bldg_subsidies")

    def _render_building_co2_costs_chart(self, co2_data: Dict[int, float], opt_years: Optional[List[int]]):
        periods = sorted(p for p in co2_data if p >= 0)
        if not periods:
            st.info("Keine CO₂-Kostendaten verfügbar.")
            return
        years = _periods_to_years(periods, opt_years)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=years, y=[co2_data[p] for p in periods],
            mode="lines+markers", name="CO₂-Kosten Vermieter €",
            line=dict(color="#b45309", width=3), marker=dict(size=8),
            hovertemplate="Jahr: %{x}<br>CO₂-Kosten: %{y:,.0f} €<extra></extra>",
        ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "CO₂-Kosten in € / Jahr")
        fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
            yaxis=yaxis_dict, height=380, hovermode="x unified", showlegend=False,
            xaxis=dict(tickmode="array", tickvals=years))
        st.plotly_chart(fig, use_container_width=True, key="bldg_co2_costs")

    def _render_building_credit_chart(self, credits_raw: dict, opt_years: Optional[List[int]]):
        """Stacked bar + line view of credits per measure per period."""
        nested = _parse_measure_period_keys(credits_raw)
        measures = sorted(
            m for m, periods in nested.items()
            if any(v > 0 for v in periods.values()) and not _is_excluded_measure(m)
        )
        if not measures:
            st.info("Keine Kreditdaten mit Werten > 0 gefunden.")
            return
        all_periods = sorted({p for periods in nested.values() for p in periods})
        all_years   = _periods_to_years(all_periods, opt_years)
        tab1, tab2 = st.tabs(["Gestapeltes Balkendiagramm", "Liniendiagramm"])
        with tab1:
            fig = go.Figure()
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in all_periods]
                translated = get_technology_translation(measure)
                color = get_technology_color(measure)
                fig.add_trace(go.Bar(
                    name=translated, x=[str(y) for y in all_years], y=values,
                    marker_color=color,
                    hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kredit: %{{y:,.2f}} €<extra></extra>",
                ))
            display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig, "Kreditbetrag in €")
            fig.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
                yaxis=yaxis_dict,
                xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
                barmode="stack", height=420, showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, use_container_width=True, key="bldg_credit_bar")
        with tab2:
            fig2 = go.Figure()
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in all_periods]
                translated = get_technology_translation(measure)
                fig2.add_trace(go.Scatter(
                    x=all_years, y=values, mode="lines+markers", name=translated,
                    line=dict(width=2), marker=dict(size=7),
                ))
            display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig2, "Kreditbetrag in €")
            fig2.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title,
                yaxis=yaxis_dict, height=420, hovermode="x unified",
                xaxis=dict(tickmode="array", tickvals=all_years),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig2, use_container_width=True, key="bldg_credit_line")

    def _render_building_depreciation_chart(self, dep_per_measure: dict, dep_existing_per_measure: dict, opt_years: Optional[List[int]]):
        nested = _parse_measure_period_keys(dep_per_measure)
        nested_existing = _parse_measure_period_keys(dep_existing_per_measure)

        combined_nested: Dict[str, Dict[int, float]] = {m: dict(periods) for m, periods in nested.items()}
        for measure, periods in nested_existing.items():
            combined_nested[f"{measure}__bestand"] = dict(periods)

        has_per_measure = bool(combined_nested) and any(
            any(v > 0 for v in periods.values())
            for m, periods in combined_nested.items()
            if not _is_excluded_measure(m.replace("__bestand", ""))
        )
        if not has_per_measure:
            st.info("Keine Maßnahmen mit Abschreibungen > 0 gefunden.")
            return

        measures = sorted(
            m for m, periods in combined_nested.items()
            if any(v > 0 for v in periods.values()) and not _is_excluded_measure(m.replace("__bestand", ""))
        )
        if not measures:
            st.info("Keine Maßnahmen mit Abschreibungen > 0 gefunden.")
            return

        all_p = sorted({p for periods in combined_nested.values() for p in periods})
        all_p_years = _periods_to_years(all_p, opt_years)
        fig2 = go.Figure()
        for measure in measures:
            is_existing = measure.endswith("__bestand")
            measure_base = measure[:-10] if is_existing else measure
            values = [combined_nested[measure].get(p, 0) for p in all_p]
            translated = get_technology_translation(measure_base)
            if is_existing:
                translated = f"{translated} (Bestand)"
            fig2.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_p_years], y=values,
                hovertemplate=f"<b>{translated}</b><br>Jahr: %{{x}}<br>Kosten: %{{y:,.2f}} €<extra></extra>",
            ))
        display_y_title, yaxis_dict, _ = _autoscale_currency_figure(fig2, "Abschreibungen in € / Jahr")
        fig2.update_layout(xaxis_title="Jahr", yaxis_title=display_y_title, barmode="stack", height=500,
            yaxis=yaxis_dict,
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_p_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig2, use_container_width=True, key="bldg_depreciation_by_measure")

    # =======================================================================
    # Legacy raw-data helper (kept for _render_portfolio_kpi_table)
    # =======================================================================

    def _render_raw_data(self, *args, **kwargs):
        """Deprecated – functionality moved to _render_portfolio_kpi_table."""
        pass
