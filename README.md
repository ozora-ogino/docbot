# DocBot - Read-only Document Explorer

A secure, Docker-based chatbot that allows users to explore documents using read-only bash commands through a natural language interface.

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Security Features](#security-features)
- [Allowed Commands](#allowed-commands)
- [Architecture](#architecture)
- [Development](#development)
- [Example Queries](#example-queries)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- 🔒 **Security First**: All write operations are blocked at multiple levels
- 🤖 **AI-Powered**: Uses LangChain and OpenAI to understand natural language queries
- 📂 **Read-Only Access**: Safely explore documents without risk of modification
- 🔍 **Rich Command Set**: Support for ls, cat, grep, find, and more
- 📊 **Real-time Streaming**: SSE-based streaming for responsive UI
- 🎯 **Session Tracking**: All commands are logged with session IDs
- 🎨 **Modern UI**: React-based interface with command history and copy functionality

## System Requirements

- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Node.js**: Version 18+ (for local development)
- **Python**: Version 3.11+ (for local development)
- **Memory**: Minimum 2GB RAM
- **Disk Space**: At least 1GB free space
- **Operating System**: Linux, macOS, or Windows with WSL2

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

### Multi-Layer Security Architecture

DocBot implements defense-in-depth with multiple security layers:

1. **Application Layer Security**
   - Command whitelisting with strict validation
   - Pattern-based blacklisting for dangerous operations
   - Input sanitization and length limits
   - Path traversal prevention
   - Command injection protection

2. **Container Security**
   - Read-only volume mounts for document directories
   - All Linux capabilities dropped (`--cap-drop=ALL`)
   - Network isolation for backend container
   - Non-root user execution (UID 1000)
   - Minimal base image (python:3.11-slim)
   - No shell access in production

3. **Runtime Security**
   - Resource limits (CPU and memory)
   - Temporary filesystem for scratch operations
   - Process isolation with Docker namespaces
   - Seccomp security profiles

### Command Validation

- **Whitelist Approach**: Only explicitly allowed commands can execute
- **Pattern Matching**: Advanced regex validation for command arguments
- **Path Restrictions**: Commands limited to `/document` directory
- **Dangerous Pattern Detection**: Blocks redirections, pipes, subshells
- **Length Limits**: Maximum 1000 characters per command

### Audit & Monitoring

- **Comprehensive Logging**: Every command attempt logged with timestamp
- **Session Tracking**: Unique session IDs for request correlation
- **Structured Logs**: JSON format for easy parsing and analysis
- **Failed Attempt Tracking**: Special attention to blocked commands
- **Performance Metrics**: Command execution time tracking

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

### Basic File Operations
- "Show me all Python files in the project"
- "What's in the config directory?"
- "List all markdown files"
- "Show me the directory structure"

### Content Search
- "Search for TODO comments in the codebase"
- "Find all occurrences of 'API_KEY'"
- "Show me files containing 'database'"
- "Search for error messages in log files"

### File Analysis
- "Show me the contents of README.md"
- "What are the largest files in the project?"
- "Count lines in all JavaScript files"
- "Show me recently modified files"

### Advanced Queries
- "Find all configuration files (json, yaml, env)"
- "Show Python files larger than 1000 lines"
- "List files modified in the last 24 hours"
- "Find duplicate file names"

## License

MIT