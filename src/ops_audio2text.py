import os
import whisper

import utils


class OperatorAudioToText:
    def __init__(self, model_name="base"):
        self.model_name = model_name
        self.model = self.load_model(self.model_name)

    def load_model(self, model_name):
        return whisper.load_model(model_name)

    def extract_audio(self, page_id, url, data_folder="", run_id=""):
        workdir = os.getenv("WORKDIR")
        data_path = f"{workdir}/{data_folder}/{run_id}"
        output_audio_filename = f"{data_path}/{page_id}_audio.mp3"

        # V1: this may download a very high resolution one
        # cmd = f"yt-dlp --extract-audio --audio-format mp3 --output {output_audio_filename} {url}"

        # V2: Super fast download a smallest while maintain
        # a good quality of audio
        cmd = f"yt-dlp --extract-audio -S +size,+res,+br,+fps --output {output_audio_filename} {url}"

        if utils.run_shell_command(cmd):
            return output_audio_filename
        else:
            return ""

    def transcribe(self, audio_file: str):
        """
        text: {text: xxx, segments: [{}, ...], language: zh/en/..}
        """
        print(f"[OperatorAudioToText] transcribe audio_file: {audio_file}")

        text = self.model.transcribe(audio_file)
        return text
