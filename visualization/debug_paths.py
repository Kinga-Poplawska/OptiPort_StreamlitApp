import sys
sys.path.insert(0, r"D:\Git Projects\OptiPort\visualization")
sys.stdout = open(r"D:\Git Projects\OptiPort\visualization\debug_out.txt", "w", encoding="utf-8")
sys.stderr = sys.stdout

from config.app_config import get_scenarios_root, get_processed_results_path
from core.instance_manager import UseCaseManager

uc = "example"
mgr = UseCaseManager()

print("=== discover_use_cases ===")
for u in mgr.discover_use_cases():
    print("  use_case:", u.name)

print("\n=== discover_scenarios ===")
scenarios = mgr.discover_scenarios(uc)
print("  scenarios:", scenarios)

for s in scenarios:
    mode = mgr.find_processed_mode(uc, s)
    print(f"\n  scenario={s}  mode={mode}")
    path = get_processed_results_path(uc, s, mode)
    print(f"  path={path}")
    print(f"  portfolio exists: {(path / 'portfolio_results.json').exists()}")


