
"""Pygame GUI with proper state management and button handling."""

import pygame
import sys
from typing import Optional, List, Tuple
from game.engine import GameEngine, GamePhase
from game.player import Player
from game.cards import (
    PokemonCard, EnergyCard, TrainerCard, CardType,
    PokemonType, get_type_effectiveness
)
from ml.ai_agent import HeuristicAgent, MLAgent, BaseAgent
from ml.battle_predictor import BattlePredictor


# ============ COLORS ============
TYPE_COLORS = {
    PokemonType.FIRE: (240, 80, 50),
    PokemonType.WATER: (50, 130, 255),
    PokemonType.GRASS: (50, 200, 80),
    PokemonType.ELECTRIC: (255, 210, 50),
    PokemonType.PSYCHIC: (200, 80, 200),
    PokemonType.FIGHTING: (180, 100, 50),
    PokemonType.DARK: (80, 60, 100),
    PokemonType.STEEL: (160, 170, 180),
    PokemonType.FAIRY: (255, 160, 200),
    PokemonType.NORMAL: (180, 180, 170),
    PokemonType.DRAGON: (100, 50, 200),
}

BG_COLOR = (30, 35, 50)
CARD_BG = (250, 245, 230)
TEXT_COLOR = (20, 20, 20)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
RED = (220, 50, 50)
GREEN = (50, 200, 80)
HOVER_COLOR = (255, 255, 200)


