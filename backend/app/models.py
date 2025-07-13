from pydantic import BaseModel
from typing import Optional, Literal


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    debug_mode: Optional[bool] = False
    model: Optional[Literal["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"]] = "gpt-4o"


class ChatResponse(BaseModel):
    type: str  # "message", "command", "result", "error"
    content: str
    session_id: Optional[str] = None