import random
import re
import requests

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


# --- EDHREC HELPERS ---

def name_to_edhrec_slug(name):
    """Converts a card name like "Y'shtola, Night's Blessed" to "yshtola-nights-blessed"."""
    name = name.lower()
    name = re.sub(r"[',]", "", name)
    name = re.sub(r"[^a-z0-9\s-]", "", name)
    name = re.sub(r"\s+", "-", name.strip())
    return name


def get_edhrec_tags(card_name):
    """Fetches the top 3 archetype tags for a commander from EDHRec."""
    slug = name_to_edhrec_slug(card_name)
    url = f"https://json.edhrec.com/pages/commanders/{slug}.json"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        # Tags live in panels → links → the item where header == "Tags"
        links = data.get("panels", {}).get("links", [])
        for section in links:
            if section.get("header") == "Tags":
                return [item["value"] for item in section.get("items", [])[:3]]
        return []
    except Exception:
        return []