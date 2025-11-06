"""
Sensitivity Testing Module for Maestro Evaluation Framework
Tests how sensitive the evaluation system is to prompt variations
"""

import asyncio
from typing import List, Dict
from dataclasses import dataclass

from scorecard import (
    score_response_with_llm,
    call_claude_api,
    call_gemini_api,
    ModelConfig,
    resolve_model,
    TaskType,
    GENERAL_CRITERIA,
    calculate_weighted_average
)
from metrics import calculate_sensitivity_metrics


@dataclass
class PromptVariation:
    """A variation of a prompt for sensitivity testing."""
    name: str
    prompt: str
    description: str


def generate_prompt_variations(base_prompt: str) -> List[PromptVariation]:
    """
    Generate systematic variations of a prompt for sensitivity testing.

    Args:
        base_prompt: The original prompt to vary

    Returns:
        List of PromptVariation objects
    """
    variations = [
        PromptVariation(
            name="original",
            prompt=base_prompt,
            description="Original prompt, unmodified"
        ),
        PromptVariation(
            name="with_period",
            prompt=base_prompt if base_prompt.endswith('.') else base_prompt + ".",
            description="Added period at end"
        ),
        PromptVariation(
            name="semicolon_punctuation",
            prompt=base_prompt.replace(",", ";"),
            description="Changed commas to semicolons"
        ),
        PromptVariation(
            name="normalized_whitespace",
            prompt=" ".join(base_prompt.split()),
            description="Normalized whitespace (single spaces)"
        ),
        PromptVariation(
            name="lowercase",
            prompt=base_prompt.lower(),
            description="Converted to lowercase"
        ),
        PromptVariation(
            name="title_case",
            prompt=base_prompt.title(),
            description="Converted to title case"
        ),
        PromptVariation(
            name="double_spaces",
            prompt=base_prompt.replace(" ", "  "),
            description="Doubled all spaces"
        ),
        PromptVariation(
            name="please_prefix",
            prompt=f"Please {base_prompt[0].lower()}{base_prompt[1:]}",
            description="Added 'Please' prefix"
        ),
        PromptVariation(
            name="kindly_prefix",
            prompt=f"Kindly {base_prompt[0].lower()}{base_prompt[1:]}",
            description="Added 'Kindly' prefix"
        ),
        PromptVariation(
            name="question_mark",
            prompt=base_prompt.rstrip('.!?') + "?",
            description="Changed punctuation to question mark"
        )
    ]

    # Remove duplicates (e.g., if original already has period)
    unique_variations = []
    seen_prompts = set()

    for var in variations:
        if var.prompt not in seen_prompts:
            unique_variations.append(var)
            seen_prompts.add(var.prompt)

    return unique_variations


async def test_prompt_sensitivity(
    base_prompt: str,
    model_identifier: str = "claude-sonnet-4.5",
    judge_identifier: str = "claude-sonnet-4.5",
    task_type: TaskType = TaskType.GENERAL
) -> Dict:
    """
    Test sensitivity to prompt variations.

    Args:
        base_prompt: The prompt to test
        model_identifier: Model to generate responses
        judge_identifier: Model to judge responses
        task_type: Type of task (GENERAL or CODE)

    Returns:
        Dictionary with sensitivity test results
    """
    model_config = resolve_model(model_identifier)
    judge_model_config = resolve_model(judge_identifier)

    # Select API function and criteria
    api_function = call_claude_api if model_config.provider == 'claude' else call_gemini_api
    criteria = GENERAL_CRITERIA

    print(f"Testing prompt sensitivity...")
    print(f"Model: {model_config.display_name}")
    print(f"Judge: {judge_model_config.display_name}")
    print(f"Base prompt: {base_prompt[:80]}...")
    print()

    # Generate variations
    variations = generate_prompt_variations(base_prompt)
    print(f"Testing {len(variations)} variations...")
    print()

    # Test each variation
    results = []

    for i, variation in enumerate(variations, 1):
        print(f"  [{i}/{len(variations)}] Testing '{variation.name}'...")

        # Generate response
        response, _ = await api_function(
            variation.prompt,
            f"sensitivity-{variation.name}",
            model_config
        )

        # Score response
        scores, _ = await score_response_with_llm(
            variation.prompt,
            response,
            task_type,
            criteria,
            f"{model_config.display_name}-{variation.name}",
            judge_model_config
        )

        # Calculate weighted average
        weighted_avg = calculate_weighted_average(scores, criteria)

        results.append({
            "variation_name": variation.name,
            "description": variation.description,
            "prompt": variation.prompt,
            "scores": scores,
            "weighted_average": weighted_avg
        })

        print(f"      Score: {weighted_avg:.2f}")

    print()

    # Calculate sensitivity metrics
    weighted_averages = [r["weighted_average"] for r in results]
    sensitivity = calculate_sensitivity_metrics(weighted_averages)

    # Detailed analysis
    original_score = next((r["weighted_average"] for r in results if r["variation_name"] == "original"), None)

    if original_score:
        max_deviation_from_original = max(abs(r["weighted_average"] - original_score) for r in results)
        avg_deviation_from_original = sum(abs(r["weighted_average"] - original_score) for r in results) / len(results)
    else:
        max_deviation_from_original = 0.0
        avg_deviation_from_original = 0.0

    return {
        "base_prompt": base_prompt,
        "model": model_config.display_name,
        "judge": judge_model_config.display_name,
        "num_variations": len(variations),
        "results": results,
        "sensitivity_metrics": sensitivity,
        "original_score": original_score,
        "max_deviation_from_original": max_deviation_from_original,
        "avg_deviation_from_original": avg_deviation_from_original
    }


