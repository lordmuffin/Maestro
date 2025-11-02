"""
LLM Comparison Scorecard Script
Compares Gemini and Claude models using weighted scoring criteria
"""

import os
import json
import time
import asyncio
import argparse
import statistics
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any
from enum import Enum
from contextlib import contextmanager
from dotenv import load_dotenv
import anthropic
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()


# Configuration
def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='LLM Comparison Scorecard')
    parser.add_argument(
        '--num-prompts',
        type=int,
        default=int(os.getenv('NUM_PROMPTS', '1')),
        help='Number of prompts to generate per task type (default: 1)'
    )
    parser.add_argument(
        '--runs-per-prompt',
        type=int,
        default=int(os.getenv('RUNS_PER_PROMPT', '1')),
        help='Number of times to run each prompt (default: 1)'
    )
    return parser.parse_args()


CONFIG = parse_arguments()


# Timing data storage
@dataclass
class TimingMetrics:
    """Store timing information for the evaluation."""
    api_calls: Dict[str, float] = field(default_factory=dict)
    scoring_calls: Dict[str, float] = field(default_factory=dict)
    task_times: Dict[str, float] = field(default_factory=dict)
    overall_time: float = 0.0


TIMING = TimingMetrics()


class TaskType(Enum):
    GENERAL = "G"
    CODE = "C"


@dataclass
class ScoringCriteria:
    name: str
    weight: float


# Define scoring criteria for different task types
GENERAL_CRITERIA = [
    ScoringCriteria("Accuracy", 1.0),
    ScoringCriteria("Clarity & Coherence", 1.0),
    ScoringCriteria("Adherence to Prompt", 1.0),
    ScoringCriteria("Depth & Insight", 1.0),
    ScoringCriteria("Creativity/Style", 1.0),
    ScoringCriteria("Usability/Actionability", 1.0),
]

CODE_CRITERIA = [
    ScoringCriteria("Functional Correctness", 2.0),
    ScoringCriteria("Adherence to Specs", 1.0),
    ScoringCriteria("Efficiency/Performance", 1.0),
    ScoringCriteria("Readability & Style", 1.0),
    ScoringCriteria("Error Handling/Robustness", 2.0),
]


# Test prompts
TEST_PROMPTS = {
    TaskType.GENERAL: "Write a 500-word executive summary on the long-term impact of decentralized autonomous organizations (DAOs) on corporate governance.",
    TaskType.CODE: "Generate a highly efficient, production-ready Python class called 'ScoreCardAggregator' with a method 'calculate_total_score(results_dict)' that accepts a dictionary of scores (1-5) and returns a weighted average. The weights for 'Accuracy' and 'Functional Correctness' must be 2.0, and all others 1.0. Include docstrings."
}


# API Configuration
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"
GEMINI_MODEL = "gemini-2.5-pro"


async def call_gemini_api(prompt: str, task_name: str) -> Tuple[str, float]:
    """
    Call Gemini API with the given prompt.
    Returns a tuple of (response text, execution time in seconds).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(GEMINI_MODEL)

    start_time = time.time()
    # Google API doesn't have native async support, so we run it in an executor
    response = await asyncio.to_thread(model.generate_content, prompt)
    elapsed_time = time.time() - start_time

    # Store timing
    TIMING.api_calls[f"Gemini - {task_name}"] = elapsed_time

    return response.text, elapsed_time


async def call_claude_api(prompt: str, task_name: str) -> Tuple[str, float]:
    """
    Call Claude API with the given prompt.
    Returns a tuple of (response text, execution time in seconds).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    start_time = time.time()
    message = await client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    elapsed_time = time.time() - start_time

    # Store timing
    TIMING.api_calls[f"Claude - {task_name}"] = elapsed_time

    return message.content[0].text, elapsed_time


async def score_response_with_llm(prompt: str, response: str, task_type: TaskType, criteria: List[ScoringCriteria], model_name: str) -> Tuple[Dict[str, float], float]:
    """
    Use Claude as a judge to score a response based on the given criteria.
    Returns a tuple of (scores dictionary, execution time in seconds).
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Build the evaluation prompt
    criteria_list = "\n".join([f"- {c.name} (weight: {c.weight})" for c in criteria])
    task_desc = "general task" if task_type == TaskType.GENERAL else "code task"

    judge_prompt = f"""You are an expert evaluator of LLM responses. Your task is to score the following response on a scale of 1-5 for each criterion.

