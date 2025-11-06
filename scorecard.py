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
def read_prompts_from_file(file_path: str) -> List[str]:
    """
    Read prompts from a .md or .txt file.
    Supports multiple prompts separated by '---' on its own line.

    Args:
        file_path: Path to the prompt file (.md or .txt)

    Returns:
        List of prompt strings

    Raises:
        ValueError: If file doesn't exist or has invalid extension
    """
    # Check file extension
    if not (file_path.endswith('.md') or file_path.endswith('.txt')):
        raise ValueError(f"Prompt file must be .md or .txt, got: {file_path}")

    # Check if file exists
    if not os.path.exists(file_path):
        raise ValueError(f"Prompt file not found: {file_path}")

    # Read file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by --- separator (on its own line)
    # Handle various line ending styles
    prompts = []
    parts = content.split('\n---\n')

    for part in parts:
        # Strip leading/trailing whitespace
        prompt = part.strip()
        if prompt:  # Only add non-empty prompts
            prompts.append(prompt)

    if not prompts:
        raise ValueError(f"No prompts found in file: {file_path}")

    return prompts


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='LLM Comparison Scorecard')
    parser.add_argument(
        '--mode',
        type=str,
        choices=['model', 'prompt'],
        default='model',
        help='Evaluation mode: "model" for Model-vs-Model, "prompt" for Prompt-vs-Prompt (default: model)'
    )
    parser.add_argument(
        '--num-prompts',
        type=int,
        default=int(os.getenv('NUM_PROMPTS', '1')),
        help='Number of prompts to generate per task type (default: 1). Only applies in model mode.'
    )
    parser.add_argument(
        '--runs-per-prompt',
        type=int,
        default=int(os.getenv('RUNS_PER_PROMPT', '1')),
        help='Number of times to run each prompt (default: 1)'
    )

    # Model selection arguments
    parser.add_argument(
        '--model1',
        type=str,
        help='First model for Model-vs-Model mode. Accepts model keys (e.g., claude-haiku, gemini-2.5-flash) or provider shortcuts (claude, gemini). Defaults to claude.'
    )
    parser.add_argument(
        '--model2',
        type=str,
        help='Second model for Model-vs-Model mode. Accepts model keys or provider shortcuts. Defaults to gemini.'
    )
    parser.add_argument(
        '--model',
        type=str,
        help='Model for Prompt-vs-Prompt mode. Accepts model keys or provider shortcuts (required when --mode=prompt).'
    )
    parser.add_argument(
        '--judge-model',
        type=str,
        default='claude-sonnet-4.5',
        help='Model to use as judge for scoring (default: claude-sonnet-4.5). Accepts model keys or provider shortcuts.'
    )

    # Prompt-vs-Prompt mode arguments
    parser.add_argument(
        '--prompt-a',
        type=str,
        help='First prompt to test in Prompt-vs-Prompt mode (required when --mode=prompt). Can be a string or path to .md/.txt file. Files can contain multiple prompts separated by "---".'
    )
    parser.add_argument(
        '--prompt-b',
        type=str,
        help='Second prompt to test in Prompt-vs-Prompt mode (required when --mode=prompt). Can be a string or path to .md/.txt file. Files can contain multiple prompts separated by "---".'
    )
    parser.add_argument(
        '--criteria',
        type=str,
        choices=['general', 'code'],
        default='general',
        help='Criteria set to use in Prompt-vs-Prompt mode (default: general)'
    )

    args = parser.parse_args()

    # Set defaults for model-vs-model mode
    if args.mode == 'model':
        if not args.model1:
            args.model1 = 'claude'
        if not args.model2:
            args.model2 = 'gemini'

    # Validate prompt mode requirements
    if args.mode == 'prompt':
        if not args.model:
            parser.error("--model is required when --mode=prompt")
        if not args.prompt_a:
            parser.error("--prompt-a is required when --mode=prompt")
        if not args.prompt_b:
            parser.error("--prompt-b is required when --mode=prompt")

    return args


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


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    provider: str  # 'claude' or 'gemini'
    model_id: str  # Full model identifier (e.g., 'claude-sonnet-4-5-20250929')
    display_name: str  # Human-readable name (e.g., 'Claude Sonnet 4.5')
    max_tokens: int = 4096


