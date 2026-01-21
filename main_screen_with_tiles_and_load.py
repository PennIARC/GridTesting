import pygame
import math
import time
import random
from generateMap import IARCMapGenerator
from text import drawText
from fontDict import fonts

pygame.init()

# ---------------- Configuration
FPS = 60
SCALE_DOWN_FACTOR = 2

screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
clock = pygame.time.Clock()

screen_width = int(screen.get_width() / SCALE_DOWN_FACTOR)
screen_height = int(screen.get_height() / SCALE_DOWN_FACTOR)

screen2 = pygame.Surface((screen_width, screen_height)).convert_alpha()
screenT = pygame.Surface((screen_width, screen_height)).convert_alpha()
screenUI = pygame.Surface((screen_width, screen_height)).convert_alpha()

font_regular = fonts[f"regular{int(25 / (SCALE_DOWN_FACTOR ** (1 / 1.5)))}"]
font_bold = fonts[f"bold{int(25 / (SCALE_DOWN_FACTOR ** (1 / 1.5)))}"]
font_bold15 = fonts[f"bold{int(15 / (SCALE_DOWN_FACTOR ** (1 / 1.5)))}"]


class Endesga:
    maroon_red = [87, 28, 39]
    lighter_maroon_red = [127, 36, 51]
    dark_green = [9, 26, 23]
    light_brown = [191, 111, 74]
    black = [19, 19, 19]
    grey_blue = [66, 76, 110]
    cream = [237, 171, 80]
    white = [255, 255, 255]
    greyL = [200, 200, 200]
    grey = [150, 150, 150]
    greyD = [100, 100, 100]
    greyVD = [50, 50, 50]
    network_green = [64, 128, 67]
    debug_red = [255, 96, 141]
    my_blue = [32, 36, 46]
    orange_bright = [255, 165, 0]
    tree_green = [34, 139, 34]

    danger_vis_color = (255, 100, 100, 80)
    danger_hid_color = (255, 165, 0, 80)
    sacrificed_color = (255, 255, 0, 100)


tile_colors = {
    1: Endesga.white,  # Safe Path
    2: Endesga.lighter_maroon_red,  # Visible Mine
    3: Endesga.orange_bright,  # Hidden Mine
    4: Endesga.light_brown,  # Tree Trunk
    5: Endesga.tree_green  # Tree Canopy
}

# ---------------- Map Logic
map_gen = IARCMapGenerator()

# Parameters
p_mines_total = 135
p_hidden_rate = 0.05
p_num_trees = 12

# Store data for 3 scenarios: [Tolerance 0, Tolerance 1, Tolerance 2]
maps_data = []  # List of tuples: (grid, violations, score, width, found)


def run_solver():
    global maps_data
    # 1. Generate & Solve
    map_gen.generate_base_map(
        num_trees=p_num_trees,
        num_mines=p_mines_total,
        hidden_rate=p_hidden_rate,
        safe_buffer_size=2
    )
    map_gen.solve_all_scenarios()

    # 2. Extract Data for all 3 scenarios
    maps_data = []
    for t in range(3):
        data = map_gen.get_render_data_for_tolerance(t)
        maps_data.append(data)


# Initial Load
run_solver()

# ---------------- Global UI State
shake = [0, 0]
scroll = [0, 0]
toggle_ui = True
click = False
drag_origin = None

# ---------------- Main Loop
last_time = time.time()
running = True

