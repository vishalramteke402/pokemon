import streamlit as st
import random
import time

st.set_page_config(page_title="Pokémon Battle Game", page_icon="🔥", layout="centered")

# ----------------------------- #
#       Pokémon Database        #
# ----------------------------- #
pokemon_data = {
    "Pikachu": {
        "attack": 55,
        "defense": 40,
        "hp": 120,
        "image": "https://img.pokemondb.net/artwork/large/pikachu.jpg",
        "moves": ["Thunderbolt", "Quick Attack", "Electro Ball", "Iron Tail"]
    },
    "Charizard": {
        "attack": 84,
        "defense": 78,
        "hp": 160,
        "image": "https://img.pokemondb.net/artwork/large/charizard.jpg",
        "moves": ["Flamethrower", "Fly", "Fire Spin", "Dragon Claw"]
    },
    "Bulbasaur": {
        "attack": 49,
        "defense": 49,
        "hp": 140,
        "image": "https://img.pokemondb.net/artwork/large/bulbasaur.jpg",
        "moves": ["Vine Whip", "Seed Bomb", "Tackle", "Razor Leaf"]
    },
    "Squirtle": {
        "attack": 48,
        "defense": 65,
        "hp": 135,
        "image": "https://img.pokemondb.net/artwork/large/squirtle.jpg",
        "moves": ["Water Gun", "Bubble", "Bite", "Aqua Tail"]
    },
    "Gengar": {
        "attack": 65,
        "defense": 60,
        "hp": 130,
        "image": "https://img.pokemondb.net/artwork/large/gengar.jpg",
        "moves": ["Shadow Ball", "Lick", "Dark Pulse", "Night Shade"]
    }
}

# ----------------------------- #
#         Game Setup            #
# ----------------------------- #
st.title("🎮 Advanced Pokémon Battle Game")
st.write("Choose a Pokémon and battle turn-by-turn!")

player_pokemon = st.selectbox("Select your Pokémon:", list(pokemon_data.keys()))

# Opponent random Pokémon
opponent_pokemon = random.choice(list(pokemon_data.keys()))

# Initialize session state
if "player_hp" not in st.session_state:
    st.session_state.player_hp = pokemon_data[player_pokemon]["hp"]

if "opponent_hp" not in st.session_state:
    st.session_state.opponent_hp = pokemon_data[opponent_pokemon]["hp"]

if "battle_log" not in st.session_state:
    st.session_state.battle_log = []

# Pokémon side-by-side UI
col1, col2 = st.columns(2)

with col1:
    st.subheader("Your Pokémon")
    st.image(pokemon_data[player_pokemon]["image"], width=200)
    st.write(f"**{player_pokemon} HP:**")
    st.progress(st.session_state.player_hp / pokemon_data[player_pokemon]["hp"])

with col2:
    st.subheader("Opponent Pokémon")
    st.image(pokemon_data[opponent_pokemon]["image"], width=200)
    st.write(f"**{opponent_pokemon} HP:**")
    st.progress(st.session_state.opponent_hp / pokemon_data[opponent_pokemon]["hp"])


# ----------------------------- #
#       Damage Calculation      #
# ----------------------------- #
def calculate_damage(attacker, defender):
    atk = pokemon_data[attacker]["attack"]
    defn = pokemon_data[defender]["defense"]

    base_damage = atk - (defn * 0.3)
    random_factor = random.randint(5, 20)

    return max(10, int(base_damage + random_factor))


# ----------------------------- #
#         Battle System         #
# ----------------------------- #
st.subheader("⚔ Select Your Move")

move_selected = st.radio(
    "Choose an attack:",
    pokemon_data[player_pokemon]["moves"]
)

if st.button("Attack"):
    # Player attack
    damage = calculate_damage(player_pokemon, opponent_pokemon)
    st.session_state.opponent_hp -= damage
    st.session_state.battle_log.append(f"🔥 {player_pokemon} used **{move_selected}** and dealt **{damage} damage**!")

    time.sleep(0.5)

    # Check if opponent fainted
    if st.session_state.opponent_hp <= 0:
        st.success(f"🎉 {player_pokemon} WINS the battle!")
    else:
        # Opponent counter-attack
        opponent_move = random.choice(pokemon_data[opponent_pokemon]["moves"])
        opp_damage = calculate_damage(opponent_pokemon, player_pokemon)
        st.session_state.player_hp -= opp_damage
        st.session_state.battle_log.append(
            f"💀 {opponent_pokemon} used **{opponent_move}** and dealt **{opp_damage} damage**!"
        )

        if st.session_state.player_hp <= 0:
            st.error(f"💀 {opponent_pokemon} defeats you... Game Over!")


# ----------------------------- #
#          Battle Log           #
# ----------------------------- #
st.subheader("📜 Battle Log")
for log in st.session_state.battle_log[-10:]:
    st.write(log)

# Reset game
if st.button("Restart Game"):
    st.session_state.player_hp = pokemon_data[player_pokemon]["hp"]
    st.session_state.opponent_hp = pokemon_data[opponent_pokemon]["hp"]
    st.session_state.battle_log = []
    st.experimental_rerun()

st.write("---")
st.caption("Made with ❤️ using Streamlit – Pokémon Battle Edition")
