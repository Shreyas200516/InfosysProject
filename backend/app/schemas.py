"""Request models with input validation (Milestone 1: validate ticket input)."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

EMAIL_PATTERN = r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$"


class TicketCreate(BaseModel):
    subject: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=10, max_length=5000)
    department: Optional[str] = Field(None, max_length=100)
    source: Literal["portal", "email", "service_desk"] = "portal"
    # Optional business context; inferred from the text when omitted.
    business_impact: Optional[Literal["critical", "high", "medium", "low"]] = None
    affected_users: Optional[int] = Field(None, ge=1, le=1_000_000)
    service_criticality: Optional[Literal["tier_1", "tier_2", "tier_3", "tier_4"]] = None
    run_agents: bool = True

    @field_validator("subject", "description")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = " ".join(v.split()) if "\n" not in v else v.strip()
        if not v:
            raise ValueError("must not be blank")
        return v


class AnalyzeRequest(BaseModel):
    subject: str = Field("", max_length=200)
    description: str = Field("", max_length=5000)
    business_impact: Optional[Literal["critical", "high", "medium", "low"]] = None
    affected_users: Optional[int] = Field(None, ge=1, le=1_000_000)
    service_criticality: Optional[Literal["tier_1", "tier_2", "tier_3", "tier_4"]] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)
    top_k: int = Field(3, ge=1, le=10)


class StatusUpdate(BaseModel):
    status: Literal["Open", "In Progress", "Escalated", "AI Resolved", "Resolved", "Closed"]
    note: Optional[str] = Field(None, max_length=1000)
    performed_by: str = "support_engineer"


class SignupRequest(BaseModel):
    """`role` is the role the person is *asking for*. Everyone starts as an employee; staff roles need admin approval."""
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=200)
    password: str = Field(..., min_length=8, max_length=128)
    role: Literal["employee", "support_engineer", "admin"] = "employee"

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("must be at least 2 characters")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("must contain at least one letter and one number")
        return v


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=200)
    password: str = Field(..., min_length=1, max_length=128)
