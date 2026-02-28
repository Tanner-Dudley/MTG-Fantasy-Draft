import random

# --- COLOR IDENTITY MAPPING ---
IDENTITY_MAP = {
    'Azorius': {'W', 'U'}, 'Orzhov': {'W', 'B'}, 'Dimir': {'U', 'B'}, 'Izzet': {'U', 'R'},
    'Rakdos': {'B', 'R'}, 'Golgari': {'B', 'G'}, 'Gruul': {'R', 'G'}, 'Boros': {'R', 'W'},
    'Selesnya': {'G', 'W'}, 'Simic': {'G', 'U'},
    'Bant': {'G', 'W', 'U'}, 'Mardu': {'W', 'B', 'R'}, 'Esper': {'W', 'U', 'B'},
    'Temur': {'U', 'R', 'G'}, 'Grixis': {'U', 'B', 'R'}, 'Abzan': {'W', 'B', 'G'},
    'Jund': {'B', 'R', 'G'}, 'Jeskai': {'U', 'R', 'W'}, 'Naya': {'R', 'G', 'W'},
    'Sultai': {'B', 'G', 'U'},
    'WUBRG': {'W', 'U', 'B', 'R', 'G'}
}


def get_diverse_pool(db, count, prevent_dupes, allowed_rarities, allowed_identities):
    filtered_db = []

    filtering_colors = any(allowed_identities.values())
    active_identity_sets = [IDENTITY_MAP[k] for k, is_active in allowed_identities.items() if is_active]

    for card in db:
        card_rarity = card.get('rarity', 'common')
        if not allowed_rarities.get(card_rarity, True):
            continue

        if filtering_colors:
            card_identity = set(card.get('color_identity', []))
            if card_identity not in active_identity_sets:
                continue

        filtered_db.append(card)

    if len(filtered_db) < count:
        return None, f"Too many restrictions! Only {len(filtered_db)} cards match your criteria. Please allow more options."

    if not prevent_dupes:
        return random.sample(filtered_db, count), None

    selected = []
    seen_sets = set()
    shuffled_db = random.sample(filtered_db, len(filtered_db))

    for card in shuffled_db:
        set_code = card.get('set')
        if set_code not in seen_sets:
            selected.append(card)
            seen_sets.add(set_code)
        if len(selected) >= count:
            break

    if len(selected) < count:
        return None, "Too many restrictions! (Set Duplicates prevented filling the pool)"

    return selected, None