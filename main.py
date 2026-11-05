import pygame
import random

# pygame setup
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
GAME_WIDTH = SCREEN_WIDTH * 5
GAME_HEIGHT = SCREEN_HEIGHT * 5
global_scale = (SCREEN_HEIGHT + SCREEN_WIDTH) // 20
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.RESIZABLE)
pygame.display.set_caption("placeholder")
clock = pygame.time.Clock()
running = True


# ----------
class Player(pygame.sprite.Sprite):
    def __init__(self, sprites, x, y, speed):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pygame.Vector2(x, y)
        self.speed = speed
        self.xspeed = 0
        self.yspeed = 0
        self.sprites = []
        for i in range(len(sprites)):
            self.sprites.append(pygame.transform.scale(pygame.image.load(sprites[i]), (global_scale, global_scale)))
        placeholder = pygame.image.load(sprites[0])
        self.sprites.insert(1, pygame.transform.scale(pygame.transform.flip(placeholder, True, False),
                                                      (global_scale, global_scale)))
        self.image = pygame.image.load(sprites[0])
        self.image = pygame.transform.scale(self.image, (global_scale, global_scale))
        self.rect = self.image.get_rect()
        self.rect.topleft = (self.pos.x, self.pos.y)
        self.width = global_scale
        self.height = global_scale

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

        self.pos.x = max(-GAME_WIDTH, min(self.pos.x, GAME_WIDTH - self.rect.width))
        self.pos.y = max(-GAME_HEIGHT, min(self.pos.y, GAME_HEIGHT - self.rect.height))

        self.rect.topleft = (int(self.pos.x), int(self.pos.y))

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect)


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


class Enemy(pygame.sprite.Sprite):
    def __init__(self, ):
        pygame.sprite.Sprite.__init__(self)
        # will be defined later on


class Tile(pygame.sprite.Sprite):
    def __init__(self, image, x, y):
        pygame.sprite.Sprite.__init__(self)
        self.image = image
        self.rect = self.image.get_rect(topleft=(x, y))


class TileMap:
    def __init__(self, group, tiles, layout):
        self.group = group
        self.tile_size = global_scale
        self.tiles = {}
        for tile_id, path in tiles.items():
            image = pygame.image.load(path).convert_alpha()
            image = pygame.transform.scale(image, (self.tile_size, self.tile_size))
            self.tiles[tile_id] = image
        for row, tiles_in_row in enumerate(layout):
            for col, tile_id in enumerate(tiles_in_row):
                x = col * self.tile_size
                y = row * self.tile_size

                tile = Tile(self.tiles[tile_id], x, y)
                self.group.add(tile)

        self.width = len(layout[0]) * self.tile_size
        self.height = len(layout) * self.tile_size


