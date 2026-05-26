
"""Card definitions and database for the Pokémon Card Game."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Dict, Set
import json
import random
import copy


class PokemonType(Enum):
    """Pokémon types with their display names."""
    FIRE = "Fire"
    WATER = "Water"
    GRASS = "Grass"
    ELECTRIC = "Electric"
    PSYCHIC = "Psychic"
    FIGHTING = "Fighting"
    DARK = "Dark"
    STEEL = "Steel"
    FAIRY = "Fairy"
    NORMAL = "Normal"
    DRAGON = "Dragon"
    ICE = "Ice"
    POISON = "Poison"
    ROCK = "Rock"
    GHOST = "Ghost"


class CardType(Enum):
    """Types of cards in the game."""
    POKEMON = auto()
    ENERGY = auto()
    TRAINER = auto()


class TrainerType(Enum):
    """Sub-types of trainer cards."""
    ITEM = auto()
    SUPPORTER = auto()
    STADIUM = auto()


class TrainerEffect(Enum):
    """Machine-readable trainer effects to avoid string matching."""
    HEAL_30 = auto()
    HEAL_60 = auto()
    DRAW_3 = auto()
    SWITCH = auto()
    FULL_HEAL = auto()
    ENERGY_RETRIEVAL = auto()


# Complete type effectiveness chart (attacker, defender): multiplier
TYPE_CHART: Dict[tuple, float] = {
    (PokemonType.FIRE, PokemonType.GRASS): 2.0,
    (PokemonType.FIRE, PokemonType.WATER): 0.5,
    (PokemonType.FIRE, PokemonType.FIRE): 0.5,
    (PokemonType.FIRE, PokemonType.STEEL): 2.0,
    (PokemonType.WATER, PokemonType.FIRE): 2.0,
    (PokemonType.WATER, PokemonType.GRASS): 0.5,
    (PokemonType.WATER, PokemonType.WATER): 0.5,
    (PokemonType.WATER, PokemonType.DRAGON): 0.5,
    (PokemonType.GRASS, PokemonType.WATER): 2.0,
    (PokemonType.GRASS, PokemonType.FIRE): 0.5,
    (PokemonType.GRASS, PokemonType.GRASS): 0.5,
    (PokemonType.GRASS, PokemonType.DRAGON): 0.5,
    (PokemonType.ELECTRIC, PokemonType.WATER): 2.0,
    (PokemonType.ELECTRIC, PokemonType.ELECTRIC): 0.5,
    (PokemonType.ELECTRIC, PokemonType.GRASS): 0.5,
    (PokemonType.ELECTRIC, PokemonType.DRAGON): 0.5,
    (PokemonType.PSYCHIC, PokemonType.FIGHTING): 2.0,
    (PokemonType.PSYCHIC, PokemonType.PSYCHIC): 0.5,
    (PokemonType.PSYCHIC, PokemonType.DARK): 0.0,
    (PokemonType.PSYCHIC, PokemonType.STEEL): 0.5,
    (PokemonType.FIGHTING, PokemonType.DARK): 2.0,
    (PokemonType.FIGHTING, PokemonType.STEEL): 2.0,
    (PokemonType.FIGHTING, PokemonType.PSYCHIC): 0.5,
    (PokemonType.FIGHTING, PokemonType.FAIRY): 0.5,
    (PokemonType.FIGHTING, PokemonType.GRASS): 0.5,
    (PokemonType.DARK, PokemonType.PSYCHIC): 2.0,
    (PokemonType.DARK, PokemonType.DARK): 0.5,
    (PokemonType.DARK, PokemonType.FAIRY): 0.5,
    (PokemonType.DARK, PokemonType.FIGHTING): 0.5,
    (PokemonType.STEEL, PokemonType.FAIRY): 2.0,
    (PokemonType.STEEL, PokemonType.ICE): 2.0,  # Note: Ice not in enum
    (PokemonType.STEEL, PokemonType.STEEL): 0.5,
    (PokemonType.STEEL, PokemonType.FIRE): 0.5,
    (PokemonType.STEEL, PokemonType.WATER): 0.5,
    (PokemonType.STEEL, PokemonType.ELECTRIC): 0.5,
    (PokemonType.FAIRY, PokemonType.DRAGON): 2.0,
    (PokemonType.FAIRY, PokemonType.DARK): 2.0,
    (PokemonType.FAIRY, PokemonType.FIRE): 0.5,
    (PokemonType.FAIRY, PokemonType.POISON): 0.5,  # Note: Poison not in enum
    (PokemonType.DRAGON, PokemonType.DRAGON): 2.0,
    (PokemonType.DRAGON, PokemonType.FAIRY): 0.0,
    (PokemonType.NORMAL, PokemonType.ROCK): 0.5,  # Note: Rock not in enum
    (PokemonType.NORMAL, PokemonType.STEEL): 0.5,
    (PokemonType.NORMAL, PokemonType.GHOST): 0.0,  # Note: Ghost not in enum
}


def get_type_effectiveness(attack_type: PokemonType, defend_type: PokemonType) -> float:
    """Get the damage multiplier for an attack type against a defender type."""
    return TYPE_CHART.get((attack_type, defend_type), 1.0)


@dataclass
class Attack:
    """Represents a Pokémon attack."""
    name: str
    damage: int
    energy_cost: int
    energy_type: PokemonType
    effect: Optional[str] = None
    effect_chance: float = 0.3


@dataclass
class PokemonCard:
    """Represents a Pokémon card."""
    id: str
    name: str
    pokemon_type: PokemonType
    hp: int
    attacks: List[Attack]
    weakness: PokemonType
    resistance: PokemonType
    retreat_cost: int
    card_type: CardType = field(default=CardType.POKEMON, init=False)

    # Mutable state (not part of card identity)
    current_hp: int = field(init=False)
    attached_energies: List[PokemonType] = field(default_factory=list, init=False)
    status: Optional[str] = field(default=None, init=False)
    is_active: bool = field(default=False, init=False)

    def __post_init__(self):
        self.current_hp = self.hp

    def is_knocked_out(self) -> bool:
        return self.current_hp <= 0

    def can_attack(self, attack_index: int) -> bool:
        if self.status == "paralyzed":
            return False
        if attack_index >= len(self.attacks):
            return False
        attack = self.attacks[attack_index]
        matching_energy = sum(
            1 for e in self.attached_energies if e == attack.energy_type
        )
        return matching_energy >= attack.energy_cost

    def get_attack_damage(self, attack_index: int, target: 'PokemonCard') -> int:
        """Calculate final damage including all modifiers."""
        if attack_index >= len(self.attacks):
            return 0

        attack = self.attacks[attack_index]
        base_damage = attack.damage

        # STAB (Same Type Attack Bonus): +10 if attack type matches pokemon type
        stab_bonus = 10 if attack.energy_type == self.pokemon_type else 0

        # Type effectiveness
        effectiveness = get_type_effectiveness(attack.energy_type, target.pokemon_type)

        # Resistance: flat -30 reduction (not percentage)
        resistance_reduction = 30 if target.resistance == attack.energy_type else 0

        # Calculate final damage
        damage_after_stab = base_damage + stab_bonus
        damage_after_effectiveness = int(damage_after_stab * effectiveness)
        final_damage = max(0, damage_after_effectiveness - resistance_reduction)

        return final_damage

    def copy(self) -> 'PokemonCard':
        """Create a deep copy of this card."""
        return PokemonCard(
            id=self.id,
            name=self.name,
            pokemon_type=self.pokemon_type,
            hp=self.hp,
            attacks=[Attack(a.name, a.damage, a.energy_cost, a.energy_type, a.effect, a.effect_chance) 
                     for a in self.attacks],
            weakness=self.weakness,
            resistance=self.resistance,
            retreat_cost=self.retreat_cost
        )


@dataclass
class EnergyCard:
    """Represents an energy card."""
    id: str
    name: str
    energy_type: PokemonType
    card_type: CardType = field(default=CardType.ENERGY, init=False)

    def copy(self) -> 'EnergyCard':
        return EnergyCard(id=self.id, name=self.name, energy_type=self.energy_type)


@dataclass
class TrainerCard:
    """Represents a trainer card."""
    id: str
    name: str
    trainer_type: TrainerType
    effect: TrainerEffect
    effect_description: str
    card_type: CardType = field(default=CardType.TRAINER, init=False)
    target_required: bool = False  # Whether card needs a target selection

    def copy(self) -> 'TrainerCard':
        return TrainerCard(
            id=self.id, name=self.name, trainer_type=self.trainer_type,
            effect=self.effect, effect_description=self.effect_description,
            target_required=self.target_required
        )


# ============ CARD DATABASE ============
def create_card_database() -> List:
    """Create a comprehensive set of Pokémon cards."""
    cards = []

    # FIRE POKEMON
    cards.append(PokemonCard(
        id="charizard", name="Charizard",
        pokemon_type=PokemonType.FIRE, hp=120,
        attacks=[
            Attack("Fire Spin", 30, 1, PokemonType.FIRE),
            Attack("Flamethrower", 60, 2, PokemonType.FIRE, "burned", 0.3)
        ],
        weakness=PokemonType.WATER, resistance=PokemonType.GRASS,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="arcanine", name="Arcanine",
        pokemon_type=PokemonType.FIRE, hp=100,
        attacks=[
            Attack("Flame Burst", 20, 1, PokemonType.FIRE),
            Attack("Fire Blast", 70, 2, PokemonType.FIRE)
        ],
        weakness=PokemonType.WATER, resistance=PokemonType.GRASS,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="magmar", name="Magmar",
        pokemon_type=PokemonType.FIRE, hp=80,
        attacks=[
            Attack("Ember", 20, 1, PokemonType.FIRE),
            Attack("Fire Punch", 40, 2, PokemonType.FIRE, "burned", 0.3)
        ],
        weakness=PokemonType.WATER, resistance=PokemonType.GRASS,
        retreat_cost=1
    ))

    # WATER POKEMON
    cards.append(PokemonCard(
        id="blastoise", name="Blastoise",
        pokemon_type=PokemonType.WATER, hp=120,
        attacks=[
            Attack("Water Gun", 30, 1, PokemonType.WATER),
            Attack("Hydro Pump", 70, 2, PokemonType.WATER)
        ],
        weakness=PokemonType.ELECTRIC, resistance=PokemonType.FIRE,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="gyarados", name="Gyarados",
        pokemon_type=PokemonType.WATER, hp=130,
        attacks=[
            Attack("Aqua Tail", 40, 1, PokemonType.WATER),
            Attack("Dragon Rage", 80, 2, PokemonType.WATER)
        ],
        weakness=PokemonType.ELECTRIC, resistance=PokemonType.FIRE,
        retreat_cost=3
    ))

    cards.append(PokemonCard(
        id="vaporeon", name="Vaporeon",
        pokemon_type=PokemonType.WATER, hp=90,
        attacks=[
            Attack("Bubble", 20, 1, PokemonType.WATER),
            Attack("Aurora Beam", 50, 2, PokemonType.WATER)
        ],
        weakness=PokemonType.ELECTRIC, resistance=PokemonType.FIRE,
        retreat_cost=1
    ))

    # GRASS POKEMON
    cards.append(PokemonCard(
        id="venusaur", name="Venusaur",
        pokemon_type=PokemonType.GRASS, hp=120,
        attacks=[
            Attack("Vine Whip", 30, 1, PokemonType.GRASS),
            Attack("Solar Beam", 70, 2, PokemonType.GRASS)
        ],
        weakness=PokemonType.FIRE, resistance=PokemonType.WATER,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="exeggutor", name="Exeggutor",
        pokemon_type=PokemonType.GRASS, hp=100,
        attacks=[
            Attack("Stomp", 20, 1, PokemonType.GRASS),
            Attack("Solar Beam", 60, 2, PokemonType.GRASS)
        ],
        weakness=PokemonType.FIRE, resistance=PokemonType.WATER,
        retreat_cost=2
    ))

    # ELECTRIC POKEMON
    cards.append(PokemonCard(
        id="pikachu", name="Pikachu",
        pokemon_type=PokemonType.ELECTRIC, hp=60,
        attacks=[
            Attack("Thunder Jolt", 20, 1, PokemonType.ELECTRIC),
            Attack("Thunder", 60, 2, PokemonType.ELECTRIC, "paralyzed", 0.3)
        ],
        weakness=PokemonType.FIGHTING, resistance=PokemonType.STEEL,
        retreat_cost=1
    ))

    cards.append(PokemonCard(
        id="raichu", name="Raichu",
        pokemon_type=PokemonType.ELECTRIC, hp=90,
        attacks=[
            Attack("Spark", 30, 1, PokemonType.ELECTRIC),
            Attack("Thunderbolt", 70, 2, PokemonType.ELECTRIC, "paralyzed", 0.3)
        ],
        weakness=PokemonType.FIGHTING, resistance=PokemonType.STEEL,
        retreat_cost=1
    ))

    cards.append(PokemonCard(
        id="jolteon", name="Jolteon",
        pokemon_type=PokemonType.ELECTRIC, hp=80,
        attacks=[
            Attack("Thunder Shock", 20, 1, PokemonType.ELECTRIC),
            Attack("Pin Missile", 50, 2, PokemonType.ELECTRIC)
        ],
        weakness=PokemonType.FIGHTING, resistance=PokemonType.STEEL,
        retreat_cost=1
    ))

    # PSYCHIC POKEMON
    cards.append(PokemonCard(
        id="mewtwo", name="Mewtwo",
        pokemon_type=PokemonType.PSYCHIC, hp=130,
        attacks=[
            Attack("Psyburn", 40, 1, PokemonType.PSYCHIC),
            Attack("Psystrike", 80, 2, PokemonType.PSYCHIC)
        ],
        weakness=PokemonType.DARK, resistance=PokemonType.FIGHTING,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="alakazam", name="Alakazam",
        pokemon_type=PokemonType.PSYCHIC, hp=90,
        attacks=[
            Attack("Confusion", 30, 1, PokemonType.PSYCHIC),
            Attack("Psychic", 60, 2, PokemonType.PSYCHIC)
        ],
        weakness=PokemonType.DARK, resistance=PokemonType.FIGHTING,
        retreat_cost=1
    ))

    # FIGHTING POKEMON
    cards.append(PokemonCard(
        id="machamp", name="Machamp",
        pokemon_type=PokemonType.FIGHTING, hp=110,
        attacks=[
            Attack("Karate Chop", 30, 1, PokemonType.FIGHTING),
            Attack("Cross Chop", 70, 2, PokemonType.FIGHTING)
        ],
        weakness=PokemonType.PSYCHIC, resistance=PokemonType.DARK,
        retreat_cost=2
    ))

    cards.append(PokemonCard(
        id="lucario", name="Lucario",
        pokemon_type=PokemonType.FIGHTING, hp=100,
        attacks=[
            Attack("Force Palm", 30, 1, PokemonType.FIGHTING),
            Attack("Aura Sphere", 60, 2, PokemonType.FIGHTING)
        ],
        weakness=PokemonType.PSYCHIC, resistance=PokemonType.DARK,
        retreat_cost=1
    ))

    # DARK POKEMON
    cards.append(PokemonCard(
        id="gengar", name="Gengar",
        pokemon_type=PokemonType.DARK, hp=100,
        attacks=[
            Attack("Shadow Punch", 30, 1, PokemonType.DARK),
            Attack("Shadow Ball", 60, 2, PokemonType.DARK, "poisoned", 0.3)
        ],
        weakness=PokemonType.FAIRY, resistance=PokemonType.PSYCHIC,
        retreat_cost=1
    ))

    cards.append(PokemonCard(
        id="tyranitar", name="Tyranitar",
        pokemon_type=PokemonType.DARK, hp=130,
        attacks=[
            Attack("Crunch", 40, 1, PokemonType.DARK),
            Attack("Dark Pulse", 80, 2, PokemonType.DARK)
        ],
        weakness=PokemonType.FAIRY, resistance=PokemonType.PSYCHIC,
        retreat_cost=3
    ))

    # DRAGON POKEMON
    cards.append(PokemonCard(
        id="dragonite", name="Dragonite",
        pokemon_type=PokemonType.DRAGON, hp=130,
        attacks=[
            Attack("Dragon Tail", 30, 1, PokemonType.DRAGON),
            Attack("Draco Meteor", 90, 2, PokemonType.DRAGON)
        ],
        weakness=PokemonType.FAIRY, resistance=PokemonType.DRAGON,
        retreat_cost=3
    ))

    # FAIRY POKEMON
    cards.append(PokemonCard(
        id="gardevoir", name="Gardevoir",
        pokemon_type=PokemonType.FAIRY, hp=110,
        attacks=[
            Attack("Fairy Wind", 30, 1, PokemonType.FAIRY),
            Attack("Moonblast", 70, 2, PokemonType.FAIRY)
        ],
        weakness=PokemonType.STEEL, resistance=PokemonType.DARK,
        retreat_cost=1
    ))

    # NORMAL POKEMON
    cards.append(PokemonCard(
        id="snorlax", name="Snorlax",
        pokemon_type=PokemonType.NORMAL, hp=140,
        attacks=[
            Attack("Body Slam", 30, 1, PokemonType.NORMAL, "paralyzed", 0.3),
            Attack("Hyper Beam", 70, 2, PokemonType.NORMAL)
        ],
        weakness=PokemonType.FIGHTING, resistance=PokemonType.PSYCHIC,
        retreat_cost=4
    ))

    cards.append(PokemonCard(
        id="eevee", name="Eevee",
        pokemon_type=PokemonType.NORMAL, hp=60,
        attacks=[
            Attack("Tackle", 10, 1, PokemonType.NORMAL),
            Attack("Bite", 30, 2, PokemonType.NORMAL)
        ],
        weakness=PokemonType.FIGHTING, resistance=PokemonType.PSYCHIC,
        retreat_cost=1
    ))

    # STEEL POKEMON
    cards.append(PokemonCard(
        id="metagross", name="Metagross",
        pokemon_type=PokemonType.STEEL, hp=120,
        attacks=[
            Attack("Metal Claw", 30, 1, PokemonType.STEEL),
            Attack("Meteor Mash", 70, 2, PokemonType.STEEL)
        ],
        weakness=PokemonType.FIRE, resistance=PokemonType.FAIRY,
        retreat_cost=3
    ))

    # ENERGY CARDS
    for ptype in PokemonType:
        cards.append(EnergyCard(
            id=f"energy_{ptype.value.lower()}",
            name=f"{ptype.value} Energy",
            energy_type=ptype
        ))

    # TRAINER CARDS
    cards.append(TrainerCard(
        id="potion", name="Potion",
        trainer_type=TrainerType.ITEM,
        effect=TrainerEffect.HEAL_30,
        effect_description="Heal 30 HP from one of your Pokémon"
    ))

    cards.append(TrainerCard(
        id="super_potion", name="Super Potion",
        trainer_type=TrainerType.ITEM,
        effect=TrainerEffect.HEAL_60,
        effect_description="Heal 60 HP from one of your Pokémon"
    ))

    cards.append(TrainerCard(
        id="professor_oak", name="Professor Oak",
        trainer_type=TrainerType.SUPPORTER,
        effect=TrainerEffect.DRAW_3,
        effect_description="Draw 3 cards from your deck"
    ))

    cards.append(TrainerCard(
        id="switch", name="Switch",
        trainer_type=TrainerType.ITEM,
        effect=TrainerEffect.SWITCH,
        effect_description="Switch your active Pokémon with a benched one",
        target_required=True
    ))

    cards.append(TrainerCard(
        id="full_heal", name="Full Heal",
        trainer_type=TrainerType.ITEM,
        effect=TrainerEffect.FULL_HEAL,
        effect_description="Remove all special conditions from your active Pokémon"
    ))

    cards.append(TrainerCard(
        id="energy_retrieval", name="Energy Retrieval",
        trainer_type=TrainerType.ITEM,
        effect=TrainerEffect.ENERGY_RETRIEVAL,
        effect_description="Attach an energy from your discard pile to a Pokémon"
    ))

    return cards


# Global card database
CARD_DATABASE = create_card_database()


def get_card_by_id(card_id: str) -> Optional[object]:
    """Get a card from the database by ID."""
    for card in CARD_DATABASE:
        if card.id == card_id:
            return card
    return None


def build_deck(deck_ids: List[str]) -> list:
    """Build a deck from card IDs with proper error handling."""
    deck = []
    missing_ids = []

    for card_id in deck_ids:
        card = get_card_by_id(card_id)
        if card is None:
            missing_ids.append(card_id)
            continue

        # Create fresh copies using the copy method
        deck.append(card.copy())

    if missing_ids:
        print(f"Warning: Could not find cards: {missing_ids}")

    random.shuffle(deck)
    return deck


def generate_random_deck() -> List[str]:
    """Generate a random valid deck of 30 cards with type matching."""
    pokemon_cards = [c for c in CARD_DATABASE if isinstance(c, PokemonCard)]
    energy_cards = [c for c in CARD_DATABASE if isinstance(c, EnergyCard)]
    trainer_cards = [c for c in CARD_DATABASE if isinstance(c, TrainerCard)]

    # Select 8-10 Pokemon
    selected_pokemon = random.sample(pokemon_cards, min(8, len(pokemon_cards)))
    # Add 2 more random pokemon
    selected_pokemon.extend(random.choices(pokemon_cards, k=2))

    # Get types of selected pokemon
    pokemon_types = {p.pokemon_type for p in selected_pokemon}

    deck_ids = [p.id for p in selected_pokemon]

    # Add energy matching pokemon types (with some variety)
    matching_energies = [e.id for e in energy_cards if e.energy_type in pokemon_types]
    other_energies = [e.id for e in energy_cards if e.energy_type not in pokemon_types]

    # 70% matching energy, 30% other
    energy_selection = random.choices(matching_energies, k=9) + random.choices(other_energies, k=4)
    deck_ids.extend(energy_selection)

    # Add trainers
    deck_ids.extend(random.choices([t.id for t in trainer_cards], k=7))

    return deck_ids
