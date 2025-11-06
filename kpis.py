"""
KPI Tracking System for Maestro Evaluation Framework
Defines and tracks Key Performance Indicators for evaluation quality
"""

from dataclasses import dataclass, asdict
from typing import Dict, List
from datetime import datetime
import json


@dataclass
class MaestroKPIs:
    """
    Key Performance Indicators for Maestro evaluation system.

    Primary KPIs:
    - overall_agreement_rate: Judge-human agreement (target: >80%)
    - inter_run_variance: Consistency across runs (target: <0.2)

    Quality KPIs:
    - false_positive_rate: Marking bad as good (target: <10%)
    - false_negative_rate: Marking good as bad (target: <15%)
    - discrimination_power: Ability to distinguish quality levels (target: >0.7)

    Efficiency KPIs:
    - avg_evaluation_time: Seconds per evaluation
    - cost_per_evaluation: API costs in USD
    """

    # Primary Metrics
    overall_agreement_rate: float  # Target: >80%
    agreement_by_category: Dict[str, float]
    agreement_by_criterion: Dict[str, float]

    # Consistency Metrics
    inter_run_variance: float  # Target: <0.2
    position_bias_score: float  # Should be near 0

    # Efficiency Metrics
    avg_evaluation_time: float  # Seconds
    cost_per_evaluation: float  # USD

    # Quality Metrics
    false_positive_rate: float  # Target: <10%
    false_negative_rate: float  # Target: <15%
    discrimination_power: float  # Target: >0.7

    # Metadata
    timestamp: str
    total_evaluations: int
    evaluation_mode: str  # "model" or "prompt"

    def meets_targets(self) -> bool:
        """Check if all target KPIs are met."""
        return (
            self.overall_agreement_rate >= 0.80 and
            self.inter_run_variance < 0.2 and
            self.false_positive_rate < 0.10 and
            self.false_negative_rate < 0.15 and
            self.discrimination_power >= 0.7
        )

    def get_failing_kpis(self) -> List[str]:
        """Get list of KPIs that don't meet targets."""
        failing = []

        if self.overall_agreement_rate < 0.80:
            failing.append(f"Overall Agreement: {self.overall_agreement_rate:.2%} (target: ≥80%)")

        if self.inter_run_variance >= 0.2:
            failing.append(f"Inter-run Variance: {self.inter_run_variance:.3f} (target: <0.2)")

        if self.false_positive_rate >= 0.10:
            failing.append(f"False Positive Rate: {self.false_positive_rate:.2%} (target: <10%)")

        if self.false_negative_rate >= 0.15:
            failing.append(f"False Negative Rate: {self.false_negative_rate:.2%} (target: <15%)")

        if self.discrimination_power < 0.7:
            failing.append(f"Discrimination Power: {self.discrimination_power:.2f} (target: ≥0.7)")

        return failing

    def to_dashboard(self) -> str:
        """Generate a dashboard view of KPIs."""
        status = "✓ ALL TARGETS MET" if self.meets_targets() else "✗ NEEDS IMPROVEMENT"

        lines = [
            "",
            "=" * 80,
            "MAESTRO KPI DASHBOARD",
            "=" * 80,
            "",
            f"Status: {status}",
            f"Timestamp: {self.timestamp}",
            f"Mode: {self.evaluation_mode}",
            f"Total Evaluations: {self.total_evaluations}",
            "",
            "🎯 PRIMARY METRICS:",
            f"  Overall Agreement:     {self.overall_agreement_rate:>6.2%}  {'✓' if self.overall_agreement_rate >= 0.80 else '✗'}  (target: ≥80%)",
            f"  Consistency Score:     {1 - self.inter_run_variance:>6.2%}  {'✓' if self.inter_run_variance < 0.2 else '✗'}  (variance: {self.inter_run_variance:.3f})",
            "",
            "⚡ EFFICIENCY:",
            f"  Avg Evaluation Time:   {self.avg_evaluation_time:>6.2f}s",
            f"  Cost per Evaluation:   ${self.cost_per_evaluation:>6.4f}",
            "",
            "📊 QUALITY METRICS:",
            f"  False Positives:       {self.false_positive_rate:>6.2%}  {'✓' if self.false_positive_rate < 0.10 else '✗'}  (target: <10%)",
            f"  False Negatives:       {self.false_negative_rate:>6.2%}  {'✓' if self.false_negative_rate < 0.15 else '✗'}  (target: <15%)",
            f"  Discrimination Power:  {self.discrimination_power:>6.2f}  {'✓' if self.discrimination_power >= 0.7 else '✗'}  (target: ≥0.7)",
            f"  Position Bias:         {abs(self.position_bias_score):>6.3f}  {'✓' if abs(self.position_bias_score) < 0.1 else '✗'}  (target: ~0)",
            "",
        ]

        # Category breakdown
        if self.agreement_by_category:
            lines.append("📁 AGREEMENT BY CATEGORY:")
            for category, rate in sorted(self.agreement_by_category.items()):
                lines.append(f"  {category:<25} {rate:>6.2%}")
            lines.append("")

        # Criterion breakdown
        if self.agreement_by_criterion:
            lines.append("📋 AGREEMENT BY CRITERION:")
            for criterion, rate in sorted(self.agreement_by_criterion.items()):
                indicator = "✓" if rate >= 0.75 else "✗"
                lines.append(f"  {criterion:<30} {rate:>6.2%}  {indicator}")
            lines.append("")

        # Recommendations
        if not self.meets_targets():
            lines.append("🔧 RECOMMENDATIONS:")
            for failing_kpi in self.get_failing_kpis():
                lines.append(f"  • {failing_kpi}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> Dict:
        """Convert KPIs to dictionary format."""
        return asdict(self)

    def save_to_file(self, filepath: str):
        """Save KPIs to JSON file."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2, default=str)

    @classmethod
    def from_dict(cls, data: Dict) -> 'MaestroKPIs':
        """Load KPIs from dictionary."""
        return cls(**data)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'MaestroKPIs':
        """Load KPIs from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)


