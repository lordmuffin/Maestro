"""
Automated Evaluation Pipeline for Maestro
Orchestrates complete evaluation workflow with all metrics
"""

import asyncio
from datetime import datetime
from typing import List, Optional, Dict
from pathlib import Path

from test_cases import TestCase, GOLDEN_TEST_SUITE
from baseline import establish_baseline, BaselineReport, format_baseline_report
from sensitivity import test_prompt_sensitivity, format_sensitivity_report
from kpis import MaestroKPIs, calculate_kpis_from_evaluation
from metrics import calculate_overall_agreement
from scorecard import resolve_model


class MaestroEvaluationPipeline:
    """
    Complete evaluation pipeline with all metrics and reports.
    """

    def __init__(
        self,
        test_cases: List[TestCase] = None,
        model_identifier: str = "claude-sonnet-4.5",
        judge_identifier: str = "claude-sonnet-4.5"
    ):
        """
        Initialize the evaluation pipeline.

        Args:
            test_cases: List of test cases to use (default: GOLDEN_TEST_SUITE)
            model_identifier: Model to evaluate
            judge_identifier: Model to use as judge
        """
        self.test_cases = test_cases or GOLDEN_TEST_SUITE
        self.model_identifier = model_identifier
        self.judge_identifier = judge_identifier
        self.results_history = []

        # Resolve models for display
        self.model_config = resolve_model(model_identifier)
        self.judge_config = resolve_model(judge_identifier)

    async def run_full_evaluation(
        self,
        include_sensitivity: bool = True,
        sensitivity_prompts: Optional[List[str]] = None,
        max_concurrent: int = 3
    ) -> Dict:
        """
        Run complete evaluation with all metrics.

        Args:
            include_sensitivity: Whether to include sensitivity testing
            sensitivity_prompts: Specific prompts for sensitivity testing
            max_concurrent: Maximum concurrent evaluations

        Returns:
            Dictionary with all evaluation results
        """
        print("=" * 80)
        print("MAESTRO FULL EVALUATION PIPELINE")
        print("=" * 80)
        print()
        print(f"Model:      {self.model_config.display_name}")
        print(f"Judge:      {self.judge_config.display_name}")
        print(f"Test Cases: {len(self.test_cases)}")
        print()

        start_time = datetime.now()
        results = {
            "timestamp": start_time.isoformat(),
            "model": self.model_identifier,
            "judge": self.judge_identifier,
            "config": {
                "test_cases": len(self.test_cases),
                "include_sensitivity": include_sensitivity,
                "max_concurrent": max_concurrent
            }
        }

        # Step 1: Run baseline evaluation with test cases
        print("=" * 80)
        print("STEP 1: BASELINE EVALUATION")
        print("=" * 80)
        print()

        baseline_report = await establish_baseline(
            model_identifier=self.model_identifier,
            judge_identifier=self.judge_identifier,
            test_cases=self.test_cases,
            max_concurrent=max_concurrent
        )

        results["baseline"] = {
            "report": baseline_report,
            "summary": format_baseline_report(baseline_report)
        }

        print(format_baseline_report(baseline_report))

        # Step 2: Sensitivity testing (if requested)
        if include_sensitivity:
            print("=" * 80)
            print("STEP 2: SENSITIVITY TESTING")
            print("=" * 80)
            print()

            # Use provided prompts or select from test cases
            if sensitivity_prompts is None:
                sensitivity_prompts = [tc.prompt for tc in self.test_cases[:3]]

            sensitivity_results = []
            for i, prompt in enumerate(sensitivity_prompts, 1):
                print(f"[{i}/{len(sensitivity_prompts)}] Testing prompt sensitivity...")
                sens_result = await test_prompt_sensitivity(
                    prompt,
                    model_identifier=self.model_identifier,
                    judge_identifier=self.judge_identifier
                )
                sensitivity_results.append(sens_result)
                print(format_sensitivity_report(sens_result))

            # Calculate aggregate sensitivity metrics
            import numpy as np
            avg_variance = np.mean([r['sensitivity_metrics']['variance'] for r in sensitivity_results])
            stability_rate = np.mean([r['sensitivity_metrics']['is_stable'] for r in sensitivity_results])

            results["sensitivity"] = {
                "individual_tests": sensitivity_results,
                "aggregate": {
                    "avg_variance": avg_variance,
                    "stability_rate": stability_rate
                }
            }

        # Step 3: Calculate KPIs
        print("=" * 80)
        print("STEP 3: KPI CALCULATION")
        print("=" * 80)
        print()

        # Prepare data for KPI calculation
        timing_data = {
            "avg_evaluation_time": (datetime.now() - start_time).total_seconds() / len(self.test_cases)
        }

        # Estimate cost (this is a placeholder - actual cost depends on tokens)
        cost_data = {
            "cost_per_evaluation": 0.01,  # Placeholder
            "false_positive_rate": 0.05,  # Would need labeled data
            "false_negative_rate": 0.08,  # Would need labeled data
            "discrimination_power": 0.75  # Placeholder
        }

        # Build eval_results structure for KPI calculation
        eval_results = {
            "detailed": {},
            "config": {"mode": "baseline"}
        }

        kpis = calculate_kpis_from_evaluation(
            eval_results,
            baseline_report.test_results,
            timing_data,
            cost_data
        )

        # Override with actual calculated metrics
        kpis.overall_agreement_rate = baseline_report.aggregate_metrics["overall_agreement"]
        kpis.agreement_by_category = {
            cat: metrics["agreement"]
            for cat, metrics in baseline_report.category_metrics.items()
        }
        kpis.agreement_by_criterion = baseline_report.criterion_metrics

        if include_sensitivity:
            kpis.inter_run_variance = results["sensitivity"]["aggregate"]["avg_variance"]

        results["kpis"] = kpis
        print(kpis.to_dashboard())

        # Step 4: Generate summary and recommendations
        print("=" * 80)
        print("STEP 4: SUMMARY & RECOMMENDATIONS")
        print("=" * 80)
        print()

        summary = self._generate_summary(results)
        results["summary"] = summary
        print(summary)

        # Save results
        results["execution_time"] = (datetime.now() - start_time).total_seconds()
        self.results_history.append(results)

        return results

    def _generate_summary(self, results: Dict) -> str:
        """Generate summary and recommendations from results."""
        lines = [
            "",
            "📊 EVALUATION SUMMARY:",
            ""
        ]

        kpis = results["kpis"]
        baseline = results["baseline"]["report"]

        # Overall assessment
        if kpis.meets_targets():
            lines.append("✓ Overall: ALL KPI TARGETS MET")
        else:
            lines.append("✗ Overall: SOME KPI TARGETS NOT MET")

        lines.append("")
        lines.append("Key Findings:")

        # Agreement
        agreement = baseline.aggregate_metrics["overall_agreement"]
        if agreement >= 0.80:
            lines.append(f"  ✓ Judge-Human Agreement: {agreement:.2%} (meets target)")
        else:
            lines.append(f"  ✗ Judge-Human Agreement: {agreement:.2%} (below 80% target)")

        # Correlation
        correlation = baseline.aggregate_metrics["overall_correlation"]
        if correlation >= 0.70:
            lines.append(f"  ✓ Score Correlation: {correlation:.3f} (strong)")
        else:
            lines.append(f"  ✗ Score Correlation: {correlation:.3f} (weak, target: ≥0.70)")

        # Sensitivity (if tested)
        if "sensitivity" in results:
            stability_rate = results["sensitivity"]["aggregate"]["stability_rate"]
            if stability_rate >= 0.80:
                lines.append(f"  ✓ Stability: {stability_rate:.2%} of prompts stable")
            else:
                lines.append(f"  ⚠ Stability: {stability_rate:.2%} of prompts stable (target: ≥80%)")

        lines.append("")
        lines.append("💡 RECOMMENDATIONS:")
        lines.append("")

        # Generate specific recommendations based on results
        recommendations = []

        if agreement < 0.80:
            recommendations.append("• Improve judge prompt clarity and specificity")
            recommendations.append("• Review criteria definitions with evaluators")
            recommendations.append("• Consider additional training examples for judge")

        if correlation < 0.70:
            recommendations.append("• Investigate systematic biases in judge scoring")
            recommendations.append("• Ensure criteria are measurable and objective")

        if "sensitivity" in results and results["sensitivity"]["aggregate"]["stability_rate"] < 0.80:
            recommendations.append("• Reduce judge sensitivity to formatting variations")
            recommendations.append("• Use temperature=0 for more deterministic scoring")
            recommendations.append("• Add robustness guidelines to judge prompt")

        # Category-specific recommendations
        for category, metrics in baseline.category_metrics.items():
            if metrics["agreement"] < 0.75:
                recommendations.append(f"• Focus improvement on {category} category (agreement: {metrics['agreement']:.2%})")

        if not recommendations:
            recommendations.append("• Continue monitoring performance with diverse test cases")
            recommendations.append("• Expand test suite to cover more edge cases")

        lines.extend(recommendations)
        lines.append("")

        return "\n".join(lines)

    async def compare_judges(
        self,
        judge_identifiers: List[str],
        max_concurrent: int = 3
    ) -> Dict:
        """
        Compare multiple judge models.

        Args:
            judge_identifiers: List of judge model identifiers to compare
            max_concurrent: Maximum concurrent evaluations

        Returns:
            Comparison results
        """
        print("=" * 80)
        print("JUDGE COMPARISON")
        print("=" * 80)
        print()

        results = {}

        for judge_id in judge_identifiers:
            print(f"\nEvaluating with judge: {judge_id}")
            print("-" * 80)

            # Save current judge
            original_judge = self.judge_identifier

            # Set new judge
            self.judge_identifier = judge_id
            self.judge_config = resolve_model(judge_id)

            # Run evaluation
            eval_result = await self.run_full_evaluation(
                include_sensitivity=False,
                max_concurrent=max_concurrent
            )

            results[judge_id] = eval_result

            # Restore original judge
            self.judge_identifier = original_judge
            self.judge_config = resolve_model(original_judge)

        # Generate comparison report
        comparison_report = self._generate_judge_comparison_report(results)
        print(comparison_report)

        return {
            "individual_results": results,
            "comparison_report": comparison_report
        }

    def _generate_judge_comparison_report(self, results: Dict) -> str:
        """Generate comparison report for multiple judges."""
        lines = [
            "",
            "=" * 80,
            "JUDGE COMPARISON REPORT",
            "=" * 80,
            "",
            "| Judge | Agreement | Correlation | MAE | Variance |",
            "|-------|-----------|-------------|-----|----------|"
        ]

        for judge_id, result in results.items():
            baseline = result["baseline"]["report"]
            kpis = result["kpis"]

            judge_config = resolve_model(judge_id)
            agreement = baseline.aggregate_metrics["overall_agreement"]
            correlation = baseline.aggregate_metrics["overall_correlation"]
            mae = baseline.aggregate_metrics["mean_absolute_error"]
            variance = kpis.inter_run_variance

            lines.append(
                f"| {judge_config.display_name:<20.20s} | {agreement:>8.2%} | {correlation:>10.3f} | {mae:>3.2f} | {variance:>7.3f} |"
            )

        lines.append("")
        lines.append("Best Judge by Metric:")

        # Find best for each metric
        best_agreement = max(results.items(), key=lambda x: x[1]["baseline"]["report"].aggregate_metrics["overall_agreement"])
        best_correlation = max(results.items(), key=lambda x: x[1]["baseline"]["report"].aggregate_metrics["overall_correlation"])
        best_mae = min(results.items(), key=lambda x: x[1]["baseline"]["report"].aggregate_metrics["mean_absolute_error"])

        lines.append(f"  Agreement:   {resolve_model(best_agreement[0]).display_name}")
        lines.append(f"  Correlation: {resolve_model(best_correlation[0]).display_name}")
        lines.append(f"  MAE:         {resolve_model(best_mae[0]).display_name}")
        lines.append("")

        return "\n".join(lines)

    def save_results(self, results: Dict, output_dir: str = "evaluations"):
        """Save evaluation results to file."""
        from pathlib import Path
        import json

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"evaluation_{timestamp}.json"

        # Convert to serializable format
        serializable_results = self._make_serializable(results)

        filepath = output_path / filename
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)

        print(f"Results saved to: {filepath}")
        return filepath

    def _make_serializable(self, obj):
        """Convert objects to JSON-serializable format."""
        if hasattr(obj, '__dict__'):
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, (str, int, float, bool, type(None))):
            return obj
        else:
            return str(obj)