ORIGINAL PROMPT:
{prompt}

RESPONSE TO EVALUATE:
{response}

TASK TYPE: {task_desc}

SCORING CRITERIA (score each from 1-5):
{criteria_list}

For each criterion, provide a score from 1 to 5 where:
- 1 = Poor/Unacceptable
- 2 = Below Average
- 3 = Average/Acceptable
- 4 = Good/Above Average
- 5 = Excellent/Outstanding

Return your evaluation as a JSON object with criterion names as keys and numeric scores as values.
Example format:
{{"Accuracy": 4.5, "Clarity & Coherence": 4.0, ...}}

Provide ONLY the JSON object, no additional text."""

    start_time = time.time()
    message = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": judge_prompt}
        ]
    )
    elapsed_time = time.time() - start_time

    # Store timing
    task_name = "General" if task_type == TaskType.GENERAL else "Code"
    TIMING.scoring_calls[f"{model_name} - {task_name}"] = elapsed_time

    # Parse the JSON response
    response_text = message.content[0].text.strip()

    # Extract JSON if it's wrapped in markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    if response_text.startswith("json"):
        response_text = response_text[4:].strip()

    scores = json.loads(response_text)
    return scores, elapsed_time


async def generate_test_prompts(num_prompts: int, task_type: TaskType) -> List[str]:
    """
    Generate diverse test prompts using Claude.
    Returns a list of prompts for the specified task type.
    """
    if num_prompts == 1:
        # Use the default prompts
        return [TEST_PROMPTS[task_type]]

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

    client = anthropic.AsyncAnthropic(api_key=api_key)

    task_desc = "general writing" if task_type == TaskType.GENERAL else "code generation"
    criteria_list = GENERAL_CRITERIA if task_type == TaskType.GENERAL else CODE_CRITERIA
    criteria_names = [c.name for c in criteria_list]

    prompt = f"""Generate {num_prompts} diverse, challenging test prompts for evaluating LLMs on {task_desc} tasks.

Each prompt should be designed to test different aspects of the model's capabilities.

For {task_desc} tasks, focus on creating prompts that evaluate: {', '.join(criteria_names)}

Requirements:
- Make prompts diverse (different topics, complexity levels, formats)
- Each prompt should be clear and specific
- Prompts should be realistic and practical
- For code tasks: vary the programming language, complexity, and requirements
- For general tasks: vary the topic, length, and style requirements

Return ONLY a JSON array of prompt strings, no additional text.
Example format: ["prompt 1", "prompt 2", "prompt 3"]"""

    message = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

    response_text = message.content[0].text.strip()

    # Extract JSON if it's wrapped in markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])
    if response_text.startswith("json"):
        response_text = response_text[4:].strip()

    prompts = json.loads(response_text)
    return prompts


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate statistical metrics for a list of values.
    Returns mean, std dev, min, max, and 95% confidence interval.
    """
    if not values:
        return {"mean": 0.0, "std_dev": 0.0, "min": 0.0, "max": 0.0, "ci_lower": 0.0, "ci_upper": 0.0}

    if len(values) == 1:
        val = values[0]
        return {
            "mean": val,
            "std_dev": 0.0,
            "min": val,
            "max": val,
            "ci_lower": val,
            "ci_upper": val
        }

    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    min_val = min(values)
    max_val = max(values)

    # Calculate 95% confidence interval (using t-distribution approximation)
    # For simplicity, using 1.96 * std_err for large samples
    std_err = std_dev / (len(values) ** 0.5)
    margin = 1.96 * std_err
    ci_lower = mean - margin
    ci_upper = mean + margin

    return {
        "mean": mean,
        "std_dev": std_dev,
        "min": min_val,
        "max": max_val,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper
    }


def aggregate_scores(score_runs: List[Dict[str, float]]) -> Tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """
    Aggregate scores across multiple runs.
    Returns (mean_scores, statistics_per_criterion).
    """
    if not score_runs:
        return {}, {}

    # Get all criterion names from the first run
    criteria = list(score_runs[0].keys())

    mean_scores = {}
    stats_per_criterion = {}

    for criterion in criteria:
        values = [run[criterion] for run in score_runs if criterion in run]
        stats = calculate_statistics(values)
        mean_scores[criterion] = stats["mean"]
        stats_per_criterion[criterion] = stats

    return mean_scores, stats_per_criterion


