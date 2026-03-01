"""
Smoke test for the database-backed backend API.

Prerequisites:
  1. Seed the database:    python -m backend.seed_cards
  2. Start the server:     uvicorn backend.main:app --reload
  3. Run this test:        python test_api.py
"""

import requests
import sys

BASE = "http://localhost:8000/api"


def main():
    # 0. Health check & card count
    print("=== Health Check ===")
    r = requests.get(f"{BASE}/health")
    if r.status_code != 200:
        print(f"Server not reachable (status {r.status_code}). Is it running?")
        sys.exit(1)
    info = r.json()
    print(f"  Status: {info['status']}, Cards loaded: {info['cards_loaded']}")
    if info["cards_loaded"] == 0:
        print("\n  No cards in database! Run:  python -m backend.seed_cards")
        print("  Then re-run this test.")
        sys.exit(1)

    # 1. Register two users
    print("\n=== Register User 1 (Alice) ===")
    r1 = requests.post(
        f"{BASE}/register",
        json={"username": "alice", "password": "Test@1234", "display_name": "Alice"},
    )
    print(f"  {r1.status_code} - got token: {bool(r1.json().get('access_token'))}")
    token1 = r1.json()["access_token"]

    print("\n=== Register User 2 (Bob) ===")
    r2 = requests.post(
        f"{BASE}/register",
        json={"username": "bob", "password": "Test@5678", "display_name": "Bob"},
    )
    print(f"  {r2.status_code} - got token: {bool(r2.json().get('access_token'))}")
    token2 = r2.json()["access_token"]

    h1 = {"Authorization": f"Bearer {token1}"}
    h2 = {"Authorization": f"Bearer {token2}"}

    # 2. Test /me
    print("\n=== GET /me (Alice) ===")
    r = requests.get(f"{BASE}/me", headers=h1)
    me = r.json()
    print(f"  {r.status_code} - {me['display_name']} ({me['username']})")

    # 3. Create lobby (Alice)
    print("\n=== Create Lobby ===")
    r = requests.post(
        f"{BASE}/lobbies", json={"name": "Test Draft", "num_players": 2}, headers=h1
    )
    lobby = r.json()
    lobby_id = lobby["id"]
    code = lobby["code"]
    print(f"  {r.status_code}")
    print(f"  Lobby ID:   {lobby_id}")
    print(f"  Lobby Code: {code}")
    print(f"  Status:     {lobby['status']}")
    print(f"  Players:    {[p['display_name'] for p in lobby['players']]}")

    # 4. Bob joins
    print("\n=== Bob Joins ===")
    r = requests.post(f"{BASE}/lobbies/join", json={"lobby_code": code}, headers=h2)
    j = r.json()
    print(f"  {r.status_code}")
    print(f"  Players: {[p['display_name'] for p in j['players']]}")

    # 5. Start draft
    print("\n=== Start Draft ===")
    r = requests.post(f"{BASE}/lobbies/{lobby_id}/start", headers=h1)
    state = r.json()
    print(f"  {r.status_code}")
    print(f"  Status:       {state['status']}")
    print(f"  Pool size:    {len(state['pool'])}")
    print(f"  Current turn: {state['current_turn_user_id']}")

    alice_id = lobby["owner_id"]
    bob_id = [p["id"] for p in j["players"] if p["id"] != alice_id][0]

    def header_for(uid):
        return h1 if uid == alice_id else h2

    def name_for(uid):
        return "Alice" if uid == alice_id else "Bob"

    # 6. Draft all 10 cards
    print("\n=== Drafting All Cards ===")
    for i in range(10):
        r = requests.get(f"{BASE}/lobbies/{lobby_id}", headers=h1)
        st = r.json()
        turn_uid = st["current_turn_user_id"]
        available = [c for c in st["pool"] if not c["is_drafted"]]
        card = available[0]

        r = requests.post(
            f"{BASE}/lobbies/{lobby_id}/pick",
            json={"card_id": card["id"]},
            headers=header_for(turn_uid),
        )
        pick = r.json()
        print(f"  Pick {i+1:>2}: {name_for(turn_uid)} drafts '{card['name']}' | complete={pick['draft_complete']}")

    # 7. Results
    print("\n=== Results ===")
    r = requests.get(f"{BASE}/lobbies/{lobby_id}/results", headers=h1)
    results = r.json()
    for p in results["players"]:
        print(f"  {p['display_name']}: {p['picks']}")

    # 8. Verify persistence -- re-fetch results to confirm DB stored everything
    print("\n=== Persistence Check (re-fetch results) ===")
    r = requests.get(f"{BASE}/lobbies/{lobby_id}/results", headers=h2)
    results2 = r.json()
    total_picks = sum(len(p["picks"]) for p in results2["players"])
    print(f"  Total picks from DB: {total_picks}")
    assert total_picks == 10, f"Expected 10 picks, got {total_picks}"

    print("\n=== ALL TESTS PASSED ===")


if __name__ == "__main__":
    main()
