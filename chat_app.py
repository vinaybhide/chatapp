import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
import os.path as ospath
import socket_client
import sys


class ConnectPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 2

        if(ospath.isfile('prev_details.txt')):
            with open('prev_details.txt', 'r') as f:
                d = f.read().split(',')
                f.close()
            
            prev_ip = d[0]
            prev_port = d[1]
            prev_username = d[2]
        else:
            prev_ip = ''
            prev_port = ''
            prev_username = ''

        self.add_widget(Label(text='IP:'))
        self.ip = TextInput(text=prev_ip, multiline=False)
        self.add_widget(self.ip)

        self.add_widget(Label(text='Port:'))
        self.port = TextInput(text=prev_port, multiline=False)
        self.add_widget(self.port)

        self.add_widget(Label(text='Username:'))
        self.username = TextInput(text=prev_username, multiline=False)
        self.add_widget(self.username)

        self.add_widget(Label(text=''))
        self.join = Button(text='Join')
        self.join.bind(on_press=self.join_button)
        self.add_widget(self.join)

    def join_button(self, instance):
        port = self.port.text
        ip = self.ip.text
        username = self.username.text

        with open('prev_details.txt', 'w') as f:
            f.write(f'{ip},{port},{username}')
            f.close()

        info = f"Attempting to join {ip}:{port} as {username}"
        chatapp.info_page.update_info(info)
        chatapp.screen_manager.current = "Info"
        Clock.schedule_once(self.connect, 1)

    # Connects to the server
    # (second parameter is the time after which this function had been called,
    #  we don't care about it, but kivy sends it, so we have to receive it)
    def connect(self, _):
        port = int(self.port.text)
        ip = self.ip.text
        username = self.username.text

        if not socket_client.connect(ip, port, username, show_error):
            return

        chatapp.create_chat_page()
        chatapp.screen_manager.current = 'Chat'

   
class InfoPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        
        self.message = Label(halign='center', valign='middle', font_size=30)
        self.message.bind(width=self.update_text_width)
        self.add_widget(self.message)

    def update_info(self, message):
        self.message.text = message
    
    def update_text_width(self, *_):
        self.message.text_size = (self.message.width *0.9, None)

