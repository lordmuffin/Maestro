"""
Demo script showing how to use Maestro's enhanced evaluation features
"""

import asyncio
from test_cases import GOLDEN_TEST_SUITE, get_test_suite_stats, TestCategory
from metrics import calculate_agreement, format_metrics_report


def demo_test_suite():
    """Demonstrate the golden test suite."""
    print("=" * 80)
    print("DEMO: GOLDEN TEST SUITE")
    print("=" * 80)
    print()

    # Show statistics
    stats = get_test_suite_stats()
    print(f"Total Test Cases: {stats['total']}")
    print()

    print("By Category:")
    for category, count in stats['by_category'].items():
        print(f"  {category:20s}: {count}")
    print()

    print("By Difficulty:")
    for difficulty, count in stats['by_difficulty'].items():
        print(f"  {difficulty:20s}: {count}")
    print()

    # Show a sample test case
    print("Sample Test Case:")
    tc = GOLDEN_TEST_SUITE[0]
    print(f"  ID:         {tc.id}")
    print(f"  Category:   {tc.category.value}")
    print(f"  Difficulty: {tc.difficulty.value}")
    print(f"  Prompt:     {tc.prompt[:80]}...")
    print(f"  Expected:   {len(tc.expected_elements)} elements")
    print(f"  Human Scores: {len(tc.human_scores)} criteria")
    print()


def demo_metrics():
    """Demonstrate agreement metrics calculation."""
    print("=" * 80)
    print("DEMO: AGREEMENT METRICS")
    print("=" * 80)
    print()

    # Example scores (simulated)
    human_scores = {
        "Factual Accuracy": 4.5,
        "Logical Consistency": 4.0,
        "Clarity & Coherence": 4.5,
        "Completeness": 4.0,
        "Relevance to Query": 5.0,
    }

    llm_scores = {
        "Factual Accuracy": 4.3,
        "Logical Consistency": 4.2,
        "Clarity & Coherence": 4.4,
        "Completeness": 3.8,
        "Relevance to Query": 4.8,
    }

    print("Human Scores:", human_scores)
    print("LLM Scores:  ", llm_scores)
    print()

    # Calculate agreement
    agreement = calculate_agreement(llm_scores, human_scores)
    print(format_metrics_report(agreement))


async def demo_baseline_quick():
    """Demonstrate baseline evaluation with a single test case."""
    print("=" * 80)
    print("DEMO: BASELINE EVALUATION (1 test case)")
    print("=" * 80)
    print()

    from baseline import evaluate_single_test_case
    from scorecard import resolve_model

    # Use first test case
    test_case = GOLDEN_TEST_SUITE[0]
    model_config = resolve_model("claude-sonnet-4.5")
    judge_config = resolve_model("claude-sonnet-4.5")

    print(f"Test Case: {test_case.id}")
    print(f"Category:  {test_case.category.value}")
    print(f"Prompt:    {test_case.prompt[:80]}...")
    print()
    print("Running evaluation...")

    result = await evaluate_single_test_case(test_case, model_config, judge_config)

    print()
    print("Results:")
    print(f"  LLM Weighted Avg:   {result.weighted_avg_llm:.2f}")
    print(f"  Human Weighted Avg: {result.weighted_avg_human:.2f}")
    print(f"  Agreement Rate:     {result.agreement_metrics['exact_agreement']:.2%}")
    print(f"  Correlation:        {result.agreement_metrics['correlation']:.3f}")
    print(f"  MAE:                {result.agreement_metrics['mean_absolute_error']:.3f}")
    print()


def demo_kpis():
    """Demonstrate KPI dashboard."""
    print("=" * 80)
    print("DEMO: KPI DASHBOARD")
    print("=" * 80)
    print()

    from kpis import MaestroKPIs
    from datetime import datetime

    # Create sample KPIs
    kpis = MaestroKPIs(
        overall_agreement_rate=0.85,
        agreement_by_category={
            "factual": 0.88,
            "analytical": 0.82,
            "creative": 0.80,
            "code": 0.90
        },
        agreement_by_criterion={
            "Factual Accuracy": 0.87,
            "Logical Consistency": 0.85,
            "Clarity & Coherence": 0.82,
            "Completeness": 0.80,
            "Relevance to Query": 0.88
        },
        inter_run_variance=0.15,
        position_bias_score=0.02,
        avg_evaluation_time=3.5,
        cost_per_evaluation=0.015,
        false_positive_rate=0.08,
        false_negative_rate=0.12,
        discrimination_power=0.75,
        timestamp=datetime.now().isoformat(),
        total_evaluations=10,
        evaluation_mode="baseline"
    )

    print(kpis.to_dashboard())

    print("Target Status:")
    if kpis.meets_targets():
        print("  ✓ All targets met!")
    else:
        print("  ✗ Some targets not met:")
        for failing in kpis.get_failing_kpis():
            print(f"    - {failing}")
    print()


