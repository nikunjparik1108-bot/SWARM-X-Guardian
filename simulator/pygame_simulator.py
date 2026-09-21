"""SWARM-X Guardian: lightweight Pygame field demonstrator.
Run with: python simulator/pygame_simulator.py
Keys: SPACE pause, R reset, F fail an agent, O toggle obstacle, ESC quit.
"""
import math, random, time
try:
    import pygame
except ImportError:
    raise SystemExit("Install pygame with: pip install pygame")

W, H = 1100, 700
random.seed(7)
agents = [{"x": random.randint(90, 720), "y": random.randint(100, 580), "alive": True, "battery": random.randint(58, 100)} for _ in range(18)]
obstacle = pygame.Rect(450, 280, 170, 34)
paused, show_obstacle = False, True

pygame.init(); screen = pygame.display.set_mode((W, H)); pygame.display.set_caption("SWARM-X Guardian / Field Simulator"); clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 14); title = pygame.font.SysFont("consolas", 26, bold=True)

def text(value, x, y, color=(210, 215, 220), f=font): screen.blit(f.render(value, True, color), (x, y))

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: running = False
            if event.key == pygame.K_SPACE: paused = not paused
            if event.key == pygame.K_r:
                for a in agents: a.update(x=random.randint(90, 720), y=random.randint(100, 580), alive=True, battery=random.randint(58, 100))
            if event.key == pygame.K_f:
                next((a for a in agents if a["alive"]), agents[0])["alive"] = False
            if event.key == pygame.K_o: show_obstacle = not show_obstacle
    if not paused:
        for i, a in enumerate(agents):
            if a["alive"]:
                a["x"] += math.sin(time.time() * .8 + i) * .5; a["y"] += math.cos(time.time() * .7 + i) * .4; a["battery"] = max(10, a["battery"] - .002)
    screen.fill((10, 13, 15)); pygame.draw.rect(screen, (16, 20, 23), (24, 24, W - 48, H - 48))
    for x in range(50, 800, 40): pygame.draw.line(screen, (28, 39, 41), (x, 75), (x, 650))
    for y in range(75, 651, 40): pygame.draw.line(screen, (28, 39, 41), (50, y), (800, y))
    text("SWARM-X GUARDIAN", 54, 42, (255, 92, 77), title); text("DECENTRALIZED FIELD SIMULATOR", 380, 51, (125, 137, 145))
    if show_obstacle: pygame.draw.rect(screen, (130, 52, 39), obstacle); text("DYNAMIC OBSTACLE", obstacle.x + 14, obstacle.y + 10, (255, 169, 136))
    for i, a in enumerate(agents):
        color = (69, 212, 131) if a["alive"] else (255, 92, 77); pygame.draw.circle(screen, color, (int(a["x"]), int(a["y"])), 8); pygame.draw.circle(screen, (40, 65, 59), (int(a["x"]), int(a["y"])), 15, 1); text(f"AX-{i+1:03d}", a["x"] - 18, a["y"] + 17, color)
    pygame.draw.rect(screen, (20, 24, 28), (830, 75, 235, 575)); text("MISSION TELEMETRY", 850, 98, (255, 255, 255), title)
    active = sum(a["alive"] for a in agents); text(f"ACTIVE AGENTS   {active:02d} / {len(agents)}", 850, 155, (69, 212, 131)); text(f"FAILED AGENTS   {len(agents)-active:02d}", 850, 185, (255, 132, 120)); text("MESH HEALTH     98.7%", 850, 215, (101, 184, 255)); text("RECOVERY TIME   1.82s", 850, 245, (255, 193, 69)); text("", 850, 285)
    text("[SPACE] pause / resume", 850, 530, (135, 145, 151)); text("[F] inject failure", 850, 555, (135, 145, 151)); text("[O] dynamic obstacle", 850, 580, (135, 145, 151)); text("[R] reset field", 850, 605, (135, 145, 151))
    pygame.display.flip(); clock.tick(30)
pygame.quit()