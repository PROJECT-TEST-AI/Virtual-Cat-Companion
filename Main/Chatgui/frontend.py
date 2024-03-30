import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.switch import Switch
from kivy.uix.slider import Slider
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.clock import Clock
from threading import Thread
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.storage.jsonstore import JsonStore
from kivy.uix.popup import Popup
from kivy.graphics import Color, Rectangle
from kivy.core.text import LabelBase
import requests

settings_store = JsonStore('settings.json')
kivy.require('2.0.0')  # Replace with your current kivy version!

# Change the color of the window background
Window.clearcolor = (0.2, 0.2, 0.2, 1)

# Set window size
Window.size = (500, 650)

class ChatMessage(BoxLayout):
    def __init__(self, message, is_user=True, **kwargs):
        super(ChatMessage, self).__init__(**kwargs)
        self.orientation = 'horizontal' if is_user else 'horizontal'
        self.message_label = Label(text=message, markup=True, halign='left', valign='middle', size_hint_y=None)
        self.size_hint_y = None
        self.height = 100  # Increase height for better visibility

        # Update the styling for the chat bubble
        bubble = BoxLayout(orientation='vertical', padding=10, size_hint_y=None)
        bubble.bind(minimum_height=bubble.setter('height'))

        # Create the label for the message text with word wrapping and apply the custom font
        message_label = Label(text=message, markup=True, halign='left', valign='middle', size_hint_y=None)
        message_label.bind(width=lambda *x: message_label.setter('text_size')(message_label, (self.width - 100, None)),
                           texture_size=lambda *x: message_label.setter('height')(message_label, message_label.texture_size[1]))
        message_label.text_size = (self.width - 100, None)
        bubble.add_widget(message_label)

        # Decide which image to use based on who is sending the message
        img_source = 'user.png' if is_user else 'ai.png'

        # Create the Image widget and add it to the layout
        image = Image(source=img_source, size_hint=(None, 1), width=50)

        if is_user:
            self.add_widget(image)
            self.add_widget(bubble)
        else:
            self.add_widget(bubble)
            self.add_widget(image)

        # Add a background color to the chat bubble
        with bubble.canvas.before:
            Color(rgba=(0.3, 0.3, 0.3, 1) if is_user else (0.1, 0.1, 0.1, 1))
            self.rect = Rectangle(size=bubble.size, pos=bubble.pos)

        bubble.bind(pos=self.update_rect, size=self.update_rect)

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def update_font_size(self, font_size):
        self.message_label.font_size = font_size

class SettingsPopup(Popup):
    def __init__(self, **kwargs):
        super(SettingsPopup, self).__init__(**kwargs)
        self.size_hint = (0.8, 0.6)
        self.title = 'Settings'
        
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Theme switch
        theme_switch_layout = BoxLayout(padding=5, spacing=10)
        theme_switch_label = Label(text='Dark Theme:')
        self.theme_switch = Switch(active=settings_store.get('user_settings')['theme'] if settings_store.exists('user_settings') else True)
        theme_switch_layout.add_widget(theme_switch_label)
        theme_switch_layout.add_widget(self.theme_switch)
        
        # Font size slider
        font_size_layout = BoxLayout(padding=5, spacing=10)
        font_size_label = Label(text='Font Size:')
        self.font_size_slider = Slider(min=12, max=24, value=settings_store.get('user_settings')['font_size'] if settings_store.exists('user_settings') else 14)
        font_size_layout.add_widget(font_size_label)
        font_size_layout.add_widget(self.font_size_slider)
        
        # Save button
        save_button = Button(text='Save', size_hint=(1, 0.2))
        save_button.bind(on_press=self.save_settings)
        
        layout.add_widget(theme_switch_layout)
        layout.add_widget(font_size_layout)
        layout.add_widget(save_button)
        
        self.content = layout
    
    def save_settings(self, instance):
        settings_store.put('user_settings', theme=self.theme_switch.active, font_size=self.font_size_slider.value)
        self.dismiss()
        # Access the ChatInterface directly from the root of the App
        App.get_running_app().root.update_messages_font_size(self.font_size_slider.value)
        
