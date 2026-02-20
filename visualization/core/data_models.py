"""
Data models for the optimization results and instances
"""
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

@dataclass
class OptimizationVariable:
    """Represents a single optimization variable from the solution"""
    name: str
    value: float
    variable_type: str  # X, E, P, Q, etc.
    category: Optional[str] = None
    building_id: Optional[str] = None
    time_period: Optional[int] = None
    technology: Optional[str] = None
    measure: Optional[str] = None

@dataclass 
class OptimizationSolution:
    """Complete optimization solution data"""
    objective_value: float
    variables: Dict[str, OptimizationVariable]
    solution_status: str
    solve_time: Optional[float] = None
    gap: Optional[float] = None
    
    def get_variables_by_type(self, var_type: str) -> Dict[str, OptimizationVariable]:
        """Get all variables of a specific type (X, E, P, Q, etc.)"""
        return {k: v for k, v in self.variables.items() if v.variable_type == var_type}
    
    def get_variables_by_category(self, category: str) -> Dict[str, OptimizationVariable]:
        """Get all variables of a specific category"""
        return {k: v for k, v in self.variables.items() if v.category == category}
    
    def get_installed_technologies(self) -> Dict[str, List[OptimizationVariable]]:
        """Get all installed technologies (X variables with value 1)"""
        x_vars = self.get_variables_by_type("X")
        installed = {}
        
        for var in x_vars.values():
            if var.value == 1 and var.technology:
                if var.technology not in installed:
                    installed[var.technology] = []
                installed[var.technology].append(var)
                
        return installed

@dataclass
class InstanceMetadata:
    """Metadata for an optimization instance"""
    name: str
    path: Path
    description: Optional[str] = None
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None
    num_buildings: Optional[int] = None
    num_time_periods: Optional[int] = None
    has_solution: bool = False
    solution_path: Optional[Path] = None
    config_files: Dict[str, Path] = None
    
    def __post_init__(self):
        if self.config_files is None:
            self.config_files = {}

@dataclass
class BuildingData:
    """Data for a single building in the optimization"""
    building_id: str
    properties: Dict[str, Any]
    technologies: Dict[str, OptimizationVariable]
    energy_flows: Dict[str, float]
    investments: Dict[int, List[str]]  # time_period -> list of technologies
    
@dataclass 
class TechnologyData:
    """Data for a specific technology across all buildings"""
    technology_name: str
    category: str
    total_capacity: float
    installations: Dict[str, Dict[int, float]]  # building_id -> {time_period: capacity}
    energy_production: Dict[str, float]  # building_id -> total_energy
    costs: Dict[str, float]  # building_id -> cost
