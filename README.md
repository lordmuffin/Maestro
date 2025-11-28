# Maestro: AI Executive Assistant

<<<<<<< HEAD
<<<<<<< HEAD
A unified, privacy-first AI platform combining advanced conversational intelligence with deep workflow automation.
=======
A unified, privacy-first AI platform combining advanced conversational intelligence with deep workflow automation and GitOps infrastructure management.
>>>>>>> develop

## 🚀 Current Status: Phase 4 Implementation + Infrastructure Automation

**Phase 4: Platform & Ecosystem** - Unified EA Skills Framework with multi-LLM support
<<<<<<< HEAD
=======
A unified, privacy-first AI platform combining advanced conversational intelligence with deep workflow automation and GitOps infrastructure management.

## 🚀 Current Status: Phase 4 Implementation + Infrastructure Automation

**Phase 4: Platform & Ecosystem** - Unified EA Skills Framework with multi-LLM support
**Infrastructure**: Enterprise-grade GitOps workflows with multi-environment deployment pipeline
>>>>>>> origin/develop
=======
**Infrastructure**: Enterprise-grade GitOps workflows with multi-environment deployment pipeline
>>>>>>> develop

---

## Features

### Maestro AI Assistant (Phases 1-4)
- **Privacy-First RAG**: Local-first knowledge base using Ollama for sensitive data
- **Obsidian Integration**: Deep integration with Obsidian markdown vaults
- **Graph-Aware Search**: Understands wikilinks, backlinks, and tags
- **Cloud Integration**: Google Drive sync and cloud-based RAG with Gemini
- **Path Mapping Service**: Bidirectional mapping between local and cloud files
- **Hybrid RAG**: Query both local vault and cloud files seamlessly
- **Unified EA Skills**: LLM-agnostic skill framework (Phase 4)
- **Multi-LLM Adapters**: Claude, Gemini, and Ollama support (Phase 4)
- **Plugin SDK**: Extensible architecture for custom skills (Phase 4)
- **Open WebUI Pipeline**: Custom pipeline integration (Phase 4)
- **Task Management**: Built-in task tracking and management API
- **RESTful API**: Complete FastAPI backend with OpenAPI docs
- **Docker Stack**: Fully containerized with PostgreSQL and Ollama

<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> develop
### GitOps Infrastructure (New)
- **Multi-Environment Pipeline**: Automated staging → production deployment workflow
- **GitHub Integration**: Automated PR creation for sessions, transcripts, and interviews
- **Branch Name Sanitization**: Robust Git ref validation and filesystem-safe naming
- **Terraform Workflows**: Automated infrastructure validation and deployment
- **Security Scanning**: Integrated tfsec security checks on all infrastructure changes
- **Manual Approval Gates**: Production deployments require explicit approval
- **Drift Detection**: Automated weekly infrastructure drift monitoring

<<<<<<< HEAD
>>>>>>> origin/develop
=======
>>>>>>> develop
### Quick Start

#### Linux/macOS

```bash
# 1. Clone and configure
git clone https://github.com/lordmuffin/Maestro.git
cd Maestro
cp .env.example .env
# Edit .env with your settings (set passwords, API keys, directory paths)

# 2. Configure your Obsidian vault path (recommended)
# In .env, set LOCAL_OBSIDIAN_PATH to your existing vault location
# Example: LOCAL_OBSIDIAN_PATH=/home/yourname/Documents/ObsidianVault

# 3. Run first-time setup
chmod +x scripts/setup/first_run.sh
./scripts/setup/first_run.sh

# 4. (Optional) Initialize Ollama for local LLM
chmod +x scripts/setup/init_ollama.sh
./scripts/setup/init_ollama.sh

# 5. Access the system
# - Open WebUI: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

#### Windows (PowerShell)

```powershell
# 1. Clone and configure
git clone https://github.com/lordmuffin/Maestro.git
cd Maestro
Copy-Item .env.example .env
# Edit .env with your settings (set passwords, API keys, directory paths)
# Use notepad or your preferred editor: notepad .env

# 2. Configure your Obsidian vault path (recommended)
# In .env, set LOCAL_OBSIDIAN_PATH to your existing vault location
# Example: LOCAL_OBSIDIAN_PATH=C:/Users/YourName/Documents/ObsidianVault
# Note: Use forward slashes (/) in the path, not backslashes (\)

