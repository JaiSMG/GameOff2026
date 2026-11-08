from collections import deque
import pygame
import random
import math

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
    _layer = 2  # draw order: tiles 0, pickups 1, player 2, held weapon 3

    def __init__(self, sprites, x, y, speed, world):
        super().__init__()

        self.pos = pygame.Vector2(x, y)
        self.speed = speed

        # The dungeon grid (world[row][col]); 1 = wall
        self.world = world

        # Collision hitbox: smaller than the sprite so the player
        # can fit through 1-tile-wide corridors without needing
        # pixel-perfect alignment.
        self.hitbox_size = 36
        self.hitbox_offset = (global_scale - self.hitbox_size) // 2
        self.hitbox = pygame.Rect(
            0, 0, self.hitbox_size, self.hitbox_size
        )
        self.sync_hitbox()

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
        self.max_weapons = 3
        self.weapons = []  # list of Weapon objects
        self.current = 0  # index of the equipped weapon
        self.attack_timer = 0  # counts down to 0

    @property
    def weapon(self):
        # The equipped weapon, or None if the inventory is empty
        if not self.weapons:
            return None
        return self.weapons[self.current]

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

    # --------------------
    # Weapons & Inventory
    # --------------------
    def cycle_weapon(self, step):
        if len(self.weapons) > 1:
            self.current = (self.current + step) % len(self.weapons)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_e:
                self.cycle_weapon(1)
            elif event.key == pygame.K_q:
                self.cycle_weapon(-1)
            elif pygame.K_1 <= event.key <= pygame.K_9:
                slot = event.key - pygame.K_1
                if slot < len(self.weapons):
                    self.current = slot

        elif event.type == pygame.MOUSEWHEEL:
            self.cycle_weapon(-event.y)  # scroll up = previous

    def pick_up(self, weapon):
        if len(self.weapons) < self.max_weapons:
            self.weapons.append(weapon)
            self.current = len(self.weapons) - 1  # equip the new one
            return None
        dropped = self.weapons[self.current]
        self.weapons[self.current] = weapon
        return dropped  # caller spawns this on the floor

    def attack(self):
        # Start an attack if a weapon is equipped and the cooldown is over.
        # HeldWeapon reads attack_timer to animate the swing.
        if self.weapon and self.attack_timer == 0:
            self.attack_timer = self.weapon.cooldown
            # TODO: when enemies exist, create the damage hitbox here
            # using self.weapon.damage

    # --------------------
    # Collision helpers
    # --------------------

    def sync_hitbox(self):
        # Place the hitbox centered inside the sprite
        self.hitbox.x = round(self.pos.x) + self.hitbox_offset
        self.hitbox.y = round(self.pos.y) + self.hitbox_offset

    def is_wall(self, col, row):
        # Anything outside the map counts as solid
        if not (0 <= row < len(self.world) and 0 <= col < len(self.world[0])):
            return True

        return self.world[row][col] == 1

    def nearby_walls(self):
        # Only check the tiles the hitbox actually overlaps
        left = self.hitbox.left // global_scale
        right = (self.hitbox.right - 1) // global_scale
        top = self.hitbox.top // global_scale
        bottom = (self.hitbox.bottom - 1) // global_scale

        walls = []

        for row in range(top, bottom + 1):
            for col in range(left, right + 1):
                if self.is_wall(col, row):
                    walls.append(pygame.Rect(
                        col * global_scale,
                        row * global_scale,
                        global_scale,
                        global_scale
                    ))

        return walls

    def move_axis(self, amount, axis):
        if amount == 0:
            return

        # Move along one axis only
        if axis == "x":
            self.pos.x += amount
        else:
            self.pos.y += amount

        self.sync_hitbox()

        # Push the hitbox back out of any wall it entered
        for wall in self.nearby_walls():
            if not self.hitbox.colliderect(wall):
                continue

            if axis == "x":
                if amount > 0:
                    self.hitbox.right = wall.left
                else:
                    self.hitbox.left = wall.right

                self.pos.x = self.hitbox.x - self.hitbox_offset

            else:
                if amount > 0:
                    self.hitbox.bottom = wall.top
                else:
                    self.hitbox.top = wall.bottom

                self.pos.y = self.hitbox.y - self.hitbox_offset

    def update(self, dt):
        # Cooldown counts down to 0, then the next attack is allowed
        self.attack_timer = max(0, self.attack_timer - dt)

        # Hold left mouse to keep attacking
        if pygame.mouse.get_pressed()[0]:
            self.attack()

        direction = self.handle_input()
        movement = direction * self.speed * dt

        # Move and resolve each axis separately so the player
        # slides along walls instead of sticking to them
        self.move_axis(movement.x, "x")
        self.move_axis(movement.y, "y")

        # Keep player inside the world
        self.pos.x = max(
            0, min(self.pos.x, GAME_WIDTH - self.rect.width)
        )

        self.pos.y = max(
            0, min(self.pos.y, GAME_HEIGHT - self.rect.height)
        )

        self.sync_hitbox()
        self.rect.topleft = (round(self.pos.x), round(self.pos.y))