def demo_tracking():
    """Demonstrate evaluation tracking."""
    print("=" * 80)
    print("DEMO: EVALUATION TRACKING")
    print("=" * 80)
    print()

    from tracking import EvaluationTracker, EvaluationSnapshot
    from datetime import datetime, timedelta

    # Create tracker with simulated history
    tracker = EvaluationTracker(storage_dir="evaluations_demo")

    # Add some sample snapshots
    base_time = datetime.now() - timedelta(days=10)

    for i in range(5):
        snapshot = EvaluationSnapshot(
            timestamp=(base_time + timedelta(days=i*2)).isoformat(),
            model="claude-sonnet-4.5",
            judge="claude-sonnet-4.5",
            agreement_rate=0.75 + i*0.02,  # Improving trend
            correlation=0.65 + i*0.03,     # Improving trend
            mean_absolute_error=0.35 - i*0.02,  # Improving (decreasing)
            inter_run_variance=0.20 - i*0.01,   # Improving (decreasing)
            num_test_cases=10,
            metadata={"run": i+1}
        )
        tracker.snapshots.append(snapshot)

    # Show trends
    print("Simulated 5 evaluations over 10 days")
    print()

    for metric in ["agreement_rate", "correlation", "mean_absolute_error"]:
        trend = tracker.get_trend(metric)
        improving = tracker.is_improving(metric)
        slope = tracker.calculate_trend_slope(metric)

        print(f"{metric}:")
        print(f"  Values:    {[f'{v:.3f}' for v in trend]}")
        print(f"  Slope:     {slope:+.4f}")
        print(f"  Improving: {'✓ Yes' if improving else '✗ No'}")
        print()

    # Show best evaluation
    best = tracker.get_best_evaluation("agreement_rate")
    print(f"Best Evaluation (by agreement rate):")
    print(f"  Timestamp:  {best.timestamp}")
    print(f"  Agreement:  {best.agreement_rate:.2%}")
    print()


async def demo_sensitivity_mock():
    """Demonstrate sensitivity testing with mock data."""
    print("=" * 80)
    print("DEMO: SENSITIVITY TESTING (Mock)")
    print("=" * 80)
    print()

    from sensitivity import generate_prompt_variations
    from metrics import calculate_sensitivity_metrics

    prompt = "Explain the concept of machine learning"

    variations = generate_prompt_variations(prompt)

    print(f"Generated {len(variations)} variations of the prompt:")
    print()

    for i, var in enumerate(variations[:5], 1):  # Show first 5
        print(f"{i}. {var.name:20s}: {var.prompt[:60]}...")

    print(f"... and {len(variations) - 5} more")
    print()

    # Simulate scores (would come from actual evaluation)
    import random
    random.seed(42)
    scores = [4.5 + random.uniform(-0.3, 0.3) for _ in variations]

    sensitivity = calculate_sensitivity_metrics(scores)

    print("Sensitivity Metrics:")
    print(f"  Variance:              {sensitivity['variance']:.4f}")
    print(f"  Std Dev:               {sensitivity['std_dev']:.4f}")
    print(f"  Coefficient of Var:    {sensitivity['coefficient_of_variation']:.2%}")
    print(f"  Range:                 {sensitivity['range']:.4f}")
    print(f"  Max Deviation:         {sensitivity['max_deviation']:.4f}")
    print(f"  Stability:             {'✓ STABLE' if sensitivity['is_stable'] else '✗ UNSTABLE'}")
    print()


def main():
    """Run all demos."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "MAESTRO EVALUATION FRAMEWORK DEMO" + " " * 25 + "║")
    print("╚" + "═" * 78 + "╝")
    print()

    demos = [
        ("Test Suite", demo_test_suite, False),
        ("Agreement Metrics", demo_metrics, False),
        ("KPI Dashboard", demo_kpis, False),
        ("Evaluation Tracking", demo_tracking, False),
        ("Sensitivity Testing (Mock)", demo_sensitivity_mock, True),
        ("Baseline Evaluation (1 test)", demo_baseline_quick, True),
    ]

    for i, (name, func, is_async) in enumerate(demos, 1):
        print(f"\n[{i}/{len(demos)}] {name}")
        print()

        if is_async:
            asyncio.run(func())
        else:
            func()

        if i < len(demos):
            input("\nPress Enter to continue to next demo...")

    print()
    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. Run 'python baseline.py' for full baseline evaluation")
    print("  2. Run 'python evaluation_pipeline.py' for complete pipeline")
    print("  3. Run 'python sensitivity.py \"your prompt\"' for sensitivity testing")
    print("  4. See IMPLEMENTATION.md for complete documentation")
    print()


if __name__ == "__main__":
    main()
