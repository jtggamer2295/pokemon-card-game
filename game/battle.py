
"""Battle system and attack resolution."""

import random
from typing import List
from game.cards import PokemonCard, PokemonType, EnergyCard, TrainerEffect
from game.player import Player


class BattleLog:
    """Thread-safe battle log with message history."""

    def __init__(self):
        self.messages: List[str] = []
        self.damage_log: List[dict] = []

    def add(self, msg: str):
        self.messages.append(msg)
        print(f"BATTLE: {msg}")

    def add_damage(self, attacker: str, defender: str, attack_name: str, 
                   base_damage: int, final_damage: int, modifiers: dict):
        entry = {
            "attacker": attacker,
            "defender": defender,
            "attack": attack_name,
            "base": base_damage,
            "final": final_damage,
            "modifiers": modifiers
        }
        self.damage_log.append(entry)

    def get_recent(self, n: int = 5) -> List[str]:
        return self.messages[-n:]

    def get_last_damage(self) -> dict:
        return self.damage_log[-1] if self.damage_log else {}


def resolve_attack(attacker: Player, defender: Player,
                   attack_index: int, log: BattleLog) -> dict:
    """Resolve an attack with full damage calculation."""
    atk_pokemon = attacker.active_pokemon
    def_pokemon = defender.active_pokemon

    if atk_pokemon is None or def_pokemon is None:
        return {"success": False, "reason": "No active Pokemon"}

    if not atk_pokemon.can_attack(attack_index):
        return {"success": False, "reason": "Cannot use this attack"}

    attack = atk_pokemon.attacks[attack_index]

    # Calculate damage using the PokemonCard method
    final_damage = atk_pokemon.get_attack_damage(attack_index, def_pokemon)

    # Track modifiers for logging
    modifiers = {
        "stab": attack.energy_type == atk_pokemon.pokemon_type,
        "effectiveness": get_type_effectiveness(attack.energy_type, def_pokemon.pokemon_type),
        "resistance": def_pokemon.resistance == attack.energy_type,
    }

    # Apply damage
    def_pokemon.current_hp -= final_damage

    result = {
        "success": True,
        "attack_name": attack.name,
        "base_damage": attack.damage,
        "final_damage": final_damage,
        "modifiers": modifiers,
        "target_knocked_out": def_pokemon.is_knocked_out()
    }

    log.add_damage(atk_pokemon.name, def_pokemon.name, attack.name,
                   attack.damage, final_damage, modifiers)

    # Build log message
    log_msg = f"{atk_pokemon.name} used {attack.name}!"
    if modifiers["stab"]:
        log_msg += " (+STAB)"

    effectiveness = modifiers["effectiveness"]
    if effectiveness > 1.0:
        log_msg += " It's super effective!"
    elif effectiveness < 1.0 and effectiveness > 0:
        log_msg += " It's not very effective..."
    elif effectiveness == 0:
        log_msg += " It had no effect!"

    if modifiers["resistance"]:
        log_msg += " (Resisted)"

    log_msg += f" [{final_damage} dmg]"
    log.add(log_msg)

    # Apply status effect
    if attack.effect and random.random() < attack.effect_chance and not def_pokemon.is_knocked_out():
        def_pokemon.status = attack.effect
        log.add(f"{def_pokemon.name} is now {attack.effect}!")

    # Process status damage AFTER attack damage
    _apply_status_damage(def_pokemon, log)

    # Check for KO after status damage
    if def_pokemon.is_knocked_out():
        log.add(f"{def_pokemon.name} was knocked out! 🎉")
        attacker.take_prize()
        log.add(f"{attacker.name} took a prize card!")

    return result


def _apply_status_damage(pokemon: PokemonCard, log: BattleLog):
    """Apply damage from status conditions."""
    if pokemon.status == "burned":
        pokemon.current_hp -= 10
        log.add(f"{pokemon.name} took 10 damage from burn!")
    elif pokemon.status == "poisoned":
        pokemon.current_hp -= 10
        log.add(f"{pokemon.name} took 10 damage from poison!")


def apply_trainer_effect(player: Player, trainer, log: BattleLog) -> str:
    """Apply trainer card effects using enum-based dispatch."""
    effect = trainer.effect

    if effect == TrainerEffect.HEAL_30:
        return _apply_heal(player, 30, log)
    elif effect == TrainerEffect.HEAL_60:
        return _apply_heal(player, 60, log)
    elif effect == TrainerEffect.DRAW_3:
        return _apply_draw(player, 3, log)
    elif effect == TrainerEffect.FULL_HEAL:
        return _apply_full_heal(player, log)
    elif effect == TrainerEffect.ENERGY_RETRIEVAL:
        return _apply_energy_retrieval(player, log)
    elif effect == TrainerEffect.SWITCH:
        return "Switch: Select a benched Pokemon"
    else:
        return f"Unknown effect: {effect}"


def _apply_heal(player: Player, amount: int, log: BattleLog) -> str:
    """Apply healing to active Pokemon."""
    if player.active_pokemon is None:
        return "No active Pokemon to heal"

    old_hp = player.active_pokemon.current_hp
    player.active_pokemon.current_hp = min(
        player.active_pokemon.hp,
        player.active_pokemon.current_hp + amount
    )
    healed = player.active_pokemon.current_hp - old_hp
    log.add(f"Healed {player.active_pokemon.name} for {healed} HP! 💚")
    return f"Heal {amount}"


def _apply_draw(player: Player, count: int, log: BattleLog) -> str:
    """Draw cards from deck."""
    drawn = 0
    for _ in range(count):
        if player.draw_card():
            drawn += 1
    log.add(f"{player.name} drew {drawn} cards! 📚")
    return f"Draw {count}"


def _apply_full_heal(player: Player, log: BattleLog) -> str:
    """Remove all special conditions."""
    if player.active_pokemon is None:
        return "No active Pokemon"

    old_status = player.active_pokemon.status
    player.active_pokemon.status = None
    if old_status:
        log.add(f"{player.active_pokemon.name} was fully healed of conditions! ✨")
        return f"Full Heal (removed {old_status})"
    return "Full Heal (no conditions)"


def _apply_energy_retrieval(player: Player, log: BattleLog) -> str:
    """Retrieve energy from discard pile."""
    energy_cards = [c for c in player.discard_pile if isinstance(c, EnergyCard)]
    if not energy_cards:
        return "No energy in discard pile"

    if player.active_pokemon is None:
        return "No active Pokemon"

    card = energy_cards[0]
    player.discard_pile.remove(card)
    player.active_pokemon.attached_energies.append(card.energy_type)
    log.add(f"Attached {card.name} from discard! ⚡")
    return f"Energy Retrieval: {card.name}"


def get_type_effectiveness(attack_type: PokemonType, defend_type: PokemonType) -> float:
    """Get type effectiveness multiplier."""
    from game.cards import get_type_effectiveness as _gte
    return _gte(attack_type, defend_type)
