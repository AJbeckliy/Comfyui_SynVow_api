# Comfyui_SynVow_api

ComfyUI custom nodes for [SynVow](https://service.synvow.com) API integration.

ComfyUI 用于 SynVow API 集成的自定义节点。

---

## Supported Models 支持的模型

| Node 节点 | Model | Description 描述 |
|-----------|-------|-----------------|
| SynVow Sora2 视频生成 | sora-2 | OpenAI Sora2 image-to-video (10/15s) / OpenAI Sora2 图像转视频（10/15 秒） |
| SynVow Sora2 优质视频生成 | sora2-优质 | OpenAI Sora2 Pro image-to-video (4/8/12s) / 优质模式（4/8/12 秒） |
| SynVow Sora2 批量视频生成 | sora-2 | Batch version / 批量版本 |
| SynVow Sora2 优质批量视频生成 | sora2-优质 | Batch Pro version / 优质批量版本 |
| SynVow Veo3.1 视频生成 | veo3.1 | Google Veo3.1 text/image-to-video / 文生视频·图生视频 |
| SynVow Veo3.1 批量视频生成 | veo3.1 | Batch version / 批量版本 |
| SynVow Grok 视频生成 | grok-* | xAI Grok image-to-video / 图生视频 |
| SynVow Grok 批量视频生成 | grok-* | Batch version / 批量版本 |
| SynVow Gemini API 图生文 | gemini-* | Google Gemini multimodal text output / 多模态文本输出 |
| SynVow Gemini 提示词生成 | gemini-* | Prompt generation via Gemini / 提示词生成 |
| SynVow NanoBanana Pro 图像生成 | nanobanana | Image generation (T2I / I2I) / 文生图·图生图 |
| SynVow NanoBanana Pro 批量出图 | nanobanana | Batch image generation / 批量出图 |
| SynVow Nano2 图像生成 | nano2 | Nano2 image generation (T2I / I2I) / 文生图·图生图 |
| SynVow Nano2 批量出图 | nano2 | Batch version / 批量版本 |
| SynVow 文本分割 | — | Split text by delimiter, output text + list / 按分隔符切分文本，输出单条与列表 |

---

## Installation 安装

1. Clone this repo into your ComfyUI `custom_nodes` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/AJbeckliy/Comfyui_SynVow_api.git
   ```

2. Restart ComfyUI.
3. Log in with your SynVow account via the menu bar (SynVow icon).

---

## Requirements 依赖

- Python `requests`, `aiohttp` (usually already available in ComfyUI environment)
- A [SynVow](https://service.synvow.com) account with API access / 需要 SynVow 账号及 API 权限

---

## Usage 使用方法

1. Click the SynVow icon in the ComfyUI menu bar to log in. / 点击菜单栏 SynVow 图标登录。
2. Add any SynVow node to your workflow. / 将节点添加到工作流。
3. Connect inputs and run. Videos/images are saved to the configured output path. / 连接输入并运行，视频/图片保存到配置的输出路径。

---

## Changelog 更新日志

### 2025-04-10
- **新增 `SynVow 文本分割` 节点**（`💫SynVow_api/tools` 分类）
  - 按分隔符切分文本
  - 输出 `text`（单条/全文）和 `list`（列表，可直接接批量节点 `prompts_list`）

---

## License

MIT
