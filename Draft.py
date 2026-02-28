import streamlit as st
import requests
import random
import time

# --- CONFIGURATION ---
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"
CARDS_PER_ROW = 4

# --- CSS ---
st.markdown("""
    <style>
    /* Clean, flat design */
    img {
        width: 100%;
        height: auto;
        border-radius: 4.5%;
        margin-bottom: 5px;
    }
    .stButton button {
        width: 100%;
    }
    header {visibility: hidden;}
    
    /* REMOVE CHAIN LINKS (Anchor Icons) */
    [data-testid="stHeader"] a, 
    [data-testid="stMarkdownContainer"] h1 a, 
    [data-testid="stMarkdownContainer"] h2 a, 
    [data-testid="stMarkdownContainer"] h3 a {
        display: none !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- HELPER: GET IMAGE ---
def get_image_uri(card):
    if 'image_uris' in card:
        return card['image_uris']['normal']
    elif 'card_faces' in card:
        return card['card_faces'][0]['image_uris']['normal']
    return "https://cards.scryfall.io/large/front/e/c/ecbeac44-5271-44e5-a7c0-06a096c5aa06.jpg"

# --- API: FETCH ALL PAGES ---
@st.cache_data(show_spinner=False)
def get_full_commander_database():
    all_cards = []
    # Updated Query: 'is:commander' ensures the card is legally able to be a commander
    query_params = {
        "q": "is:commander f:commander game:paper",
        "unique": "cards",
        "order": "name" 
    }
    
    url = SCRYFALL_SEARCH_URL
    has_more = True
    progress_text = st.empty()
    progress_text.text("Building Commander Database... (Page 1)")
    
    while has_more:
        try:
            resp = requests.get(url, params=query_params if url == SCRYFALL_SEARCH_URL else None)
            resp.raise_for_status()
            data = resp.json()
            all_cards.extend(data.get('data', []))
            
            has_more = data.get('has_more', False)
            if has_more:
                url = data.get('next_page')
                time.sleep(0.1)
                progress_text.text(f"Building Commander Database... ({len(all_cards)} cards found)")
        except Exception as e:
            st.error(f"Error fetching data: {e}")
            break
            
    progress_text.empty()
    return all_cards

# --- LOGIC: GENERATE POOL ---
def get_diverse_pool(db, count, prevent_dupes, exclusions):
    filtered_db = []
    
    # 1. Apply Color Filters
    for card in db:
        identity = card.get('color_identity', [])
        
        if not identity and exclusions['C']: continue
        if 'W' in identity and exclusions['W']: continue
        if 'U' in identity and exclusions['U']: continue
        if 'B' in identity and exclusions['B']: continue
        if 'R' in identity and exclusions['R']: continue
        if 'G' in identity and exclusions['G']: continue
        
        filtered_db.append(card)

    if len(filtered_db) < count:
        return None, f"Too many restrictions! Only {len(filtered_db)} cards match your criteria."

    # 2. Apply Duplicate Logic
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

# --- INITIALIZE STATE ---
if 'setup_complete' not in st.session_state:
    st.session_state.setup_complete = False
    st.session_state.num_players = 4
    st.session_state.pool = []
    st.session_state.drafted_ids = set()
    st.session_state.player_names = []
    st.session_state.player_drafts = {}
    st.session_state.turn_index = 0
    st.session_state.direction = 1
    # Settings
    st.session_state.prevent_dupes = False
    st.session_state.exclusions = {'W': False, 'U': False, 'B': False, 'R': False, 'G': False, 'C': False}
    st.session_state.error_msg = None

# --- HELPER: UPDATE PLAYERS ---
def update_player_list():
    """Syncs player_names list with num_players integer"""
    current_count = st.session_state.num_players
    st.session_state.player_names = [f"Player {i+1}" for i in range(current_count)]
    for p in st.session_state.player_names:
        if p not in st.session_state.player_drafts:
            st.session_state.player_drafts[p] = []

# --- UI START ---
st.set_page_config(layout="wide", page_title="MTG Draft Tool")

with st.spinner("Accessing Scryfall..."):
    full_db = get_full_commander_database()

# --- SETTINGS MENU (GLOBAL) ---
with st.popover("⚙️ Settings"):
    st.markdown("### Draft Preferences")
    
    # 1. Player Count
    st.number_input(
        "Number of Players", 
        min_value=2, 
        max_value=12, 
        key="num_players",
        on_change=update_player_list
    )
    
    # 2. Toggles
    st.session_state.prevent_dupes = st.toggle("Prevent Set Duplicates", value=st.session_state.prevent_dupes)
    
    st.divider()
    st.markdown("### Exclusions")
    c1, c2 = st.columns(2)
    with c1:
        st.session_state.exclusions['W'] = st.toggle("Exclude White", value=st.session_state.exclusions['W'])
        st.session_state.exclusions['U'] = st.toggle("Exclude Blue", value=st.session_state.exclusions['U'])
        st.session_state.exclusions['B'] = st.toggle("Exclude Black", value=st.session_state.exclusions['B'])
    with c2:
        st.session_state.exclusions['R'] = st.toggle("Exclude Red", value=st.session_state.exclusions['R'])
        st.session_state.exclusions['G'] = st.toggle("Exclude Green", value=st.session_state.exclusions['G'])
        st.session_state.exclusions['C'] = st.toggle("Exclude Colorless", value=st.session_state.exclusions['C'])


# --- VIEW 1: SETUP SCREEN ---
if not st.session_state.setup_complete:
    st.title("MTG: Commander Draft Tool")
    st.write("Configure your draft settings in the settings menu or start below.")
    
    st.write(f"**Current Players:** {st.session_state.num_players}")
    
    if st.button("Start Draft"):
        update_player_list()
        pool_size = st.session_state.num_players * 5
        
        pool, err = get_diverse_pool(full_db, pool_size, st.session_state.prevent_dupes, st.session_state.exclusions)
        
        if err:
            st.error(err)
        else:
            st.session_state.pool = pool
            st.session_state.setup_complete = True
            st.rerun()

# --- VIEW 2: DRAFT SCREEN ---
else:
    # Error Trap
    if st.session_state.error_msg:
        st.error(st.session_state.error_msg)
        if st.button("Return to Setup"):
            st.session_state.setup_complete = False
            st.session_state.error_msg = None
            st.rerun()
        st.stop()

    total_cards = len(st.session_state.pool)
    is_finished = len(st.session_state.drafted_ids) == total_cards
    
    def handle_draft(card):
        if st.session_state.turn_index >= len(st.session_state.player_names):
            st.session_state.turn_index = 0
            
        current_player = st.session_state.player_names[st.session_state.turn_index]
        st.session_state.player_drafts[current_player].append(card['name'])
        st.session_state.drafted_ids.add(card['id'])
        
        num_players = st.session_state.num_players
        next_index = st.session_state.turn_index + st.session_state.direction
        
        # Snake Logic
        if next_index >= num_players:
            st.session_state.turn_index = num_players - 1
            st.session_state.direction = -1
        elif next_index < 0:
            st.session_state.turn_index = 0
            st.session_state.direction = 1
        else:
            st.session_state.turn_index = next_index

    if not is_finished:
        main_col, side_col = st.columns([5, 1])
        
        with main_col:
            if st.session_state.turn_index < len(st.session_state.player_names):
                current_p = st.session_state.player_names[st.session_state.turn_index]
            else:
                current_p = st.session_state.player_names[0]
                
            st.subheader(f"Current Turn: {current_p}")
            
            rows_needed = (len(st.session_state.pool) + CARDS_PER_ROW - 1) // CARDS_PER_ROW
            
            for row in range(rows_needed):
                cols = st.columns(CARDS_PER_ROW)
                for col_idx in range(CARDS_PER_ROW):
                    card_idx = row * CARDS_PER_ROW + col_idx
                    if card_idx < len(st.session_state.pool):
                        card = st.session_state.pool[card_idx]
                        drafted = card['id'] in st.session_state.drafted_ids
                        image_url = get_image_uri(card)
                        
                        with cols[col_idx]:
                            opacity = 0.2 if drafted else 1.0
                            st.markdown(
                                f'<img src="{image_url}" style="opacity:{opacity};">', 
                                unsafe_allow_html=True
                            )
                            st.button("Draft", key=f"btn_{card['id']}", disabled=drafted, on_click=handle_draft, args=(card,), use_container_width=True)

            # --- REFRESH BUTTON ---
            if len(st.session_state.drafted_ids) == 0:
                st.markdown("---")
                c_left, c_btn, c_right = st.columns([1.5, 1, 1.5])
                with c_btn:
                    btn_label = "Refresh Pool"
                    if len(st.session_state.pool) != (st.session_state.num_players * 5):
                         btn_label = "Refresh Pool (Update Size)"
                    
                    if st.button(btn_label, use_container_width=True):
                        update_player_list()
                        pool_size = st.session_state.num_players * 5
                        pool, err = get_diverse_pool(full_db, pool_size, st.session_state.prevent_dupes, st.session_state.exclusions)
                        
                        if err:
                            st.session_state.error_msg = err
                        else:
                            st.session_state.error_msg = None
                            st.session_state.pool = pool
                        st.rerun()

        with side_col:
            st.header("Draft Board")
            for player in st.session_state.player_names:
                marker = " <" if player == current_p else ""
                st.write(f"**{player}**{marker}")
                if player in st.session_state.player_drafts:
                    for picked in st.session_state.player_drafts[player]:
                        st.caption(f"- {picked}")
                st.divider()

    else:
        st.header("Draft Results")
        
        cols_per_row = 4
        num_players = st.session_state.num_players
        for i in range(0, num_players, cols_per_row):
            cols = st.columns(cols_per_row)
            for j in range(cols_per_row):
                if i + j < num_players:
                    player = st.session_state.player_names[i+j]
                    with cols[j]:
                        st.subheader(player)
                        decklist_text = "\n".join([f"1 {name}" for name in st.session_state.player_drafts.get(player, [])])
                        st.text_area(f"Copy List:", value=decklist_text, height=150, key=f"area_{player}")
                        st.download_button(label=f"Download {player}", data=decklist_text, file_name=f"{player}_draft.txt", key=f"dl_{player}")

        if st.button("Start New Draft"):
            st.session_state.setup_complete = False
            st.session_state.drafted_ids = set()
            st.session_state.pool = []
            st.session_state.error_msg = None
            st.session_state.turn_index = 0
            st.session_state.direction = 1
            st.rerun()