# PRE-FILLED TEST DATA (Human evaluator scores based on manual review)
# Scores range from 1-5
# Gemini performs slightly better on General tasks
# Claude performs slightly better on Code tasks
TEST_SCORES = {
    "Gemini": {
        TaskType.GENERAL: {
            "Accuracy": 4.5,
            "Clarity & Coherence": 4.5,
            "Adherence to Prompt": 5.0,
            "Depth & Insight": 4.0,
            "Creativity/Style": 4.5,
            "Usability/Actionability": 4.5,
        },
        TaskType.CODE: {
            "Functional Correctness": 4.0,
            "Adherence to Specs": 4.0,
            "Efficiency/Performance": 4.0,
            "Readability & Style": 4.5,
            "Error Handling/Robustness": 3.5,
        }
    },
    "Claude": {
        TaskType.GENERAL: {
            "Accuracy": 4.5,
            "Clarity & Coherence": 4.5,
            "Adherence to Prompt": 4.5,
            "Depth & Insight": 4.5,
            "Creativity/Style": 4.0,
            "Usability/Actionability": 4.5,
        },
        TaskType.CODE: {
            "Functional Correctness": 5.0,
            "Adherence to Specs": 4.5,
            "Efficiency/Performance": 4.5,
            "Readability & Style": 5.0,
            "Error Handling/Robustness": 4.5,
        }
    }
}

# Global variable to store detailed evaluation results
EVAL_RESULTS = None


def calculate_weighted_average(scores: Dict[str, float], criteria: List[ScoringCriteria]) -> float:
    """
    Calculate weighted average score using the formula:
    weighted_avg = sum(score * weight) / sum(weight)
    """
    total_weighted_score = 0.0
    total_weight = 0.0

    for criterion in criteria:
        if criterion.name in scores:
            total_weighted_score += scores[criterion.name] * criterion.weight
            total_weight += criterion.weight

    return total_weighted_score / total_weight if total_weight > 0 else 0.0