def format_sensitivity_report(test_results: Dict) -> str:
    """Format sensitivity test results as readable report."""
    lines = [
        "",
        "=" * 80,
        "PROMPT SENSITIVITY TEST REPORT",
        "=" * 80,
        "",
        f"Model: {test_results['model']}",
        f"Judge: {test_results['judge']}",
        f"Variations Tested: {test_results['num_variations']}",
        "",
        f"Base Prompt:",
        f"  {test_results['base_prompt']}",
        "",
        "📊 SENSITIVITY METRICS:",
    ]

    metrics = test_results['sensitivity_metrics']
    lines.extend([
        f"  Variance:                  {metrics['variance']:.4f}",
        f"  Standard Deviation:        {metrics['std_dev']:.4f}",
        f"  Coefficient of Variation:  {metrics['coefficient_of_variation']:.2%}",
        f"  Score Range:               {metrics['range']:.4f}",
        f"  Max Deviation:             {metrics['max_deviation']:.4f}",
        f"  Stability:                 {'✓ STABLE' if metrics['is_stable'] else '✗ UNSTABLE'}",
        "",
        "📈 DEVIATION FROM ORIGINAL:",
        f"  Original Score:            {test_results['original_score']:.4f}",
        f"  Max Deviation:             {test_results['max_deviation_from_original']:.4f}",
        f"  Avg Deviation:             {test_results['avg_deviation_from_original']:.4f}",
        "",
        "📋 DETAILED RESULTS:",
        ""
    ])

    # Sort results by score for better readability
    sorted_results = sorted(test_results['results'], key=lambda x: x['weighted_average'], reverse=True)

    lines.append("| Rank | Variation | Score | Deviation | Description |")
    lines.append("|------|-----------|-------|-----------|-------------|")

    original_score = test_results['original_score']
    for i, result in enumerate(sorted_results, 1):
        deviation = result['weighted_average'] - original_score if original_score else 0.0
        deviation_str = f"{deviation:+.3f}" if deviation != 0 else " 0.000"

        lines.append(
            f"| {i:4d} | {result['variation_name']:<20.20s} | {result['weighted_average']:5.3f} | {deviation_str:>9s} | {result['description']:<30.30s} |"
        )

    lines.append("")
    lines.append("🎯 ASSESSMENT:")

    if metrics['is_stable']:
        lines.append("  ✓ System shows good stability across prompt variations")
        lines.append(f"    - Variance ({metrics['variance']:.4f}) is below threshold (0.1)")
        lines.append(f"    - CV ({metrics['coefficient_of_variation']:.2%}) is below 10%")
    else:
        lines.append("  ✗ System shows instability across prompt variations")
        lines.append("    This suggests the judge is sensitive to minor prompt changes")
        lines.append("    Recommendations:")
        lines.append("      • Review judge prompt for clarity")
        lines.append("      • Consider using temperature=0 for more deterministic scoring")
        lines.append("      • Add more specific scoring guidelines")

    if test_results['max_deviation_from_original'] > 0.5:
        lines.append("")
        lines.append("  ⚠ Warning: Large deviations detected!")
        lines.append(f"    Max deviation from original: {test_results['max_deviation_from_original']:.3f} points")
        lines.append("    Some variations produced significantly different scores")

    lines.append("")
    lines.append("=" * 80)
    lines.append("")

    return "\n".join(lines)


async def test_multiple_prompts(
    prompts: List[str],
    model_identifier: str = "claude-sonnet-4.5",
    judge_identifier: str = "claude-sonnet-4.5"
) -> Dict:
    """
    Test sensitivity across multiple prompts.

    Args:
        prompts: List of prompts to test
        model_identifier: Model to generate responses
        judge_identifier: Model to judge responses

    Returns:
        Dictionary with aggregated results
    """
    print(f"Testing sensitivity across {len(prompts)} prompts...")
    print()

    all_results = []

    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] Testing prompt: {prompt[:80]}...")
        result = await test_prompt_sensitivity(prompt, model_identifier, judge_identifier)
        all_results.append(result)
        print()

    # Calculate aggregate statistics
    import numpy as np

    all_variances = [r['sensitivity_metrics']['variance'] for r in all_results]
    all_cvs = [r['sensitivity_metrics']['coefficient_of_variation'] for r in all_results]
    all_stable = [r['sensitivity_metrics']['is_stable'] for r in all_results]

    aggregate = {
        "num_prompts_tested": len(prompts),
        "avg_variance": np.mean(all_variances),
        "avg_cv": np.mean(all_cvs),
        "stability_rate": np.mean(all_stable),
        "individual_results": all_results
    }

    return aggregate


async def main():
    """Run sensitivity tests."""
    import argparse

    parser = argparse.ArgumentParser(description='Test prompt sensitivity')
    parser.add_argument('prompt', type=str, help='Prompt to test')
    parser.add_argument('--model', type=str, default='claude-sonnet-4.5',
                        help='Model to test (default: claude-sonnet-4.5)')
    parser.add_argument('--judge', type=str, default='claude-sonnet-4.5',
                        help='Judge model (default: claude-sonnet-4.5)')

    args = parser.parse_args()

    # Run sensitivity test
    results = await test_prompt_sensitivity(
        args.prompt,
        model_identifier=args.model,
        judge_identifier=args.judge
    )

    # Display report
    print(format_sensitivity_report(results))


if __name__ == "__main__":
    asyncio.run(main())
