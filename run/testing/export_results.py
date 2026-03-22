"""
Results export utilities for saving comparison data and generating reports.
"""

import sys
from pathlib import Path
import json
import csv
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import run.testing.config as test_config
from run.testing.logger import get_logger


def export_to_csv(comparisons: List, output_path: Path):
    """Export comparison results to CSV file with support for multiple benders variants."""
    logger = get_logger()

    if not comparisons:
        logger.warning("No comparisons to export")
        return

    # Detect if compact is present and get all variants
    first_comp = comparisons[0].to_dict()
    has_compact = 'compact' in first_comp.get('approach_labels', [])
    benders_variants = [label for label in first_comp.get('approach_labels', []) if label != 'compact']

    # Define CSV columns based on what's available
    fieldnames = ['use_case_name', 'num_buildings', 'num_time_periods']

    if has_compact:
        fieldnames.extend(['compact_status', 'compact_objective', 'compact_runtime', 'compact_error'])

    # Add columns for each benders variant
    for variant in benders_variants:
        fieldnames.extend([
            f'{variant}_status',
            f'{variant}_objective',
            f'{variant}_runtime',
            f'{variant}_error',
        ])

        # Only add comparison columns if compact is present
        if has_compact:
            fieldnames.extend([
                f'{variant}_objective_diff',
                f'{variant}_objective_rel_error',
                f'{variant}_objective_match',
                f'{variant}_runtime_ratio',
                f'{variant}_discrepancy',
            ])

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for comparison in comparisons:
            comp_dict = comparison.to_dict()

            row = {
                'use_case_name': comp_dict['use_case_name'],
                'num_buildings': comp_dict.get('num_buildings'),
                'num_time_periods': comp_dict.get('num_time_periods'),
            }

            if 'approach_labels' in comp_dict:
                # Get compact index if it exists
                compact_idx = None
                if has_compact:
                    try:
                        compact_idx = comp_dict['approach_labels'].index('compact')
                        row['compact_status'] = comp_dict['statuses']['compact']
                        row['compact_objective'] = comp_dict['objectives']['compact']
                        row['compact_runtime'] = comp_dict['runtimes']['compact']
                        row['compact_error'] = comp_dict['errors']['compact']
                    except (ValueError, IndexError):
                        pass

                # Add data for each benders variant - use actual index from approach_labels
                for idx, label in enumerate(comp_dict['approach_labels']):
                    if label == 'compact':
                        continue

                    row[f'{label}_status'] = comp_dict['statuses'][label]
                    row[f'{label}_objective'] = comp_dict['objectives'][label]
                    row[f'{label}_runtime'] = comp_dict['runtimes'][label]
                    row[f'{label}_error'] = comp_dict['errors'][label]

                    # Only calculate comparisons if compact is present
                    if has_compact and compact_idx is not None:
                        # Calculate objective differences
                        if comp_dict['objectives']['compact'] is not None and comp_dict['objectives'][label] is not None:
                            obj_diff = abs(comp_dict['objectives']['compact'] - comp_dict['objectives'][label])
                            row[f'{label}_objective_diff'] = obj_diff

                            if comp_dict['objectives']['compact'] != 0:
                                rel_error = (obj_diff / abs(comp_dict['objectives']['compact'])) * 100
                                row[f'{label}_objective_rel_error'] = rel_error
                                row[f'{label}_objective_match'] = obj_diff <= test_config.OBJECTIVE_TOLERANCE
                            else:
                                row[f'{label}_objective_rel_error'] = None
                                row[f'{label}_objective_match'] = None
                        else:
                            row[f'{label}_objective_diff'] = None
                            row[f'{label}_objective_rel_error'] = None
                            row[f'{label}_objective_match'] = None

                        # Calculate runtime ratio
                        if comp_dict['runtimes']['compact'] is not None and comp_dict['runtimes'][label] is not None:
                            if comp_dict['runtimes']['compact'] > 0:
                                row[f'{label}_runtime_ratio'] = comp_dict['runtimes'][label] / comp_dict['runtimes']['compact']
                            else:
                                row[f'{label}_runtime_ratio'] = None
                        else:
                            row[f'{label}_runtime_ratio'] = None

                        # Get discrepancy
                        if label != "compact":
                            row[f'{label}_discrepancy'] = comp_dict['objectives'][label]/comp_dict['objectives']['compact']
            writer.writerow(row)

    logger.debug(f"Exported CSV to: {output_path}")


