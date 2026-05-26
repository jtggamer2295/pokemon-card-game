
"""AI agents with proper turn handling."""

import random
try:
    import numpy as np
except ImportError:
    np = None
from typing import Optional, List
from game.player import Player
from game.cards import PokemonCard, EnergyCard, TrainerCard, CardType, get_type_effectiveness
from game.engine import GameEngine, GamePhase


class BaseAgent:
    """Base class for all AI agents with common utilities."""

    def __init__(self, player: Player, engine: GameEngine):
        self.player = player
        self.engine = engine

    def take_turn(self):
        """Execute a full turn. Must be implemented by subclasses."""
        raise NotImplementedError

    def _can_act(self) -> bool:
        """Check if agent can still act this turn."""
        return (self.engine.phase != GamePhase.GAME_OVER and 
                self.engine.current_player == self.player and
                not self.engine.is_game_over())

    def _play_pokemon_to_bench(self):
        """Play Pokemon from hand to bench."""
        pokemon_in_hand = [c for c in self.player.hand if isinstance(c, PokemonCard)]
        for card in sorted(pokemon_in_hand, key=lambda p: p.hp, reverse=True):
            if len(self.player.bench) < 5:
                self.player.play_pokemon_to_bench(card)

    def _get_best_attack(self) -> int:
        """Find the best attack index. Returns -1 if no attack possible."""
        if not self.player.active_pokemon:
            return -1

        best_idx = -1
        best_score = -1
        opponent = self.engine.opponent

        for i, atk in enumerate(self.player.active_pokemon.attacks):
            if not self.player.active_pokemon.can_attack(i):
                continue

            score = atk.damage
            if opponent.active_pokemon:
                # Calculate actual damage
                damage = self.player.active_pokemon.get_attack_damage(i, opponent.active_pokemon)
                score = damage

                # Big bonus for KO
                if damage >= opponent.active_pokemon.current_hp:
                    score += 100

                # Bonus for status effects
                if atk.effect and opponent.active_pokemon.status is None:
                    score += 20

            if score > best_score:
                best_score = score
                best_idx = i

        return best_idx


class RandomAgent(BaseAgent):
    """Simple random AI for baseline/testing."""

    def take_turn(self):
        """Take a random turn with proper phase handling."""
        if not self._can_act():
            return

        # Draw phase
        if self.engine.phase == GamePhase.DRAW:
            self.engine.draw_phase()

        if not self._can_act():
            return

        # Main phase
        if self.engine.phase == GamePhase.MAIN:
            # Play pokemon to bench
            self._play_pokemon_to_bench()

            # Attach energy randomly
            if not self.player.has_played_energy:
                energies = [c for c in self.player.hand if isinstance(c, EnergyCard)]
                targets = []
                if self.player.active_pokemon:
                    targets.append(self.player.active_pokemon)
                targets.extend(self.player.bench)

                if energies and targets:
                    target = random.choice(targets)
                    self.player.attach_energy(energies[0], target)

            # Play trainer cards randomly
            for card in list(self.player.hand):
                if isinstance(card, TrainerCard):
                    success, _ = self.engine.play_trainer(card)
                    if not success:
                        break  # Stop if supporter played

            # Attack if possible
            attack_idx = self._get_best_attack()
            if attack_idx >= 0:
                self.engine.attack(attack_idx)
                return  # Attack ends turn

        # End turn if we haven't attacked
        if self._can_act():
            self.engine.end_turn()


class HeuristicAgent(BaseAgent):
    """Rule-based AI with smart heuristics."""

    def take_turn(self):
        """Take an optimized turn."""
        if not self._can_act():
            return

        # Draw phase
        if self.engine.phase == GamePhase.DRAW:
            self.engine.draw_phase()

        if not self._can_act():
            return

        # Main phase
        if self.engine.phase == GamePhase.MAIN:
            self._play_pokemon_to_bench()
            self._attach_energy_smart()
            self._play_trainers()

            if not self._can_act():
                return

            attack_idx = self._get_best_attack()
            if attack_idx >= 0:
                self.engine.attack(attack_idx)
                return  # Attack ends turn

        # End turn if we haven't attacked
        if self._can_act():
            self.engine.end_turn()

    def _attach_energy_smart(self):
        """Attach energy to the Pokemon that needs it most."""
        if self.player.has_played_energy:
            return

        energies = [c for c in self.player.hand if isinstance(c, EnergyCard)]
        if not energies:
            return

        best_target = None
        best_energy = None
        best_score = -1

        candidates = []
        if self.player.active_pokemon:
            candidates.append(self.player.active_pokemon)
        candidates.extend(self.player.bench)

        for energy in energies:
            for pokemon in candidates:
                score = self._energy_attachment_score(pokemon, energy)
                if score > best_score:
                    best_score = score
                    best_energy = energy
                    best_target = pokemon

        if best_energy and best_target:
            self.player.attach_energy(best_energy, best_target)

    def _energy_attachment_score(self, pokemon: PokemonCard, energy: EnergyCard) -> float:
        """Score how valuable attaching this energy would be."""
        score = 0

        # Bonus for active pokemon
        if pokemon == self.player.active_pokemon:
            score += 5

        # Bonus if it enables an attack
        for atk in pokemon.attacks:
            if energy.energy_type == atk.energy_type:
                matching = sum(1 for e in pokemon.attached_energies if e == atk.energy_type)
                if matching == atk.energy_cost - 1:
                    score += 15  # This attachment enables the attack!
                elif matching < atk.energy_cost:
                    score += 3

        # Bonus for matching type
        if energy.energy_type == pokemon.pokemon_type:
            score += 2

        return score

    def _play_trainers(self):
        """Play trainer cards intelligently."""
        for card in list(self.player.hand):
            if isinstance(card, TrainerCard):
                # Only play heal if active pokemon is significantly damaged
                if card.effect and "HEAL" in str(card.effect):
                    if (self.player.active_pokemon and 
                        self.player.active_pokemon.current_hp < self.player.active_pokemon.hp * 0.6):
                        self.engine.play_trainer(card)
                else:
                    self.engine.play_trainer(card)


