"""
MTG Commander Draft -- FastAPI backend.

Run from the project root:
    uvicorn backend.main:app --reload

Then open http://localhost:8000/docs for interactive API documentation.
"""

import logging
import random
import string
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .auth import (
    create_access_token,
    get_current_user_id,
    hash_password,
    validate_password,
    verify_password,
)
from .database import get_db, init_db
from .models import Card, DraftPick, DraftPool, Lobby, LobbyUser, User
from .schemas import (
    CardInfo,
    LobbyCreateRequest,
    LobbyJoinRequest,
    LobbyStateResponse,
    LoginRequest,
    PickRequest,
    PickResponse,
    PlayerInfo,
    RegisterRequest,
    TokenResponse,
    UserResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Database tables verified / created.")
    yield


app = FastAPI(title="MTG Commander Draft API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Helpers ───────────────────────────────────────────────────────────

def _get_user_or_401(db: Session, user_id: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _get_lobby_or_404(db: Session, lobby_id: str) -> Lobby:
    lobby = db.query(Lobby).filter(Lobby.id == lobby_id).first()
    if not lobby:
        raise HTTPException(status_code=404, detail="Lobby not found")
    return lobby


def _generate_lobby_code(db: Session, length: int = 6) -> str:
    while True:
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if not db.query(Lobby).filter(Lobby.code == code).first():
            return code


def _player_ids_ordered(db: Session, lobby_id: str) -> list[str]:
    """Return user IDs in seat order for a lobby."""
    rows = (
        db.query(LobbyUser.user_id)
        .filter(LobbyUser.lobby_id == lobby_id)
        .order_by(LobbyUser.seat_index)
        .all()
    )
    return [r[0] for r in rows]


def _build_lobby_state(db: Session, lobby: Lobby) -> LobbyStateResponse:
    """Serialize a Lobby ORM object into the API response schema."""
    player_ids = _player_ids_ordered(db, lobby.id)

    players = []
    for uid in player_ids:
        user = db.query(User).filter(User.id == uid).first()
        picks = (
            db.query(DraftPick)
            .filter(DraftPick.lobby_id == lobby.id, DraftPick.user_id == uid)
            .order_by(DraftPick.pick_number)
            .all()
        )
        pick_names = [p.card.name for p in picks]
        players.append(
            PlayerInfo(id=uid, display_name=user.display_name, picks=pick_names)
        )

    current_turn_user_id = None
    pool_cards = None

    if lobby.status in ("drafting", "completed"):
        current_turn_user_id = player_ids[lobby.current_turn_index]

        pool_entries = (
            db.query(DraftPool).filter(DraftPool.lobby_id == lobby.id).all()
        )
        picked_ids = {
            row[0]
            for row in db.query(DraftPick.card_id)
            .filter(DraftPick.lobby_id == lobby.id)
            .all()
        }
        pool_cards = [
            CardInfo(
                id=pe.card.id,
                name=pe.card.name,
                image_url=pe.card.image_url or "",
                set_code=pe.card.set_code or "",
                rarity=pe.card.rarity or "",
                is_drafted=pe.card.id in picked_ids,
            )
            for pe in pool_entries
        ]

    return LobbyStateResponse(
        id=lobby.id,
        code=lobby.code,
        name=lobby.name,
        status=lobby.status,
        owner_id=lobby.owner_id,
        num_players_expected=lobby.num_players_expected,
        players=players,
        current_turn_user_id=current_turn_user_id,
        pool=pool_cards,
    )


# ══════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/register", response_model=TokenResponse)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == req.username.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="Username already taken")

    pw_error = validate_password(req.password)
    if pw_error:
        raise HTTPException(status_code=422, detail=pw_error)

    user = User(
        username=req.username.lower(),
        display_name=req.display_name,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user.id))


@app.post("/api/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username.lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return TokenResponse(access_token=create_access_token(user.id))


@app.get("/api/me", response_model=UserResponse)
def get_me(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = _get_user_or_401(db, user_id)
    return UserResponse(id=user.id, username=user.username, display_name=user.display_name)


# ══════════════════════════════════════════════════════════════════════
#  LOBBY ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/lobbies", response_model=LobbyStateResponse)
def create_lobby(
    req: LobbyCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)

    if not 2 <= req.num_players <= 12:
        raise HTTPException(status_code=422, detail="num_players must be between 2 and 12")

    lobby = Lobby(
        code=_generate_lobby_code(db),
        name=req.name,
        owner_id=user_id,
        num_players_expected=req.num_players,
    )
    db.add(lobby)
    db.flush()

    db.add(LobbyUser(lobby_id=lobby.id, user_id=user_id, seat_index=0))
    db.commit()
    db.refresh(lobby)

    return _build_lobby_state(db, lobby)


@app.post("/api/lobbies/join", response_model=LobbyStateResponse)
def join_lobby(
    req: LobbyJoinRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)

    lobby = db.query(Lobby).filter(Lobby.code == req.lobby_code.upper()).first()
    if not lobby:
        raise HTTPException(status_code=404, detail="Invalid lobby code")

    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Lobby is not accepting new players")

    already_in = (
        db.query(LobbyUser)
        .filter(LobbyUser.lobby_id == lobby.id, LobbyUser.user_id == user_id)
        .first()
    )
    if already_in:
        raise HTTPException(status_code=400, detail="You are already in this lobby")

    player_count = (
        db.query(LobbyUser).filter(LobbyUser.lobby_id == lobby.id).count()
    )
    if player_count >= lobby.num_players_expected:
        raise HTTPException(status_code=400, detail="Lobby is full")

    db.add(LobbyUser(lobby_id=lobby.id, user_id=user_id, seat_index=player_count))
    db.commit()
    db.refresh(lobby)

    return _build_lobby_state(db, lobby)


@app.get("/api/lobbies/{lobby_id}", response_model=LobbyStateResponse)
def get_lobby(
    lobby_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)
    lobby = _get_lobby_or_404(db, lobby_id)

    is_member = (
        db.query(LobbyUser)
        .filter(LobbyUser.lobby_id == lobby.id, LobbyUser.user_id == user_id)
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not in this lobby")

    return _build_lobby_state(db, lobby)


# ══════════════════════════════════════════════════════════════════════
#  DRAFT ROUTES
# ══════════════════════════════════════════════════════════════════════

@app.post("/api/lobbies/{lobby_id}/start", response_model=LobbyStateResponse)
def start_draft(
    lobby_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)
    lobby = _get_lobby_or_404(db, lobby_id)

    if lobby.owner_id != user_id:
        raise HTTPException(status_code=403, detail="Only the lobby owner can start the draft")
    if lobby.status != "waiting":
        raise HTTPException(status_code=400, detail="Draft already started or completed")

    player_count = db.query(LobbyUser).filter(LobbyUser.lobby_id == lobby.id).count()
    if player_count < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 players to start")

    pool_size = player_count * 5

    total_cards = db.query(Card).count()
    if total_cards == 0:
        raise HTTPException(
            status_code=500,
            detail="No cards in database. Run:  python -m backend.seed_cards",
        )
    if total_cards < pool_size:
        raise HTTPException(status_code=500, detail=f"Not enough cards ({total_cards})")

    all_card_ids = [row[0] for row in db.query(Card.id).all()]
    selected_ids = random.sample(all_card_ids, pool_size)

    for card_id in selected_ids:
        db.add(DraftPool(lobby_id=lobby.id, card_id=card_id))

    lobby.status = "drafting"
    lobby.current_turn_index = 0
    lobby.direction = 1
    lobby.num_players_expected = player_count
    db.commit()
    db.refresh(lobby)

    logger.info(
        "Draft started in lobby %s with %d players, %d cards",
        lobby_id, player_count, pool_size,
    )
    return _build_lobby_state(db, lobby)


@app.post("/api/lobbies/{lobby_id}/pick", response_model=PickResponse)
def make_pick(
    lobby_id: str,
    req: PickRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)
    lobby = _get_lobby_or_404(db, lobby_id)

    if lobby.status != "drafting":
        raise HTTPException(status_code=400, detail="Draft is not in progress")

    player_ids = _player_ids_ordered(db, lobby.id)
    expected_user = player_ids[lobby.current_turn_index]
    if user_id != expected_user:
        raise HTTPException(status_code=403, detail="It is not your turn")

    in_pool = (
        db.query(DraftPool)
        .filter(DraftPool.lobby_id == lobby.id, DraftPool.card_id == req.card_id)
        .first()
    )
    if not in_pool:
        raise HTTPException(status_code=400, detail="Card is not in this draft pool")

    already_picked = (
        db.query(DraftPick)
        .filter(DraftPick.lobby_id == lobby.id, DraftPick.card_id == req.card_id)
        .first()
    )
    if already_picked:
        raise HTTPException(status_code=400, detail="Card has already been drafted")

    pick_number = (
        db.query(DraftPick).filter(DraftPick.lobby_id == lobby.id).count()
    )
    db.add(DraftPick(
        lobby_id=lobby.id,
        user_id=user_id,
        card_id=req.card_id,
        pick_number=pick_number,
    ))

    # ── Snake draft turn advancement (mirrors Draft.py logic) ──
    num_players = len(player_ids)
    next_index = lobby.current_turn_index + lobby.direction

    if next_index >= num_players:
        lobby.current_turn_index = num_players - 1
        lobby.direction = -1
    elif next_index < 0:
        lobby.current_turn_index = 0
        lobby.direction = 1
    else:
        lobby.current_turn_index = next_index

    pool_size = db.query(DraftPool).filter(DraftPool.lobby_id == lobby.id).count()
    draft_complete = (pick_number + 1) == pool_size

    if draft_complete:
        lobby.status = "completed"
        logger.info("Draft completed in lobby %s", lobby_id)

    db.commit()
    db.refresh(lobby)

    current_player_ids = _player_ids_ordered(db, lobby.id)

    return PickResponse(
        status="ok",
        draft_complete=draft_complete,
        next_turn_user_id=current_player_ids[lobby.current_turn_index],
    )


@app.get("/api/lobbies/{lobby_id}/results", response_model=LobbyStateResponse)
def get_results(
    lobby_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    _get_user_or_401(db, user_id)
    lobby = _get_lobby_or_404(db, lobby_id)

    is_member = (
        db.query(LobbyUser)
        .filter(LobbyUser.lobby_id == lobby.id, LobbyUser.user_id == user_id)
        .first()
    )
    if not is_member:
        raise HTTPException(status_code=403, detail="You are not in this lobby")

    return _build_lobby_state(db, lobby)


# ══════════════════════════════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════════════════════════════

@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    card_count = db.query(Card).count()
    return {"status": "ok", "cards_loaded": card_count}
