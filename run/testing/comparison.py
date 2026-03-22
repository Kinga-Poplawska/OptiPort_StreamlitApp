"""
Comparison utilities for analyzing compact vs. Benders optimization results.
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
import run.testing.config as test_config
from run.testing.logger import OutputFormatter


@dataclass
class ComparisonResult:
    """Store comparison between compact and Benders optimization results."""
    use_case_name: str
    num_buildings: int = None
    num_time_periods: int = None
    compact_status: str = None
    benders_status: str = None
    status_match: bool = None
    compact_objective: float = None
    benders_objective: float = None
    objective_match: bool = None
    objective_difference: float = None
    objective_relative_error: float = None
    compact_runtime: float = None
    benders_runtime: float = None
    runtime_ratio: float = None
    compact_error: str = None
    benders_error: str = None
    discrepancy: str = None
    
    def has_discrepancy(self) -> bool:
        """Check if there's any discrepancy between approaches."""
        return not (self.status_match and (self.objective_match if self.objective_match is not None else True))
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'use_case_name': self.use_case_name,
            'num_buildings': self.num_buildings,
            'num_time_periods': self.num_time_periods,
            'compact_status': self.compact_status,
            'benders_status': self.benders_status,
            'status_match': self.status_match,
            'compact_objective': self.compact_objective,
            'benders_objective': self.benders_objective,
            'objective_match': self.objective_match,
            'objective_difference': self.objective_difference,
            'objective_relative_error': self.objective_relative_error,
            'compact_runtime': self.compact_runtime,
            'benders_runtime': self.benders_runtime,
            'runtime_ratio': self.runtime_ratio,
            'compact_error': self.compact_error,
            'benders_error': self.benders_error,
            'discrepancy': self.discrepancy
        }


@dataclass
class MultiComparisonResult:
    """Store comparison between multiple optimization approaches."""
    use_case_name: str
    num_buildings: int = None
    num_time_periods: int = None
    approach_labels: List[str] = None
    statuses: Dict[str, str] = None
    objectives: Dict[str, float] = None
    runtimes: Dict[str, float] = None
    errors: Dict[str, str] = None
    all_match: bool = None
    discrepancies: Dict[str, float] = None

    def __post_init__(self):
        if self.approach_labels is None:
            self.approach_labels = []
        if self.statuses is None:
            self.statuses = {}
        if self.objectives is None:
            self.objectives = {}
        if self.runtimes is None:
            self.runtimes = {}
        if self.errors is None:
            self.errors = {}
        if self.discrepancies is None:
            self.discrepancies = {}

    def has_discrepancy(self) -> bool:
        """Check if there's any discrepancy between approaches."""
        return not self.all_match

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            'use_case_name': self.use_case_name,
            'num_buildings': self.num_buildings,
            'num_time_periods': self.num_time_periods,
            'approach_labels': self.approach_labels,
            'statuses': self.statuses,
            'objectives': self.objectives,
            'runtimes': self.runtimes,
            'errors': self.errors,
            'all_match': self.all_match,
            'discrepancies': self.discrepancies
        }


def compare_all_approaches(results_dict: Dict, use_case_metadata: Dict = None) -> MultiComparisonResult:
    """Compare multiple optimization approaches.

    Args:
        results_dict: Dictionary mapping approach names to OptimizationResult objects
        use_case_metadata: Optional metadata about the use case

    Returns:
        MultiComparisonResult containing comparison of all approaches
    """
    use_case_name = next(iter(results_dict.values())).use_case_name
    comparison = MultiComparisonResult(use_case_name=use_case_name)

    if use_case_metadata:
        comparison.num_buildings = use_case_metadata.get('num_buildings')
        comparison.num_time_periods = use_case_metadata.get('num_time_periods')

    # Extract data from all results
    comparison.approach_labels = list(results_dict.keys())
    for approach, result in results_dict.items():
        comparison.statuses[approach] = result.status_name
        comparison.objectives[approach] = result.objective_value if result.is_optimal() else None
        if result.is_optimal():
            diff = abs(comparison.objectives[approach] - comparison.objectives["compact"])
            comparison.discrepancies[approach] = diff / comparison.objectives["compact"]
        else:
            comparison.discrepancies[approach] = None
        comparison.runtimes[approach] = result.runtime
        comparison.errors[approach] = result.error_message

    # Check if all approaches agree
    statuses = list(comparison.statuses.values())
    # Check status consistency
    all_statuses_match = len(set(statuses)) == 1

    # # Add status discrepancies
    # if not all_statuses_match:
    #     status_str = ", ".join([f"{k}={v}" for k, v in comparison.statuses.items()])
    #     comparison.discrepancies.append(f"Status mismatch: {status_str}")
    #
    # # Add error discrepancies
    # for approach, error in comparison.errors.items():
    #     if error:
    #         comparison.discrepancies.append(f"{approach} error: {error}")

    return comparison