# --------------------
# Weapons
# --------------------

class Weapon:
    """Plain data: what a weapon is. Not a sprite."""

    def __init__(self, name, damage, cooldown, icon_path=None,
                 held_path=None, color=(200, 200, 200),
                 held_size=(50, 14), style="slash"):
        self.name = name
        self.damage = damage
        self.cooldown = cooldown  # seconds between attacks

        # Attack animation: "slash", "stab" or "chop" (see strike_pose)
        self.style = style

        # Hotbar / floor icon (square)
        self.icon = self.load_image(icon_path, (40, 40), color)

        # Image drawn in the player's hand. Draw the art pointing RIGHT,
        # because HeldWeapon rotates it toward the mouse.
        self.held_image = self.load_image(
            held_path or icon_path, held_size, color
        )

    @staticmethod
    def load_image(path, size, fallback_color):
        # Use the real art if the file exists, otherwise a colored
        # placeholder so the game still runs without weapon graphics.
        if path:
            try:
                image = pygame.image.load(path).convert_alpha()
                return pygame.transform.scale(image, size)
            except (pygame.error, FileNotFoundError):
                pass

        surface = pygame.Surface(size, pygame.SRCALPHA)
        surface.fill(fallback_color)
        pygame.draw.rect(surface, (0, 0, 0), surface.get_rect(), 2)
        return surface


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out(t):
    # Fast at the start, slows to a stop (cubic)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    # Slow start, fast middle, slow end (smoothstep)
    return t * t * (3 - 2 * t)


def attack_pose(style, progress):
    """Return (angle_offset_degrees, reach_offset_px) for an attack.

    progress runs 0 -> 1 over the weapon's cooldown. Positive angle
    offsets rotate the weapon counterclockwise on screen. The last 20%
    eases back to the resting pose so the weapon never snaps back.
    """
    recovery_start = 0.8

    if progress <= recovery_start:
        return strike_pose(style, progress / recovery_start)

    angle, reach = strike_pose(style, 1.0)
    t = ease_in_out((progress - recovery_start) / (1 - recovery_start))
    return lerp(angle, 0, t), lerp(reach, 0, t)


def strike_pose(style, progress):
    # The attack itself, with progress 0 -> 1
    if style == "stab":
        # Pull back for the first 30%, then drive forward and return
        if progress < 0.3:
            return 0, lerp(0, -10, progress / 0.3)
        t = (progress - 0.3) / 0.7
        return 0, -10 + 55 * math.sin(math.pi * t)

    if style == "chop":
        # Lift the weapon up and back, then slam it down hard
        if progress < 0.35:
            t = ease_in_out(progress / 0.35)
            return lerp(0, 80, t), lerp(0, -6, t)
        t = ease_out((progress - 0.35) / 0.65)
        return lerp(80, -60, t), lerp(-6, 14, t)

    # "slash": brief wind-up, then a 140 degree arc with easing so it
    # whips through the middle
    if progress < 0.2:
        return lerp(0, 70, ease_in_out(progress / 0.2)), 0
    t = ease_in_out((progress - 0.2) / 0.8)
    return lerp(70, -110, t), 0


class HeldWeapon(pygame.sprite.Sprite):
    # World presence of whatever the player has equipped.
    _layer = 3

    def __init__(self, player, camera, *groups):
        super().__init__(*groups)
        self.player = player
        self.camera = camera
        self.reach = 30  # px from player center to weapon center

        self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
        self.rect = self.image.get_rect()

    def update(self, dt):
        weapon = self.player.weapon

        # Nothing equipped: draw nothing
        if weapon is None:
            self.image = pygame.Surface((1, 1), pygame.SRCALPHA)
            return

        # Mouse is in screen space; add the camera offset for world space
        mouse = pygame.Vector2(pygame.mouse.get_pos()) + self.camera.offset
        center = pygame.Vector2(self.player.rect.center)

        aim = mouse - center
        if aim.length_squared() == 0:
            return
        aim = aim.normalize()

        # pygame's y axis points down and rotate() is counterclockwise,
        # so the angle is negated
        angle = -pygame.Vector2(1, 0).angle_to(aim)

        # Attack animation, chosen by the weapon's style
        reach = self.reach
        if self.player.attack_timer > 0 and weapon.cooldown > 0:
            progress = 1 - self.player.attack_timer / weapon.cooldown
            progress = max(0, min(1, progress))

            angle_offset, reach_offset = attack_pose(weapon.style, progress)

            # Mirror the swing when aiming left so it matches the flipped image
            if aim.x < 0:
                angle_offset = -angle_offset

            angle += angle_offset
            reach += reach_offset

        image = weapon.held_image
        # Avoid an upside-down sprite when aiming left
        if aim.x < 0:
            image = pygame.transform.flip(image, False, True)

        self.image = pygame.transform.rotate(image, angle)
        self.rect = self.image.get_rect(center=center + aim * reach)