def generate_comparison_report(eval_results: Dict = None) -> str:
    """
    Generate a comprehensive Markdown report comparing Gemini and Claude.
    Includes statistical analysis if eval_results with multiple runs is provided.
    """
    lines = []

    # Header
    lines.append("# LLM Model Comparison Report")
    lines.append("")
    lines.append("**Models Evaluated:** Gemini vs Claude")
    lines.append("")

    # Configuration info
    if eval_results and "config" in eval_results:
        config = eval_results["config"]
        lines.append(f"**Configuration:** {config['num_prompts']} prompts per task type, {config['runs_per_prompt']} runs per prompt")
        lines.append("")

    # Test Prompts Section
    lines.append("## Test Prompts")
    lines.append("")

    if eval_results and "prompts" in eval_results:
        # Show all prompts used
        prompts = eval_results["prompts"]

        lines.append("### General Task (Type G)")
        for idx, prompt in enumerate(prompts[TaskType.GENERAL]):
            if len(prompts[TaskType.GENERAL]) > 1:
                lines.append(f"**Prompt {idx + 1}:**")
            lines.append(f"> {prompt}")
            lines.append("")

        lines.append("### Code Task (Type C)")
        for idx, prompt in enumerate(prompts[TaskType.CODE]):
            if len(prompts[TaskType.CODE]) > 1:
                lines.append(f"**Prompt {idx + 1}:**")
            lines.append(f"> {prompt}")
            lines.append("")
    else:
        # Fallback to default prompts
        lines.append("### General Task (Type G)")
        lines.append(f"> {TEST_PROMPTS[TaskType.GENERAL]}")
        lines.append("")
        lines.append("### Code Task (Type C)")
        lines.append(f"> {TEST_PROMPTS[TaskType.CODE]}")
        lines.append("")

    # General Task Results
    lines.append("## General Task Results")
    lines.append("")
    lines.append("| Criterion | Weight | Gemini | Claude |")
    lines.append("|-----------|--------|--------|--------|")

    for criterion in GENERAL_CRITERIA:
        gemini_score = TEST_SCORES["Gemini"][TaskType.GENERAL].get(criterion.name, 0)
        claude_score = TEST_SCORES["Claude"][TaskType.GENERAL].get(criterion.name, 0)
        lines.append(f"| {criterion.name} | {criterion.weight:.1f} | {gemini_score:.1f} | {claude_score:.1f} |")

    gemini_general_avg = calculate_weighted_average(
        TEST_SCORES["Gemini"][TaskType.GENERAL],
        GENERAL_CRITERIA
    )
    claude_general_avg = calculate_weighted_average(
        TEST_SCORES["Claude"][TaskType.GENERAL],
        GENERAL_CRITERIA
    )

    lines.append(f"| **Average** | - | **{gemini_general_avg:.2f}** | **{claude_general_avg:.2f}** |")
    lines.append("")

    # Code Task Results
    lines.append("## Code Task Results")
    lines.append("")
    lines.append("| Criterion | Weight | Gemini | Claude |")
    lines.append("|-----------|--------|--------|--------|")

    for criterion in CODE_CRITERIA:
        gemini_score = TEST_SCORES["Gemini"][TaskType.CODE].get(criterion.name, 0)
        claude_score = TEST_SCORES["Claude"][TaskType.CODE].get(criterion.name, 0)
        lines.append(f"| {criterion.name} | {criterion.weight:.1f} | {gemini_score:.1f} | {claude_score:.1f} |")

    gemini_code_avg = calculate_weighted_average(
        TEST_SCORES["Gemini"][TaskType.CODE],
        CODE_CRITERIA
    )
    claude_code_avg = calculate_weighted_average(
        TEST_SCORES["Claude"][TaskType.CODE],
        CODE_CRITERIA
    )

    lines.append(f"| **Weighted Average** | - | **{gemini_code_avg:.2f}** | **{claude_code_avg:.2f}** |")
    lines.append("")

    # Overall Summary
    lines.append("## Overall Summary")
    lines.append("")
    lines.append("| Model | General Tasks | Code Tasks | Overall Average |")
    lines.append("|-------|---------------|------------|-----------------|")

    gemini_overall = (gemini_general_avg + gemini_code_avg) / 2
    claude_overall = (claude_general_avg + claude_code_avg) / 2

    lines.append(f"| **Gemini** | {gemini_general_avg:.2f} | {gemini_code_avg:.2f} | {gemini_overall:.2f} |")
    lines.append(f"| **Claude** | {claude_general_avg:.2f} | {claude_code_avg:.2f} | {claude_overall:.2f} |")
    lines.append("")

    # Statistical Analysis (if multiple runs)
    if eval_results and "detailed" in eval_results and eval_results["config"]["runs_per_prompt"] > 1:
        lines.append("## Statistical Analysis")
        lines.append("")
        lines.append("*Statistics across multiple runs per prompt*")
        lines.append("")

        detailed = eval_results["detailed"]
        for task_type in [TaskType.GENERAL, TaskType.CODE]:
            task_name = "General" if task_type == TaskType.GENERAL else "Code"
            criteria = GENERAL_CRITERIA if task_type == TaskType.GENERAL else CODE_CRITERIA

            lines.append(f"### {task_name} Task Statistics")
            lines.append("")

            for model in ["Gemini", "Claude"]:
                lines.append(f"**{model}:**")
                lines.append("")

                # Aggregate all runs across all prompts for this task/model
                all_runs = []
                for prompt_idx in detailed[model][task_type]:
                    all_runs.extend(detailed[model][task_type][prompt_idx])

                if all_runs:
                    _, stats = aggregate_scores(all_runs)

                    lines.append("| Criterion | Mean | Std Dev | Min | Max | 95% CI |")
                    lines.append("|-----------|------|---------|-----|-----|--------|")

                    for criterion in criteria:
                        if criterion.name in stats:
                            s = stats[criterion.name]
                            ci_str = f"[{s['ci_lower']:.2f}, {s['ci_upper']:.2f}]"
                            lines.append(f"| {criterion.name} | {s['mean']:.2f} | {s['std_dev']:.2f} | {s['min']:.2f} | {s['max']:.2f} | {ci_str} |")

                    lines.append("")

            lines.append("")

    # Conclusion
    lines.append("## Conclusion")
    lines.append("")

    if gemini_overall > claude_overall:
        winner = "Gemini"
        margin = gemini_overall - claude_overall
    elif claude_overall > gemini_overall:
        winner = "Claude"
        margin = claude_overall - gemini_overall
    else:
        winner = "Tie"
        margin = 0.0

    if winner == "Tie":
        lines.append("Both models achieved identical overall scores.")
    else:
        lines.append(f"**Winner: {winner}** (margin: +{margin:.2f} points)")
        lines.append("")
        if winner == "Gemini":
            lines.append(f"- Gemini excelled in General tasks: {gemini_general_avg:.2f} vs {claude_general_avg:.2f}")
            if claude_code_avg > gemini_code_avg:
                lines.append(f"- Claude performed better in Code tasks: {claude_code_avg:.2f} vs {gemini_code_avg:.2f}")
        else:
            lines.append(f"- Claude excelled in Code tasks: {claude_code_avg:.2f} vs {gemini_code_avg:.2f}")
            if gemini_general_avg > claude_general_avg:
                lines.append(f"- Gemini performed better in General tasks: {gemini_general_avg:.2f} vs {claude_general_avg:.2f}")     

    return "\n".join(lines)


