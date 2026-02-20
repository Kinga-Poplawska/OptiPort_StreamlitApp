"""
Data processing utilities for transforming and analyzing optimization data
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
import logging
from config.translations import get_technology_translation

logger = logging.getLogger(__name__)

def categorize_technology(technology_name: str) -> str:
    """Categorize a technology based on its name"""
    tech_lower = technology_name.lower()
    
    # Heating technologies
    if any(keyword in tech_lower for keyword in ['boi', 'boiler', 'hp', 'heat_pump', 'chp', 'eh', 'dh']):
        return 'heating'
    
    # Envelope technologies
    elif any(keyword in tech_lower for keyword in ['wall', 'roof', 'win', 'window', 'insulation']):
        return 'envelope'
    
    # Distribution technologies
    elif any(keyword in tech_lower for keyword in ['rad', 'radiator', 'ufh', 'underfloor']):
        return 'distribution'
    
    # Storage technologies
    elif any(keyword in tech_lower for keyword in ['tes', 'bat', 'battery', 'storage']):
        return 'storage'
    
    # Renewable technologies
    elif any(keyword in tech_lower for keyword in ['pv', 'solar', 'stc', 'photovoltaic']):
        return 'renewable'
    
    # Connection technologies
    elif 'connection' in tech_lower:
        return 'connection'
    
    else:
        return 'other'

def extract_variable_components(variable_name: str) -> Dict[str, Any]:
    """Extract components from a variable name"""
    import re
    
    # Standard pattern: TYPE_STATE_BUILDING_TIMEPERIOD_TECHNOLOGY
    pattern = r'^([A-Z]+)_([a-z]+)_(\d+)_(\d+)_([a-zA-Z0-9_]+)$'
    match = re.match(pattern, variable_name)
    
    if match:
        return {
            'variable_type': match.group(1),
            'state': match.group(2),
            'building_id': match.group(3),
            'time_period': int(match.group(4)),
            'technology': match.group(5),
            'category': categorize_technology(match.group(5))
        }
    
    # Alternative patterns for different variable formats
    alt_patterns = [
        r'^([A-Z]+)_([a-zA-Z0-9_]+)$',  # Simple TYPE_NAME format
        r'^([a-zA-Z_][a-zA-Z0-9_]*)$'   # Single name
    ]
    
    for pattern in alt_patterns:
        match = re.match(pattern, variable_name)
        if match:
            if len(match.groups()) == 2:
                return {
                    'variable_type': match.group(1),
                    'state': 'unknown',
                    'building_id': None,
                    'time_period': None,
                    'technology': match.group(2),
                    'category': categorize_technology(match.group(2))
                }
            else:
                var_type = variable_name.split('_')[0] if '_' in variable_name else 'OTHER'
                return {
                    'variable_type': var_type,
                    'state': 'unknown',
                    'building_id': None,
                    'time_period': None,
                    'technology': variable_name,
                    'category': 'other'
                }
    
    return {
        'variable_type': 'UNKNOWN',
        'state': 'unknown',
        'building_id': None,
        'time_period': None,
        'technology': variable_name,
        'category': 'other'
    }

def aggregate_by_category(data: List[Dict[str, Any]], 
                         value_key: str = 'value',
                         category_key: str = 'category') -> Dict[str, float]:
    """Aggregate data by category"""
    aggregated = {}
    
    for item in data:
        category = item.get(category_key, 'other')
        value = item.get(value_key, 0)
        
        if category in aggregated:
            aggregated[category] += value
        else:
            aggregated[category] = value
    
    return aggregated

def aggregate_by_time_period(data: List[Dict[str, Any]], 
                           value_key: str = 'value',
                           time_key: str = 'time_period') -> Dict[int, float]:
    """Aggregate data by time period"""
    aggregated = {}
    
    for item in data:
        time_period = item.get(time_key)
        value = item.get(value_key, 0)
        
        if time_period is not None:
            if time_period in aggregated:
                aggregated[time_period] += value
            else:
                aggregated[time_period] = value
    
    return aggregated

def create_technology_matrix(variables: Dict[str, Any]) -> pd.DataFrame:
    """Create a matrix of technologies by buildings and time periods"""
    
    data = []
    
    for var_name, var in variables.items():
        if hasattr(var, 'building_id') and hasattr(var, 'time_period') and hasattr(var, 'technology'):
            if var.building_id and var.time_period is not None and var.technology:
                data.append({
                    'variable': var_name,
                    'building': var.building_id,
                    'time_period': var.time_period,
                    'technology': var.technology,
                    'category': getattr(var, 'category', 'other'),
                    'value': getattr(var, 'value', 0)
                })
    
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    return df

def calculate_technology_statistics(variables: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics for technologies"""
    
    stats = {
        'total_technologies': 0,
        'installed_technologies': 0,
        'categories': {},
        'time_periods': set(),
        'buildings': set(),
        'capacity_by_technology': {},
        'installations_by_period': {}
    }
    
    for var in variables.values():
        if hasattr(var, 'variable_type') and var.variable_type == 'X':
            stats['total_technologies'] += 1
            
            if hasattr(var, 'value') and var.value == 1:
                stats['installed_technologies'] += 1
                
                # Category tracking
                category = getattr(var, 'category', 'other')
                if category not in stats['categories']:
                    stats['categories'][category] = 0
                stats['categories'][category] += 1
                
                # Time period tracking
                if hasattr(var, 'time_period') and var.time_period is not None:
                    stats['time_periods'].add(var.time_period)
                    
                    if var.time_period not in stats['installations_by_period']:
                        stats['installations_by_period'][var.time_period] = 0
                    stats['installations_by_period'][var.time_period] += 1
                
                # Building tracking
                if hasattr(var, 'building_id') and var.building_id:
                    stats['buildings'].add(var.building_id)
        
        # Capacity tracking for E variables
        elif hasattr(var, 'variable_type') and var.variable_type == 'E':
            if hasattr(var, 'value') and var.value > 0:
                technology = getattr(var, 'technology', 'unknown')
                if technology not in stats['capacity_by_technology']:
                    stats['capacity_by_technology'][technology] = 0
                stats['capacity_by_technology'][technology] += var.value
    
    # Convert sets to lists for JSON serialization
    stats['time_periods'] = sorted(list(stats['time_periods']))
    stats['buildings'] = sorted(list(stats['buildings']))
    
    return stats

