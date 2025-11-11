# Maestro: AI Executive Assistant

A unified, privacy-first AI platform combining advanced conversational intelligence with deep workflow automation.

## 🚀 Current Status: Phase 1 Implementation

**Phase 1: Local-First Knowledge Core** - Privacy-preserving RAG with Obsidian vault integration

---

## Features

### Maestro AI Assistant (Phase 1)
- **Privacy-First RAG**: Local-first knowledge base using Ollama for sensitive data
- **Obsidian Integration**: Deep integration with Obsidian markdown vaults
- **Graph-Aware Search**: Understands wikilinks, backlinks, and tags
- **Task Management**: Built-in task tracking and management API
- **RESTful API**: Complete FastAPI backend with OpenAPI docs
- **Docker Stack**: Fully containerized with PostgreSQL and Ollama
- **Multi-LLM Ready**: Architecture prepared for Claude and Gemini integration (Phase 2+)

### Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/lordmuffin/Maestro.git
cd Maestro
cp .env.example .env
# Edit .env with your settings (set passwords, API keys)

# 2. Run first-time setup
chmod +x scripts/setup/first_run.sh
./scripts/setup/first_run.sh

# 3. (Optional) Initialize Ollama for local LLM
chmod +x scripts/setup/init_ollama.sh
./scripts/setup/init_ollama.sh

# 4. Access the system
# - Open WebUI: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

### Architecture

Maestro uses a "Tri-Hybrid" architecture:
- **Data Plane**: Bifurcated local + cloud knowledge base
- **Intelligence Plane**: LangGraph supervisor with specialized worker agents (Phase 3)
- **Abstraction Plane**: Unified EA Skills framework (Phase 4)

#### Phase 1 Components
```
┌─────────────────────────────────────────┐
│         Open WebUI Frontend             │
│      (http://localhost:3000)            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      FastAPI Backend (Port 8000)        │
│  ┌──────────────────────────────────┐   │
│  │    ObsidianRAG                   │   │
│  │  (Privacy-Preserving Search)     │   │
│  └──────────────────────────────────┘   │
│  ┌──────────────────────────────────┐   │
│  │    Task Management               │   │
│  └──────────────────────────────────┘   │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐         ┌─────▼──────┐
│Postgres│         │   Ollama   │
│Database│         │(Local LLM) │
└────────┘         └────────────┘
```

### API Endpoints

#### RAG (Retrieval-Augmented Generation)
- `POST /api/v1/rag/query` - Query your Obsidian vault
  ```json
  {
    "query": "What are my thoughts on AI?",
    "similarity_top_k": 5
  }
  ```
- `POST /api/v1/rag/index` - Re-index vault
- `GET /api/v1/rag/graph/{file_path}` - Get file graph context (backlinks, outlinks, tags)
- `GET /api/v1/rag/search/tag/{tag}` - Search by tag

