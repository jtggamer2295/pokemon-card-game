
"""Core game engine with state management."""

from typing import Optional, Tuple
from enum import Enum, auto
from game.player import Player
from game.battle import BattleLog, resolve_attack, apply_trainer_effect
from game.cards import PokemonCard, EnergyCard, TrainerCard, CardType


class GamePhase(Enum):
    """Game phases as serializable strings."""
    DRAW = "draw"
    MAIN = "main"
    ATTACK = "attack"
    END = "end"
    GAME_OVER = "game_over"


class GameEngine:
    """Main game engine managing turns and state."""

    def __init__(self, player1: Player, player2: Player):
        self.players = [player1, player2]
        self.current_player_index = 0
        self.phase = GamePhase.DRAW
        self.turn_count = 0
        self.log = BattleLog()
        self.winner: Optional[Player] = None
        self.max_turns = 100  # Prevent infinite games

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_index]

    @property
    def opponent(self) -> Player:
        return self.players[1 - self.current_player_index]

    def start_game(self):
        """Initialize and start the game with mulligan handling."""
        self.log.add("=== Pokémon Card Game Started! ===")

        for player in self.players:
            self._setup_player(player)

        self.phase = GamePhase.DRAW
        self.turn_count = 1
        self.log.add(f"--- {self.current_player.name}'s Turn ---")

    def _setup_player(self, player: Player):
        """Setup a player with mulligan handling."""
        max_mulligans = 5
        mulligan_count = 0

        # Draw initial hand and handle mulligans
        player.draw_hand(7)

        while not player.has_pokemon_in_hand() and mulligan_count < max_mulligans:
            # Return hand to deck, shuffle, and redraw
            player.deck.extend(player.hand)
            player.hand = []
            random.shuffle(player.deck)
            player.draw_hand(7)
            mulligan_count += 1

        player.mulligan_count = mulligan_count
        if mulligan_count > 0:
            self.log.add(f"{player.name} took {mulligan_count} mulligans")

        # If still no Pokemon after max mulligans, force add one
        if not player.has_pokemon_in_hand():
            self.log.add(f"{player.name} forced to add a basic Pokemon")
            from game.cards import CARD_DATABASE
            basic = next((c for c in CARD_DATABASE if isinstance(c, PokemonCard)), None)
            if basic:
                player.hand.append(basic.copy())

        player.setup_prizes(3)

        # Auto-set first pokemon as active
        for card in player.hand:
            if isinstance(card, PokemonCard) and player.active_pokemon is None:
                player.set_active_pokemon(card)
                break

    def draw_phase(self):
        """Player draws a card at start of turn."""
        if self.phase != GamePhase.DRAW:
            return

        # Check for deck out (lose if can't draw)
        if not self.current_player.can_draw_at_turn_start():
            self.log.add(f"{self.current_player.name} cannot draw - deck out!")
            self.winner = self.opponent
            self.phase = GamePhase.GAME_OVER
            return

        card = self.current_player.draw_card()
        if card:
            self.log.add(f"{self.current_player.name} drew a card.")

        self.phase = GamePhase.MAIN

    def play_pokemon(self, pokemon: PokemonCard, to_bench: bool = True) -> bool:
        """Play a Pokemon card."""
        if self.phase != GamePhase.MAIN:
            return False
        if self.current_player_index != 0:  # Only human player for now
            return False

        if to_bench:
            return self.current_player.play_pokemon_to_bench(pokemon)
        else:
            # Set as active (only if no active)
            if self.current_player.active_pokemon is None:
                self.current_player.set_active_pokemon(pokemon)
                return True
        return False

    def attach_energy(self, energy: EnergyCard, target: PokemonCard) -> bool:
        """Attach energy to a Pokemon."""
        if self.phase != GamePhase.MAIN:
            return False
        if self.current_player_index != 0:
            return False
        return self.current_player.attach_energy(energy, target)

    def play_trainer(self, trainer: TrainerCard) -> Tuple[bool, str]:
        """Play a trainer card."""
        if self.phase != GamePhase.MAIN:
            return False, "Not in main phase"
        if self.current_player_index != 0:
            return False, "Not your turn"

        success, result = self.current_player.play_trainer(trainer)
        if success:
            effect_result = apply_trainer_effect(self.current_player, trainer, self.log)
            return True, effect_result
        return False, result

    def retreat(self, bench_index: int) -> bool:
        """Retreat active Pokemon."""
        if self.phase != GamePhase.MAIN:
            return False
        if self.current_player_index != 0:
            return False
        return self.current_player.retreat_active(bench_index)

    def attack(self, attack_index: int) -> dict:
        """Execute an attack."""
        if self.phase not in (GamePhase.MAIN, GamePhase.ATTACK):
            return {"success": False, "reason": "Not in attack phase"}
        if self.current_player_index != 0:
            return {"success": False, "reason": "Not your turn"}

        result = resolve_attack(
            self.current_player, self.opponent, attack_index, self.log
        )

        if not result.get("success"):
            return result

        # Clean up knocked out pokemon
        self.opponent.clean_up_knocked_out()

        # Check if opponent needs to promote
        if self.opponent.active_pokemon is None:
            if not self.opponent.promote_benched_pokemon():
                self.winner = self.current_player
                self.phase = GamePhase.GAME_OVER
                self.log.add(f"🏆 {self.current_player.name} wins!")
                return result

        # Check prize victory
        if len(self.current_player.prize_cards) == 0:
            self.winner = self.current_player
            self.phase = GamePhase.GAME_OVER
            self.log.add(f"🏆 {self.current_player.name} collected all prizes!")
            return result

        # Check max turns
        if self.turn_count >= self.max_turns:
            self._resolve_by_hp()
            return result

        self.end_turn()
        return result

    def _resolve_by_hp(self):
        """Resolve game by total HP if max turns reached."""
        p1_hp = sum(p.current_hp for p in self.players[0].bench)
        p1_hp += self.players[0].active_pokemon.current_hp if self.players[0].active_pokemon else 0
        p2_hp = sum(p.current_hp for p in self.players[1].bench)
        p2_hp += self.players[1].active_pokemon.current_hp if self.players[1].active_pokemon else 0

        if p1_hp > p2_hp:
            self.winner = self.players[0]
        elif p2_hp > p1_hp:
            self.winner = self.players[1]
        else:
            self.winner = None  # Draw

        self.phase = GamePhase.GAME_OVER
        self.log.add(f"Game ended by turn limit. Winner: {self.winner.name if self.winner else 'Draw'}")

    def end_turn(self):
        """End the current player's turn."""
        if self.phase == GamePhase.GAME_OVER:
            return

        self.current_player.end_turn_cleanup()

        # Switch turns
        self.current_player_index = 1 - self.current_player_index
        self.turn_count += 1
        self.phase = GamePhase.DRAW

        # Reset paralysis for new active player (at end of their turn)
        if self.current_player.active_pokemon and \
           self.current_player.active_pokemon.status == "paralyzed":
            self.current_player.active_pokemon.status = None
            self.log.add(f"{self.current_player.active_pokemon.name} is no longer paralyzed!")

        self.log.add(f"--- {self.current_player.name}'s Turn ---")

    def get_game_state(self) -> dict:
        """Return serializable game state for ML/AI."""
        cp = self.current_player
        op = self.opponent

        def serialize_pokemon(p: Optional[PokemonCard]) -> dict:
            if p is None:
                return None
            return {
                "name": p.name,
                "type": p.pokemon_type.value,
                "hp": p.current_hp,
                "max_hp": p.hp,
                "hp_ratio": p.current_hp / max(p.hp, 1),
                "energy_count": len(p.attached_energies),
                "energy_types": [e.value for e in p.attached_energies],
                "status": p.status,
                "can_attack": [p.can_attack(i) for i in range(len(p.attacks))],
                "attack_names": [a.name for a in p.attacks],
                "attack_damages": [a.damage for a in p.attacks],
            }

        def serialize_bench(bench: list) -> list:
            return [serialize_pokemon(p) for p in bench]

        return {
            "turn": self.turn_count,
            "phase": self.phase.value,  # Serialize as string
            "current_player": {
                "name": cp.name,
                "hand_size": len(cp.hand),
                "deck_size": len(cp.deck),
                "prizes_remaining": len(cp.prize_cards),
                "bench_size": len(cp.bench),
                "bench": serialize_bench(cp.bench),
                "active": serialize_pokemon(cp.active_pokemon),
                "playable_cards": {
                    k: len(v) if not isinstance(v, list) or not v or not isinstance(v[0], tuple) 
                    else len(v) 
                    for k, v in cp.get_playable_cards().items()
                }
            },
            "opponent": {
                "name": op.name,
                "hand_size": len(op.hand),
                "deck_size": len(op.deck),
                "prizes_remaining": len(op.prize_cards),
                "bench_size": len(op.bench),
                "bench": serialize_bench(op.bench),
                "active": serialize_pokemon(op.active_pokemon),
            }
        }

    def is_game_over(self) -> bool:
        return self.phase == GamePhase.GAME_OVER or self.winner is not None