class ChatInterface(BoxLayout):
    def __init__(self, **kwargs):
        super(ChatInterface, self).__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = 10
        self.padding = [10, 10, 10, 10]

        # BoxLayout to contain the chat history and settings button
        top_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        settings_button = Button(text='Settings')
        settings_button.bind(on_press=self.open_settings)
        top_layout.add_widget(settings_button)

        # Add top_layout to the main layout
        self.add_widget(top_layout)

        # BoxLayout to contain the chat history
        self.chat_history_layout = BoxLayout(orientation='vertical', size_hint_y=None)
        self.chat_history_layout.bind(minimum_height=self.chat_history_layout.setter('height'))

        # Scrollable view for chat history
        self.chat_history = ScrollView(size_hint=(1, 0.8), do_scroll_x=False)
        self.chat_history.add_widget(self.chat_history_layout)
        self.add_widget(self.chat_history)

        # User input
        self.user_input = TextInput(size_hint=(1, 0.1), multiline=False)
        self.user_input.bind(on_text_validate=self.on_enter)
        self.add_widget(self.user_input)

        # Send button
        send_button = Button(text="Send", size_hint=(1, 0.1))
        send_button.bind(on_press=self.on_send_press)
        self.add_widget(send_button)

    def on_enter(self, instance):
        self.send_message_to_ai()

    def on_send_press(self, instance):
        self.send_message_to_ai()

    def update_chat_history(self, message, is_user=True):
        # Call this method from the main thread
        chat_message = ChatMessage(message, is_user=is_user)
        self.chat_history_layout.add_widget(chat_message)
        # Scroll to the latest message
        self.chat_history.scroll_to(chat_message)
        
    def send_message_to_ai(self):
        user_message = self.user_input.text
        self.user_input.text = ''
        if user_message:
            self.update_chat_history(user_message)
            # Use a thread to avoid freezing the UI
            Thread(target=self.call_virtual_cat_companion, args=(user_message,)).start()

    def call_virtual_cat_companion(self, user_input):
        try:
            response = requests.post('http://localhost:5000/ask', json={'input': user_input}).json()
            # Schedule the message update to happen on the main thread
            Clock.schedule_once(lambda dt: self.update_chat_history(response['response'], is_user=False))
        except requests.RequestException as e:
            # Handle connection error
            print(f"Error: {e}")

    def build(self):
        # Set the background color for the entire layout
        with self.canvas.before:
            Color(rgba=(0.05, 0.05, 0.05, 1))  # Dark background color
            self.rect = Rectangle(size=self.size, pos=self.pos)

        self.bind(pos=self.update_rect, size=self.update_rect)
        return super(ChatInterface, self).build()

    def update_rect(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def open_settings(self, instance):
        settings_popup = SettingsPopup()
        settings_popup.open()

    def update_messages_font_size(self, new_size):
        for message in self.chat_history_layout.children:
            message.update_font_size(new_size)

class VirtualCatApp(App):
    def build(self):
        self.title = 'VirtualCat'
        self.apply_settings()
        main_interface = ChatInterface()
        settings_button = Button(text='Settings', size_hint=(1, 0.1))
        settings_button.bind(on_press=self.open_settings)
        return main_interface

    def apply_settings(self):
        if settings_store.exists('user_settings'):
            settings = settings_store.get('user_settings')
            Window.clearcolor = (0.2, 0.2, 0.2, 1) if settings['theme'] else (1, 1, 1, 1)
            # Call method to update the UI with new settings if necessary

    def open_settings(self, instance):
        settings_popup = SettingsPopup()
        settings_popup.open()

if __name__ == "__main__":
    VirtualCatApp().run()