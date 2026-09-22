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

class ClipperLayout(BoxLayout):
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

        self.ids.clip_btn.disabled = True
        self.ids.status_label.text = "Connecting to YouTube..."
        
        ratio = self.ids.ratio_spinner.text
        threading.Thread(target=self.process_clip, args=(url, start_sec, end_sec, ratio), daemon=True).start()

    def process_clip(self, url, start_sec, end_sec, ratio):
        download_dir = "/storage/emulated/0/Download"
        if not os.path.exists(download_dir):
            download_dir = os.path.expanduser("~")

        # 1. Use yt-dlp quietly just to extract the raw video stream URL
        ydl_opts = {'format': 'best[ext=mp4]', 'quiet': True, 'noprogress': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                video_id = info.get('id', 'video')
        except Exception as e:
            self.update_status(f"Extraction Error: {str(e)[:50]}")
            return

        if not stream_url:
            self.update_status("Error: Could not extract video stream.")
            return

        output_path = os.path.join(download_dir, f"clip_{video_id}.mp4")
        if os.path.exists(output_path):
            os.remove(output_path)

        duration = end_sec - start_sec
        self.update_status("Processing clip via Java native engine...")

        # 2. Build the command string
        if "9:16" in ratio:
            # Re-encode specifically to crop the center for Reels/Shorts
            cmd = f"-ss {start_sec} -i \"{stream_url}\" -t {duration} -vf \"crop=ih*(9/16):ih\" -c:v libx264 -preset ultrafast -c:a copy \"{output_path}\""
        else:
            # Fast copy for standard HD
            cmd = f"-ss {start_sec} -i \"{stream_url}\" -t {duration} -c copy \"{output_path}\""

        # 3. Execute directly through Android's Java memory using pyjnius
        try:
            from jnius import autoclass
            FFmpegKit = autoclass('com.arthenica.ffmpegkit.FFmpegKit')
            
            session = FFmpegKit.execute(cmd)
            return_code = session.getReturnCode().getValue()
            
            if return_code == 0:
                self.update_status("Success! Clip saved to your Downloads folder.")
            else:
                self.update_status("Processing Error: Engine failed to compile video.")
        except Exception as e:
            self.update_status(f"Java Error: {str(e)[:50]}")

    @mainthread
    def update_status(self, message):
        self.ids.status_label.text = message
        self.ids.clip_btn.disabled = False

class YTClipperProApp(App):
    def build(self):
        return ClipperLayout()

if __name__ == '__main__':
    YTClipperProApp().run()
