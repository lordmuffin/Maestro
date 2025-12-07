# Jarvis (V2V2B Interrogator)

This Azure Function App hosts "Jarvis", a Telegram bot designed for technical content extraction and interrogation.

## Features

- **Technical Interviewing:** Conducts structured interviews to extract knowledge.
- **Multimodal Analysis:** Analyzes images, audio, and documents (PDF, etc.) using Google Gemini.
- **Knowledge Base Search:** Autonomously searches configured GitHub repositories to answer questions or refine inquiries before asking the user.
- **Session Management:** Stores session history in Cosmos DB.
- **GitOps Integration:** Creates Pull Requests for saved sessions, transcripts, and interview notes.

## Configuration

- **Repositories:** Configured in `repos.json`.
- **Environment Variables:** See `function_app.py` for required variables (e.g., `TELEGRAM_BOT_TOKEN`, `GOOGLE_API_KEY`, `GITHUB_TOKEN_MAESTRO`).

## Agentic Behavior

Jarvis utilizes an agentic workflow:
1.  **Analyze:** Upon receiving a message, it analyzes the context.
2.  **Decide:** It determines if it needs to consult the Knowledge Base (GitHub Repos).
3.  **Search:** If needed, it searches the repositories via GitHub API.
4.  **Refine/Answer:** It uses the found information to answer directly or ask more specific, informed questions.
