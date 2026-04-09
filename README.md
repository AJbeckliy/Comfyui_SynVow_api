# Comfyui_SynVow_api

ComfyUI custom nodes for [SynVow](https://service.synvow.com) API integration.

## Supported Models

| Node | Model | Description |
|------|-------|-------------|
| SynVow Sora2 视频生成 | sora-2 | OpenAI Sora2 image-to-video (10/15s) |
| SynVow Sora2 优质视频生成 | sora2-优质 | OpenAI Sora2 Pro image-to-video (4/8/12s) |
| SynVow Sora2 批量视频生成 | sora-2 | Batch version |
| SynVow Sora2 优质批量视频生成 | sora2-优质 | Batch Pro version |
| SynVow Veo3 视频生成 | veo3 | Google Veo3 text/image-to-video |
| SynVow Veo3 批量视频生成 | veo3 | Batch version |
| SynVow Gemini | gemini-* | Google Gemini text/vision models |
| SynVow Grok | grok-* | xAI Grok text/vision models |
| SynVow NanoBanana | nanobanana | Image generation |

## Installation

1. Clone this repo into your ComfyUI custom_nodes directory:
   `ash
   cd ComfyUI/custom_nodes
   git clone https://github.com/YOUR_USERNAME/Comfyui_SynVow_api.git
   `
2. Restart ComfyUI.
3. Log in with your SynVow account via the menu bar (SynVow icon).

## Requirements

- Python equests (usually already available in ComfyUI environment)
- A [SynVow](https://service.synvow.com) account with API access

## Usage

1. Click the SynVow icon in the ComfyUI menu bar to log in.
2. Add any SynVow node to your workflow.
3. Connect inputs and run  videos/images are saved to the configured output path.

## License

MIT
