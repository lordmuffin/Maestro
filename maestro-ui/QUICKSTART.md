# Maestro UI - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies

```bash
cd maestro-ui
npm install
```

This will install all required dependencies including React, TypeScript, Vite, Tailwind CSS, and shadcn/ui components.

### Step 2: Start Development Server

```bash
npm run dev
```

The application will be available at `http://localhost:3000`

### Step 3: Configure Your Environment

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Configure backend services:**
   Ensure your Maestro backend services are running:
   - Supervisor (port 8003)
   - Local RAG (port 8001)
   - Path Mapping (port 8002)
   - Skills (port 8004)
   - Evaluation (port 8000)

## 🐳 Docker Deployment (Production)

### Build and Run

```bash
# Build the Docker image
docker build -t maestro/ui:latest .

# Run with Docker Compose
docker-compose -f docker-compose.ui.yml up -d
```

### Verify Deployment

```bash
# Check container status
docker ps | grep maestro-ui

# View logs
docker logs maestro-ui

# Access application
open http://localhost
```

## 📝 Available Commands

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server with HMR |
| `npm run build` | Build production bundle |
| `npm run preview` | Preview production build locally |
| `npm run lint` | Run ESLint for code quality |

## 🎨 Application Pages

Once running, you can access:

- **Home** (`/`) - Welcome page with quick start guide
- **Chat** (`/chat`) - Interactive chat interface
- **Dashboard** (`/dashboard`) - System monitoring and metrics
- **Settings** (`/settings`) - Configuration and preferences

## 🔧 Configuration Options

### LLM Providers

Configure in Settings or directly in Chat sidebar:

- **Local** - Ollama (privacy-first, no API key needed)
- **Claude** - Anthropic Claude (requires API key)
- **Gemini** - Google Gemini (requires API key)
- **OpenAI** - GPT models (requires API key)

### Data Sensitivity Levels

- **Low** - Public data, any provider allowed
- **Medium** - Internal data, shows warnings for cloud providers
- **High** - Sensitive data, strongly recommends local provider

## 🐛 Troubleshooting

### Port Already in Use

```bash
# Kill process on port 3000
lsof -ti:3000 | xargs kill -9

# Or use a different port
npm run dev -- --port 3001
```

### Backend Services Not Connecting

1. Verify backend services are running
2. Check Docker network: `docker network ls | grep maestro`
3. Test API endpoints: `curl http://localhost:8003/health`

### Build Errors

```bash
# Clean install
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
```

## 📚 Next Steps

1. **Explore the UI** - Navigate through all pages to understand features
2. **Configure Vault** - Set your Obsidian vault path in Settings
3. **Add API Keys** - Configure cloud provider API keys if needed
4. **Start Chatting** - Ask questions about your knowledge base
5. **Monitor Health** - Check Dashboard for system status

## 🎓 Learn More

- [Full README](./README.md) - Comprehensive documentation
- [Architecture Diagram](./README.md#architecture) - System design
- [API Documentation](./README.md#api-routes) - Backend integration

## 💡 Tips

- **Keyboard Shortcuts:**
  - `Enter` - Send message
  - `Shift + Enter` - New line in message

- **Privacy Best Practices:**
  - Use "Local" provider for sensitive data
  - Set appropriate sensitivity levels
  - Review privacy warnings before sending

- **Performance:**
  - Development mode includes hot reload
  - Production build is optimized and minified
  - Service health checks run every 5 seconds

---

Happy querying! 🎉
