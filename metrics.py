"""
Metrics for Maestro Evaluation Framework
Implements judge-human agreement metrics and statistical analysis
"""

import numpy as np
from typing import Dict, List, Tuple
from scipy import stats
from dataclasses import dataclass


@dataclass
class AgreementMetrics:
    """Container for agreement metrics between LLM judge and human scores."""
    exact_agreement: float  # Percentage with < 0.5 point difference
    correlation: float  # Pearson correlation coefficient
    mean_absolute_error: float  # Average absolute difference
    root_mean_square_error: float  # RMSE
    cohens_kappa: float  # Inter-rater reliability
    agreement_within_1: float  # Percentage within 1 point
    p_value: float  # Statistical significance of correlation


def calculate_agreement(llm_scores: Dict[str, float], human_scores: Dict[str, float]) -> AgreementMetrics:
    """
    Calculate various agreement metrics between LLM judge and human scores.

    Args:
        llm_scores: Dictionary of criterion name -> LLM score
        human_scores: Dictionary of criterion name -> human score

    Returns:
        AgreementMetrics object with all calculated metrics
    """
    # Extract common criteria
    common_criteria = set(llm_scores.keys()) & set(human_scores.keys())

    if not common_criteria:
        raise ValueError("No common criteria found between LLM and human scores")

    llm_values = np.array([llm_scores[c] for c in common_criteria])
    human_values = np.array([human_scores[c] for c in common_criteria])

    # Calculate various metrics
    differences = np.abs(llm_values - human_values)

    exact_agreement = np.mean(differences < 0.5)
    agreement_within_1 = np.mean(differences <= 1.0)
    mae = np.mean(differences)
    rmse = np.sqrt(np.mean(differences ** 2))

    # Pearson correlation
    if len(llm_values) > 1:
        correlation, p_value = stats.pearsonr(llm_values, human_values)
    else:
        correlation = 1.0 if llm_values[0] == human_values[0] else 0.0
        p_value = 1.0

    # Cohen's Kappa (convert continuous scores to ordinal categories)
    kappa = calculate_cohens_kappa(llm_values, human_values)

    return AgreementMetrics(
        exact_agreement=exact_agreement,
        correlation=correlation,
        mean_absolute_error=mae,
        root_mean_square_error=rmse,
        cohens_kappa=kappa,
        agreement_within_1=agreement_within_1,
        p_value=p_value
    )


def calculate_cohens_kappa(scores1: np.ndarray, scores2: np.ndarray, bins: int = 5) -> float:
    """
    Calculate Cohen's Kappa for inter-rater reliability.
    Converts continuous scores to ordinal categories for calculation.

    Args:
        scores1: Array of scores from first rater
        scores2: Array of scores from second rater
        bins: Number of bins to discretize scores (default: 5 for 1-5 scale)

    Returns:
        Cohen's Kappa coefficient (-1 to 1, where 1 is perfect agreement)
    """
    # Convert continuous scores to categories
    categories1 = np.round(scores1).astype(int)
    categories2 = np.round(scores2).astype(int)

    # Build confusion matrix
    max_cat = max(categories1.max(), categories2.max())
    min_cat = min(categories1.min(), categories2.min())

    confusion_matrix = np.zeros((max_cat - min_cat + 1, max_cat - min_cat + 1))

    for c1, c2 in zip(categories1, categories2):
        confusion_matrix[c1 - min_cat, c2 - min_cat] += 1

    n = confusion_matrix.sum()
    if n == 0:
        return 0.0

    # Calculate observed agreement
    po = np.trace(confusion_matrix) / n

    # Calculate expected agreement
    row_sums = confusion_matrix.sum(axis=1)
    col_sums = confusion_matrix.sum(axis=0)
    pe = np.sum(row_sums * col_sums) / (n ** 2)

    # Cohen's Kappa
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0

    kappa = (po - pe) / (1 - pe)
    return kappa


def calculate_overall_agreement(test_results: List[Dict]) -> float:
    """
    Calculate overall agreement rate across multiple test cases.

    Args:
        test_results: List of test result dictionaries containing llm_scores and human_scores

    Returns:
        Overall agreement rate (0.0 to 1.0)
    """
    if not test_results:
        return 0.0

    agreement_scores = []

    for result in test_results:
        if "llm_scores" in result and "human_scores" in result:
            metrics = calculate_agreement(result["llm_scores"], result["human_scores"])
            agreement_scores.append(metrics.exact_agreement)

    return np.mean(agreement_scores) if agreement_scores else 0.0


def calculate_category_agreement(test_results: List[Dict]) -> Dict[str, float]:
    """
    Calculate agreement rates by test case category.

    Args:
        test_results: List of test result dictionaries with category information

    Returns:
        Dictionary mapping category name to agreement rate
    """
    category_results = {}

    for result in test_results:
        if "category" in result:
            category = result["category"]
            if category not in category_results:
                category_results[category] = []

            if "llm_scores" in result and "human_scores" in result:
                metrics = calculate_agreement(result["llm_scores"], result["human_scores"])
                category_results[category].append(metrics.exact_agreement)

    return {cat: np.mean(scores) for cat, scores in category_results.items()}