class MLAgent(BaseAgent):
    """ML-powered AI that uses the battle predictor for decisions."""

    def __init__(self, player: Player, engine: GameEngine,
                 battle_predictor=None):
        super().__init__(player, engine)
        self.predictor = battle_predictor

    def take_turn(self):
        """Take a turn using ML evaluation."""
        if not self._can_act():
            return

        # Draw phase
        if self.engine.phase == GamePhase.DRAW:
            self.engine.draw_phase()

        if not self._can_act():
            return

        # Main phase
        if self.engine.phase == GamePhase.MAIN:
            self._play_pokemon_to_bench()
            self._attach_energy_ml()
            self._play_trainers_ml()

            if not self._can_act():
                return

            # Decide whether to attack
            attack_idx = self._choose_best_attack()
            if attack_idx >= 0 and self._should_attack(attack_idx):
                self.engine.attack(attack_idx)
                return

        # End turn if we haven't attacked
        if self._can_act():
            self.engine.end_turn()

    def _evaluate_state(self) -> float:
        """Evaluate current game state using ML predictor or heuristic fallback."""
        if self.predictor and getattr(self.predictor, 'is_trained', False):
            try:
                state = self.engine.get_game_state()
                prob = self.predictor.predict_win_probability(state)
                # Adjust based on which player we are
                if self.engine.current_player_index == 1:
                    prob = 1 - prob
                return prob
            except Exception:
                pass  # Fall through to heuristic

        return self._heuristic_evaluation()

    def _heuristic_evaluation(self) -> float:
        """Simple heuristic state evaluation."""
        score = 0.5

        if self.player.active_pokemon:
            hp_ratio = self.player.active_pokemon.current_hp / max(self.player.active_pokemon.hp, 1)
            score += hp_ratio * 0.15
            score += len(self.player.active_pokemon.attached_energies) * 0.02

        opponent = self.engine.opponent
        if opponent.active_pokemon:
            opp_hp_ratio = opponent.active_pokemon.current_hp / max(opponent.active_pokemon.hp, 1)
            score -= opp_hp_ratio * 0.15

        score += len(self.player.bench) * 0.03
        score -= len(opponent.bench) * 0.03
        score += (3 - len(self.player.prize_cards)) * 0.08
        score -= (3 - len(opponent.prize_cards)) * 0.05

        return max(0.0, min(1.0, score))

    def _attach_energy_ml(self):
        """Use ML to decide energy attachment."""
        if self.player.has_played_energy:
            return

        energies = [c for c in self.player.hand if isinstance(c, EnergyCard)]
        if not energies:
            return

        candidates = []
        if self.player.active_pokemon:
            candidates.append(self.player.active_pokemon)
        candidates.extend(self.player.bench)

        if not candidates:
            return

        best_energy = None
        best_target = None
        best_score = -1

        for energy in energies:
            for target in candidates:
                # Simulate attachment
                target.attached_energies.append(energy.energy_type)
                score = self._evaluate_state()
                target.attached_energies.pop()

                if score > best_score:
                    best_score = score
                    best_energy = energy
                    best_target = target

        if best_energy and best_target:
            self.player.attach_energy(best_energy, best_target)

    def _play_trainers_ml(self):
        """Play trainers based on ML evaluation."""
        for card in list(self.player.hand):
            if isinstance(card, TrainerCard):
                score_before = self._evaluate_state()

                # Simulate playing the card
                if card.effect == "HEAL_30" or card.effect == "HEAL_60":
                    if self.player.active_pokemon:
                        heal_amount = 30 if "30" in str(card.effect) else 60
                        hp_before = self.player.active_pokemon.current_hp
                        self.player.active_pokemon.current_hp = min(
                            self.player.active_pokemon.hp,
                            hp_before + heal_amount
                        )
                        score_after = self._evaluate_state()
                        self.player.active_pokemon.current_hp = hp_before
                    else:
                        continue
                else:
                    score_after = score_before + 0.05  # Rough estimate for draw/switch

                if score_after > score_before:
                    self.engine.play_trainer(card)

    def _should_attack(self, attack_idx: int) -> bool:
        """Decide whether attacking is the best move."""
        opponent = self.engine.opponent

        # Always attack if we can KO
        if opponent.active_pokemon and self.player.active_pokemon:
            damage = self.player.active_pokemon.get_attack_damage(
                attack_idx, opponent.active_pokemon
            )
            if damage >= opponent.active_pokemon.current_hp:
                return True

        # Use ML evaluation
        current_score = self._evaluate_state()
        return current_score > 0.25  # Attack if we're doing okay

    def _choose_best_attack(self) -> int:
        """Choose the best attack using ML evaluation."""
        return self._get_best_attack()
