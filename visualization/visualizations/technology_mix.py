"""
Technology mix visualization built on ProcessedPortfolioResult and
ProcessedBuildingResult – no .sol parsing, no regex.
"""
import hashlib
import plotly.graph_objects as go
import streamlit as st
from typing import Dict, List, Optional

from .base_viz import BaseVisualization
from core.data_models import ProcessedPortfolioResult, ProcessedBuildingResult
from config.translations import get_technology_translation
from config.technology_colors import get_technology_color
from utils.data_processing import parse_period_dict, get_energy_axis_config, get_power_axis_config, get_currency_axis_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tech_color(measure_type: str) -> str:
    """Deterministic color per measure name using consistent technology colors."""
    # Use the new centralized color mapping
    return get_technology_color(measure_type)


# Hull / fix measure category definitions
_HULL_FIX_CATEGORIES = ["roof", "wall", "win", "rad"]


def _classify_hull_fix(measure: str) -> Optional[str]:
    """Return hull/fix category ('roof','wall','win','rad','ufh') or None."""
    for prefix in _HULL_FIX_CATEGORIES:
        if measure.startswith(prefix):
            return prefix
    if measure == "ufh":
        return "rad"
    return None


def _hull_fix_color(measure_type: str) -> str:
    """Return the color for a specific hull/fix measure type using centralized colors."""
    return get_technology_color(measure_type)


def _parse_measure_period_keys(flat: Dict[str, float]) -> Dict[str, Dict[int, float]]:
    """
    Convert a flat measure×period dict like {"eh_t0": 1.0, "eh_t2": 2.0, ...}
    into a nested dict {measure: {period_int: value}}.

    Key format: "{anything}_t{int}" – the last "_t{int}" segment is the period.
    """
    result: Dict[str, Dict[int, float]] = {}
    for key, value in flat.items():
        # Find the last occurrence of "_t" followed by digits (possibly negative)
        # e.g. "el_converter_t9" → measure="el_converter", period=9
        idx = key.rfind("_t")
        if idx == -1:
            continue
        measure = key[:idx]
        period_str = key[idx + 2:]   # strip "_t"
        try:
            period = int(period_str)
        except ValueError:
            continue
        if measure not in result:
            result[measure] = {}
        result[measure][period] = value
    return result