def calculate_criterion_agreement(test_results: List[Dict]) -> Dict[str, float]:
    """
    Calculate agreement rates by individual criterion.

    Args:
        test_results: List of test result dictionaries

    Returns:
        Dictionary mapping criterion name to agreement rate
    """
    criterion_diffs = {}

    for result in test_results:
        if "llm_scores" in result and "human_scores" in result:
            llm_scores = result["llm_scores"]
            human_scores = result["human_scores"]

            common_criteria = set(llm_scores.keys()) & set(human_scores.keys())

            for criterion in common_criteria:
                if criterion not in criterion_diffs:
                    criterion_diffs[criterion] = []

                diff = abs(llm_scores[criterion] - human_scores[criterion])
                criterion_diffs[criterion].append(diff < 0.5)

    return {crit: np.mean(agreements) for crit, agreements in criterion_diffs.items()}


def calculate_sensitivity_metrics(scores: List[float]) -> Dict[str, float]:
    """
    Calculate sensitivity metrics for prompt variation testing.

    Args:
        scores: List of scores from different prompt variations

    Returns:
        Dictionary with sensitivity metrics
    """
    if not scores or len(scores) < 2:
        return {
            "variance": 0.0,
            "std_dev": 0.0,
            "coefficient_of_variation": 0.0,
            "range": 0.0,
            "max_deviation": 0.0,
            "is_stable": True
        }

    scores_array = np.array(scores)
    mean_score = np.mean(scores_array)
    variance = np.var(scores_array)
    std_dev = np.std(scores_array)
    score_range = np.max(scores_array) - np.min(scores_array)
    max_deviation = np.max(np.abs(scores_array - mean_score))

    # Coefficient of variation (normalized std dev)
    cv = (std_dev / mean_score) if mean_score > 0 else 0.0

    # Consider stable if variance is low (< 0.1) and CV is < 10%
    is_stable = variance < 0.1 and cv < 0.10

    return {
        "variance": float(variance),
        "std_dev": float(std_dev),
        "coefficient_of_variation": float(cv),
        "range": float(score_range),
        "max_deviation": float(max_deviation),
        "is_stable": is_stable
    }


def calculate_discrimination_power(scores: List[Tuple[float, str]]) -> float:
    """
    Calculate the judge's ability to discriminate between quality levels.

    Args:
        scores: List of (score, quality_label) tuples where quality_label is "high" or "low"

    Returns:
        Discrimination power score (0.0 to 1.0, higher is better)
    """
    if not scores or len(scores) < 2:
        return 0.0

    high_scores = [s for s, label in scores if label == "high"]
    low_scores = [s for s, label in scores if label == "low"]

    if not high_scores or not low_scores:
        return 0.0

    # Calculate effect size (Cohen's d)
    mean_high = np.mean(high_scores)
    mean_low = np.mean(low_scores)
    pooled_std = np.sqrt((np.var(high_scores) + np.var(low_scores)) / 2)

    if pooled_std == 0:
        return 1.0 if mean_high > mean_low else 0.0

    cohens_d = (mean_high - mean_low) / pooled_std

    # Normalize to 0-1 range (Cohen's d of 0.8+ is considered large effect)
    discrimination_power = min(abs(cohens_d) / 0.8, 1.0)

    return discrimination_power


def calculate_false_positive_rate(predictions: List[bool], actuals: List[bool]) -> float:
    """
    Calculate false positive rate (marking bad as good).

    Args:
        predictions: List of boolean predictions (True = good, False = bad)
        actuals: List of boolean actual values (True = good, False = bad)

    Returns:
        False positive rate (0.0 to 1.0)
    """
    if not predictions or not actuals or len(predictions) != len(actuals):
        return 0.0

    # False positive: predicted good when actually bad
    actual_negatives = sum(1 for a in actuals if not a)

    if actual_negatives == 0:
        return 0.0

    false_positives = sum(1 for p, a in zip(predictions, actuals) if p and not a)

    return false_positives / actual_negatives


def calculate_false_negative_rate(predictions: List[bool], actuals: List[bool]) -> float:
    """
    Calculate false negative rate (marking good as bad).

    Args:
        predictions: List of boolean predictions (True = good, False = bad)
        actuals: List of boolean actual values (True = good, False = bad)

    Returns:
        False negative rate (0.0 to 1.0)
    """
    if not predictions or not actuals or len(predictions) != len(actuals):
        return 0.0

    # False negative: predicted bad when actually good
    actual_positives = sum(1 for a in actuals if a)

    if actual_positives == 0:
        return 0.0

    false_negatives = sum(1 for p, a in zip(predictions, actuals) if not p and a)

    return false_negatives / actual_positives


def format_metrics_report(metrics: AgreementMetrics) -> str:
    """
    Format agreement metrics as a readable report.

    Args:
        metrics: AgreementMetrics object

    Returns:
        Formatted string report
    """
    return f"""
Agreement Metrics Report:
========================
Exact Agreement (<0.5 pts): {metrics.exact_agreement:.2%}
Agreement Within 1 pt:      {metrics.agreement_within_1:.2%}
Correlation (Pearson):      {metrics.correlation:.3f} (p={metrics.p_value:.4f})
Mean Absolute Error:        {metrics.mean_absolute_error:.3f}
Root Mean Square Error:     {metrics.root_mean_square_error:.3f}
Cohen's Kappa:             {metrics.cohens_kappa:.3f}

Interpretation:
- Exact Agreement: {"✓ Good" if metrics.exact_agreement >= 0.8 else "✗ Needs Improvement"} (target: ≥80%)
- Correlation: {"✓ Strong" if metrics.correlation >= 0.7 else "✗ Weak"} (target: ≥0.70)
- Cohen's Kappa: {"✓ Good" if metrics.cohens_kappa >= 0.6 else "✗ Fair" if metrics.cohens_kappa >= 0.4 else "✗ Poor"}
  (>0.6=good, 0.4-0.6=fair, <0.4=poor)
"""
