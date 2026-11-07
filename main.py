from collections import deque
import pygame
import random

# --------------------
# Pygame setup
# --------------------

SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600

global_scale = 60

WORLD_COLS = 100
WORLD_ROWS = 100

GAME_WIDTH = WORLD_COLS * global_scale
GAME_HEIGHT = WORLD_ROWS * global_scale

pygame.init()

screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT),
    pygame.SCALED | pygame.RESIZABLE
)

pygame.display.set_caption("Dungeon Generator")

clock = pygame.time.Clock()
running = True


# --------------------
# Player
# --------------------

class Player(pygame.sprite.Sprite):
    def __init__(self, sprites, x, y, speed):
        super().__init__()

        self.pos = pygame.Vector2(x, y)
        self.speed = speed

        # Load idle sprite and its flipped version
        idle = pygame.image.load(sprites[0]).convert_alpha()
        idle = pygame.transform.scale(
            idle, (global_scale, global_scale)
        )

        self.sprites = [
            idle,
            pygame.transform.flip(idle, True, False)
        ]

        self.image = self.sprites[0]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)

    def handle_input(self):
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(0, 0)

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            direction.x -= 1
            self.image = self.sprites[1]

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            direction.x += 1
            self.image = self.sprites[0]

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            direction.y -= 1

        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            direction.y += 1

        if direction.length_squared() > 0:
            direction = direction.normalize()

        return direction

    def update(self, dt):
        direction = self.handle_input()

        self.pos += direction * self.speed * dt

        # Keep player inside the world
        self.pos.x = max(
            0, min(self.pos.x, GAME_WIDTH - self.rect.width)
        )

        self.pos.y = max(
            0, min(self.pos.y, GAME_HEIGHT - self.rect.height)
        )

        self.rect.topleft = (int(self.pos.x), int(self.pos.y))


# --------------------
# Camera
# --------------------

class Camera:
    def __init__(self, group):
        self.group = group
        self.offset = pygame.Vector2(0, 0)

    def update(self, target):
        self.offset.x = target.rect.centerx - SCREEN_WIDTH // 2
        self.offset.y = target.rect.centery - SCREEN_HEIGHT // 2

    def draw(self, surface):
        for sprite in self.group:
            screen_pos = sprite.rect.topleft - self.offset
            surface.blit(sprite.image, screen_pos)


# --------------------
# Tiles and Tilemap
# --------------------

class Tile(pygame.sprite.Sprite):
    def __init__(self, image, x, y):
        super().__init__()

        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))


class TileMap:
    def __init__(self, group, tiles, layout):
        self.group = group
        self.tile_size = global_scale

        self.tiles = {}

        # Load and scale tile images
        for tile_id, path in tiles.items():
            image = pygame.image.load(path).convert_alpha()

            image = pygame.transform.scale(
                image, (self.tile_size, self.tile_size)
            )

            self.tiles[tile_id] = image

        # Convert the 2D grid into sprites
        for row, tiles_in_row in enumerate(layout):
            for col, tile_id in enumerate(tiles_in_row):

                x = col * self.tile_size
                y = row * self.tile_size

                tile = Tile(self.tiles[tile_id], x, y)
                self.group.add(tile)

        self.width = len(layout[0]) * self.tile_size
        self.height = len(layout) * self.tile_size


# --------------------
# Dungeon generation
# --------------------


