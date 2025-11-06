# Maestro Week 1-2 Implementation Guide

## Overview

This document describes the Week 1-2 implementation of enhanced evaluation capabilities for the Maestro LLM evaluation framework. The implementation focuses on three key priorities:

1. **Accuracy/Correctness** - Improved criteria and validation
2. **Response Quality** - Comprehensive metrics and KPI tracking
3. **Cost Efficiency** - Monitoring and optimization

## What's New

### 1. Enhanced Evaluation Criteria

**File: `scorecard.py` (updated)**

We've refined the evaluation criteria to be more specific and weighted according to priorities:

```python
GENERAL_CRITERIA = [
    # Accuracy/Correctness (Priority #1)
    ScoringCriteria("Factual Accuracy", 2.0),      # Higher weight
    ScoringCriteria("Logical Consistency", 1.5),

    # Response Quality (Priority #2)
    ScoringCriteria("Clarity & Coherence", 1.0),
    ScoringCriteria("Completeness", 1.0),
    ScoringCriteria("Relevance to Query", 1.5),

    # Practical aspects
    ScoringCriteria("Actionability", 1.0),
    ScoringCriteria("Appropriate Detail Level", 1.0),
]

# New: Cost-aware criteria
COST_AWARE_CRITERIA = [
    ScoringCriteria("Response Conciseness", 2.0),  # Shorter = cheaper
    ScoringCriteria("First-Try Success", 2.0),     # Avoiding iterations
    ScoringCriteria("Factual Accuracy", 1.5),
    ScoringCriteria("Completeness", 1.0),
]
```

### 2. Golden Test Suite

**File: `test_cases.py` (new)**

A structured test suite with 10 diverse test cases (expandable to 50-100) across multiple categories:

- **Factual Knowledge** - Tests for accurate information retrieval
- **Analytical/Reasoning** - Tests for logical thinking and analysis
- **Creative/Generative** - Tests for creative content generation
- **Code** - Tests for programming tasks
- **Instruction Following** - Tests for precise adherence to instructions
- **Edge Cases** - Tests for handling unusual scenarios

Each test case includes:
- Human-scored baseline for validation
- Expected elements that should be covered
- Difficulty level
- Category classification

**Usage:**
```python
from test_cases import GOLDEN_TEST_SUITE, get_test_cases_by_category, TestCategory

# Get all factual test cases
factual_tests = get_test_cases_by_category(TestCategory.FACTUAL)

# Access test suite statistics
from test_cases import get_test_suite_stats
stats = get_test_suite_stats()
print(stats)  # Shows breakdown by category and difficulty
```

### 3. Baseline Measurement System

**File: `baseline.py` (new)**

Establishes baseline measurements by running test cases through your evaluation system and comparing with human scores.

**Features:**
- Runs all test cases through evaluation
- Calculates judge-human agreement metrics
- Provides category and criterion breakdowns
- Saves results for tracking improvements

**Usage:**
```bash
# Run baseline evaluation
python baseline.py --model claude-sonnet-4.5 --judge claude-sonnet-4.5

# With custom concurrency
python baseline.py --model gemini-2.5-pro --judge claude-opus --concurrent 5
```

**Output:**
- Overall agreement rate
- Correlation with human scores
- Mean absolute error
- Category-specific metrics
- Criterion-specific agreement rates

### 4. Judge-Human Agreement Metrics

**File: `metrics.py` (new)**

Comprehensive metrics for measuring how well the LLM judge agrees with human evaluators.

**Metrics Included:**
- **Exact Agreement** - Percentage within 0.5 points
- **Pearson Correlation** - Linear relationship strength
- **Mean Absolute Error** - Average difference
- **Cohen's Kappa** - Inter-rater reliability
- **Agreement Within 1 Point** - Percentage within 1 point
- **Statistical Significance** - p-value for correlation

**Usage:**
```python
from metrics import calculate_agreement, format_metrics_report

agreement = calculate_agreement(llm_scores, human_scores)
print(format_metrics_report(agreement))
```

**Target Metrics:**
- Exact Agreement: ≥80%
- Correlation: ≥0.70
- Cohen's Kappa: ≥0.60 (good), 0.40-0.60 (fair)

### 5. KPI Tracking System

**File: `kpis.py` (new)**

Defines and tracks Key Performance Indicators for the evaluation system.

**Primary KPIs:**
- Overall Agreement Rate (target: >80%)
- Inter-run Variance (target: <0.2)
- Position Bias Score (target: ~0)

