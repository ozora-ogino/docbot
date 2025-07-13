import re
import os
from typing import List, Tuple, Set
import shlex
from pathlib import Path


class CommandValidator:
    """Enhanced security validator for shell commands"""
    
    # Read-only commands whitelist
    ALLOWED_COMMANDS = {
        "ls", "cat", "head", "tail", "grep", "rg", "find", 
        "wc", "sort", "uniq", "awk", "cut", "tr",
        "file", "stat", "du", "tree", "pwd", "less", "more"
    }
    
    # Dangerous operations that must be blocked
    FORBIDDEN_PATTERNS = [
        # File modification
        r"\brm\b", r"\bmv\b", r"\bcp\b", r"\btouch\b", r"\bmkdir\b", r"\brmdir\b",
        # Output redirection (but allow pipe to head/tail/grep)
        r">\s*[^|]", r">>\s*", r"<\s*[^<]",
        # Permission changes
        r"\bchmod\b", r"\bchown\b", r"\bchgrp\b",
        # System commands
        r"\bdd\b", r"\bmkfs\b", r"\bfdisk\b", r"\bmount\b", r"\bumount\b",
        # Process control
        r"\bkill\b", r"\bpkill\b", r"\bkillall\b",
        # Network operations
        r"\bwget\b", r"\bcurl\b", r"\bscp\b", r"\brsync\b",
        # Package management
        r"\bapt\b", r"\bapt-get\b", r"\byum\b", r"\bdnf\b", r"\bpip\b", r"\bnpm\b",
        # Shell features (but allow pipe)
        r";\s*", r"&&", r"\$\(", r"\${",
        # Command substitution
        r"`[^`]+`",
        # Editor commands
        r"\bvi\b", r"\bvim\b", r"\bnano\b", r"\bemacs\b", r"\bed\b"
    ]
    
    # Allowed file extensions for reading
    ALLOWED_EXTENSIONS = {
        '.txt', '.md', '.log', '.json', '.yaml', '.yml', '.xml',
        '.csv', '.tsv', '.conf', '.cfg', '.ini', '.properties',
        '.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.go',
        '.rs', '.rb', '.php', '.html', '.css', '.scss', '.less'
    }
    
    WORKSPACE_DIR = "/workspace/document"
    MAX_COMMAND_LENGTH = 500
    
    @classmethod
    def validate_command(cls, command: str) -> Tuple[bool, str]:
        """Comprehensive command validation"""
        if not command:
            return False, "Empty command"
        
        command = command.strip()
        
        # Length check
        if len(command) > cls.MAX_COMMAND_LENGTH:
            return False, f"Command too long (max {cls.MAX_COMMAND_LENGTH} chars)"
        
        # Check for forbidden patterns
        for pattern in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Forbidden operation detected"
        
        # Parse command safely
        try:
            # Handle pipes separately
            if '|' in command:
                # Validate each part of the pipe
                pipe_parts = command.split('|')
                for part in pipe_parts:
                    part = part.strip()
                    if not part:
                        continue
                    part_tokens = shlex.split(part)
                    if not part_tokens:
                        continue
                    part_cmd = part_tokens[0]
                    if part_cmd not in cls.ALLOWED_COMMANDS:
                        return False, f"Command '{part_cmd}' in pipe is not allowed"
                    # Validate paths in this part
                    for token in part_tokens[1:]:
                        if not cls._validate_path(token, part_cmd):
                            return False, f"Invalid path in pipe: {token}"
                return True, "Command validated"
            
            parts = shlex.split(command)
            if not parts:
                return False, "Empty command after parsing"
            
            cmd = parts[0]
            
            # Validate command is in whitelist
            if cmd not in cls.ALLOWED_COMMANDS:
                return False, f"Command '{cmd}' is not allowed. Use only read operations."
            
            # Validate all paths in arguments
            for i, part in enumerate(parts[1:], 1):
                if not cls._validate_path(part, cmd):
                    return False, f"Invalid or forbidden path: {part}"
            
            # Special validation for specific commands
            if cmd == "find":
                if not cls._validate_find_command(parts):
                    return False, "Find command contains forbidden operations"
            
            if cmd == "awk":
                if not cls._validate_awk_command(parts):
                    return False, "Awk command contains forbidden operations"
            
            return True, "Command validated"
            
        except Exception as e:
            return False, f"Command parsing error: {str(e)}"
    
    @classmethod
    def _validate_path(cls, path: str, command: str) -> bool:
        """Validate individual path arguments"""
        # Skip command flags
        if path.startswith('-'):
            return True
        
        # No path traversal
        if '..' in path:
            return False
        
        # Convert to absolute path for checking
        if path.startswith('/'):
            abs_path = path
        else:
            abs_path = os.path.join(cls.WORKSPACE_DIR, path)
        
        # Must be within workspace
        try:
            resolved = str(Path(abs_path).resolve())
            if not resolved.startswith(cls.WORKSPACE_DIR):
                return False
        except:
            # If path resolution fails, it's likely invalid
            return False
        
        return True
    
    @classmethod
    def _validate_find_command(cls, parts: List[str]) -> bool:
        """Special validation for find command"""
        # Block -exec, -execdir, -ok, -okdir
        forbidden_find_flags = {'-exec', '-execdir', '-ok', '-okdir', '-delete'}
        for part in parts:
            if part in forbidden_find_flags:
                return False
        return True
    
    @classmethod
    def _validate_awk_command(cls, parts: List[str]) -> bool:
        """Special validation for awk command"""
        # Block system() calls and getline with commands
        awk_script = ' '.join(parts[1:])
        if 'system(' in awk_script or 'getline <' in awk_script:
            return False
        return True