class Dungeon:
    def __init__(self, width, height):
        self.width = width
        self.height = height

        # 0 = floor / corridor
        # 1 = wall
        # 2 = blank (not used by this generation method)

        self.world = [
            [1 for _ in range(width)]
            for _ in range(height)
        ]

        self.rooms = []

    # --------------------
    # Room creation
    # --------------------

    def room(self, width, height, x, y):

        for row in range(height):
            for col in range(width):

                world_x = x + col
                world_y = y + row

                # Room borders
                if (
                    row == 0 or
                    row == height - 1 or
                    col == 0 or
                    col == width - 1
                ):
                    self.world[world_y][world_x] = 1

                # Room interior
                else:
                    self.world[world_y][world_x] = 0

        self.rooms.append((x, y, width, height))

    # --------------------
    # Random room placement
    # --------------------

    def generate_rooms(self):

        # Starting room
        self.room(10, 10, 0, 0)

        # Make a fixed number of placement attempts
        room_attempts = 200

        for _ in range(room_attempts):

            rwidth = random.randint(6, 12)
            rheight = random.randint(6, 12)

            rx = random.randint(1, self.width - rwidth - 1)
            ry = random.randint(1, self.height - rheight - 1)

            overlapping = False

            for room in self.rooms:
                ox, oy, ow, oh = room

                # Check overlap, including a one-tile gap
                if (
                    rx < ox + ow + 1 and
                    rx + rwidth + 1 > ox and
                    ry < oy + oh + 1 and
                    ry + rheight + 1 > oy
                ):
                    overlapping = True
                    break

            if not overlapping:
                self.room(rwidth, rheight, rx, ry)

        print("Generated rooms:", len(self.rooms))

    # --------------------
    # Create room mask
    # --------------------

    def create_room_mask(self):

        mask = [
            [False for _ in range(self.width)]
            for _ in range(self.height)
        ]

        for x, y, width, height in self.rooms:

            for row in range(y, y + height):
                for col in range(x, x + width):
                    mask[row][col] = True

        return mask

    # --------------------
    # Maze generation
    # --------------------

    def generate_maze(self):

        # Start with the existing rooms and walls
        grid = [row[:] for row in self.world]

        room_mask = self.create_room_mask()

        # Directions: up, down, left, right
        directions = [
            (-2, 0),
            (2, 0),
            (0, -2),
            (0, 2)
        ]

        # Check every possible maze starting position
        for start_row in range(1, self.height - 1, 2):
            for start_col in range(1, self.width - 1, 2):

                # Skip rooms and already generated corridors
                if (
                    room_mask[start_row][start_col] or
                    grid[start_row][start_col] == 0
                ):
                    continue

                # Start a new maze section
                path = [(start_row, start_col)]

                grid[start_row][start_col] = 0

                # Randomized DFS
                while path:

                    row, col = path[-1]

                    pickable = []

                    for dy, dx in directions:

                        new_row = row + dy
                        new_col = col + dx

                        middle_row = row + dy // 2
                        middle_col = col + dx // 2

                        # Check boundaries
                        if not (
                            0 < new_row < self.height - 1 and
                            0 < new_col < self.width - 1
                        ):
                            continue

                        # Don't enter rooms
                        if room_mask[new_row][new_col]:
                            continue

                        if room_mask[middle_row][middle_col]:
                            continue

                        # Only visit uncarved cells
                        if (
                            grid[new_row][new_col] == 1 and
                            grid[middle_row][middle_col] == 1
                        ):
                            pickable.append((new_row, new_col))

                    if pickable:

                        new_row, new_col = random.choice(pickable)

                        # Carve the wall between the cells
                        middle_row = (row + new_row) // 2
                        middle_col = (col + new_col) // 2

                        grid[middle_row][middle_col] = 0
                        grid[new_row][new_col] = 0

                        path.append((new_row, new_col))

                    else:
                        # Backtrack
                        path.pop()

        # Connect rooms to the maze
        self.connect_rooms(grid, room_mask)

        # Remove some dead ends
        self.remove_some_dead_ends(grid, room_mask)

        self.world = grid

        return grid

    # --------------------
    # Connect rooms
    # --------------------

    def connect_rooms(self, grid, room_mask):

        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1)
        ]

        for x, y, width, height in self.rooms:

            # Get all wall tiles around the room
            perimeter = set()

            for col in range(x, x + width):
                perimeter.add((y, col))
                perimeter.add((y + height - 1, col))

            for row in range(y + 1, y + height - 1):
                perimeter.add((row, x))
                perimeter.add((row, x + width - 1))

            # Find walls directly touching corridors
            connected = False

            for row, col in perimeter:

                for dy, dx in directions:

                    ny = row + dy
                    nx = col + dx

                    if not (
                        0 <= ny < self.height and
                        0 <= nx < self.width
                    ):
                        continue

                    if not room_mask[ny][nx] and grid[ny][nx] == 0:

                        # Open the room wall
                        grid[row][col] = 0
                        connected = True
                        break

            # If no corridor touches the room,
            # carve a short connector using BFS
            if not connected:

                queue = deque()
                parents = {}

                for position in perimeter:
                    queue.append(position)
                    parents[position] = None

                destination = None

                while queue:

                    row, col = queue.popleft()

                    # Found a maze corridor
                    if (
                        not room_mask[row][col] and
                        grid[row][col] == 0
                    ):
                        destination = (row, col)
                        break

                    for dy, dx in directions:

                        ny = row + dy
                        nx = col + dx

                        if not (
                            0 <= ny < self.height and
                            0 <= nx < self.width
                        ):
                            continue

                        if room_mask[ny][nx]:
                            continue

                        next_position = (ny, nx)

                        if next_position not in parents:
                            parents[next_position] = (row, col)
                            queue.append(next_position)

                # Carve the path from the room to the maze
                if destination is not None:

                    current = destination

                    while current is not None:

                        row, col = current
                        grid[row][col] = 0

                        current = parents[current]

    # --------------------
    # Remove some dead ends
    # --------------------

    def remove_some_dead_ends(self, grid, room_mask):

        dead_ends = []

        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1)
        ]

        # Find corridor tiles with only one floor neighbor
        for row in range(1, self.height - 1):
            for col in range(1, self.width - 1):

                if room_mask[row][col] or grid[row][col] != 0:
                    continue

                neighbors = 0

                for dy, dx in directions:
                    if grid[row + dy][col + dx] == 0:
                        neighbors += 1

                if neighbors == 1:
                    dead_ends.append((row, col))

        # Only remove a portion of the dead ends
        random.shuffle(dead_ends)

        amount_to_remove = len(dead_ends) // 4

        for row, col in dead_ends[:amount_to_remove]:

            # Check again because earlier removals may have
            # changed the number of neighboring floor tiles
            neighbors = 0

            for dy, dx in directions:
                if grid[row + dy][col + dx] == 0:
                    neighbors += 1

            if neighbors == 1:
                grid[row][col] = 1

