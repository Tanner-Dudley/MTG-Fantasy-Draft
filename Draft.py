import streamlit as st
import requests
import time

# --- CONFIGURATION ---
SCRYFALL_SEARCH_URL = "https://api.scryfall.com/cards/search"
CARDS_PER_ROW = 4

# Import pure logic (no Streamlit) so test_logic.py can import it without side effects
from draft_logic import IDENTITY_MAP, get_diverse_pool

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
    st.session_state.error_msg = None
    
    # New Settings Variables
    st.session_state.prevent_dupes = False
    st.session_state.allowed_rarities = {'common': True, 'uncommon': True, 'rare': True, 'mythic': True}
    st.session_state.allowed_identities = {k: False for k in IDENTITY_MAP.keys()}

# --- HELPER: UPDATE PLAYERS ---
def update_player_list():
    # Safely capture the UI widget's value into permanent memory
    if 'num_players_widget' in st.session_state:
        st.session_state.num_players = st.session_state.num_players_widget
        
    current_count = st.session_state.num_players
    st.session_state.player_names = [f"Player {i+1}" for i in range(current_count)]
    for p in st.session_state.player_names:
        if p not in st.session_state.player_drafts:
            st.session_state.player_drafts[p] = []

# --- HELPER: RENDER SETTINGS ---
def render_settings(show_player_count=True):
    """Renders the draft settings expander. Called in both Setup and Draft views."""
    with st.expander("⚙️ Draft Settings", expanded=not st.session_state.setup_complete):
        
        if show_player_count:
            st.subheader("General Settings")
            col1, col2 = st.columns(2)
            with col1:
                st.number_input(
                    "Number of Players",
                    min_value=2,
                    max_value=12,
                    value=st.session_state.num_players,
                    key="num_players_widget",
                    on_change=update_player_list
                )
            with col2:
                st.write("")
                st.write("")
                st.session_state.prevent_dupes = st.toggle("Prevent Set Duplicates", value=st.session_state.prevent_dupes, key="toggle_dupes")
        else:
            st.subheader("General Settings")
            st.session_state.prevent_dupes = st.toggle("Prevent Set Duplicates", value=st.session_state.prevent_dupes, key="toggle_dupes")

        st.divider()

        ### RARITY SETTINGS ###
        st.subheader("Allowed Rarities")
        st.write("Toggle off to remove a rarity from the draft pool.")
        r_col1, r_col2, r_col3, r_col4 = st.columns(4)
        with r_col1:
            st.session_state.allowed_rarities['common'] = st.toggle("Common", value=st.session_state.allowed_rarities['common'], key="toggle_common")
        with r_col2:
            st.session_state.allowed_rarities['uncommon'] = st.toggle("Uncommon", value=st.session_state.allowed_rarities['uncommon'], key="toggle_uncommon")
        with r_col3:
            st.session_state.allowed_rarities['rare'] = st.toggle("Rare", value=st.session_state.allowed_rarities['rare'], key="toggle_rare")
        with r_col4:
            st.session_state.allowed_rarities['mythic'] = st.toggle("Mythic Rare", value=st.session_state.allowed_rarities['mythic'], key="toggle_mythic")

        st.divider()

        ### COLOR IDENTITY SETTINGS ###
        st.subheader("Color Identity Restrictions")
        st.write("Enable to lock the draft pool to specific exact color identities. Leave all unchecked to allow everything.")

        st.markdown("**2-Color (Guilds)**")
        g_col1, g_col2, g_col3, g_col4, g_col5 = st.columns(5)
        with g_col1:
            st.session_state.allowed_identities['Azorius'] = st.toggle("Azorius (WU)", value=st.session_state.allowed_identities['Azorius'], key="toggle_Azorius")
            st.session_state.allowed_identities['Orzhov'] = st.toggle("Orzhov (WB)", value=st.session_state.allowed_identities['Orzhov'], key="toggle_Orzhov")
        with g_col2:
            st.session_state.allowed_identities['Dimir'] = st.toggle("Dimir (UB)", value=st.session_state.allowed_identities['Dimir'], key="toggle_Dimir")
            st.session_state.allowed_identities['Izzet'] = st.toggle("Izzet (UR)", value=st.session_state.allowed_identities['Izzet'], key="toggle_Izzet")
        with g_col3:
            st.session_state.allowed_identities['Rakdos'] = st.toggle("Rakdos (BR)", value=st.session_state.allowed_identities['Rakdos'], key="toggle_Rakdos")
            st.session_state.allowed_identities['Golgari'] = st.toggle("Golgari (BG)", value=st.session_state.allowed_identities['Golgari'], key="toggle_Golgari")
        with g_col4:
            st.session_state.allowed_identities['Gruul'] = st.toggle("Gruul (RG)", value=st.session_state.allowed_identities['Gruul'], key="toggle_Gruul")
            st.session_state.allowed_identities['Boros'] = st.toggle("Boros (RW)", value=st.session_state.allowed_identities['Boros'], key="toggle_Boros")
        with g_col5:
            st.session_state.allowed_identities['Selesnya'] = st.toggle("Selesnya (GW)", value=st.session_state.allowed_identities['Selesnya'], key="toggle_Selesnya")
            st.session_state.allowed_identities['Simic'] = st.toggle("Simic (GU)", value=st.session_state.allowed_identities['Simic'], key="toggle_Simic")

        st.markdown("**3-Color (Shards & Wedges)**")
        s_col1, s_col2, s_col3, s_col4, s_col5 = st.columns(5)
        with s_col1:
            st.session_state.allowed_identities['Bant'] = st.toggle("Bant (GWU)", value=st.session_state.allowed_identities['Bant'], key="toggle_Bant")
            st.session_state.allowed_identities['Mardu'] = st.toggle("Mardu (WBR)", value=st.session_state.allowed_identities['Mardu'], key="toggle_Mardu")
        with s_col2:
            st.session_state.allowed_identities['Esper'] = st.toggle("Esper (WUB)", value=st.session_state.allowed_identities['Esper'], key="toggle_Esper")
            st.session_state.allowed_identities['Temur'] = st.toggle("Temur (URG)", value=st.session_state.allowed_identities['Temur'], key="toggle_Temur")
        with s_col3:
            st.session_state.allowed_identities['Grixis'] = st.toggle("Grixis (UBR)", value=st.session_state.allowed_identities['Grixis'], key="toggle_Grixis")
            st.session_state.allowed_identities['Abzan'] = st.toggle("Abzan (WBG)", value=st.session_state.allowed_identities['Abzan'], key="toggle_Abzan")
        with s_col4:
            st.session_state.allowed_identities['Jund'] = st.toggle("Jund (BRG)", value=st.session_state.allowed_identities['Jund'], key="toggle_Jund")
            st.session_state.allowed_identities['Jeskai'] = st.toggle("Jeskai (URW)", value=st.session_state.allowed_identities['Jeskai'], key="toggle_Jeskai")
        with s_col5:
            st.session_state.allowed_identities['Naya'] = st.toggle("Naya (RGW)", value=st.session_state.allowed_identities['Naya'], key="toggle_Naya")
            st.session_state.allowed_identities['Sultai'] = st.toggle("Sultai (BGU)", value=st.session_state.allowed_identities['Sultai'], key="toggle_Sultai")

        st.markdown("**5-Color**")
        st.session_state.allowed_identities['WUBRG'] = st.toggle("WUBRG (All Colors)", value=st.session_state.allowed_identities['WUBRG'], key="toggle_WUBRG")

