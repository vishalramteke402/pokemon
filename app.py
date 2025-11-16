# app.py
import streamlit as st
import requests
import random
import time
from PIL import Image
from io import BytesIO

st.set_page_config(page_title="Pokémon Battle — Deluxe", layout="wide", page_icon="🧩")

# -----------------------
# Constants & Audio URLs
# -----------------------
POKEAPI_BASE = "https://pokeapi.co/api/v2"
GEN1_LIMIT = 151

# NOTE: These are example public audio URLs. If one fails you can replace with other hosted audio files.
AUDIO_ATTACK = "https://freesound.org/data/previews/341/341695_6266573-lq.mp3"
AUDIO_HIT = "https://freesound.org/data/previews/66/66073_931655-lq.mp3"
AUDIO_FAINT = "https://freesound.org/data/previews/331/331912_3248244-lq.mp3"
AUDIO_WIN = "https://freesound.org/data/previews/331/331912_3248244-lq.mp3"
BATTLE_MUSIC = "https://cdn.simplecast.com/audio/episodes/places-holder.mp3"  # placeholder: replace with preferred music URL

# -----------------------
# Helpers: Data Fetching
# -----------------------
@st.cache_data(show_spinner=False)
def fetch_gen1_list():
    """Fetch first 151 pokemon results from PokeAPI (name + url)."""
    resp = requests.get(f"{POKEAPI_BASE}/pokemon?limit={GEN1_LIMIT}")
    resp.raise_for_status()
    return resp.json()["results"]

@st.cache_data(show_spinner=False)
def fetch_pokemon_details(url):
    """Fetch a single pokemon's details by url."""
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def load_pokemon_by_name(name):
    resp = requests.get(f"{POKEAPI_BASE}/pokemon/{name.lower()}")
    resp.raise_for_status()
    return resp.json()

def image_from_sprite(url):
    if not url:
        return None
    try:
        r = requests.get(url)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content)).convert("RGBA")
        return img
    except Exception:
        return None

# -----------------------
# Game Engine Functions
# -----------------------

def compute_base_stats(poke):
    """Return simplified stats dict: attack, defense, max_hp, moves, sprite."""
    # We'll compute attack as attack + special-attack averaged with some weighting
    stats = {s['stat']['name']: s['base_stat'] for s in poke['stats']}
    atk = stats.get('attack', 50)
    spatk = stats.get('special-attack', 50)
    defense = stats.get('defense', 50)
    hp = stats.get('hp', 100)
    # get up to 4 moves that have a power value when possible
    moves = []
    for m in poke['moves']:
        move_name = m['move']['name']
        # prefer moves learned by level-up or default; rely on PokeAPI move details lazily if needed
        if len(moves) < 4:
            moves.append(move_name.replace('-', ' ').title())
    sprite = poke['sprites']['other']['official-artwork']['front_default'] or poke['sprites']['front_default']
    return {
        "attack": int((atk + spatk) / 2),
        "defense": int(defense),
        "max_hp": int(hp * 1.5),  # scale HP visually for gameplay
        "moves": moves[:4] if moves else ["Tackle", "Quick Attack"],
        "sprite": sprite
    }

def calculate_damage(attacker_stats, defender_stats, power_mod=1.0, shield=False):
    """Damage formula: base = atk - defense*0.3 + random + power_mod"""
    base = attacker_stats["attack"] - (defender_stats["defense"] * 0.28)
    random_part = random.randint(5, 20)
    dmg = max(5, int((base + random_part) * power_mod))
    if shield:
        dmg = int(dmg * 0.6)  # shield reduces damage by 40%
    return dmg

def play_sound(url):
    """Insert a small st.audio to play a sound. Works per action."""
    if url:
        st.audio(url)

# -----------------------
# Session State Init
# -----------------------
def init_session():
    if "pokelist" not in st.session_state:
        st.session_state.pokelist = fetch_gen1_list()  # list of dicts with name & url
    if "cache_pokemon" not in st.session_state:
        st.session_state.cache_pokemon = {}  # name -> details cached
    if "mode" not in st.session_state:
        st.session_state.mode = "Singleplayer"
    if "player_slots" not in st.session_state:
        st.session_state.player_slots = {"player1": None, "player2": None}
    if "party" not in st.session_state:
        # store selected pokemons with stats, hp, xp, level, items
        st.session_state.party = {}
    if "turn" not in st.session_state:
        st.session_state.turn = "player1"
    if "battle_log" not in st.session_state:
        st.session_state.battle_log = []
    if "bgm_on" not in st.session_state:
        st.session_state.bgm_on = False
    if "music_widget_key" not in st.session_state:
        st.session_state.music_widget_key = 0
    if "multiplayer" not in st.session_state:
        st.session_state.multiplayer = False

