

"""Smart search agent that explores documents comprehensively using Gemini"""

import asyncio
import json
import re
from typing import List, Dict, Any, Optional, Tuple, Set
import os
import time
from collections import OrderedDict
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from ..security import CommandValidator
from ..logging_config import security_logger

# Configure the Gemini client
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("GOOGLE_API_KEY environment variable not set")
genai.configure(api_key=api_key)

class GeminiClient:
    """Client for interacting with the Gemini API"""
    def __init__(self, model_name: str = "gemini-1.5-flash-latest"):
        self.model = genai.GenerativeModel(model_name)

    async def generate_content(self, prompt: str, generation_config: Optional[GenerationConfig] = None) -> str:
        """Generate content using the Gemini API"""
        if generation_config is None:
            generation_config = GenerationConfig(
                temperature=0.1,
                top_p=0.95,
                top_k=64,
                max_output_tokens=8192,
            )
        
        response = await self.model.generate_content_async(
            contents=[prompt],
            generation_config=generation_config,
        )
        return response.text

class SmartSearchAgent:
    """Agent that intelligently searches through documents with deep reasoning capabilities"""
    
    def __init__(self, session_id: str, debug_mode: bool = False):
        self.gemini_client = GeminiClient()
        self.session_id = session_id
        self.cwd = "/workspace/document"
        self.context_cache = OrderedDict()
        self.file_structure = None
        self.debug_mode = debug_mode
        self.thinking_steps = []
        self.search_history = []
        self.insights = []
        self.enable_web_search = os.getenv('ENABLE_WEB_SEARCH', 'false').lower() == 'true'
        self.max_cache_size = 50
        self.max_cache_content_size = 10000
        self.search_cache = {}
        self.search_cache_ttl = 300
        self.performance_metrics = {
            'llm_calls': 0,
            'shell_commands': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'start_time': None
        }
        
    async def _run_shell_command(self, command: str) -> str:
        """Run a shell command securely"""
        is_valid, message = CommandValidator.validate_command(command)
        security_logger.log_command_attempt(command, self.session_id, is_valid, message)
        
        if not is_valid:
            return f"❌ Security Error: {message}"

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            
            output = stdout.decode()
            if len(output) > self.max_cache_content_size:
                output = output[:self.max_cache_content_size] + "\n... (output truncated)"

            security_logger.log_command_result(command, self.session_id, proc.returncode == 0, len(output))

            if proc.returncode != 0:
                return f"❌ Command failed:\n{stderr.decode()}"
            
            return output if output else "✓ Command executed successfully (no output)"

        except asyncio.TimeoutError:
            security_logger.log_command_result(command, self.session_id, False, 0)
            return "❌ Error: Command timeout (60 seconds)"
        except Exception as e:
            security_logger.log_command_result(command, self.session_id, False, 0)
            return f"❌ Error executing command: {str(e)}"

    async def process_query(self, query: str):
        """Process user query with deep reasoning and multi-step search"""
        self.performance_metrics['start_time'] = time.time()
        
        yield {"type": "message", "content": "🧠 Thinking..."}
        
        init_tasks = []
        if not self.file_structure:
            if self.debug_mode:
                yield {"type": "message", "content": "Exploring document structure..."}
            init_tasks.append(self._init_file_structure())
        
        combined_analysis_task = asyncio.create_task(self._combined_query_analysis(query))
        
        if init_tasks:
            await asyncio.gather(*init_tasks)
        
        thinking, search_strategies = await combined_analysis_task
        
        yield {"type": "message", "content": "🔍 Searching documentation..."}
        
        parallel_strategies = []
        sequential_strategies = []
        
        search_strategies.sort(key=lambda s: {'high': 0, 'medium': 1, 'low': 2}.get(s.get('priority', 'medium'), 1))
        
        for strategy in search_strategies:
            if strategy["type"] in ["keyword_search", "specific_feature"]:
                parallel_strategies.append(strategy)
            else:
                sequential_strategies.append(strategy)
        
        if parallel_strategies:
            yield {"type": "message", "content": f"📍 Running {len(parallel_strategies)} parallel searches..."}
            parallel_results = await self._execute_parallel_strategies(parallel_strategies, query)
            for result in parallel_results:
                yield result
        
        for strategy in sequential_strategies:
            yield {"type": "message", "content": f"📍 {strategy['description']}..."}
            
            try:
                if strategy["type"] == "topic_search":
                    topic = strategy.get("topic", query)
                    async for result in self._topic_search(topic):
                        yield result
                        
                elif strategy["type"] == "file_exploration":
                    patterns = strategy.get("patterns", ["*.md", "*.txt"])
                    async for result in self._explore_files(patterns):
                        yield result
                        
                elif strategy["type"] == "deep_content_analysis":
                    files = strategy.get("files", [])
                    async for result in self._deep_content_analysis(files):
                        yield result
                        
                else:
                    async for result in self._general_exploration(query):
                        yield result
            except Exception as e:
                print(f"Error executing strategy {strategy.get('type', 'unknown')}: {e}")
                continue
        
        yield {"type": "message", "content": "🔬 Preparing answer..."}
        
        if not self.context_cache:
            yield {"type": "message", "content": "\n⚠️ **No relevant information found in the documentation.**\n\nI couldn't find any information about your query in the available documents. Please ensure your question relates to the documented topics."}
            return
        
        final_answer = await self._deep_synthesis(query)
        yield {"type": "message", "content": f"\n📋 **Answer:**\n\n{final_answer}"}
    
    async def _explore_structure(self):
        """Explore and cache the document structure"""
        tree_cmd = "find . -type f -name '*.md' -o -name '*.txt' -o -name '*.rst' | head -100"
        yield {"type": "command", "content": f"$ {tree_cmd}"}
        tree_output = await self._run_shell_command(tree_cmd)
        yield {"type": "result", "content": tree_output}
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine search strategy"""
        system_prompt = """Analyze the user query to determine the best search strategy.
        
        For technical queries about specific products or features (like "AI on A2"):
        - Extract the EXACT product/feature name (e.g., "A2", "a2")
        - Search for that specific term, not generic words
        
        Return strategy as:
        - type: "specific_feature" for product/feature queries
        - type: "keyword_search" for general information
        - type: "file_exploration" for file listing requests
        - keywords: most relevant technical terms (not generic words like "kind", "supported")
        - description: brief strategy description"""
        
        response = await self.gemini_client.generate_content(f"{system_prompt}\nQuery: {query}")
        
        query_lower = query.lower()
        
        if "a2" in query_lower or "A2" in query:
            strategy = {
                "type": "specific_feature",
                "keywords": ["A2", "a2"],
                "description": "Searching for A2-specific information"
            }
        elif any(term in query_lower for term in ["what", "which", "supported", "available"]) and \
             any(term in query_lower for term in ["ai", "model", "feature", "capability"]):
            keywords = []
            words = query.split()
            for word in words:
                if word.isupper() or (len(word) <= 3 and word.isalnum()):
                    keywords.append(word)
                elif word.lower() in ["ai", "model", "gpu", "cpu", "api"]:
                    keywords.append(word)
            
            if not keywords:
                keywords = self._extract_technical_keywords(query)
            
            strategy = {
                "type": "specific_feature",
                "keywords": keywords[:3],
                "description": f"Searching for specific features: {', '.join(keywords[:3])}"
            }
        elif "all" in query_lower and any(ext in query_lower for ext in ["md", "markdown", "files"]):
            strategy = {
                "type": "file_exploration",
                "patterns": ["*.md"],
                "description": "Exploring all Markdown files"
            }
        else:
            keywords = self._extract_technical_keywords(query)
            strategy = {
                "type": "keyword_search",
                "keywords": keywords,
                "description": f"Searching for: {', '.join(keywords)}"
            }
        
        return strategy
    
    async def _keyword_search(self, keywords: List[str]):
        """Search for keywords across all relevant files"""
        async for result in self._keyword_search_parallel(keywords):
            yield result
        
    async def _topic_search(self, topic: str):
        """Search for information about a specific topic"""
        patterns = [f"*{topic}*", f"*{topic.lower()}*", f"*{topic.upper()}*"]
        
        for pattern in patterns:
            find_cmd = f"find . -iname '{pattern}' -type f | head -10"
            yield {"type": "command", "content": f"$ {find_cmd}"}
            output = await self._run_shell_command(find_cmd)
            
            if output and "Error" not in output:
                yield {"type": "result", "content": output}
                
                files = output.split('\n')[:3]
                for file_path in files:
                    if file_path.strip():
                        cat_cmd = f"head -50 {file_path.strip()}"
                        yield {"type": "command", "content": f"$ {cat_cmd}"}
                        content = await self._run_shell_command(cat_cmd)
                        yield {"type": "result", "content": content[:500] + "..."}
    
    async def _explore_files(self, patterns: List[str]):
        """Explore files matching specific patterns"""
        for pattern in patterns:
            find_cmd = f"find . -name '{pattern}' -type f | grep -v '_build' | sort"
            yield {"type": "command", "content": f"$ {find_cmd}"}
            files_output = await self._run_shell_command(find_cmd)
            yield {"type": "result", "content": files_output}
            
            files = [f.strip() for f in files_output.split('\n') if f.strip()]
            
            dirs = {}
            for file_path in files:
                dir_name = '/'.join(file_path.split('/')[:-1]) or '.'
                if dir_name not in dirs:
                    dirs[dir_name] = []
                dirs[dir_name].append(file_path)
            
            for dir_name, dir_files in list(dirs.items())[:5]:
                yield {"type": "message", "content": f"Exploring {dir_name}/..."}
                
                for file_path in dir_files[:2]:
                    head_cmd = f"head -20 {file_path}"
                    yield {"type": "command", "content": f"$ {head_cmd}"}
                    content = await self._run_shell_command(head_cmd)
                    yield {"type": "result", "content": content[:300] + "..."}
    
    async def _general_exploration(self, query: str):
        """General exploration based on query"""
        tree_cmd = "tree -L 2 -d | head -30"
        yield {"type": "command", "content": f"$ {tree_cmd}"}
        tree_output = await self._run_shell_command(tree_cmd)
        
        if "Error" in tree_output:
            ls_cmd = "ls -la"
            yield {"type": "command", "content": f"$ {ls_cmd}"}
            tree_output = await self._run_shell_command(ls_cmd)
        
        yield {"type": "result", "content": tree_output}
        
        readme_cmd = "find . -iname 'readme*' -type f | head -10"
        yield {"type": "command", "content": f"$ {readme_cmd}"}
        readme_output = await self._run_shell_command(readme_cmd)
        
        if readme_output and "Error" not in readme_output:
            yield {"type": "result", "content": readme_output}
            
            readmes = readme_output.split('\n')
            if readmes and readmes[0].strip():
                cat_cmd = f"head -50 {readmes[0].strip()}"
                yield {"type": "command", "content": f"$ {cat_cmd}"}
                content = await self._run_shell_command(cat_cmd)
                yield {"type": "result", "content": content[:500] + "..."}
    
    def _detect_language(self, text: str) -> str:
        """Detect the language of the query"""
        japanese_pattern = re.compile(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]')
        if japanese_pattern.search(text):
            return 'japanese'
        return 'english'
    
    async def _synthesize_answer(self, original_query: str) -> str:
        """Synthesize final answer from gathered context"""
        query_language = self._detect_language(original_query)
        
        context_summary = f"Found {len(self.context_cache)} relevant files.\n"
        
        if self.file_structure:
            context_summary += f"Document structure: {self.file_structure['total_files']} files, "
            context_summary += f"{len(self.file_structure['directories'])} directories.\n"
            context_summary += f"File types: {dict(list(self.file_structure['file_types'].items())[:5])}\n"
        
        context_contents = []
        for path, content in list(self.context_cache.items())[:5]:
            context_contents.append(content[:500])
        
        language_instruction = "Answer in Japanese." if query_language == 'japanese' else "Answer in English."
        
        system_prompt = f"""Based on the search results and file contents explored, \n        provide a comprehensive answer to the user's query.\n        {language_instruction}\n        Do NOT mention specific file paths or file locations in your answer.\n        Focus on providing the information the user requested."""
        
        context = "\n\n".join(context_contents)
        
        response = await self.gemini_client.generate_content(f"{system_prompt}\nQuery: {original_query}\n\nContext:\n{context_summary}\n{context}")
        
        return response
    
    async def _init_file_structure(self):
        """Initialize file structure in the background"""
        structure_data = []
        async for result in self._explore_structure():
            structure_data.append(result)
        self.file_structure = self._parse_structure_from_results(structure_data)
    
    async def _execute_parallel_strategies(self, strategies: List[Dict], query: str) -> List[Dict]:
        """Execute multiple search strategies in parallel"""
        async def execute_strategy(strategy: Dict) -> List[Dict]:
            results = []
            try:
                if strategy["type"] == "keyword_search":
                    keywords = strategy.get("keywords", self._extract_keywords(query))
                    async for result in self._keyword_search_parallel(keywords):
                        results.append(result)
                elif strategy["type"] == "specific_feature":
                    keywords = strategy.get("keywords", self._extract_technical_keywords(query))
                    async for result in self._specific_feature_search_parallel(keywords):
                        results.append(result)
            except Exception as e:
                print(f"Error in parallel strategy {strategy['type']}: {e}")
            return results
        
        all_results = await asyncio.gather(
            *[execute_strategy(s) for s in strategies],
            return_exceptions=True
        )
        
        flattened_results = []
        for results in all_results:
            if isinstance(results, list):
                flattened_results.extend(results)
        
        return flattened_results
    
    async def _keyword_search_parallel(self, keywords: List[str]):
        """Parallel keyword search optimized for performance"""
        cache_key = f"keyword_search:{':'.join(sorted(keywords))}"
        if cache_key in self.search_cache:
            cache_entry = self.search_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.search_cache_ttl:
                self.performance_metrics['cache_hits'] += 1
                for result in cache_entry['results']:
                    yield result
                return
        
        self.performance_metrics['cache_misses'] += 1
        results_to_cache = []
        
        find_cmd = "find . -type f \\( -name '*.md' -o -name '*.txt' -o -name '*.rst' \\) | grep -v '_build' | head -50"
        self.performance_metrics['shell_commands'] += 1
        files_output = await self._run_shell_command(find_cmd)
        files = [f.strip() for f in files_output.split('\n') if f.strip()]
        
        async def grep_keyword(keyword: str):
            grep_cmd = f"grep -r -i -n '{keyword}' . --include='*.md' --include='*.txt' | head -20"
            self.performance_metrics['shell_commands'] += 1
            return keyword, await self._run_shell_command(grep_cmd)
        
        grep_results = await asyncio.gather(
            *[grep_keyword(kw) for kw in keywords[:3]],
            return_exceptions=True
        )
        
        file_matches = set()
        for result in grep_results:
            if isinstance(result, tuple) and result[1] and "Error" not in result[1]:
                keyword, output = result
                yield {"type": "command", "content": f"$ grep -r -i -n '{keyword}' . --include='*.md' --include='*.txt' | head -20"}
                yield {"type": "result", "content": output[:1000] + "..." if len(output) > 1000 else output}
                results_to_cache.extend([{"type": "command", "content": f"$ grep -r -i -n '{keyword}' . --include='*.md' --include='*.txt' | head -20"},
                                       {"type": "result", "content": output[:1000] + "..." if len(output) > 1000 else output}])
                
                for match in output.split('\n')[:5]:
                    if ':' in match:
                        file_path = match.split(':')[0]
                        file_matches.add(file_path)
        
        await self._read_files_batch(list(file_matches)[:10])
        
        self.search_cache[cache_key] = {
            'timestamp': time.time(),
            'results': results_to_cache
        }
    
    async def _specific_feature_search_parallel(self, keywords: List[str]):
        """Parallel specific feature search"""
        cache_key = f"feature_search:{':'.join(sorted(keywords))}"
        if cache_key in self.search_cache:
            cache_entry = self.search_cache[cache_key]
            if time.time() - cache_entry['timestamp'] < self.search_cache_ttl:
                self.performance_metrics['cache_hits'] += 1
                for result in cache_entry['results']:
                    yield result
                return
        
        self.performance_metrics['cache_misses'] += 1
        results_to_cache = []
        
        async def search_keyword(keyword: str, case_sensitive: bool = True):
            flag = "" if case_sensitive else "-i "
            grep_cmd = f"grep -r {flag}'{keyword}' . --include='*.md' --include='*.txt' | head -30"
            self.performance_metrics['shell_commands'] += 1
            return keyword, case_sensitive, await self._run_shell_command(grep_cmd)
        
        search_tasks = []
        for keyword in keywords[:3]:
            search_tasks.append(search_keyword(keyword, True))
            search_tasks.append(search_keyword(keyword, False))
        
        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        file_matches = set()
        for result in search_results:
            if isinstance(result, tuple) and result[2] and "Error" not in result[2] and len(result[2].strip()) > 10:
                keyword, case_sensitive, output = result
                flag = "" if case_sensitive else "-i "
                yield {"type": "command", "content": f"$ grep -r {flag}'{keyword}' . --include='*.md' --include='*.txt' | head -30"}
                yield {"type": "result", "content": output[:1500] + "..." if len(output) > 1500 else output}
                results_to_cache.extend([{"type": "command", "content": f"$ grep -r {flag}'{keyword}' . --include='*.md' --include='*.txt' | head -30"},
                                       {"type": "result", "content": output[:1500] + "..." if len(output) > 1500 else output}])
                
                for match in output.split('\n')[:10]:
                    if ':' in match:
                        file_path = match.split(':')[0]
                        file_matches.add(file_path)
        
        await self._read_files_batch(list(file_matches)[:15])
        
        self.search_cache[cache_key] = {
            'timestamp': time.time(),
            'results': results_to_cache
        }
    
    async def _read_files_batch(self, file_paths: List[str]):
        """Read multiple files concurrently with caching"""
        files_to_read = []
        for file_path in file_paths:
            if file_path not in self.context_cache:
                files_to_read.append(file_path)
        
        if not files_to_read:
            return
        
        async def read_file(file_path: str):
            cat_cmd = f"cat {file_path}"
            self.performance_metrics['shell_commands'] += 1
            content = await self._run_shell_command(cat_cmd)
            return file_path, content
        
        read_results = await asyncio.gather(
            *[read_file(fp) for fp in files_to_read[:10]],
            return_exceptions=True
        )
        
        for result in read_results:
            if isinstance(result, tuple) and result[1] and "Error" not in result[1]:
                file_path, content = result
                self._add_to_cache(file_path, content)
    
    def _add_to_cache(self, file_path: str, content: str):
        """Add content to cache with size management"""
        if len(content) > self.max_cache_content_size:
            content = content[:self.max_cache_content_size]
        
        if len(self.context_cache) >= self.max_cache_size:
            self.context_cache.popitem(last=False)
        
        self.context_cache[file_path] = content
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract keywords from query"""
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                     "of", "with", "by", "from", "about", "what", "where", "when", "how",
                     "is", "are", "was", "were", "been", "be", "have", "has", "had",
                     "do", "does", "did", "will", "would", "could", "should", "may", "might"}
        
        words = re.findall(r'\w+', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords[:5]
    
    def _extract_technical_keywords(self, query: str) -> List[str]:
        """Extract technical keywords from query"""
        technical_terms = {
            "ai", "ml", "api", "sdk", "gpu", "cpu", "model", "engine",
            "server", "client", "protocol", "format", "version",
            "feature", "capability", "support", "configuration"
        }
        
        words = re.findall(r'\\b[A-Za-z0-9]+\\b', query)
        keywords = []
        
        for word in words:
            if word.isupper() or (len(word) <= 3 and word.isalnum() and not word.isdigit()):
                keywords.append(word)
        
        for word in words:
            if word.lower() in technical_terms and word not in keywords:
                keywords.append(word)
        
        for word in words:
            if len(word) > 3 and word.lower() not in self._get_stop_words() and word not in keywords:
                keywords.append(word)
        
        return keywords[:5]
    
    def _get_stop_words(self):
        """Get stop words for filtering"""
        return {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", 
                "of", "with", "by", "from", "about", "what", "where", "when", "how",
                "is", "are", "was", "were", "been", "be", "have", "has", "had",
                "do", "does", "did", "will", "would", "could", "should", "may", "might",
                "kind", "type", "sort", "which", "that", "this", "these", "those"}
    
    async def _specific_feature_search(self, keywords: List[str]):
        """Search for specific features or products"""
        async for result in self._specific_feature_search_parallel(keywords):
            yield result
        
    def _parse_structure_from_results(self, results):
        """Parse structure from command results"""
        structure = {
            "total_files": 0,
            "file_types": {},
            "directories": set(),
            "md_files": [],
            "index_files": []
        }
        
        for result in results:
            if result.get("type") == "result" and result.get("content"):
                for line in result["content"].split('\n'):
                    if line.strip():
                        structure["total_files"] += 1
                        
                        if '.' in line:
                            ext = line.split('.')[-1]
                            structure["file_types"][ext] = structure["file_types"].get(ext, 0) + 1
                        
                        if '/' in line:
                            dir_path = '/'.join(line.split('/')[:-1])
                            structure["directories"].add(dir_path)
                        
                        if line.endswith('.md'):
                            structure["md_files"].append(line.strip())
                        if 'index' in line.lower():
                            structure["index_files"].append(line.strip())
        
        structure["directories"] = list(structure["directories"])
        return structure
    
    async def _combined_query_analysis(self, query: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Combined deep analysis and multi-step strategy generation in a single LLM call"""
        system_prompt = """You are analyzing a user query for a documentation search system.
        You work with a documentation-only system, no web search.
        
        Provide a JSON response with two sections:
        
        1. "analysis": Understanding of the query
           - understanding: Clear understanding of what the user is asking
           - key_concepts: List of key concepts and entities
           - implicit_requirements: Any implicit requirements or context
           - search_areas: Documentation areas to search
        
        2. "strategies": Multi-step search strategy (2-4 steps)
           Each step should have:
           - type: "keyword_search", "topic_search", "specific_feature", "file_exploration", or "deep_content_analysis"
           - description: Brief description of what this step will do
           - keywords/topic/patterns: Relevant search terms
           - priority: "high", "medium", or "low"
        
        For technical queries, start with specific terms then broaden.
        For general queries, start broad then narrow down.
        
        Return as JSON object with "analysis" and "strategies" keys."""
        
        self.performance_metrics['llm_calls'] += 1
        response = await self.gemini_client.generate_content(f"{system_prompt}\nQuery: {query}")
        
        try:
            result = json.loads(response)
            
            analysis = result.get('analysis', {})
            if not analysis:
                analysis = {
                    "understanding": "Query analysis",
                    "original_query": query
                }
            else:
                analysis["original_query"] = query
            
            strategies = result.get('strategies', [])
            if not strategies:
                strategies = [await self._analyze_query(query)]
            else:
                for strategy in strategies:
                    if 'type' not in strategy:
                        continue
                    
                    if strategy['type'] == 'keyword_search' and 'keywords' not in strategy:
                        strategy['keywords'] = self._extract_keywords(query)
                    elif strategy['type'] == 'specific_feature' and 'keywords' not in strategy:
                        strategy['keywords'] = self._extract_technical_keywords(query)
                    elif strategy['type'] == 'topic_search' and 'topic' not in strategy:
                        strategy['topic'] = query
                    elif strategy['type'] == 'file_exploration' and 'patterns' not in strategy:
                        strategy['patterns'] = ['*.md', '*.txt']
                    elif strategy['type'] == 'deep_content_analysis' and 'files' not in strategy:
                        strategy['files'] = []
                    
                    if 'description' not in strategy:
                        strategy['description'] = f"Performing {strategy['type']}"
            
            return analysis, strategies
            
        except Exception as e:
            print(f"Error parsing combined analysis: {e}")
            analysis = {
                "understanding": "Query analysis",
                "original_query": query
            }
            strategies = [await self._analyze_query(query)]
            return analysis, strategies
    
    async def _deep_content_analysis(self, files: List[str]):
        """Perform deep analysis on specific files"""
        for file_path in files[:5]:
            if file_path in self.context_cache:
                continue
                
            cat_cmd = f"cat {file_path}"
            yield {"type": "command", "content": f"$ {cat_cmd}"}
            content = await self._run_shell_command(cat_cmd)
            
            if content and "Error" not in content:
                self.context_cache[file_path] = content
                yield {"type": "result", "content": content[:2000] + "..." if len(content) > 2000 else content}
                
                analysis = await self._analyze_file_content(file_path, content)
                if analysis:
                    self.insights.append(f"From {file_path}: {analysis}")
    
    async def _analyze_file_content(self, file_path: str, content: str) -> str:
        """Analyze specific file content for insights"""
        system_prompt = """Analyze this file content and provide key insights.
        ONLY describe what is explicitly documented in this file.
        
        Focus on:
        1. Main topics covered in this document
        2. Important technical details stated here
        3. Code examples or configurations found in the text
        4. References to other documented features
        
        Be concise but thorough. Do NOT add external knowledge."""
        
        self.performance_metrics['llm_calls'] += 1
        response = await self.gemini_client.generate_content(f"{system_prompt}\nFile: {file_path}\n\nContent:\n{content[:3000]}")
        
        return response
    
    async def _analyze_findings(self) -> Optional[str]:
        """Analyze current findings for insights"""
        if not self.context_cache:
            return None
            
        recent_files = list(self.context_cache.keys())[-3:]
        if not recent_files:
            return None
            
        context_summary = "\n".join([
            f"File: {f}\nContent preview: {self.context_cache[f][:500]}..."
            for f in recent_files
        ])
        
        system_prompt = """Based on these documentation findings, what is the most important insight?
        ONLY state what is explicitly documented. Be very concise (1-2 sentences max)."""
        
        self.performance_metrics['llm_calls'] += 1
        response = await self.gemini_client.generate_content(f"{system_prompt}\nContext:\n{context_summary}")
        
        return response
    
    async def _deep_synthesis(self, original_query: str) -> str:
        """Perform deep synthesis with structured output"""
        all_files = list(self.context_cache.keys())
        context_parts = []
        
        file_relevance = {}
        for file_path in all_files:
            content = self.context_cache[file_path]
            score = 0
            keywords = self._extract_keywords(original_query) + self._extract_technical_keywords(original_query)
            for keyword in keywords:
                score += content.lower().count(keyword.lower())
            file_relevance[file_path] = score
        
        sorted_files = sorted(all_files, key=lambda f: file_relevance.get(f, 0), reverse=True)
        
        file_groups = {}
        for file_path in sorted_files[:20]:
            dir_name = file_path.split('/')[1] if '/' in file_path else 'root'
            if dir_name not in file_groups:
                file_groups[dir_name] = []
            file_groups[dir_name].append(file_path)
        
        for group, files in file_groups.items():
            group_context = f"\n### {group.upper()} Documentation:\n"
            for file_path in files[:3]:
                content = self.context_cache[file_path]
                group_context += f"\n**{file_path}:**\n{content[:1000]}...\n"
            context_parts.append(group_context)
        
        full_context = "\n".join(context_parts)
        insights_text = "\n".join([f"- {insight}" for insight in self.insights]) if self.insights else "None"
        
        system_prompt = f"""Based on the comprehensive search and analysis, provide a detailed answer.\n        \n        CRITICAL RULES:\n        1. ONLY use information found in the documentation\n        2. Do NOT make up or infer information not explicitly stated\n        3. If information is not found, clearly state that it's not documented\n        4. Do NOT use external knowledge or web information\n        \n        Original query: {original_query}\n        Query language: {self._detect_language(original_query)}\n        \n        Key insights discovered:\n        {insights_text}\n        \n        Structure your answer with:\n        1. **Direct Answer**: Clear, concise answer to the question (only from docs)\n        2. **Details**: Important technical details and explanations (only from docs)\n        3. **Examples**: Relevant examples or code snippets if found in docs\n        4. **Note**: If some aspects are not documented, mention this clearly\n        \n        Answer in the same language as the query.\n        Use markdown formatting for clarity.\n        Do NOT mention file paths.\n        Base your answer ONLY on the provided documentation context."""
        
        self.performance_metrics['llm_calls'] += 1
        response = await self.gemini_client.generate_content(f"{system_prompt}\nContext from search:\n{full_context[:8000]}")
        
        if self.debug_mode and self.performance_metrics['start_time']:
            elapsed = time.time() - self.performance_metrics['start_time']
            print(f"\nPerformance Metrics:")
            print(f"  Total time: {elapsed:.2f}s")
            print(f"  LLM calls: {self.performance_metrics['llm_calls']}")
            print(f"  Shell commands: {self.performance_metrics['shell_commands']}")
            print(f"  Cache hits: {self.performance_metrics['cache_hits']}")
            print(f"  Cache misses: {self.performance_metrics['cache_misses']}")
            print(f"  Cache hit rate: {self.performance_metrics['cache_hits'] / max(1, self.performance_metrics['cache_hits'] + self.performance_metrics['cache_misses']) * 100:.1f}%")
        
        return response