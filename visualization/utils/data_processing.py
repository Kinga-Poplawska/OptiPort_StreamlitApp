"""
Data processing utilities for transforming and analyzing optimization data.
"""
from typing import Dict
import logging

logger = logging.getLogger(__name__)


def parse_period_dict(d: Dict[str, float]) -> Dict[int, float]:
    """
    Convert a period-keyed dict from the JSON ("t0", "t2", "t-1", ...)
    to an integer-keyed dict (0, 2, -1, ...) suitable for plotting.

    Key format expected: "t{integer}" where integer may be negative (e.g. "t-1").

    Example:
        {"t0": 500000.0, "t2": 530000.0, "t-1": 480000.0}
        → {0: 500000.0, 2: 530000.0, -1: 480000.0}

    Raises:
        ValueError: if a key cannot be converted (i.e. does not start with "t"
                    followed by an integer).
    """
    result: Dict[int, float] = {}
    for k, v in d.items():
        if not k.startswith("t"):
            raise ValueError(
                f"parse_period_dict: unexpected key format '{k}' – expected 't{{int}}'."
            )
        result[int(k[1:])] = v
    return result


def categorize_technology(technology_name: str) -> str:
    """Categorize a technology based on its name."""
    tech_lower = technology_name.lower()

    if any(kw in tech_lower for kw in ["boi", "hp", "chp", "eh", "dh"]):
        return "heating"
    elif any(kw in tech_lower for kw in ["wall", "roof", "win"]):
        return "envelope"
    elif any(kw in tech_lower for kw in ["rad", "ufh"]):
        return "distribution"
    elif any(kw in tech_lower for kw in ["tes", "bat"]):
        return "storage"
    elif any(kw in tech_lower for kw in ["pv", "stc", "el_converter"]):
        return "renewable"
    elif "connection" in tech_lower:
        return "connection"
    else:
        return "other"

def autoscale_energy_values(values, base_unit="Wh"):
    """
    Automatically scale energy values to appropriate unit (Wh, kWh, MWh, GWh).
    
    Selects the unit such that the maximum value is in a readable range (typically < 10000).
    Prefers MWh over GWh for better readability (e.g., 100 MWh instead of 0.1 GWh).
    
    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "Wh")
    
    Returns:
        Tuple of:
        - scaled_values: List of values scaled to the selected unit
        - unit: The selected unit string
        - scale_factor: Numeric factor used for scaling (e.g., 1000 for kWh from Wh)
    """
    if not values:
        return [], base_unit, 1.0
    
    max_val = max(float(v) for v in values if v is not None)
    
    if max_val == 0:
        return values, base_unit, 1.0
    
    # Define unit conversion factors (all relative to Wh)
    units = [
        ("Wh", 1.0),
        ("kWh", 1_000.0),
        ("MWh", 1_000_000.0),
        ("GWh", 1_000_000_000.0),
    ]
    
    # Select unit where max value is >= 1.0
    # This ensures 100 MWh is shown instead of 0.1 GWh
    selected_unit = "Wh"
    selected_factor = 1.0
    
    for unit, factor in units:
        scaled_max = max_val / factor
        if scaled_max >= 1.0:
            selected_unit = unit
            selected_factor = factor
        else:
            # Previous unit was better
            break
    
    # Scale all values to the selected unit
    scaled_values = [v / selected_factor if v is not None else 0 for v in values]
    
    return scaled_values, selected_unit, selected_factor


def _resolve_decimal_places(scaled_vals, decimal_places=None):
    """Resolve decimal places for axis labels.

    If not explicitly set, show one decimal for small ranges (max < 10)
    so steps like 2.1/2.2 remain visible; otherwise use integer labels.
    """
    if decimal_places is not None:
        return decimal_places

    non_null_vals = [float(v) for v in scaled_vals if v is not None]
    if not non_null_vals:
        return 0

    max_abs = max(abs(v) for v in non_null_vals)
    return 1 if 0 < max_abs < 10 else 0


def get_energy_axis_config(values, base_unit="Wh", decimal_places=None):
    """
    Generate Plotly axis configuration for automatically scaled energy values.
    
    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "Wh")
        decimal_places: Number of decimal places for tick formatting.
                If None, uses adaptive precision.
    
    Returns:
        Dict with Plotly yaxis configuration including:
        - tickformat: Format string for readable numbers (no scientific notation)
        - title: Formatted axis title with unit
        - scale_factor: The scaling factor used
        - unit: The selected unit
    """
    scaled_vals, unit, scale_factor = autoscale_energy_values(values, base_unit)
    
    if not scaled_vals:
        return {
            "tickformat": ",.0f",
            "unit": base_unit,
            "scale_factor": 1.0,
            "title": f"{base_unit}"
        }
    
    decimal_places = _resolve_decimal_places(scaled_vals, decimal_places)

    # Use custom tickformat to avoid scientific notation and make numbers readable
    # ".0f"/".1f" = fixed format, "," = thousands separator
    tickformat = f",.{decimal_places}f"
    
    return {
        "tickformat": tickformat,
        "unit": unit,
        "scale_factor": scale_factor,
        "title": f"{unit}"
    }