async def run_evaluation() -> Dict:
    """
    Run the actual evaluation by calling both APIs and scoring responses.
    Supports multiple prompts and multiple runs per prompt.
    Returns a nested dictionary with all results and statistics.
    """
    num_prompts = CONFIG.num_prompts
    runs_per_prompt = CONFIG.runs_per_prompt

    print(f"Running LLM evaluations...")
    print(f"Configuration: {num_prompts} prompts per task type, {runs_per_prompt} runs per prompt")
    print()

    # Store all prompts used
    all_prompts = {}

    # Results structure: {model: {task_type: {prompt_idx: [run1_scores, run2_scores, ...]}}}
    detailed_results = {
        "Gemini": {TaskType.GENERAL: {}, TaskType.CODE: {}},
        "Claude": {TaskType.GENERAL: {}, TaskType.CODE: {}}
    }

    # Generate or use default prompts
    for task_type in [TaskType.GENERAL, TaskType.CODE]:
        task_name = "General" if task_type == TaskType.GENERAL else "Code"
        print(f"[{task_name} Task]")

        if num_prompts > 1:
            print(f"  Generating {num_prompts} diverse prompts...")
            prompts = await generate_test_prompts(num_prompts, task_type)
        else:
            prompts = [TEST_PROMPTS[task_type]]

        all_prompts[task_type] = prompts
        criteria = GENERAL_CRITERIA if task_type == TaskType.GENERAL else CODE_CRITERIA

        # Process each prompt
        for prompt_idx, prompt in enumerate(prompts):
            print(f"\n  Prompt {prompt_idx + 1}/{len(prompts)}: {prompt[:80]}...")

            # Initialize storage for this prompt
            for model in ["Gemini", "Claude"]:
                detailed_results[model][task_type][prompt_idx] = []

            # Run multiple times
            for run_idx in range(runs_per_prompt):
                if runs_per_prompt > 1:
                    print(f"    Run {run_idx + 1}/{runs_per_prompt}...")

                # Call both APIs in parallel
                api_tasks = [
                    call_gemini_api(prompt, f"{task_name}-P{prompt_idx+1}-R{run_idx+1}"),
                    call_claude_api(prompt, f"{task_name}-P{prompt_idx+1}-R{run_idx+1}")
                ]

                results = await asyncio.gather(*api_tasks)
                gemini_response, gemini_time = results[0]
                claude_response, claude_time = results[1]

                # Score both responses in parallel
                scoring_tasks = [
                    score_response_with_llm(prompt, gemini_response, task_type, criteria, f"Gemini-P{prompt_idx+1}-R{run_idx+1}"),
                    score_response_with_llm(prompt, claude_response, task_type, criteria, f"Claude-P{prompt_idx+1}-R{run_idx+1}")
                ]

                scoring_results = await asyncio.gather(*scoring_tasks)
                gemini_scores, gemini_score_time = scoring_results[0]
                claude_scores, claude_score_time = scoring_results[1]

                # Store results
                detailed_results["Gemini"][task_type][prompt_idx].append(gemini_scores)
                detailed_results["Claude"][task_type][prompt_idx].append(claude_scores)

                if runs_per_prompt > 1:
                    print(f"      ✓ Completed run {run_idx + 1}")

        print()

    # Calculate aggregated scores for compatibility with existing code
    aggregated_scores = {
        "Gemini": {TaskType.GENERAL: {}, TaskType.CODE: {}},
        "Claude": {TaskType.GENERAL: {}, TaskType.CODE: {}}
    }

    for model in ["Gemini", "Claude"]:
        for task_type in [TaskType.GENERAL, TaskType.CODE]:
            # Collect all scores across all prompts and runs
            all_runs = []
            for prompt_idx in detailed_results[model][task_type]:
                all_runs.extend(detailed_results[model][task_type][prompt_idx])

            if all_runs:
                mean_scores, _ = aggregate_scores(all_runs)
                aggregated_scores[model][task_type] = mean_scores

    # Return both detailed and aggregated results
    return {
        "aggregated": aggregated_scores,
        "detailed": detailed_results,
        "prompts": all_prompts,
        "config": {
            "num_prompts": num_prompts,
            "runs_per_prompt": runs_per_prompt
        }
    }


