# Maestro UI - Web Frontend

A modern, responsive React application for the Maestro AI Assistant system. Built with React 18, TypeScript, Vite, Tailwind CSS, and shadcn/ui.

## Features

- 💬 **Interactive Chat Interface** - Query your knowledge base with real-time responses
- 🎛️ **Multi-LLM Support** - Choose between local (Ollama) and cloud providers (Claude, GPT, Gemini)
- 🔒 **Privacy-First** - Data sensitivity controls with privacy warnings
- 📊 **System Dashboard** - Monitor service health and performance metrics
- ⚙️ **Configurable Settings** - Customize vault paths, API keys, and preferences
- 🎨 **Modern UI** - Beautiful, accessible components built with shadcn/ui
- 📱 **Responsive Design** - Works seamlessly on desktop, tablet, and mobile

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first CSS framework
- **shadcn/ui** - High-quality accessible components
- **@tanstack/react-query** - Data fetching and caching
- **axios** - HTTP client
- **react-router-dom** - Client-side routing
- **Nginx** - Reverse proxy for API routes

## Architecture

```
User Browser (localhost:3000)
       ↓
   Nginx Reverse Proxy (localhost:80)
       ├── /                    → React Static Files
       ├── /api/supervisor      → http://supervisor:8003
       ├── /api/rag             → http://local-rag:8001
       ├── /api/mapping         → http://path-mapping:8002
       ├── /api/skills          → http://skills:8004
       └── /api/evaluation      → http://evaluation-api:8000
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Docker and Docker Compose (for containerized deployment)
- Running Maestro backend services (supervisor, rag, mapping, skills, evaluation)

### Development

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Start development server:**
   ```bash
   npm run dev
   ```

3. **Open your browser:**
   Navigate to `http://localhost:3000`

The development server includes hot module replacement for instant updates.

### Build for Production

```bash
npm run build
```

This creates an optimized production build in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Docker Deployment

### Build Docker Image

```bash
docker build -t maestro/ui:latest .
```

### Run with Docker Compose

```bash
docker-compose -f docker-compose.ui.yml up -d
```

This will:
- Build the production React bundle
- Serve static files via Nginx
- Proxy API requests to backend services
- Expose the application on port 80

### Access the Application

Once running, open `http://localhost` in your browser.

## Project Structure

```
maestro-ui/
├── public/                      # Static assets
├── src/
│   ├── main.tsx                 # Application entry point
│   ├── App.tsx                  # Root component with routing
│   ├── components/              # Reusable components
│   │   ├── ui/                  # shadcn/ui components
│   │   ├── Chat/                # Chat interface components
│   │   ├── Dashboard/           # Dashboard components
│   │   ├── Settings/            # Settings components
│   │   └── Layout/              # Layout components
│   ├── pages/                   # Route pages
│   │   ├── HomePage.tsx
│   │   ├── ChatPage.tsx
│   │   ├── DashboardPage.tsx
│   │   └── SettingsPage.tsx
│   ├── lib/                     # Utilities and API clients
│   │   ├── api/                 # API client modules
│   │   └── utils.ts             # Helper functions
│   ├── hooks/                   # Custom React hooks
│   ├── types/                   # TypeScript type definitions
│   └── styles/                  # Global styles
├── nginx.conf                   # Nginx configuration
├── Dockerfile                   # Multi-stage Docker build
├── docker-compose.ui.yml        # Docker Compose config
├── package.json
├── tsconfig.json
├── vite.config.ts
└── tailwind.config.js
```

## Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
VITE_API_BASE_URL=/api
VITE_APP_TITLE=Maestro AI Assistant
```

### Nginx Proxy Configuration

The `nginx.conf` file configures reverse proxy routes. Modify upstream servers if your backend services run on different hosts/ports.

## Usage Guide

### 1. Configure Your Vault

1. Navigate to **Settings** → **Vault**
2. Enter your Obsidian vault path
3. Click **Sync** to index your documents

### 2. Set Up API Keys (Optional)

1. Go to **Settings** → **API Keys**
2. Enter API keys for cloud providers (OpenAI, Anthropic, Google)
3. Click **Save** for each provider

### 3. Start Chatting

1. Navigate to **Chat**
2. Select your preferred LLM provider and model tier
3. Choose data sensitivity level
4. Type your query and press Enter or click Send

### 4. Monitor System

1. Visit **Dashboard** to view:
   - Service health status
   - Performance metrics
   - System uptime
   - Query statistics

## API Routes

All API calls are proxied through Nginx:

- **Supervisor**: `/api/supervisor/*` → `http://supervisor:8003`
- **RAG**: `/api/rag/*` → `http://local-rag:8001`
- **Mapping**: `/api/mapping/*` → `http://path-mapping:8002`
- **Skills**: `/api/skills/*` → `http://skills:8004`
- **Evaluation**: `/api/evaluation/*` → `http://evaluation-api:8000`

## Key Components

### Chat Interface
- **ChatWindow**: Main chat container
- **MessageList**: Displays conversation history
- **MessageInput**: Text input with keyboard shortcuts
- **AgentBadge**: Shows which agent handled the query

### Dashboard
- **ServiceStatus**: Real-time service health monitoring
- **HealthCheck**: Aggregate system health overview
- **Metrics**: Performance statistics and analytics

### Settings
- **LLMSelector**: Choose LLM provider, model tier, and sensitivity
- **VaultConfig**: Configure Obsidian vault path and sync
- **APIKeyManager**: Securely manage API keys

## Development Tips

### Adding New shadcn/ui Components

```bash
npx shadcn-ui@latest add [component-name]
```

### Type Safety

All API responses and component props are fully typed. Check the `src/types/` directory for type definitions.

### Custom Hooks

- `useChat`: Manage chat state and send messages
- `useServiceHealth`: Monitor backend service health
- `useSettings`: Persist user settings to localStorage

## Troubleshooting

### Services Not Connecting

1. Check that all backend services are running
2. Verify Docker network connectivity
3. Check nginx logs: `docker logs maestro-ui`

### Build Errors

1. Clear node_modules: `rm -rf node_modules && npm install`
2. Clear Vite cache: `rm -rf node_modules/.vite`
3. Ensure Node.js version is 18+

### API Proxy Issues

1. Verify nginx.conf upstream configurations
2. Check CORS settings in backend services
3. Inspect browser network tab for failed requests

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## License

This project is part of the Maestro AI Assistant system.

## Support

For issues and questions:
- Check the [documentation](../docs/)
- Review existing GitHub issues
- Open a new issue with detailed information

---

Built with ❤️ using React, TypeScript, and modern web technologies.