def autoscale_power_values(values, base_unit="W"):
    """
    Automatically scale power values to appropriate unit (W, kW, MW, GW).

    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "W")

    Returns:
        Tuple of:
        - scaled_values: List of values scaled to the selected unit
        - unit: The selected unit string
        - scale_factor: Numeric factor used for scaling
    """
    if not values:
        return [], base_unit, 1.0

    max_val = max(float(v) for v in values if v is not None)

    if max_val == 0:
        return values, base_unit, 1.0

    units = [
        ("W", 1.0),
        ("kW", 1_000.0),
        ("MW", 1_000_000.0),
        ("GW", 1_000_000_000.0),
    ]

    selected_unit = "W"
    selected_factor = 1.0

    for unit, factor in units:
        scaled_max = max_val / factor
        if scaled_max >= 1.0:
            selected_unit = unit
            selected_factor = factor
        else:
            break

    scaled_values = [v / selected_factor if v is not None else 0 for v in values]

    return scaled_values, selected_unit, selected_factor


def get_power_axis_config(values, base_unit="W", decimal_places=None):
    """
    Generate Plotly axis configuration for automatically scaled power values.

    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "W")
        decimal_places: Number of decimal places for tick formatting.
                If None, uses adaptive precision.

    Returns:
        Dict with Plotly yaxis configuration including:
        - tickformat: Format string for readable numbers (no scientific notation)
        - scale_factor: The scaling factor used
        - unit: The selected unit
    """
    scaled_vals, unit, scale_factor = autoscale_power_values(values, base_unit)

    if not scaled_vals:
        return {
            "tickformat": ",.0f",
            "unit": base_unit,
            "scale_factor": 1.0,
            "title": f"{base_unit}"
        }

    decimal_places = _resolve_decimal_places(scaled_vals, decimal_places)
    tickformat = f",.{decimal_places}f"

    return {
        "tickformat": tickformat,
        "unit": unit,
        "scale_factor": scale_factor,
        "title": f"{unit}"
    }


def autoscale_currency_values(values, base_unit="€"):
    """
    Automatically scale currency values to appropriate unit (€, k€, M€, G€).

    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "€")

    Returns:
        Tuple of:
        - scaled_values: List of values scaled to the selected unit
        - unit: The selected unit string
        - scale_factor: Numeric factor used for scaling
    """
    if not values:
        return [], base_unit, 1.0

    max_val = max(float(v) for v in values if v is not None)

    if max_val == 0:
        return values, base_unit, 1.0

    units = [
        ("€", 1.0),
        ("k€", 1_000.0),
        ("Mio €", 1_000_000.0),
        ("Mrd €", 1_000_000_000.0),
    ]

    selected_unit = "€"
    selected_factor = 1.0

    for unit, factor in units:
        scaled_max = max_val / factor
        if scaled_max >= 1.0:
            selected_unit = unit
            selected_factor = factor
        else:
            break

    scaled_values = [v / selected_factor if v is not None else 0 for v in values]

    return scaled_values, selected_unit, selected_factor


def get_currency_axis_config(values, base_unit="€", decimal_places=None):
    """
    Generate Plotly axis configuration for automatically scaled currency values.

    Args:
        values: List of numeric values in the base unit
        base_unit: Original unit (default "€")
        decimal_places: Number of decimal places for tick formatting.
                        If None, uses adaptive precision.

    Returns:
        Dict with Plotly yaxis configuration including:
        - tickformat: Format string for readable numbers (no scientific notation)
        - scale_factor: The scaling factor used
        - unit: The selected unit
    """
    scaled_vals, unit, scale_factor = autoscale_currency_values(values, base_unit)

    if not scaled_vals:
        return {
            "tickformat": ",.0f",
            "unit": base_unit,
            "scale_factor": 1.0,
            "title": f"{base_unit}"
        }

    decimal_places = _resolve_decimal_places(scaled_vals, decimal_places)
    tickformat = f",.{decimal_places}f"

    return {
        "tickformat": tickformat,
        "unit": unit,
        "scale_factor": scale_factor,
        "title": f"{unit}"
    }