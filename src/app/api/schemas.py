"""Esquemas Pydantic para la API REST (request/response DTOs)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = None
    timezone: str = "Europe/Madrid"


class UserOut(BaseModel):
    id: str
    email: str
    phone: str | None = None
    timezone: str
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginForm(BaseModel):
    username: str
    password: str


class BoutSubscriptionCreate(BaseModel):
    event_id: str
    bout_id: str
    target_match_number: int
    previous_bout_id: str | None = None
    previous_match_number: int | None = None
    lead_minutes: int = 15


class BoutSubscriptionOut(BaseModel):
    id: str
    user_id: str
    event_id: str
    bout_id: str
    target_match_number: int
    previous_bout_id: str | None = None
    previous_match_number: int | None = None
    lead_minutes: int
    status: str

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: str
    subscription_id: str
    user_id: str
    bout_id: str
    fired_at: datetime
    status: str
    attempts: int
    notifier_response: str | None = None

    model_config = {"from_attributes": True}
