"""
Solution Comparison Script
Compares variable values between two CPLEX solution files based on specified variable prefixes.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple
import re


# Define variable prefixes to compare
VARIABLE_PREFIXES = [
    "E_",
    "P_out_(0,0)_(0"
]


def parse_solution_file(filepath: str) -> Tuple[float, Dict[str, float]]:
    """
    Parse a CPLEX solution file and extract objective value and variables.
    
    Args:
        filepath: Path to the solution file
        
    Returns:
        Tuple of (objective_value, variables_dict)
    """
    variables = {}
    objective_value = None
    
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Extract objective value
            if line.startswith('# Objective value ='):
                objective_value = float(line.split('=')[1].strip())
                continue
                
            # Skip other comment lines
            if line.startswith('#'):
                continue
            
            # Parse variable lines: "variable_name value"
            parts = line.split()
            if len(parts) == 2:
                var_name, value = parts
                try:
                    variables[var_name] = float(value)
                except ValueError:
                    continue
    
    return objective_value, variables


def filter_variables_by_prefix(variables: Dict[str, float], prefixes: List[str]) -> Dict[str, float]:
    """
    Filter variables that start with any of the specified prefixes.
    
    Args:
        variables: Dictionary of all variables
        prefixes: List of variable prefixes to filter by
        
    Returns:
        Filtered dictionary of variables
    """
    filtered = {}
    for var_name, value in variables.items():
        for prefix in prefixes:
            if var_name.startswith(prefix):
                filtered[var_name] = value
                break
    return filtered


def compare_solutions(sol1: Dict[str, float], sol2: Dict[str, float], 
                     tolerance: float = 1e-6) -> Dict[str, Dict]:
    """
    Compare two solution dictionaries and identify differences.
    
    Args:
        sol1: First solution dictionary
        sol2: Second solution dictionary
        tolerance: Tolerance for floating point comparison
        
    Returns:
        Dictionary with comparison results
    """
    comparison = {
        'matching': {},
        'different': {},
        'only_in_sol1': {},
        'only_in_sol2': {}
    }
    
    all_vars = set(sol1.keys()) | set(sol2.keys())
    
    for var in sorted(all_vars):
        val1 = sol1.get(var)
        val2 = sol2.get(var)
        
        if val1 is None:
            comparison['only_in_sol2'][var] = val2
        elif val2 is None:
            comparison['only_in_sol1'][var] = val1
        elif abs(val1 - val2) <= tolerance:
            comparison['matching'][var] = {'sol1': val1, 'sol2': val2}
        else:
            comparison['different'][var] = {
                'sol1': val1, 
                'sol2': val2, 
                'diff': val1 - val2,
                'rel_diff': abs(val1 - val2) / max(abs(val1), abs(val2), 1e-10)
            }
    
    return comparison


def print_comparison_summary(comparison: Dict, obj1: float, obj2: float):
    """Print a summary of the comparison results."""
    
    print("=" * 80)
    print("SOLUTION COMPARISON SUMMARY")
    print("=" * 80)
    print()
    
    print(f"Objective Values:")
    print(f"  Benders: {obj1:,.2f}")
    print(f"  Compact: {obj2:,.2f}")
    print(f"  Difference: {obj1 - obj2:,.2f}")
    print(f"  Relative Difference: {abs(obj1 - obj2) / max(abs(obj1), abs(obj2)) * 100:.4f}%")
    print()
    
    print(f"Variable Comparison:")
    print(f"  Matching variables: {len(comparison['matching'])}")
    print(f"  Different variables: {len(comparison['different'])}")
    print(f"  Only in Benders: {len(comparison['only_in_sol1'])}")
    print(f"  Only in Compact: {len(comparison['only_in_sol2'])}")
    print()
    
    if comparison['different']:
        print("=" * 80)
        print("DIFFERENT VARIABLES")
        print("=" * 80)
        print(f"{'Variable':<50} {'Benders':>15} {'Compact':>15} {'Diff':>15}")
        print("-" * 80)
        
        # Sort by absolute difference
        sorted_diff = sorted(comparison['different'].items(), 
                            key=lambda x: abs(x[1]['diff']), 
                            reverse=True)
        
        for var, vals in sorted_diff:  # Show all differences
            print(f"{var:<50} {vals['sol1']:>15.6f} {vals['sol2']:>15.6f} {vals['diff']:>15.6f}")
        print()
    
    if comparison['only_in_sol1']:
        print("=" * 80)
        print(f"VARIABLES ONLY IN BENDERS (showing first 10 of {len(comparison['only_in_sol1'])})")
        print("=" * 80)
        for var in list(comparison['only_in_sol1'].keys())[:10]:
            print(f"  {var}: {comparison['only_in_sol1'][var]}")
        print()
    
    if comparison['only_in_sol2']:
        print("=" * 80)
        print(f"VARIABLES ONLY IN COMPACT (showing first 10 of {len(comparison['only_in_sol2'])})")
        print("=" * 80)
        for var in list(comparison['only_in_sol2'].keys())[:10]:
            print(f"  {var}: {comparison['only_in_sol2'][var]}")
        print()


def main():
    """Main execution function."""
    
    # Get script directory
    script_dir = Path(__file__).parent
    
    # Define solution file paths
    benders_file = script_dir / "benders.sol"
    compact_file = script_dir / "compact.sol"
    
    # Check files exist
    if not benders_file.exists():
        print(f"Error: {benders_file} not found")
        return
    if not compact_file.exists():
        print(f"Error: {compact_file} not found")
        return
    
    print("Reading solution files...")
    
    # Parse solution files
    obj_benders, vars_benders = parse_solution_file(benders_file)
    obj_compact, vars_compact = parse_solution_file(compact_file)
    
    print(f"  Benders solution: {len(vars_benders)} variables")
    print(f"  Compact solution: {len(vars_compact)} variables")
    print()
    
    # Filter by prefixes
    print(f"Filtering variables by prefixes: {', '.join(VARIABLE_PREFIXES)}")
    filtered_benders = filter_variables_by_prefix(vars_benders, VARIABLE_PREFIXES)
    filtered_compact = filter_variables_by_prefix(vars_compact, VARIABLE_PREFIXES)
    
    print(f"  Filtered Benders: {len(filtered_benders)} variables")
    print(f"  Filtered Compact: {len(filtered_compact)} variables")
    print()
    
    # Compare solutions
    print("Comparing solutions...")
    comparison = compare_solutions(filtered_benders, filtered_compact)
    
    # Print summary
    print_comparison_summary(comparison, obj_benders, obj_compact)


if __name__ == "__main__":
    main()
