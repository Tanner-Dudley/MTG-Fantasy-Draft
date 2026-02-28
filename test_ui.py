from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock
import streamlit as st

@patch("requests.get")
def test_app_loads_and_counts_players(mock_get):
    # Generate 30 unique cards instead of copying the exact same one
    fake_cards = [{'id': str(i), 'name': f'Mock Commander {i}', 'rarity': 'rare', 'color_identity': ['W', 'U'], 'set': 'm21'} for i in range(30)]
    
    mock_response = MagicMock()
    mock_response.json.return_value = {'data': fake_cards, 'has_more': False}
    mock_get.return_value = mock_response
    
    at = AppTest.from_file("Draft.py")
    at.run()
    
    assert at.title[0].value == "MTG: Commander Draft Tool"
    at.number_input(key="num_players_widget").set_value(6).run()
    assert len(at.session_state.player_names) == 6

@patch("requests.get")
def test_snake_draft_turn_logic(mock_get):
    fake_cards = [{'id': str(i), 'name': f'Card {i}', 'rarity': 'common', 'color_identity': ['R'], 'set': 'm21'} for i in range(10)]
    
    mock_response = MagicMock()
    mock_response.json.return_value = {'data': fake_cards, 'has_more': False}
    mock_get.return_value = mock_response
    
    st.cache_data.clear()
    
    at = AppTest.from_file("Draft.py")
    
    # Bypass the setup screen entirely — pre-load session state as if
    # setup already completed with 2 players. This avoids AppTest trying
    # to replay the number_input widget on screens where it doesn't exist.
    at.session_state["setup_complete"] = True
    at.session_state["num_players"] = 2
    at.session_state["player_names"] = ["Player 1", "Player 2"]
    at.session_state["player_drafts"] = {"Player 1": [], "Player 2": []}
    at.session_state["pool"] = fake_cards
    at.session_state["drafted_ids"] = set()
    at.session_state["turn_index"] = 0
    at.session_state["direction"] = 1
    at.session_state["error_msg"] = None
    
    at.run()
    
    assert at.session_state.turn_index == 0
    at.button(key="btn_0").click().run()
    
    assert at.session_state.turn_index == 1
    at.button(key="btn_1").click().run()
    
    assert at.session_state.turn_index == 1
    at.button(key="btn_2").click().run()
    
    assert at.session_state.turn_index == 0