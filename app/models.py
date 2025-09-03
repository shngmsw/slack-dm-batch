from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, validator
import uuid
from datetime import datetime

class User(BaseModel):
    id: str = Field(..., description="Slack user ID")
    name: str = Field(..., description="Slack username")
    display_name: str = Field(..., description="Display name")
    real_name: Optional[str] = Field(None, description="Real name")
    email: Optional[str] = Field(None, description="Email address")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "U123ABC456",
                "name": "john.doe",
                "display_name": "John Doe",
                "real_name": "John Doe",
                "email": "john.doe@company.com"
            }
        }

class MessageTemplate(BaseModel):
    content: str = Field(..., description="Message template with variables")
    variables: List[str] = Field(default_factory=list, description="Extracted variables")
    
    @validator('content')
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Hello {name}, welcome to {company}!",
                "variables": ["name", "company"]
            }
        }

class ParseMentionsRequest(BaseModel):
    text: str = Field(..., description="Text containing @mentions")
    token: str = Field(..., description="Slack token")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "@john.doe @jane.smith Hello everyone!",
                "token": "xoxp-..."
            }
        }

class ParseMentionsResponse(BaseModel):
    users: List[User] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
class PreviewRequest(BaseModel):
    template: str = Field(..., description="Message template")
    user_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="User variables")
    
    class Config:
        json_schema_extra = {
            "example": {
                "template": "Hello {name}, welcome to {company}!",
                "user_data": {
                    "U123ABC456": {"name": "John", "company": "ACME Corp"}
                }
            }
        }

class PreviewResponse(BaseModel):
    rendered_messages: Dict[str, str] = Field(default_factory=dict, description="User ID to rendered message mapping")
    missing_variables: List[str] = Field(default_factory=list)
    available_variables: List[str] = Field(default_factory=list)

class SendRequest(BaseModel):
    template: str = Field(..., description="Message template")
    users: List[User] = Field(..., description="Target users")
    user_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="User-specific variables")
    token: str = Field(..., description="Slack token")
    
    @validator('users')
    def validate_users(cls, v):
        if not v:
            raise ValueError("At least one user is required")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "template": "Hello {name}, welcome to {company}!",
                "users": [
                    {"id": "U123ABC456", "name": "john.doe", "display_name": "John Doe"}
                ],
                "user_data": {
                    "U123ABC456": {"name": "John", "company": "ACME Corp"}
                },
                "token": "xoxp-..."
            }
        }

class SendResult(BaseModel):
    job_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    total_users: int = Field(default=0)
    sent_count: int = Field(default=0)
    failed_count: int = Field(default=0)
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    status: str = Field(default="pending")  # pending, running, completed, failed
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)
    
    class Config:
        json_schema_extra = {
            "example": {
                "job_id": "job-123abc",
                "total_users": 2,
                "sent_count": 1,
                "failed_count": 1,
                "errors": [
                    {"user_id": "U456", "error": "User not found"}
                ],
                "status": "completed",
                "started_at": "2023-12-01T10:00:00Z",
                "completed_at": "2023-12-01T10:00:30Z"
            }
        }

class ImportVariablesResponse(BaseModel):
    imported_count: int = Field(default=0)
    user_data: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "imported_count": 2,
                "user_data": {
                    "U123ABC456": {"name": "John", "company": "ACME Corp"},
                    "U789DEF012": {"name": "Jane", "company": "XYZ Inc"}
                },
                "errors": []
            }
        }

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Invalid token",
                "details": "The provided Slack token is invalid or expired"
            }
        }