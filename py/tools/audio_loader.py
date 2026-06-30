import os
import hashlib
import torch
import folder_paths

from .media_crop import maybe_crop_media


def _load_audio(filepath):
    import av
    with av.open(filepath) as af:
        stream = af.streams.audio[0]
        sr = stream.codec_context.sample_rate
        n_channels = stream.channels
        frames = []
        for frame in af.decode(streams=stream.index):
            buf = torch.from_numpy(frame.to_ndarray())
            if buf.shape[0] != n_channels:
                buf = buf.view(-1, n_channels).t()
            frames.append(buf)
        wav = torch.cat(frames, dim=1).float()
        return wav, sr


class AudioLoader:
    FUNCTION = "load_audio"
    CATEGORY = "💫SynVow_api/Utils"

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        os.makedirs(input_dir, exist_ok=True)
        files = sorted(folder_paths.filter_files_content_types(os.listdir(input_dir), ["audio"]))
        if not files:
            files = [""]
        return {
            "required": {
                "audio": (files, {}),
                "起始秒": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
                "裁剪秒数": ("FLOAT", {"default": 0.0, "min": 0.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("AUDIO", "STRING")
    RETURN_NAMES = ("audio", "audio_path")
    OUTPUT_NODE = True

    @classmethod
    def IS_CHANGED(cls, audio, 起始秒, 裁剪秒数):
        audio_path = folder_paths.get_annotated_filepath(audio)
        if os.path.isfile(audio_path):
            m = hashlib.sha256()
            with open(audio_path, "rb") as f:
                m.update(f.read())
            m.update(f"{起始秒:.6f}|{裁剪秒数:.6f}".encode())
            return m.digest().hex()
        return float("NaN")

    @classmethod
    def VALIDATE_INPUTS(cls, audio):
        if not folder_paths.exists_annotated_filepath(audio):
            return f"音频文件不存在: {audio}"
        return True

    def load_audio(self, audio, 起始秒, 裁剪秒数):
        audio_path = folder_paths.get_annotated_filepath(audio)

        if not os.path.isfile(audio_path):
            empty = {"waveform": torch.zeros(1, 1, 1), "sample_rate": 44100}
            return {"ui": {"audio": []}, "result": (empty, "")}

        effective_path = maybe_crop_media(audio_path, 起始秒, 裁剪秒数)
        try:
            waveform, sample_rate = _load_audio(effective_path)
            audio_data = {"waveform": waveform.unsqueeze(0), "sample_rate": sample_rate}
        except Exception:
            audio_data = {"waveform": torch.zeros(1, 1, 1), "sample_rate": 44100}
            effective_path = audio_path

        audio_ui = [{"filename": audio, "subfolder": "", "type": "input"}]
        return {"ui": {"audio": audio_ui}, "result": (audio_data, effective_path)}


NODE_CLASS_MAPPINGS = {
    "SynVowApiAudioLoader": AudioLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "SynVowApiAudioLoader": "加载音频（输出路径）",
}