# 3. Run first-time setup
powershell -ExecutionPolicy Bypass -File .\scripts\setup\first_run.ps1
# If first_run.ps1 doesn't exist, use WSL or Git Bash to run:
# bash ./scripts/setup/first_run.sh

# 4. (Optional) Initialize Ollama for local LLM
powershell -ExecutionPolicy Bypass -File .\scripts\setup\init_ollama.ps1
# If init_ollama.ps1 doesn't exist, use WSL or Git Bash to run:
# bash ./scripts/setup/init_ollama.sh

# 5. Access the system
# - Open WebUI: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - Health Check: http://localhost:8000/health
```

**Note for Windows users**: If PowerShell scripts (.ps1) are not available, you can use Windows Subsystem for Linux (WSL) or Git Bash to run the bash scripts (.sh) instead.

### Obsidian Vault Configuration

Maestro can directly access your existing Obsidian vault on your local file system. This is the **recommended approach** for most users.

#### Configure Local Vault Path (Recommended)

Edit your `.env` file and set the `LOCAL_OBSIDIAN_PATH` variable to point to your vault directory:

```bash
# Local Obsidian Vault Path (Host System)
LOCAL_OBSIDIAN_PATH=/path/to/your/obsidian/vault

# Examples for different operating systems:
# Windows:
#   LOCAL_OBSIDIAN_PATH=C:/Users/YourName/Documents/ObsidianVault
# Linux:
#   LOCAL_OBSIDIAN_PATH=/home/yourname/Documents/ObsidianVault
# macOS:
#   LOCAL_OBSIDIAN_PATH=/Users/yourname/Documents/ObsidianVault
```

**Benefits:**
- Direct access to your existing vault (no copying required)
- Changes are immediately visible to Maestro
- Works with any cloud sync solution you may use (Google Drive, Dropbox, OneDrive, Syncthing, etc.)

### Google Drive API Integration (Optional)

For advanced use cases, you can also enable Google Drive API integration for cloud-based RAG with Gemini. Configure the following environment variables in your `.env` file:

#### Required Environment Variables

```bash
# Google Cloud Project Configuration
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/google-credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-actual-drive-folder-id

# Google API Key (for Gemini)
GOOGLE_API_KEY=your-google-api-key
# OR
GOOGLE_GEMINI_API_KEY=your-gemini-api-key
```

#### Setup Steps

1. **Create a Google Cloud Project**
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select an existing one
   - Note your project ID

2. **Enable Google Drive API**
   - In your Google Cloud project, enable the Google Drive API
   - Navigate to "APIs & Services" > "Enable APIs and Services"
   - Search for "Google Drive API" and enable it

3. **Create Service Account Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "Service Account"
   - Download the JSON key file
   - Place it in `credentials/google-credentials.json` (relative to project root)

4. **Get Google Drive Folder ID**
   - Create or select a folder in Google Drive
   - Share the folder with your service account email (found in the credentials JSON)
   - Copy the folder ID from the URL: `https://drive.google.com/drive/folders/FOLDER_ID_HERE`

5. **Get Google API Key** (for Gemini)
   - Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
   - Create or copy your API key
   - Add it to your `.env` file

6. **Run First-Time Setup**
   - The `first_run.sh` script will automatically detect your Google Drive configuration
   - It will create the necessary directories and validate your credentials
   - Warnings will be displayed if any configuration is missing

```bash
./scripts/setup/first_run.sh
```

#### Path Mapping

Maestro automatically maintains a bidirectional mapping between your local Obsidian vault and Google Drive files. Use the Path Mapping API endpoints to:
- Sync your entire vault: `POST /api/v1/path-mapping/sync`
- Resolve local to cloud paths: `GET /api/v1/path-mapping/resolve/local/{path}`
- Resolve cloud to local paths: `GET /api/v1/path-mapping/resolve/cloud/{id}`

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

#### Local RAG (Retrieval-Augmented Generation)
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

#### Cloud RAG (Phase 2)
- `POST /api/v1/cloud-rag/query` - Query Google Drive files with Gemini
- `POST /api/v1/cloud-rag/search` - Search Google Drive files
- `POST /api/v1/cloud-rag/query-files` - Query specific file IDs
- `GET /api/v1/cloud-rag/status` - Check cloud integration status