def filter_variables_by_criteria(variables: Dict[str, Any], 
                                criteria: Dict[str, Any]) -> Dict[str, Any]:
    """Filter variables based on specified criteria"""
    
    filtered = {}
    
    for var_name, var in variables.items():
        include = True
        
        # Check each criterion
        for key, value in criteria.items():
            var_value = getattr(var, key, None)
            
            if isinstance(value, list):
                if var_value not in value:
                    include = False
                    break
            elif var_value != value:
                include = False
                break
        
        if include:
            filtered[var_name] = var
    
    return filtered

def create_summary_table(variables: Dict[str, Any]) -> pd.DataFrame:
    """Create a summary table of variables"""
    
    data = []
    
    for var_name, var in variables.items():
        row = {
            'Variable': var_name,
            'Type': getattr(var, 'variable_type', 'N/A'),
            'Value': getattr(var, 'value', 0),
            'Building': getattr(var, 'building_id', 'N/A'),
            'Time Period': getattr(var, 'time_period', 'N/A'),
            'Technology': getattr(var, 'technology', 'N/A'),
            'Category': getattr(var, 'category', 'N/A'),
            'State': getattr(var, 'measure', 'N/A')
        }
        data.append(row)
    
    return pd.DataFrame(data)

def format_currency(value: float, currency: str = "€") -> str:
    """Format currency values with appropriate scaling"""
    abs_value = abs(value)
    
    if abs_value >= 1e9:
        return f"{currency}{value/1e9:.1f}B"
    elif abs_value >= 1e6:
        return f"{currency}{value/1e6:.1f}M"
    elif abs_value >= 1e3:
        return f"{currency}{value/1e3:.0f}K"
    else:
        return f"{currency}{value:.0f}"

def format_energy(value: float, unit: str = "kWh") -> str:
    """Format energy values with appropriate scaling"""
    abs_value = abs(value)
    
    if abs_value >= 1e9:
        return f"{value/1e9:.1f} G{unit}"
    elif abs_value >= 1e6:
        return f"{value/1e6:.1f} M{unit}"
    elif abs_value >= 1e3:
        return f"{value/1e3:.0f} k{unit}"
    else:
        return f"{value:.0f} {unit}"
