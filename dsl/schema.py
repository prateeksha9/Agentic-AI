# dsl/schema.py
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, validator


class DSLAction(BaseModel):
    """Represents one step in the action plan."""
    action: Literal["open", "find_and_click", "fill", "wait_for", "expect", "press"]
    target: Optional[str] = None       # e.g., button text, selector, field label
    value: Optional[str] = None        # e.g., text to fill
    extra: Optional[Dict[str, Any]] = None  # optional args like timeout

    @validator("target", always=True)
    def clean_target(cls, v):
        return v.strip() if isinstance(v, str) else v