class ScrollableView(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # ScrollView does not allow us to add more than one widget, so we need to trick it
        # by creating a layout and placing two widgets inside it
        # Layout is going to have one collumn and and size_hint_y set to None,
        # so height wo't default to any size (we are going to set it on our own)
        self.layout = GridLayout(cols=1, size_hint_y=None)
        self.add_widget(self.layout)

        # Now we need two widgets - Label for chat history and 'artificial' widget below
        # so we can scroll to it every new message and keep new messages visible
        # We want to enable markup, so we can set colors for example
        self.chat_history = Label(size_hint_y=None, markup=True)
        self.scroll_to_point = Label()
    
         # We add them to our layout
        self.layout.add_widget(self.chat_history)
        self.layout.add_widget(self.scroll_to_point)

    # Method called externally to add new message to the chat history
    def update_chat_history(self, message):
         # First add new line and message itself
        self.chat_history.text += '\n' + message

        # Set layout height to whatever height of chat history text is + 15 pixels
        # (adds a bit of space at teh bottom)
        # Set chat history label to whatever height of chat history text is
        # Set width of chat history text to 98 of the label width (adds small margins)
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

        # As we are updating above, text height, so also label and layout height are going to be bigger
        # than the area we have for this widget. ScrollView is going to add a scroll, but won't
        # scroll to the botton, nor is there a method that can do that.
        # That's why we want additional, empty widget below whole text - just to be able to scroll to it,
        # so scroll to the bottom of the layout
        self.scroll_to(self.scroll_to_point)

    def update_chat_history_layout(self, _=None):
        # Set layout height to whatever height of chat history text is + 15 pixels
        # (adds a bit of space at the bottom)
        # Set chat history label to whatever height of chat history text is
        # Set width of chat history text to 98 of the label width (adds small margins)
        self.layout.height = self.chat_history.texture_size[1] + 15
        self.chat_history.height = self.chat_history.texture_size[1]
        self.chat_history.text_size = (self.chat_history.width * 0.98, None)

class ChatPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 1
        self.rows = 2

        # First row is going to be occupied by our scrollable label
        # We want it be take 90% of app height
        self.history = ScrollableView(height=Window.size[1]*0.9, size_hint_y=None)
        self.add_widget(self.history)

        # In the second row, we want to have input fields and Send button
        # Input field should take 80% of window width
        # We also want to bind button click to send_message method
        self.new_message = TextInput(width=Window.size[0]*0.8, size_hint_x=None, multiline=False)
        self.send = Button(text='Send')
        self.send.bind(on_press=self.send_message)

        # To be able to add 2 widgets into a layout with just one collumn, we use additional layout,
        # add widgets there, then add this layout to main layout as second row
        bottom_line = GridLayout(cols=2)
        bottom_line.add_widget(self.new_message)
        bottom_line.add_widget(self.send)
        self.add_widget(bottom_line)

        Window.bind(on_key_down=self.on_key_down)
        Clock.schedule_once(self.focus_text_input, 1)

        socket_client.start_listening(self.incoming_message, show_error)

        self.bind(size=self.adjust_fields)

    # Updates page layout
    def adjust_fields(self, *_):

        # Chat history height - 90%, but at least 50px for bottom new message/send button part
        if Window.size[1] * 0.1 < 50:
            new_height = Window.size[1] - 50
        else:
            new_height = Window.size[1] * 0.9
        self.history.height = new_height

        # New message input width - 80%, but at least 160px for send button
        if Window.size[0] * 0.2 < 160:
            new_width = Window.size[0] - 160
        else:
            new_width = Window.size[0] * 0.8
        self.new_message.width = new_width

        # Update chat history layout
        #self.history.update_chat_history_layout()
        Clock.schedule_once(self.history.update_chat_history_layout, 0.01)
        
    # Gets called when either Send button or Enter key is being pressed
    # (kivy passes button object here as well, but we don;t care about it)
    def send_message(self, _):
        message = self.new_message.text
        self.new_message.text = ''
        
        # If there is any message - add it to chat history and send to the server
        if message:
            self.history.update_chat_history(f'[color=dd2020]{chatapp.connect_page.username.text}[/color] > {message}')
            socket_client.send(message)

        # As mentioned above, we have to shedule for refocusing to input field
        Clock.schedule_once(self.focus_text_input, 0.1)

    def on_key_down(self, instance, keyboard, keycode, text, modifiers):
        if(keycode == 40):
            self.send_message(None)
    def focus_text_input(self, _):
        self.new_message.focus = True
     
     # Passed to sockets client, get's called on new message
    def incoming_message(self, username, message):
        self.history.update_chat_history(f'[color=20dd20]{username}[/color] > {message}')

class EpicApp(App):
    def build(self):
        self.screen_manager = ScreenManager()

        self.connect_page = ConnectPage()
        screen = Screen(name='Connect')
        screen.add_widget(self.connect_page)
        self.screen_manager.add_widget(screen)

        self.info_page = InfoPage()
        screen = Screen(name='Info')
        screen.add_widget(self.info_page)
        self.screen_manager.add_widget(screen)

        return self.screen_manager

    # We cannot create chat screen with other but screens, as it;s init method will start listening
    # for incoming connections, but at this stage connection is not being made yet, so we
    # call this method later
    def create_chat_page(self):
        self.chat_page = ChatPage()
        screen = Screen(name='Chat')
        screen.add_widget(self.chat_page)
        self.screen_manager.add_widget(screen)        

# Error callback function, used by sockets client
# Updates info page with an error message, shows message and schedules exit in 10 seconds
# time.sleep() won't work here - will block Kivy and page with error message won't show up
def show_error(message):
    chatapp.info_page.update_info(message)
    chatapp.screen_manager.current = 'Info'
    Clock.schedule_once(sys.exit, 10)


if __name__ == "__main__":
    chatapp = EpicApp()
    chatapp.run()