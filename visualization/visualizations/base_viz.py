"""
Base visualization class for all charts and plots
"""
import plotly.graph_objects as go
from abc import ABC, abstractmethod

from config.visualization_config import CHART_CONFIG
from config.app_config import COLOR_SCHEMES


class BaseVisualization(ABC):
    """Base class for all visualizations"""

    def __init__(self, title: str, description: str = ""):
        self.title = title
        self.description = description
        self.config = CHART_CONFIG
        self.colors = COLOR_SCHEMES

    @abstractmethod
    def create_figure(self, *args, **kwargs) -> go.Figure:
        """Create the visualization figure"""
        pass

    def _create_empty_figure(self, message: str = "Keine Daten verfügbar") -> go.Figure:
        """Return a blank figure with an annotation message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color="#6b7280")
        )
        fig.update_layout(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            height=300
        )
        return fig
