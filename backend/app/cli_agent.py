#!/usr/bin/env python3
"""
Gemini CLI Agent Runner
Run with: python -m app.cli_agent
"""

import asyncio
import argparse
import os
import sys
from dotenv import load_dotenv
from app.agents.gemini_cli_agent import GeminiCLIAgent
import uuid

load_dotenv()


def main():
    parser = argparse.ArgumentParser(description="Gemini CLI Agent for Document Exploration")
    parser.add_argument("--model", default="gemini-1.5-flash-latest", help="Gemini model to use")
    parser.add_argument("--session-id", help="Session ID (auto-generated if not provided)")
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY environment variable not set")
        print("Please set it in your .env file or export it:")
        print("export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Create session ID
    session_id = args.session_id or str(uuid.uuid4())
    
    print(f"🚀 Starting Gemini CLI Agent")
    print(f"📝 Session ID: {session_id}")
    print(f"🤖 Model: {args.model}")
    print("-" * 50)
    
    try:
        agent = GeminiCLIAgent(session_id, model_name=args.model)
        asyncio.run(agent.interactive_session())
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()