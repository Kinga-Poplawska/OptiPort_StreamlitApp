"""
Main testing orchestrator for comparing compact and Benders optimization approaches.

Usage:
    python run_tests.py [--num-instances N] [--skip-generation] [--verbosity LEVEL]
"""

import sys
from pathlib import Path
import argparse
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import run.testing.config as test_config
from run.testing.use_case_generator import TestUseCaseGenerator
from run.testing.optimization_runner import run_all_approaches
from run.testing.comparison import (
    compare_all_approaches,
    generate_multi_comparison_summary,
    print_multi_comparison_summary
)
from run.testing.export_results import export_all_results
from run.testing.logger import (
    get_logger, 
    set_verbosity, 
    VerbosityLevel, 
    setup_file_logging,
    OutputFormatter
)


def run_full_test_suite(num_instances: int = None, use_case_names: list = None):
    """Run the complete test suite."""
    logger = get_logger()
    fmt = OutputFormatter()
    
    start_time = datetime.now()
    num_inst = num_instances or test_config.NUM_TEST_INSTANCES

    predefined_cases = use_case_names or test_config.USE_CASE_NAMES
    
    logger.section("OPTIMIZATION COMPARISON TEST SUITE")
    # logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    # logger.info(f"Test instances: {num_inst}, Time limit: {test_config.TIME_LIMIT}s, MIP gap: {test_config.MIP_GAP}")

    if predefined_cases:
        # Use predefined use case names
        logger.section("STEP 1: USING PREDEFINED USE CASES")
        logger.info(f"Testing {len(predefined_cases)} predefined use cases")

        successful_use_cases = []
        for name in predefined_cases:
            # Create minimal metadata (actual data will be loaded during optimization)
            successful_use_cases.append({
                'use_case_name': name,
                'status': 'success',
                'num_buildings': 'N/A',  # Will be determined from actual data
                'num_time_periods': 'N/A'
            })

        num_inst = len(predefined_cases)
    else:
        # Generate new use cases
        logger.section("STEP 1: GENERATING SYNTHETIC USE CASES")
        num_inst = num_instances or test_config.NUM_TEST_INSTANCES

        generator = TestUseCaseGenerator()
        use_cases = generator.generate_test_instances(num_inst)

        # Filter successful generations
        successful_use_cases = [uc for uc in use_cases if uc['status'] == 'success']
        if not successful_use_cases:
            logger.error("No use cases were successfully generated. Aborting.")
            return None

        logger.info(f"Successfully generated {len(successful_use_cases)} use cases")

    logger.info(f"Time limit: {test_config.TIME_LIMIT}s, MIP gap: {test_config.MIP_GAP}")
    
    logger.section("STEP 2: RUNNING OPTIMIZATIONS")
    
    all_results = []
    
    for idx, use_case_metadata in enumerate(successful_use_cases, 1):
        use_case_name = use_case_metadata['use_case_name']
        
        logger.progress(idx, len(successful_use_cases), f"Testing {use_case_name}")
        logger.verbose(
            f"  Buildings: {use_case_metadata['num_buildings']}, "
            f"Time periods: {use_case_metadata['num_time_periods']}"
        )
        
        # try:
        results_dict = run_all_approaches(use_case_name)
        all_results.append((results_dict, use_case_metadata))

        # Log results for each approach
        status_str = ", ".join([f"{k}: {v.status_name}" for k, v in results_dict.items()])
        logger.verbose(f"  {status_str}")

        # except Exception as e:
        #     logger.error(f"Failed to run optimizations for {use_case_name}: {e}")
        #     if not test_config.CONTINUE_ON_ERROR:
        #         raise
    
    logger.section("STEP 3: COMPARING RESULTS")
    
    comparisons = []
    for results_dict, metadata in all_results:
        comparison = compare_all_approaches(results_dict, metadata)
        comparisons.append(comparison)
    
    # Generate summary
    summary = generate_multi_comparison_summary(comparisons)
    print_multi_comparison_summary(summary)

    logger.section("STEP 4: EXPORTING RESULTS")
    results_dir = Path(__file__).parent / test_config.RESULTS_DIR
    export_all_results(comparisons, summary, results_dir)
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.section("TEST SUITE COMPLETED")
    logger.info(f"Duration: {fmt.format_duration(duration)}")
    logger.info(f"Total tests: {len(comparisons)}")
    logger.info(f"All approaches match: {summary['all_match_count']}/{len(comparisons)}")

    if summary['discrepancy_count'] == 0:
        logger.info("ALL TESTS PASSED - No discrepancies found")
    else:
        logger.warning(f"{summary['discrepancy_count']} discrepancies found - see output files")
    
    return comparisons, summary


def main():
    """Main entry point for the test suite."""
    parser = argparse.ArgumentParser(
        description='Run optimization comparison tests between compact and Benders approaches'
    )
    parser.add_argument(
        '--num-instances', type=int, default=None,
        help=f'Number of test instances (default: {test_config.NUM_TEST_INSTANCES})'
    )

    parser.add_argument(
        '--verbosity', type=str, default=test_config.VERBOSITY,
        choices=['quiet', 'normal', 'verbose', 'debug'],
        help='Output verbosity level (default: normal)'
    )
    
    args = parser.parse_args()
    
    verbosity_map = {
        'quiet': VerbosityLevel.QUIET,
        'normal': VerbosityLevel.NORMAL,
        'verbose': VerbosityLevel.VERBOSE,
        'debug': VerbosityLevel.DEBUG
    }
    set_verbosity(verbosity_map[args.verbosity])
    
    results_dir = Path(__file__).parent / test_config.RESULTS_DIR
    results_dir.mkdir(parents=True, exist_ok=True)
    setup_file_logging(str(results_dir / test_config.LOG_FILE))
    
    logger = get_logger()
    
    # try:
    result = run_full_test_suite(
        num_instances=args.num_instances
    )
    
    if result is None:
        logger.error("Test suite failed")
        sys.exit(1)
    
    comparisons, summary = result
    
    if summary['discrepancy_count'] > 0:
        logger.warning(f"Completed with {summary['discrepancy_count']} discrepancies")
        sys.exit(1)
    else:
        logger.info("Test suite completed successfully")
        sys.exit(0)

    # except KeyboardInterrupt:
    #     logger.info("\nTest suite interrupted by user")
    #     sys.exit(130)
    
    # except Exception as e:
    #     logger.error(f"Test suite failed: {e}")
    #     sys.exit(1)


if __name__ == "__main__":
    main()