class CardRenderer:
    """Render Pokémon cards on screen with instance-based sizing."""

    DEFAULT_W = 120
    DEFAULT_H = 170

    def __init__(self, width: int = DEFAULT_W, height: int = DEFAULT_H):
        self.width = width
        self.height = height

    def draw_card(self, surface, card, x, y, face_up=True, selected=False,
                  hover=False, font_scale=1.0):
        w, h = self.width, self.height
        rect = pygame.Rect(x, y, w, h)

        if not face_up:
            # Card back
            pygame.draw.rect(surface, (40, 60, 120), rect, border_radius=8)
            pygame.draw.rect(surface, (60, 90, 160), rect, 2, border_radius=8)
            cx, cy = x + w // 2, y + h // 2
            pygame.draw.circle(surface, WHITE, (cx, cy), 20, 2)
            pygame.draw.line(surface, WHITE, (cx - 20, cy), (cx + 20, cy), 2)
            return rect

        # Card face
        bg_color = HOVER_COLOR if hover else CARD_BG
        pygame.draw.rect(surface, bg_color, rect, border_radius=8)

        if selected:
            pygame.draw.rect(surface, GOLD, rect, 3, border_radius=8)
        else:
            pygame.draw.rect(surface, (100, 100, 100), rect, 1, border_radius=8)

        font_small = pygame.font.SysFont("Arial", int(10 * font_scale))
        font_med = pygame.font.SysFont("Arial", int(12 * font_scale))
        font_bold = pygame.font.SysFont("Arial", int(11 * font_scale), bold=True)

        if isinstance(card, PokemonCard):
            self._draw_pokemon_card(surface, card, x, y, w, h, 
                                   font_small, font_med, font_bold)
        elif isinstance(card, EnergyCard):
            self._draw_energy_card(surface, card, x, y, w, h, font_med)
        elif isinstance(card, TrainerCard):
            self._draw_trainer_card(surface, card, x, y, w, h, 
                                   font_small, font_med, font_bold)

        return rect

    def _draw_pokemon_card(self, surface, card, x, y, w, h, 
                          font_small, font_med, font_bold):
        type_color = TYPE_COLORS.get(card.pokemon_type, (150, 150, 150))
        header_rect = pygame.Rect(x + 3, y + 3, w - 6, 25)
        pygame.draw.rect(surface, type_color, header_rect, border_radius=5)

        # Name
        name_surf = font_bold.render(card.name[:12], True, WHITE)
        surface.blit(name_surf, (x + 6, y + 6))

        # HP
        hp_text = f"{card.current_hp}/{card.hp}"
        hp_color = GREEN if card.current_hp > card.hp * 0.5 else RED
        hp_surf = font_small.render(hp_text, True, hp_color)
        surface.blit(hp_surf, (x + w - 38, y + 8))

        # HP Bar
        bar_w = w - 12
        bar_h = 6
        bar_x = x + 6
        bar_y = y + 28
        pygame.draw.rect(surface, (100, 100, 100), (bar_x, bar_y, bar_w, bar_h))
        hp_ratio = max(0, card.current_hp / max(card.hp, 1))
        fill_color = GREEN if hp_ratio > 0.5 else GOLD if hp_ratio > 0.25 else RED
        pygame.draw.rect(surface, fill_color,
                        (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

        # Attacks
        attack_y = y + 40
        for i, atk in enumerate(card.attacks):
            cost_text = "●" * atk.energy_cost
            cost_surf = font_small.render(cost_text, True, type_color)
            surface.blit(cost_surf, (x + 6, attack_y))

            atk_surf = font_small.render(atk.name[:15], True, TEXT_COLOR)
            surface.blit(atk_surf, (x + 30, attack_y))

            dmg_surf = font_bold.render(f"{atk.damage}", True, RED)
            surface.blit(dmg_surf, (x + w - 25, attack_y))

            attack_y += 18

        # Type & Status
        type_surf = font_small.render(card.pokemon_type.value, True, type_color)
        surface.blit(type_surf, (x + 6, y + h - 30))

        if card.status:
            status_surf = font_small.render(f"[{card.status}]", True, RED)
            surface.blit(status_surf, (x + 6, y + h - 18))

        # Energy count
        energy_text = f"⚡{len(card.attached_energies)}"
        energy_surf = font_small.render(energy_text, True, (50, 130, 255))
        surface.blit(energy_surf, (x + w - 30, y + h - 18))

    def _draw_energy_card(self, surface, card, x, y, w, h, font_med):
        type_color = TYPE_COLORS.get(card.energy_type, (150, 150, 150))
        cx, cy = x + w // 2, y + h // 2
        pygame.draw.circle(surface, type_color, (cx, cy), 25)
        pygame.draw.circle(surface, WHITE, (cx, cy), 25, 2)

        name_surf = font_med.render(card.energy_type.value, True, WHITE)
        name_rect = name_surf.get_rect(center=(cx, cy))
        surface.blit(name_surf, name_rect)

    def _draw_trainer_card(self, surface, card, x, y, w, h, 
                          font_small, font_med, font_bold):
        header_rect = pygame.Rect(x + 3, y + 3, w - 6, 25)
        pygame.draw.rect(surface, (140, 80, 180), header_rect, border_radius=5)

        name_surf = font_bold.render(card.name[:12], True, WHITE)
        surface.blit(name_surf, (x + 6, y + 6))

        # Effect text (wrapped)
        words = card.effect_description.split()
        lines = []
        current_line = ""
        for word in words:
            test = current_line + " " + word if current_line else word
            if font_small.size(test)[0] < w - 12:
                current_line = test
            else:
                lines.append(current_line)
                current_line = word
        lines.append(current_line)

        text_y = y + 40
        for line in lines[:4]:
            line_surf = font_small.render(line, True, TEXT_COLOR)
            surface.blit(line_surf, (x + 6, text_y))
            text_y += 14


class PokemonCardGame:
    """Main game GUI with improved state management."""

    def __init__(self):
        pygame.init()
        self.WIDTH = 1200
        self.HEIGHT = 800
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption("Pokémon Card Game - ML Edition (Improved)")
        self.clock = pygame.time.Clock()

        # Fonts
        self.font_large = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_med = pygame.font.SysFont("Arial", 18)
        self.font_small = pygame.font.SysFont("Arial", 14)

        # Game state
        self.engine: Optional[GameEngine] = None
        self.ai_agent: Optional[BaseAgent] = None
        self.battle_predictor: Optional[BattlePredictor] = None

        # UI state
        self.selected_hand_card: Optional[int] = None
        self.selected_attack: Optional[int] = None
        self.target_selection = False
        self.message_log: List[str] = []
        self.animation_timer = 0
        self.ai_thinking = False

        # Buttons - use a class to avoid dict clearing issues
        self.buttons = {}
        self.attack_buttons = {}

        # Renderers
        self.card_renderer = CardRenderer()
        self.active_renderer = CardRenderer(180, 250)

    def init_game(self, ai_type: str = "heuristic"):
        """Initialize a new game."""
        try:
            player1 = Player("You")
            player2 = Player("AI Opponent")

            self.engine = GameEngine(player1, player2)
            self.engine.start_game()

            # Initialize battle predictor
            self.battle_predictor = BattlePredictor()

            # Set up AI
            if ai_type == "ml" and self.battle_predictor.is_trained:
                self.ai_agent = MLAgent(player2, self.engine, self.battle_predictor)
            else:
                if ai_type == "ml" and not self.battle_predictor.is_trained:
                    self.add_message("ML model not trained, using heuristic AI")
                self.ai_agent = HeuristicAgent(player2, self.engine)

            self.message_log = [f"Game Started! {player1.name} vs {player2.name}"]
            self.selected_hand_card = None
            self.selected_attack = None
            self.buttons = {}
            self.attack_buttons = {}
            self.ai_thinking = False

        except Exception as e:
            self.add_message(f"Error starting game: {e}")
            print(f"Game initialization error: {e}")

    def add_message(self, msg: str):
        self.message_log.append(msg)
        if len(self.message_log) > 50:
            self.message_log = self.message_log[-50:]

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click(event.pos)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_n:
                    self.init_game()
                elif event.key == pygame.K_ESCAPE:
                    self.selected_hand_card = None
                    self.selected_attack = None
                    self.target_selection = False
                elif event.key == pygame.K_a:
                    # Attack shortcut - only if valid
                    if (self.selected_attack is not None and 
                        self.engine and 
                        self.engine.current_player_index == 0 and
                        self.engine.phase in (GamePhase.MAIN, GamePhase.ATTACK)):
                        self.do_attack(self.selected_attack)
                        self.selected_attack = None

        return True

    def handle_click(self, pos):
        if not self.engine:
            return

        if self.engine.phase == GamePhase.GAME_OVER:
            self.init_game()
            return

        if self.engine.current_player_index != 0:
            return  # Not player's turn

        # Check button clicks
        for btn_name, btn_rect in self.buttons.items():
            if btn_rect.collidepoint(pos):
                self.handle_button(btn_name)
                return

        # Check attack button clicks
        for btn_name, btn_rect in self.attack_buttons.items():
            if btn_rect.collidepoint(pos):
                idx = int(btn_name.split("_")[1])
                self.selected_attack = idx
                return

        # Check hand card clicks
        hand_rects = self._get_hand_rects()
        for i, rect in enumerate(hand_rects):
            if rect.collidepoint(pos) and i < len(self.engine.current_player.hand):
                self.selected_hand_card = i
                self.selected_attack = None
                self.target_selection = False
                return

        # Check target selection (for energy attachment)
        if self.selected_hand_card is not None:
            card = self.engine.current_player.hand[self.selected_hand_card]
            if isinstance(card, EnergyCard):
                active_rect = self._get_active_pokemon_rect()
                if active_rect and active_rect.collidepoint(pos):
                    self.do_attach_energy(self.engine.current_player.active_pokemon)
                    return

                bench_rects = self._get_bench_rects()
                for i, rect in enumerate(bench_rects):
                    if rect.collidepoint(pos) and i < len(self.engine.current_player.bench):
                        self.do_attach_energy(self.engine.current_player.bench[i])
                        return

        self.selected_hand_card = None
        self.selected_attack = None

    def handle_button(self, name):
        if name == "end_turn":
            if self.engine.phase == GamePhase.MAIN:
                self.engine.end_turn()
                self.selected_hand_card = None
                self.selected_attack = None
                self.add_message("--- AI's Turn ---")
                self.ai_thinking = True
        elif name == "draw":
            if self.engine.phase == GamePhase.DRAW:
                self.engine.draw_phase()
                self.add_message("You drew a card!")
        elif name == "play_card" and self.selected_hand_card is not None:
            self.do_play_card()
        elif name.startswith("attack_"):
            idx = int(name.split("_")[1])
            self.do_attack(idx)
        elif name == "new_game":
            self.init_game()

    def do_play_card(self):
        if not self.engine or self.engine.current_player_index != 0:
            return

        player = self.engine.current_player
        card = player.hand[self.selected_hand_card]

        if isinstance(card, PokemonCard):
            if player.active_pokemon is None:
                player.set_active_pokemon(card)
                self.add_message(f"Set {card.name} as active!")
            elif len(player.bench) < 5:
                player.play_pokemon_to_bench(card)
                self.add_message(f"Put {card.name} on the bench!")
            else:
                self.add_message("Bench is full!")
        elif isinstance(card, TrainerCard):
            success, result = self.engine.play_trainer(card)
            if success:
                self.add_message(f"Played {card.name}: {result}")
            else:
                self.add_message(f"Can't play {card.name}: {result}")
        elif isinstance(card, EnergyCard):
            self.add_message("Click a Pokémon to attach energy to!")
            self.target_selection = True
            return

        self.selected_hand_card = None

    def do_attach_energy(self, target):
        if not self.engine or self.engine.current_player_index != 0:
            return

        player = self.engine.current_player
        if self.selected_hand_card is None:
            return

        card = player.hand[self.selected_hand_card]
        if isinstance(card, EnergyCard):
            if player.attach_energy(card, target):
                self.add_message(f"Attached {card.name} to {target.name}!")
            else:
                self.add_message("Can't attach more energy this turn!")
        self.selected_hand_card = None
        self.target_selection = False

    def do_attack(self, attack_index):
        if not self.engine or self.engine.current_player_index != 0:
            return

        result = self.engine.attack(attack_index)
        if result.get("success"):
            self.add_message(
                f"Used {result['attack_name']} for {result['final_damage']} damage!"
            )
            self.selected_attack = None
            self.selected_hand_card = None

            if self.engine.phase == GamePhase.GAME_OVER:
                if self.engine.winner:
                    self.add_message(f"🏆 {self.engine.winner.name} wins!")
            else:
                self.ai_thinking = True
        else:
            self.add_message(f"Can't attack: {result.get('reason', 'unknown')}")

    def do_ai_turn(self):
        """Execute AI turn with error handling."""
        try:
            if self.ai_agent and self.engine and not self.engine.is_game_over():
                self.ai_agent.take_turn()
        except Exception as e:
            self.add_message(f"AI error: {e}")
            print(f"AI turn error: {e}")
        finally:
            self.ai_thinking = False

        if self.engine and self.engine.phase == GamePhase.GAME_OVER and self.engine.winner:
            self.add_message(f"🏆 {self.engine.winner.name} wins!")

    def update(self):
        if not self.engine:
            return

        # AI turn processing
        if self.ai_thinking and self.engine.current_player_index == 1:
            self.animation_timer += 1
            if self.animation_timer > 30:
                self.do_ai_turn()
                self.animation_timer = 0

        # Process messages from battle log
        if self.engine.log.messages:
            for msg in self.engine.log.messages[-3:]:
                if msg not in self.message_log:
                    self.add_message(msg)

    def draw(self):
        self.screen.fill(BG_COLOR)

        if not self.engine:
            self._draw_title_screen()
        else:
            self._draw_game()
            if self.engine.phase == GamePhase.GAME_OVER:
                self._draw_game_over()

        pygame.display.flip()

    def _draw_title_screen(self):
        title = self.font_large.render("Pokémon Card Game", True, GOLD)
        self.screen.blit(title, (self.WIDTH // 2 - title.get_width() // 2, 200))

        sub = self.font_med.render("ML Edition (Improved) - Press N to Start", True, WHITE)
        self.screen.blit(sub, (self.WIDTH // 2 - sub.get_width() // 2, 280))

        features = [
            "🃏 Full Pokémon Card Game with Type System",
            "🤖 AI Opponent (Heuristic / ML-powered)",
            "📊 Battle Outcome Prediction (Gradient Boosting)",
            "🖼️ Card Image Recognition (CNN)",
            "⚡ Real-time Win Probability Display",
            "✅ Fixed: Mulligan handling, STAB bonus, proper turn flow",
        ]
        for i, feat in enumerate(features):
            text = self.font_small.render(feat, True, (180, 180, 200))
            self.screen.blit(text, (self.WIDTH // 2 - 250, 350 + i * 25))

    def _draw_game(self):
        if not self.engine:
            return

        opponent = self.engine.players[1]
        player = self.engine.players[0]

        # OPPONENT AREA
        self._draw_player_info(opponent, 10, 10, is_opponent=True)
        if opponent.active_pokemon:
            self.active_renderer.draw_card(self.screen, opponent.active_pokemon, 450, 60)
        self._draw_bench(opponent.bench, 30, 110, small=True)

        # DIVIDER
        pygame.draw.line(self.screen, (60, 65, 80), (0, 270), (self.WIDTH, 270), 2)

        # PLAYER AREA
        self._draw_player_info(player, 10, 280, is_opponent=False)
        if player.active_pokemon:
            self.active_renderer.draw_card(self.screen, player.active_pokemon, 450, 310)
        self._draw_bench(player.bench, 30, 360)

        # HAND
        self._draw_hand(player.hand, 30, 510)

        # ATTACKS
        if player.active_pokemon and self.engine.current_player_index == 0:
            self._draw_attacks(player.active_pokemon, 750, 310)

        # BUTTONS
        self._draw_buttons()

        # MESSAGE LOG
        self._draw_log()

        # ML PREDICTIONS
        self._draw_ml_panel()

        # TURN INDICATOR
        turn_text = f"Turn {self.engine.turn_count} - "
        if self.engine.current_player_index == 0:
            turn_text += "YOUR TURN"
            turn_color = GREEN
        else:
            turn_text += "AI THINKING..."
            turn_color = GOLD
        turn_surf = self.font_med.render(turn_text, True, turn_color)
        self.screen.blit(turn_surf, (self.WIDTH // 2 - turn_surf.get_width() // 2, 273))

    def _draw_player_info(self, player, x, y, is_opponent=False):
        name_surf = self.font_med.render(player.name, True, WHITE)
        self.screen.blit(name_surf, (x, y))

        deck_text = f"Deck: {len(player.deck)} | Prizes: {len(player.prize_cards)} | Hand: {len(player.hand)}"
        deck_surf = self.font_small.render(deck_text, True, (180, 180, 200))
        self.screen.blit(deck_surf, (x, y + 25))

        # Prize cards
        for i in range(len(player.prize_cards)):
            px = x + i * 25
            py = y + 45
            rect = pygame.Rect(px, py, 20, 28)
            pygame.draw.rect(self.screen, (40, 60, 120), rect, border_radius=3)
            pygame.draw.rect(self.screen, GOLD, rect, 1, border_radius=3)

    def _draw_bench(self, bench, x, y, small=False):
        renderer = CardRenderer(80, 110) if small else self.card_renderer
        for i, pokemon in enumerate(bench):
            bx = x + i * (90 if small else 130)
            renderer.draw_card(self.screen, pokemon, bx, y, face_up=True)
            if not small:
                label = self.font_small.render(f"Bench {i+1}", True, (150, 150, 170))
                self.screen.blit(label, (bx + 20, y - 15))

    def _draw_hand(self, hand, x, y):
        for i, card in enumerate(hand):
            cx = x + i * 135
            is_selected = (i == self.selected_hand_card)

            mx, my = pygame.mouse.get_pos()
            card_rect = pygame.Rect(cx, y, self.card_renderer.width, self.card_renderer.height)
            is_hover = card_rect.collidepoint(mx, my)

            self.card_renderer.draw_card(self.screen, card, cx, y,
                                      face_up=True, selected=is_selected,
                                      hover=is_hover)

    def _draw_attacks(self, pokemon, x, y):
        pygame.draw.rect(self.screen, (40, 45, 60),
                        (x, y, 200, len(pokemon.attacks) * 60 + 30),
                        border_radius=8)
        pygame.draw.rect(self.screen, (80, 90, 110),
                        (x, y, 200, len(pokemon.attacks) * 60 + 30),
                        2, border_radius=8)

        title = self.font_med.render("Attacks", True, GOLD)
        self.screen.blit(title, (x + 10, y + 5))

        # Only clear attack buttons, not all buttons
        self.attack_buttons.clear()

        for i, atk in enumerate(pokemon.attacks):
            btn_y = y + 30 + i * 60
            can_use = pokemon.can_attack(i)
            color = (60, 80, 60) if can_use else (60, 40, 40)
            btn_rect = pygame.Rect(x + 5, btn_y, 190, 50)
            pygame.draw.rect(self.screen, color, btn_rect, border_radius=5)

            if can_use:
                type_color = TYPE_COLORS.get(atk.energy_type, (150, 150, 150))
                name_surf = self.font_med.render(atk.name, True, WHITE)
                self.screen.blit(name_surf, (x + 12, btn_y + 5))

                dmg_surf = self.font_med.render(f"{atk.damage} dmg", True, RED)
                self.screen.blit(dmg_surf, (x + 120, btn_y + 5))

                cost_text = f"Cost: {'●' * atk.energy_cost} {atk.energy_type.value}"
                cost_surf = self.font_small.render(cost_text, True, type_color)
                self.screen.blit(cost_surf, (x + 12, btn_y + 28))

                # Show effectiveness
                opponent_active = self.engine.opponent.active_pokemon
                if opponent_active:
                    eff = get_type_effectiveness(atk.energy_type, opponent_active.pokemon_type)
                    if eff > 1.0:
                        eff_text = "Super Effective!"
                        eff_color = GREEN
                    elif eff < 1.0 and eff > 0:
                        eff_text = "Not Effective"
                        eff_color = (200, 150, 50)
                    elif eff == 0:
                        eff_text = "No Effect"
                        eff_color = RED
                    else:
                        eff_text = "Normal"
                        eff_color = WHITE

                    eff_surf = self.font_small.render(eff_text, True, eff_color)
                    self.screen.blit(eff_surf, (x + 120, btn_y + 28))

                self.attack_buttons[f"attack_{i}"] = btn_rect

    def _draw_buttons(self):
        btn_y = 700
        self.buttons.clear()  # Now safe to clear since attack_buttons is separate

        if self.engine.phase == GamePhase.DRAW:
            btn_rect = pygame.Rect(30, btn_y, 120, 40)
            pygame.draw.rect(self.screen, (50, 100, 200), btn_rect, border_radius=8)
            text = self.font_med.render("Draw Card", True, WHITE)
            self.screen.blit(text, (btn_rect.x + 10, btn_rect.y + 10))
            self.buttons["draw"] = btn_rect

        if self.selected_hand_card is not None and self.engine.phase == GamePhase.MAIN:
            btn_rect = pygame.Rect(170, btn_y, 120, 40)
            pygame.draw.rect(self.screen, (50, 150, 50), btn_rect, border_radius=8)
            text = self.font_med.render("Play Card", True, WHITE)
            self.screen.blit(text, (btn_rect.x + 15, btn_rect.y + 10))
            self.buttons["play_card"] = btn_rect

        if self.engine.phase == GamePhase.MAIN and self.engine.current_player_index == 0:
            btn_rect = pygame.Rect(310, btn_y, 120, 40)
            pygame.draw.rect(self.screen, (150, 80, 50), btn_rect, border_radius=8)
            text = self.font_med.render("End Turn", True, WHITE)
            self.screen.blit(text, (btn_rect.x + 20, btn_rect.y + 10))
            self.buttons["end_turn"] = btn_rect

        btn_rect = pygame.Rect(self.WIDTH - 150, btn_y, 120, 40)
        pygame.draw.rect(self.screen, (80, 80, 100), btn_rect, border_radius=8)
        text = self.font_med.render("New Game", True, WHITE)
        self.screen.blit(text, (btn_rect.x + 15, btn_rect.y + 10))
        self.buttons["new_game"] = btn_rect

    def _draw_log(self):
        log_x = 750
        log_y = 540
        log_h = 200

        pygame.draw.rect(self.screen, (25, 28, 40),
                        (log_x, log_y, 420, log_h), border_radius=8)
        pygame.draw.rect(self.screen, (60, 65, 80),
                        (log_x, log_y, 420, log_h), 1, border_radius=8)

        title = self.font_small.render("Battle Log", True, GOLD)
        self.screen.blit(title, (log_x + 5, log_y + 3))

        visible_messages = self.message_log[-10:]
        for i, msg in enumerate(visible_messages):
            msg = msg[:55]
            msg_surf = self.font_small.render(msg, True, (180, 180, 200))
            self.screen.blit(msg_surf, (log_x + 8, log_y + 20 + i * 17))

    def _draw_ml_panel(self):
        panel_x = 980
        panel_y = 280

        pygame.draw.rect(self.screen, (25, 28, 45),
                        (panel_x, panel_y, 200, 200), border_radius=8)
        pygame.draw.rect(self.screen, (80, 60, 160),
                        (panel_x, panel_y, 200, 200), 2, border_radius=8)

        title = self.font_med.render("🧠 ML Predictions", True, (180, 140, 255))
        self.screen.blit(title, (panel_x + 10, panel_y + 8))

        if self.battle_predictor and self.battle_predictor.is_trained and self.engine:
            try:
                state = self.engine.get_game_state()
                win_prob = self.battle_predictor.predict_win_probability(state)
                if self.engine.current_player_index == 1:
                    win_prob = 1 - win_prob

                bar_x = panel_x + 15
                bar_y = panel_y + 40
                bar_w = 170
                bar_h = 25

                pygame.draw.rect(self.screen, (60, 40, 40),
                               (bar_x, bar_y, bar_w, bar_h), border_radius=5)
                fill_w = int(bar_w * win_prob)
                color = GREEN if win_prob > 0.5 else RED
                pygame.draw.rect(self.screen, color,
                               (bar_x, bar_y, fill_w, bar_h), border_radius=5)

                prob_text = f"Win: {win_prob*100:.0f}%"
                prob_surf = self.font_med.render(prob_text, True, WHITE)
                self.screen.blit(prob_surf, (bar_x + 50, bar_y + 3))

                # Feature importance
                importance = self.battle_predictor.get_feature_importance()
                imp_y = bar_y + 40
                imp_title = self.font_small.render("Key Factors:", True, GOLD)
                self.screen.blit(imp_title, (bar_x, imp_y))

                for i, (feat, score) in enumerate(list(importance.items())[:5]):
                    feat_text = f"{feat}: {score:.3f}"
                    feat_surf = self.font_small.render(feat_text, True, (160, 160, 180))
                    self.screen.blit(feat_surf, (bar_x, imp_y + 18 + i * 15))
            except Exception as e:
                error_surf = self.font_small.render("Prediction error", True, RED)
                self.screen.blit(error_surf, (panel_x + 20, panel_y + 45))
        else:
            no_model = self.font_small.render("Model not trained", True, (120, 120, 140))
            self.screen.blit(no_model, (panel_x + 20, panel_y + 45))

            train_hint = self.font_small.render("Run train.py first", True, (140, 100, 200))
            self.screen.blit(train_hint, (panel_x + 25, panel_y + 65))

    def _draw_game_over(self):
        overlay = pygame.Surface((self.WIDTH, self.HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        if self.engine.winner:
            is_player_win = self.engine.winner == self.engine.players[0]
            text = "YOU WIN! 🎉" if is_player_win else "AI WINS! 🤖"
            color = GOLD if is_player_win else RED
        else:
            text = "DRAW!"
            color = WHITE

        text_surf = self.font_large.render(text, True, color)
        text_rect = text_surf.get_rect(center=(self.WIDTH // 2, self.HEIGHT // 2))
        self.screen.blit(text_surf, text_rect)

        restart = self.font_med.render("Click or press N to play again", True, WHITE)
        self.screen.blit(restart, (self.WIDTH // 2 - restart.get_width() // 2,
                                   self.HEIGHT // 2 + 50))

    def _get_hand_rects(self):
        if not self.engine:
            return []
        return [pygame.Rect(30 + i * 135, 510, self.card_renderer.width, self.card_renderer.height)
                for i in range(len(self.engine.current_player.hand))]

    def _get_active_pokemon_rect(self):
        return pygame.Rect(450, 310, self.active_renderer.width, self.active_renderer.height)

    def _get_bench_rects(self):
        return [pygame.Rect(30 + i * 130, 360, self.card_renderer.width, self.card_renderer.height)
                for i in range(5)]

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
