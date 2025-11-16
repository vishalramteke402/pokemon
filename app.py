import streamlit as st
import random

# Pokémon type effectiveness chart
type_chart = {
    "Fire": {"strong": "Grass", "weak": "Water"},
    "Water": {"strong": "Fire", "weak": "Grass"},
    "Grass": {"strong": "Water", "weak": "Fire"},
}

# Pokémon class to track stats and battle mechanics
class Pokemon:
    def __init__(self, name, poke_type, hp, attack, defense, moves):
        self.name = name
        self.poke_type = poke_type
        self.max_hp = hp
        self.hp = hp
        self.attack = attack
        self.defense = defense
        self.moves = moves

    def is_alive(self):
        return self.hp > 0

    def take_damage(self, damage):
        self.hp = max(0, self.hp - damage)

    def use_move(self, move, opponent):
        if move not in self.moves:
            return f"{self.name} does not know {move}!"
        multiplier = 1
        if type_chart[self.poke_type]["strong"] == opponent.poke_type:
            multiplier = 2
        elif type_chart[self.poke_type]["weak"] == opponent.poke_type:
            multiplier = 0.5
        base_power = self.moves[move]
        damage = int((base_power + self.attack - opponent.defense) * multiplier)
        damage = max(damage, 1)  # Minimum damage
        opponent.take_damage(damage)
        eff_text = ""
        if multiplier == 2:
            eff_text = " It's super effective!"
        elif multiplier == 0.5:
            eff_text = " It's not very effective..."
        return f"{self.name} used {move}!{eff_text} It dealt {damage} damage."

# Stateful storage of Pokémon and battle log
if "pikachu" not in st.session_state:
    st.session_state.pikachu = Pokemon(
        name="Pikachu",
        poke_type="Fire",
        hp=60,
        attack=18,
        defense=8,
        moves={"Thunderbolt": 20, "Quick Attack": 10},
    )

if "bulbasaur" not in st.session_state:
    st.session_state.bulbasaur = Pokemon(
        name="Bulbasaur",
        poke_type="Grass",
        hp=70,
        attack=14,
        defense=10,
        moves={"Vine Whip": 18, "Tackle": 12},
    )

if "turn" not in st.session_state:
    st.session_state.turn = 0  # 0 = player's turn (Pikachu), 1 = AI's (Bulbasaur)

if "battle_log" not in st.session_state:
    st.session_state.battle_log = []

if "battle_over" not in st.session_state:
    st.session_state.battle_over = False

st.title("Simple Pokémon Battle in Streamlit")

# Display HP bars
def hp_bar(pokemon):
    bar_length = 100
    hp_ratio = pokemon.hp / pokemon.max_hp
    return f"{pokemon.name} HP: [{'█' * int(hp_ratio * 20):<20}] {pokemon.hp}/{pokemon.max_hp}"

st.write(hp_bar(st.session_state.pikachu))
st.write(hp_bar(st.session_state.bulbasaur))

# Show battle log
st.subheader("Battle Log")
for line in st.session_state.battle_log[-6:]:
    st.write(line)

# Player's turn to choose a move
if not st.session_state.battle_over:
    if st.session_state.turn == 0:
        st.subheader("Your turn! Choose a move:")
        move = st.selectbox("Select move", list(st.session_state.pikachu.moves.keys()))
        if st.button("Attack"):
            msg = st.session_state.pikachu.use_move(move, st.session_state.bulbasaur)
            st.session_state.battle_log.append(msg)
            if not st.session_state.bulbasaur.is_alive():
                st.session_state.battle_log.append(f"{st.session_state.bulbasaur.name} fainted! You win!")
                st.session_state.battle_over = True
            else:
                st.session_state.turn = 1

    # AI's turn
    elif st.session_state.turn == 1:
        st.subheader("Bulbasaur is attacking...")
        move = random.choice(list(st.session_state.bulbasaur.moves.keys()))
        msg = st.session_state.bulbasaur.use_move(move, st.session_state.pikachu)
        st.session_state.battle_log.append(msg)
        if not st.session_state.pikachu.is_alive():
            st.session_state.battle_log.append(f"{st.session_state.pikachu.name} fainted! You lose!")
            st.session_state.battle_over = True
        else:
            st.session_state.turn = 0

# Button to reset the game
if st.button("Restart Game"):
    st.session_state.pikachu.hp = st.session_state.pikachu.max_hp
    st.session_state.bulbasaur.hp = st.session_state.bulbasaur.max_hp
    st.session_state.battle_log = []
    st.session_state.turn = 0
    st.session_state.battle_over = False
