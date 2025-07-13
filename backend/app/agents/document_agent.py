"""Document-based agent that uses concatenated documentation as context"""

import os
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from ..config import get_gemini_config
from ..logging_config import security_logger


class DocumentAgent:
    """Agent that uses pre-loaded documentation as context for answering queries"""
    
    def __init__(self, session_id: str):
        # Load configuration
        self.gemini_config = get_gemini_config()
        
        # Validate API key
        if not self.gemini_config.api_key:
            raise ValueError("GOOGLE_API_KEY environment variable not set")
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_config.api_key)
        self.model = genai.GenerativeModel(self.gemini_config.model_name)
        
        # Session settings
        self.session_id = session_id
        
        # Load documentation content
        self.documentation_content = self._load_documentation()
        
        # Generation configuration
        self.generation_config = GenerationConfig(
            temperature=self.gemini_config.temperature,
            top_p=self.gemini_config.top_p,
            top_k=self.gemini_config.top_k,
            max_output_tokens=self.gemini_config.max_output_tokens,
        )
    
    def _load_documentation(self) -> str:
        """Load the concatenated documentation file"""
        doc_path = "/workspace/document/concatenated_documentation.md"
        
        # Try alternative path if running in development
        if not os.path.exists(doc_path):
            doc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "concatenated_documentation.md")
        
        # Try absolute path for local development
        if not os.path.exists(doc_path):
            doc_path = "/Users/ozoraogino/dev/donut/docbot/concatenated_documentation.md"
        
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Successfully loaded documentation from: {doc_path}")
            print(f"Documentation size: {len(content)} characters")
            # Check if PDF content is included
            if "Single arm rated load" in content:
                print("✓ PDF content (arm rated load) found in documentation")
            else:
                print("✗ PDF content (arm rated load) NOT found in documentation")
            return content
        except FileNotFoundError:
            print(f"Warning: Documentation file not found at {doc_path}")
            return ""
        except Exception as e:
            print(f"Error loading documentation: {e}")
            return ""
    
    async def process_query(self, query: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Process user query using the documentation context"""
        
        yield {"type": "message", "content": "🔍 Searching documentation..."}
        
        # Build prompt with documentation context
        system_prompt = """You are a helpful assistant that answers questions based on the provided documentation.
        
        IMPORTANT RULES:
        1. ONLY use information from the documentation provided below
        2. Do NOT use any external knowledge or make assumptions
        3. If the information is not in the documentation, clearly state that
        4. Provide accurate, detailed answers based on what's documented
        5. Include relevant examples or code snippets from the documentation when helpful
        
        Documentation content:
        """
        
        # Create the full prompt
        full_prompt = f"""{system_prompt}

{self.documentation_content}

User Question: {query}

Please provide a comprehensive answer based ONLY on the documentation above. Structure your response clearly with appropriate sections if needed."""

        try:
            # Generate response
            response = await self.model.generate_content_async(
                contents=[full_prompt],
                generation_config=self.generation_config,
            )
            
            # Yield the response
            yield {"type": "message", "content": f"\n📋 **Answer:**\n\n{response.text}"}
            
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            print(error_msg)
            yield {"type": "error", "content": error_msg}
    
    async def process_query_simple(self, query: str) -> str:
        """Process query and return simple string response (for CLI agent)"""
        results = []
        async for result in self.process_query(query):
            if result.get("type") == "message" and "Answer:" in result.get("content", ""):
                # Extract just the answer part
                content = result["content"]
                answer_start = content.find("**Answer:**")
                if answer_start != -1:
                    return content[answer_start + 11:].strip()
            results.append(result.get("content", ""))
        
        return "\n".join(results)