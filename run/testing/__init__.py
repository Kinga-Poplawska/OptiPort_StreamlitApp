"""
Testing module for comparing compact and Benders optimization approaches.

This package provides comprehensive testing infrastructure for generating
synthetic use cases and comparing the results of compact vs. Benders 
optimization methods.

Key Modules:
    config: Configuration parameters for testing
    use_case_generator: Generate synthetic test use cases
    optimization_runner: Run optimizations and capture results
    comparison: Compare results between approaches
    export_results: Export results to various formats
    run_tests: Main orchestrator script

Usage:
    From command line:
        cd run/testing
        python run_tests.py [--num-instances N]
    
    From Python:
        from run.testing.run_tests import run_full_test_suite
        comparisons, summary = run_full_test_suite(num_instances=10)
"""

__version__ = "1.0.0"
__author__ = "MIP4Klima Team"

# Expose main testing function
from .run_tests import run_full_test_suite

__all__ = ['run_full_test_suite']