class WeaponPickup(pygame.sprite.Sprite):
    """A weapon lying on the floor. Holds a Weapon as its data."""
    _layer = 1

    def __init__(self, weapon, center, *groups):
        super().__init__(*groups)
        self.weapon = weapon
        self.image = weapon.icon
        self.rect = self.image.get_rect(center=center)


def try_pickup(player, pickups, *groups):
    # Pick up the first pickup the player is standing on. If the
    # inventory is full, the equipped weapon is swapped onto the floor.
    for pickup in pickups:
        if pickup.rect.colliderect(player.hitbox):
            dropped = player.pick_up(pickup.weapon)
            pickup.kill()

            if dropped is not None:
                WeaponPickup(dropped, player.rect.center, *groups)

            return


def draw_hotbar(surface, player, font):
    slot_size = 50
    gap = 6
    total = player.max_weapons * slot_size + (player.max_weapons - 1) * gap
    start_x = (SCREEN_WIDTH - total) // 2
    y = SCREEN_HEIGHT - slot_size - 10

    for i in range(player.max_weapons):
        x = start_x + i * (slot_size + gap)
        rect = pygame.Rect(x, y, slot_size, slot_size)

        pygame.draw.rect(surface, (30, 30, 30), rect)

        border = (255, 220, 80) if i == player.current else (90, 90, 90)
        pygame.draw.rect(surface, border, rect, 3)

        if i < len(player.weapons):
            icon = player.weapons[i].icon
            surface.blit(icon, icon.get_rect(center=rect.center))

        number = font.render(str(i + 1), True, (200, 200, 200))
        surface.blit(number, (x + 4, y + 2))

    # Name of the equipped weapon above the hotbar
    if player.weapon:
        label = font.render(player.weapon.name, True, (255, 255, 255))
        surface.blit(label, label.get_rect(midbottom=(SCREEN_WIDTH // 2, y - 4)))


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
        self.remove_dead_ends(grid, room_mask)

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

    def remove_dead_ends(self, grid, room_mask):

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


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, pattern, sprite):
        pass


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
    300,
    world
)

# LayeredUpdates draws by each sprite's _layer, so pickups sit under
# the player and the held weapon sits on top
renderable = pygame.sprite.LayeredUpdates()
pickups = pygame.sprite.Group()

tilemap = TileMap(renderable, tile_images, world)
renderable.add(player)

camera = Camera(renderable)

held_weapon = HeldWeapon(player, camera, renderable)

# Test weapons. Pass icon_path= / held_path= to use real art; without
# them a colored placeholder is drawn.
sword = Weapon("Sword", 10, 0.4, held_size=(50, 50), icon_path="graphics/Weapons/Sword/Icon.png",
               held_path="graphics/Weapons/Sword/Held.png", style="slash")
axe = Weapon("Axe", 18, 0.8, held_size=(50, 50), icon_path="graphics/Weapons/Axe/Icon.png",
             held_path="graphics/Weapons/Axe/Held.png",
             style="chop")
dagger = Weapon("Dagger", 2, 0.2, held_size=(50, 50), icon_path="graphics/Weapons/Dagger/Icon.png",
                held_path="graphics/Weapons/Dagger/Held.png", style="stab")

player.pick_up(sword)
player.pick_up(axe)

# A dagger on the floor in the starting room (tile 7, 7)
WeaponPickup(
    dagger,
    (7 * global_scale + global_scale // 2, 7 * global_scale + global_scale // 2),
    renderable, pickups
)

# HUD
comic_sans = pygame.font.Font(None, 50)
hud_font = pygame.font.Font(None, 24)

# --------------------
# Game loop
# --------------------

while running:

    dt = clock.tick(60) / 1000

    # quit handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        player.handle_event(event)

        # F picks up the weapon you're standing on
        if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
            try_pickup(player, pickups, renderable, pickups)

    # update
    renderable.update(dt)

    camera.update(player)

    # draw
    screen.fill((0, 0, 0))

    camera.draw(screen)

    draw_hotbar(screen, player, hud_font)

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
