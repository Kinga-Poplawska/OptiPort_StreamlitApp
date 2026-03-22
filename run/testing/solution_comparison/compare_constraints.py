from gurobipy import *
from pathlib import Path


cur_dir = Path(__file__).resolve().parent

model_old_dir = cur_dir / "model_rmp_old.lp"
model_new_dir = cur_dir / "model_rmp_new.lp"

model_old = read(str(model_old_dir))
model_new = read(str(model_new_dir))

constrs_old = {c.ConstrName for c in model_old.getConstrs()}
constrs_new = {c.ConstrName for c in model_new.getConstrs()}

constrs_only_in_old = constrs_old - constrs_new
constrs_only_in_new = constrs_new - constrs_old

print("Constraints only in old model:")
for c in constrs_only_in_old:
    print(c)

print("\nConstraints only in new model:")
for c in constrs_only_in_new:
    print(c)