class Dungeon:
    def __init__(self, tile_images, game_width, game_height):
        self.tile_images = tile_images
        self.game_width = game_width
        self.game_height = game_height

        self.width = 100
        self.height = 100

        self.world = [
            [2 for _ in range(self.width)]
            for _ in range(self.height)
        ]

        self.rooms = []

    def room(self, width, height, x, y):
        for row in range(height):
            for col in range(width):

                world_x = x + col
                world_y = y + row

                if 0 <= world_x < self.width and 0 <= world_y < self.height:

                    if row == 0 or row == height - 1 or col == 0 or col == width - 1:
                        self.world[world_y][world_x] = 1
                    else:
                        self.world[world_y][world_x] = 0

        self.rooms.append((x, y, width, height))

    def generate_rooms(self):
        self.room(10, 10, 0, 0)

        number_of_rooms = random.randint(40, 50)

        for i in range(number_of_rooms):
            rwidth = random.randint(8, 20)
            rheight = random.randint(8, 20)

            rx = random.randint(0, self.width - rwidth)
            ry = random.randint(0, self.height - rheight)

            overlapping = False

            for r in self.rooms:
                # existing room boundaries
                ctl = (r[0] - 1, r[1] - 1)
                cbr = (r[0] + r[2] + 1, r[1] + r[3] + 1)

                # new room boundaries
                rtl = (rx - 1, ry - 1)
                rbr = (rx + rwidth + 1, ry + rheight + 1)

                # check whether the rooms overlap
                if (rtl[0] < cbr[0] and rbr[0] > ctl[0] and
                        rtl[1] < cbr[1] and rbr[1] > ctl[1]):
                    overlapping = True
                    break
                elif (rbr[0] > (GAME_WIDTH // global_scale) or rbr[1] > (GAME_HEIGHT // global_scale)):
                    overlapping = True
                    break

            if not overlapping:
                self.room(rwidth, rheight, rx, ry)

        #print(len(self.rooms), '-- : --', self.rooms)
        return self.world

    def generate_maze(self):
        cols = self.width
        rows = self.height

        # 0 = corridor, 1 = wall, 2 = room floor
        grid = [[1 for _ in range(cols)] for _ in range(rows)]

        # Mark room locations
        for room in self.rooms:
            x, y, width, height = room

            for row in range(y, y + height):
                for col in range(x, x + width):
                    grid[row][col] = 2

        # Find possible starting positions
        possible_starts = []

        for row in range(1, rows - 1, 2):
            for col in range(1, cols - 1, 2):
                if grid[row][col] == 1:
                    possible_starts.append((row, col))

        if not possible_starts:
            return grid

        # Choose starting position
        walker = random.choice(possible_starts)

        # Stack remembers positions for backtracking
        path = [walker]

        # Carve starting position
        grid[walker[0]][walker[1]] = 0

        # Directions: up, down, left, right
        directions = [
            (-2, 0),
            (2, 0),
            (0, -2),
            (0, 2)
        ]

        # Start walking
        while path:
            row, col = path[-1]

            # Find available directions
            pickable = []

            for dy, dx in directions:
                new_row = row + dy
                new_col = col + dx

                middle_row = row + dy // 2
                middle_col = col + dx // 2

                # Check boundaries and make sure neither tile
                # is a room or an already-carved corridor
                if (0 < new_row < rows - 1 and
                        0 < new_col < cols - 1 and
                        grid[new_row][new_col] == 1 and
                        grid[middle_row][middle_col] == 1):
                    pickable.append((new_row, new_col))

            if pickable:
                # Choose random direction
                new_row, new_col = random.choice(pickable)

                # Carve the wall between the two positions
                middle_row = (row + new_row) // 2
                middle_col = (col + new_col) // 2

                grid[middle_row][middle_col] = 0
                grid[new_row][new_col] = 0

                # Move walker and remember position
                path.append((new_row, new_col))

            else:
                # No available directions: backtrack
                path.pop()
        #print(grid)
        return grid


# ----------
renderable = pygame.sprite.Group()
player = Player(['graphics/Player/Idle.png',
                 'graphics/Player/Walk1.png',
                 'graphics/Player/Walk2.png'], 0, 0, 300)
tile_images = {
    0: "graphics/Tileset/Stone/Floor.png",
    1: 'graphics/Tileset/Stone/Wall.png',
    2: 'graphics/Tileset/Stone/Blank.png'
}
dungeon = Dungeon(tile_images, 100, 100)
dungeon.generate_rooms()
world = dungeon.generate_maze()
renderable = pygame.sprite.Group()
print(world)
tilemap = TileMap(renderable, tile_images, world)

renderable.add(player)

camera = Camera(renderable)
now = pygame.time.get_ticks()
comic_sans = pygame.font.Font(None, 50)
while running:
    dt = pygame.time.get_ticks() - now
    now = pygame.time.get_ticks()
    dt /= 1000
    # event handler
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # screen wipe
    screen.fill((0, 0, 0))
    renderable.update(dt)
    camera.update(player)
    camera.draw(screen)
    # hud
    position = str(player.pos[0] // global_scale) + ' , ' + str(player.pos[1] // global_scale)
    ppos = comic_sans.render(position, True, (255, 255, 255))
    screen.blit(ppos, (0, 0))
    pygame.display.flip()
    clock.tick(60)  # limits FPS to 60

pygame.quit()
