"""
Testing configuration for synthetic use case generation and optimization comparison.

This module defines all parameters for generating test instances and running
both compact and Benders optimization approaches.
"""

# ============================================================================
# TEST INSTANCE GENERATION
# ============================================================================

# Testing behavior
USE_CASE_NAMES = ["test"]  # List of existing use case names to test, e.g., ['use_case_001', 'use_case_002']
                      # If empty, new use cases will be generated

# modes to compare
benders_variants: list[str] = [ "standard", "standard_alternative", "standard_alternative_peak_vars", "standard_peak_vars",
                                "no_y", "no_y_alternative", "no_y_alternative_peak_vars", "no_y_peak_vars"]  # Variants to compare
compare_compact: bool = False  # Whether to also compare with compact


# Number of synthetic test instances to generate
NUM_TEST_INSTANCES = 1

# Range of buildings per instance
NUM_BUILDINGS_RANGE = {
    "min": 3,
    "max": 3
}

# Range of time periods (2-5 as per generator constraints)
NUM_TIME_PERIODS_RANGE = {
    "min": 5,
    "max": 5
}


# Range of apartments/flats per building (overrides generator defaults)
# Note: SFH and TH are always 1 flat (single family homes)
# MFH default: 2-20 flats, AB default: 8-64 flats
NUM_FLATS_RANGE = {
    "MFH": {"min": 3, "max": 6},   # Multi-family house: 4-12 apartments
    "AB": {"min": 5, "max": 20}    # Apartment block: 16-32 apartments
}

# Base seed for reproducibility (each instance gets seed + instance_id)
BASE_SEED = 1000

# Naming pattern for test use cases
USE_CASE_NAME_PREFIX = "test_synth"

# ============================================================================
# OPTIMIZATION SETTINGS (Override config/values/algorithm.py)
# ============================================================================

# IMPORTANT: For testing, we need exact termination to compare results
# These settings will override the algorithm settings in config/values/algorithm.py

# Time limit for each optimization run (seconds)
# None = no limit (we want to solve to optimality for comparison)
TIME_LIMIT = None

# MIP gap tolerance
# 0.0 = solve to proven optimality (required for accurate comparison)
MIP_GAP = 0.0

# Number of threads for Gurobi
THREADS = 6

# Whether to save LP files (for debugging)
SAVE_LP_FILES = False

# Whether to save ILP files for infeasible models
SAVE_ILP_FILES = True

# ============================================================================
# RESULT COMPARISON SETTINGS
# ============================================================================

# Tolerance for comparing objective values
OBJECTIVE_TOLERANCE = 1e-4

# Whether to overwrite existing building/portfolio data
OVERWRITE_BUILDING_DATA = False
OVERWRITE_PORTFOLIO_DATA = False

# ============================================================================
# OUTPUT SETTINGS
# ============================================================================

# Results directory (relative to run/testing/)
RESULTS_DIR = "results"

# Output file names
COMPARISON_CSV = "optimization_comparison.csv"
COMPARISON_JSON = "optimization_comparison.json"
SUMMARY_TXT = "summary_statistics.txt"
LOG_FILE = "test_execution.log"

# ============================================================================
# TESTING BEHAVIOR
# ============================================================================

# Continue testing even if one instance fails
CONTINUE_ON_ERROR = True

# Verbosity level: 'quiet', 'normal', 'verbose', 'debug'
VERBOSITY = 'normal'

# Clean up generated use cases after testing
CLEANUP_USE_CASES = False  # Set to True to remove test use cases after completion
