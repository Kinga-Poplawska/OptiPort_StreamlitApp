"""
Investment analysis visualization: Equity / Debt / Liquidity timeline
from ProcessedPortfolioResult.
"""
import plotly.graph_objects as go
import streamlit as st
from typing import List, Optional

from .base_viz import BaseVisualization
from core.data_models import ProcessedPortfolioResult, ProcessedBuildingResult
from utils.data_processing import parse_period_dict, get_currency_axis_config


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


class InvestmentAnalysis(BaseVisualization):
    """Visualization for equity, debt and liquidity over the planning horizon."""

    def __init__(self):
        super().__init__(
            title="Eigenkapital- und Schuldenverlauf",
            description=""
        )

    # ------------------------------------------------------------------
    # Public API expected by OptimizationResultsPage
    # ------------------------------------------------------------------

    def render(
        self,
        portfolio_result: ProcessedPortfolioResult,
        building_results: List[ProcessedBuildingResult],
        key: str = "investment_analysis",
        opt_years: Optional[List[int]] = None,
        **kwargs,
    ):
        """Render the finance overview tab."""
        fig = self.create_figure(portfolio_result, opt_years=opt_years, **kwargs)
        st.plotly_chart(fig, use_container_width=True, key=key)
        # Tooltip for "Liquidität (kritisch)"
        st.caption(
            "ℹ️ **Kritische Liquidität**: Liquidität nach Investitions- und "
            "Fördertransaktionen (Kredite, Installationskosten, Boni, Förderungen), "
            "aber vor betrieblichem Cashflow (Miete, Energieerlöse, Zinsen, Tilgung)."
        )
        # EK-Quote as a separate chart below
        fig_quota = self.create_equity_quota_figure(portfolio_result, opt_years=opt_years)
        st.plotly_chart(fig_quota, use_container_width=True, key=key + "_ekquote")

    # ------------------------------------------------------------------
    # Figure creation
    # ------------------------------------------------------------------

    def create_figure(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
        **kwargs,
    ) -> go.Figure:
        """Create equity / debt / liquidity timeline from ProcessedPortfolioResult."""

        equity_data    = parse_period_dict(portfolio_result.equity)
        debt_data      = parse_period_dict(portfolio_result.debt)
        liquidity_data = parse_period_dict(portfolio_result.liquidity)
        liq_crit_data  = parse_period_dict(
            getattr(portfolio_result, "liquidity_critical", None) or {}
        )

        cp = getattr(portfolio_result, "constraint_params", None) or {}
        init_equity = kwargs.get("initial_equity")
        if init_equity is None:
            init_equity = cp.get("q_init")
        if init_equity is None:
            init_equity = equity_data.get(-1)

        init_debt = kwargs.get("initial_debt")
        if init_debt is None:
            init_debt = cp.get("d_init")
        if init_debt is None:
            init_debt = debt_data.get(-1)

        init_liquidity = kwargs.get("initial_liquidity")
        if init_liquidity is None:
            init_liquidity = cp.get("l_liq_init")
        if init_liquidity is None:
            init_liquidity = liquidity_data.get(-1)
        if init_liquidity is None and 0 in liquidity_data:
            init_liquidity = liquidity_data[0]

        has_today_point = any(v is not None for v in (init_equity, init_debt, init_liquidity))

        all_periods = sorted(
            set(list(equity_data.keys()) + list(debt_data.keys()) + list(liquidity_data.keys()))
        )
        planning_periods = [p for p in all_periods if p >= 0]

        if not planning_periods and not has_today_point:
            return self._create_empty_figure("Keine Zeitreihendaten für EK / Schulden / Liquidität gefunden")

        planning_years = _periods_to_years(planning_periods, opt_years)
        planning_x = [str(y) for y in planning_years]
        x_ticks = (["Heute"] if has_today_point else []) + planning_x

        fig = go.Figure()

        # Equity
        equity_periods = [p for p in planning_periods if p in equity_data]
        if equity_periods or init_equity is not None:
            x_values = (["Heute"] if init_equity is not None else []) + [str(_periods_to_years([p], opt_years)[0]) for p in equity_periods]
            y_values = ([init_equity] if init_equity is not None else []) + [equity_data[p] for p in equity_periods]
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                customdata=y_values,
                mode="lines+markers", name="Eigenkapital",
                line=dict(color="#2563eb", width=3), marker=dict(size=8),
                yaxis="y"
            ))

        # Debt
        debt_periods = [p for p in planning_periods if p in debt_data]
        if debt_periods or init_debt is not None:
            x_values = (["Heute"] if init_debt is not None else []) + [str(_periods_to_years([p], opt_years)[0]) for p in debt_periods]
            y_values = ([init_debt] if init_debt is not None else []) + [debt_data[p] for p in debt_periods]
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                customdata=y_values,
                mode="lines+markers", name="Schulden",
                line=dict(color="#dc2626", width=3), marker=dict(size=8),
                yaxis="y"
            ))

        # Liquidity
        liq_periods = [p for p in planning_periods if p in liquidity_data]
        if liq_periods or init_liquidity is not None:
            x_values = (["Heute"] if init_liquidity is not None else []) + [str(_periods_to_years([p], opt_years)[0]) for p in liq_periods]
            y_values = ([init_liquidity] if init_liquidity is not None else []) + [liquidity_data[p] for p in liq_periods]
            fig.add_trace(go.Scatter(
                x=x_values,
                y=y_values,
                customdata=y_values,
                mode="lines+markers", name="Liquidität",
                line=dict(color="#059669", width=3), marker=dict(size=8),
                yaxis="y"
            ))

        # Critical liquidity (post-investment-transactions, pre-operating-cashflow)
        liq_crit_periods = [p for p in planning_periods if p in liq_crit_data]
        if liq_crit_periods:
            liq_crit_values = [liq_crit_data[p] for p in liq_crit_periods]
            fig.add_trace(go.Scatter(
                x=[str(_periods_to_years([p], opt_years)[0]) for p in liq_crit_periods],
                y=liq_crit_values,
                customdata=liq_crit_values,
                mode="lines+markers",
                name="Kritische Liquidität ⓘ",
                line=dict(color="#059669", width=2, dash="dot"),
                marker=dict(size=6, symbol="triangle-down"),
                yaxis="y",
                hovertemplate="<b>Kritische Liquidität</b><br>"
                    "Liquidität nach Investitions- und Fördertransaktionen,<br>"
                    "vor betrieblichem Cashflow<br>"
                    "Jahr: %{x}<br>Betrag: %{customdata:,.0f} €<extra></extra>",
            ))

        # Keep a small visual buffer below 0 so floor annotations near the axis remain readable.
        y_values_all = []
        y_values_all.extend(v for v in (init_equity, init_debt, init_liquidity) if v is not None)
        y_values_all.extend(equity_data[p] for p in equity_periods)
        y_values_all.extend(debt_data[p] for p in debt_periods)
        y_values_all.extend(liquidity_data[p] for p in liq_periods)
        y_values_all.extend(liq_crit_data[p] for p in liq_crit_periods)

        if y_values_all:
            y_min_data = min(y_values_all)
            y_max_data = max(y_values_all)
        else:
            y_min_data = 0
            y_max_data = 0

        currency_axis = get_currency_axis_config(y_values_all, "€")
        scale_factor = currency_axis["scale_factor"]
        currency_unit = currency_axis["unit"]

        if scale_factor != 1.0:
            for trace in fig.data:
                if trace.y is not None:
                    trace.y = [float(v) / scale_factor if v is not None else v for v in trace.y]

        for trace in fig.data:
            if trace.hovertemplate is None:
                trace.hovertemplate = (
                    f"<b>%{{fullData.name}}</b><br>"
                    f"Jahr: %{{x}}<br>"
                    "Betrag: %{customdata:,.0f} €<extra></extra>"
                )

        y_min_data = y_min_data / scale_factor if scale_factor != 0 else y_min_data
        y_max_data = y_max_data / scale_factor if scale_factor != 0 else y_max_data

        y_max_base = max(y_max_data, 0)
        y_span = max(y_max_base, 1.0)
        y_range = [0, y_max_base + 0.05 * y_span]

        fig.update_layout(
            xaxis_title="Jahr",
            xaxis=dict(tickmode="array", tickvals=x_ticks,
                       ticktext=x_ticks,
                       type="category",
                       categoryorder="array",
                       categoryarray=x_ticks),
            yaxis=dict(title=f"Betrag in {currency_unit}", side="left", range=y_range,
                       gridcolor="rgba(200, 200, 200, 0.5)", tickformat=currency_axis["tickformat"]),
            hovermode="x unified",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.06,
                        xanchor="center", x=0.5),
            margin=dict(t=130)
        )

        # Min liquidity floor
        l_liq_min = cp.get("l_liq_min")
        if l_liq_min is not None and l_liq_min > 0:
            scaled_liq_min = l_liq_min / scale_factor if scale_factor != 0 else l_liq_min
            fig.add_hline(
                y=scaled_liq_min, line_dash="dash", line_color="#059669", line_width=2,
                annotation_text="Min. Liquidität",
                annotation_position="bottom right",
                annotation_font_color="#059669",
                yref="y",
            )

        return fig

    def create_equity_quota_figure(
        self,
        portfolio_result: ProcessedPortfolioResult,
        opt_years: Optional[List[int]] = None,
        **kwargs,
    ) -> go.Figure:
        """Create a standalone Eigenkapitalquote (EK-Quote) chart."""
        equity_data = parse_period_dict(portfolio_result.equity)
        debt_data   = parse_period_dict(portfolio_result.debt)

        all_periods = sorted(
            set(list(equity_data.keys()) + list(debt_data.keys()))
        )
        planning_periods = [p for p in all_periods if p >= 0]

        init_equity = equity_data.get(-1)
        init_debt = debt_data.get(-1)
        has_today_point = init_equity is not None and init_debt is not None

        if not planning_periods and not has_today_point:
            return self._create_empty_figure("Keine Daten für EK-Quote verfügbar")

        planning_years = _periods_to_years(planning_periods, opt_years)
        planning_x = [str(y) for y in planning_years]
        x_values = (["Heute"] if has_today_point else []) + planning_x

        planning_quotas = {}
        for p in planning_periods:
            eq = equity_data.get(p, 0)
            de = debt_data.get(p, 0)
            total = eq + de
            planning_quotas[p] = (eq / total * 100) if total > 0 else 0

        y_values = []
        if has_today_point:
            today_total = init_equity + init_debt
            today_quota = (init_equity / today_total * 100) if today_total > 0 else 0
            y_values.append(today_quota)
        y_values.extend(planning_quotas[p] for p in planning_periods)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines+markers",
            name="Eigenkapitalquote",
            line=dict(color="#7c3aed", width=3),
            marker=dict(size=8, symbol="diamond"),
        ))

        fig.update_layout(
            title="Eigenkapitalquote (EK-Quote)",
            xaxis_title="Jahr",
            xaxis=dict(tickmode="array", tickvals=x_values,
                       ticktext=x_values,
                       type="category",
                       categoryorder="array",
                       categoryarray=x_values),
            yaxis=dict(title="EK-Quote in %", rangemode="tozero",
                       gridcolor="rgba(200, 200, 200, 0.5)"),
            hovermode="x unified",
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.06,
                        xanchor="center", x=0.5),
            margin=dict(t=80),
        )

        # Min equity quota reference line
        cp = getattr(portfolio_result, "constraint_params", None) or {}
        q_quota = cp.get("q_quota")
        if q_quota is not None and q_quota > 0:
            fig.add_hline(
                y=q_quota * 100, line_dash="dash", line_color="#7c3aed",
                line_width=2,
                annotation_text=f"Min. EK-Quote ({q_quota*100:.0f}%)",
                annotation_position="top right",
                annotation_font_color="#7c3aed",
            )

        return fig