init_session()

# -----------------------
# UI: Sidebar Controls
# -----------------------
st.sidebar.title("Pokémon Deluxe — Controls")
mode = st.sidebar.radio("Mode", ["Singleplayer", "Local Multiplayer"])
st.session_state.mode = mode
st.session_state.multiplayer = (mode == "Local Multiplayer")

st.sidebar.markdown("### Background Music")
bgm_toggle = st.sidebar.checkbox("Play battle music", value=st.session_state.bgm_on)
st.session_state.bgm_on = bgm_toggle

if st.session_state.bgm_on:
    # Provide an audio widget (user can stop via media controls)
    # Changing key forces widget to refresh if toggled
    st.sidebar.audio(BATTLE_MUSIC, format="audio/mp3", start_time=0, key=f"bgm_{st.session_state.music_widget_key}")

# -----------------------
# Main Layout
# -----------------------
st.title("🧩 Pokémon Battle — Deluxe Edition")
st.markdown(
    "First 151 Gen Pokémon loaded from **PokeAPI**. Turn-based combat, XP, items, sounds, music, and multiplayer!"
)

col_main, col_help = st.columns([3, 1])
with col_help:
    st.info(
        """
        **How to play**
        - Pick Pokémon (player1, player2 or CPU).
        - Use moves and items.
        - Gain XP on victory and level up.
        - Toggle background music in sidebar.
        """
    )

# -----------------------
# Pokémon Selection Area
# -----------------------
with col_main:
    st.header("1) Select Pokémon / Load from PokeAPI")

    poke_names = [p['name'].title() for p in st.session_state.pokelist]
    # Selection UI depends on mode
    if st.session_state.multiplayer:
        st.subheader("Local Multiplayer: Select both players")
        p1 = st.selectbox("Player 1 Pokémon", poke_names, key="p1_select")
        p2 = st.selectbox("Player 2 Pokémon", poke_names, key="p2_select")
        if p1 and p2:
            # load details if not cached
            for pname in (p1, p2):
                lname = pname.lower()
                if lname not in st.session_state.cache_pokemon:
                    try:
                        data = load_pokemon_by_name(lname)
                        st.session_state.cache_pokemon[lname] = data
                    except Exception as e:
                        st.error(f"Failed to fetch {pname}: {e}")
            # initialize party entries
            def ensure_init_slot(slot_name, pname):
                lname = pname.lower()
                if slot_name not in st.session_state.party or st.session_state.party[slot_name] is None or st.session_state.party[slot_name]["name"] != pname:
                    details = st.session_state.cache_pokemon[lname]
                    base = compute_base_stats(details)
                    st.session_state.party[slot_name] = {
                        "name": pname,
                        "level": 5,
                        "xp": 0,
                        "attack": base["attack"],
                        "defense": base["defense"],
                        "max_hp": base["max_hp"],
                        "hp": base["max_hp"],
                        "moves": base["moves"],
                        "sprite": base["sprite"],
                        "items": {"Potion": 2, "Shield": 1, "Power Boost": 1}
                    }
            ensure_init_slot("player1", p1)
            ensure_init_slot("player2", p2)
    else:
        st.subheader("Singleplayer: Choose your Pokémon (you vs CPU)")
        p1 = st.selectbox("Choose your Pokémon", poke_names, key="single_p_select")
        if p1:
            lname = p1.lower()
            if lname not in st.session_state.cache_pokemon:
                try:
                    data = load_pokemon_by_name(lname)
                    st.session_state.cache_pokemon[lname] = data
                except Exception as e:
                    st.error(f"Failed to fetch {p1}: {e}")
            details = st.session_state.cache_pokemon.get(lname)
            base = compute_base_stats(details)
            # initialize player slot
            if "player1" not in st.session_state.party or st.session_state.party.get("player1", {}).get("name") != p1:
                st.session_state.party["player1"] = {
                    "name": p1,
                    "level": 5,
                    "xp": 0,
                    "attack": base["attack"],
                    "defense": base["defense"],
                    "max_hp": base["max_hp"],
                    "hp": base["max_hp"],
                    "moves": base["moves"],
                    "sprite": base["sprite"],
                    "items": {"Potion": 3, "Shield": 1, "Power Boost": 1}
                }
        # choose CPU opponent randomly if not set
        if "cpu_choice" not in st.session_state or st.session_state.party.get("opponent") is None:
            cpu_choice = random.choice(poke_names)
            clower = cpu_choice.lower()
            if clower not in st.session_state.cache_pokemon:
                st.session_state.cache_pokemon[clower] = load_pokemon_by_name(clower)
            cdetails = st.session_state.cache_pokemon[clower]
            cbase = compute_base_stats(cdetails)
            st.session_state.party["opponent"] = {
                "name": cpu_choice,
                "level": random.randint(4, 8),
                "xp": 0,
                "attack": cbase["attack"],
                "defense": cbase["defense"],
                "max_hp": cbase["max_hp"],
                "hp": cbase["max_hp"],
                "moves": cbase["moves"],
                "sprite": cbase["sprite"],
                "items": {}
            }

