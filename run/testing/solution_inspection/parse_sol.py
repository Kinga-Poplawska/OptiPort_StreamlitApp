# parse the file model_rmp_relax and display non-zero x variables
from pathlib import Path
import re

cur_dir = Path(__file__).resolve().parent

model_sol_dir = cur_dir / "model_rmp_relax.sol"
output_file = cur_dir / "nonzero_x_variables.txt"

# Parse variables and store them with sort keys
variables = []

with open(model_sol_dir, "r") as file:
    lines = file.readlines()
    
    for line in lines:
        if line.startswith("X"):
            parts = line.split()
            var_name = parts[0]
            value = float(parts[1])
            if value != 0:
                # Extract type (inst/rem/avail)
                type_match = re.match(r'X_(inst|rem|avail)_', var_name)
                var_type = type_match.group(1) if type_match else ""
                
                # Extract building (tuple with two numbers)
                # First number is building ID, second number is year
                building_match = re.search(r'\((\d+),(\d+)\)', var_name)
                if building_match:
                    building_id = int(building_match.group(1))
                    year = int(building_match.group(2))
                else:
                    building_id = 999
                    year = 999
                
                variables.append((building_id, var_type, year, var_name, value))

# Sort by building ID, type, year
# Define type order: inst, rem, avail
type_order = {'inst': 0, 'rem': 1, 'avail': 2}
variables.sort(key=lambda x: (x[0], type_order.get(x[1], 3), x[2]))

# Write sorted output
with open(output_file, "w") as out:
    for building_id, var_type, year, var_name, value in variables:
        output = f"{var_name}: {value}"
        print(output)
        out.write(output + "\n")
