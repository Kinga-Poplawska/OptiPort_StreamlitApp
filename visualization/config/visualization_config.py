"""
Visualization-specific configuration settings
"""

# Chart settings
CHART_CONFIG = {
    "height": {
        "small": 300,
        "medium": 400, 
        "large": 600,
        "xlarge": 800
    },
    "default_theme": "plotly_white",
    "font_family": "Arial, sans-serif",
    "title_size": 16,
    "axis_title_size": 14,
    "legend_size": 12
}

# Dashboard layout settings
DASHBOARD_CONFIG = {
    "sidebar_width": 300,
    "main_content_padding": "1rem",
    "metric_card_height": 120,
    "chart_margin": {"t": 40, "b": 40, "l": 40, "r": 40}
}

# Export settings
EXPORT_CONFIG = {
    "formats": ["png", "svg", "pdf", "html"],
    "default_dpi": 300,
    "default_width": 1200,
    "default_height": 800
}