#### Task Management
- `GET /api/v1/tasks` - List all tasks
- `POST /api/v1/tasks` - Create new task
- `GET /api/v1/tasks/{id}` - Get specific task
- `PATCH /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task

#### Health & Status
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed component status
- `GET /` - API information

### Development Roadmap

- ✅ **Phase 1** (Weeks 1-6): Local-First Knowledge Core
  - Obsidian RAG integration
  - Docker infrastructure
  - Basic API layer
  - Task management
  - PostgreSQL database

- 🔄 **Phase 2** (Weeks 7-12): Cloud Knowledge Integration
  - Google Drive sync
  - Path mapping service
  - Hybrid RAG (local + cloud)
  - Cloud RAG with Gemini

- 📋 **Phase 3** (Weeks 13-18): Multi-LLM Orchestration
  - LangGraph supervisor agent
  - Claude/Gemini worker integration
  - Multi-LLM routing matrix
  - HITL (Human-in-the-Loop) confirmations

- 📋 **Phase 4** (Weeks 19-24): Platform & Ecosystem
  - Unified EA Skills framework
  - Plugin SDK
  - Skill marketplace
  - Advanced automation

### Project Structure

```
maestro/
├── backend/           # FastAPI backend
│   ├── core/         # Core modules (RAG, models, database)
│   ├── api/          # API routes
│   └── services/     # Business logic services
├── frontend/         # Open WebUI customizations
├── infra/            # Docker infrastructure
│   ├── docker-compose.yml
│   └── docker/       # Dockerfiles
├── scripts/          # Setup and utility scripts
├── data/            # Data directory (gitignored)
│   └── vault/       # Place your Obsidian vault here
└── docs/            # Documentation
```

### License

MIT License - See [LICENSE](LICENSE) file

---

## LLM Comparison Scorecard (Legacy Component)

A comprehensive evaluation framework for comparing LLM models and prompts using automated scoring with Claude as a judge.

## Features

### Core Features
- **Two Evaluation Modes:**
  - **Model-vs-Model (MvM)**: Compare different LLM models (Gemini vs Claude)
  - **Prompt-vs-Prompt (PvP)**: Compare different prompts on the same model
- **File-Based Prompts**: Load prompts from .md/.txt files with support for multiple prompts per file (separated by `---`)
- **Automated Scoring**: Uses Claude as an expert judge to score responses
- **Statistical Analysis**: Supports multiple runs with confidence intervals
- **Weighted Criteria**: Customizable scoring criteria with configurable weights
- **Parallel Execution**: Efficient async API calls for faster evaluations
- **Comprehensive Reports**: Markdown reports with timing analysis and detailed statistics

### 🆕 Enhanced Features (Week 1-2)
- **Golden Test Suite**: 10 validated test cases with human scores for baseline measurement
- **Agreement Metrics**: Judge-human agreement tracking (correlation, MAE, Cohen's kappa)
- **KPI Dashboard**: Comprehensive performance indicators with targets
- **Sensitivity Testing**: Robustness testing across prompt variations
- **Evaluation Pipeline**: Automated end-to-end evaluation workflow
- **Trend Tracking**: Historical analysis and improvement monitoring
- **Enhanced Criteria**: Refined scoring focused on accuracy, quality, and efficiency

> 📖 **See [IMPLEMENTATION.md](IMPLEMENTATION.md) for complete documentation of enhanced features**

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your API keys:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here
```

## Quick Start

### Try the Demo
See all features in action:
```bash
python demo.py
```

### Run Enhanced Evaluation Pipeline
Get comprehensive metrics with the golden test suite:
```bash
# Full evaluation with baseline + sensitivity testing
python evaluation_pipeline.py --model claude-sonnet-4.5 --judge claude-sonnet-4.5

# Just baseline evaluation
python baseline.py --model claude-sonnet-4.5

# Test prompt sensitivity
python sensitivity.py "Explain quantum computing" --model claude-sonnet-4.5

# View evaluation trends
python tracking.py trends
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
- `--prompt-a TEXT`: First prompt (control) - required. Can be a string or path to .md/.txt file
- `--prompt-b TEXT`: Second prompt (challenger) - required. Can be a string or path to .md/.txt file
- `--criteria {general,code}`: Criteria set to use (default: `general`)

**File Support**: Both `--prompt-a` and `--prompt-b` can accept file paths to `.md` or `.txt` files. Files can contain multiple prompts separated by `---` on its own line. When multiple prompts are provided, all combinations will be evaluated.

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

### Using File-Based Prompts

You can now directly provide file paths for prompts instead of using command substitution. This is especially useful for:
- Complex prompts with special characters
- Very long prompts
- Testing multiple prompt variations efficiently

#### Single Prompt Per File

```bash
# Create prompt files
echo "Write a guide for urban gardening" > prompt_a.txt
echo "Write a comprehensive guide for urban gardening with sections on recommended plants and seasonal planning" > prompt_b.txt

# Pass file paths directly
python scorecard.py --mode prompt --model gemini \
  --prompt-a prompt_a.txt \
  --prompt-b prompt_b.txt \
  --runs-per-prompt 3
```

#### Multiple Prompts Per File

Separate multiple prompts in a file using `---` on its own line:

**prompts_a.md:**
```markdown
Write a short story about a robot learning to paint.
---
Explain the concept of machine learning in simple terms.
---
Create a haiku about artificial intelligence.
```

**prompts_b.md:**
```markdown
Write a brief narrative about an AI learning artistic expression.
---
Describe machine learning concepts for beginners.
```

Run all combinations (3 × 2 = 6 comparisons):
```bash
python scorecard.py --mode prompt --model claude \
  --prompt-a prompts_a.md \
  --prompt-b prompts_b.md \
  --runs-per-prompt 3
```

This will automatically:
1. Read all prompts from both files
2. Evaluate all prompt combinations (Prompt A.1 vs B.1, A.1 vs B.2, A.2 vs B.1, etc.)
3. Generate a comprehensive report with all comparisons

**Supported file types**: `.md` and `.txt`

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
