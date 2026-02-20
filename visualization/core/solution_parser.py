"""
Parser for MILP solution files (.sol format)
"""
import re
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

from .data_models import OptimizationSolution, OptimizationVariable
from config.app_config import VARIABLE_CATEGORIES, TECHNOLOGY_CATEGORIES

logger = logging.getLogger(__name__)

class SolutionParser:
    """Parser for .sol files from MILP optimization"""
    
    def __init__(self):
        self.variable_pattern = re.compile(r'^([A-Z]+)_([a-z]+)_(\d+)_(\d+)_([a-zA-Z0-9_]+)\s+([-\d\.-e\+]+)$')
        self.objective_pattern = re.compile(r'# Objective value = ([\d\.-e\+]+)')
        self.comment_pattern = re.compile(r'^#')
        
    def parse_solution_file(self, file_path: Path) -> OptimizationSolution:
        """Parse a .sol file and return OptimizationSolution object"""
        if not file_path.exists():
            raise FileNotFoundError(f"Solution file not found: {file_path}")
            
        logger.info(f"Parsing solution file: {file_path}")
        
        objective_value = 0.0
        variables = {}
        solution_status = "UNKNOWN"
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
                
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if not line:
                    continue
                    
                # Parse objective value
                obj_match = self.objective_pattern.match(line)
                if obj_match:
                    objective_value = float(obj_match.group(1))
                    continue
                    
                # Skip comments
                if self.comment_pattern.match(line):
                    continue
                    
                # Parse variable
                var = self._parse_variable_line(line, line_num)
                if var:
                    variables[var.name] = var
                    
        except Exception as e:
            logger.error(f"Error parsing solution file {file_path}: {e}")
            raise
            
        # Determine solution status based on objective value and variables
        if variables and objective_value > 0:
            solution_status = "OPTIMAL"
        elif variables:
            solution_status = "FEASIBLE"
        else:
            solution_status = "INFEASIBLE"
            
        logger.info(f"Parsed {len(variables)} variables with objective value {objective_value}")
        
        sol = OptimizationSolution(
            objective_value=objective_value,
            variables=variables,
            solution_status=solution_status
        )

        return sol

    def _parse_variable_line(self, line: str, line_num: int) -> Optional[OptimizationVariable]:

        """Parse a single variable line from the solution file"""

        # Try the standard pattern first
        match = self.variable_pattern.match(line)
        if match:
            var_type = match.group(1)
            state = match.group(2)
            building_id = match.group(3)
            time_period = int(match.group(4))
            technology = match.group(5)
            value = float(match.group(6))

            var_name = f"{var_type}_{state}_{building_id}_{time_period}_{technology}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology),
                building_id=building_id,
                time_period=time_period,
                technology=technology,
                measure=state
            )

        # Enhanced pattern for R variables with complex technology names: R_building_timeperiod_technology_th_param1_param2
        r_complex_pattern = r"^(R)_(\d+)_(\d+)_(.+?)_th_(\d+)_(\d+)\s+([-\d\.-e\+]+)$"
        match = re.match(r_complex_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            technology = match.group(4)
            value = float(match.group(7))

            var_name = f"{var_type}_{building_id}_{time_period}_{technology}_th_{match.group(5)}_{match.group(6)}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology),
                building_id=building_id,
                time_period=time_period,
                technology=technology
            )

        # Enhanced pattern for C_dep variables with complex technology names: C_dep_building_timeperiod_technology
        c_dep_enhanced_pattern = r"^(C_dep)_(\d+)_(\d+)_(.+?)\s+([-\d\.-e\+]+)$"
        match = re.match(c_dep_enhanced_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            technology = match.group(4)
            value = float(match.group(5))

            var_name = f"{var_type}_{building_id}_{time_period}_{technology}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology),
                building_id=building_id,
                time_period=time_period,
                technology=technology
            )

        # Try pattern for complex variables with tuples (like Y variables)
        complex_pattern = r"^([A-Z]+)_(\d+)_(\d+)_\([^)]+\)_([a-zA-Z0-9_]+)\s+([-\d\.-e\+]+)$"
        match = re.match(complex_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            technology = match.group(4)
            value = float(match.group(5))

            # Extract the tuple part for the variable name
            tuple_start = line.find('(')
            tuple_end = line.find(')', tuple_start)
            tuple_part = line[tuple_start:tuple_end+1]

            var_name = f"{var_type}_{building_id}_{time_period}_{tuple_part}_{technology}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology),
                building_id=building_id,
                time_period=time_period,
                technology=technology
            )

        # Alternative R pattern for simpler format: R_building_timeperiod_technology_th_param1_param2
        r_simple_pattern = r"^(R)_(\d+)_(\d+)_([a-zA-Z]+)_th_(\d+)_(\d+)\s+([-\d\.-e\+]+)$"
        match = re.match(r_simple_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            technology = match.group(4)
            value = float(match.group(7))

            var_name = f"{var_type}_{building_id}_{time_period}_{technology}_th_{match.group(5)}_{match.group(6)}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology),
                building_id=building_id,
                time_period=time_period,
                technology=technology
            )

        # Pattern for delta variables: delta_building_timeperiod_param
        delta_pattern = r"^(delta)_(\d+)_(\d+)_(\d+)\s+([-\d\.-e\+]+)$"
        match = re.match(delta_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            param = match.group(4)
            value = float(match.group(5))

            var_name = f"{var_type}_{building_id}_{time_period}_{param}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                building_id=building_id,
                time_period=time_period
            )

        # Pattern for C_rent variables: C_rent_building_timeperiod
        c_rent_pattern = r"^(C_rent)_(\d+)_(-?\d+)\s+([-\d\.-e\+]+)$"
        match = re.match(c_rent_pattern, line)
        if match:
            var_type = match.group(1)
            building_id = match.group(2)
            time_period = int(match.group(3))
            value = float(match.group(4))

            var_name = f"{var_type}_{building_id}_{time_period}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                building_id=building_id,
                time_period=time_period
            )

        # Pattern for single letter variables: F value
        single_letter_pattern = r"^([A-Z])\s+([-\d\.-e\+]+)$"
        match = re.match(single_letter_pattern, line)
        if match:
            var_type = match.group(1)
            value = float(match.group(2))

            return OptimizationVariable(
                name=var_type,
                value=value,
                variable_type=var_type
            )

        # Financial pattern for Q, D, L variables
        financial_pattern = r'^([QDL])_(\d+)\s+([-\d\.-e\+]+)$'
        match = re.match(financial_pattern, line)
        if match:
            var_type = match.group(1)
            time_period = int(match.group(2))
            value = float(match.group(3))
            var_name = f"{var_type}_{time_period}"

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                time_period=time_period
            )

        # Generic pattern for most other variables: VAR_components_separated_by_underscore value
        generic_pattern = r'^([A-Za-z][a-zA-Z0-9_]*?)_(.+?)\s+([-\d\.-e\+]+)$'
        match = re.match(generic_pattern, line)
        if match:
            var_type = match.group(1)
            var_suffix = match.group(2)
            value = float(match.group(3))
            var_name = f"{var_type}_{var_suffix}"

            # Try to extract building_id and time_period from suffix
            suffix_parts = var_suffix.split('_')
            building_id = None
            time_period = None
            technology = None

            # Look for numeric parts that could be building_id and time_period
            for i, part in enumerate(suffix_parts):
                if part.isdigit() or (part.startswith('-') and part[1:].isdigit()):
                    if building_id is None:
                        building_id = part
                    elif time_period is None:
                        time_period = int(part)
                        break

            # Extract technology (usually the last non-numeric part before time indicators)
            tech_parts = [part for part in suffix_parts if not (part.isdigit() or (part.startswith('-') and part[1:].isdigit()))]
            if tech_parts:
                technology = '_'.join(tech_parts)

            return OptimizationVariable(
                name=var_name,
                value=value,
                variable_type=var_type,
                category=self._categorize_technology(technology) if technology else None,
                building_id=building_id,
                time_period=time_period,
                technology=technology
            )

        # If no pattern matches, log warning but don't fail
        logger.warning(f"Could not parse line {line_num}: {line}")
        return None

    def _categorize_technology(self, technology: str) -> Optional[str]:
        """Categorize a technology based on its name"""
        technology = technology.lower()
        
        for category, tech_list in TECHNOLOGY_CATEGORIES.items():
            for tech in tech_list:
                if tech.lower() in technology:
                    return category
                    
        return "other"
    
    def get_solution_summary(self, solution: OptimizationSolution) -> Dict[str, any]:
        """Generate a summary of the solution"""
        summary = {
            "objective_value": solution.objective_value,
            "solution_status": solution.solution_status,
            "total_variables": len(solution.variables),
            "variable_types": {},
            "installed_technologies": {},
            "buildings": set(),
            "time_periods": set()
        }
        
        # Count variables by type
        for var in solution.variables.values():
            var_type = var.variable_type
            if var_type not in summary["variable_types"]:
                summary["variable_types"][var_type] = 0
            summary["variable_types"][var_type] += 1
            
            # Collect buildings and time periods
            if var.building_id:
                summary["buildings"].add(var.building_id)
            if var.time_period is not None:
                summary["time_periods"].add(var.time_period)
        
        # Count installed technologies (X variables with value 1)
        x_vars = solution.get_variables_by_type("X")
        for var in x_vars.values():
            if var.value == 1 and var.technology:
                category = var.category or "other"
                if category not in summary["installed_technologies"]:
                    summary["installed_technologies"][category] = 0
                summary["installed_technologies"][category] += 1
        
        # Convert sets to sorted lists for JSON serialization
        summary["buildings"] = sorted(list(summary["buildings"]))
        summary["time_periods"] = sorted(list(summary["time_periods"]))
        
        return summary
