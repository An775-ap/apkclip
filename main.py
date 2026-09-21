import os
import threading
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.button import Button
from kivy.clock import mainthread
import yt_dlp

def parse_time_to_seconds(time_str):
    """Converts mm:ss or hh:mm:ss string to integer seconds."""
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
        super().__init__(orientation='vertical', padding=20, spacing=12, **kwargs)

        # App Header
        self.add_widget(Label(
            text="[b]YT Clipper Pro[/b]", 
            markup=True, 
            font_size='22sp', 
            size_hint_y=None, 
            height=45
        ))

        # 1. URL Input
        self.url_input = TextInput(
            hint_text="Paste YouTube URL here", 
            multiline=False, 
            size_hint_y=None, 
            height=48
        )
        self.add_widget(self.url_input)

        # 2. Start and End Timestamps
        time_box = BoxLayout(orientation='horizontal', spacing=10, size_hint_y=None, height=48)
        self.start_input = TextInput(hint_text="Start (e.g. 00:10)", multiline=False)
        self.end_input = TextInput(hint_text="End (e.g. 00:30)", multiline=False)
        time_box.add_widget(self.start_input)
        time_box.add_widget(self.end_input)
        self.add_widget(time_box)

        # 3. Aspect Ratio Selector (16:9 vs 9:16 Shorts)
        self.ratio_spinner = Spinner(
            text="16:9 Standard",
            values=("16:9 Standard", "9:16 Shorts / Reels"),
            size_hint_y=None, 
            height=48
        )
        self.add_widget(self.ratio_spinner)

        # 4. Action Button
        self.clip_btn = Button(
            text="Generate & Save Clip", 
            background_color=(0.9, 0.1, 0.1, 1), 
            font_size='16sp',
            bold=True,
            size_hint_y=None, 
            height=52
        )
        self.clip_btn.bind(on_press=self.start_clipping_thread)
        self.add_widget(self.clip_btn)

        # 5. Status Output
        self.status_label = Label(
            text="Ready to clip", 
            font_size='14sp', 
            color=(0.7, 0.7, 0.7, 1)
        )
        self.add_widget(self.status_label)

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
        self.status_label.text = "Starting download on your local network..."
        
        # Run heavy processing in background thread so UI stays responsive
        threading.Thread(
            target=self.process_clip, 
            args=(url, start_sec, end_sec, ratio), 
            daemon=True
        ).start()

    def process_clip(self, url, start_sec, end_sec, ratio):
        # Save straight to Android's primary Download directory
        download_dir = "/storage/emulated/0/Download"
        if not os.path.exists(download_dir):
            download_dir = os.path.expanduser("~")

        output_path = os.path.join(download_dir, "clip_%(id)s.%(ext)s")

        # Configure yt-dlp options
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            'force_keyframes_at_cuts': True,
            'quiet': True,
        }

        # Apply 9:16 center-crop filter via FFmpeg if Shorts format is selected
        if "9:16" in ratio:
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-vf', 'crop=ih*(9/16):ih']
            }

        try:
            self.update_status("Clipping and processing format...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Success! Clip saved to your Downloads folder.")
        except Exception as err:
            self.update_status(f"Failed: {str(err)[:60]}")

    @mainthread
    def update_status(self, message):
        self.status_label.text = message
        self.clip_btn.disabled = False

class YTClipperProApp(App):
    def build(self):
        return ClipperLayout()

if __name__ == '__main__':
    YTClipperProApp().run()