def export_to_json(comparisons: List, summary: Dict, output_path: Path):
    """Export comparison results and summary to JSON file."""
    data = {
        'metadata': {
            'export_timestamp': datetime.now().isoformat(),
            'num_test_instances': test_config.NUM_TEST_INSTANCES,
            'base_seed': test_config.BASE_SEED,
            'time_limit': test_config.TIME_LIMIT,
            'mip_gap': test_config.MIP_GAP,
            'objective_tolerance': test_config.OBJECTIVE_TOLERANCE,
        },
        'summary': summary,
        'comparisons': [c.to_dict() for c in comparisons]
    }
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    get_logger().debug(f"Exported JSON to: {output_path}")


def export_summary_to_txt(summary: Dict, comparisons: List, output_path: Path):
    """Export detailed summary to text file with multi-variant support."""
    with open(output_path, 'w') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("OPTIMIZATION COMPARISON TEST SUMMARY\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Test instances: {test_config.NUM_TEST_INSTANCES}\n")
        f.write(f"Base seed: {test_config.BASE_SEED}\n")
        f.write(f"Time limit: {test_config.TIME_LIMIT} seconds\n")
        f.write(f"MIP gap: {test_config.MIP_GAP}\n")
        f.write(f"Objective tolerance: {test_config.OBJECTIVE_TOLERANCE}\n")
        f.write("\n")

        # Detect if compact is present
        has_compact = False
        if comparisons:
            first_comp = comparisons[0].to_dict()
            has_compact = 'compact' in first_comp.get('approach_labels', [])

        # Overall statistics per variant
        f.write("=" * 80 + "\n")
        f.write("OVERALL STATISTICS BY VARIANT\n")
        f.write("=" * 80 + "\n")

        if comparisons:
            first_comp = comparisons[0].to_dict()
            if 'approach_labels' in first_comp:
                variants = [label for label in first_comp['approach_labels'] if label != 'compact']

                for variant in variants:
                    f.write(f"\n{variant.upper()}:\n")
                    f.write(f"{'-' * 40}\n")

                    # Calculate statistics for this variant
                    variant_stats = calculate_variant_statistics(comparisons, variant, has_compact)

                    f.write(f"Total comparisons: {variant_stats['total']}\n")

                    if has_compact:
                        f.write(f"Status matches: {variant_stats['status_matches']}/{variant_stats['total']} "
                                f"({variant_stats['status_match_rate']:.1f}%)\n")
                        f.write(f"Both optimal: {variant_stats['both_optimal']}/{variant_stats['total']} "
                                f"({variant_stats['both_optimal_rate']:.1f}%)\n")

                        if variant_stats['both_optimal'] > 0:
                            f.write(
                                f"Objective matches: {variant_stats['objective_matches']}/{variant_stats['both_optimal']} "
                                f"({variant_stats['objective_match_rate']:.1f}%)\n")

                        f.write(f"Discrepancies: {variant_stats['discrepancies']}/{variant_stats['total']} "
                                f"({variant_stats['discrepancy_rate']:.1f}%)\n")

                        if variant_stats['avg_runtime'] is not None:
                            f.write(f"Average runtime: {variant_stats['avg_runtime']:.2f}s "
                                    f"(ratio: {variant_stats['avg_runtime_ratio']:.2f}x)\n")
                    else:
                        # Just show runtime stats without comparison
                        if variant_stats['avg_runtime'] is not None:
                            f.write(f"Average runtime: {variant_stats['avg_runtime']:.2f}s\n")

        # Detailed results for each use case
        f.write("\n" + "=" * 80 + "\n")
        f.write("DETAILED RESULTS BY USE CASE\n")
        f.write("=" * 80 + "\n\n")

        for comparison in comparisons:
            comp_dict = comparison.to_dict()
            f.write(f"Use Case: {comp_dict['use_case_name']}\n")
            f.write(f"{'-' * 80}\n")

            if comp_dict.get('num_buildings') is not None:
                f.write(f"Buildings: {comp_dict['num_buildings']}, "
                        f"Time Periods: {comp_dict['num_time_periods']}\n\n")

            if 'approach_labels' in comp_dict:
                compact_idx = None
                if has_compact:
                    try:
                        compact_idx = comp_dict['approach_labels'].index('compact')
                        # Compact results
                        f.write(f"COMPACT:\n")
                        f.write(f"  Status:    {comp_dict['statuses']['compact']}\n")
                        if comp_dict['objectives']['compact'] is not None:
                            f.write(f"  Objective: {comp_dict['objectives']['compact']:.10f}\n")
                        if comp_dict['runtimes']['compact'] is not None:
                            f.write(f"  Runtime:   {comp_dict['runtimes']['compact']:.2f}s\n")
                        if comp_dict['errors']['compact']:
                            f.write(f"  Error:     {comp_dict['errors']['compact']}\n")
                        f.write("\n")
                    except (ValueError, IndexError):
                        compact_idx = None

                # Each benders variant
                for i, label in enumerate(comp_dict['approach_labels']):
                    if label == 'compact':
                        continue

                    f.write(f"{label.upper()}:\n")
                    f.write(f"  Status:    {comp_dict['statuses'][label]}")
                    if has_compact and compact_idx is not None and comp_dict['statuses']['compact'] == \
                            comp_dict['statuses'][label]:
                        f.write("OK")
                    f.write("\n")

                    if comp_dict['objectives'][label] is not None:
                        f.write(f"  Objective: {comp_dict['objectives'][label]:.10f}\n")

                        if has_compact and compact_idx is not None and comp_dict['objectives']['compact'] is not None:
                            diff = abs(comp_dict['objectives']['compact'] - comp_dict['objectives'][label])
                            f.write(f"  Difference: {diff:.2e}")
                            if diff <= test_config.OBJECTIVE_TOLERANCE:
                                f.write("Ok")
                            f.write("\n")

                    if comp_dict['runtimes'][label] is not None:
                        f.write(f"  Runtime:   {comp_dict['runtimes'][label]:.2f}s")
                        if has_compact and compact_idx is not None and comp_dict['runtimes'][
                            'compact'] is not None and comp_dict['runtimes']['compact'] > 0:
                            ratio = comp_dict['runtimes'][label] / comp_dict['runtimes']['compact']
                            f.write(f" ({ratio:.2f}x)")
                        f.write("\n")

                    if comp_dict['errors'][label]:
                        f.write(f"  Error:     {comp_dict['errors'][label]}\n")

                    if has_compact:
                        discrepancy = comp_dict.get('discrepancies', {}).get(label, "None")
                        if discrepancy != "None":
                            f.write(f"Discrepancy: {discrepancy}\n")

                    f.write("\n")

            f.write("\n")

    get_logger().debug(f"Exported summary to: {output_path}")


