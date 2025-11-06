"""
Baseline Measurement System for Maestro Evaluation Framework
Establishes baseline measurements and tracks improvements
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict

from test_cases import TestCase, GOLDEN_TEST_SUITE, TestCategory
from metrics import calculate_agreement, AgreementMetrics
from scorecard import (
    score_response_with_llm,
    call_claude_api,
    call_gemini_api,
    ModelConfig,
    resolve_model,
    TaskType,
    GENERAL_CRITERIA,
    CODE_CRITERIA,
    calculate_weighted_average
)


@dataclass
class BaselineResult:
    """Result from baseline evaluation of a single test case."""
    test_case_id: str
    category: str
    difficulty: str
    llm_scores: Dict[str, float]
    human_scores: Dict[str, float]
    weighted_avg_llm: float
    weighted_avg_human: float
    agreement_metrics: Dict[str, float]
    timestamp: str


@dataclass
class BaselineReport:
    """Complete baseline evaluation report."""
    timestamp: str
    model_config: Dict[str, str]
    judge_config: Dict[str, str]
    total_test_cases: int
    test_results: List[Dict]
    aggregate_metrics: Dict[str, float]
    category_metrics: Dict[str, Dict[str, float]]
    criterion_metrics: Dict[str, float]


async def evaluate_single_test_case(
    test_case: TestCase,
    model_config: ModelConfig,
    judge_model_config: ModelConfig
) -> BaselineResult:
    """
    Evaluate a single test case and compare with human scores.

    Args:
        test_case: TestCase to evaluate
        model_config: Model configuration for generating response
        judge_model_config: Model configuration for judging

    Returns:
        BaselineResult with scores and agreement metrics
    """
    # Select API function based on provider
    api_function = call_claude_api if model_config.provider == 'claude' else call_gemini_api

    # Determine task type and criteria
    task_type = TaskType.CODE if test_case.category == TestCategory.CODE else TaskType.GENERAL
    criteria = CODE_CRITERIA if task_type == TaskType.CODE else GENERAL_CRITERIA

    # Generate response
    response, _ = await api_function(test_case.prompt, f"baseline-{test_case.id}", model_config)

    # Score the response
    llm_scores, _ = await score_response_with_llm(
        test_case.prompt,
        response,
        task_type,
        criteria,
        f"{model_config.display_name}-{test_case.id}",
        judge_model_config
    )

    # Calculate weighted averages
    weighted_avg_llm = calculate_weighted_average(llm_scores, criteria)
    weighted_avg_human = calculate_weighted_average(test_case.human_scores, criteria)

    # Calculate agreement metrics
    try:
        agreement = calculate_agreement(llm_scores, test_case.human_scores)
        agreement_dict = asdict(agreement)
    except ValueError:
        # If no common criteria, create empty metrics
        agreement_dict = {
            "exact_agreement": 0.0,
            "correlation": 0.0,
            "mean_absolute_error": 0.0,
            "root_mean_square_error": 0.0,
            "cohens_kappa": 0.0,
            "agreement_within_1": 0.0,
            "p_value": 1.0
        }

    return BaselineResult(
        test_case_id=test_case.id,
        category=test_case.category.value,
        difficulty=test_case.difficulty.value,
        llm_scores=llm_scores,
        human_scores=test_case.human_scores,
        weighted_avg_llm=weighted_avg_llm,
        weighted_avg_human=weighted_avg_human,
        agreement_metrics=agreement_dict,
        timestamp=datetime.now().isoformat()
    )


async def establish_baseline(
    model_identifier: str = "claude-sonnet-4.5",
    judge_identifier: str = "claude-sonnet-4.5",
    test_cases: List[TestCase] = None,
    max_concurrent: int = 3
) -> BaselineReport:
    """
    Run all test cases through evaluation to establish baseline.

    Args:
        model_identifier: Model to test (default: Claude Sonnet 4.5)
        judge_identifier: Model to use as judge (default: Claude Sonnet 4.5)
        test_cases: List of test cases (default: GOLDEN_TEST_SUITE)
        max_concurrent: Maximum concurrent evaluations

    Returns:
        BaselineReport with complete results
    """
    if test_cases is None:
        test_cases = GOLDEN_TEST_SUITE

    model_config = resolve_model(model_identifier)
    judge_model_config = resolve_model(judge_identifier)

    print(f"Establishing baseline with {len(test_cases)} test cases...")
    print(f"Model: {model_config.display_name}")
    print(f"Judge: {judge_model_config.display_name}")
    print()

    # Evaluate test cases with concurrency limit
    semaphore = asyncio.Semaphore(max_concurrent)

    async def evaluate_with_limit(tc: TestCase) -> BaselineResult:
        async with semaphore:
            print(f"  [{tc.id}] {tc.category.value} - {tc.difficulty.value}")
            result = await evaluate_single_test_case(tc, model_config, judge_model_config)
            print(f"  [{tc.id}] ✓ Agreement: {result.agreement_metrics['exact_agreement']:.2%}")
            return result

    tasks = [evaluate_with_limit(tc) for tc in test_cases]
    results = await asyncio.gather(*tasks)

    print()
    print("Calculating aggregate metrics...")

    # Build results structure
    test_results = []
    for result in results:
        test_results.append({
            "id": result.test_case_id,
            "category": result.category,
            "difficulty": result.difficulty,
            "llm_scores": result.llm_scores,
            "human_scores": result.human_scores,
            "weighted_avg_llm": result.weighted_avg_llm,
            "weighted_avg_human": result.weighted_avg_human,
            "agreement_rate": result.agreement_metrics["exact_agreement"]
        })

    # Calculate aggregate metrics
    from metrics import (
        calculate_overall_agreement,
        calculate_category_agreement,
        calculate_criterion_agreement
    )

    overall_agreement = calculate_overall_agreement(test_results)

    # Calculate correlation across all test cases
    import numpy as np
    llm_avgs = [r.weighted_avg_llm for r in results]
    human_avgs = [r.weighted_avg_human for r in results]
    from scipy import stats
    correlation, p_value = stats.pearsonr(llm_avgs, human_avgs)

    # Calculate MAE
    mae = np.mean([abs(l - h) for l, h in zip(llm_avgs, human_avgs)])

    aggregate_metrics = {
        "overall_agreement": overall_agreement,
        "overall_correlation": correlation,
        "correlation_p_value": p_value,
        "mean_absolute_error": mae,
        "average_llm_score": np.mean(llm_avgs),
        "average_human_score": np.mean(human_avgs)
    }

    # Calculate by category
    category_metrics = {}
    for category in TestCategory:
        cat_results = [r for r in test_results if r["category"] == category.value]
        if cat_results:
            cat_agreement = np.mean([r["agreement_rate"] for r in cat_results])
            cat_llm_avg = np.mean([r["weighted_avg_llm"] for r in cat_results])
            cat_human_avg = np.mean([r["weighted_avg_human"] for r in cat_results])

            category_metrics[category.value] = {
                "agreement": cat_agreement,
                "avg_llm_score": cat_llm_avg,
                "avg_human_score": cat_human_avg,
                "count": len(cat_results)
            }

    # Calculate by criterion
    criterion_metrics = calculate_criterion_agreement(test_results)

    # Create report
    report = BaselineReport(
        timestamp=datetime.now().isoformat(),
        model_config={
            "provider": model_config.provider,
            "model_id": model_config.model_id,
            "display_name": model_config.display_name
        },
        judge_config={
            "provider": judge_model_config.provider,
            "model_id": judge_model_config.model_id,
            "display_name": judge_model_config.display_name
        },
        total_test_cases=len(test_cases),
        test_results=test_results,
        aggregate_metrics=aggregate_metrics,
        category_metrics=category_metrics,
        criterion_metrics=criterion_metrics
    )

    return report


def format_baseline_report(report: BaselineReport) -> str:
    """Format baseline report as readable text."""
    lines = [
        "",
        "=" * 80,
        "BASELINE EVALUATION REPORT",
        "=" * 80,
        "",
        f"Timestamp: {report.timestamp}",
        f"Model: {report.model_config['display_name']} ({report.model_config['model_id']})",
        f"Judge: {report.judge_config['display_name']} ({report.judge_config['model_id']})",
        f"Test Cases: {report.total_test_cases}",
        "",
        "📊 AGGREGATE METRICS:",
        f"  Overall Agreement:     {report.aggregate_metrics['overall_agreement']:.2%}",
        f"  Overall Correlation:   {report.aggregate_metrics['overall_correlation']:.3f} (p={report.aggregate_metrics['correlation_p_value']:.4f})",
        f"  Mean Absolute Error:   {report.aggregate_metrics['mean_absolute_error']:.3f}",
        f"  Avg LLM Score:         {report.aggregate_metrics['average_llm_score']:.2f}",
        f"  Avg Human Score:       {report.aggregate_metrics['average_human_score']:.2f}",
        "",
        "📁 CATEGORY BREAKDOWN:",
    ]

    for category, metrics in sorted(report.category_metrics.items()):
        lines.append(f"  {category}:")
        lines.append(f"    Agreement:    {metrics['agreement']:.2%}")
        lines.append(f"    LLM Avg:      {metrics['avg_llm_score']:.2f}")
        lines.append(f"    Human Avg:    {metrics['avg_human_score']:.2f}")
        lines.append(f"    Count:        {metrics['count']}")

    lines.append("")
    lines.append("📋 CRITERION AGREEMENT:")

    for criterion, agreement in sorted(report.criterion_metrics.items()):
        indicator = "✓" if agreement >= 0.75 else "✗"
        lines.append(f"  {criterion:<30} {agreement:>6.2%}  {indicator}")

    lines.append("")

    # Assessment
    lines.append("🎯 ASSESSMENT:")

    if report.aggregate_metrics['overall_agreement'] >= 0.80:
        lines.append("  ✓ Overall agreement meets target (≥80%)")
    else:
        lines.append(f"  ✗ Overall agreement below target: {report.aggregate_metrics['overall_agreement']:.2%} < 80%")

    if report.aggregate_metrics['overall_correlation'] >= 0.70:
        lines.append("  ✓ Correlation is strong (≥0.70)")
    else:
        lines.append(f"  ✗ Correlation is weak: {report.aggregate_metrics['overall_correlation']:.3f} < 0.70")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    return "\n".join(lines)


def save_baseline_report(report: BaselineReport, output_dir: str = "baselines"):
    """
    Save baseline report to JSON file.

    Args:
        report: BaselineReport to save
        output_dir: Directory to save the report (default: "baselines")

    Returns:
        Path to the saved file
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"baseline_{timestamp}.json"
    filepath = output_path / filename

    # Convert to dictionary
    data = {
        "timestamp": report.timestamp,
        "model_config": report.model_config,
        "judge_config": report.judge_config,
        "total_test_cases": report.total_test_cases,
        "test_results": report.test_results,
        "aggregate_metrics": report.aggregate_metrics,
        "category_metrics": report.category_metrics,
        "criterion_metrics": report.criterion_metrics
    }

    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2, default=str)

    # Also save formatted report
    text_filepath = output_path / f"baseline_{timestamp}.txt"
    with open(text_filepath, 'w') as f:
        f.write(format_baseline_report(report))

    print(f"Baseline saved to: {filepath}")
    print(f"Report saved to: {text_filepath}")

    return filepath


async def main():
    """Run baseline evaluation."""
    import argparse

    parser = argparse.ArgumentParser(description='Establish baseline measurements')
    parser.add_argument('--model', type=str, default='claude-sonnet-4.5',
                        help='Model to test (default: claude-sonnet-4.5)')
    parser.add_argument('--judge', type=str, default='claude-sonnet-4.5',
                        help='Judge model (default: claude-sonnet-4.5)')
    parser.add_argument('--concurrent', type=int, default=3,
                        help='Max concurrent evaluations (default: 3)')

    args = parser.parse_args()

    # Run baseline establishment
    report = await establish_baseline(
        model_identifier=args.model,
        judge_identifier=args.judge,
        max_concurrent=args.concurrent
    )

    # Display report
    print(format_baseline_report(report))

    # Save report
    save_baseline_report(report)


if __name__ == "__main__":
    asyncio.run(main())
