import pygame
import random

pygame.init()

screen = pygame.display.set_mode((1920, 1080))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 100)
small_font = pygame.font.SysFont(None, 50)

running = True
dt = 0
game_over = False

# --- KONSTANTY ---
PLAYER_SPEED = 320
PLAYER_MAX_HEALTH = 150
ENEMY_SPEED_REGULAR = 150
ENEMY_RADIUS_REGULAR = 40
BULLET_RADIUS = 7
MAX_ENEMIES = 10 
BASE_SHOOT_COOLDOWN = 150 # Základní rychlost střelby

ENEMY_SHOOT_INTERVAL = 2500 
ENEMY_BULLET_SPEED = 350
ENEMY_BULLET_DAMAGE = 30
HEALTH_STEP_FOR_SPAWN = 1000 

# --- PROMĚNNÉ ---
last_shot_time = 0
kills = 0
total_spawned_count = 0 
hits_landed = 0 
player_health = PLAYER_MAX_HEALTH
bullets = []
boss_bullets = [] 
enemies = []

# Rapid Fire proměnné
total_bullets_fired = 0
rapid_fire_ready = False
rapid_fire_active = False
rapid_fire_end_time = 0

def spawn_enemy(is_boss=False, pos=None):
    global total_spawned_count
    if pos is None:
        side = random.randint(0, 3)
        if side == 0: pos = pygame.Vector2(random.randint(0, screen.get_width()), -100)
        elif side == 1: pos = pygame.Vector2(random.randint(0, screen.get_width()), screen.get_height() + 100)
        elif side == 2: pos = pygame.Vector2(-100, random.randint(0, screen.get_height()))
        else: pos = pygame.Vector2(screen.get_width() + 100, random.randint(0, screen.get_height()))

    if is_boss:
        return {
            "pos": pos, "health": 5000, "max_health": 5000,
            "speed": ENEMY_SPEED_REGULAR / 5, "radius": 120, "color": "orange",
            "is_boss": True, "can_shoot": True,
            "last_spawn_health": 5000,
            "last_shot": 0, "shoot_cooldown": 1700 # Sníženo o 15 % (z 2000)
        }
    else:
        total_spawned_count += 1
        can_shoot = (total_spawned_count % 10 == 0)
        return {
            "pos": pos, "health": 100, "max_health": 100,
            "speed": ENEMY_SPEED_REGULAR, "radius": ENEMY_RADIUS_REGULAR,
            "color": "blue" if can_shoot else "red",
            "is_boss": False, "can_shoot": can_shoot,
            "last_shot": random.randint(0, 1000), "shoot_cooldown": ENEMY_SHOOT_INTERVAL
        }

def reset_game():
    global player_pos, bullets, boss_bullets, enemies, game_over, kills, hits_landed, player_health, total_spawned_count, total_bullets_fired, rapid_fire_ready, rapid_fire_active
    player_pos = pygame.Vector2(screen.get_width() / 2, screen.get_height() / 2)
    bullets, boss_bullets, enemies = [], [], []
    kills, hits_landed, total_spawned_count, total_bullets_fired = 0, 0, 0, 0
    player_health = PLAYER_MAX_HEALTH
    rapid_fire_ready = False
    rapid_fire_active = False
    for _ in range(MAX_ENEMIES): enemies.append(spawn_enemy())
    game_over = False

reset_game()

