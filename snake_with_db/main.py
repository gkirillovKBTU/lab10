import pygame, sys
import random
import time
from functools import partial
from db_manager import database_init, get_user_data, add_user, add_score, update_user_score
from objects import UserObject
from abc import ABC, abstractmethod

pygame.init()
FPS = 60
FramePerSec = pygame.time.Clock()

# Predefined some colors
BLUE  = (0, 0, 255)
RED   = (255, 0, 0)
GREEN = (0, 255, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# Screen information
SCREEN_WIDTH = 600
SCREEN_HEIGHT = 600
INIT_SCORE = 0
INIT_LEVEL = 1
SNAKE_INITIAL_LENGTH = 75

DISPLAYSURF = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Game")

appState = dict(
    speed=1,
    RUN=True,
    window_size=SNAKE_INITIAL_LENGTH,
    score=INIT_SCORE,
    level=INIT_LEVEL,
    PAUSED=False
)


font_small = pygame.font.SysFont("Verdana", 20)
font = pygame.font.SysFont("Verdana", 60)
game_over = font.render("Game Over", True, 'white')
CREATE_FRUIT = pygame.USEREVENT + 1
pygame.time.set_timer(CREATE_FRUIT, 1500)

font_small = pygame.font.SysFont("Verdana", 20)
font = pygame.font.SysFont("Verdana", 60)

snakeHeadImage = pygame.image.load("snakeout.png")
fruitImage = pygame.image.load("appleout.png")

BASIC_BORDERS = [pygame.Rect(0, 0, SCREEN_WIDTH, 10),
                 pygame.Rect(0, 0, 10, SCREEN_HEIGHT),
                 pygame.Rect(SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT),
                 pygame.Rect(0, SCREEN_HEIGHT - 10, SCREEN_WIDTH, 10)]

SHORT_HORIZONTAL_BORDER = lambda left, top: pygame.Rect(left, top, SCREEN_WIDTH // 3, 10)
LONG_HORIZONTAL_BORDER = lambda left, top: pygame.Rect(left, top, SCREEN_WIDTH, 10)
SHORT_VERTICAL_BORDER = lambda left, top: pygame.Rect(left, top, 10, SCREEN_HEIGHT // 3)
LONG_VERTICAL_BORDER = lambda left, top: pygame.Rect(left, top, 10, SCREEN_HEIGHT)

LEVELS = [
    # Level 1: Basic border
    BASIC_BORDERS,

    # Level 2: Diagonal pattern
    BASIC_BORDERS + [
        pygame.Rect(SCREEN_WIDTH//4, 0, 10, SCREEN_HEIGHT//2),
        pygame.Rect(SCREEN_WIDTH//2, SCREEN_HEIGHT//2, 10, SCREEN_HEIGHT//2),
        pygame.Rect(3*SCREEN_WIDTH//4, 0, 10, SCREEN_HEIGHT//2)
    ],

    # Level 3: Cross pattern
    BASIC_BORDERS + [
        pygame.Rect(SCREEN_WIDTH//2 - 5, 100, 10, SCREEN_HEIGHT - 200),
        pygame.Rect(100, SCREEN_HEIGHT//2 - 5, SCREEN_WIDTH - 200, 10)
    ],

    # Level 4: Box pattern
    BASIC_BORDERS + [
        SHORT_HORIZONTAL_BORDER(left=100, top=100),
        LONG_HORIZONTAL_BORDER(left=200, top=200),
        SHORT_VERTICAL_BORDER(left=100, top=300),
        SHORT_VERTICAL_BORDER(left=400, top=400),
        SHORT_VERTICAL_BORDER(left=500, top=300),
    ],

    # Level 5: Maze-like pattern
    BASIC_BORDERS + [
        SHORT_HORIZONTAL_BORDER(left=50, top=100),
        SHORT_HORIZONTAL_BORDER(left=50, top=300),
        SHORT_VERTICAL_BORDER(left=50, top=275),
        SHORT_VERTICAL_BORDER(left=250, top=0),

        SHORT_HORIZONTAL_BORDER(left=350, top=300),
        SHORT_HORIZONTAL_BORDER(left=350, top=500),
        SHORT_VERTICAL_BORDER(left=350, top=200),
        SHORT_VERTICAL_BORDER(left=550, top=400),

        SHORT_VERTICAL_BORDER(left=450, top=50),
    ]
]


# Try to use State pattern
class SnakeHead(pygame.sprite.Sprite):

    def __init__(self, x, y):
        super().__init__() 
        self.image = snakeHeadImage
        self.rect = self.image.get_rect(center=(x, y))
        self.current_state = 'DOWN'
        self.tail = self

    def change_direction(self):
        pressed_keys = pygame.key.get_pressed()
        if pressed_keys[pygame.K_UP]:
            if self.current_state != "DOWN":
                self.image = pygame.transform.rotate(snakeHeadImage, 180)
                self.current_state = 'UP'
        if pressed_keys[pygame.K_DOWN]:
            if self.current_state != 'UP':
                self.image = pygame.transform.rotate(snakeHeadImage, 0)
                self.current_state = 'DOWN'

        if pressed_keys[pygame.K_LEFT]:
            if self.current_state != 'RIGHT':
                self.image = pygame.transform.rotate(snakeHeadImage, -90)
                self.current_state = 'LEFT'

        if pressed_keys[pygame.K_RIGHT]:
            if self.current_state != 'LEFT':
                self.image = pygame.transform.rotate(snakeHeadImage, 90)
                self.current_state = 'RIGHT'

    def leave_point(self):
        cur_center = self.rect.center
        point = CollisionPoint(cur_center[0], cur_center[1], self.current_state)

        return point

    def move(self):

        self.rect.move_ip(get_movement(self.current_state))
        # self.rect.x = max(0, min(self.rect.x, SCREEN_WIDTH - self.rect.width))
        # self.rect.y = max(0, min(self.rect.y, SCREEN_HEIGHT - self.rect.height))
        # if self.rect.x > SCREEN_WIDTH or self.rect.x < 0 or \
        #    self.rect.y > SCREEN_WIDTH or self.rect.y < 0:
        #     game_over_handler()
# lifetime, weight randomly initialized separately 
# litetime, weight - initialiazation logic - keep it in __init__

class Fruit(pygame.sprite.Sprite):
    def __init__(self, lifetime=None, weight=None):
        super().__init__() 
        self.image = fruitImage
        self.rect = self.image.get_rect()
        self.rect.center = (random.randint(40,SCREEN_WIDTH-40),random.randint(40, SCREEN_HEIGHT-40))

        self.appear_time = pygame.time.get_ticks()
        self.lifetime = (random.randint(5000, 8000)
                         if lifetime is None else lifetime)

        self.weight = (random.randint(1, 5) if weight is None else weight)

    def update(self):
        if pygame.time.get_ticks() - self.appear_time > self.lifetime:
            self.kill()


class CollisionPoint(pygame.sprite.Sprite):
    def __init__(self, x, y, state):
        super().__init__()
        self.image = pygame.Surface((5, 5), pygame.SRCALPHA)  # Small point
        self.image.fill((0, 255, 0, 255))
        self.change_state = state
        self.rect = self.image.get_rect(center=(x, y))


def get_sign(n): return (n > 0) - (n < 0)


def get_movement(state):
    match state:
        case 'UP':
            return (0, -appState.get('speed'))
        case 'DOWN':
            return (0, appState.get('speed'))
        case 'RIGHT':
            return (appState.get('speed'), 0)
        case 'LEFT':
            return (-appState.get('speed'), 0)


class Scene:
    def __init__(self, manager):
        self.manager = manager

    def handle_events(self, events):
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass

# Weak command pattern
class SceneManager:
    def __init__(self):
        self.scenes = {}
        self.current_scene = None
        self.user_data = None

    def add_scene(self, name, scene):
        self.scenes[name] = scene

    def switch_scene(self, name):
        if name in self.scenes:
            self.current_scene = self.scenes[name]

    def handle_events(self, events):
        if self.current_scene:
            self.current_scene.handle_events(events)

    def update(self):
        if hasattr(self.current_scene, 'update') and callable(self.current_scene.update):
            self.current_scene.update()

    def draw(self, screen):
        if self.current_scene:
            self.current_scene.draw(screen)

    def set_user_data(self, user_data):
        self.user_data = user_data


class IUpdatable(ABC):
    @abstractmethod
    def update(self):
        pass


class IGameEntityFactory(ABC):
    @abstractmethod
    def create_snake_head(self):
        pass

    @abstractmethod
    def create_fruit(self):
        pass


class DefaultGameEntityFactory(IGameEntityFactory):

    def create_snake_head(self):
        return SnakeHead(*DISPLAYSURF.get_rect().center)

    def create_fruit(self):
        return Fruit()


class StartMenu(Scene):
    def __init__(self, manager):
        super().__init__(manager)
        self.username = ""

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.username:
                    user_data = get_user_data(self.username)
                    if not user_data:
                        user_id = add_user(self.username)
                        add_score(user_id, 0)
                        user_data = get_user_data(self.username)
                    self.manager.switch_scene("gameplay")
                    self.manager.set_user_data(UserObject(*user_data[0]))
                elif event.key == pygame.K_BACKSPACE:
                    self.username = self.username[:-1]
                elif event.unicode.isalnum() and len(self.username) < 20:
                    self.username += event.unicode

    def draw(self, screen):
        screen.fill((30, 30, 30))
        font = pygame.font.Font(None, 50)
        label_text = font.render("Input your username", True, (255, 255, 255))
        username_text = font.render(self.username, True, (255, 255, 255)) # True enables anti-aliasing
        screen.blit(label_text, (200, 250))
        screen.blit(username_text, (200, 300))
    

class GameplayScene(Scene, IUpdatable):
    def __init__(self, manager):
        super().__init__(manager)
        self.S1 = SnakeHead(*DISPLAYSURF.get_rect().center)
        self.fruits = pygame.sprite.Group()
        self.collision_points = pygame.sprite.Group()
        self.bodyWindow = list()
        self.all_sprites = pygame.sprite.Group()
        self.all_sprites.add(self.S1)

    def handle_events(self, events):
        for event in events:              
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    appState['PAUSED'] = not appState['PAUSED']
            if event.type == CREATE_FRUIT and len(self.fruits) < 5:
                fruit = Fruit()
                self.fruits.add(fruit)

    def update(self):

        self.S1.change_direction()
        self.S1.move()
        col_point = self.S1.leave_point()
        self.collision_points.add(col_point)
        self.bodyWindow.append(col_point)

        self.bodyWindow = self.bodyWindow[-appState.get('window_size'):]

        if pygame.sprite.spritecollideany(self.S1, self.fruits):
            # self.manager.user_data['score'] += random.randint(1, 3)
            appState['window_size'] = self.manager.user_data.score*5 + SNAKE_INITIAL_LENGTH
        
        for point in self.collision_points:
            if point not in self.bodyWindow:
                point.kill()

        for collide_point in self.bodyWindow[:-50]:
            # if pygame.sprite.collide_rect(collide_point, S1):
            #     game_over_handler()
            if collide_point.rect.collidepoint(self.S1.rect.center):
                game_over_handler()

        for fruit in self.fruits:
            if pygame.sprite.collide_rect(fruit, self.S1):
                self.manager.user_data.score += fruit.weight
                fruit.kill()
            fruit.update()
    
        LEVEL = self.manager.user_data.score // 10 + 1
        self.manager.user_data.level = LEVEL

        appState['speed'] = 0 if appState['PAUSED'] else LEVEL

    def draw(self, screen):
        screen.fill('black')
        screen.blit(self.S1.image, self.S1.rect)

        score = font_small.render(str(self.manager.user_data.score), True, 'yellow')
        screen.blit(score, (SCREEN_WIDTH - 30, 10))

        self.collision_points.draw(screen)

        for point in self.collision_points:
            if point not in self.bodyWindow:
                point.kill()

        for collide_point in self.bodyWindow[:-50]:
            if collide_point.rect.collidepoint(self.S1.rect.center):
                game_over_handler()
        # for fruit in self.fruits:
        #     screen.blit(fruit.image, fruit.rect)
        self.fruits.draw(screen)

        for border in LEVELS[self.manager.user_data.level - 1]:
            pygame.draw.rect(screen, WHITE, border)

        level_display = font_small.render(f"Level:{self.manager.user_data.level:<3}", True, 'green')
        screen.blit(level_display, (30, 10))


def game_over_handler(screen=DISPLAYSURF):
    screen.fill(RED)
    screen.blit(game_over, (60,250))
    pygame.display.update()
    for sprite in scene_manager.current_scene.all_sprites:
        sprite.kill()
    appState['RUN'] = False


if __name__ == "__main__":
    database_init()
    scene_manager = SceneManager()
    scene_manager.add_scene('start_menu', StartMenu(scene_manager))
    scene_manager.add_scene('gameplay', GameplayScene(scene_manager))
    scene_manager.switch_scene('start_menu')

    while appState['RUN']:
        events = pygame.event.get()
        scene_manager.handle_events(events)
        scene_manager.update()
        scene_manager.draw(DISPLAYSURF)

        pygame.display.flip()
        FramePerSec.tick(FPS)

    # Save user data to database
    update_user_score(scene_manager.user_data.id, scene_manager.user_data.score, scene_manager.user_data.level)