# -----------------------
# Battle UI & Controls
# -----------------------
st.markdown("---")
st.header("2) Battle Arena")

arena_col1, arena_col2, arena_col3 = st.columns([2, 2, 1])

# Determine active players
player1 = st.session_state.party.get("player1")
if st.session_state.multiplayer:
    player2 = st.session_state.party.get("player2")
    opponent = player2
    player_slot_names = ("player1", "player2")
else:
    player2 = st.session_state.party.get("opponent")
    opponent = player2
    player_slot_names = ("player1", "opponent")

# Show both combatants
with arena_col1:
    if player1:
        st.subheader(f"Player 1 — {player1['name']} (Lv {player1['level']})")
        if player1["sprite"]:
            st.image(player1["sprite"], width=220)
        st.text(f"HP: {player1['hp']} / {player1['max_hp']}")
        # HP progress bar (animated via key update)
        pct1 = max(0.0, player1["hp"] / player1["max_hp"])
        st.progress(pct1)
with arena_col2:
    if opponent:
        title = "Player 2" if st.session_state.multiplayer else "CPU Opponent"
        st.subheader(f"{title} — {opponent['name']} (Lv {opponent['level']})")
        if opponent["sprite"]:
            st.image(opponent["sprite"], width=220)
        st.text(f"HP: {opponent['hp']} / {opponent['max_hp']}")
        pct2 = max(0.0, opponent["hp"] / opponent["max_hp"])
        st.progress(pct2)

# Battle controls (center)
with arena_col3:
    st.write("**Turn**")
    current_turn = st.session_state.turn
    st.info(f"Now: {current_turn}")

st.markdown("### Actions")

action_col1, action_col2 = st.columns(2)

# Actions for Player whose turn it is
def reset_battle_log():
    st.session_state.battle_log = []

def add_log(msg):
    st.session_state.battle_log.append(msg)

def end_turn():
    if st.session_state.multiplayer:
        st.session_state.turn = "player2" if st.session_state.turn == "player1" else "player1"
    else:
        st.session_state.turn = "opponent" if st.session_state.turn == "player1" else "player1"

def try_level_up(slot):
    p = st.session_state.party.get(slot)
    if not p:
        return
    # simple xp threshold
    threshold = 100 + (p["level"] - 1) * 40
    if p["xp"] >= threshold:
        p["xp"] -= threshold
        p["level"] += 1
        # upgrade stats modestly
        p["attack"] = int(p["attack"] * 1.08)
        p["defense"] = int(p["defense"] * 1.07)
        p["max_hp"] = int(p["max_hp"] * 1.12)
        p["hp"] = p["max_hp"]
        add_log(f"✨ {p['name']} leveled up to {p['level']}! Stats increased.")

def perform_attack(attacker_slot, defender_slot, move_name, use_power_boost=False):
    attacker = st.session_state.party.get(attacker_slot)
    defender = st.session_state.party.get(defender_slot)
    if not attacker or not defender:
        return

    # shield active?
    defender_shield = False
    # Check if defender has Shield active flag (we won't implement lasting shields, just item used on defender's previous turn)
    # Items simple: immediate effect at use time, not persistent unless we implement statuses.

    # power boost
    power_mod = 1.5 if use_power_boost else 1.0

    # Calculate damage
    dmg = calculate_damage(attacker, defender, power_mod=power_mod, shield=defender_shield)
    defender["hp"] -= dmg
    if defender["hp"] < 0:
        defender["hp"] = 0

    add_log(f"⚔️ {attacker['name']} used **{move_name}** and dealt **{dmg}** damage to {defender['name']}.")

    # play sounds
    play_sound(AUDIO_ATTACK)
    time.sleep(0.15)
    play_sound(AUDIO_HIT)

    # check faint
    if defender["hp"] == 0:
        add_log(f"💀 {defender['name']} fainted!")
        play_sound(AUDIO_FAINT)
        # winner XP
        winner_xp = 60 + defender.get("level", 5) * 8
        attacker["xp"] += winner_xp
        add_log(f"🏆 {attacker['name']} gains {winner_xp} XP.")
        try_level_up(attacker_slot)

