from draft_logic import get_diverse_pool, IDENTITY_MAP, name_to_edhrec_slug

# --- HELPER FUNCTION ---
def make_card(name, rarity, identity, set_code="m21"):
    """Quickly generates a fake card dictionary for testing."""
    return {'id': name, 'name': name, 'rarity': rarity, 'color_identity': identity, 'set': set_code}

# --- POOL TESTS ---
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


# --- SLUG CONVERSION TESTS ---

def test_slug_standard_name():
    # Basic name with comma — the most common case
    assert name_to_edhrec_slug("Atraxa, Praetors' Voice") == "atraxa-praetors-voice"

def test_slug_accented_character():
    # é must become e, colon must become a hyphen
    # Ratonhnhaké:ton is an Assassin's Creed Universes Beyond card
    assert name_to_edhrec_slug("Ratonhnhaké:ton") == "ratonhnhake-ton"

def test_slug_colon_without_accent():
    # Colon alone should also become a hyphen
    assert name_to_edhrec_slug("Urza: Academy Headmaster") == "urza-academy-headmaster"

def test_slug_split_card():
    # Only the first half of a split card name should be used
    assert name_to_edhrec_slug("Wear // Tear") == "wear"

def test_slug_megatron():
    # Straightforward name — confirms no hidden character issues
    assert name_to_edhrec_slug("Megatron, Tyrant") == "megatron-tyrant"

def test_slug_apostrophe_in_name():
    # Apostrophe should be removed cleanly, not turned into a hyphen
    assert name_to_edhrec_slug("Gollum, Patient Plotter") == "gollum-patient-plotter"

def test_slug_multiple_accents():
    # Multiple accented chars in one name should all convert
    assert name_to_edhrec_slug("Lathiel, the Bounteous Dawn") == "lathiel-the-bounteous-dawn"

def test_slug_no_special_chars():
    # Plain name should pass through cleanly
    assert name_to_edhrec_slug("Yuriko the Tigers Shadow") == "yuriko-the-tigers-shadow"

def test_slug_double_faced_card():
    # Double-faced cards: the combined slug should join both face names
    # This is the fallback EDHRec uses for cards like Megatron
    full_name = "Megatron, Tyrant // Megatron, Destructive Force"
    both_faces = " ".join(part.strip() for part in full_name.split("//"))
    assert name_to_edhrec_slug(both_faces) == "megatron-tyrant-megatron-destructive-force"

def test_slug_double_faced_first_face():
    # The first-face-only slug should also be correct (tried before the fallback)
    assert name_to_edhrec_slug("Megatron, Tyrant // Megatron, Destructive Force") == "megatron-tyrant"