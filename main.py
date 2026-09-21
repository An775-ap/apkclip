import os
import sys
import threading
import urllib.request
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

Window.clearcolor = get_color_from_hex('#121212')

class YTDLLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def isatty(self): return False

class ClipperLayout(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', padding=[40, 80, 40, 40], spacing=25, **kwargs)

        self.add_widget(Label(
            text="[b][color=#e50914]YT[/color] Clipper Pro[/b]", 
            markup=True, font_size='32sp', size_hint_y=None, height=70
        ))

        # URL Input Row
        self.add_widget(Label(text="YouTube URL:", font_size='16sp', bold=True, size_hint_y=None, height=30, halign='left', color=get_color_from_hex('#ffffff')))
        self.url_input = TextInput(
            hint_text="Paste link here...", multiline=False, size_hint_y=None, height=55,
            font_size='16sp', padding_y=[15, 0], background_color=get_color_from_hex('#ffffff')
        )
        self.add_widget(self.url_input)

        # Time Input Row (Split Minutes and Seconds for default colon)
        time_container = BoxLayout(orientation='vertical', spacing=10, size_hint_y=None, height=130)
        
        # Start Time
        start_row = BoxLayout(orientation='horizontal', spacing=5)
        start_row.add_widget(Label(text="Start Time:", bold=True, size_hint_x=0.4))
        self.start_m = TextInput(text="00", input_filter='int', halign='center', multiline=False, size_hint_x=0.25, font_size='18sp')
        start_row.add_widget(self.start_m)
        start_row.add_widget(Label(text=":", bold=True, font_size='24sp', size_hint_x=0.1))
        self.start_s = TextInput(text="00", input_filter='int', halign='center', multiline=False, size_hint_x=0.25, font_size='18sp')
        start_row.add_widget(self.start_s)
        time_container.add_widget(start_row)

        # End Time
        end_row = BoxLayout(orientation='horizontal', spacing=5)
        end_row.add_widget(Label(text="End Time:", bold=True, size_hint_x=0.4))
        self.end_m = TextInput(text="00", input_filter='int', halign='center', multiline=False, size_hint_x=0.25, font_size='18sp')
        end_row.add_widget(self.end_m)
        end_row.add_widget(Label(text=":", bold=True, font_size='24sp', size_hint_x=0.1))
        self.end_s = TextInput(text="15", input_filter='int', halign='center', multiline=False, size_hint_x=0.25, font_size='18sp')
        end_row.add_widget(self.end_s)
        time_container.add_widget(end_row)
        
        self.add_widget(time_container)

        # Format Options
        self.ratio_spinner = Spinner(
            text="16:9 Standard HD",
            values=("16:9 Standard HD", "9:16 Shorts / Reels"),
            size_hint_y=None, height=60, font_size='16sp',
            background_color=get_color_from_hex('#333333'), color=get_color_from_hex('#ffffff')
        )
        self.add_widget(self.ratio_spinner)

        # Download Button
        self.clip_btn = Button(
            text="Generate & Save Clip", 
            background_color=get_color_from_hex('#e50914'), color=get_color_from_hex('#ffffff'),
            font_size='18sp', bold=True, size_hint_y=None, height=65, background_normal=''
        )
        self.clip_btn.bind(on_press=self.start_clipping_thread)
        self.add_widget(self.clip_btn)

        # Status Label
        self.status_label = Label(
            text="Ready to clip.", font_size='14sp', color=get_color_from_hex('#aaaaaa'),
            size_hint_y=None, height=60, halign='center', valign='middle'
        )
        self.status_label.bind(width=lambda s, w: s.setter('text_size')(s, (w, None)))
        self.add_widget(self.status_label)

        self.add_widget(Widget())

    def get_ffmpeg_binary(self):
        """Downloads a static Android FFmpeg binary on first run to enable 1080p and 9:16 cropping."""
        try:
            from android.storage import app_storage_path
            storage_dir = app_storage_path()
        except ImportError:
            storage_dir = os.path.dirname(os.path.abspath(__file__))

        ffmpeg_bin = os.path.join(storage_dir, 'ffmpeg')

        if not os.path.exists(ffmpeg_bin):
            self.update_status("Installing HD Video Engine (12MB)... Please wait.")
            # Highly reliable static arm64 FFmpeg build specifically for Android
            url = "https://github.com/Khang-NT/ffmpeg-binary-android/releases/download/v4.4/ffmpeg-aarch64"
            try:
                urllib.request.urlretrieve(url, ffmpeg_bin)
                os.chmod(ffmpeg_bin, 0o755) # Make it executable on Android
            except Exception as e:
                self.update_status(f"Engine download failed: {str(e)[:40]}")
                return None
        return ffmpeg_bin

    def start_clipping_thread(self, instance):
        url = self.url_input.text.strip()
        
        # Convert split boxes to seconds
        try:
            start_sec = int(self.start_m.text) * 60 + int(self.start_s.text)
            end_sec = int(self.end_m.text) * 60 + int(self.end_s.text)
        except ValueError:
            self.status_label.text = "Error: Use numbers for time."
            return

        if not url:
            self.status_label.text = "Error: Please provide a YouTube link."
            return
        if start_sec >= end_sec:
            self.status_label.text = "Error: End time must be after Start time."
            return

        self.clip_btn.disabled = True
        self.status_label.text = "Initializing HD Engine..."
        
        threading.Thread(target=self.process_clip, args=(url, start_sec, end_sec, self.ratio_spinner.text), daemon=True).start()

    def process_clip(self, url, start_sec, end_sec, ratio):
        ffmpeg_path = self.get_ffmpeg_binary()

        download_dir = "/storage/emulated/0/Download"
        if not os.path.exists(download_dir):
            download_dir = os.path.expanduser("~")

        output_path = os.path.join(download_dir, "clip_%(id)s.%(ext)s")

        # Prioritize 1080p and merge with high quality audio using FFmpeg
        ydl_opts = {
            'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]',
            'outtmpl': output_path,
            'download_ranges': yt_dlp.utils.download_range_func(None, [(start_sec, end_sec)]),
            'force_keyframes_at_cuts': True,
            'quiet': True,
            'noprogress': True,
            'logger': YTDLLogger(),
        }

        # Inject the Android FFmpeg binary into yt-dlp
        if ffmpeg_path and os.path.exists(ffmpeg_path):
            ydl_opts['ffmpeg_location'] = ffmpeg_path

        # Apply FFmpeg postprocessor if 9:16 is selected
        if "9:16" in ratio:
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-vf', 'crop=ih*(9/16):ih']
            }

        old_stderr = sys.stderr
        old_stdout = sys.stdout
        sys.stderr = NullWriter()
        sys.stdout = NullWriter()

        try:
            self.update_status("Downloading HD video and processing crop...")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Success! Clip saved to your Downloads folder.")
        except Exception as err:
            self.update_status(f"Error: {str(err)[:50]}")
        finally:
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