# --- UI START ---
st.set_page_config(layout="wide", page_title="MTG Draft Tool")

with st.spinner("Accessing Scryfall..."):
    full_db = get_full_commander_database()

# --- VIEW 1: SETUP SCREEN ---
if not st.session_state.setup_complete:
    st.title("MTG: Commander Draft Tool")
    
    render_settings(show_player_count=True)

    st.write("---")
    st.write(f"**Current Players:** {st.session_state.num_players}")
    
    if st.button("Start Draft", type="primary"):
        update_player_list()
        pool_size = st.session_state.num_players * 5
        
        pool, err = get_diverse_pool(full_db, pool_size, st.session_state.prevent_dupes, st.session_state.allowed_rarities, st.session_state.allowed_identities)
        
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
                render_settings(show_player_count=False)
                c_left, c_btn, c_right = st.columns([1.5, 1, 1.5])
                with c_btn:
                    btn_label = "Refresh Pool"
                    if len(st.session_state.pool) != (st.session_state.num_players * 5):
                         btn_label = "Refresh Pool (Update Size)"
                    
                    if st.button(btn_label, use_container_width=True):
                        update_player_list()
                        pool_size = st.session_state.num_players * 5
                        pool, err = get_diverse_pool(full_db, pool_size, st.session_state.prevent_dupes, st.session_state.allowed_rarities, st.session_state.allowed_identities)
                        
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