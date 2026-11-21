import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from dataclasses import dataclass


from backend.database import Base, get_db
from backend.main import app
from backend.models import Card

@pytest.fixture
def engine():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False}, 
        poolclass=StaticPool,)
    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    test_engine.dispose()



@pytest.fixture
def client(engine):
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()


    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@dataclass
class Player:
    id: str
    headers: dict

@pytest.fixture
def cards(engine):
    TestingSession = sessionmaker(bind=engine)
    with TestingSession() as session:
        session.add_all(
            [Card(id=f"card-{i}", name=f"Test Card {i}") for i in range (40)]
        )
        session.commit()

@pytest.fixture
def make_player(client):
    def _make_player(name):
        response = client.post("/api/session", json={"screen_name": name})
        assert response.status_code == 200
        headers = {"Authorization": f"Bearer {response.json() ['access_token']}"}

        me = client.get("/api/me", headers=headers)
        return Player(id=me.json()["id"],
    headers=headers)

    return _make_player