def calculate_variant_statistics(comparisons: List, variant: str, has_compact: bool = True) -> Dict:
    """Calculate statistics for a specific benders variant."""
    stats = {
        'total': len(comparisons),
        'status_matches': 0,
        'both_optimal': 0,
        'objective_matches': 0,
        'discrepancies': 0,
        'total_runtime': 0,
        'total_runtime_ratio': 0,
        'count_runtime': 0,
    }

    for comp in comparisons:
        comp_dict = comp.to_dict()
        if 'approach_labels' not in comp_dict:
            continue

        try:
            variant_idx = comp_dict['approach_labels'].index(variant)
        except ValueError:
            continue

        # Only calculate comparison stats if compact is present
        if has_compact:
            try:
                compact_idx = comp_dict['approach_labels'].index('compact')

                # Status match
                if comp_dict['statuses']['compact'] == comp_dict['statuses'][variant]:
                    stats['status_matches'] += 1

                # Both optimal
                if comp_dict['statuses']['compact'] == 'Optimal' and comp_dict['statuses'][variant] == 'Optimal':
                    stats['both_optimal'] += 1

                    # Objective match
                    if comp_dict['objectives']['compact'] is not None and comp_dict['objectives'][
                        variant] is not None:
                        diff = abs(comp_dict['objectives']['compact'] - comp_dict['objectives'][variant])
                        if diff <= test_config.OBJECTIVE_TOLERANCE:
                            stats['objective_matches'] += 1

                # Discrepancies
                discrepancy = comp_dict.get('discrepancies', {}).get(variant, "None")
                if discrepancy != "None":
                    stats['discrepancies'] += 1

                # Runtime ratio
                if comp_dict['runtimes']['compact'] is not None and comp_dict['runtimes']['compact'] > 0 and \
                        comp_dict['runtimes'][variant] is not None:
                    ratio = comp_dict['runtimes'][variant] / comp_dict['runtimes']['compact']
                    stats['total_runtime_ratio'] += ratio

            except (ValueError, IndexError):
                pass

        # Runtime statistics (always calculated)
        if comp_dict['runtimes'][variant] is not None:
            stats['total_runtime'] += comp_dict['runtimes'][variant]
            stats['count_runtime'] += 1

    # Calculate rates and averages
    if has_compact:
        stats['status_match_rate'] = (stats['status_matches'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['both_optimal_rate'] = (stats['both_optimal'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['objective_match_rate'] = (stats['objective_matches'] / stats['both_optimal'] * 100) if stats[
                                                                                                          'both_optimal'] > 0 else 0
        stats['discrepancy_rate'] = (stats['discrepancies'] / stats['total'] * 100) if stats['total'] > 0 else 0
        stats['avg_runtime_ratio'] = (stats['total_runtime_ratio'] / stats['count_runtime']) if stats[
                                                                                                    'count_runtime'] > 0 else None

    stats['avg_runtime'] = (stats['total_runtime'] / stats['count_runtime']) if stats['count_runtime'] > 0 else None

    return stats


def export_all_results(comparisons: List, summary: Dict, results_dir: Path):
    """Export results to all formats."""
    logger = get_logger()
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate timestamped filenames
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export to CSV
    csv_path = results_dir / f"comparison_{timestamp}.csv"
    export_to_csv(comparisons, csv_path)
    
    # Also save with standard name (for easy access)
    csv_path_standard = results_dir / test_config.COMPARISON_CSV
    export_to_csv(comparisons, csv_path_standard)
    
    # Export to JSON
    json_path = results_dir / f"comparison_{timestamp}.json"
    export_to_json(comparisons, summary, json_path)
    
    # Also save with standard name
    json_path_standard = results_dir / test_config.COMPARISON_JSON
    export_to_json(comparisons, summary, json_path_standard)
    
    # Export summary to TXT
    txt_path = results_dir / f"summary_{timestamp}.txt"
    export_summary_to_txt(summary, comparisons, txt_path)
    
    # Also save with standard name
    txt_path_standard = results_dir / test_config.SUMMARY_TXT
    export_summary_to_txt(summary, comparisons, txt_path_standard)
    
    logger.info(f"Results exported to: {results_dir}")
    logger.verbose(f"  CSV:  {csv_path_standard.name}")
    logger.verbose(f"  JSON: {json_path_standard.name}")
    logger.verbose(f"  TXT:  {txt_path_standard.name}")
