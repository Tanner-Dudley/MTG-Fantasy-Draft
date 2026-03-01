"""
Pydantic models that define the shape of every API request and response.

FastAPI uses these to:
1. Automatically validate incoming JSON bodies.
2. Serialize outgoing responses.
3. Generate interactive API docs at /docs.
"""

from __future__ import annotations

from pydantic import BaseModel


# ── Auth ──────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    password: str
    display_name: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    display_name: str


# ── Lobby ─────────────────────────────────────────────────────────────

class LobbyCreateRequest(BaseModel):
    name: str
    num_players: int = 4


class LobbyJoinRequest(BaseModel):
    lobby_code: str


class PlayerInfo(BaseModel):
    id: str
    display_name: str
    picks: list[str]


class CardInfo(BaseModel):
    id: str
    name: str
    image_url: str
    set_code: str
    rarity: str
    is_drafted: bool


class LobbyStateResponse(BaseModel):
    id: str
    code: str
    name: str
    status: str
    owner_id: str
    num_players_expected: int
    players: list[PlayerInfo]
    current_turn_user_id: str | None = None
    pool: list[CardInfo] | None = None


# ── Draft ─────────────────────────────────────────────────────────────

class PickRequest(BaseModel):
    card_id: str


class PickResponse(BaseModel):
    status: str
    draft_complete: bool
    next_turn_user_id: str | None = None