while running:
    # ---------------- Input
    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

            if event.key == pygame.K_SPACE:
                toggle_ui = not toggle_ui

            if event.key == pygame.K_g:
                run_solver()

            if event.key == pygame.K_m:
                if p_mines_total < 6000: p_mines_total += 5
                run_solver()
            if event.key == pygame.K_n:
                if p_mines_total > 0: p_mines_total -= 5
                run_solver()

            if event.key == pygame.K_p:
                if p_hidden_rate <= 0.95: p_hidden_rate += 0.05
                run_solver()
            if event.key == pygame.K_o:
                if p_hidden_rate >= 0.05: p_hidden_rate -= 0.05
                run_solver()

            if event.key == pygame.K_k:
                p_num_trees += 1
                run_solver()
            if event.key == pygame.K_l:
                if p_num_trees > 0: p_num_trees -= 1
                run_solver()

            if event.key == pygame.K_r:
                scroll = [0, 0]

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button in [1, 2]:
                click = True
                drag_origin = pygame.math.Vector2(mx, my)
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button in [1, 2]:
                click = False
                drag_origin = None

    if click and drag_origin:
        curr_mouse = pygame.math.Vector2(mx, my)
        delta = curr_mouse - drag_origin
        scroll[0] += delta.x / SCALE_DOWN_FACTOR
        scroll[1] += delta.y / SCALE_DOWN_FACTOR
        drag_origin = curr_mouse

    # ---------------- Layout Calculation
    # We display 3 maps vertically
    PADDING = 20
    HEADER_H = 30
    MAP_H = 40
    MAP_W = 150

    # Calculate scale to fit 3 maps + headers in screen height
    total_content_h = (MAP_H * 3) + (PADDING * 4) + (HEADER_H * 3)

    avail_w = screen_width - (PADDING * 2)
    avail_h = screen_height

    scale_x = avail_w / MAP_W
    scale_y = avail_h / total_content_h
    tile_size = int(max(1, min(scale_x, scale_y)))

    start_x = (screen_width - (tile_size * MAP_W)) // 2

    # ---------------- Update Logic
    dt = (time.time() - last_time) * FPS
    last_time = time.time()

    screen.fill(Endesga.my_blue)
    screen2.fill(Endesga.my_blue)
    screenT.fill((0, 0, 0, 0))
    screenUI.fill((0, 0, 0, 0))

    # ---------------- Render Loop (3 Maps)
    current_y = PADDING + scroll[1]

    for t_idx in range(3):
        # Unpack data
        grid, violations, score, width, found = maps_data[t_idx]

        # 1. Draw Header Info
        header_text = f"TOLERANCE: {t_idx}  |  PATH WIDTH: {width}  |  SCORE: {int(score)}  |  VIOLATIONS: {violations}"
        if not found: header_text += " [NO PATH]"

        col = Endesga.white
        if violations > t_idx: col = Endesga.orange_bright  # Actual > Allowed

        drawText(screenUI, col, font_bold15, start_x + scroll[0], current_y, header_text)
        current_y += HEADER_H

        # 2. Draw Map Tiles
        draw_solid = []
        draw_trans = []

        start_y_map = current_y

        for r_idx, row in enumerate(grid):
            for c_idx, tile_id in enumerate(row):
                if tile_id != 0:
                    rect_x = start_x + (c_idx * tile_size) + scroll[0]
                    rect_y = start_y_map + (r_idx * tile_size)

                    # Basic Culling
                    if -tile_size < rect_x < screen_width and -tile_size < rect_y < screen_height:
                        r = pygame.Rect(rect_x, rect_y, tile_size, tile_size)

                        if tile_id == 6:
                            draw_trans.append((r, Endesga.danger_vis_color))
                        elif tile_id == 7:
                            draw_trans.append((r, Endesga.danger_hid_color))
                        elif tile_id == 8:
                            draw_trans.append((r, Endesga.sacrificed_color))
                        else:
                            draw_solid.append((r, tile_id))

        if tile_size > 2:
            for r, tid in draw_solid:
                pygame.draw.rect(screen2, Endesga.greyVD, (r.x - r.width / 6, r.y + r.height / 4, r.width, r.height))

        for r, tid in draw_solid:
            color = tile_colors.get(tid, Endesga.debug_red)
            pygame.draw.rect(screen2, color, r)

        for r, col in draw_trans:
            pygame.draw.rect(screenT, col, r)

        # Increment Y for next map
        current_y += (MAP_H * tile_size) + PADDING

    # ---------------- Render UI Overlay
    if toggle_ui:
        infos = [
            f"FPS: {int(clock.get_fps())}",
            f"Mines: {p_mines_total} (M/N)",
            f"Hidden: {int(p_hidden_rate * 100)}% (P/O)",
            f"Trees: {p_num_trees} (K/L)",
        ]
        ui_y = 10
        for info in infos:
            drawText(screenUI, Endesga.white, font_bold, 10, ui_y, info)
            ui_y += 12

        # Legend
        leg_y = 10
        leg_x = screen_width - 120
        legend_items = [
            ("Safe Path", Endesga.white, False),
            ("Visible Mine", Endesga.lighter_maroon_red, False),
            ("Sacrificed Zone", (255, 255, 0), True),
            ("Danger Zone", (255, 100, 100), True),
            ("Hidden Mine", Endesga.orange_bright, False),
            ("Unknown Danger", (255, 165, 0), True),
            ("Tree Trunk", Endesga.light_brown, False),
            ("Tree Canopy", Endesga.tree_green, False),
        ]
        for name, col, outline in legend_items:
            if outline:
                pygame.draw.rect(screenUI, col, (leg_x, leg_y, 8, 8), 1)
            else:
                pygame.draw.rect(screenUI, col, (leg_x, leg_y, 8, 8))
            drawText(screenUI, Endesga.white, font_regular, leg_x + 12, leg_y - 2, name)
            leg_y += 12

        mx_sc, my_sc = mx / SCALE_DOWN_FACTOR, my / SCALE_DOWN_FACTOR
        pygame.mouse.set_visible(False)
        pygame.draw.circle(screenUI, Endesga.black, (mx_sc + 1, my_sc + 1), 3, 1)
        pygame.draw.circle(screenUI, Endesga.white, (mx_sc, my_sc), 3, 1)

    screen.blit(pygame.transform.scale(screen2, (screen.get_width(), screen.get_height())), (0, 0))
    screen.blit(pygame.transform.scale(screenT, (screen.get_width(), screen.get_height())), (0, 0))
    screen.blit(pygame.transform.scale(screenUI, (screen.get_width(), screen.get_height())), (0, 0))

    pygame.display.flip()
    clock.tick(FPS)