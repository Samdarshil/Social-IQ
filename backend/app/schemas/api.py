"""Request/response validation. Input is validated and control characters are stripped."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.content import CATEGORIES, CONTENT_TYPES

_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(v: str) -> str:
    return _CTRL.sub("", v).strip()


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(default="", max_length=80)

    @field_validator("display_name")
    @classmethod
    def _dn(cls, v): return clean_text(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class PredictIn(BaseModel):
    title: str = Field(default="", max_length=200)
    platform: Literal["youtube", "instagram", "x", "linkedin"]
    category: str
    content_type: str
    duration_sec: int | None = Field(default=None, ge=0, le=14400)
    publish_at: datetime

    @field_validator("title")
    @classmethod
    def _t(cls, v): return clean_text(v)

    @field_validator("category")
    @classmethod
    def _c(cls, v):
        if v not in CATEGORIES:
            raise ValueError(f"category must be one of {CATEGORIES}")
        return v

    @model_validator(mode="after")
    def _ct(self):
        if self.content_type not in CONTENT_TYPES[self.platform]:
            raise ValueError(f"content_type for {self.platform} must be one of {CONTENT_TYPES[self.platform]}")
        return self


class BatchPredictIn(BaseModel):
    items: list[PredictIn] = Field(min_length=1, max_length=5)


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=12)

    @field_validator("message")
    @classmethod
    def _m(cls, v):
        v = clean_text(v)
        if not v:
            raise ValueError("message is empty")
        return v
