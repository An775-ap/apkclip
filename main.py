import os
import sys
import threading
from kivy.app import App
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.clock import mainthread
from kivy.utils import get_color_from_hex
import yt_dlp

# Modern dark theme background
Window.clearcolor = get_color_from_hex('#121212')

# 1. FIX: Create a silent logger to prevent yt-dlp from crashing the Kivy mobile app.
class YTDLLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def isatty(self): return False

def parse_time_to_seconds(time_str):
    try:
        parts = [int(p) for p in time_str.strip().split(':')]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        elif len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        return int(time_str)
    except Exception:
        return None

class ClipperLayout(BoxLayout):
    def __init__(self, **kwargs):
        # 2. FIX: Heavy top padding (80) pushes UI below the phone's status bar.
        # Spacing (20) separates the elements so they aren't squished together.
        super().__init__(orientation='vertical', padding=[40, 80, 40, 40], spacing=20, **kwargs)

        # App Header
        self.add_widget(Label(
            text="[b][color=#e50914]YT[/color] Clipper Pro[/b]", 
            markup=True, 
            font_size='28sp', 
            size_hint_y=None, 
            height=60
        ))

        # URL Input
        self.url_input = TextInput(
            hint_text="Paste YouTube URL here", 
            multiline=False, 
            size_hint_y=None, 
            height=60, # Taller for easier tapping
            font_size='16sp',
            padding_y=[17, 0],
            background_color=get_color_from_hex('#ffffff')
        )
        self.add_widget(self.url_input)

        # Timestamps Row
        time_box = BoxLayout(orientation='horizontal', spacing=15, size_hint_y=None, height=60)
        self.start_input = TextInput(
            hint_text="Start (00:00)", 
            multiline=False,
            font_size='16sp',
            padding_y=[17, 0],
            background_color=get_color_from_hex('#ffffff')
        )
        self.end_input = TextInput(
            hint_text="End (00:15)", 
            multiline=False,
            font_size='16sp',
            padding_y=[17, 0],
            background_color=get_color_from_hex('#ffffff')
        )
        time_box.add_widget(self.start_input)
        time_box.add_widget(self.end_input)
        self.add_widget(time_box)

        # Aspect Ratio Selector
        self.ratio_spinner = Spinner(
            text="16:9 Standard",
            values=("16:9 Standard", "9:16 Shorts / Reels"),
            size_hint_y=None, 
            height=60,
            font_size='16sp',
            background_color=get_color_from_hex('#333333'),
            color=get_color_from_hex('#ffffff')
        )
        self.add_widget(self.ratio_spinner)

        # Action Button
        self.clip_btn = Button(
            text="Generate & Save Clip", 
            background_color=get_color_from_hex('#e50914'), 
            color=get_color_from_hex('#ffffff'),
            font_size='18sp',
            bold=True,
            size_hint_y=None, 
            height=65,
            background_normal='' # Flattens the color for a modern look
        )
        self.clip_btn.bind(on_press=self.start_clipping_thread)
        self.add_widget(self.clip_btn)

        # Status Output
        self.status_label = Label(
            text="Ready to clip", 
            font_size='15sp', 
            color=get_color_from_hex('#aaaaaa'),
            size_hint_y=None,
            height=80,
            halign='center',
            valign='middle'
        )
        self.status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.add_widget(self.status_label)

        # 3. FIX: Add an invisible spacer at the very bottom.
        # This consumes the empty black void space and pushes your UI beautifully to the top.
        self.add_widget(Widget())

    def start_clipping_thread(self, instance):
        url = self.url_input.text.strip()
        start_raw = self.start_input.text.strip()
        end_raw = self.end_input.text.strip()
        ratio = self.ratio_spinner.text

        start_sec = parse_time_to_seconds(start_raw)
        end_sec = parse_time_to_seconds(end_raw)

        if not url:
            self.status_label.text = "Error: Please provide a YouTube link."
            return
        if start_sec is None or end_sec is None or start_sec >= end_sec:
            self.status_label.text = "Error: Invalid start or end timestamp."
            return

        self.clip_btn.disabled = True
        self.status_label.text = "Starting download..."
        
        threading.Thread(
            target=self.process_clip, 
            args=(url, start_sec, end_sec, ratio), 
            daemon=True
        ).start()

    def process_clip(self, url, start_sec, end_sec, ratio):
        download_dir = "/storage/emulated/0/Download"
        if not os.path.exists(download_dir):
            download_dir = os.path.expanduser("~")

        output_path = os.path.join(download_dir, "clip_%(id)s.%(ext)s")

        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            'force_keyframes_at_cuts': True,
            'quiet': True,
            'noprogress': True,
            'logger': YTDLLogger(), # Use our silent logger
        }

        # Apply crop filter if Shorts format is selected
        if "9:16" in ratio:
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-vf', 'crop=ih*(9/16):ih']
            }

        # FIX: Temporarily redirect system stdout/stderr so yt-dlp doesn't crash the logger
        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = NullWriter()
        sys.stdout = NullWriter()

        try:
            self.update_status("Downloading and processing...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Success! Clip saved to your Downloads folder.")
        except Exception as err:
            self.update_status(f"Error: {str(err)}")
        finally:
            # Restore normal logging after download finishes
            sys.stderr = old_stderr
            sys.stdout = old_stdout

    @mainthread
    def update_status(self, message):
        self.status_label.text = message
        self.clip_btn.disabled = False

class YTClipperProApp(App):
    def build(self):
        return ClipperLayout()

if __name__ == '__main__':
    YTClipperProApp().run()