def calculate_kpis_from_evaluation(
    eval_results: Dict,
    test_results: List[Dict],
    timing_data: Dict,
    cost_data: Dict
) -> MaestroKPIs:
    """
    Calculate KPIs from evaluation results.

    Args:
        eval_results: Results from evaluation run
        test_results: List of test case results with human/LLM scores
        timing_data: Timing information
        cost_data: Cost information

    Returns:
        MaestroKPIs object with calculated metrics
    """
    from metrics import (
        calculate_overall_agreement,
        calculate_category_agreement,
        calculate_criterion_agreement
    )

    # Primary metrics
    overall_agreement = calculate_overall_agreement(test_results)
    agreement_by_category = calculate_category_agreement(test_results)
    agreement_by_criterion = calculate_criterion_agreement(test_results)

    # Consistency metrics
    inter_run_variance = calculate_inter_run_variance(eval_results)
    position_bias = calculate_position_bias(eval_results)

    # Efficiency metrics
    avg_time = timing_data.get("avg_evaluation_time", 0.0)
    cost = cost_data.get("cost_per_evaluation", 0.0)

    # Quality metrics (these require additional data)
    fpr = cost_data.get("false_positive_rate", 0.0)
    fnr = cost_data.get("false_negative_rate", 0.0)
    discrimination = cost_data.get("discrimination_power", 0.5)

    return MaestroKPIs(
        overall_agreement_rate=overall_agreement,
        agreement_by_category=agreement_by_category,
        agreement_by_criterion=agreement_by_criterion,
        inter_run_variance=inter_run_variance,
        position_bias_score=position_bias,
        avg_evaluation_time=avg_time,
        cost_per_evaluation=cost,
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        discrimination_power=discrimination,
        timestamp=datetime.now().isoformat(),
        total_evaluations=len(test_results),
        evaluation_mode=eval_results.get("config", {}).get("mode", "unknown")
    )


