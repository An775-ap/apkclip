import os
import sys
import threading
import shutil
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import mainthread
from kivy.core.window import Window
import yt_dlp

Window.clearcolor = (0.07, 0.07, 0.09, 1)

KV = '''
<CleanInput@TextInput>:
    background_color: 1, 1, 1, 1
    foreground_color: 0, 0, 0, 1
    hint_text_color: 0.5, 0.5, 0.5, 1
    font_size: '16sp'
    multiline: False
    padding: ['10dp', '14dp']

<SmoothButton@Button>:
    background_color: 0, 0, 0, 0
    background_normal: ''
    background_down: ''
    canvas.before:
        Color:
            rgba: (0.9, 0.04, 0.08, 1) if self.state == 'normal' else (0.7, 0.02, 0.06, 1)
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8,]

<ClipperLayout>:
    orientation: 'vertical'
    padding: '25dp', '40dp', '25dp', '25dp'
    spacing: '20dp'

    Label:
        text: '[b][color=#e50914]YT[/color] Clipper Pro[/b]'
        markup: True
        font_size: '32sp'
        size_hint_y: None
        height: '50dp'

    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '240dp'
        padding: '20dp'
        spacing: '15dp'
        canvas.before:
            Color:
                rgba: 0.15, 0.15, 0.18, 1
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [15,]

        CleanInput:
            id: url_input
            hint_text: 'Paste YouTube link here...'
            size_hint_y: None
            height: '50dp'

        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: '50dp'
            spacing: '10dp'
            
            Label:
                text: 'Start:'
                bold: True
                size_hint_x: None
                width: '45dp'
            CleanInput:
                id: start_m
                text: '00'
                input_filter: 'int'
                halign: 'center'
            Label:
                text: ':'
                bold: True
                font_size: '20sp'
                size_hint_x: None
                width: '10dp'
            CleanInput:
                id: start_s
                text: '00'
                input_filter: 'int'
                halign: 'center'

        BoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: '50dp'
            spacing: '10dp'
            
            Label:
                text: 'End:'
                bold: True
                size_hint_x: None
                width: '40dp'
            CleanInput:
                id: end_m
                text: '00'
                input_filter: 'int'
                halign: 'center'
            Label:
                text: ':'
                bold: True
                font_size: '20sp'
                size_hint_x: None
                width: '10dp'
            CleanInput:
                id: end_s
                text: '15'
                input_filter: 'int'
                halign: 'center'

        Spinner:
            id: ratio_spinner
            text: '16:9 Standard HD'
            values: ('16:9 Standard HD', '9:16 Shorts / Reels')
            size_hint_y: None
            height: '45dp'
            background_normal: ''
            background_color: 1, 1, 1, 1
            color: 0, 0, 0, 1
            font_size: '15sp'
            bold: True

    SmoothButton:
        id: clip_btn
        text: 'Generate & Save Clip'
        font_size: '18sp'
        bold: True
        size_hint_y: None
        height: '60dp'
        on_press: root.start_clipping_thread()

    Label:
        id: status_label
        text: 'Ready to clip.'
        color: 0.8, 0.8, 0.8, 1
        font_size: '13sp'
        size_hint_y: None
        height: '60dp'
        halign: 'center'
        valign: 'top'
        text_size: self.width, None

    Widget: 
'''

Builder.load_string(KV)

class YTDLLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

class NullWriter:
    def write(self, s): pass
    def flush(self): pass
    def isatty(self): return False

class ClipperLayout(BoxLayout):
    def get_ffmpeg_binary(self):
        native_lib = None
        
        # 1. Locate the hidden system library
        try:
            from jnius import autoclass
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            lib_dir = PythonActivity.mActivity.getApplicationInfo().nativeLibraryDir
            ffmpeg_path = os.path.join(lib_dir, 'libffmpeg.so')
            if os.path.exists(ffmpeg_path):
                native_lib = ffmpeg_path
        except Exception:
            pass

        if not native_lib:
            home_dir = os.environ.get('HOME', '')
            lib_dir = os.path.join(os.path.dirname(home_dir), 'lib')
            ffmpeg_path = os.path.join(lib_dir, 'libffmpeg.so')
            if os.path.exists(ffmpeg_path):
                native_lib = ffmpeg_path

        # 2. Copy it to writable storage and force executable permissions
        if native_lib:
            files_dir = os.environ.get('HOME', '')
            executable_ffmpeg = os.path.join(files_dir, 'ffmpeg_exec')
            
            try:
                # Only copy if it doesn't already exist to save processing time
                if not os.path.exists(executable_ffmpeg) or os.path.getsize(executable_ffmpeg) != os.path.getsize(native_lib):
                    shutil.copy2(native_lib, executable_ffmpeg)
                    os.chmod(executable_ffmpeg, 0o777)
                return executable_ffmpeg
            except Exception:
                return native_lib
                
        return None

    def start_clipping_thread(self):
        url = self.ids.url_input.text.strip()
        
        try:
            start_sec = int(self.ids.start_m.text) * 60 + int(self.ids.start_s.text)
            end_sec = int(self.ids.end_m.text) * 60 + int(self.ids.end_s.text)
        except ValueError:
            self.ids.status_label.text = "Error: Use numbers for time."
            return

        if not url:
            self.ids.status_label.text = "Error: Please provide a YouTube link."
            return
        if start_sec >= end_sec:
            self.ids.status_label.text = "Error: End time must be after Start time."
            return

        ffmpeg_path = self.get_ffmpeg_binary()
        if not ffmpeg_path:
            self.ids.status_label.text = "Error: FFmpeg engine missing. Check GitHub Actions."
            return

        self.ids.clip_btn.disabled = True
        self.ids.status_label.text = "Engine authorized! Extracting clip..."
        
        ratio = self.ids.ratio_spinner.text
        threading.Thread(target=self.process_clip, args=(url, start_sec, end_sec, ratio, ffmpeg_path), daemon=True).start()

    def process_clip(self, url, start_sec, end_sec, ratio, ffmpeg_path):
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
            'logger': YTDLLogger(),
            'ffmpeg_location': ffmpeg_path
        }

        if "9:16" in ratio:
            ydl_opts['postprocessor_args'] = {
                'ffmpeg': ['-vf', 'crop=ih*(9/16):ih']
            }

        old_stderr, old_stdout = sys.stderr, sys.stdout
        sys.stderr, sys.stdout = NullWriter(), NullWriter()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Success! Clip saved to your Downloads folder.")
        except Exception as err:
            self.update_status(f"Download Error: {str(err)[:60]}")
        finally:
            sys.stderr, sys.stdout = old_stderr, old_stdout

    @mainthread
    def update_status(self, message):
        self.ids.status_label.text = message
        self.ids.clip_btn.disabled = False

class YTClipperProApp(App):
    def build(self):
        return ClipperLayout()

if __name__ == '__main__':
    YTClipperProApp().run()
