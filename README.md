# LLM Comparison Scorecard

A comprehensive evaluation framework for comparing LLM models and prompts using automated scoring with Claude as a judge.

## Features

- **Two Evaluation Modes:**
  - **Model-vs-Model (MvM)**: Compare different LLM models (Gemini vs Claude)
  - **Prompt-vs-Prompt (PvP)**: Compare different prompts on the same model
- **Automated Scoring**: Uses Claude as an expert judge to score responses
- **Statistical Analysis**: Supports multiple runs with confidence intervals
- **Weighted Criteria**: Customizable scoring criteria with configurable weights
- **Parallel Execution**: Efficient async API calls for faster evaluations
- **Comprehensive Reports**: Markdown reports with timing analysis and detailed statistics

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install anthropic google-generativeai python-dotenv
```

3. Create a `.env` file with your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## Usage

### Model-vs-Model Comparison (Default Mode)

Compare Gemini and Claude on standard tasks:

```bash
# Single prompt per task type, single run
python scorecard.py

# Multiple prompts per task type
python scorecard.py --num-prompts 5

# Multiple runs for statistical significance
python scorecard.py --runs-per-prompt 5

# Comprehensive evaluation
python scorecard.py --num-prompts 3 --runs-per-prompt 5
```

### Prompt-vs-Prompt Comparison

Compare two different prompts on the same model to determine which performs better:

#### Basic Example

```bash
python scorecard.py \
  --mode prompt \
  --model gemini \
  --prompt-a "Write a guide for urban gardening" \
  --prompt-b "Act as an expert horticulturist. Write a comprehensive guide for urban gardening with sections on: recommended plants, seasonal calendar, common mistakes, vertical solutions, and quick start tips" \
  --criteria general
```

#### With Multiple Runs for Statistical Analysis

```bash
python scorecard.py \
  --mode prompt \
  --model claude \
  --prompt-a "Write a Python function to calculate factorial" \
  --prompt-b "Write a production-ready Python function to calculate factorial with: type hints, docstrings, error handling for negative numbers, and unit tests" \
  --criteria code \
  --runs-per-prompt 5
```

#### Testing on Different Models

```bash
# Test prompts on Gemini
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Explain quantum computing" \
  --prompt-b "Explain quantum computing to a 12-year-old using everyday analogies" \
  --runs-per-prompt 3

# Test the same prompts on Claude
python scorecard.py --mode prompt --model claude \
  --prompt-a "Explain quantum computing" \
  --prompt-b "Explain quantum computing to a 12-year-old using everyday analogies" \
  --runs-per-prompt 3
```

## Command-Line Arguments

### Common Arguments

- `--mode {model,prompt}`: Evaluation mode (default: `model`)
- `--runs-per-prompt N`: Number of times to run each prompt for statistical analysis (default: 1)

### Model-vs-Model Mode Arguments

- `--num-prompts N`: Number of prompts to generate per task type (default: 1)

### Prompt-vs-Prompt Mode Arguments

- `--model {gemini,claude}`: Model to test (required in prompt mode)
- `--prompt-a TEXT`: First prompt (control) - required
- `--prompt-b TEXT`: Second prompt (challenger) - required
- `--criteria {general,code}`: Criteria set to use (default: `general`)

## Scoring Criteria

### General Task Criteria (Equal Weights)
- Accuracy (1.0)
- Clarity & Coherence (1.0)
- Adherence to Prompt (1.0)
- Depth & Insight (1.0)
- Creativity/Style (1.0)
- Usability/Actionability (1.0)

### Code Task Criteria (Weighted)
- Functional Correctness (2.0) - Higher weight
- Adherence to Specs (1.0)
- Efficiency/Performance (1.0)
- Readability & Style (1.0)
- Error Handling/Robustness (2.0) - Higher weight

## Output

All evaluations generate:
1. **Console Output**: Real-time progress and timing information
2. **Markdown Report**: Saved to `reports/YYYY-MM-DD_HH-MM-SS.md`

### Report Contents

#### Model-vs-Model Reports Include:
- Test prompts used
- Criterion-by-criterion comparison
- Weighted averages
- Statistical analysis (if multiple runs)
- Winner determination with margin
- Parallelization efficiency metrics

#### Prompt-vs-Prompt Reports Include:
- Both prompts tested
- Model used
- Criterion-by-criterion comparison
- Difference analysis (Prompt B vs Prompt A)
- Weighted averages
- Statistical analysis (if multiple runs)
- Winner determination with key improvements highlighted
- Recommendations

## Example Use Cases

### 1. Prompt Engineering Workflow

Iteratively improve your prompts:

```bash
# Test baseline
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Write a blog post about AI" \
  --prompt-b "Write an SEO-optimized 800-word blog post about AI for business leaders" \
  --runs-per-prompt 3

