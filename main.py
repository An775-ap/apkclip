import os
import sys
import threading
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
        text: '[b][color=#e50914]YT[/color] Downloader Pro[/b]'
        markup: True
        font_size: '32sp'
        size_hint_y: None
        height: '50dp'

    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '140dp'
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

        Spinner:
            id: format_spinner
            text: 'High Quality (MP4)'
            values: ('High Quality (MP4)', 'Audio Only (MP3)')
            size_hint_y: None
            height: '45dp'
            background_normal: ''
            background_color: 1, 1, 1, 1
            color: 0, 0, 0, 1
            font_size: '15sp'
            bold: True

    SmoothButton:
        id: dl_btn
        text: 'Download Full Video'
        font_size: '18sp'
        bold: True
        size_hint_y: None
        height: '60dp'
        on_press: root.start_download_thread()

    Label:
        id: status_label
        text: 'Ready.'
        color: 0.8, 0.8, 0.8, 1
        font_size: '14sp'
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
    def start_download_thread(self):
        url = self.ids.url_input.text.strip()
        
        if not url:
            self.ids.status_label.text = "Error: Please provide a YouTube link."
            return

        self.ids.dl_btn.disabled = True
        self.ids.status_label.text = "Starting download..."
        
        mode = self.ids.format_spinner.text
        threading.Thread(target=self.process_download, args=(url, mode), daemon=True).start()

    def process_download(self, url, mode):
        download_dir = "/storage/emulated/0/Download"
        if not os.path.exists(download_dir):
            download_dir = os.path.expanduser("~")

        output_path = os.path.join(download_dir, "%(title)s.%(ext)s")

        if "Audio" in mode:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path,
                'quiet': True,
                'noprogress': True,
                'logger': YTDLLogger(),
            }
        else:
            ydl_opts = {
                'format': 'best[ext=mp4]/best',
                'outtmpl': output_path,
                'quiet': True,
                'noprogress': True,
                'logger': YTDLLogger(),
            }

        old_stderr, old_stdout = sys.stderr, sys.stdout
        sys.stderr, sys.stdout = NullWriter(), NullWriter()

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status("Success! Saved to your Downloads folder.")
        except Exception as err:
            self.update_status(f"Error: {str(err)[:50]}")
        finally:
            sys.stderr, sys.stdout = old_stderr, old_stdout

    @mainthread
    def update_status(self, message):
        self.ids.status_label.text = message
        self.ids.dl_btn.disabled = False

class YTClipperProApp(App):
    def build(self):
        return ClipperLayout()

if __name__ == '__main__':
    YTClipperProApp().run()
