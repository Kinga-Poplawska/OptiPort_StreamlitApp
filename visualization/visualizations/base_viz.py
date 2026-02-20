"""
Base visualization class for all charts and plots
"""
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from config.visualization_config import CHART_CONFIG
from config.app_config import COLOR_SCHEMES
from core.data_models import OptimizationSolution

class BaseVisualization(ABC):
    """Base class for all visualizations"""
    
    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.config = CHART_CONFIG
        self.colors = COLOR_SCHEMES
        
    @abstractmethod
    def create_figure(self, solution: OptimizationSolution, instance_data=None, **kwargs) -> go.Figure:
        """Create the visualization figure"""
        pass
    
    def render(self, solution: OptimizationSolution, instance_data=None, **kwargs):
        """Render the visualization in Streamlit"""
        
        st.subheader(self.title)
        
        if self.description:
            st.markdown(self.description)
            
        if not solution:
            st.warning("No solution data available for visualization")
            return
            
        try:
            fig = self.create_figure(solution, instance_data=instance_data, **kwargs)

            if fig:
                # Apply common styling
                fig.update_layout(
                    font_family=self.config["font_family"],
                    title_font_size=self.config["title_size"],
                    font_size=self.config["legend_size"],
                    margin=self.config.get("margin", dict(t=40, b=40, l=40, r=40))
                )
                
                # Display the figure
                st.plotly_chart(fig, use_container_width=True)
                
            else:
                st.error("Could not generate visualization")
                
        except Exception as e:
            st.error(f"Error creating visualization: {e}")
            st.exception(e)
    
    def _get_technology_color(self, technology: str) -> str:
        """Get color for a technology based on its category"""
        tech_lower = technology.lower()
        
        for category, color in self.colors["technology"].items():
            if any(keyword in tech_lower for keyword in [category]):
                return color
                
        return "#95A5A6"  # Default gray color
    
    def _format_currency(self, value: float) -> str:
        """Format currency values"""
        if abs(value) >= 1e6:
            return f"€{value/1e6:.1f}M"
        elif abs(value) >= 1e3:
            return f"€{value/1e3:.0f}K"
        else:
            return f"€{value:.0f}"
    
    def _create_empty_figure(self, message: str = "No data available") -> go.Figure:
        """Create an empty figure with a message"""
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            text=message,
            showarrow=False,
            font=dict(size=16, color="gray")
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=400
        )
        return fig