def use_item(slot, item_name, target_slot=None):
    p = st.session_state.party.get(slot)
    if not p:
        return
    items = p.get("items", {})
    if items.get(item_name, 0) <= 0:
        add_log(f"❌ {p['name']} has no {item_name}s left.")
        return
    # consume
    items[item_name] -= 1
    add_log(f"🧪 {p['name']} used {item_name}!")
    if item_name == "Potion":
        heal_amount = int(p["max_hp"] * 0.35)
        p["hp"] = min(p["max_hp"], p["hp"] + heal_amount)
        add_log(f"❤️ {p['name']} healed {heal_amount} HP.")
    elif item_name == "Shield":
        # apply to target if provided otherwise to self
        target = st.session_state.party.get(target_slot) if target_slot else p
        # simple immediate effect: next incoming damage is reduced in calculation by flag set (we implement as temp field)
        target["_temp_shield"] = True
        add_log(f"🛡 {target['name']} will take reduced damage next hit.")
    elif item_name == "Power Boost":
        # give attacker a temporary attack boost for next attack
        p["_temp_power"] = 1.5
        add_log(f"⚡ {p['name']}'s next attack will deal increased damage.")

# UI: show moves + items for player whose turn it is
active_slot = st.session_state.turn
inactive_slot = "player2" if active_slot == "player1" else "player1"
if not st.session_state.multiplayer:
    inactive_slot = "opponent" if active_slot == "player1" else "player1"

active_player = st.session_state.party.get(active_slot)
inactive_player = st.session_state.party.get(inactive_slot)

if active_player is None or inactive_player is None:
    st.warning("Select Pokémon first to start battle.")