def calculate_inter_run_variance(eval_results: Dict) -> float:
    """
    Calculate variance across multiple runs for consistency measurement.

    Args:
        eval_results: Evaluation results with multiple runs

    Returns:
        Variance score (lower is more consistent)
    """
    if "detailed" not in eval_results:
        return 0.0

    import numpy as np

    all_variances = []
    detailed = eval_results["detailed"]

    # For each prompt/model combination, calculate variance across runs
    for entity_name, entity_data in detailed.items():
        if isinstance(entity_data, dict):
            for task_or_prompt, runs in entity_data.items():
                if isinstance(runs, list) and len(runs) > 1:
                    # Extract weighted averages from each run
                    from scorecard import calculate_weighted_average, GENERAL_CRITERIA

                    weighted_avgs = [
                        calculate_weighted_average(run, GENERAL_CRITERIA)
                        for run in runs
                    ]
                    if weighted_avgs:
                        all_variances.append(np.var(weighted_avgs))

    return float(np.mean(all_variances)) if all_variances else 0.0


def calculate_position_bias(eval_results: Dict) -> float:
    """
    Calculate position bias (whether order affects scoring).

    Args:
        eval_results: Evaluation results

    Returns:
        Position bias score (should be near 0 for no bias)
    """
    # This is a placeholder - actual implementation would require
    # tracking which response was shown first in A/B comparisons
    # For now, return 0.0
    return 0.0


class KPITracker:
    """Track KPIs over time to monitor improvement trends."""

    def __init__(self):
        self.history: List[MaestroKPIs] = []

    def add_measurement(self, kpis: MaestroKPIs):
        """Add a new KPI measurement to the history."""
        self.history.append(kpis)

    def get_trend(self, metric_name: str) -> List[float]:
        """
        Get the trend for a specific metric over time.

        Args:
            metric_name: Name of the metric (e.g., "overall_agreement_rate")

        Returns:
            List of values for that metric over time
        """
        return [getattr(kpi, metric_name) for kpi in self.history]

    def is_improving(self, metric_name: str, window: int = 5) -> bool:
        """
        Check if a metric is improving over recent measurements.

        Args:
            metric_name: Name of the metric
            window: Number of recent measurements to consider

        Returns:
            True if the metric is improving
        """
        trend = self.get_trend(metric_name)
        if len(trend) < 2:
            return True  # Not enough data

        recent = trend[-window:]
        if len(recent) < 2:
            return True

        # Simple linear regression to check trend
        import numpy as np
        x = np.arange(len(recent))
        slope = np.polyfit(x, recent, 1)[0]

        # Positive slope is good for most metrics (except variance and error rates)
        inverse_metrics = ["inter_run_variance", "false_positive_rate", "false_negative_rate"]
        if metric_name in inverse_metrics:
            return slope < 0
        else:
            return slope > 0

    def generate_trends_report(self) -> str:
        """Generate a report showing trends over time."""
        if len(self.history) < 2:
            return "Not enough data to show trends (need at least 2 measurements)"

        lines = [
            "",
            "=" * 80,
            "KPI TRENDS REPORT",
            "=" * 80,
            "",
            f"Total Measurements: {len(self.history)}",
            f"First: {self.history[0].timestamp}",
            f"Latest: {self.history[-1].timestamp}",
            "",
        ]

        key_metrics = [
            ("overall_agreement_rate", "Overall Agreement", False),
            ("inter_run_variance", "Inter-run Variance", True),
            ("false_positive_rate", "False Positive Rate", True),
            ("discrimination_power", "Discrimination Power", False),
        ]

        for metric_name, display_name, lower_is_better in key_metrics:
            trend = self.get_trend(metric_name)
            first_val = trend[0]
            latest_val = trend[-1]
            change = latest_val - first_val
            improving = self.is_improving(metric_name)

            if lower_is_better:
                direction = "↓" if change < 0 else "↑"
                status = "✓" if change < 0 else "✗"
            else:
                direction = "↑" if change > 0 else "↓"
                status = "✓" if change > 0 else "✗"

            lines.append(f"{display_name}:")
            lines.append(f"  First:  {first_val:.4f}")
            lines.append(f"  Latest: {latest_val:.4f}")
            lines.append(f"  Change: {change:+.4f} {direction} {status}")
            lines.append(f"  Trend:  {'Improving' if improving else 'Not improving'}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("")

        return "\n".join(lines)
