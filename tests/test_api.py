def start_draft(client, players):
    # 1. Player[0] creates a lobby sized len(players)
    owner = players[0]

    lobby = client.post(
        "/api/lobbies",
        json={"name": "Test Lobby", "num_players": len(players)},
        headers=owner.headers,
    ).json()

    # 2. Everyone else joins with the lobby's code
    for player in players[1:]:
        client.post(
            "/api/lobbies/join",
            json={"lobby_code": lobby["code"]},
            headers=player.headers,
        )

    # 3. Players[0] starts it
    response = client.post(f"/api/lobbies/{lobby['id']}/start", headers=owner.headers)

    # 4. Return the JSON state from the start response
    return response.json()

def test_health_check_uses_empty_test_database(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status" : "ok", "cards_loaded" :0}


def test_owner_can_start_draft_with_two_players(client, cards, make_player):
    alice = make_player("alice")
    bob = make_player("bob")

    state = start_draft(client, [alice, bob])

    assert state["status"] == "drafting"
    assert len(state["pool"]) == 10
    assert state["current_turn_user_id"] == alice.id


def test_cannot_pick_out_of_turn(client, cards, make_player):
    alice= make_player("alice")
    bob = make_player("bob")
    state = start_draft(client, [alice, bob])

    card_id=state["pool"][0]["id"]
    response = client.post(f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers=bob.headers,)
    assert response.status_code == 403    


def test_cannot_pick_card_aleady_taken(client, cards, make_player):
    alice= make_player("alice")
    bob = make_player("bob")
    state = start_draft(client, [alice, bob])

    card_id=state["pool"][0]["id"]

    #Alice is successfully able to pick the card
    client.post(f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers= alice.headers,)
   
    #Bob is not able to pick the same card
    response = client.post(f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers=bob.headers,)
    assert response.status_code == 400
    assert response.json()["detail"] == "Card has already been drafted"   



def test_cannot_pick_card_not_in_pool(client, cards, make_player):
    alice= make_player("alice")
    bob = make_player("bob")
    state = start_draft(client, [alice, bob])   

    response = client.post(f"/api/lobbies/{state['id']}/pick", json={"card_id": "not-a-card"}, headers=alice.headers,) 
    assert response.status_code == 400
    assert response.json()["detail"] == "Card is not in this draft pool"



def test_only_owner_can_start_draft(client, make_player):        
    alice = make_player("alice")
    bob = make_player("bob")
    owner = alice

    lobby = client.post(
        "/api/lobbies",
        json={"name": "Test Lobby", "num_players": 2},
        headers=owner.headers,
    ).json()

    # 2. Bob Joins
    client.post(
        "/api/lobbies/join",
        json={"lobby_code": lobby["code"]},
        headers=bob.headers,
    )

    # 3. Bob trys to starts it
    response = client.post(f"/api/lobbies/{lobby['id']}/start", headers=bob.headers)
    assert response.status_code == 403

def test_join_with_bad_code_returns_404(client, make_player):

    alice = make_player("alice")
    bob = make_player("bob")
    owner = alice

    lobby = client.post(
        "/api/lobbies",
        json={"name": "Test Lobby", "num_players": 2},
        headers=owner.headers,  
    ).json()

    response = client.post(
        "/api/lobbies/join",
        json={"lobby_code": "ZZZZZZ"},
        headers=bob.headers,
    )
    assert response.status_code == 404

def test_cannot_join_full_lobby(client, make_player):

    alice = make_player("alice")
    bob = make_player("bob")
    carrol = make_player("carrol")
   

    lobby = client.post(
        "/api/lobbies",
        json={"name": "Test Lobby", "num_players": 2},
        headers=alice.headers,
    ).json()

    client.post(
        "/api/lobbies/join",
        json={"lobby_code": lobby["code"]},
        headers=bob.headers,
    )   

    response = client.post(
        "/api/lobbies/join",
        json={"lobby_code": lobby["code"]},
        headers=carrol.headers,
    )

    
    assert response.status_code == 400
    assert response.json()["detail"] == "Lobby is full"


def test_snake_draft_order_with_four_players(client, cards, make_player):
        alice = make_player("alice")
        bob = make_player("bob")
        carol = make_player("carol")
        gene = make_player("gene")

        state = start_draft(client, [alice, bob, carol, gene])

        expected_order = [alice, bob, carol, gene, gene, carol, bob, alice]

        for pick_number, player in enumerate(expected_order):
            card_id = state["pool"][pick_number]["id"]
            response = client.post(
                f"/api/lobbies/{state['id']}/pick",
                json={"card_id": card_id},
                headers=player.headers,
            )

            assert response.status_code == 200, f"pick{pick_number} should be allowed"

        assert response.json()["next_turn_user_id"] == alice.id


def test_draft_completes_after_last_pick(client, cards, make_player):
    alice = make_player("alice")
    bob = make_player("bob")

    state = start_draft(client, [alice, bob]) 

    expected_order = [alice, bob, bob, alice, alice, bob, bob, alice, alice, bob]

    for pick_number, player in enumerate(expected_order):
        card_id = state["pool"][pick_number]["id"]
        response = client.post(
            f"/api/lobbies/{state['id']}/pick",
            json={"card_id": card_id},
            headers=player.headers,
        
        )
        assert response.status_code == 200, f"pick{pick_number} should be allowed"
    assert response.json()["draft_complete"] is True
    lobby = client.get(f"/api/lobbies/{state['id']}", headers = alice.headers).json()
    assert lobby["status"] == "completed"

# ── Screen names ──────────────────────────────────────────────────────

def test_session_rejects_blank_screen_name(client):
    response = client.post("/api/session", json={"screen_name": "   "})
    assert response.status_code == 422


def test_session_trims_screen_name(client):
    token = client.post("/api/session", json={"screen_name": "  alice  "}).json()["access_token"]
    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["screen_name"] == "alice"


def test_requests_without_a_token_get_401(client):
    response = client.post("/api/lobbies", json={"name": "No Token", "num_players": 2})
    assert response.status_code == 401


def test_cannot_join_lobby_with_duplicate_screen_name(client, make_player):
    alice = make_player("alice")
    other_alice = make_player("ALICE")

    lobby = client.post(
        "/api/lobbies",
        json={"name": "Test Lobby", "num_players": 4},
        headers=alice.headers,
    ).json()

    response = client.post(
        "/api/lobbies/join",
        json={"lobby_code": lobby["code"]},
        headers=other_alice.headers,
    )
    assert response.status_code == 409


def test_same_screen_name_allowed_in_different_lobbies(client, make_player):
    alice = make_player("alice")
    bob = make_player("bob")
    other_alice = make_player("alice")

    client.post("/api/lobbies", json={"name": "Lobby 1", "num_players": 2}, headers=alice.headers)
    lobby2 = client.post(
        "/api/lobbies", json={"name": "Lobby 2", "num_players": 2}, headers=bob.headers
    ).json()

    response = client.post(
        "/api/lobbies/join",
        json={"lobby_code": lobby2["code"]},
        headers=other_alice.headers,
    )
    assert response.status_code == 200


# ── Practice drafts (solo vs bots) ────────────────────────────────────

def start_practice(client, player, num_players):
    response = client.post(
        "/api/practice", json={"num_players": num_players}, headers=player.headers
    )
    assert response.status_code == 200
    return response.json()


def test_practice_draft_starts_on_your_turn(client, cards, make_player):
    alice = make_player("alice")

    state = start_practice(client, alice, 4)

    assert state["status"] == "drafting"
    assert len(state["players"]) == 4
    assert len(state["pool"]) == 20
    assert [p["screen_name"] for p in state["players"]].count("alice") == 1
    # Any bots seated before alice have already picked; now it's her turn.
    assert state["current_turn_user_id"] == alice.id


def test_bots_pick_until_it_is_your_turn_again(client, cards, make_player):
    alice = make_player("alice")
    state = start_practice(client, alice, 3)

    card_id = next(c["id"] for c in state["pool"] if not c["is_drafted"])
    response = client.post(
        f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers=alice.headers
    )

    assert response.status_code == 200
    assert response.json()["next_turn_user_id"] == alice.id


def test_full_practice_draft_completes(client, cards, make_player):
    alice = make_player("alice")
    state = start_practice(client, alice, 4)

    while state["status"] == "drafting":
        card_id = next(c["id"] for c in state["pool"] if not c["is_drafted"])
        response = client.post(
            f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers=alice.headers
        )
        assert response.status_code == 200
        state = client.get(f"/api/lobbies/{state['id']}", headers=alice.headers).json()

    assert state["status"] == "completed"
    assert all(len(p["picks"]) == 5 for p in state["players"])
    all_picks = [name for p in state["players"] for name in p["picks"]]
    assert len(all_picks) == len(set(all_picks)), "no card should be drafted twice"


def test_practice_draft_rejects_bad_table_size(client, make_player):
    alice = make_player("alice")
    response = client.post("/api/practice", json={"num_players": 1}, headers=alice.headers)
    assert response.status_code == 422


def test_cannot_join_a_practice_draft(client, cards, make_player):
    alice = make_player("alice")
    bob = make_player("bob")
    state = start_practice(client, alice, 4)

    response = client.post(
        "/api/lobbies/join", json={"lobby_code": state["code"]}, headers=bob.headers
    )
    assert response.status_code == 400


def test_bots_never_pick_in_a_normal_draft(client, cards, make_player):
    alice = make_player("alice")
    bob = make_player("bob")
    state = start_draft(client, [alice, bob])

    card_id = state["pool"][0]["id"]
    response = client.post(
        f"/api/lobbies/{state['id']}/pick", json={"card_id": card_id}, headers=alice.headers
    )
    # Bob is a human, so the turn stops on him instead of being auto-picked.
    assert response.json()["next_turn_user_id"] == bob.id
