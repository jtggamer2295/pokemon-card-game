
"""Player class and game state management."""

from typing import List, Optional
from game.cards import (
    PokemonCard, EnergyCard, TrainerCard, CardType,
    TrainerType, TrainerEffect, build_deck, generate_random_deck
)


class Player:
    """Represents a player in the game."""

    def __init__(self, name: str, deck_ids: Optional[List[str]] = None):
        self.name = name
        self.deck_ids = deck_ids if deck_ids else generate_random_deck()
        self.deck = build_deck(self.deck_ids)
        self.hand: List = []
        self.bench: List[PokemonCard] = []
        self.active_pokemon: Optional[PokemonCard] = None
        self.discard_pile: List = []
        self.prize_cards: List = []
        self.has_played_energy = False
        self.has_played_supporter = False
        self.mulligan_count = 0

    def draw_card(self) -> bool:
        """Draw a card from deck. Returns True if successful."""
        if not self.deck:
            return False
        card = self.deck.pop()
        self.hand.append(card)
        return True

    def draw_hand(self, n: int = 7):
        """Draw initial hand."""
        for _ in range(n):
            if not self.draw_card():
                break

    def has_pokemon_in_hand(self) -> bool:
        """Check if hand contains at least one Pokemon."""
        return any(isinstance(c, PokemonCard) for c in self.hand)

    def setup_prizes(self, n: int = 3):
        """Set up prize cards from top of deck."""
        for _ in range(min(n, len(self.deck))):
            if self.deck:
                self.prize_cards.append(self.deck.pop())

    def play_pokemon_to_bench(self, pokemon: PokemonCard) -> bool:
        """Play a Pokemon from hand to bench."""
        if len(self.bench) >= 5:
            return False
        if pokemon not in self.hand:
            return False
        self.hand.remove(pokemon)
        self.bench.append(pokemon)
        return True

    def set_active_pokemon(self, pokemon: PokemonCard):
        """Set a Pokemon from hand as the active Pokemon."""
        if pokemon not in self.hand:
            raise ValueError("Pokemon not in hand")
        self.hand.remove(pokemon)
        self.active_pokemon = pokemon
        pokemon.is_active = True

    def attach_energy(self, energy: EnergyCard, target: PokemonCard) -> bool:
        """Attach an energy card to a Pokemon."""
        if self.has_played_energy:
            return False
        if energy not in self.hand:
            return False
        if target not in self.bench and target != self.active_pokemon:
            return False

        self.hand.remove(energy)
        target.attached_energies.append(energy.energy_type)
        self.has_played_energy = True
        return True

    def play_trainer(self, trainer: TrainerCard) -> tuple:
        """Play a trainer card. Returns (success: bool, message: str)."""
        if trainer not in self.hand:
            return False, "Card not in hand"

        if trainer.trainer_type == TrainerType.SUPPORTER and self.has_played_supporter:
            return False, "Already played a supporter this turn"

        self.hand.remove(trainer)
        self.discard_pile.append(trainer)

        if trainer.trainer_type == TrainerType.SUPPORTER:
            self.has_played_supporter = True

        return True, trainer.effect

    def retreat_active(self, bench_index: int) -> bool:
        """Retreat active Pokemon and promote a benched one."""
        if self.active_pokemon is None:
            return False
        if bench_index >= len(self.bench):
            return False

        # Check status conditions that prevent retreat
        if self.active_pokemon.status in ["paralyzed", "asleep"]:
            return False

        # Check retreat cost
        if len(self.active_pokemon.attached_energies) < self.active_pokemon.retreat_cost:
            return False

        # Pay retreat cost (discard energies)
        energies_to_discard = self.active_pokemon.attached_energies[:self.active_pokemon.retreat_cost]
        self.active_pokemon.attached_energies = self.active_pokemon.attached_energies[self.active_pokemon.retreat_cost:]

        # Move old active to bench (if not KO'd)
        old_active = self.active_pokemon
        old_active.is_active = False

        new_active = self.bench.pop(bench_index)
        new_active.is_active = True
        self.active_pokemon = new_active

        if not old_active.is_knocked_out():
            self.bench.append(old_active)
        else:
            self.discard_pile.append(old_active)

        return True

    def promote_benched_pokemon(self) -> bool:
        """Move a benched Pokemon to active after KO."""
        if not self.bench:
            return False

        new_active = self.bench.pop(0)
        new_active.is_active = True
        self.active_pokemon = new_active
        return True

    def take_prize(self) -> bool:
        """Take a prize card. Returns True if successful."""
        if self.prize_cards:
            card = self.prize_cards.pop()
            self.hand.append(card)
            return True
        return False

    def clean_up_knocked_out(self):
        """Remove KO'd Pokemon and move to discard."""
        if self.active_pokemon and self.active_pokemon.is_knocked_out():
            self.active_pokemon.is_active = False
            self.discard_pile.append(self.active_pokemon)
            self.active_pokemon = None

        ko_bench = [p for p in self.bench if p.is_knocked_out()]
        for p in ko_bench:
            self.bench.remove(p)
            self.discard_pile.append(p)

    def end_turn_cleanup(self):
        """Reset per-turn flags."""
        self.has_played_energy = False
        self.has_played_supporter = False

    def is_eliminated(self) -> bool:
        """Check if player is eliminated (no active and no bench)."""
        return self.active_pokemon is None and len(self.bench) == 0

    def can_draw_at_turn_start(self) -> bool:
        """Check if player can draw at the start of their turn."""
        return len(self.deck) > 0

    def get_playable_cards(self) -> dict:
        """Get cards that can be played from hand."""
        playable = {
            'pokemon': [],
            'energy': [],
            'trainers': []
        }

        for card in self.hand:
            if isinstance(card, PokemonCard):
                if self.active_pokemon is None:
                    playable['pokemon'].append(card)
                elif len(self.bench) < 5:
                    playable['pokemon'].append(card)
            elif isinstance(card, EnergyCard):
                if not self.has_played_energy:
                    targets = []
                    if self.active_pokemon:
                        targets.append(self.active_pokemon)
                    targets.extend(self.bench)
                    if targets:
                        playable['energy'].append((card, targets))
            elif isinstance(card, TrainerCard):
                if card.trainer_type != TrainerType.SUPPORTER or not self.has_played_supporter:
                    playable['trainers'].append(card)

        return playable