#### Path Mapping (Phase 2)
- `POST /api/v1/path-mapping` - Create/update path mapping
- `GET /api/v1/path-mapping` - List all mappings
- `GET /api/v1/path-mapping/resolve/local/{path}` - Resolve local to cloud
- `GET /api/v1/path-mapping/resolve/cloud/{id}` - Resolve cloud to local
- `POST /api/v1/path-mapping/sync` - Sync entire vault

#### Task Management
- `GET /api/v1/tasks` - List all tasks
- `POST /api/v1/tasks` - Create new task
- `GET /api/v1/tasks/{id}` - Get specific task
- `PATCH /api/v1/tasks/{id}` - Update task
- `DELETE /api/v1/tasks/{id}` - Delete task

#### Skills Framework (Phase 4)
- `GET /api/v1/skills/skills` - List all available skills
- `GET /api/v1/skills/skills/{name}` - Get skill details
- `POST /api/v1/skills/execute` - Execute a skill
  ```json
  {
    "skill_name": "search_knowledge_base",
    "parameters": {
      "query": "project updates",
      "max_results": 5
    }
  }
  ```
- `GET /api/v1/skills/tools/{provider}` - Get tool schemas for LLM (claude, gemini, ollama)
- `GET /api/v1/skills/categories` - List skill categories
- `GET /api/v1/skills/stats` - Get skill statistics

#### Built-in Skills (Phase 4)
- **generate_weekly_review** - Create comprehensive weekly summaries
- **search_knowledge_base** - Semantic search across Obsidian vault
- **extract_tasks** - Extract actionable tasks from notes
- **generate_project_synthesis** - Generate project overviews

<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> develop
#### GitHub Integration (Infrastructure)
- **Automated PR Creation**: Creates pull requests for:
  - AI conversation sessions
  - Meeting transcripts
  - Interview notes
- **Branch Sanitization**: Automatic Git ref validation with comprehensive character handling
- **Multi-Repository Support**: Route content to different repositories based on type

<<<<<<< HEAD
>>>>>>> origin/develop
=======
>>>>>>> develop
#### Health & Status
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed component status
- `GET /` - API information

<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> develop
## GitOps & Infrastructure

### GitHub Actions Workflows

Maestro includes enterprise-grade GitOps workflows for infrastructure management:

#### Terraform PR Pipeline
- **Trigger**: Push to any branch (except main/master) with Terraform changes
- **Actions**: Format check, init, validate, plan, security scan (tfsec)
- **Output**: Automated PR with plan details and security findings

#### Staging Deployment
- **Trigger**: Merge to `develop` branch
- **Actions**: Auto-deploy to staging environment
- **Features**: Automatic rollback on failure, deployment summary

#### Production Deployment
- **Trigger**: Merge to `main` branch
- **Actions**: Deploy to production with manual approval gate
- **Safety**: Requires reviewer approval before deployment

#### Drift Detection
- **Trigger**: Weekly schedule (Mondays 9 AM UTC)
- **Actions**: Detect infrastructure drift, create GitHub issue
- **Notifications**: Email alerts on drift detection

### Branch Name Sanitization