**Quality KPIs:**
- False Positive Rate (target: <10%)
- False Negative Rate (target: <15%)
- Discrimination Power (target: >0.7)

**Efficiency KPIs:**
- Average Evaluation Time
- Cost per Evaluation

**Usage:**
```python
from kpis import MaestroKPIs, KPITracker

# Create KPIs from evaluation
kpis = calculate_kpis_from_evaluation(eval_results, test_results, timing_data, cost_data)

# Display dashboard
print(kpis.to_dashboard())

# Track over time
tracker = KPITracker()
tracker.add_measurement(kpis)
print(tracker.generate_trends_report())
```

### 6. Sensitivity Testing

**File: `sensitivity.py` (new)**

Tests how sensitive the evaluation system is to minor prompt variations.

**Tests Include:**
- Punctuation changes
- Whitespace normalization
- Case variations
- Politeness prefixes
- Formatting differences

**Usage:**
```bash
# Test a single prompt
python sensitivity.py "Explain quantum computing" --model claude-sonnet-4.5

# Programmatic usage
from sensitivity import test_prompt_sensitivity

results = await test_prompt_sensitivity(
    "Explain quantum computing",
    model_identifier="claude-sonnet-4.5",
    judge_identifier="claude-sonnet-4.5"
)
```

**Output:**
- Variance across variations
- Stability assessment
- Detailed breakdown by variation
- Recommendations for improvement

### 7. Automated Evaluation Pipeline

**File: `evaluation_pipeline.py` (new)**

Orchestrates the complete evaluation workflow with all metrics.

**Pipeline Steps:**
1. Baseline evaluation with test suite
2. Sensitivity testing (optional)
3. KPI calculation
4. Summary and recommendations

**Usage:**
```bash
# Run full pipeline
python evaluation_pipeline.py --model claude-sonnet-4.5 --judge claude-sonnet-4.5

# Skip sensitivity testing
python evaluation_pipeline.py --model gemini-2.5-pro --no-sensitivity

# Compare multiple judges
python evaluation_pipeline.py --compare-judges claude-sonnet-4.5 claude-opus gemini-2.5-pro
```

**Programmatic Usage:**
```python
from evaluation_pipeline import MaestroEvaluationPipeline

pipeline = MaestroEvaluationPipeline(
    model_identifier="claude-sonnet-4.5",
    judge_identifier="claude-sonnet-4.5"
)

# Run full evaluation
results = await pipeline.run_full_evaluation(
    include_sensitivity=True,
    max_concurrent=3
)

# Compare judges
comparison = await pipeline.compare_judges(
    judge_identifiers=["claude-sonnet-4.5", "claude-opus", "gemini-2.5-pro"]
)
```

### 8. Evaluation Tracking and Version Control

**File: `tracking.py` (new)**

Tracks evaluations over time and monitors trends.

**Features:**
- Save evaluation snapshots
- Track metrics over time
- Calculate trend slopes
- Compare with baseline
- Export to CSV

**Usage:**
```bash
# View trends
python tracking.py trends --window 10

# Compare baseline vs current
python tracking.py compare

# Export history
python tracking.py export

# Show best evaluation
python tracking.py best
```

**Programmatic Usage:**
```python
from tracking import EvaluationTracker

tracker = EvaluationTracker(storage_dir="evaluations")

# Save evaluation
tracker.save_evaluation(evaluation_result)

# Generate trends report
print(tracker.generate_trends_report(window=10))

# Check if improving
is_improving = tracker.is_improving("agreement_rate", window=5)

# Get best evaluation
best = tracker.get_best_evaluation("agreement_rate")
```

## Quick Start Guide

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment

Ensure your `.env` file has:
```
ANTHROPIC_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here
```

### 3. Run Baseline Evaluation

```bash
python baseline.py --model claude-sonnet-4.5 --judge claude-sonnet-4.5
```

This will:
- Run all test cases from the golden suite
- Compare LLM judge scores with human scores
- Generate comprehensive baseline report
- Save results to `baselines/` directory

### 4. Run Full Pipeline

```bash
python evaluation_pipeline.py --model claude-sonnet-4.5 --judge claude-sonnet-4.5
```

This will:
- Run baseline evaluation
- Perform sensitivity testing
- Calculate all KPIs
- Generate summary and recommendations
- Save results to `evaluations/` directory

### 5. Track Progress Over Time