def _full_periods(dense_period_dict: dict) -> List[int]:
    """
    Extract the complete sorted period list from a dense period-keyed dict
    (e.g. costs_investment {"t0": 0, "t1": 0, …}).
    Ensures charts always show every year of the planning horizon.
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


def _is_excluded_measure(measure: str) -> bool:
    """Return True for measures that should never appear in charts."""
    return "el_converter" in measure


_STORAGE_PREFIXES = ("tes", "bat")

def _is_storage_measure(measure: str) -> bool:
    """Return True for storage measures (tes, tes_dhw, bat)."""
    return measure.startswith(_STORAGE_PREFIXES)


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class TechnologyMix(BaseVisualization):
    """Portfolio-Analyse visualization."""

    def __init__(self):
        super().__init__(
            title="Portfolio-Analyse",
            description=""
        )

    # -----------------------------------------------------------------------
    # Public render entry-point
    # -----------------------------------------------------------------------

    def render(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        opt_years: Optional[List[int]] = None,
        **kwargs,
    ):
        # 1. Total emissions over time
        st.subheader("Gesamtemissionen über den Planungshorizont")
        fig_em = self._create_emission_chart(portfolio_result, opt_years)
        st.plotly_chart(fig_em, use_container_width=True, key="portfolio_emissions")

        st.markdown("---")

        # 2. Verfügbare Kapazitäten im Portfolio
        st.subheader("Verfügbare Kapazitäten im Portfolio")
        st.markdown("#### Energietransformatoren")
        fig_tra = self._create_capacity_chart(portfolio_result, opt_years, storage=False)
        st.plotly_chart(fig_tra, use_container_width=True, key="portfolio_capacity_tra")

        st.markdown("#### Speicher")
        fig_sto = self._create_capacity_chart(portfolio_result, opt_years, storage=True)
        st.plotly_chart(fig_sto, use_container_width=True, key="portfolio_capacity_sto")

        # 2b. Verfügbare Effizienzmaßnahmen (hull + heating distribution)
        fig_hull_avail = self._create_hull_available_chart(building_results, portfolio_result, opt_years)
        if fig_hull_avail is not None:
            st.markdown("#### Effizienzmaßnahmen")
            st.plotly_chart(fig_hull_avail, use_container_width=True, key="portfolio_hull_available")

        st.markdown("---")

        # 3. Neuinstallationen im Portfolio
        st.subheader("Neuinstallationen im Portfolio")
        st.markdown("#### Energietransformatoren")
        fig_new_tra = self._create_installed_measures_chart(portfolio_result, opt_years, storage=False)
        st.plotly_chart(fig_new_tra, use_container_width=True, key="portfolio_inst_tra")

        st.markdown("#### Speicher")
        fig_new_sto = self._create_installed_measures_chart(portfolio_result, opt_years, storage=True)
        st.plotly_chart(fig_new_sto, use_container_width=True, key="portfolio_inst_sto")

        # 3b. Neuinstallierte Effizienzmaßnahmen
        fig_hull_inst = self._create_hull_fix_installed_chart(portfolio_result, opt_years)
        if fig_hull_inst is not None:
            st.markdown("#### Effizienzmaßnahmen")
            st.plotly_chart(fig_hull_inst, use_container_width=True, key="portfolio_hull_installed")

    # -----------------------------------------------------------------------
    # Charts
    # -----------------------------------------------------------------------

    def _create_emission_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
    ) -> go.Figure:
        """Line chart of embodied, operational and total CO₂ emissions over time."""
        try:
            emb_data = parse_period_dict(portfolio_result.emissions_embodied)
            op_data  = parse_period_dict(portfolio_result.emissions_operational)
            tot_data = parse_period_dict(portfolio_result.emissions_total)
        except Exception:
            return self._create_empty_figure("Keine Emissionsdaten verfügbar")

        all_periods = sorted(set(list(emb_data) + list(op_data) + list(tot_data)))
        if not all_periods:
            return self._create_empty_figure("Keine Zeitreihendaten für Emissionen gefunden")

        all_years = _periods_to_years(all_periods, opt_years)

        fig = go.Figure()
        if emb_data:
            fig.add_trace(go.Scatter(
                x=all_years, y=[emb_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gebundene Emissionen",
                line=dict(color="#8c564b", width=3), marker=dict(size=8),
            ))
        if op_data:
            fig.add_trace(go.Scatter(
                x=all_years, y=[op_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Betriebsemissionen",
                line=dict(color="#ff7f0e", width=3), marker=dict(size=8),
            ))
        if tot_data:
            fig.add_trace(go.Scatter(
                x=all_years, y=[tot_data.get(p, 0) / 1_000 for p in all_periods],
                mode="lines+markers", name="Gesamtemissionen",
                line=dict(color="#d62728", width=3, dash="dash"), marker=dict(size=8),
            ))
        fig.update_layout(
            xaxis_title="Jahr", yaxis_title="CO₂-Emissionen t CO₂",
            yaxis=dict(rangemode="tozero"), height=420, hovermode="x unified",
            xaxis=dict(tickmode="array", tickvals=all_years),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig

    def _create_capacity_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
        storage: bool = False,
    ) -> go.Figure:
        """Stacked bar: available capacity per measure per period.

        When *storage=True*, only storage measures are shown (tes, bat).
        When *storage=False*, only non-storage (transformer) measures are shown.
        """
        nested = _parse_measure_period_keys(portfolio_result.capacity_available_total)
        if not nested:
            return self._create_empty_figure("Keine Kapazitätsdaten gefunden")

        all_periods = _full_periods(portfolio_result.costs_investment)
        if not all_periods:
            all_periods = sorted({p for periods in nested.values() for p in periods})
        all_years = _periods_to_years(all_periods, opt_years)

        measures = sorted(
            m for m, periods in nested.items()
            if any(v > 0 for v in periods.values())
            and not _is_excluded_measure(m)
            and _is_storage_measure(m) == storage
        )
        if not measures:
            lbl = "Speicher" if storage else "Energietransformatoren"
            return self._create_empty_figure(f"Keine {lbl} > 0 gefunden")

        # Autoscaling for both storage (Wh) and transformers (W)
        base_unit = "Wh" if storage else "W"
        use_autoscale = True
        axis_config = None
        if use_autoscale:
            all_values = []
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in all_periods]
                all_values.extend(values)
            if base_unit == "Wh":
                axis_config = get_energy_axis_config(all_values, "Wh")
            else:
                axis_config = get_power_axis_config(all_values, "W")

        fig = go.Figure()
        for measure in measures:
            raw_values = [nested[measure].get(p, 0) for p in all_periods]
            values = raw_values
            if use_autoscale and axis_config:
                values = [v / axis_config["scale_factor"] for v in values]
            translated = get_technology_translation(measure)
            fig.add_trace(go.Bar(
                name=translated,
                x=[str(y) for y in all_years],
                y=values,
                customdata=raw_values if use_autoscale and axis_config else None,
                marker_color=_tech_color(measure),
                hovertemplate=(
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    f"Kapazität: %{{customdata:,.0f}} {base_unit}<br>"
                    "<extra></extra>"
                ) if use_autoscale and axis_config else (
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    f"Kapazität: %{{y:{axis_config['tickformat'] if axis_config else ',.0f'}}} {axis_config['unit'] if axis_config else ('Wh' if storage else 'W')}<br>"
                    "<extra></extra>"
                )
            ))
        
        # Update y_label with autoscaled unit
        if use_autoscale and axis_config:
            y_label = f"Verfügbare Kapazität in {axis_config['unit']}"
            tickformat = axis_config["tickformat"]
        else:
            y_label = "Verfügbare Kapazität in Wh" if storage else "Verfügbare Kapazität in W"
            tickformat = ",.0f"
        
        fig.update_layout(
            xaxis_title="Jahr",
            yaxis_title=y_label,
            yaxis=dict(rangemode="tozero", tickformat=tickformat),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    # Keep the old name as a public alias (used by create_figure)
    def create_installation_pathway(self, portfolio_result, opt_years=None):
        return self._create_capacity_chart(portfolio_result, opt_years, storage=False)

    def _create_installed_measures_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
        storage: bool = False,
    ) -> go.Figure:
        """Stacked bar: newly installed capacity per measure per period."""
        nested = _parse_measure_period_keys(portfolio_result.capacity_installed_total)
        if not nested:
            return self._create_empty_figure("Keine Neuinstallationsdaten gefunden")

        all_periods = _full_periods(portfolio_result.costs_investment)
        if not all_periods:
            all_periods = sorted({p for periods in nested.values() for p in periods})
        all_years = _periods_to_years(all_periods, opt_years)

        measures = sorted(
            m for m, periods in nested.items()
            if any(v > 0 for v in periods.values())
            and not _is_excluded_measure(m)
            and _is_storage_measure(m) == storage
        )
        if not measures:
            lbl = "Speicher" if storage else "Energietransformatoren"
            return self._create_empty_figure(f"Keine {lbl}-Neuinstallationen > 0 gefunden")

        # Autoscaling for both storage (Wh) and transformers (W)
        base_unit = "Wh" if storage else "W"
        use_autoscale = True
        axis_config = None
        if use_autoscale:
            all_values = []
            for measure in measures:
                values = [nested[measure].get(p, 0) for p in all_periods]
                all_values.extend(values)
            if base_unit == "Wh":
                axis_config = get_energy_axis_config(all_values, "Wh")
            else:
                axis_config = get_power_axis_config(all_values, "W")

        fig = go.Figure()
        for measure in measures:
            raw_values = [nested[measure].get(p, 0) for p in all_periods]
            values = raw_values
            if use_autoscale and axis_config:
                values = [v / axis_config["scale_factor"] for v in values]
            translated = get_technology_translation(measure)
            fig.add_trace(go.Bar(
                name=translated,
                x=[str(y) for y in all_years],
                y=values,
                customdata=raw_values if use_autoscale and axis_config else None,
                marker_color=_tech_color(measure),
                hovertemplate=(
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    f"Kapazität: %{{customdata:,.0f}} {base_unit}<br>"
                    "<extra></extra>"
                ) if use_autoscale and axis_config else (
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    f"Kapazität: %{{y:{axis_config['tickformat'] if axis_config else ',.0f'}}} {axis_config['unit'] if axis_config else ('Wh' if storage else 'W')}<br>"
                    "<extra></extra>"
                )
            ))
        
        # Update y_label with autoscaled unit
        if use_autoscale and axis_config:
            y_label = f"Neu verfügbare Kapazität in {axis_config['unit']}"
            tickformat = axis_config["tickformat"]
        else:
            y_label = "Neu verfügbare Kapazität in Wh" if storage else "Neu verfügbare Kapazität in W"
            tickformat = ",.0f"
        
        fig.update_layout(
            xaxis_title="Jahr",
            yaxis_title=y_label,
            yaxis=dict(rangemode="tozero", tickformat=tickformat),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return fig

    # -----------------------------------------------------------------------
    # Hull / fix measure charts
    # -----------------------------------------------------------------------

    def _create_hull_available_chart(
        self,
        building_results: List[ProcessedBuildingResult],
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
    ) -> Optional[go.Figure]:
        """Grouped stacked bar: disaggregated hull types + heating distribution
        active across portfolio buildings.

        Hull types come from ``available_hull_measures``.
        Heating distribution (rad/ufh) comes from ``available_dis_measures``.
        """
        all_periods = _full_periods(portfolio_result.costs_investment)
        if not all_periods:
            return None

        # type_counts[type_key][period] = number of buildings with that type active
        type_counts: Dict[str, Dict[int, int]] = {}

        for br in building_results:
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
                type_counts.setdefault(type_key, {})
                type_counts[type_key][period] = type_counts[type_key].get(period, 0) + 1

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
                type_counts.setdefault(measure, {})
                type_counts[measure][period] = type_counts[measure].get(period, 0) + 1

        if not type_counts:
            return None

        all_years = _periods_to_years(all_periods, opt_years)

        # Order: best efficiency at bottom (level 3 first), rad types at end
        ordered_types = [
            f"{cat}_{lvl}"
            for cat in ("roof", "wall", "win")
            for lvl in (3, 2, 1)
            if f"{cat}_{lvl}" in type_counts
        ] + sorted((k for k in type_counts if k.startswith("rad") or k == "ufh"), reverse=True)

        fig = go.Figure()
        for type_key in ordered_types:
            translated = get_technology_translation(type_key)
            color = _hull_fix_color(type_key)
            cat = _classify_hull_fix(type_key) or type_key.rsplit("_", 1)[0]
            values = [type_counts[type_key].get(p, 0) for p in all_periods]
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                marker_color=color,
                offsetgroup=cat,
                legendgroup=cat,
                hovertemplate=(
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    "Anzahl Gebäude: %{y}<br>"
                    "<extra></extra>"
                ),
            ))
        fig.update_layout(
            xaxis_title="Jahr",
            yaxis_title="Anzahl Gebäude",
            barmode="stack", height=420, showlegend=True,
            yaxis=dict(dtick=1, rangemode="tozero"),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig

    def _create_hull_fix_installed_chart(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
    ) -> Optional[go.Figure]:
        """Stacked bar: investment costs for newly installed hull/fix measures,
        disaggregated by specific type (roof_1, wall_3, rad_11, …)."""
        inv_data = portfolio_result.investment_by_measure_total
        if not inv_data:
            return None

        # Parse investment_by_measure keys → {measure_type: {period: cost}}
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
            if _classify_hull_fix(measure) is None:
                continue
            type_costs.setdefault(measure, {})
            type_costs[measure][period] = type_costs[measure].get(period, 0) + cost

        if not type_costs:
            return None

        all_periods = _full_periods(portfolio_result.costs_investment)
        all_years = _periods_to_years(all_periods, opt_years)

        # Order: best efficiency at bottom (highest number first within each category)
        def _sort_key(m):
            if m.startswith("roof"): return (0, m)
            if m.startswith("wall"): return (1, m)
            if m.startswith("win"):  return (2, m)
            return (3, m)
        ordered = sorted(type_costs.keys(), key=_sort_key, reverse=True)

        fig = go.Figure()
        for measure in ordered:
            translated = get_technology_translation(measure)
            color = _hull_fix_color(measure)
            category = _classify_hull_fix(measure)  # e.g. "roof", "wall", "rad"
            values = [type_costs[measure].get(p, 0) for p in all_periods]
            if all(v == 0 for v in values):
                continue
            fig.add_trace(go.Bar(
                name=translated, x=[str(y) for y in all_years], y=values,
                customdata=values,
                marker_color=color,
                offsetgroup=category,
                legendgroup=category,
                hovertemplate=(
                    f"<b>{translated}</b><br>"
                    "Jahr: %{x}<br>"
                    "Kosten: %{customdata:,.0f} €<br>"
                    "<extra></extra>"
                ),
            ))

        all_vals_currency = []
        for trace in fig.data:
            if trace.y is not None:
                all_vals_currency.extend([float(v) for v in trace.y if v is not None])
        currency_axis = get_currency_axis_config(all_vals_currency, "€")

        if currency_axis["scale_factor"] != 1.0:
            for trace in fig.data:
                if trace.y is not None:
                    trace.y = [float(v) / currency_axis["scale_factor"] if v is not None else v for v in trace.y]

        fig.update_layout(
            xaxis_title="Jahr",
            yaxis_title=f"Investitionskosten in {currency_axis['unit']}",
            yaxis=dict(rangemode="tozero", tickformat=currency_axis["tickformat"]),
            xaxis=dict(tickmode="array", tickvals=[str(y) for y in all_years]),
            barmode="stack", height=420, showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        return fig


    # -----------------------------------------------------------------------
    # Required by BaseVisualization
    # -----------------------------------------------------------------------

    def create_figure(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
        **kwargs,
    ) -> go.Figure:
        return self.create_installation_pathway(portfolio_result, opt_years)