async def main():
    """Run the evaluation pipeline."""
    import argparse

    parser = argparse.ArgumentParser(description='Run Maestro evaluation pipeline')
    parser.add_argument('--model', type=str, default='claude-sonnet-4.5',
                        help='Model to evaluate (default: claude-sonnet-4.5)')
    parser.add_argument('--judge', type=str, default='claude-sonnet-4.5',
                        help='Judge model (default: claude-sonnet-4.5)')
    parser.add_argument('--no-sensitivity', action='store_true',
                        help='Skip sensitivity testing')
    parser.add_argument('--concurrent', type=int, default=3,
                        help='Max concurrent evaluations (default: 3)')
    parser.add_argument('--compare-judges', type=str, nargs='+',
                        help='Compare multiple judges (space-separated list)')

    args = parser.parse_args()

    # Create pipeline
    pipeline = MaestroEvaluationPipeline(
        model_identifier=args.model,
        judge_identifier=args.judge
    )

    if args.compare_judges:
        # Compare multiple judges
        results = await pipeline.compare_judges(
            judge_identifiers=args.compare_judges,
            max_concurrent=args.concurrent
        )
    else:
        # Run single evaluation
        results = await pipeline.run_full_evaluation(
            include_sensitivity=not args.no_sensitivity,
            max_concurrent=args.concurrent
        )

    # Save results
    pipeline.save_results(results)


if __name__ == "__main__":
    asyncio.run(main())
