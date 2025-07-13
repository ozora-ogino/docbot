# DocBot - Read-only Document Explorer

A secure, Docker-based chatbot that allows users to explore documents using read-only bash commands through a natural language interface.

## Features

- 🔒 **Security First**: All write operations are blocked at multiple levels
- 🤖 **AI-Powered**: Uses LangChain and OpenAI to understand natural language queries
- 📂 **Read-Only Access**: Safely explore documents without risk of modification
- 🔍 **Rich Command Set**: Support for ls, cat, grep, find, and more
- 📊 **Real-time Streaming**: SSE-based streaming for responsive UI
- 🎯 **Session Tracking**: All commands are logged with session IDs
- 🎨 **Modern UI**: React-based interface with command history and copy functionality

## Quick Start

1. Clone the repository:
```bash
git clone <repo-url>
cd docbot
```

2. Set up environment:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY
```

3. Add documents to explore:
```bash
# Place your documents in the ./document directory
cp -r /path/to/your/docs ./document/
```

4. Run with Docker Compose:
```bash
docker-compose up --build
```

5. Open http://localhost:5173 in your browser

## Security Features

### Command Validation
- Whitelist of allowed read-only commands
- Blacklist of dangerous patterns and operations
- Path traversal protection
- Command injection prevention
- Maximum command length limits

### Docker Security
- Read-only volume mounts
- Dropped capabilities (`--cap-drop=ALL`)
- No network access for backend
- Temporary filesystem for scratch space
- Non-root user execution

### Logging
- All command attempts are logged
- Session tracking for audit trails
- Structured JSON logging format

## Allowed Commands

- **File Listing**: `ls`, `tree`, `find`
- **File Reading**: `cat`, `head`, `tail`, `less`, `more`
- **Text Search**: `grep`, `rg` (ripgrep)
- **Text Processing**: `awk`, `cut`, `sort`, `uniq`, `wc`
- **File Info**: `file`, `stat`, `du`
- **Navigation**: `pwd`

## Architecture

```
docbot/
├── backend/          # FastAPI + LangChain backend
├── frontend/         # React + Vite frontend  
├── document/         # Your documents (mounted read-only)
└── docker-compose.yml
```

## Development

### Backend Development
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd frontend
pnpm install
pnpm dev
```

### Security Testing
```bash
cd backend
python test_security.py
```

## Example Queries

- "Show me all Python files in the project"
- "Search for TODO comments in the codebase"
- "What's the directory structure?"
- "Find all configuration files"
- "Show me the contents of README.md"

## License

MIT