while running:
    current_time = pygame.time.get_ticks()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r: reset_game()
            # Aktivace Rapid Fire
            if event.key == pygame.K_LSHIFT and rapid_fire_ready:
                rapid_fire_ready = False
                rapid_fire_active = True
                rapid_fire_end_time = current_time + 4000 # Trvá 4 sekundy

    if rapid_fire_active and current_time > rapid_fire_end_time:
        rapid_fire_active = False

    keys = pygame.key.get_pressed()
    screen.fill("purple")

    if not game_over:
        if keys[pygame.K_w]: player_pos.y -= PLAYER_SPEED * dt
        if keys[pygame.K_s]: player_pos.y += PLAYER_SPEED * dt
        if keys[pygame.K_a]: player_pos.x -= PLAYER_SPEED * dt
        if keys[pygame.K_d]: player_pos.x += PLAYER_SPEED * dt
        if keys[pygame.K_ESCAPE]: running = False

        # Dynamický cooldown střelby
        current_cooldown = (BASE_SHOOT_COOLDOWN / 3) if rapid_fire_active else BASE_SHOOT_COOLDOWN

        # Střelba hráče
        if keys[pygame.K_SPACE] and current_time - last_shot_time > current_cooldown:
            last_shot_time = current_time
            mouse_pos = pygame.mouse.get_pos()
            direction = pygame.Vector2(mouse_pos) - player_pos
            if direction.length() != 0:
                is_super = (hits_landed >= 10)
                if is_super: hits_landed = 0 
                
                # Počítadlo pro Rapid Fire
                if not rapid_fire_ready and not rapid_fire_active:
                    total_bullets_fired += 1
                    if total_bullets_fired >= 50:
                        rapid_fire_ready = True
                        total_bullets_fired = 0

                bullets.append({
                    "pos": player_pos.copy(), "dir": direction.normalize(), 
                    "damage": 100 if is_super else 20,
                    "color": "magenta" if is_super else ("cyan" if rapid_fire_active else "yellow")
                })

        # Update kulek
        for bullet in bullets:
            bullet["pos"] += bullet["dir"] * 1000 * dt
            pygame.draw.circle(screen, bullet["color"], bullet["pos"], BULLET_RADIUS)
        bullets = [b for b in bullets if 0 < b["pos"].x < screen.get_width() and 0 < b["pos"].y < screen.get_height()]

        for b_bullet in boss_bullets[:]:
            b_bullet["pos"] += b_bullet["dir"] * b_bullet["speed"] * dt
            pygame.draw.circle(screen, b_bullet["color"], b_bullet["pos"], b_bullet["radius"])
            if b_bullet["pos"].distance_to(player_pos) < b_bullet["radius"] + 30:
                player_health -= b_bullet["damage"]
                if b_bullet in boss_bullets: boss_bullets.remove(b_bullet)
        boss_bullets = [b for b in boss_bullets if 0 < b["pos"].x < screen.get_width() and 0 < b["pos"].y < screen.get_height()]

        # Kolize a logika spawnování
        for bullet in bullets[:]:
            bullet_removed = False
            for enemy in enemies:
                if bullet["pos"].distance_to(enemy["pos"]) < enemy["radius"] + BULLET_RADIUS:
                    enemy["health"] -= bullet["damage"]
                    if enemy.get("is_boss") and enemy["last_spawn_health"] - enemy["health"] >= HEALTH_STEP_FOR_SPAWN:
                        enemy["last_spawn_health"] -= HEALTH_STEP_FOR_SPAWN
                        for _ in range(10):
                            enemies.append(spawn_enemy(pos=enemy["pos"] + pygame.Vector2(random.randint(-150, 150), random.randint(-150, 150))))
                    if bullet["color"] == "yellow" and hits_landed < 10: hits_landed += 1 
                    if not bullet_removed:
                        if bullet in bullets: bullets.remove(bullet)
                        bullet_removed = True
                    break

        boss_present = any(e.get("is_boss", False) for e in enemies)
        for enemy in enemies[:]:
            if enemy["can_shoot"]:
                if current_time - enemy["last_shot"] > enemy["shoot_cooldown"]:
                    enemy["last_shot"] = current_time
                    b_dir = (player_pos - enemy["pos"])
                    if b_dir.length() != 0:
                        boss_bullets.append({
                            "pos": enemy["pos"].copy(), "dir": b_dir.normalize(),
                            "speed": 400 if enemy["is_boss"] else ENEMY_BULLET_SPEED,
                            "damage": 100 if enemy["is_boss"] else ENEMY_BULLET_DAMAGE,
                            "radius": 25 if enemy["is_boss"] else 12,
                            "color": "orange" if enemy["is_boss"] else "cyan"
                        })
            if player_pos.distance_to(enemy["pos"]) < enemy["radius"] + 35: player_health -= 50 * dt 
            if enemy["health"] <= 0:
                is_dead_boss = enemy.get("is_boss", False)
                enemies.remove(enemy)
                kills += 1
                if is_dead_boss:
                    while len(enemies) < MAX_ENEMIES: enemies.append(spawn_enemy())
                elif not boss_present:
                    if kills % 15 == 0: enemies.append(spawn_enemy(is_boss=True))
                    else: enemies.append(spawn_enemy())

        # Pohyb a vykreslení
        for enemy in enemies:
            direction = player_pos - enemy["pos"]
            if direction.length() != 0: enemy["pos"] += direction.normalize() * enemy["speed"] * dt
            pygame.draw.circle(screen, enemy["color"], enemy["pos"], enemy["radius"])
            bar_w = enemy["radius"] * 1.5
            h_ratio = max(0, enemy["health"] / enemy["max_health"])
            pygame.draw.rect(screen, "black", (enemy["pos"].x - bar_w/2 - 2, enemy["pos"].y - enemy["radius"] - 22, bar_w + 4, 14))
            pygame.draw.rect(screen, "darkred", (enemy["pos"].x - bar_w/2, enemy["pos"].y - enemy["radius"] - 20, bar_w, 10))
            pygame.draw.rect(screen, "green", (enemy["pos"].x - bar_w/2, enemy["pos"].y - enemy["radius"] - 20, bar_w * h_ratio, 10))

        if player_health <= 0: game_over = True

        # --- UI SEKCE ---
        screen.blit(small_font.render(f"Zabití: {kills}", True, "white"), (20, 20))
        
        # Super Bar
        fill_ratio = min(1.0, hits_landed / 10)
        pygame.draw.rect(screen, "white", (20, 70, 300, 30), 2)
        pygame.draw.rect(screen, "magenta" if hits_landed >= 10 else (150, 0, 150), (22, 72, 296 * fill_ratio, 26))
        screen.blit(small_font.render("SUPER", True, "white"), (330, 68))

        # Rapid Fire UI
        if rapid_fire_ready:
            screen.blit(small_font.render("RAPID READY (SHIFT)", True, "cyan"), (20, 110))
        elif rapid_fire_active:
            time_left = (rapid_fire_end_time - current_time) / 1000
            screen.blit(small_font.render(f"RAPID FIRE: {time_left:.1f}s", True, "cyan"), (20, 110))
        else:
            # Malý progress bar pro nabití Rapidu
            pygame.draw.rect(screen, "white", (20, 110, 150, 10), 1)
            pygame.draw.rect(screen, "cyan", (20, 110, 150 * (total_bullets_fired/50), 10))

        # Health bar hráče
        p_bar_w = 80
        p_h_ratio = max(0, player_health / PLAYER_MAX_HEALTH)
        pygame.draw.rect(screen, "black", (player_pos.x - p_bar_w/2 - 2, player_pos.y - 62, p_bar_w + 4, 12))
        pygame.draw.rect(screen, "darkred", (player_pos.x - p_bar_w/2, player_pos.y - 60, p_bar_w, 8))
        pygame.draw.rect(screen, "cyan", (player_pos.x - p_bar_w/2, player_pos.y - 60, p_bar_w * p_h_ratio, 8))

    else:
        msg = font.render("ZEMŘEL JSI - Stiskni R", True, "white")
        screen.blit(msg, (screen.get_width()/2 - msg.get_width()/2, screen.get_height()/2))

    pygame.draw.circle(screen, "teal", player_pos, 40)
    pygame.display.flip()
    dt = clock.tick(240) / 1000

pygame.quit()