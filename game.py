import kivy
kivy.require('2.0.0')

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Rectangle, Color, Ellipse
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.uix.textinput import TextInput
import random
import numpy as np
from kivy.graphics.texture import Texture

import os
import json
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials, auth, db
from firebase_admin import firestore

# Load environment variables
load_dotenv()

# Initialize Firebase
firebase_credentials = {
    "type": os.getenv("FIREBASE_TYPE"),
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
    "universe_domain": os.getenv("FIREBASE_UNIVERSE_DOMAIN"),
}

cred = credentials.Certificate(firebase_credentials)
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://spaceshooter-4ca08-default-rtdb.firebaseio.com/'
})

time_left = 30
current_user = None

class GradientBackground(FloatLayout):
    #Creates a 45° gradient background that covers the entire window.
    def __init__(self, **kwargs):
        super(GradientBackground, self).__init__(**kwargs)
        # Initially set to Window size; will update later via on_size.
        self.size = Window.size
        self.pos = (0, 0)
        self.disabled = True  # So it doesn't intercept input
        with self.canvas:
            Color(1, 1, 1, 1)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        # Schedule the gradient creation once the widget is laid out.
        Clock.schedule_once(self.create_gradient, 0)
        self.bind(size=self.update_bg, pos=self.update_bg)

    def create_gradient(self, *args):
        width, height = int(self.width), int(self.height)
        # If width or height is 0, use a default value.
        if width == 0 or height == 0:
            width = height = 256
        size_val = max(width, height)
        data = np.zeros((size_val, size_val, 3), dtype=np.uint8)

        # Define colors (Blue to White)
        start_color = np.array([0, 102, 255])  # Blue
        end_color = np.array([255, 255, 255])    # White

        # Generate a diagonal (45°) gradient.
        for i in range(size_val):
            factor = i / size_val
            color = (1 - factor) * start_color + factor * end_color
            data[i, :, :] = color.astype(np.uint8)

        texture = Texture.create(size=(size_val, size_val))
        texture.blit_buffer(data.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        texture.flip_vertical()

        # Apply the texture.
        self.bg_rect.texture = texture
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

    def update_bg(self, *args):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size
        # Update the gradient texture when size changes.
        self.create_gradient()

class LoginScreen(FloatLayout):
   # User login and registration screen with centered, wider text boxes.
    def __init__(self, switch_callback, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.switch_callback = switch_callback
        
        # Add gradient background.
        self.add_widget(GradientBackground())
        
        # Centered UI elements using pos_hint.
        self.email_input = TextInput(
            hint_text="Email",
            size_hint=(None, None),
            size=(500, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.7}
        )
        self.password_input = TextInput(
            hint_text="Password",
            password=True,
            size_hint=(None, None),
            size=(500, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.62}
        )
        self.login_button = Button(
            text="Login",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.54},
            background_normal='',
            background_color=(19/255, 40/255, 77/255, 1)
        )
        self.register_button = Button(
            text="Register",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.46},
            background_normal='',
            background_color=(19/255, 40/255, 77/255, 1)
        )
        
        self.login_button.bind(on_press=self.login)
        self.register_button.bind(on_press=self.register)
        
        self.add_widget(self.email_input)
        self.add_widget(self.password_input)
        self.add_widget(self.login_button)
        self.add_widget(self.register_button)
    
    def login(self, instance):
        global current_user
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            print("Email and password cannot be empty")
            return
        try:
            user = auth.get_user_by_email(email)
            current_user = user.uid
            print("Login successful!")
            self.switch_callback()
        except Exception as e:
            print("Login failed:", e)
    
    def register(self, instance):
        email = self.email_input.text.strip()
        password = self.password_input.text.strip()
        if not email or not password:
            print("Email and password cannot be empty")
            return
        try:
            user = auth.create_user(email=email, password=password)
            db.reference(f'users/{user.uid}').set({'email': email, 'games': {}})
            print("User registered successfully")
        except Exception as e:
            print("Registration failed:", e)

