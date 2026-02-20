"""
Investment analysis visualization showing technology adoption over time
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List
import streamlit as st

from .base_viz import BaseVisualization
from core.data_models import OptimizationSolution

class InvestmentAnalysis(BaseVisualization):
    """Visualization for investment decisions over time periods"""
    
    def __init__(self):
        super().__init__(
            title="Eigenkapital- und Schuldenverlauf", 
            description=""
        )
    
    def create_figure(self, solution: OptimizationSolution = None, instance_data=None, **kwargs) -> go.Figure:
        """Create equity and debt timeline visualization from solution or instance_data"""
        # Extrahiere Variablen aus solution oder instance_data
        if solution is not None:
            q_vars = solution.get_variables_by_type("Q")
            d_vars = solution.get_variables_by_type("D")
            l_vars = solution.get_variables_by_type("L")
        elif instance_data is not None:
            # Extrahiere Q, D, L Variablen aus instance_data
            variables = instance_data.get("variables") if isinstance(instance_data, dict) else getattr(instance_data, "variables", None)
            q_vars = {k: v for k, v in variables.items() if k.startswith("Q_")}
            d_vars = {k: v for k, v in variables.items() if k.startswith("D_")}
            l_vars = {k: v for k, v in variables.items() if k.startswith("L_")}
        else:
            q_vars, d_vars, l_vars = {}, {}, {}

        if not q_vars and not d_vars and not l_vars:
            return self._create_empty_figure("No equity (Q), debt (D), or liquidity (L) variables found")
        
        # Extract time series data
        equity_data = {}
        debt_data = {}
        liquidity_data = {}
        
        # Process Q variables (equity)
        for var in q_vars.values():
            if var.time_period is not None:
                equity_data[var.time_period] = var.value
        
        # Process D variables (debt)  
        for var in d_vars.values():
            if var.time_period is not None:
                debt_data[var.time_period] = var.value
        
        # Process L variables (liquidity)
        for var in l_vars.values():
            if var.time_period is not None:
                liquidity_data[var.time_period] = var.value
        
        if not equity_data and not debt_data and not liquidity_data:
            return self._create_empty_figure("No time period data found for equity, debt, or liquidity")
        
        # Create timeline plot with secondary y-axis
        fig = go.Figure()
        
        # Get all time periods and sort them
        all_periods = sorted(set(list(equity_data.keys()) + list(debt_data.keys()) + list(liquidity_data.keys())))
        
        # Calculate equity quota (equity / (equity + debt) * 100) for each period
        equity_quota_data = {}
        for period in all_periods:
            equity_val = equity_data.get(period, 0)
            debt_val = debt_data.get(period, 0)
            total = equity_val + debt_val
            if total > 0:
                equity_quota_data[period] = (equity_val / total) * 100
            else:
                equity_quota_data[period] = 0
        
        # Add equity line if available
        if equity_data:
            equity_values = [equity_data.get(period, 0) for period in all_periods]
            fig.add_trace(go.Scatter(
                x=all_periods,
                y=equity_values,
                mode='lines+markers',
                name='Eigenkapital (€)',
                line=dict(color='#2563eb', width=3),
                marker=dict(size=8),
                yaxis='y'
            ))
        
        # Add debt line if available
        if debt_data:
            debt_values = [debt_data.get(period, 0) for period in all_periods]
            fig.add_trace(go.Scatter(
                x=all_periods,
                y=debt_values,
                mode='lines+markers',
                name='Schulden (€)',
                line=dict(color='#dc2626', width=3),
                marker=dict(size=8),
                yaxis='y'
            ))
        
        # Add liquidity line if available
        if liquidity_data:
            liquidity_values = [liquidity_data.get(period, 0) for period in all_periods]
            fig.add_trace(go.Scatter(
                x=all_periods,
                y=liquidity_values,
                mode='lines+markers',
                name='Liquidität (€)',
                line=dict(color='#059669', width=3),  # Emerald green, different from equity quota
                marker=dict(size=8),
                yaxis='y',  # Explicitly specify left y-axis
                #hovertemplate="Liquidität (L)</b><br>" +
                #             "Jahr: %{x}<br>" +
                #             "Wert: €%{y:,.2f}<br>" +
                #             "<extra></extra>"
            ))
        
        # Add equity quota line on secondary y-axis
        if equity_quota_data:
            equity_quota_values = [equity_quota_data.get(period, 0) for period in all_periods]
            fig.add_trace(go.Scatter(
                x=all_periods,
                y=equity_quota_values,
                mode='lines+markers',
                name='Eigenkapitalquote (%)',
                line=dict(color='#7c3aed', width=3, dash='dash'),  # Purple color, distinct from others
                marker=dict(size=8, symbol='diamond'),
                yaxis='y2'
            ))
        
        # Update layout for timeline with secondary y-axis
        fig.update_layout(
            title="",
            xaxis_title="Jahr",
            xaxis=dict(
                tickmode='array',
                tickvals=all_periods,
                ticktext=[str(p) for p in all_periods]
            ),
            yaxis=dict(
                title="Betrag (€)",
                side="left",
                rangemode="tozero"  # Ensure y-axis starts from zero
            ),
            yaxis2=dict(
                title="Eigenkapitalquote (%)",
                side="right",
                overlaying="y",
                range=[0, 102]
            ),
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.06,  # Position the legend even lower to create more space from title
                xanchor="center",
                x=0.5
            ),
            margin=dict(t=130)  # Increase top margin further to accommodate more space
        )
        
        return fig
