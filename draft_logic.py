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
    """
    Converts a card name to an EDHRec URL slug.

    Handles:
    - Accented characters  : Ratonhnhaké:ton  → ratonhnhake-ton
    - Colons               : Ratonhnhaké:ton  → ratonhnhake-ton
    - Apostrophes/commas   : Y'shtola, Night's Blessed → yshtola-nights-blessed
    - Split card names     : Wear // Tear     → wear
    - Ampersands           : Gargos & Friends → gargos-friends
    - Extra punctuation    : Dr. Julius Jumblemorph → dr-julius-jumblemorph
    """
    import unicodedata

    # Split cards — only use the first half
    if "//" in name:
        name = name.split("//")[0]

    # Normalize accented characters to their ASCII base equivalents
    # e.g. é → e, ü → u, ñ → n
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode("ascii")

    name = name.lower()

    # Convert colons and ampersands to spaces so they become hyphens
    name = re.sub(r"[:&]", " ", name)

    # Remove all remaining punctuation except spaces and hyphens
    name = re.sub(r"[^a-z0-9\s-]", "", name)

    # Collapse multiple spaces/hyphens and convert to single hyphens
    name = re.sub(r"[\s-]+", "-", name.strip())

    return name


def get_edhrec_tags(card_name):
    """
    Fetches the top 3 archetype tags for a commander from EDHRec.

    For double-faced cards (e.g. "Megatron, Tyrant // Megatron, Destructive Force"),
    tries the first-face slug first, then falls back to the full combined slug if
    EDHRec returns a 404.
    """
    slugs_to_try = [name_to_edhrec_slug(card_name)]

    # If it's a double-faced card, also build the combined slug as a fallback
    if "//" in card_name:
        both_faces = " ".join(
            part.strip() for part in card_name.split("//")
        )
        combined_slug = name_to_edhrec_slug(both_faces)
        slugs_to_try.append(combined_slug)

    for slug in slugs_to_try:
        try:
            url = f"https://json.edhrec.com/pages/commanders/{slug}.json"
            resp = requests.get(url, timeout=5)
            if resp.status_code != 200:
                continue
            data = resp.json()
            links = data.get("panels", {}).get("links", [])
            for section in links:
                if section.get("header") == "Tags":
                    return [item["value"] for item in section.get("items", [])[:3]]
        except Exception:
            continue

    return []