# Define available models
AVAILABLE_MODELS = {
    'claude-sonnet-4.5': ModelConfig(
        provider='claude',
        model_id='claude-sonnet-4-5-20250929',
        display_name='Claude Sonnet 4.5',
        max_tokens=4096
    ),
    'claude-haiku': ModelConfig(
        provider='claude',
        model_id='claude-haiku-20250305',
        display_name='Claude Haiku',
        max_tokens=4096
    ),
    'claude-opus': ModelConfig(
        provider='claude',
        model_id='claude-opus-4-5-20250514',
        display_name='Claude Opus',
        max_tokens=4096
    ),
    'gemini-2.5-pro': ModelConfig(
        provider='gemini',
        model_id='gemini-2.5-pro',
        display_name='Gemini 2.5 Pro',
        max_tokens=4096
    ),
    'gemini-2.5-flash': ModelConfig(
        provider='gemini',
        model_id='gemini-2.5-flash',
        display_name='Gemini 2.5 Flash',
        max_tokens=4096
    ),
}

# Default models for provider shortcuts
DEFAULT_MODELS = {
    'claude': 'claude-sonnet-4.5',
    'gemini': 'gemini-2.5-pro',
}


# Define scoring criteria for different task types
# Enhanced criteria with focus on accuracy, quality, and cost efficiency

GENERAL_CRITERIA = [
    # Accuracy/Correctness (Priority #1)
    ScoringCriteria("Factual Accuracy", 2.0),      # Higher weight for correctness
    ScoringCriteria("Logical Consistency", 1.5),

    # Response Quality (Priority #2)
    ScoringCriteria("Clarity & Coherence", 1.0),
    ScoringCriteria("Completeness", 1.0),
    ScoringCriteria("Relevance to Query", 1.5),

    # Practical aspects
    ScoringCriteria("Actionability", 1.0),
    ScoringCriteria("Appropriate Detail Level", 1.0),
]

CODE_CRITERIA = [
    ScoringCriteria("Functional Correctness", 2.0),
    ScoringCriteria("Adherence to Specs", 1.0),
    ScoringCriteria("Efficiency/Performance", 1.0),
    ScoringCriteria("Readability & Style", 1.0),
    ScoringCriteria("Error Handling/Robustness", 2.0),
]

# New: Cost-aware criteria for when efficiency matters
COST_AWARE_CRITERIA = [
    ScoringCriteria("Response Conciseness", 2.0),  # Shorter = cheaper
    ScoringCriteria("First-Try Success", 2.0),     # Avoiding iterations
    ScoringCriteria("Factual Accuracy", 1.5),
    ScoringCriteria("Completeness", 1.0),
]


# Test prompts
TEST_PROMPTS = {
    TaskType.GENERAL: "Write a 500-word executive summary on the long-term impact of decentralized autonomous organizations (DAOs) on corporate governance.",
    TaskType.CODE: "Generate a highly efficient, production-ready Python class called 'ScoreCardAggregator' with a method 'calculate_total_score(results_dict)' that accepts a dictionary of scores (1-5) and returns a weighted average. The weights for 'Accuracy' and 'Functional Correctness' must be 2.0, and all others 1.0. Include docstrings."
}


