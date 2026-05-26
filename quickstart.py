
"""Quick start - minimal working version with fixes."""

import pygame
import random
import sys
from enum import Enum

# ============ MINI CARD GAME ============

class PType(Enum):
    FIRE = ("Fire", (240, 80, 50))
    WATER = ("Water", (50, 130, 255))
    GRASS = ("Grass", (50, 200, 80))
    ELECTRIC = ("Electric", (255, 210, 50))
    PSYCHIC = ("Psychic", (200, 80, 200))

# Complete type effectiveness chart
EFFECTIVENESS = {
    (PType.FIRE, PType.GRASS): 2.0,
    (PType.FIRE, PType.WATER): 0.5,
    (PType.FIRE, PType.FIRE): 0.5,
    (PType.WATER, PType.FIRE): 2.0,
    (PType.WATER, PType.GRASS): 0.5,
    (PType.WATER, PType.WATER): 0.5,
    (PType.GRASS, PType.WATER): 2.0,
    (PType.GRASS, PType.FIRE): 0.5,
    (PType.GRASS, PType.GRASS): 0.5,
    (PType.ELECTRIC, PType.WATER): 2.0,
    (PType.ELECTRIC, PType.ELECTRIC): 0.5,
    (PType.ELECTRIC, PType.GRASS): 0.5,
    (PType.PSYCHIC, PType.PSYCHIC): 0.5,
}

CARDS = [
    {"name": "Charizard", "type": PType.FIRE, "hp": 120,
     "attacks": [("Fire Spin", 30, 1), ("Flamethrower", 60, 2)]},
    {"name": "Blastoise", "type": PType.WATER, "hp": 120,
     "attacks": [("Water Gun", 30, 1), ("Hydro Pump", 70, 2)]},
    {"name": "Venusaur", "type": PType.GRASS, "hp": 120,
     "attacks": [("Vine Whip", 30, 1), ("Solar Beam", 70, 2)]},
    {"name": "Pikachu", "type": PType.ELECTRIC, "hp": 60,
     "attacks": [("Thunder Jolt", 20, 1), ("Thunder", 60, 2)]},
    {"name": "Mewtwo", "type": PType.PSYCHIC, "hp": 130,
     "attacks": [("Psyburn", 40, 1), ("Psystrike", 80, 2)]},
    {"name": "Arcanine", "type": PType.FIRE, "hp": 100,
     "attacks": [("Flame Burst", 20, 1), ("Fire Blast", 70, 2)]},
    {"name": "Gyarados", "type": PType.WATER, "hp": 130,
     "attacks": [("Aqua Tail", 40, 1), ("Dragon Rage", 80, 2)]},
    {"name": "Exeggutor", "type": PType.GRASS, "hp": 100,
     "attacks": [("Stomp", 20, 1), ("Solar Beam", 60, 2)]},
]


class Pokemon:
    def __init__(self, data):
        self.name = data["name"]
        self.ptype = data["type"]
        self.max_hp = data["hp"]
        self.hp = data["hp"]
        self.attacks = data["attacks"]
        self.energy = 1  # Start with 1 energy so first turn is playable

    def can_attack(self, idx):
        return self.energy >= self.attacks[idx][2] and self.hp > 0

    def get_damage(self, atk_idx, defender):
        """Calculate damage with type effectiveness."""
        name, base_dmg, cost = self.attacks[atk_idx]
        eff = EFFECTIVENESS.get((self.ptype, defender.ptype), 1.0)

        # STAB bonus
        stab = 1.2 if self.ptype == self.ptype else 1.0  # Always same type in this mini version

        damage = int(base_dmg * eff * stab)
        return damage, eff