The GitHub integration includes robust branch name sanitization:
- Removes Git-invalid characters (`:`, `~`, `^`, `?`, `*`, `[`, `\`)
- Handles Unicode and emoji characters gracefully
- Ensures filesystem compatibility
- Validates against Git ref naming rules
- Provides debug logging for troubleshooting

See [GITOPS_SETUP_GUIDE.md](docs/GITOPS_SETUP_GUIDE.md) for detailed setup instructions.

<<<<<<< HEAD
>>>>>>> origin/develop
=======
>>>>>>> develop
### Development Roadmap

- ✅ **Phase 1** (Weeks 1-6): Local-First Knowledge Core
  - Obsidian RAG integration
  - Docker infrastructure
  - Basic API layer
  - Task management
  - PostgreSQL database

- ✅ **Phase 2** (Weeks 7-12): Cloud Knowledge Integration
  - Google Drive client integration
  - Path mapping service
  - Hybrid RAG (local + cloud)
  - Cloud RAG with Gemini
  - Cloud API endpoints

- 📋 **Phase 3** (Weeks 13-18): Multi-LLM Orchestration
  - LangGraph supervisor agent
  - Claude/Gemini worker integration
  - Multi-LLM routing matrix
  - HITL (Human-in-the-Loop) confirmations

- ✅ **Phase 4** (Weeks 19-24): Platform & Ecosystem
  - Unified EA Skills framework
  - Multi-LLM adapters (Claude, Gemini, Ollama)
  - Plugin SDK & documentation
  - Open WebUI pipeline integration
  - Built-in skills (weekly review, search, tasks, synthesis)

<<<<<<< HEAD
<<<<<<< HEAD
=======
=======
>>>>>>> develop
- 🚀 **Infrastructure Automation** (Ongoing)
  - GitHub Actions workflows for Terraform
  - Multi-environment deployment pipeline (staging, production)
  - Automated PR creation for AI-generated content
  - Git ref name sanitization and validation
  - Security scanning with tfsec
  - Drift detection and monitoring

<<<<<<< HEAD
>>>>>>> origin/develop
=======
>>>>>>> develop
### Project Structure

```
maestro/
<<<<<<< HEAD
<<<<<<< HEAD
├── backend/           # FastAPI backend
│   ├── core/         # Core modules (RAG, models, database)
│   ├── api/          # API routes
│   ├── services/     # Business logic services (path_mapping, etc.)
│   ├── integrations/ # External integrations (Google Drive, Gemini)
│   └── tests/        # Unit and integration tests
├── frontend/         # Open WebUI customizations
├── infra/            # Docker infrastructure
│   ├── docker-compose.yml
│   └── docker/       # Dockerfiles
├── scripts/          # Setup and utility scripts
├── data/            # Data directory (gitignored)
│   └── vault/       # Place your Obsidian vault here
├── credentials/     # API credentials (gitignored)
└── docs/            # Documentation
    └── guides/      # User guides and tutorials
=======
├── backend/                        # FastAPI backend
│   ├── core/                      # Core modules (RAG, models, database)
│   ├── api/                       # API routes
│   ├── services/                  # Business logic services (path_mapping, etc.)
│   ├── integrations/              # External integrations (Google Drive, Gemini)
│   └── tests/                     # Unit and integration tests
├── frontend/                      # Open WebUI customizations
├── infra/                         # Docker infrastructure
│   ├── docker-compose.yml
=======
├── backend/                        # FastAPI backend
│   ├── core/                      # Core modules (RAG, models, database)
│   ├── api/                       # API routes
│   ├── services/                  # Business logic services (path_mapping, etc.)
│   ├── integrations/              # External integrations (Google Drive, Gemini)
│   └── tests/                     # Unit and integration tests
├── frontend/                      # Open WebUI customizations
├── infra/                         # Docker infrastructure
│   ├── docker-compose.yml
>>>>>>> develop
│   └── docker/                    # Dockerfiles
├── iac/                           # Infrastructure as Code
│   └── maestro-artifacts/
│       └── terraform/             # Terraform configurations
│           ├── main.py            # GitHub PR automation (sessions, transcripts, interviews)
│           ├── backend.tf         # Multi-environment state management
│           └── environments/      # Environment-specific configs
├── .github/                       # GitHub Actions workflows
│   └── workflows/
│       ├── terraform-pr-pipeline.yml      # PR validation workflow
│       ├── terraform-apply-staging.yml    # Auto-deploy to staging
│       ├── terraform-apply-production.yml # Manual production deployment
│       └── terraform-drift.yml            # Weekly drift detection
├── scripts/                       # Setup and utility scripts
│   ├── setup/                     # Initial setup scripts
│   ├── quick-commit.sh/.ps1       # Developer productivity helpers
│   └── fix-wif-repo-case.sh/.ps1  # WIF configuration fixes
├── data/                          # Data directory (gitignored)
│   └── vault/                     # Place your Obsidian vault here
├── credentials/                   # API credentials (gitignored)
└── docs/                          # Documentation
    ├── guides/                    # User guides and tutorials
    ├── GITOPS_SETUP_GUIDE.md      # GitOps configuration guide
    └── GITOPS_IMPLEMENTATION.md   # GitOps implementation details
<<<<<<< HEAD
>>>>>>> origin/develop
=======
>>>>>>> develop
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
