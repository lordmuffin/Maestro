"""
Evaluation Tracking and Version Control for Maestro
Tracks evaluations over time and monitors trends
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import numpy as np
from dataclasses import dataclass, asdict


@dataclass
class EvaluationSnapshot:
    """Snapshot of an evaluation result."""
    timestamp: str
    model: str
    judge: str
    agreement_rate: float
    correlation: float
    mean_absolute_error: float
    inter_run_variance: float
    num_test_cases: int
    metadata: Dict


class EvaluationTracker:
    """Track evaluations over time to monitor improvement trends."""

    def __init__(self, storage_dir: str = "evaluations"):
        """
        Initialize the tracker.

        Args:
            storage_dir: Directory to store evaluation data
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.statistics_file = self.storage_dir / "statistics.json"
        self.snapshots: List[EvaluationSnapshot] = []
        self._load_statistics()

    def _load_statistics(self):
        """Load existing statistics from file."""
        if self.statistics_file.exists():
            with open(self.statistics_file, 'r') as f:
                data = json.load(f)
                self.snapshots = [
                    EvaluationSnapshot(**snapshot)
                    for snapshot in data.get("snapshots", [])
                ]

    def save_evaluation(self, evaluation_result: Dict):
        """
        Save evaluation with metadata.

        Args:
            evaluation_result: Dictionary containing evaluation results
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Add metadata
        evaluation_result["metadata"] = {
            "version": "1.0",
            "timestamp": timestamp,
            "framework": "Maestro"
        }

        # Save full evaluation to file
        filename = f"eval_{timestamp}.json"
        filepath = self.storage_dir / filename

        with open(filepath, 'w') as f:
            json.dump(evaluation_result, f, indent=2, default=str)

        print(f"Evaluation saved to: {filepath}")

        # Extract key metrics for snapshot
        if "baseline" in evaluation_result:
            baseline = evaluation_result["baseline"]["report"]
            snapshot = EvaluationSnapshot(
                timestamp=evaluation_result["timestamp"],
                model=evaluation_result.get("model", "unknown"),
                judge=evaluation_result.get("judge", "unknown"),
                agreement_rate=baseline.aggregate_metrics["overall_agreement"],
                correlation=baseline.aggregate_metrics["overall_correlation"],
                mean_absolute_error=baseline.aggregate_metrics["mean_absolute_error"],
                inter_run_variance=evaluation_result.get("kpis", {}).inter_run_variance if hasattr(evaluation_result.get("kpis", {}), 'inter_run_variance') else 0.0,
                num_test_cases=baseline.total_test_cases,
                metadata=evaluation_result["metadata"]
            )

            self.snapshots.append(snapshot)
            self._save_statistics()

        return filepath

    def _save_statistics(self):
        """Save statistics to file."""
        data = {
            "snapshots": [asdict(snapshot) for snapshot in self.snapshots],
            "last_updated": datetime.now().isoformat(),
            "total_evaluations": len(self.snapshots)
        }

        with open(self.statistics_file, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def get_trend(self, metric_name: str, window: Optional[int] = None) -> List[float]:
        """
        Get the trend for a specific metric over time.

        Args:
            metric_name: Name of the metric (e.g., "agreement_rate")
            window: Number of recent measurements (None = all)

        Returns:
            List of values for that metric over time
        """
        values = [getattr(snapshot, metric_name) for snapshot in self.snapshots]

        if window is not None:
            values = values[-window:]

        return values

    def calculate_trend_slope(self, metric_name: str, window: int = 10) -> float:
        """
        Calculate the slope of a metric's trend.

        Args:
            metric_name: Name of the metric
            window: Number of recent measurements to consider

        Returns:
            Slope value (positive = improving, negative = declining)
        """
        trend = self.get_trend(metric_name, window=window)

        if len(trend) < 2:
            return 0.0

        x = np.arange(len(trend))
        slope = np.polyfit(x, trend, 1)[0]

        return float(slope)

    def is_improving(self, metric_name: str, window: int = 5) -> bool:
        """
        Check if a metric is improving over recent measurements.

        Args:
            metric_name: Name of the metric
            window: Number of recent measurements to consider

        Returns:
            True if the metric is improving
        """
        slope = self.calculate_trend_slope(metric_name, window)

        # Positive slope is good for most metrics (except variance and error)
        inverse_metrics = ["inter_run_variance", "mean_absolute_error"]

        if metric_name in inverse_metrics:
            return slope < 0
        else:
            return slope > 0

    def get_best_evaluation(self, metric_name: str = "agreement_rate") -> Optional[EvaluationSnapshot]:
        """
        Get the best evaluation based on a metric.

        Args:
            metric_name: Metric to optimize for

        Returns:
            EvaluationSnapshot of the best evaluation
        """
        if not self.snapshots:
            return None

        # Inverse metrics should be minimized
        inverse_metrics = ["inter_run_variance", "mean_absolute_error"]

        if metric_name in inverse_metrics:
            return min(self.snapshots, key=lambda s: getattr(s, metric_name))
        else:
            return max(self.snapshots, key=lambda s: getattr(s, metric_name))

    def compare_with_baseline(self, current_metrics: Dict, baseline_idx: int = 0) -> Dict:
        """
        Compare current metrics with baseline.

        Args:
            current_metrics: Dictionary of current metric values
            baseline_idx: Index of baseline snapshot (default: 0 = first evaluation)

        Returns:
            Dictionary with comparison results
        """
        if not self.snapshots or baseline_idx >= len(self.snapshots):
            return {}

        baseline = self.snapshots[baseline_idx]
        comparison = {}

        for metric_name, current_value in current_metrics.items():
            if hasattr(baseline, metric_name):
                baseline_value = getattr(baseline, metric_name)
                change = current_value - baseline_value
                pct_change = (change / baseline_value * 100) if baseline_value != 0 else 0.0

                comparison[metric_name] = {
                    "baseline": baseline_value,
                    "current": current_value,
                    "change": change,
                    "percent_change": pct_change,
                    "improved": change > 0 if metric_name not in ["inter_run_variance", "mean_absolute_error"] else change < 0
                }

        return comparison

    def generate_trends_report(self, window: int = 10) -> str:
        """
        Generate a report showing trends over time.

        Args:
            window: Number of recent measurements to analyze

        Returns:
            Formatted report string
        """
        if len(self.snapshots) < 2:
            return "Not enough data to show trends (need at least 2 evaluations)"

        lines = [
            "",
            "=" * 80,
            "EVALUATION TRENDS REPORT",
            "=" * 80,
            "",
            f"Total Evaluations: {len(self.snapshots)}",
            f"First: {self.snapshots[0].timestamp}",
            f"Latest: {self.snapshots[-1].timestamp}",
            f"Analysis Window: Last {min(window, len(self.snapshots))} evaluations",
            "",
        ]

        metrics_to_track = [
            ("agreement_rate", "Agreement Rate", False),
            ("correlation", "Correlation", False),
            ("mean_absolute_error", "Mean Absolute Error", True),
            ("inter_run_variance", "Inter-run Variance", True),
        ]

        for metric_name, display_name, lower_is_better in metrics_to_track:
            trend = self.get_trend(metric_name, window=window)

            if not trend:
                continue

            first_val = trend[0]
            latest_val = trend[-1]
            change = latest_val - first_val
            slope = self.calculate_trend_slope(metric_name, window)

            # Determine status
            if lower_is_better:
                direction = "↓" if change < 0 else "↑"
                status = "✓ Improving" if change < 0 else "✗ Declining"
            else:
                direction = "↑" if change > 0 else "↓"
                status = "✓ Improving" if change > 0 else "✗ Declining"

            lines.append(f"{display_name}:")
            lines.append(f"  First:      {first_val:.4f}")
            lines.append(f"  Latest:     {latest_val:.4f}")
            lines.append(f"  Change:     {change:+.4f} {direction}")
            lines.append(f"  Slope:      {slope:+.4f}")
            lines.append(f"  Status:     {status}")
            lines.append("")

        # Best evaluation
        best = self.get_best_evaluation("agreement_rate")
        if best:
            lines.append("🏆 BEST EVALUATION (by Agreement Rate):")
            lines.append(f"  Timestamp:  {best.timestamp}")
            lines.append(f"  Model:      {best.model}")
            lines.append(f"  Judge:      {best.judge}")
            lines.append(f"  Agreement:  {best.agreement_rate:.2%}")
            lines.append(f"  Correlation:{best.correlation:.3f}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)

    def generate_comparison_report(self, baseline_idx: int = 0, current_idx: int = -1) -> str:
        """
        Generate a comparison report between two evaluations.

        Args:
            baseline_idx: Index of baseline evaluation
            current_idx: Index of current evaluation (default: -1 = latest)

        Returns:
            Formatted comparison report
        """
        if len(self.snapshots) < 2:
            return "Not enough evaluations to compare"

        baseline = self.snapshots[baseline_idx]
        current = self.snapshots[current_idx]

        lines = [
            "",
            "=" * 80,
            "EVALUATION COMPARISON REPORT",
            "=" * 80,
            "",
            "BASELINE:",
            f"  Timestamp:  {baseline.timestamp}",
            f"  Model:      {baseline.model}",
            f"  Judge:      {baseline.judge}",
            "",
            "CURRENT:",
            f"  Timestamp:  {current.timestamp}",
            f"  Model:      {current.model}",
            f"  Judge:      {current.judge}",
            "",
            "METRICS COMPARISON:",
            "",
            "| Metric | Baseline | Current | Change | % Change | Status |",
            "|--------|----------|---------|--------|----------|--------|"
        ]

        metrics_to_compare = [
            ("agreement_rate", "Agreement Rate", False),
            ("correlation", "Correlation", False),
            ("mean_absolute_error", "MAE", True),
            ("inter_run_variance", "Variance", True),
        ]

        for metric_name, display_name, lower_is_better in metrics_to_compare:
            baseline_val = getattr(baseline, metric_name)
            current_val = getattr(current, metric_name)
            change = current_val - baseline_val
            pct_change = (change / baseline_val * 100) if baseline_val != 0 else 0.0

            if lower_is_better:
                status = "✓" if change < 0 else "✗"
            else:
                status = "✓" if change > 0 else "✗"

            lines.append(
                f"| {display_name:<14} | {baseline_val:>8.4f} | {current_val:>7.4f} | {change:>+6.4f} | {pct_change:>+7.1f}% | {status:>6} |"
            )

        lines.append("")
        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)

    def export_to_csv(self, output_file: str = "evaluation_history.csv"):
        """
        Export evaluation history to CSV file.

        Args:
            output_file: Path to output CSV file
        """
        import csv

        filepath = self.storage_dir / output_file

        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = [
                'timestamp', 'model', 'judge', 'agreement_rate',
                'correlation', 'mean_absolute_error', 'inter_run_variance',
                'num_test_cases'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for snapshot in self.snapshots:
                writer.writerow({
                    'timestamp': snapshot.timestamp,
                    'model': snapshot.model,
                    'judge': snapshot.judge,
                    'agreement_rate': snapshot.agreement_rate,
                    'correlation': snapshot.correlation,
                    'mean_absolute_error': snapshot.mean_absolute_error,
                    'inter_run_variance': snapshot.inter_run_variance,
                    'num_test_cases': snapshot.num_test_cases
                })

        print(f"History exported to: {filepath}")
        return filepath


def main():
    """CLI for tracking management."""
    import argparse

    parser = argparse.ArgumentParser(description='Maestro evaluation tracking')
    parser.add_argument('command', choices=['trends', 'compare', 'export', 'best'],
                        help='Command to execute')
    parser.add_argument('--window', type=int, default=10,
                        help='Window size for trend analysis (default: 10)')
    parser.add_argument('--storage-dir', type=str, default='evaluations',
                        help='Storage directory (default: evaluations)')

    args = parser.parse_args()

    tracker = EvaluationTracker(storage_dir=args.storage_dir)

    if args.command == 'trends':
        print(tracker.generate_trends_report(window=args.window))

    elif args.command == 'compare':
        print(tracker.generate_comparison_report())

    elif args.command == 'export':
        tracker.export_to_csv()

    elif args.command == 'best':
        best = tracker.get_best_evaluation()
        if best:
            print("\n🏆 BEST EVALUATION:")
            print(f"  Timestamp:  {best.timestamp}")
            print(f"  Model:      {best.model}")
            print(f"  Judge:      {best.judge}")
            print(f"  Agreement:  {best.agreement_rate:.2%}")
            print(f"  Correlation:{best.correlation:.3f}")
            print(f"  MAE:        {best.mean_absolute_error:.3f}")
            print()
        else:
            print("No evaluations found")


if __name__ == "__main__":
    main()
