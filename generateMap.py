import random
import heapq
import collections


class IARCMapGenerator:
    def __init__(self):
        # IARC Field Specifications (Horizontal)
        self.WIDTH = 150
        self.HEIGHT = 40

        # Internal Logic Codes
        self.TILE_EMPTY = 0
        self.TILE_MINE_VISIBLE = 2
        self.TILE_MINE_HIDDEN = 3
        self.TILE_OBSTACLE = 4
        self.TILE_UNSURE = 5

        # Renderer Codes
        self.OUT_SAFE_PATH = 1
        self.OUT_MINE_VISIBLE = 2
        self.OUT_MINE_HIDDEN = 3
        self.OUT_OBSTACLE = 4
        self.OUT_UNSURE = 5
        self.OUT_DANGER_VISIBLE = 6
        self.OUT_DANGER_HIDDEN = 7
        self.OUT_MISSED_ZONE = 8

        # State
        self.grid = []
        self.mines_visible = []
        self.mines_hidden = []

        self.distance_field_visible = {}
        self.distance_field_all = {}
        self.mine_id_map = {}

        # Store best results for each tolerance level (0, 1, 2)
        self.solutions = {}

        self.start_node = (0, self.HEIGHT // 2)
        self.end_node = (self.WIDTH - 1, self.HEIGHT // 2)

        # Initial Generation
        self.generate_base_map(safe_buffer_size=2)

    def generate_base_map(self, num_trees=12, num_mines=135, hidden_rate=0.05, safe_buffer_size=2):
        self.grid = [[self.TILE_EMPTY for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]
        self.mines_visible = []
        self.mines_hidden = []
        self.solutions = {}

        # 1. Obstacles
        for _ in range(num_trees):
            tx = random.randint(safe_buffer_size + 4, self.WIDTH - safe_buffer_size - 4)
            ty = random.randint(3, self.HEIGHT - 4)

            radius = 3
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    ny, nx = ty + dy, tx + dx
                    if 0 <= ny < self.HEIGHT and 0 <= nx < self.WIDTH:
                        if dx * dx + dy * dy <= radius * radius:
                            if self.grid[ny][nx] != self.TILE_OBSTACLE:
                                self.grid[ny][nx] = self.TILE_UNSURE
            self.grid[ty][tx] = self.TILE_OBSTACLE

        # 2. Mines
        all_mines = []
        target = min(num_mines, (self.WIDTH * self.HEIGHT) // 2)
        attempts = 0
        while len(all_mines) < target and attempts < target * 10:
            attempts += 1
            mx = random.randint(0, self.WIDTH - 1)
            my = random.randint(0, self.HEIGHT - 1)

            if mx <= safe_buffer_size or mx >= self.WIDTH - 1 - safe_buffer_size:
                continue

            tile = self.grid[my][mx]
            if tile != self.TILE_OBSTACLE and tile != self.TILE_MINE_VISIBLE and tile != self.TILE_MINE_HIDDEN:
                if random.random() < hidden_rate:
                    self.grid[my][mx] = self.TILE_MINE_HIDDEN
                    self.mines_hidden.append((mx, my))
                else:
                    self.grid[my][mx] = self.TILE_MINE_VISIBLE
                    self.mines_visible.append((mx, my))
                all_mines.append((mx, my))

        # 3. Compute Fields
        self.distance_field_visible, self.mine_id_map = self.compute_voronoi_bfs(self.mines_visible)
        self.distance_field_all, _ = self.compute_voronoi_bfs(all_mines)

    def compute_voronoi_bfs(self, sources):
        dist_map = {}
        id_map = {}
        queue = collections.deque()

        for i, (mx, my) in enumerate(sources):
            dist_map[(mx, my)] = 0
            id_map[(mx, my)] = i
            queue.append((mx, my))

        while queue:
            cx, cy = queue.popleft()
            cur_dist = dist_map[(cx, cy)]
            cur_id = id_map[(cx, cy)]

            for nx, ny in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:
                    if (nx, ny) in dist_map: continue
                    dist_map[(nx, ny)] = cur_dist + 1
                    id_map[(nx, ny)] = cur_id
                    queue.append((nx, ny))
        return dist_map, id_map

    def heuristic(self, a, b):
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return dx + dy + (0.001 * (dx * dx + dy * dy) ** 0.5)

    def calculate_score(self, path_len, width, missed_count):
        if path_len == 0: return 0
        w_feet = width * 2
        l_feet = path_len * 2
        # Standard Formula: (150000 * W) / ((1 + B) * L)
        # Assuming A=0 and N=0 for simplicity in this optimization
        return (150000 * w_feet) / ((1 + missed_count) * l_feet)

    def run_weighted_astar(self, width, allowed_missed_count):
        start = self.start_node
        start_dist = self.distance_field_visible.get(start, 999)

        initial_violated = set()
        if start_dist <= width:
            mid = self.mine_id_map.get(start, -1)
            if mid != -1: initial_violated.add(mid)

        if len(initial_violated) > allowed_missed_count:
            return None, set()

        # State: (x, y, frozenset(violated_ids))
        start_state = (start[0], start[1], frozenset(initial_violated))

        frontier = []
        heapq.heappush(frontier, (0, 0, start[0], start[1], initial_violated))

        min_costs = {start_state: 0}
        came_from = {}

        while frontier:
            _, current_g, cx, cy, c_violated = heapq.heappop(frontier)

            if (cx, cy) == self.end_node:
                path = []
                curr = (cx, cy, frozenset(c_violated))
                while curr in came_from:
                    path.append((curr[0], curr[1]))
                    curr = came_from[curr]
                path.append(start)
                return path[::-1], c_violated

            for nx, ny in [(cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)]:
                if 0 <= nx < self.WIDTH and 0 <= ny < self.HEIGHT:

                    tile = self.grid[ny][nx]
                    if tile == self.TILE_OBSTACLE or tile == self.TILE_MINE_VISIBLE:
                        continue

                    dist = self.distance_field_visible.get((nx, ny), 999)
                    new_violated = set(c_violated)

                    if dist <= width:
                        m_id = self.mine_id_map.get((nx, ny), -1)
                        if m_id != -1:
                            if m_id not in c_violated:
                                if len(c_violated) < allowed_missed_count:
                                    new_violated.add(m_id)
                                else:
                                    continue  # Wall

                    new_g = current_g + 1
                    next_state = (nx, ny, frozenset(new_violated))

                    if next_state not in min_costs or new_g < min_costs[next_state]:
                        min_costs[next_state] = new_g
                        priority = new_g + self.heuristic((nx, ny), self.end_node)
                        came_from[next_state] = (cx, cy, frozenset(c_violated))
                        heapq.heappush(frontier, (priority, new_g, nx, ny, new_violated))

        return None, set()

    def solve_all_scenarios(self):
        """
        Runs the optimizer for Tolerance 0, 1, and 2 independently.
        Stores the best result for each in self.solutions.
        """
        # Reset solutions container
        self.solutions = {}
        for t in range(3):
            self.solutions[t] = {
                'score': 0, 'found': False,
                'path': [], 'width': 0, 'sacrificed': set()
            }

        # Optimization Loop
        # Check Widths 0 to 8
        for width in range(0, 9):
            # Check Tolerances 0 to 2
            for tolerance in range(3):

                path, sacrificed = self.run_weighted_astar(width, tolerance)

                if path:
                    missed = len(sacrificed)
                    length = len(path)
                    score = self.calculate_score(length, width, missed)

                    # Update if this is the best score for THIS tolerance level
                    if score > self.solutions[tolerance]['score']:
                        self.solutions[tolerance] = {
                            'score': score,
                            'found': True,
                            'path': path,
                            'width': width,
                            'sacrificed': sacrificed
                        }

    def get_render_data_for_tolerance(self, tolerance_index):
        """
        Returns grid and stats for a specific optimization result.
        """
        sol = self.solutions.get(tolerance_index)
        if not sol or not sol['found']:
            # Return empty grid if no path found
            return [[self.TILE_EMPTY] * self.WIDTH for _ in range(self.HEIGHT)], 0, 0, 0, False

        path = sol['path']
        width = sol['width']
        sacrificed_ids = sol['sacrificed']
        score = sol['score']

        display_grid = [[self.TILE_EMPTY for _ in range(self.WIDTH)] for _ in range(self.HEIGHT)]

        # 1. Base Map
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                tile = self.grid[y][x]

                if tile == self.TILE_MINE_VISIBLE:
                    display_grid[y][x] = self.OUT_MINE_VISIBLE
                elif tile == self.TILE_MINE_HIDDEN:
                    display_grid[y][x] = self.OUT_MINE_HIDDEN
                elif tile == self.TILE_OBSTACLE:
                    display_grid[y][x] = self.OUT_OBSTACLE
                else:
                    vis_dist = self.distance_field_visible.get((x, y), 999)

                    if vis_dist <= width:
                        m_id = self.mine_id_map.get((x, y), -1)
                        if m_id in sacrificed_ids:
                            display_grid[y][x] = self.OUT_MISSED_ZONE
                        else:
                            display_grid[y][x] = self.OUT_DANGER_VISIBLE
                    else:
                        dist_all = self.distance_field_all.get((x, y), 999)
                        if dist_all <= width:
                            display_grid[y][x] = self.OUT_DANGER_HIDDEN
                        elif tile == self.TILE_UNSURE:
                            display_grid[y][x] = self.OUT_UNSURE

        # 2. Path & Stats
        violations = 0
        if path:
            for (px, py) in path:
                display_grid[py][px] = self.OUT_SAFE_PATH
                if self.distance_field_all.get((px, py), 999) <= width:
                    violations += 1

        return display_grid, violations, score, width, True