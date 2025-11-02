# Scorecard Usage Examples

## Quick Start

### 1. Basic Prompt Comparison (Gemini)

```bash
python scorecard.py \
  --mode prompt \
  --model gemini \
  --prompt-a "Write a guide for urban gardening" \
  --prompt-b "Act as an expert horticulturist. Write a comprehensive guide for urban gardening with clear sections" \
  --criteria general
```

### 2. Code Prompt Comparison (Claude)

```bash
python scorecard.py \
  --mode prompt \
  --model claude \
  --prompt-a "Write a Python function to sort a list" \
  --prompt-b "Write a production-ready Python function to sort a list with type hints, docstrings, error handling, and unit tests" \
  --criteria code \
  --runs-per-prompt 3
```

### 3. Model Comparison (Default Mode)

```bash
python scorecard.py --runs-per-prompt 5
```

## Real-World Scenarios

### Scenario 1: Optimizing Marketing Copy

**Goal**: Find the best prompt for generating product descriptions

```bash
# Test 1: Basic vs Structured
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Write a product description for wireless headphones" \
  --prompt-b "Write a 150-word product description for wireless headphones. Include: headline, 3 key features, emotional appeal, and call-to-action" \
  --runs-per-prompt 3

# Test 2: Add persona (if Test 1's Prompt B won)
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Write a 150-word product description for wireless headphones. Include: headline, 3 key features, emotional appeal, and call-to-action" \
  --prompt-b "You are a creative copywriter. Write a 150-word product description for wireless headphones. Include: catchy headline, 3 key features with benefits, emotional appeal, and strong call-to-action. Use power words." \
  --runs-per-prompt 3
```

### Scenario 2: Code Generation Best Practices

**Goal**: Determine which prompt style generates better code

```bash
# Test: Minimal vs Comprehensive instructions
python scorecard.py --mode prompt --model claude \
  --prompt-a "Create a REST API endpoint for user authentication" \
  --prompt-b "Create a REST API endpoint for user authentication in Python using Flask. Requirements: JWT tokens, password hashing with bcrypt, rate limiting, input validation, proper HTTP status codes, and comprehensive error handling. Include docstrings and type hints." \
  --criteria code \
  --runs-per-prompt 5
```

### Scenario 3: Educational Content

**Goal**: Test different teaching approaches

```bash
# Test: Direct explanation vs Socratic method
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Explain machine learning to a beginner" \
  --prompt-b "Using the Socratic method with concrete examples, guide a beginner through understanding machine learning. Start with familiar concepts like recipe recommendations, then build up to the formal definition." \
  --runs-per-prompt 5
```

### Scenario 4: Technical Documentation

**Goal**: Compare documentation prompt styles

```bash
# Test: Standard vs User-focused
python scorecard.py --mode prompt --model claude \
  --prompt-a "Write API documentation for a payment processing endpoint" \
  --prompt-b "Write user-friendly API documentation for a payment processing endpoint. Include: clear description, authentication requirements, request/response examples with explanations, common error codes with solutions, and a complete working example. Format using Markdown." \
  --criteria general \
  --runs-per-prompt 3
```

### Scenario 5: Creative Writing Styles

**Goal**: Test persona effectiveness

```bash
# Test personas
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Write a blog post about time management" \
  --prompt-b "You are a productivity coach who has helped thousands of professionals. Write an engaging blog post about time management with personal anecdotes, actionable tips, and a motivational conclusion" \
  --runs-per-prompt 5
```

## Interpretation Guide

### Understanding the Results

When you receive a report, look at these key metrics:

1. **Weighted Average Difference**
   - < 0.1: No meaningful difference
   - 0.1 - 0.3: Modest improvement, worth testing in production
   - 0.3 - 0.5: Significant improvement, definitely use the better prompt
   - \> 0.5: Substantial improvement, clear winner

2. **Standard Deviation**
   - Low (< 0.2): Consistent results, reliable prompt
   - Medium (0.2 - 0.5): Some variability, consider more runs
   - High (> 0.5): Inconsistent results, prompt may need refinement

3. **Specific Criteria**
   - Look for criteria where one prompt significantly outperforms
   - Example: If Prompt B scores +0.8 on "Adherence to Prompt" but only +0.1 overall, it's more precise but not necessarily better

### Example Report Analysis

```
Prompt A: 4.23
Prompt B: 4.67
Difference: +0.44

Key Improvements:
- Clarity & Coherence: +0.6 (4.0 → 4.6)
- Usability/Actionability: +0.8 (3.8 → 4.6)
```

**Interpretation**: Prompt B is significantly better (+0.44 is substantial). The main improvements are in clarity and usability, suggesting the added structure in Prompt B made outputs more actionable.

## Tips for Effective Comparisons

### 1. Control One Variable at a Time

**Good**:
```
Prompt A: "Explain blockchain"
Prompt B: "Explain blockchain using simple analogies"
```
(Testing: analogies vs no analogies)

**Bad**:
```
Prompt A: "Explain blockchain"
Prompt B: "You are an expert. Explain blockchain to a 5-year-old using analogies in 200 words with examples"
```
(Changed too many variables: persona, audience, analogies, length, examples)

### 2. Use Multiple Runs for Important Decisions

For production prompts:
```bash
--runs-per-prompt 5
```

For quick iterations:
```bash
--runs-per-prompt 2
```

### 3. Test on Both Models

Some prompts work better on different models:

```bash
# Test on Gemini
python scorecard.py --mode prompt --model gemini \
  --prompt-a "..." --prompt-b "..." --runs-per-prompt 3

# Test on Claude
python scorecard.py --mode prompt --model claude \
  --prompt-a "..." --prompt-b "..." --runs-per-prompt 3
```

### 4. Progressive Refinement

Use the winner as the new baseline:

```bash
# Round 1
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Basic prompt" \
  --prompt-b "Basic + persona" \
  --runs-per-prompt 3

# Round 2 (if Prompt B won)
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Basic + persona" \
  --prompt-b "Basic + persona + examples" \
  --runs-per-prompt 3

# Round 3 (if Prompt B won again)
python scorecard.py --mode prompt --model gemini \
  --prompt-a "Basic + persona + examples" \
  --prompt-b "Basic + persona + examples + format constraints" \
  --runs-per-prompt 3
```

## Windows-Specific Commands

For long prompts on Windows PowerShell, use backticks for line continuation:

```powershell
python scorecard.py `
  --mode prompt `
  --model gemini `
  --prompt-a "Your first prompt here" `
  --prompt-b "Your second prompt here" `
  --criteria general `
  --runs-per-prompt 5
```

Or save prompts to files:

```powershell
# Create prompt files
"Your control prompt" | Out-File -Encoding UTF8 prompt_a.txt
"Your challenger prompt" | Out-File -Encoding UTF8 prompt_b.txt

# Run comparison
python scorecard.py --mode prompt --model gemini `
  --prompt-a (Get-Content prompt_a.txt -Raw) `
  --prompt-b (Get-Content prompt_b.txt -Raw) `
  --runs-per-prompt 5
```

## Troubleshooting

### High Variance

If you see high standard deviation:
- Increase `--runs-per-prompt` to 10+
- Check if prompt is too open-ended
- Consider adding more specific constraints

### All Perfect Scores (5.0)

If both prompts get 5.0 on all criteria:
- Task might be too easy
- Try more challenging prompts
- Use code criteria for code tasks

### Unexpected Results

If the "worse" prompt wins:
- Run more iterations (`--runs-per-prompt 10`)
- Check the detailed criteria breakdown
- Review the actual responses in the API logs
- Consider if your intuition about "better" aligns with the scoring criteria