# If Prompt B wins, use it as new baseline
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Write an SEO-optimized 800-word blog post about AI for business leaders" \
  --prompt-b "Act as a tech journalist. Write an SEO-optimized 800-word blog post about AI for business leaders. Include: executive summary, 3 key trends, ROI examples, and action items" \
  --runs-per-prompt 3
```

### 2. Model Selection for Production

Determine which model performs best for your specific use case:

```bash
python scorecard.py --num-prompts 10 --runs-per-prompt 5
```

### 3. Persona Testing

Compare different persona instructions:

```bash
python scorecard.py --mode prompt --model claude \
  --prompt-a "Explain machine learning" \
  --prompt-b "You are a patient university professor. Explain machine learning using the Socratic method" \
  --criteria general \
  --runs-per-prompt 5
```

### 4. Format Comparison

Test different output formats:

```bash
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Create a REST API in Python" \
  --prompt-b "Create a REST API in Python. Return ONLY executable code with inline comments. No explanations outside code blocks." \
  --criteria code \
  --runs-per-prompt 3
```

## Advanced Tips

### Statistical Significance

For reliable results, use at least 5 runs:
```bash
--runs-per-prompt 5
```

### Comparing Complex Prompts

When prompts contain special characters or are very long, save them to files:

```bash
# Create prompt files
echo "Your control prompt here" > prompt_a.txt
echo "Your challenger prompt here" > prompt_b.txt

# Use command substitution
python scorecard.py --mode prompt --model gemini \
  --prompt-a "$(cat prompt_a.txt)" \
  --prompt-b "$(cat prompt_b.txt)" \
  --runs-per-prompt 5
```

On Windows (PowerShell):
```powershell
python scorecard.py --mode prompt --model gemini `
  --prompt-a (Get-Content prompt_a.txt -Raw) `
  --prompt-b (Get-Content prompt_b.txt -Raw) `
  --runs-per-prompt 5
```

### Interpreting Results

- **Margin < 0.1**: Prompts are essentially equivalent
- **Margin 0.1-0.3**: Modest improvement
- **Margin 0.3-0.5**: Significant improvement
- **Margin > 0.5**: Substantial improvement

Pay attention to:
- Standard deviation (lower is more consistent)
- 95% confidence intervals (non-overlapping intervals indicate statistical significance)
- Specific criteria improvements (which aspects improved?)

## Architecture

1. **Evaluation Engine**: Async execution of API calls
2. **Scoring System**: Claude-as-judge with structured criteria
3. **Statistical Analysis**: Mean, std dev, min, max, 95% CI
4. **Report Generation**: Markdown with comprehensive metrics

## Models

- **Gemini**: `gemini-2.5-pro`
- **Claude**: `claude-sonnet-4-5-20250929`
- **Judge**: `claude-sonnet-4-5-20250929`

## License

MIT

## Contributing

Contributions welcome! Areas for improvement:
- Additional criteria sets
- More models (GPT-4, etc.)
- Custom scoring rubrics
- JSON output format
- A/B/C/D testing (3+ prompts)
