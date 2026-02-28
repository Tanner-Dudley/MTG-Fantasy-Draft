from draft_logic import get_diverse_pool, IDENTITY_MAP

# --- HELPER FUNCTION ---
def make_card(name, rarity, identity, set_code="m21"):
    """Quickly generates a fake card dictionary for testing."""
    return {'id': name, 'name': name, 'rarity': rarity, 'color_identity': identity, 'set': set_code}

# --- TESTS ---
def test_rarity_filtering():
    db = [
        make_card("Common Hero", "common", ["W"]),
        make_card("Mythic Dragon", "mythic", ["R"])
    ]
    # Turn off mythics
    allowed_r = {'common': True, 'uncommon': True, 'rare': True, 'mythic': False}
    allowed_id = {k: False for k in IDENTITY_MAP.keys()} 
    
    pool, err = get_diverse_pool(db, 1, prevent_dupes=False, allowed_rarities=allowed_r, allowed_identities=allowed_id)
    
    assert err is None
    assert len(pool) == 1
    assert pool[0]['name'] == "Common Hero" # The dragon should be filtered out

def test_color_identity_filtering():
    db = [
        make_card("Azorius Mage", "rare", ["W", "U"]),
        make_card("Boros Fighter", "rare", ["R", "W"]),
        make_card("Bant Angel", "mythic", ["G", "W", "U"])
    ]
    allowed_r = {'common': True, 'uncommon': True, 'rare': True, 'mythic': True}
    allowed_id = {k: False for k in IDENTITY_MAP.keys()}
    
    # Enable ONLY Azorius
    allowed_id['Azorius'] = True 
    
    pool, err = get_diverse_pool(db, 1, prevent_dupes=False, allowed_rarities=allowed_r, allowed_identities=allowed_id)
    
    assert err is None
    assert len(pool) == 1
    assert pool[0]['name'] == "Azorius Mage" # Only the exact W/U match survives

def test_duplicate_prevention():
    db = [
        make_card("Card A", "rare", ["B"], "set1"),
        make_card("Card B", "rare", ["B"], "set1"), # Same set!
        make_card("Card C", "rare", ["B"], "set2")
    ]
    allowed_r = {'common': True, 'uncommon': True, 'rare': True, 'mythic': True}
    allowed_id = {k: False for k in IDENTITY_MAP.keys()}
    
    # We want 2 cards, and we WANT to prevent set duplicates
    pool, err = get_diverse_pool(db, 2, prevent_dupes=True, allowed_rarities=allowed_r, allowed_identities=allowed_id)
    
    assert err is None
    assert len(pool) == 2
    
    # Grab the set codes of the drafted cards
    sets_in_pool = {card['set'] for card in pool}
    assert len(sets_in_pool) == 2 # Proves it pulled from two distinct sets
    
def test_not_enough_cards_error():
    # Provide only 1 fake card
    db = [make_card("Lonely Card", "common", ["W"])]
    allowed_r = {'common': True, 'uncommon': True, 'rare': True, 'mythic': True}
    allowed_id = {k: False for k in IDENTITY_MAP.keys()}
    
    # Ask the app to draft 50 cards from a database that only has 1
    pool, err = get_diverse_pool(db, count=50, prevent_dupes=False, allowed_rarities=allowed_r, allowed_identities=allowed_id)
    
    # Verify the app returns None for the pool, and hands back our error string
    assert pool is None
    assert "Too many restrictions!" in err