class MiniGame:
    def __init__(self):
        pygame.init()
        self.W, self.H = 900, 600
        self.screen = pygame.display.set_mode((self.W, self.H))
        pygame.display.set_caption("Pokémon Card Battle ⚔️ (Improved)")
        self.clock = pygame.time.Clock()
        self.font_lg = pygame.font.SysFont("Arial", 32, bold=True)
        self.font_md = pygame.font.SysFont("Arial", 20)
        self.font_sm = pygame.font.SysFont("Arial", 14)
        self.new_game()

    def new_game(self):
        pool = random.sample(CARDS, 6)
        self.player = Pokemon(pool[0])
        self.enemy = Pokemon(pool[1])
        self.log = ["Battle Start!"]
        self.turn = "player"
        self.turn_count = 1
        self.max_turns = 50
        self.game_over = False
        self.winner = None
        self.selected_attack = None

    def calc_damage(self, attacker, atk_idx, defender):
        damage, eff = attacker.get_damage(atk_idx, defender)
        defender.hp -= damage

        name, base_dmg, cost = attacker.attacks[atk_idx]
        msg = f"{attacker.name} used {name}! {damage} dmg"
        if eff > 1.0: 
            msg += " (Super Effective!)"
        elif eff < 1.0: 
            msg += " (Not Effective)"
        self.log.append(msg)

        if defender.hp <= 0:
            defender.hp = 0
            self.log.append(f"{defender.name} fainted!")
            self.game_over = True
            self.winner = attacker.name

    def ai_turn(self):
        if self.game_over:
            return

        # Gain energy at turn start
        self.enemy.energy += 1

        best = 0
        best_score = -1
        for i, (n, d, c) in enumerate(self.enemy.attacks):
            if self.enemy.can_attack(i):
                # Score by damage
                damage, eff = self.enemy.get_damage(i, self.player)
                score = damage
                if damage >= self.player.hp:
                    score += 100  # KO bonus
                if score > best_score:
                    best_score = score
                    best = i

        if self.enemy.can_attack(best):
            self.enemy.energy -= self.enemy.attacks[best][2]
            self.calc_damage(self.enemy, best, self.player)

        self.turn = "player"
        self.turn_count += 1

        # Check max turns
        if self.turn_count >= self.max_turns:
            self.game_over = True
            if self.player.hp > self.enemy.hp:
                self.winner = self.player.name
            elif self.enemy.hp > self.player.hp:
                self.winner = self.enemy.name
            else:
                self.winner = "Draw"

    def draw_card(self, pokemon, x, y, is_enemy=False):
        color = pokemon.ptype.value[1]
        dark = tuple(max(0, c - 80) for c in color)

        rect = pygame.Rect(x, y, 200, 280)
        pygame.draw.rect(self.screen, (250, 245, 235), rect, border_radius=12)
        pygame.draw.rect(self.screen, color, rect, 3, border_radius=12)

        header = pygame.Rect(x + 5, y + 5, 190, 40)
        pygame.draw.rect(self.screen, color, header, border_radius=8)

        name_surf = self.font_md.render(pokemon.name, True, (255, 255, 255))
        self.screen.blit(name_surf, (x + 15, y + 12))

        hp_text = f"HP: {pokemon.hp}/{pokemon.max_hp}"
        hp_color = (50, 200, 80) if pokemon.hp > pokemon.max_hp * 0.5 else (220, 50, 50)
        hp_surf = self.font_md.render(hp_text, True, hp_color)
        self.screen.blit(hp_surf, (x + 15, y + 52))

        bar_rect = pygame.Rect(x + 15, y + 78, 170, 15)
        pygame.draw.rect(self.screen, (80, 80, 80), bar_rect, border_radius=5)
        ratio = max(0, pokemon.hp / pokemon.max_hp)
        fill_color = (50, 200, 80) if ratio > 0.5 else (255, 215, 0) if ratio > 0.25 else (220, 50, 50)
        fill_rect = pygame.Rect(x + 15, y + 78, int(170 * ratio), 15)
        pygame.draw.rect(self.screen, fill_color, fill_rect, border_radius=5)

        type_surf = self.font_sm.render(f"Type: {pokemon.ptype.value[0]}", True, color)
        self.screen.blit(type_surf, (x + 15, y + 100))

        energy_surf = self.font_md.render(f"⚡ Energy: {pokemon.energy}", True, (50, 130, 255))
        self.screen.blit(energy_surf, (x + 15, y + 120))

        # Attacks
        atk_y = y + 150
        self.attack_btns = []
        for i, (aname, dmg, cost) in enumerate(pokemon.attacks):
            can = pokemon.can_attack(i)
            btn_rect = pygame.Rect(x + 10, atk_y, 180, 50)

            if self.selected_attack == i and not is_enemy:
                pygame.draw.rect(self.screen, (255, 255, 200), btn_rect, border_radius=6)
            else:
                bg = (60, 80, 60) if can else (60, 40, 40)
                pygame.draw.rect(self.screen, bg, btn_rect, border_radius=6)

            pygame.draw.rect(self.screen, color, btn_rect, 1, border_radius=6)

            aname_surf = self.font_sm.render(aname, True, (255, 255, 255) if can else (150, 150, 150))
            self.screen.blit(aname_surf, (x + 18, atk_y + 5))

            info = f"Dmg: {dmg} | Cost: {'●' * cost}"
            info_surf = self.font_sm.render(info, True, (200, 200, 200) if can else (120, 120, 120))
            self.screen.blit(info_surf, (x + 18, atk_y + 25))

            if not is_enemy and can:
                self.attack_btns.append((btn_rect, i))

            atk_y += 58

    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_n:
                        self.new_game()

                if event.type == pygame.MOUSEBUTTONDOWN:
                    mx, my = event.pos

                    if self.game_over:
                        self.new_game()
                        continue

                    if self.turn == "player" and not self.game_over:
                        # Check attack buttons
                        for rect, idx in self.attack_btns:
                            if rect.collidepoint(mx, my):
                                if self.player.can_attack(idx):
                                    self.player.energy -= self.player.attacks[idx][2]
                                    self.calc_damage(self.player, idx, self.enemy)
                                    if not self.game_over:
                                        self.turn = "ai"
                                break

                        # Energy button - only if no attack is affordable
                        energy_btn = pygame.Rect(370, 400, 160, 40)
                        if energy_btn.collidepoint(mx, my):
                            # Check if any attack is affordable
                            can_attack_any = any(self.player.can_attack(i) for i in range(len(self.player.attacks)))
                            if not can_attack_any:
                                self.player.energy += 1
                                self.log.append(f"Gained 1 energy! (⚡{self.player.energy})")

            # AI turn
            if self.turn == "ai" and not self.game_over:
                pygame.time.delay(800)
                self.ai_turn()
                if not self.game_over:
                    self.player.energy += 1  # Player gains energy at turn start

            # DRAW
            self.screen.fill((30, 35, 50))

            title = self.font_lg.render("⚔️ Pokémon Card Battle", True, (255, 215, 0))
            self.screen.blit(title, (self.W // 2 - title.get_width() // 2, 10))

            self.draw_card(self.enemy, 50, 60, is_enemy=True)
            self.draw_card(self.player, 50, 360)

            vs = self.font_lg.render("VS", True, (255, 100, 100))
            self.screen.blit(vs, (self.W // 2 - vs.get_width() // 2, 200))

            if not self.game_over:
                turn_text = "Your Turn!" if self.turn == "player" else "AI Thinking..."
                turn_color = (50, 200, 80) if self.turn == "player" else (255, 215, 0)
            else:
                turn_text = f"{self.winner} Wins!"
                turn_color = (255, 215, 0)

            turn_surf = self.font_md.render(turn_text, True, turn_color)
            self.screen.blit(turn_surf, (370, 100))

            # Energy button
            if self.turn == "player" and not self.game_over:
                can_attack_any = any(self.player.can_attack(i) for i in range(len(self.player.attacks)))
                if not can_attack_any:
                    energy_btn = pygame.Rect(370, 400, 160, 40)
                    pygame.draw.rect(self.screen, (50, 100, 200), energy_btn, border_radius=8)
                    e_text = self.font_md.render("+ Energy ⚡", True, (255, 255, 255))
                    self.screen.blit(e_text, (energy_btn.x + 20, energy_btn.y + 8))

            # Battle log
            log_rect = pygame.Rect(370, 150, 500, 220)
            pygame.draw.rect(self.screen, (25, 28, 40), log_rect, border_radius=8)
            pygame.draw.rect(self.screen, (60, 65, 80), log_rect, 1, border_radius=8)

            log_title = self.font_md.render("Battle Log", True, (255, 215, 0))
            self.screen.blit(log_title, (380, 155))

            for i, msg in enumerate(self.log[-8:]):
                msg_surf = self.font_sm.render(msg, True, (180, 180, 200))
                self.screen.blit(msg_surf, (380, 180 + i * 20))

            # Info
            hint = self.font_sm.render("Type Chart: Fire>Grass>Water>Fire  Electric>Water", True, (120, 120, 150))
            self.screen.blit(hint, (370, 560))

            restart = self.font_sm.render("Press N for New Game", True, (120, 120, 150))
            self.screen.blit(restart, (370, 580))

            pygame.display.flip()
            self.clock.tick(30)


if __name__ == "__main__":
    game = MiniGame()
    game.run()