class ModeSelection(FloatLayout):
    #Screen for selecting game mode with centered buttons.
    def __init__(self, start_game_callback, **kwargs):
        super(ModeSelection, self).__init__(**kwargs)
        self.start_game_callback = start_game_callback
        
        self.add_widget(GradientBackground())
        
        self.single_player_button = Button(
            text="Single Player",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.6},
            background_normal='',
            background_color=(19/255, 40/255, 77/255, 1)
        )
        self.multi_player_button = Button(
            text="Two Players",
            size_hint=(None, None),
            size=(200, 50),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            background_normal='',
            background_color=(19/255, 40/255, 77/255, 1)
        )
        
        self.single_player_button.bind(on_press=lambda x: self.start_game(1))
        self.multi_player_button.bind(on_press=lambda x: self.start_game(2))
        
        self.add_widget(self.single_player_button)
        self.add_widget(self.multi_player_button)
        
    def start_game(self, mode):
        self.start_game_callback(mode)

class ShootGame(FloatLayout):
    #Main shooting game logic with gradient background and keyboard handling.
    def __init__(self, mode, **kwargs):
        super(ShootGame, self).__init__(**kwargs)
        self.mode = mode
        
        self.add_widget(GradientBackground())
        
        # Request keyboard events.
        self._keyboard = Window.request_keyboard(self.on_keyboard_closed, self)
        if self._keyboard:
            self._keyboard.bind(on_key_down=self.on_key_down)
            self._keyboard.bind(on_key_up=self.on_key_up)
        
        self.player1 = Image(source='aim.png', size_hint=(None, None), size=(40, 40), pos=(100, 10))
        self.add_widget(self.player1)
        if self.mode == 2:
            self.player2 = Image(source='aim.png', size_hint=(None, None), size=(40, 40), pos=(300, 10))
            self.add_widget(self.player2)
        
        self.score1 = 0
        self.score_label1 = Label(text="Player 1: 0", size_hint=(None, None), pos=(50, 450))
        self.add_widget(self.score_label1)
        if self.mode == 2:
            self.score2 = 0
            self.score_label2 = Label(text="Player 2: 0", size_hint=(None, None), pos=(350, 450))
            self.add_widget(self.score_label2)
        
        self.timer_label = Label(text="Time: 30", size_hint=(None, None), pos=(220, 450))
        self.add_widget(self.timer_label)
        
        self.bullets = []
        self.balls = []
        self.new_ball()
        self.new_ball()
        
        Clock.schedule_interval(self.update, 1/120)
        Clock.schedule_interval(self.update_timer, 1)
    
    def on_keyboard_closed(self):
        if self._keyboard:
            self._keyboard.unbind(on_key_down=self.on_key_down)
            self._keyboard.unbind(on_key_up=self.on_key_up)
            self._keyboard = None
    
    def on_key_down(self, keyboard, keycode, text, modifiers):
        key = keycode[1]
        if key == 'left':
            self.player1.x = max(self.player1.x - 10, 0)
        elif key == 'right':
            self.player1.x = min(self.player1.x + 10, Window.width - self.player1.width)
        elif key == 'up':
            self.shoot_bullet(self.player1.x + self.player1.width / 2, self.player1.y + self.player1.height, 1)
        if self.mode == 2:
            if key == 'a':
                self.player2.x = max(self.player2.x - 10, 0)
            elif key == 'd':
                self.player2.x = min(self.player2.x + 10, Window.width - self.player2.width)
            elif key == 'w':
                self.shoot_bullet(self.player2.x + self.player2.width / 2, self.player2.y + self.player2.height, 2)
        return True
    
    def on_key_up(self, keyboard, keycode):
        return True
    
    def shoot_bullet(self, x, y, player):
        with self.canvas:
            Color(1, 1, 0, 1)
            bullet = Rectangle(pos=(x, y), size=(5, 15))
            self.bullets.append((bullet, player))
    
    def new_ball(self):
        x = random.randint(50, int(Window.width) - 50)
        with self.canvas:
            Color(1, 0, 0, 1)
            ball = Ellipse(pos=(x, 350), size=(20, 20))
            self.balls.append(ball)
    
    def update(self, dt):
        for bullet, player in self.bullets[:]:
            bullet.pos = (bullet.pos[0], bullet.pos[1] + 5)
            if bullet.pos[1] > Window.height:
                self.canvas.remove(bullet)
                self.bullets.remove((bullet, player))
        for ball in self.balls[:]:
            bx, by = ball.pos
            for bullet, player in self.bullets[:]:
                if bx < bullet.pos[0] < bx + 20 and by < bullet.pos[1] < by + 20:
                    if ball in self.balls:
                        self.canvas.remove(ball)
                        self.balls.remove(ball)
                        self.new_ball()
                    self.canvas.remove(bullet)
                    self.bullets.remove((bullet, player))
                    if player == 1:
                        self.score1 += 10
                        self.score_label1.text = f"Player 1: {self.score1}"
                    elif self.mode == 2:
                        self.score2 += 10
                        self.score_label2.text = f"Player 2: {self.score2}"
                    break
        for ball in self.balls[:]:
            ball.pos = (ball.pos[0], ball.pos[1] - 1)
            if ball.pos[1] < 0:
                self.canvas.remove(ball)
                self.balls.remove(ball)
                self.new_ball()
    
    def update_timer(self, dt):
        global time_left
        if time_left > 0:
            time_left -= 1
            self.timer_label.text = f"Time: {time_left}"
        else:
            self.end_game()
    
    def end_game(self):
        global time_left
        winner_text = (
            f"Score: {self.score1}\nNew High Score!" if self.score1 > self.get_highest_score() else 
            f"Score: {self.score1}\nHighest Score: {self.get_highest_score()}"
        ) if self.mode == 1 else (
            "Player 1 Wins!" if self.score1 > self.score2 else
            "Player 2 Wins!" if self.score2 > self.score1 else "It's a Tie!"
        )

        self.save_score()
        
        self.add_widget(Label(text=winner_text, size_hint=(None, None), pos=(220, 250)))
        Clock.unschedule(self.update)
        Clock.unschedule(self.update_timer)
        restart_button = Button(
            text="Restart", 
            size_hint=(None, None), 
            size=(200, 50), 
            pos=(150, 150),
            background_normal='',
            background_color=(19/255, 40/255, 77/255, 1)
        )
        restart_button.bind(on_press=self.restart_game)
        self.add_widget(restart_button)
        time_left = 30

    def save_score(self):
        if current_user:
            print(current_user)
            ref = db.reference(f'users/{current_user}/games').push()
            ref.set({
                'score': self.score1 if self.mode == 1 else {'player1': self.score1, 'player2': self.score2},
                'mode': self.mode
            })

            print(json.dumps(self.score1))

    def get_highest_score(self):
        ref = db.reference(f'users/{current_user}/games')
        scores = ref.get()

       ## print(ref.get())

        if not scores:
            return None  # No scores found

        highest_score = 0

        for game in scores.values():
            if isinstance(game, dict) and 'mode' in game and 'score' in game:  # Ensure valid data
                if game['mode'] == 1:
                    highest_score = max(highest_score, game['score'])
                else:
                    highest_score = max(highest_score, game['score'].get('player1', 0), game['score'].get('player2', 0))

        return highest_score
    
    def restart_game(self, instance):
        from kivy.app import App
        App.get_running_app().show_mode_selection()

class GameApp(App):
    def build(self):
        Window.size = (500, 500)
        self.root_widget = FloatLayout()
        self.login_screen = LoginScreen(self.show_mode_selection)
        self.root_widget.add_widget(self.login_screen)
        return self.root_widget
    
    def show_mode_selection(self):
        self.root_widget.clear_widgets()
        self.root_widget.add_widget(ModeSelection(self.start_game))
    
    def start_game(self, mode):
        self.root_widget.clear_widgets()
        self.root_widget.add_widget(ShootGame(mode))

if __name__ == '__main__':
    GameApp().run()
