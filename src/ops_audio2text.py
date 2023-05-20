import whisper

import utils


class OperatorAudioToText:
    def __init__(self, model_name="base"):
        self.model_name = model_name
        self.model = self.load_model(self.model_name)

    def load_model(self, model_name):
        return whisper.load_model(model_name)

    def extract_audio(self, page_id, url):
        output_audio_filename = f"{page_id}_audio.wav"
        cmd = f"yt-dlp --extract-audio --audio-format wav --output {output_audio_filename} {url}"

        if utils.run_shell_command(cmd):
            return output_audio_filename
        else:
            return ""

    def transcribe(self, audio_file: str):
        print(f"[OperatorAudioToText] transcribe audio_file: {audio_file}")

        text = self.model.transcribe(audio_file)
        return text
