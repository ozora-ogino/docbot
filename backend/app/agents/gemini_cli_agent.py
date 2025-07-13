"""Gemini CLI Agent for interactive command-line interface"""

import asyncio
import os
import json
from typing import Optional, List, Dict, Any
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from ..security import CommandValidator
from ..logging_config import security_logger
from ..config import get_gemini_config, get_agent_config


class GeminiCLIAgent:
    """CLI Agent powered by Google Gemini for interactive document exploration"""
    
    def __init__(self, session_id: str, model_name: Optional[str] = None):
        # Load configurations
        self.gemini_config = get_gemini_config()
        self.agent_config = get_agent_config()
        
        # Validate API key
        if not self.gemini_config.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_config.api_key)
        model_to_use = model_name or self.gemini_config.model_name
        self.model = genai.GenerativeModel(model_to_use)
        
        # Session settings
        self.session_id = session_id
        self.cwd = "/workspace/document"
        self.conversation_history = []
        self.context = {}
        
        # Generation configuration from settings
        self.generation_config = GenerationConfig(
            temperature=self.gemini_config.temperature,
            top_p=self.gemini_config.top_p,
            top_k=self.gemini_config.top_k,
            max_output_tokens=self.gemini_config.max_output_tokens,
        )
        
        self.system_prompt = """You are a helpful CLI assistant for exploring documentation.
        You can execute read-only bash commands to help users find and understand information.
        
        Available commands:
        - ls, tree, find: Navigate and list files
        - cat, head, tail, less: Read file contents
        - grep, rg: Search for patterns
        - pwd: Show current directory
        
        Always explain what you're doing and why. Be concise but informative.
        """
    
    async def process_command(self, user_input: str) -> Dict[str, Any]:
        """Process a single user command/query"""
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Generate response with Gemini
        prompt = self._build_prompt(user_input)
        response = await self._generate_response(prompt)
        
        # Parse response for commands to execute
        commands = self._extract_commands(response)
        
        result = {
            "response": response,
            "commands_executed": [],
            "outputs": []
        }
        
        # Execute extracted commands
        for cmd in commands:
            is_valid, message = CommandValidator.validate_command(cmd)
            security_logger.log_command_attempt(cmd, self.session_id, is_valid, message)
            
            if is_valid:
                output = await self._execute_command(cmd)
                result["commands_executed"].append(cmd)
                result["outputs"].append(output)
                
                # Update context with command results
                self.context[cmd] = output
            else:
                result["outputs"].append(f"❌ Security Error: {message}")
        
        self.conversation_history.append({
            "role": "assistant", 
            "content": response,
            "commands": commands,
            "outputs": result["outputs"]
        })
        
        return result
    
    async def interactive_session(self):
        """Run an interactive CLI session"""
        print("🤖 Gemini CLI Agent Started")
        print("Type 'help' for available commands, 'exit' to quit")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n> ").strip()
                
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    print(self._get_help_text())
                    continue
                
                if user_input.lower() == 'clear':
                    self.conversation_history.clear()
                    self.context.clear()
                    print("✨ Conversation cleared")
                    continue
                
                # Process the command
                result = await self.process_command(user_input)
                
                # Display response
                print(f"\n🤖 {result['response']}")
                
                # Display command outputs
                for i, (cmd, output) in enumerate(zip(result['commands_executed'], result['outputs'])):
                    print(f"\n💻 $ {cmd}")
                    print(output[:500] + "..." if len(output) > 500 else output)
                    
            except KeyboardInterrupt:
                print("\n\n👋 Interrupted. Type 'exit' to quit.")
                continue
            except Exception as e:
                print(f"\n❌ Error: {str(e)}")
    
    def _build_prompt(self, user_input: str) -> str:
        """Build prompt with context and history"""
        prompt_parts = [self.system_prompt]
        
        # Add recent conversation history
        recent_history = self.conversation_history[-6:]  # Last 3 exchanges
        if recent_history:
            prompt_parts.append("\nRecent conversation:")
            for entry in recent_history:
                role = entry['role']
                content = entry['content']
                prompt_parts.append(f"{role}: {content}")
                
                if 'commands' in entry and entry['commands']:
                    prompt_parts.append("Commands executed:")
                    for cmd, output in zip(entry.get('commands', []), entry.get('outputs', [])):
                        prompt_parts.append(f"$ {cmd}")
                        if output:
                            prompt_parts.append(output[:200] + "..." if len(output) > 200 else output)
        
        # Add current query
        prompt_parts.append(f"\nCurrent query: {user_input}")
        prompt_parts.append("\nProvide a helpful response. If you need to execute commands to answer the query, include them in your response prefixed with '$'.")
        
        return "\n".join(prompt_parts)
    
    async def _generate_response(self, prompt: str) -> str:
        """Generate response using Gemini"""
        response = await self.model.generate_content_async(
            contents=[prompt],
            generation_config=self.generation_config,
        )
        return response.text
    
    def _extract_commands(self, response: str) -> List[str]:
        """Extract bash commands from response"""
        commands = []
        lines = response.split('\n')
        
        for line in lines:
            line = line.strip()
            # Look for lines starting with $ or containing command patterns
            if line.startswith('$'):
                cmd = line[1:].strip()
                if cmd:
                    commands.append(cmd)
            elif line.startswith('```bash'):
                # Handle code blocks
                continue
            elif line.startswith('```') and len(commands) > 0:
                # End of code block
                continue
            elif len(commands) > 0 and line and not line.startswith('```'):
                # Inside a code block
                if not any(line.startswith(x) for x in ['#', '//', '<!--']):
                    commands.append(line)
        
        return commands
    
    async def _execute_command(self, command: str) -> str:
        """Execute a shell command safely"""
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), 
                timeout=self.agent_config.command_timeout
            )
            
            if proc.returncode != 0:
                return f"Command failed: {stderr.decode()}"
            
            output = stdout.decode()
            return output if output else "Command executed successfully (no output)"
            
        except asyncio.TimeoutError:
            return f"Command timeout ({self.agent_config.command_timeout} seconds)"
        except Exception as e:
            return f"Error executing command: {str(e)}"
    
    def _get_help_text(self) -> str:
        """Get help text for the CLI"""
        return """
🤖 Gemini CLI Agent Help

Available commands:
- help      : Show this help message
- clear     : Clear conversation history
- exit/quit : Exit the CLI

You can ask questions about the documentation, and I'll help you explore it using bash commands.

Examples:
- "Show me all markdown files"
- "Search for API documentation"
- "What's in the getting_started folder?"
- "Find all files mentioning 'configuration'"

Security: Only read-only commands are allowed for safety.
"""


async def main():
    """Main entry point for CLI agent"""
    import uuid
    session_id = str(uuid.uuid4())
    agent = GeminiCLIAgent(session_id)
    await agent.interactive_session()


if __name__ == "__main__":
    asyncio.run(main())