# --------------------
# Main game setup
# --------------------

tile_images = {
    0: "graphics/Tileset/Stone/Floor.png",
    1: "graphics/Tileset/Stone/Wall.png",
    2: "graphics/Tileset/Stone/Blank.png"
}

# create dungeon
dungeon = Dungeon(WORLD_COLS, WORLD_ROWS)

dungeon.generate_rooms()
world = dungeon.generate_maze()

player = Player(
    [
        "graphics/Player/Idle.png",
        "graphics/Player/Walk1.png",
        "graphics/Player/Walk2.png"
    ],
    5 * global_scale,
    5 * global_scale,
    300
)

renderable = pygame.sprite.Group()

tilemap = TileMap(renderable, tile_images, world)
renderable.add(player)

camera = Camera(renderable)

# HUD
comic_sans = pygame.font.Font(None, 50)


# --------------------
# Game loop
# --------------------

while running:

    dt = clock.tick(60) / 1000

    # quit handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # update
    renderable.update(dt)

    camera.update(player)

    # draw
    screen.fill((0, 0, 0))

    camera.draw(screen)

    # display player tile coordinates
    position = (
        str(int(player.pos.x // global_scale)) +
        " , " +
        str(int(player.pos.y // global_scale))
    )

    ppos = comic_sans.render(position, True, (255, 255, 255))
    screen.blit(ppos, (0, 0))
    pygame.display.flip()

pygame.quit()