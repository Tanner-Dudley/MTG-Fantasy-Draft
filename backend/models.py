"""
SQLAlchemy ORM models -- one class per database table.

Each class defines:
  - __tablename__: the actual SQL table name
  - Columns: the fields stored in each row
  - Relationships: convenient Python-level links between related tables

When you do  db.query(User).filter(User.username == "alice").first()
SQLAlchemy turns that into  SELECT * FROM users WHERE username = 'alice' LIMIT 1
and returns a User object whose attributes are the column values.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from .database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=_new_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    display_name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=_utcnow)


class Lobby(Base):
    __tablename__ = "lobbies"

    id = Column(String, primary_key=True, default=_new_uuid)
    code = Column(String(6), unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    status = Column(String, default="waiting")  # waiting | drafting | completed
    num_players_expected = Column(Integer, nullable=False)
    current_turn_index = Column(Integer, default=0)
    direction = Column(Integer, default=1)
    created_at = Column(DateTime, default=_utcnow)

    owner = relationship("User")
    players = relationship(
        "LobbyUser", back_populates="lobby", order_by="LobbyUser.seat_index"
    )


class LobbyUser(Base):
    """Maps users to lobbies and tracks their seat (draft order)."""
    __tablename__ = "lobby_users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lobby_id = Column(String, ForeignKey("lobbies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    seat_index = Column(Integer, nullable=False)

    lobby = relationship("Lobby", back_populates="players")
    user = relationship("User")


class Card(Base):
    __tablename__ = "cards"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    set_code = Column(String)
    rarity = Column(String)
    color_identity = Column(JSON)
    image_url = Column(String)
    scryfall_data = Column(JSON)


class DraftPool(Base):
    """Links a lobby to the specific cards available in its draft pool."""
    __tablename__ = "draft_pools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lobby_id = Column(String, ForeignKey("lobbies.id"), nullable=False)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)

    card = relationship("Card")


class DraftPick(Base):
    """Records each individual pick a user makes during a draft."""
    __tablename__ = "draft_picks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lobby_id = Column(String, ForeignKey("lobbies.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    card_id = Column(String, ForeignKey("cards.id"), nullable=False)
    pick_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utcnow)

    card = relationship("Card")
    user = relationship("User")
