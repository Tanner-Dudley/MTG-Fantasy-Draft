from streamlit.testing.v1 import AppTest
from unittest.mock import patch, MagicMock

# Intercept the global requests.get function instead
@patch("requests.get")
def test_app_loads_and_counts_players(mock_get):
    # 1. Create a fake card
    fake_card = {'id': '123', 'name': 'Mock Commander', 'rarity': 'rare', 'color_identity': ['W', 'U'], 'set': 'm21'}
    
    # 2. Configure our fake internet request to return a successful Scryfall-style response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'data': [fake_card] * 30, # Give it 30 copies of our fake card
        'has_more': False         # Tell the while-loop to stop downloading
    }
    mock_get.return_value = mock_response
    
    # 3. Initialize the simulated app
    at = AppTest.from_file("Draft.py")
    
    # 4. Run the app (should take milliseconds now!)
    at.run()
    
    # 5. Verify the title is correct
    assert at.title[0].value == "MTG: Commander Draft Tool"
    
    # 6. Simulate changing the Number of Players input
    at.number_input(key="num_players").set_value(6).run()
    
    # 7. Verify the session state updated correctly behind the scenes
    assert len(at.session_state.player_names) == 6