else:
    # show moves
    st.subheader(f"Actions — {active_player['name']} (Turn)")

    cols = st.columns([1, 1, 1])
    with cols[0]:
        st.markdown("**Moves**")
        move_choice = st.selectbox("Choose move", active_player["moves"], key=f"move_{active_slot}")
        if st.button("Use Move", key=f"use_move_{active_slot}"):
            # check temp power
            use_power = False
            if active_player.get("_temp_power"):
                use_power = True
                del active_player["_temp_power"]
            # check target shield on defender
            def_shield = bool(inactive_player.get("_temp_shield"))
            if def_shield:
                # consume shield flag and mark a local effect
                inactive_player["_temp_shield"] = False
            # perform attack using modified defender shield flag
            # To support shield we pass shield flag
            if def_shield:
                # calculate damage with shield True
                dmg = calculate_damage(active_player, inactive_player, power_mod=1.5 if use_power else 1.0, shield=True)
                inactive_player["hp"] = max(0, inactive_player["hp"] - dmg)
                add_log(f"⚔️ {active_player['name']} used **{move_choice}** and dealt **{dmg}** damage (reduced by Shield) to {inactive_player['name']}.")
            else:
                perform_attack(active_slot, inactive_slot, move_choice, use_power_boost=use_power)
            # after action check faint and end turn (with CPU auto actions)
            if inactive_player["hp"] == 0:
                # victory handling
                add_log(f"🎉 {active_player['name']} won the battle!")
                play_sound(AUDIO_WIN)
                # Reward xp already applied by perform_attack/logic
            else:
                # if singleplayer and opponent, do auto counter
                if not st.session_state.multiplayer and inactive_slot == "opponent":
                    time.sleep(0.6)
                    # CPU selects move and may use item randomly
                    cpu_use_item = random.random() < 0.18
                    if cpu_use_item and inactive_player.get("items"):
                        # try potion if hp low
                        if inactive_player["hp"] < inactive_player["max_hp"] * 0.45 and inactive_player.get("items", {}).get("Potion", 0) > 0:
                            use_item(inactive_slot, "Potion")
                        else:
                            # else 20% chance to use power boost
                            if inactive_player.get("items", {}).get("Power Boost", 0) > 0 and random.random() < 0.4:
                                use_item(inactive_slot, "Power Boost")
                    # CPU attack
                    cpu_move = random.choice(inactive_player["moves"])
                    # check temp power/shield
                    cpu_power = False
                    if inactive_player.get("_temp_power"):
                        cpu_power = True
                        del inactive_player["_temp_power"]
                    target_shield = bool(active_player.get("_temp_shield"))
                    if target_shield:
                        active_player["_temp_shield"] = False
                        dmg = calculate_damage(inactive_player, active_player, power_mod=1.5 if cpu_power else 1.0, shield=True)
                        active_player["hp"] = max(0, active_player["hp"] - dmg)
                        add_log(f"💥 CPU {inactive_player['name']} used **{cpu_move}** and dealt **{dmg}** (reduced by Shield) to {active_player['name']}.")
                    else:
                        perform_attack(inactive_slot, active_slot, cpu_move, use_power_boost=cpu_power)
                else:
                    # just change turn
                    end_turn()
    with cols[1]:
        st.markdown("**Items**")
        it_choice = st.selectbox("Choose item", list(active_player.get("items", {}).keys()), key=f"item_{active_slot}")
        if st.button("Use Item", key=f"use_item_{active_slot}"):
            # for Shield item, ask target if multiplayer
            tgt = None
            if it_choice == "Shield" and st.session_state.multiplayer:
                # offer choice to use on self or ally (for simplicity only self or the other)
                # here we'll just apply to self in this simple flow
                tgt = active_slot
            use_item(active_slot, it_choice, target_slot=tgt)
            # end turn after using item
            if not st.session_state.multiplayer and active_slot == "player1":
                # CPU might act immediately if singleplayer
                time.sleep(0.5)
                # CPU randomly act
                cpu_move = random.choice(inactive_player["moves"])
                perform_attack(inactive_slot, active_slot, cpu_move)
            else:
                end_turn()
    with cols[2]:
        st.markdown("**Utility**")
        if st.button("Forfeit / Restart Match"):
            # reset hp to max for both and clear log
            for s in player_slot_names:
                if st.session_state.party.get(s):
                    st.session_state.party[s]["hp"] = st.session_state.party[s]["max_hp"]
                    # replenish some items moderately
                    st.session_state.party[s]["items"] = {"Potion": 2, "Shield": 1, "Power Boost": 1}
            reset_battle_log()
            st.success("Match reset.")
            st.experimental_rerun()

# -----------------------
# Battle Log & XP Panels
# -----------------------
st.markdown("---")
left_col, right_col = st.columns([2, 1])

with left_col:
    st.subheader("Battle Log")
    for entry in st.session_state.battle_log[-30:]:
        st.write(entry)

with right_col:
    st.subheader("Player Stats & Inventory")
    for slot in player_slot_names:
        p = st.session_state.party.get(slot)
        if not p:
            continue
        st.markdown(f"**{slot.upper()}: {p['name']} (Lv {p['level']})**")
        st.write(f"HP: {p['hp']} / {p['max_hp']}")
        st.progress(max(0.0, p['hp'] / p['max_hp']))
        st.write(f"Attack: {p['attack']}  Defense: {p['defense']}")
        st.write(f"XP: {p['xp']} / {100 + (p['level']-1)*40}")
        st.write("Items:")
        for itnm, qty in p.get("items", {}).items():
            st.write(f"- {itnm}: {qty}")

# -----------------------
# Endgame detection & rewards
# -----------------------
def detect_and_handle_victory():
    # check if any side has all fainted (for simplicity we consider single-mon battles)
    p1_dead = st.session_state.party["player1"]["hp"] <= 0
    opp_dead = st.session_state.party[player_slot_names[1]]["hp"] <= 0
    if p1_dead and opp_dead:
        add_log("It's a double KO!")
    elif opp_dead:
        add_log("🏆 Player 1 wins the match!")
        # apply reward xp already applied earlier; give bonus
        st.session_state.party["player1"]["xp"] += 30
        try_level_up("player1")
    elif p1_dead:
        add_log("🏆 Opponent wins the match!")
        if st.session_state.multiplayer:
            st.session_state.party["player2"]["xp"] += 30
            try_level_up("player2")

detect_and_handle_victory()

# -----------------------
# Final controls & tips
# -----------------------
st.markdown("---")
st.caption("Tips: Use Potions when low HP, Shields to reduce big hits, and Power Boost before a big attack.")

st.write("If you want me to export this to a packaged app with hosted audio and custom images, say `package` and I’ll prepare a deployment guide.")

