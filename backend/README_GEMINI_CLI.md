# Gemini CLI Agent

A command-line interface agent powered by Google Gemini for interactive document exploration.

## Setup

1. Set your Google API key in `.env`:
```bash
GOOGLE_API_KEY=your-api-key-here
```

2. Install dependencies (if not already installed):
```bash
cd backend
pip install google-generativeai
```

## Usage

### 1. Standalone CLI Mode

Run the Gemini CLI agent directly:

```bash
cd backend
python -m app.cli_agent
```

Options:
- `--model`: Specify Gemini model (default: gemini-1.5-flash-latest)
- `--session-id`: Custom session ID (auto-generated if not provided)

Example:
```bash
python -m app.cli_agent --model gemini-1.5-pro-latest
```

### 2. API Endpoint

The agent is also available via the FastAPI endpoint:

```
POST /cli-chat
{
  "message": "Show me all markdown files",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "session_id": "uuid",
  "response": "I'll help you find all markdown files...",
  "commands_executed": ["find . -name '*.md'"],
  "outputs": ["./README.md\n./docs/guide.md..."]
}
```

## Configuration

Environment variables in `.env`:

```bash
# Gemini settings
GOOGLE_API_KEY=your-api-key
GEMINI_MODEL=gemini-1.5-flash-latest
GEMINI_TEMPERATURE=0.7
GEMINI_TOP_P=0.95
GEMINI_TOP_K=64
GEMINI_MAX_TOKENS=4096

# Agent settings
AGENT_DEFAULT_AGENT=gemini_cli
AGENT_SESSION_TIMEOUT=3600
AGENT_COMMAND_TIMEOUT=30
AGENT_MAX_COMMAND_LENGTH=1000
```

## Features

- **Interactive CLI**: Natural language interface for document exploration
- **Security**: Only read-only commands are allowed
- **Context Awareness**: Maintains conversation history
- **Command Extraction**: Automatically extracts and executes bash commands
- **Configurable**: Flexible model and generation settings

## Example Usage

```
> Show me all markdown files in the documentation

🤖 I'll help you find all markdown files in the documentation.

💻 $ find . -name '*.md' -type f
./README.md
./document/ja/index.md
./document/ja/getting_started/index.md
./document/ja/faq/index.md
...

> What's in the getting started guide?

🤖 Let me check the getting started guide for you.

💻 $ cat ./document/ja/getting_started/index.md
# Getting Started Guide
This guide will help you...
```

## Commands

CLI commands:
- `help`: Show available commands
- `clear`: Clear conversation history
- `exit/quit`: Exit the CLI

## Security

The agent enforces security through:
- Command validation before execution
- Whitelist of allowed read-only commands
- Path traversal protection
- Command injection prevention
- Timeout limits on command execution