async def call_gemini_api(prompt: str, task_name: str, model_config: ModelConfig) -> Tuple[str, float]:
    """
    Call Gemini API with the given prompt.
    Returns a tuple of (response text, execution time in seconds).
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found in environment variables")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_config.model_id)

    start_time = time.time()
    # Google API doesn't have native async support, so we run it in an executor
    response = await asyncio.to_thread(model.generate_content, prompt)
    elapsed_time = time.time() - start_time

    # Store timing
    TIMING.api_calls[f"{model_config.display_name} - {task_name}"] = elapsed_time

    return response.text, elapsed_time


async def call_claude_api(prompt: str, task_name: str, model_config: ModelConfig) -> Tuple[str, float]:
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
        model=model_config.model_id,
        max_tokens=model_config.max_tokens,
        messages=[
            {"role": "user", "content": prompt}
        ]
    )
    elapsed_time = time.time() - start_time

    # Store timing
    TIMING.api_calls[f"{model_config.display_name} - {task_name}"] = elapsed_time

    return message.content[0].text, elapsed_time


async def score_response_with_llm(prompt: str, response: str, task_type: TaskType, criteria: List[ScoringCriteria], model_name: str, judge_model_config: ModelConfig) -> Tuple[Dict[str, float], float]:
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
        model=judge_model_config.model_id,
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


def resolve_model(model_identifier: str) -> ModelConfig:
    """
    Resolve a model identifier to a ModelConfig.
    Accepts either a full model key (e.g., 'claude-haiku') or a provider shortcut (e.g., 'claude').

    Args:
        model_identifier: Either a model key from AVAILABLE_MODELS or a provider shortcut from DEFAULT_MODELS

    Returns:
        ModelConfig for the specified model

    Raises:
        ValueError: If the model identifier is not recognized
    """
    # First check if it's a direct model key
    if model_identifier in AVAILABLE_MODELS:
        return AVAILABLE_MODELS[model_identifier]

    # Check if it's a provider shortcut
    if model_identifier in DEFAULT_MODELS:
        default_model_key = DEFAULT_MODELS[model_identifier]
        return AVAILABLE_MODELS[default_model_key]

    # Not found
    available_keys = sorted(list(AVAILABLE_MODELS.keys()) + list(DEFAULT_MODELS.keys()))
    raise ValueError(f"Unknown model identifier '{model_identifier}'. Available options: {', '.join(available_keys)}")


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


def generate_prompt_comparison_report(eval_results: Dict) -> str:
    """
    Generate a comprehensive Markdown report comparing two prompts on the same model.
    Includes statistical analysis if multiple runs were performed.
    """
    lines = []

    # Extract data
    model = eval_results["model"]
    criteria = eval_results["criteria"]
    criteria_type = eval_results["criteria_type"]
    prompts = eval_results["prompts"]
    aggregated = eval_results["aggregated"]
    config = eval_results["config"]

    # Header
    lines.append("# Prompt Comparison Report")
    lines.append("")
    lines.append(f"**Model Tested:** {model}")
    lines.append(f"**Criteria Set:** {criteria_type}")
    lines.append(f"**Configuration:** {config['runs_per_prompt']} runs per prompt")
    lines.append("")

    # Prompts Section
    lines.append("## Prompts Tested")
    lines.append("")
    lines.append("### Prompt A (Control)")
    lines.append(f"> {prompts['Prompt A']}")
    lines.append("")
    lines.append("### Prompt B (Challenger)")
    lines.append(f"> {prompts['Prompt B']}")
    lines.append("")

    # Results Table
    lines.append("## Evaluation Results")
    lines.append("")
    lines.append("| Criterion | Weight | Prompt A | Prompt B | Difference |")
    lines.append("|-----------|--------|----------|----------|------------|")

    prompt_a_scores = aggregated.get("Prompt A", {})
    prompt_b_scores = aggregated.get("Prompt B", {})

    for criterion in criteria:
        score_a = prompt_a_scores.get(criterion.name, 0)
        score_b = prompt_b_scores.get(criterion.name, 0)
        diff = score_b - score_a
        diff_str = f"{diff:+.2f}"
        lines.append(f"| {criterion.name} | {criterion.weight:.1f} | {score_a:.2f} | {score_b:.2f} | {diff_str} |")

    # Calculate weighted averages
    avg_a = calculate_weighted_average(prompt_a_scores, criteria)
    avg_b = calculate_weighted_average(prompt_b_scores, criteria)
    diff_avg = avg_b - avg_a
    diff_avg_str = f"{diff_avg:+.2f}"

    lines.append(f"| **Weighted Average** | - | **{avg_a:.2f}** | **{avg_b:.2f}** | **{diff_avg_str}** |")
    lines.append("")

    # Statistical Analysis (if multiple runs)
    if config['runs_per_prompt'] > 1:
        lines.append("## Statistical Analysis")
        lines.append("")
        lines.append("*Statistics across multiple runs*")
        lines.append("")

        detailed = eval_results["detailed"]

        for prompt_label in ["Prompt A", "Prompt B"]:
            lines.append(f"### {prompt_label}")
            lines.append("")

            runs = detailed[prompt_label]
            if runs:
                _, stats = aggregate_scores(runs)

                lines.append("| Criterion | Mean | Std Dev | Min | Max | 95% CI |")
                lines.append("|-----------|------|---------|-----|-----|--------|")

                for criterion in criteria:
                    if criterion.name in stats:
                        s = stats[criterion.name]
                        ci_str = f"[{s['ci_lower']:.2f}, {s['ci_upper']:.2f}]"
                        lines.append(f"| {criterion.name} | {s['mean']:.2f} | {s['std_dev']:.2f} | {s['min']:.2f} | {s['max']:.2f} | {ci_str} |")

                lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")

    if avg_b > avg_a:
        winner = "Prompt B"
        margin = avg_b - avg_a
        lines.append(f"**Winner: Prompt B** (margin: +{margin:.2f} points)")
        lines.append("")
        lines.append(f"Prompt B achieved a weighted average score of **{avg_b:.2f}**, outperforming Prompt A's score of {avg_a:.2f}.")
        lines.append("")

        # Highlight areas of improvement
        improvements = []
        for criterion in criteria:
            score_a = prompt_a_scores.get(criterion.name, 0)
            score_b = prompt_b_scores.get(criterion.name, 0)
            if score_b > score_a:
                diff = score_b - score_a
                improvements.append(f"- **{criterion.name}**: +{diff:.2f} ({score_a:.2f} → {score_b:.2f})")

        if improvements:
            lines.append("**Key Improvements:**")
            lines.extend(improvements)

    elif avg_a > avg_b:
        winner = "Prompt A"
        margin = avg_a - avg_b
        lines.append(f"**Winner: Prompt A** (margin: +{margin:.2f} points)")
        lines.append("")
        lines.append(f"Prompt A (control) achieved a weighted average score of **{avg_a:.2f}**, outperforming Prompt B's score of {avg_b:.2f}.")
        lines.append("")
        lines.append("**Recommendation:** The original prompt (Prompt A) performs better. Consider revising Prompt B's approach.")
    else:
        lines.append("**Result: Tie**")
        lines.append("")
        lines.append(f"Both prompts achieved identical weighted average scores of **{avg_a:.2f}**.")

    lines.append("")

    # Recommendation section
    if config['runs_per_prompt'] == 1:
        lines.append("---")
        lines.append("")
        lines.append("*Note: This evaluation was based on a single run per prompt. For more robust results, consider running with `--runs-per-prompt 5` or higher to account for variability.*")

    return "\n".join(lines)


def generate_comparison_report(eval_results: Dict = None) -> str:
    """
    Generate a comprehensive Markdown report comparing two models.
    Includes statistical analysis if eval_results with multiple runs is provided.
    """
    lines = []

    # Get model names from eval_results
    if eval_results and "models" in eval_results:
        model1_name = eval_results["models"]["model1"].display_name
        model2_name = eval_results["models"]["model2"].display_name
    else:
        # Fallback for backwards compatibility
        model1_name = "Model 1"
        model2_name = "Model 2"

    # Header
    lines.append("# LLM Model Comparison Report")
    lines.append("")
    lines.append(f"**Models Evaluated:** {model1_name} vs {model2_name}")
    lines.append("")

    # Configuration info
    if eval_results and "config" in eval_results:
        config = eval_results["config"]
        lines.append(f"**Configuration:** {config['num_prompts']} prompts per task type, {config['runs_per_prompt']} runs per prompt")
        lines.append("")
        if "models" in eval_results:
            lines.append(f"**Judge Model:** {eval_results['models']['judge'].display_name}")
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
    lines.append(f"| Criterion | Weight | {model1_name} | {model2_name} |")
    lines.append("|-----------|--------|--------|--------|")

    for criterion in GENERAL_CRITERIA:
        model1_score = TEST_SCORES[model1_name][TaskType.GENERAL].get(criterion.name, 0)
        model2_score = TEST_SCORES[model2_name][TaskType.GENERAL].get(criterion.name, 0)
        lines.append(f"| {criterion.name} | {criterion.weight:.1f} | {model1_score:.1f} | {model2_score:.1f} |")

    model1_general_avg = calculate_weighted_average(
        TEST_SCORES[model1_name][TaskType.GENERAL],
        GENERAL_CRITERIA
    )
    model2_general_avg = calculate_weighted_average(
        TEST_SCORES[model2_name][TaskType.GENERAL],
        GENERAL_CRITERIA
    )

    lines.append(f"| **Average** | - | **{model1_general_avg:.2f}** | **{model2_general_avg:.2f}** |")
    lines.append("")

    # Code Task Results
    lines.append("## Code Task Results")
    lines.append("")
    lines.append(f"| Criterion | Weight | {model1_name} | {model2_name} |")
    lines.append("|-----------|--------|--------|--------|")

    for criterion in CODE_CRITERIA:
        model1_score = TEST_SCORES[model1_name][TaskType.CODE].get(criterion.name, 0)
        model2_score = TEST_SCORES[model2_name][TaskType.CODE].get(criterion.name, 0)
        lines.append(f"| {criterion.name} | {criterion.weight:.1f} | {model1_score:.1f} | {model2_score:.1f} |")

    model1_code_avg = calculate_weighted_average(
        TEST_SCORES[model1_name][TaskType.CODE],
        CODE_CRITERIA
    )
    model2_code_avg = calculate_weighted_average(
        TEST_SCORES[model2_name][TaskType.CODE],
        CODE_CRITERIA
    )

    lines.append(f"| **Weighted Average** | - | **{model1_code_avg:.2f}** | **{model2_code_avg:.2f}** |")
    lines.append("")

    # Overall Summary
    lines.append("## Overall Summary")
    lines.append("")
    lines.append("| Model | General Tasks | Code Tasks | Overall Average |")
    lines.append("|-------|---------------|------------|-----------------|")

    model1_overall = (model1_general_avg + model1_code_avg) / 2
    model2_overall = (model2_general_avg + model2_code_avg) / 2

    lines.append(f"| **{model1_name}** | {model1_general_avg:.2f} | {model1_code_avg:.2f} | {model1_overall:.2f} |")
    lines.append(f"| **{model2_name}** | {model2_general_avg:.2f} | {model2_code_avg:.2f} | {model2_overall:.2f} |")
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

            for model_name in [model1_name, model2_name]:
                lines.append(f"**{model_name}:**")
                lines.append("")

                # Aggregate all runs across all prompts for this task/model
                all_runs = []
                if model_name in detailed and task_type in detailed[model_name]:
                    for prompt_idx in detailed[model_name][task_type]:
                        all_runs.extend(detailed[model_name][task_type][prompt_idx])

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

    if model1_overall > model2_overall:
        winner = model1_name
        margin = model1_overall - model2_overall
    elif model2_overall > model1_overall:
        winner = model2_name
        margin = model2_overall - model1_overall
    else:
        winner = "Tie"
        margin = 0.0

    if winner == "Tie":
        lines.append("Both models achieved identical overall scores.")
    else:
        lines.append(f"**Winner: {winner}** (margin: +{margin:.2f} points)")
        lines.append("")
        if winner == model1_name:
            if model1_general_avg > model2_general_avg:
                lines.append(f"- {model1_name} excelled in General tasks: {model1_general_avg:.2f} vs {model2_general_avg:.2f}")
            if model2_code_avg > model1_code_avg:
                lines.append(f"- {model2_name} performed better in Code tasks: {model2_code_avg:.2f} vs {model1_code_avg:.2f}")
        else:
            if model2_general_avg > model1_general_avg:
                lines.append(f"- {model2_name} excelled in General tasks: {model2_general_avg:.2f} vs {model1_general_avg:.2f}")
            if model1_code_avg > model2_code_avg:
                lines.append(f"- {model1_name} performed better in Code tasks: {model1_code_avg:.2f} vs {model2_code_avg:.2f}")     

    return "\n".join(lines)


async def run_prompt_evaluation() -> Dict:
    """
    Run Prompt-vs-Prompt evaluation: compare two prompts on the same model.
    Supports file inputs with multiple prompts separated by '---'.
    Returns a nested dictionary with all results and statistics.
    """
    prompt_a_input = CONFIG.prompt_a
    prompt_b_input = CONFIG.prompt_b
    runs_per_prompt = CONFIG.runs_per_prompt
    criteria_type = CONFIG.criteria

    # Resolve models
    model_config = resolve_model(CONFIG.model)
    judge_model_config = resolve_model(CONFIG.judge_model)

    # Select criteria and determine API function
    criteria = GENERAL_CRITERIA if criteria_type == 'general' else CODE_CRITERIA
    task_type = TaskType.GENERAL if criteria_type == 'general' else TaskType.CODE

    # Select the API function based on provider
    if model_config.provider == 'gemini':
        api_function = call_gemini_api
    elif model_config.provider == 'claude':
        api_function = call_claude_api
    else:
        raise ValueError(f"Unknown provider: {model_config.provider}")

    # Parse prompts from files or strings
    def parse_prompt_input(prompt_input: str) -> List[str]:
        """Parse prompt input - either a file path or direct string."""
        # Check if it looks like a file path
        if (prompt_input.endswith('.md') or prompt_input.endswith('.txt')) and os.path.exists(prompt_input):
            print(f"  Loading prompts from file: {prompt_input}")
            prompts = read_prompts_from_file(prompt_input)
            print(f"  Found {len(prompts)} prompt(s) in file")
            return prompts
        else:
            # Treat as direct prompt string
            return [prompt_input]

    prompts_a = parse_prompt_input(prompt_a_input)
    prompts_b = parse_prompt_input(prompt_b_input)

    print(f"Running Prompt-vs-Prompt evaluation...")
    print(f"Model: {model_config.display_name}")
    print(f"Judge: {judge_model_config.display_name}")
    print(f"Criteria: {criteria_type}")
    print(f"Runs per prompt: {runs_per_prompt}")
    print(f"Total comparisons: {len(prompts_a)} × {len(prompts_b)} = {len(prompts_a) * len(prompts_b)}")
    print()

    # Store all comparison results
    all_comparisons = []

    # Run comparisons for all combinations
    comparison_idx = 0
    for a_idx, prompt_a in enumerate(prompts_a):
        for b_idx, prompt_b in enumerate(prompts_b):
            comparison_idx += 1

            # Create labels
            prompt_a_label = f"Prompt A" if len(prompts_a) == 1 else f"Prompt A.{a_idx + 1}"
            prompt_b_label = f"Prompt B" if len(prompts_b) == 1 else f"Prompt B.{b_idx + 1}"

            print(f"=" * 80)
            print(f"Comparison {comparison_idx}/{len(prompts_a) * len(prompts_b)}")
            print(f"=" * 80)
            print()

            # Results structure: {prompt_label: [run1_scores, run2_scores, ...]}
            detailed_results = {
                prompt_a_label: [],
                prompt_b_label: []
            }

            prompts = {
                prompt_a_label: prompt_a,
                prompt_b_label: prompt_b
            }

            # Evaluate both prompts
            for prompt_label, prompt_text in prompts.items():
                print(f"[{prompt_label}]")
                print(f"  Text: {prompt_text[:80]}...")
                print()

                # Run multiple times
                for run_idx in range(runs_per_prompt):
                    if runs_per_prompt > 1:
                        print(f"    Run {run_idx + 1}/{runs_per_prompt}...")

                    # Call the API
                    response, response_time = await api_function(prompt_text, f"{prompt_label}-R{run_idx+1}", model_config)

                    # Score the response
                    scores, score_time = await score_response_with_llm(
                        prompt_text, response, task_type, criteria, f"{model_config.display_name}-{prompt_label}-R{run_idx+1}", judge_model_config
                    )

                    # Store results
                    detailed_results[prompt_label].append(scores)

                    if runs_per_prompt > 1:
                        print(f"      [OK] Completed run {run_idx + 1}")

                print()

            # Calculate aggregated scores for this comparison
            aggregated_scores = {}
            for prompt_label in [prompt_a_label, prompt_b_label]:
                if detailed_results[prompt_label]:
                    mean_scores, _ = aggregate_scores(detailed_results[prompt_label])
                    aggregated_scores[prompt_label] = mean_scores

            # Store this comparison
            all_comparisons.append({
                "aggregated": aggregated_scores,
                "detailed": detailed_results,
                "prompts": prompts,
                "prompt_a_label": prompt_a_label,
                "prompt_b_label": prompt_b_label
            })

    # If only one comparison, return it directly for backward compatibility
    if len(all_comparisons) == 1:
        comparison = all_comparisons[0]
        return {
            "aggregated": comparison["aggregated"],
            "detailed": comparison["detailed"],
            "prompts": comparison["prompts"],
            "model": model_config.display_name,
            "model_config": model_config,
            "judge_config": judge_model_config,
            "criteria": criteria,
            "criteria_type": criteria_type,
            "config": {
                "mode": "prompt",
                "model": model_config.display_name,
                "runs_per_prompt": runs_per_prompt
            }
        }
    else:
        # Multiple comparisons - return all of them
        return {
            "multiple_comparisons": True,
            "comparisons": all_comparisons,
            "model": model_config.display_name,
            "model_config": model_config,
            "judge_config": judge_model_config,
            "criteria": criteria,
            "criteria_type": criteria_type,
            "config": {
                "mode": "prompt",
                "model": model_config.display_name,
                "runs_per_prompt": runs_per_prompt,
                "num_comparisons": len(all_comparisons)
            }
        }


async def run_evaluation() -> Dict:
    """
    Run the actual evaluation by calling both APIs and scoring responses.
    Supports multiple prompts and multiple runs per prompt.
    Returns a nested dictionary with all results and statistics.
    """
    num_prompts = CONFIG.num_prompts
    runs_per_prompt = CONFIG.runs_per_prompt

    # Resolve models
    model1_config = resolve_model(CONFIG.model1)
    model2_config = resolve_model(CONFIG.model2)
    judge_model_config = resolve_model(CONFIG.judge_model)

    model1_name = model1_config.display_name
    model2_name = model2_config.display_name

    print(f"Running LLM evaluations...")
    print(f"Models: {model1_name} vs {model2_name}")
    print(f"Judge: {judge_model_config.display_name}")
    print(f"Configuration: {num_prompts} prompts per task type, {runs_per_prompt} runs per prompt")
    print()

    # Store all prompts used
    all_prompts = {}

    # Results structure: {model: {task_type: {prompt_idx: [run1_scores, run2_scores, ...]}}}
    detailed_results = {
        model1_name: {TaskType.GENERAL: {}, TaskType.CODE: {}},
        model2_name: {TaskType.GENERAL: {}, TaskType.CODE: {}}
    }

    # Determine which API function to use for each model
    def get_api_function(model_config: ModelConfig):
        if model_config.provider == 'gemini':
            return call_gemini_api
        elif model_config.provider == 'claude':
            return call_claude_api
        else:
            raise ValueError(f"Unknown provider: {model_config.provider}")

    model1_api = get_api_function(model1_config)
    model2_api = get_api_function(model2_config)

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
            for model_name in [model1_name, model2_name]:
                detailed_results[model_name][task_type][prompt_idx] = []

            # Run multiple times
            for run_idx in range(runs_per_prompt):
                if runs_per_prompt > 1:
                    print(f"    Run {run_idx + 1}/{runs_per_prompt}...")

                # Call both APIs in parallel
                api_tasks = [
                    model1_api(prompt, f"{task_name}-P{prompt_idx+1}-R{run_idx+1}", model1_config),
                    model2_api(prompt, f"{task_name}-P{prompt_idx+1}-R{run_idx+1}", model2_config)
                ]

                results = await asyncio.gather(*api_tasks)
                model1_response, model1_time = results[0]
                model2_response, model2_time = results[1]

                # Score both responses in parallel
                scoring_tasks = [
                    score_response_with_llm(prompt, model1_response, task_type, criteria, f"{model1_name}-P{prompt_idx+1}-R{run_idx+1}", judge_model_config),
                    score_response_with_llm(prompt, model2_response, task_type, criteria, f"{model2_name}-P{prompt_idx+1}-R{run_idx+1}", judge_model_config)
                ]

                scoring_results = await asyncio.gather(*scoring_tasks)
                model1_scores, model1_score_time = scoring_results[0]
                model2_scores, model2_score_time = scoring_results[1]

                # Store results
                detailed_results[model1_name][task_type][prompt_idx].append(model1_scores)
                detailed_results[model2_name][task_type][prompt_idx].append(model2_scores)

                if runs_per_prompt > 1:
                    print(f"      [OK] Completed run {run_idx + 1}")

        print()

    # Calculate aggregated scores for compatibility with existing code
    aggregated_scores = {
        model1_name: {TaskType.GENERAL: {}, TaskType.CODE: {}},
        model2_name: {TaskType.GENERAL: {}, TaskType.CODE: {}}
    }

    for model_name in [model1_name, model2_name]:
        for task_type in [TaskType.GENERAL, TaskType.CODE]:
            # Collect all scores across all prompts and runs
            all_runs = []
            for prompt_idx in detailed_results[model_name][task_type]:
                all_runs.extend(detailed_results[model_name][task_type][prompt_idx])

            if all_runs:
                mean_scores, _ = aggregate_scores(all_runs)
                aggregated_scores[model_name][task_type] = mean_scores

    # Return both detailed and aggregated results
    return {
        "aggregated": aggregated_scores,
        "detailed": detailed_results,
        "prompts": all_prompts,
        "models": {
            "model1": model1_config,
            "model2": model2_config,
            "judge": judge_model_config
        },
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


def save_report(timing_report: str, comparison_report: str, eval_results: Dict = None) -> str:
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

    # Add model information if available
    if eval_results and "models" in eval_results:
        model1 = eval_results["models"]["model1"]
        model2 = eval_results["models"]["model2"]
        lines.append(f"**Models:** {model1.display_name} ({model1.model_id}) vs {model2.display_name} ({model2.model_id})")
    elif eval_results and "model_config" in eval_results:
        # Prompt-vs-Prompt mode
        model = eval_results["model_config"]
        lines.append(f"**Model:** {model.display_name} ({model.model_id})")

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


def generate_multiple_prompt_comparison_report(eval_results: Dict) -> str:
    """
    Generate a comprehensive report for multiple prompt comparisons.
    """
    lines = []

    # Header
    model = eval_results["model"]
    criteria_type = eval_results["criteria_type"]
    config = eval_results["config"]

    lines.append("# Multiple Prompt Comparison Report")
    lines.append("")
    lines.append(f"**Model Tested:** {model}")
    lines.append(f"**Criteria Set:** {criteria_type}")
    lines.append(f"**Configuration:** {config['runs_per_prompt']} runs per prompt")
    lines.append(f"**Total Comparisons:** {config['num_comparisons']}")
    lines.append("")

    # Generate individual comparison reports
    for idx, comparison in enumerate(eval_results["comparisons"], 1):
        lines.append("---")
        lines.append("")
        lines.append(f"## Comparison {idx}/{config['num_comparisons']}")
        lines.append("")

        # Create a temporary eval_results dict for this comparison
        temp_results = {
            "aggregated": comparison["aggregated"],
            "detailed": comparison["detailed"],
            "prompts": comparison["prompts"],
            "model": model,
            "criteria": eval_results["criteria"],
            "criteria_type": criteria_type,
            "config": {
                "runs_per_prompt": config["runs_per_prompt"]
            }
        }

        # Generate report for this comparison (skip the header)
        comparison_report = generate_prompt_comparison_report(temp_results)
        # Remove the main header from each sub-report
        report_lines = comparison_report.split('\n')
        # Skip the first "# Prompt Comparison Report" line and blank lines until content
        content_start = 0
        for i, line in enumerate(report_lines):
            if line.startswith("## Prompts Tested"):
                content_start = i
                break

        lines.extend(report_lines[content_start:])
        lines.append("")

    return "\n".join(lines)


async def async_main():
    """
    Async main execution function.
    """
    mode = CONFIG.mode
    title = "LLM PROMPT COMPARISON SCORECARD" if mode == 'prompt' else "LLM MODEL COMPARISON SCORECARD"

    print("=" * 80)
    print(title)
    print("=" * 80)
    print()

    try:
        # Run the actual evaluation with overall timing
        global TEST_SCORES
        global EVAL_RESULTS
        overall_start = time.time()

        # Route to appropriate evaluation function
        if mode == 'prompt':
            EVAL_RESULTS = await run_prompt_evaluation()
        else:
            EVAL_RESULTS = await run_evaluation()

        TIMING.overall_time = time.time() - overall_start

        # Extract aggregated scores for backward compatibility
        if "multiple_comparisons" in EVAL_RESULTS and EVAL_RESULTS["multiple_comparisons"]:
            # For multiple comparisons, use the first one for backward compatibility
            TEST_SCORES = EVAL_RESULTS["comparisons"][0]["aggregated"]
        else:
            TEST_SCORES = EVAL_RESULTS["aggregated"]

        # Display timing report
        timing_report = generate_timing_report()
        print(timing_report)

        print("=" * 80)
        print("GENERATING COMPARISON REPORT")
        print("=" * 80)
        print()

        # Generate and display the comparison report (with detailed stats if available)
        if mode == 'prompt':
            if "multiple_comparisons" in EVAL_RESULTS and EVAL_RESULTS["multiple_comparisons"]:
                comparison_report = generate_multiple_prompt_comparison_report(EVAL_RESULTS)
            else:
                comparison_report = generate_prompt_comparison_report(EVAL_RESULTS)
        else:
            comparison_report = generate_comparison_report(EVAL_RESULTS)

        print(comparison_report)
        print()

        # Save report to file
        filepath = save_report(timing_report, comparison_report, EVAL_RESULTS)
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