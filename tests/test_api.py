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