def generate_comparison_summary(comparisons: List[ComparisonResult]) -> Dict:
    """Generate summary statistics from multiple comparisons."""
    total = len(comparisons)
    
    if total == 0:
        return {"total": 0, "message": "No comparisons to analyze"}
    
    status_matches = sum(1 for c in comparisons if c.status_match)
    both_optimal = sum(
        1 for c in comparisons 
        if c.compact_status == "OPTIMAL" and c.benders_status == "OPTIMAL"
    )
    objective_matches = sum(1 for c in comparisons if c.objective_match is True)
    discrepancies = sum(1 for c in comparisons if c.has_discrepancy())

    compact_runtimes = [c.compact_runtime for c in comparisons if c.compact_runtime is not None]
    benders_runtimes = [c.benders_runtime for c in comparisons if c.benders_runtime is not None]
    runtime_ratios = [c.runtime_ratio for c in comparisons if c.runtime_ratio is not None]
    
    discrepancy_cases = [c for c in comparisons if c.has_discrepancy()]
    
    summary = {
        "total_comparisons": total,
        "status_matches": status_matches,
        "status_match_rate": status_matches / total * 100,
        "both_optimal_count": both_optimal,
        "both_optimal_rate": both_optimal / total * 100 if total > 0 else 0,
        "objective_matches": objective_matches,
        "objective_match_rate": objective_matches / both_optimal * 100 if both_optimal > 0 else 0,
        "discrepancy_count": discrepancies,
        "discrepancy_rate": discrepancies / total * 100,
        "avg_compact_runtime": sum(compact_runtimes) / len(compact_runtimes) if compact_runtimes else None,
        "avg_benders_runtime": sum(benders_runtimes) / len(benders_runtimes) if benders_runtimes else None,
        "avg_runtime_ratio": sum(runtime_ratios) / len(runtime_ratios) if runtime_ratios else None,
        "median_runtime_ratio": sorted(runtime_ratios)[len(runtime_ratios)//2] if runtime_ratios else None,
        "discrepancy_cases": [
            {"use_case": c.use_case_name, "description": c.discrepancy}
            for c in discrepancy_cases
        ]
    }
    
    return summary


def generate_multi_comparison_summary(comparisons: List[MultiComparisonResult]) -> Dict:
    """Generate summary statistics from multiple multi-approach comparisons."""
    total = len(comparisons)

    if total == 0:
        return {"total": 0, "message": "No comparisons to analyze"}

    all_match_count = sum(1 for c in comparisons if c.all_match)
    discrepancy_count = sum(1 for c in comparisons if c.has_discrepancy())

    # Collect runtime stats per approach
    approach_labels = comparisons[0].approach_labels if comparisons else []
    approach_runtimes = {label: [] for label in approach_labels}
    approach_optimal_counts = {label: 0 for label in approach_labels}

    for comp in comparisons:
        for label in comp.approach_labels:
            if comp.runtimes.get(label) is not None:
                approach_runtimes[label].append(comp.runtimes[label])
            if comp.statuses.get(label) == "OPTIMAL":
                approach_optimal_counts[label] += 1

    discrepancy_cases = [c for c in comparisons if c.has_discrepancy()]

    summary = {
        "total_comparisons": total,
        "all_match_count": all_match_count,
        "all_match_rate": all_match_count / total * 100 if total > 0 else 0,
        "discrepancy_count": discrepancy_count,
        "discrepancy_rate": discrepancy_count / total * 100 if total > 0 else 0,
        "approach_labels": approach_labels,
        "approach_optimal_counts": approach_optimal_counts,
        "approach_avg_runtimes": {
            label: sum(times) / len(times) if times else None
            for label, times in approach_runtimes.items()
        },
        "discrepancy_cases": [
            {
                "use_case": c.use_case_name,
                "discrepancies": c.discrepancies
            }
            for c in discrepancy_cases
        ]
    }

    return summary


def format_comparison_summary(summary: Dict) -> str:
    """Format comparison summary as string."""
    lines = [
        "\nCOMPARISON SUMMARY",
        "=" * 80,
        f"Total: {summary['total_comparisons']} comparisons",
        f"Status matches: {summary['status_matches']}/{summary['total_comparisons']} ({summary['status_match_rate']:.1f}%)",
        f"Both optimal: {summary['both_optimal_count']}/{summary['total_comparisons']} ({summary['both_optimal_rate']:.1f}%)",
    ]
    
    if summary['both_optimal_count'] > 0:
        lines.append(
            f"Objective matches: {summary['objective_matches']}/{summary['both_optimal_count']} "
            f"({summary['objective_match_rate']:.1f}%)"
        )
    
    lines.append(f"Discrepancies: {summary['discrepancy_count']} ({summary['discrepancy_rate']:.1f}%)")
    
    if summary['discrepancy_count'] > 0:
        lines.append("\nDiscrepancy details:")
        for case in summary['discrepancy_cases']:
            lines.append(f"  {case['use_case']}: {case['description']}")
    
    if summary['avg_compact_runtime'] is not None:
        lines.extend([
            "\nRuntime statistics:",
            f"  Compact: {summary['avg_compact_runtime']:.2f}s avg",
            f"  Benders: {summary['avg_benders_runtime']:.2f}s avg",
            f"  Ratio: {summary['avg_runtime_ratio']:.2f}x avg, {summary['median_runtime_ratio']:.2f}x median"
        ])
    
    lines.append("=" * 80)
    return "\n".join(lines)


def print_comparison_summary(summary: Dict):
    """Print comparison summary (wrapper for backward compatibility)."""
    print(format_comparison_summary(summary))


def format_multi_comparison_summary(summary: Dict) -> str:
    """Format multi-approach comparison summary as string."""
    lines = [
        "\nMULTI-APPROACH COMPARISON SUMMARY",
        "=" * 80,
        f"Total: {summary['total_comparisons']} comparisons",
        f"All approaches match: {summary['all_match_count']}/{summary['total_comparisons']} ({summary['all_match_rate']:.1f}%)",
        f"Discrepancies: {summary['discrepancy_count']} ({summary['discrepancy_rate']:.1f}%)",
        "",
        "Per-approach statistics:",
    ]

    for label in summary['approach_labels']:
        optimal_count = summary['approach_optimal_counts'][label]
        avg_runtime = summary['approach_avg_runtimes'][label]
        runtime_str = f"{avg_runtime:.2f}s avg" if avg_runtime is not None else "N/A"
        lines.append(f"  {label}: {optimal_count}/{summary['total_comparisons']} optimal, {runtime_str}")

    if summary['discrepancy_count'] > 0:
        lines.append("\nDiscrepancy details:")
        for case in summary['discrepancy_cases']:
            lines.append(f"  {case['use_case']}:")
            for disc in case['discrepancies']:
                lines.append(f"    - {disc}")

    lines.append("=" * 80)
    return "\n".join(lines)


def print_multi_comparison_summary(summary: Dict):
    """Print multi-approach comparison summary."""
    print(format_multi_comparison_summary(summary))


