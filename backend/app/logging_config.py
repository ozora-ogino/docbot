import logging
import sys
from datetime import datetime
import json
from typing import Any, Dict


class SecurityLogger:
    """Security-focused logger for command execution"""
    
    def __init__(self, name: str = "docbot.security"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # JSON formatter for structured logs
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"module": "%(name)s", "message": %(message)s}'
        )
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_command_attempt(self, command: str, session_id: str, 
                          validated: bool, reason: str = ""):
        """Log command execution attempts"""
        log_data = {
            "event": "command_attempt",
            "command": command[:200],  # Truncate long commands
            "session_id": session_id,
            "validated": validated,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if validated:
            self.logger.info(json.dumps(log_data))
        else:
            self.logger.warning(json.dumps(log_data))
    
    def log_command_result(self, command: str, session_id: str, 
                         success: bool, output_size: int):
        """Log command execution results"""
        log_data = {
            "event": "command_result",
            "command": command[:200],
            "session_id": session_id,
            "success": success,
            "output_size": output_size,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.logger.info(json.dumps(log_data))


security_logger = SecurityLogger()