```bash
# View trends after multiple evaluations
python tracking.py trends --window 10

# Compare first evaluation with latest
python tracking.py compare
```

## Directory Structure

```
Maestro/
├── scorecard.py              # Core evaluation (updated)
├── test_cases.py             # Golden test suite (new)
├── baseline.py               # Baseline measurements (new)
├── metrics.py                # Agreement metrics (new)
├── kpis.py                   # KPI tracking (new)
├── sensitivity.py            # Sensitivity testing (new)
├── evaluation_pipeline.py    # Full pipeline (new)
├── tracking.py               # Result tracking (new)
├── requirements.txt          # Dependencies (updated)
├── baselines/                # Baseline results (created)
├── evaluations/              # Evaluation results (created)
└── reports/                  # Scorecard reports (existing)
```

## Key Metrics and Targets

| Metric | Target | Purpose |
|--------|--------|---------|
| Overall Agreement | ≥80% | Judge matches human evaluation |
| Correlation | ≥0.70 | Scores correlate with human scores |
| Cohen's Kappa | ≥0.60 | Inter-rater reliability |
| Inter-run Variance | <0.2 | Consistency across runs |
| False Positive Rate | <10% | Not marking bad as good |
| False Negative Rate | <15% | Not marking good as bad |
| Discrimination Power | ≥0.7 | Distinguish quality levels |
| Sensitivity Variance | <0.1 | Stable across prompt variations |

## Integration with Existing Workflow

The new modules integrate seamlessly with the existing `scorecard.py`:

### Option 1: Use Original Scorecard (Unchanged)

```bash
python scorecard.py --mode model --model1 claude --model2 gemini
python scorecard.py --mode prompt --model claude --prompt-a "prompt 1" --prompt-b "prompt 2"
```

### Option 2: Use Enhanced Pipeline

```bash
# Get baseline measurements
python baseline.py

# Run full evaluation with all metrics
python evaluation_pipeline.py

# Test sensitivity
python sensitivity.py "Your prompt here"

# Track progress
python tracking.py trends
```

### Option 3: Programmatic Integration

```python
# In your code, import and use new modules
from evaluation_pipeline import MaestroEvaluationPipeline
from tracking import EvaluationTracker

# Run pipeline
pipeline = MaestroEvaluationPipeline()
results = await pipeline.run_full_evaluation()

# Track results
tracker = EvaluationTracker()
tracker.save_evaluation(results)
```

## Next Steps (Week 3-4 Recommendations)

1. **Expand Test Suite** - Add more test cases to reach 50-100
2. **Fine-tune Criteria** - Adjust weights based on baseline results
3. **Implement Cost Tracking** - Add actual API cost calculation
4. **Add Visualization** - Create charts for trend analysis
5. **A/B Testing Framework** - Compare different judge prompts
6. **Automated Regression Testing** - Detect degradation automatically
7. **Multi-judge Consensus** - Combine multiple judges for more reliable scoring

## Troubleshooting

### Issue: Import errors

**Solution:** Install dependencies
```bash
pip install -r requirements.txt
```

### Issue: API rate limits

**Solution:** Reduce concurrency
```bash
python baseline.py --concurrent 1
```

### Issue: Test cases don't match criteria

**Solution:** The baseline system automatically matches criteria from test cases with available criteria in the judge's scores. Only common criteria are compared.

### Issue: Low agreement rates

**Potential causes:**
- Judge prompt needs clarification
- Criteria definitions are ambiguous
- Human scores may need recalibration
- Model limitations

**Solutions:**
- Review judge prompt in `scorecard.py` (line 280-304)
- Add more specific examples in criteria descriptions
- Run sensitivity tests to check stability
- Consider using temperature=0 for deterministic scoring

## Support and Feedback

This implementation provides the foundation for rigorous LLM evaluation. As you use the system:

1. Monitor the KPI dashboard regularly
2. Track trends over time
3. Adjust criteria weights based on results
4. Expand the test suite with real use cases
5. Share feedback to improve the framework

## Summary

Week 1-2 implementation delivers:

✅ Enhanced, granular evaluation criteria
✅ Golden test suite with 10 validated test cases
✅ Baseline measurement system
✅ Comprehensive agreement metrics
✅ KPI tracking and monitoring
✅ Sensitivity testing for robustness
✅ Automated evaluation pipeline
✅ Results tracking and trend analysis

All modules work together to provide a rigorous, measurable approach to LLM evaluation with a focus on accuracy, quality, and efficiency.