def generate_timing_report() -> str:
    """
    Generate a timing report showing execution times.
    """
    lines = []

    lines.append("=" * 80)
    lines.append("TIMING REPORT")
    lines.append("=" * 80)
    lines.append("")

    # API Call Times
    lines.append("API Call Times:")
    lines.append("-" * 40)
    for call_name, duration in sorted(TIMING.api_calls.items()):
        lines.append(f"  {call_name:<30} {duration:>8.2f}s")
    lines.append("")

    # Scoring Times
    lines.append("Scoring Times:")
    lines.append("-" * 40)
    for score_name, duration in sorted(TIMING.scoring_calls.items()):
        lines.append(f"  {score_name:<30} {duration:>8.2f}s")
    lines.append("")

    # Per-Task Times (sum of API + scoring for that task)
    lines.append("Per-Task Total Times:")
    lines.append("-" * 40)
    for task_name, duration in TIMING.task_times.items():
        lines.append(f"  {task_name:<30} {duration:>8.2f}s")
    lines.append("")

    # Overall Time
    lines.append("Overall Execution Time:")
    lines.append("-" * 40)
    lines.append(f"  Total (wall clock)             {TIMING.overall_time:>8.2f}s")
    lines.append("")

    # Calculate speedup
    total_sequential = sum(TIMING.api_calls.values()) + sum(TIMING.scoring_calls.values())
    if TIMING.overall_time > 0:
        speedup = total_sequential / TIMING.overall_time
        lines.append(f"Parallelization Efficiency:")
        lines.append("-" * 40)
        lines.append(f"  Sequential time estimate:      {total_sequential:>8.2f}s")
        lines.append(f"  Parallel time (actual):        {TIMING.overall_time:>8.2f}s")
        lines.append(f"  Speedup factor:                {speedup:>8.2f}x")
        lines.append("")

    return "\n".join(lines)


def save_report(timing_report: str, comparison_report: str) -> str:
    """
    Save the combined report to a timestamped markdown file in the reports directory.
    Returns the path to the saved file.
    """
    # Create reports directory if it doesn't exist
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)

    # Generate timestamp for filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"{timestamp}.md"
    filepath = os.path.join(reports_dir, filename)

    # Build the complete report
    lines = []

    # Header
    lines.append("# LLM Comparison Scorecard Report")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Models:** {GEMINI_MODEL} vs {CLAUDE_MODEL}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Timing Report
    lines.append(timing_report)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Comparison Report
    lines.append(comparison_report)

    # Write to file
    content = "\n".join(lines)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath


async def async_main():
    """
    Async main execution function.
    """
    print("=" * 80)
    print("LLM MODEL COMPARISON SCORECARD")
    print("=" * 80)
    print()

    try:
        # Run the actual evaluation with overall timing
        global TEST_SCORES
        global EVAL_RESULTS
        overall_start = time.time()
        EVAL_RESULTS = await run_evaluation()
        TIMING.overall_time = time.time() - overall_start

        # Extract aggregated scores for backward compatibility
        TEST_SCORES = EVAL_RESULTS["aggregated"]

        # Display timing report
        timing_report = generate_timing_report()
        print(timing_report)

        print("=" * 80)
        print("GENERATING COMPARISON REPORT")
        print("=" * 80)
        print()

        # Generate and display the comparison report (with detailed stats if available)
        comparison_report = generate_comparison_report(EVAL_RESULTS)
        print(comparison_report)
        print()

        # Save report to file
        filepath = save_report(timing_report, comparison_report)
        print("=" * 80)
        print(f"REPORT SAVED: {filepath}")
        print("=" * 80)

    except ValueError as e:
        print(f"ERROR: {e}")
        print()
        print("Please ensure you have:")
        print("1. Created a .env file (copy .env.example)")
        print("2. Added your ANTHROPIC_API_KEY")
        print("3. Added your GOOGLE_API_KEY")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()


def main():
    """
    Main entry point that runs the async main function.
    """
    asyncio.run(async_main())


if __name__ == "__main__":
    main()