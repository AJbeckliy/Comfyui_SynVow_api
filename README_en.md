# Comfyui_SynVow_api

ComfyUI custom nodes for SynVow integration, including account login, image/video/audio generation, prompt tools, and transparent PNG asset generation.

---

## Changelog

### 2026-08-03
- **Image nodes**
  - Jimeng adds `即梦5.0-pro`
  - Added `SynVow GK1.5` / `(T_batch)` / `(I_batch)` / `(T_I_batch)`, requesting `grok-image-1.5-稳定`
  - Added `SynVow 悠船 文生图`, `SynVow 悠船 多图融合`, `SynVow 悠船 图像编辑`
  - GPT-Image-2 adds `gpt-image-2-1k-qy` / `gpt-image-2-4k-qy`; the 1K model is fixed to 1K, while the 4K model supports 1K / 2K / 4K; fast and affordable
  - NanoBanana adds `nanobanana2-qy` / `nanobananapro-qy`; fast and affordable
- **Video nodes**
  - Fixed `SynVow Seedance2.0 视频生成 (720P)`
- **Account / Web**
  - Login / register support both phone and email channels
- **Text models**
  - Gemini adds `gemini-3.5-flash-lite-稳定` / `gemini-3.6-flash-稳定`
  - GPT adds `gpt-5.5-2607` / `gpt-5.6-sol-2607`

### 2026-07-22
- **Video / audio nodes refreshed**
  - Added `SynVow Seedance` (`/image/edit`: 全能 / mini / face / resolution / edit / extend)
  - **Kept** legacy `SynVow Seedance2.0 视频生成 (720P)` (`/video/generate`, model `seedance_2_720p`)
  - Added `SynVow Grok Video` (`grok-1.5-video`)
  - Added `SynVow Omni-Flash` (`Omni-Flash-Ext` / `omni-flash-preview`)
  - Added `SynVow Veo31` (`veo3.1`)
  - Added `SynVow Suno 灵感模式` / `SynVow Suno 自定义模式` (`suno5.5`)
  - Video nodes output ComfyUI `VIDEO`; Suno outputs `AUDIO` plus path/url/lyrics
  - Short-video parse models aligned: Douyin / Xiaohongshu / Channels / bilibili / YouTube
- **Image nodes**
  - Added `SynVow 即梦` / `(T_batch)` / `(I_batch)` / `(T_I_batch)` (model `即梦5.0`, resolution `2K`/`3K`)
  - GPT-Image-2 adds `gpt-image-2-2607`; NanoBanana adds `nano-banana-2-lite-2607`
- **GPT-Image-2 product and prompt workflows**
  - Added `SynVow GPT-Image-2 产品六合一`: product refinement, scene compositing, clarity restoration, object removal, mask-guided technology light effects, and outpainting
  - Added the **One-Take Prompt Workflow (Beta)** with character setup, scene setup, route storyboard, and Seedance LLM prompt compiler nodes
  - The One-Take workflow is currently a test version; prompt structure, parameters, and output behavior may continue to change based on real-world testing
- **Code cleanup**
  - Shared submit/poll/download/upload helpers in `media_common.py`
  - Removed redundant outer download retries and duplicated `IS_CHANGED` helpers
  - Cancel-poll button registered for the new video/audio nodes

### 2026-07-01
- **Added transparent PNG asset workflow nodes**
  - `SynVow 透明素材提示词生成器`: generates reusable transparent asset prompts by scene
  - `SynVow GPT-Image-2 Alpha (T_batch)`: URL-only transparent PNG generation (prompt-list batch)
  - `SynVow 透明PNG保存预览`: saves original image URLs as RGBA PNG files to preserve the real alpha channel

### 2026-06-30
- **Code cleanup**: removed unused/duplicate/dead code and unified logic, behavior unchanged
  - Deleted the dead model-pool filter script, an orphaned backend route, and related dead code
  - Consolidated duplicated logic (audio/video loaders, pagination styles, time/request helpers)
- **Models & UI aligned with the frontend**
  - GPT-Image-2 adds the `gpt-image-2-官方` model; image inputs extended to 9
  - Gemini model list and default model aligned
  - Model price dialog switched to a card grid; display name now uses the real model name only
- **Fixed consumption-record "resource" open**: resolves URLs by model type (image/video/audio), fixing video/audio records that previously showed no link

### 2026-06-23
- **Integrated YMAI prompt nodes**: adds `YM-爆款封面`, `YM-故事板`, `YM-人物情绪`, `YM-角色卡`; reuses SynVow login and endpoints, no extra setup needed

### 2026-06-01
- **Added models `nano-banana-2-低价`, `nano-banana-pro-低价`** (NanoBanana nodes: single, T_batch, I_batch, TI_batch)
  - Low-price variants use `ratio` / `resolution` / `files` request shape; results parsed from `result.url`

### 2026-05-29
- **Added models `gpt-5.5-2606`, `gpt-5.4-2606`** (SynVow GPT 提示词生成, GPT-Image-2 文生图提示词控制器, 图生图提示词控制器)
  - New default model: `gpt-5.5-2606`
- **Added models `gemini-3.1-flash-2606`, `gemini-3.5-flash-2606`, `gemini-3.1-pro-2606`, `gemini-3-pro-2606`** (SynVow Gemini 提示词生成, 🛒 电商详情页提示词生成器, GPT-Image-2 文生图提示词控制器, 图生图提示词控制器)
  - New default model for Gemini nodes and 电商详情页提示词生成器: `gemini-3.1-flash-2606`

### 2026-05-20
- **Added `短视频解析` node** (`💫SynVow_api/api/视频`)
  - Accepts Douyin share link or text containing a URL; extracts URL, calls API to get watermark-free direct link, and downloads locally
- **Added model `gemini-3.5-flash-2605`** (Gemini nodes, Ecommerce Prompt Generator, GPT-Image-2 Prompt Optimizer)
- **GPT-Image-2 Prompt Optimizer** added model `gemini-3.1-flash-2605`
- **Reference Image Prompt Optimizer** added models `gemini-3.1-flash-2605`, `gemini-3.5-flash-2605`

### 2026-05-18
- **Added `SynVow 阿里云OSS上传` node** (`💫SynVow_api/OSS`)
  - Uploads a single image to Aliyun OSS and returns a public access URL
- **Added `图像列表数量校验` node** (`💫SynVow_api/Image`)
  - Validates that 2–5 image list groups have equal counts; raises an error if mismatched
- **Ecommerce Prompt Generator** added `prompts_count` output, returning the actual number of prompts generated
- **Text List Editor** removed unused `seed` parameter
- **Added `运行索引计数器` node** (`💫SynVow_api/Utils`)
  - Auto-increments output index on each run; resets to zero when workflow is queued
- **`图像列表组合器`** now supports list inputs; automatically flattens batch and list inputs into ordered single-image output
- **Added `SynVow Gemini 提示词生成 (T_batch)` node** (`💫SynVow_api/api/文本`)
  - Accepts `prompts_list`, concurrently calls Gemini for each prompt, outputs result list
- **Added model `gemini-3.1-flash-2605`** (Gemini nodes, Ecommerce Prompt Generator)

### 2026-05-17
- Added model `gpt-image-2-稳定` (GPT-Image-2 nodes)
- Added models `nano-banana-2-稳定`, `nano-banana-2-官方`, `nano-banana-pro-稳定`, `nano-banana-pro-官方` (NanoBanana nodes)

### 2026-05-15
- **Refactored all nodes; previous nodes are deprecated**
- **Added `字符串范围提取器`** (`💫SynVow_api/Text`)
  - Supports mark pattern mode (`{|}`) and JSON field extraction mode (`{[field]}`)
  - Outputs a list of matched segments; supports single-index or full-list output
- **Added `列表批次转换器`** (`💫SynVow_api/Text`)
  - Groups multiline text or JSON array by `batch_size`; batches separated by `---`
- **Added `提示词范围选择器`** (`💫SynVow_api/Text`)
  - Selects a subset from a text list by start/end index; auto-truncates on overflow
- **Added `提示词选择器`** (`💫SynVow_api/Text`)
  - Selects a single item from a text list by index; returns last item on overflow
- **Added `TXT文件加载器`** (`💫SynVow_api/Text`)
  - Reads one or multiple TXT files by path; supports `file_index` to target a single file
- **Added `文件夹扫描器`** (`💫SynVow_api/Utils`)
  - Recursively scans a folder and outputs path list and count
  - `file_type` filter: `all` / `images` / `txt` / `video` / `audio`
  - Supports natural sort, time sort, and max depth limit
- **Added `批次图像加载器`** (`💫SynVow_api/Image`)
  - Loads images from a folder by batch index; outputs tensor, count, and filename list
- **Added `文件夹图像列表加载器`** (`💫SynVow_api/Image`)
  - Loads images by group index; outputs image list, filename list, total groups, and frame count
- **Added `图像范围选择器`** (`💫SynVow_api/Image`)
  - Selects a range of images from an image list or batch by start/end index
- **Added `图像列表组合器`** (`💫SynVow_api/Image`)
  - Composes up to 10 image inputs into an ordered image list
- **Added `图像加载器`** (`💫SynVow_api/Image`)
  - Loads a single image; additionally outputs filename, full path, folder path, and mask

---

## Supported Nodes

### 💫SynVow_api/api/图像

| Node | Model | Description |
|------|-------|-------------|
| SynVow NanoBanana | nanobanana | Text-to-image |
| SynVow NanoBanana (T_batch) | nanobanana | Batch text-to-image |
| SynVow NanoBanana (I_batch) | nanobanana | Batch image-to-image |
| SynVow NanoBanana (T_I_batch) | nanobanana | Batch T2I + I2I |
| SynVow 即梦 | 即梦5.0 / 即梦5.0-pro | Text/image-to-image |
| SynVow 即梦 (T_batch) | 即梦5.0 / 即梦5.0-pro | Prompt-list batch |
| SynVow 即梦 (I_batch) | 即梦5.0 / 即梦5.0-pro | Prompt × image-group batch |
| SynVow 即梦 (T_I_batch) | 即梦5.0 / 即梦5.0-pro | Paired prompt/image-group batch |
| SynVow GK1.5 | grok-image-1.5-稳定 | Text/image-to-image (max 1 ref) |
| SynVow GK1.5 (T_batch) | grok-image-1.5-稳定 | Prompt-list batch |
| SynVow GK1.5 (I_batch) | grok-image-1.5-稳定 | Prompt × image-list batch |
| SynVow GK1.5 (T_I_batch) | grok-image-1.5-稳定 | Paired prompt/image batch |
| SynVow 悠船 文生图 | Midjourney_文生图 | Text-to-image (oref/sref/dref) |
| SynVow 悠船 多图融合 | Midjourney_多图融合 | Blend 2–4 images |
| SynVow 悠船 图像编辑 | Midjourney_图像编辑 | Single-image edit (oref/sref/dref) |
| SynVow GPT-Image-2 | gpt-image-2 | Text-to-image & image-to-image |
| SynVow GPT-Image-2 (T_batch) | gpt-image-2 | Batch text-to-image |
| SynVow GPT-Image-2 (I_batch) | gpt-image-2 | Batch image-to-image |
| SynVow GPT-Image-2 (T_I_batch) | gpt-image-2 | Batch T2I + I2I |
| SynVow GPT-Image-2 Alpha (T_batch) | gpt-image-2 | URL-only transparent PNG (prompt-list batch) |
| SynVow GPT-Image-2 产品六合一 | gpt-image-2 | Product refine / scene / clarity / remove / light FX / outpaint |

### 💫SynVow_api/api/视频

| Node | Model | Description |
|------|-------|-------------|
| SynVow Seedance | seedance2.0-* | `/image/edit`: text/image/video/audio refs; path/url/info outputs |
| SynVow Seedance2.0 视频生成 (720P) | seedance_2_720p | `/image/edit` + `content[]`, fixed 720P; path/url/info outputs |
| SynVow Grok Video | grok-1.5-video | Text/image to video (up to 6 refs) |
| SynVow Omni-Flash | Omni-Flash-Ext / omni-flash-preview | Image/video reference to video |
| SynVow Veo31 | veo3.1 | Text/image to video (up to 2 refs, 1080p) |
| 短视频解析 | platform parsers | Douyin / Xiaohongshu / Channels / bilibili / YouTube watermark-free download |

### 💫SynVow_api/api/音频

| Node | Model | Description |
|------|-------|-------------|
| SynVow Suno 灵感模式 | suno5.5 | Inspiration-mode music generation (`AUDIO` output) |
| SynVow Suno 自定义模式 | suno5.5 | Custom-mode music generation with title/tags (`AUDIO` output) |

### 💫SynVow_api/api/文本

| Node | Model | Description |
|------|-------|-------------|
| SynVow Gemini 提示词生成 | gemini-* | Prompt generation via Gemini |
| SynVow Gemini 提示词生成 (T_batch) | gemini-* | Prompt-list batch |
| SynVow GPT 提示词生成 | gpt-* | Prompt generation via GPT |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | Optimize image generation prompts via LLM |
| 图生图提示词控制器 | gemini-* / gpt-* | Reference image prompt optimizer |
| 🛒 电商详情页提示词生成器 | gemini-* | Multi-screen e-commerce detail page prompt generator |
| GPT-image2详情页规划 | gemini-* | Plan long-scroll product detail page narrative and visual master direction |
| GPT-image2详情页结构 | gemini-* | Build per-screen page structure blueprints from narrative JSON |
| GPT-image2详情页批量提示词 | gemini-* | Generate batch GPT-image2 prompts as `STRING[]` |
| 详情页图像列表顺序拼接长图 | — | Concatenate generated detail-page image list vertically |
| SynVow 透明素材提示词生成器 | gemini-* | Generate transparent PNG asset prompts and asset plans |
| 一镜到底-人物设定提示词 | — | One-Take character setup (Beta) |
| 一镜到底-场景设定提示词 | — | One-Take scene setup (Beta) |
| 一镜到底-路线分镜提示词 | — | One-Take route storyboard (Beta) |
| 一镜到底-Seedance提示词编译器（LLM） | — | One-Take Seedance prompt compiler (Beta) |

### 💫SynVow_api/api/文本 - YM prompt nodes

| Node | Model | Description |
|------|-------|-------------|
| YM-爆款封面 | SynVow text/multimodal models | Generate cover-design prompts from title, topic, and optional reference image |
| YM-故事板 | SynVow text/multimodal models | Generate storyboard-table prompts and storyboard video prompts from a script |
| YM-人物情绪 | SynVow text/multimodal models | Generate character emotion reaction video prompts from image and emotion direction |
| YM-角色卡 | SynVow text/multimodal models | Generate character three-view, face three-view, enhanced face view, outfit reference, or character-card prompts |

### 💫SynVow_api/Text

| Node | Model | Description |
|------|-------|-------------|
| 文本停留编辑器 | — | Interactive text list editor in workflow |
| SynVow 文本分割 | — | Split text by delimiter, output text + list |
| 文本重复 | — | Repeat text N times |
| 字符串范围提取器 | — | Extract text segments by mark pattern or JSON field |
| 列表批次转换器 | — | Split text list into fixed-size batches |
| 提示词范围选择器 | — | Select a range of items from text list by index |
| 提示词选择器 | — | Select a single item from text list by index |
| TXT文件加载器 | — | Load one or multiple TXT files by path |

### 💫SynVow_api/Image

| Node | Model | Description |
|------|-------|-------------|
| 批次图像加载器 | — | Load a batch of images from folder by index |
| 文件夹图像列表加载器 | — | Load images from folder by group index |
| 图像范围选择器 | — | Select a range of images from image list by index |
| 图像列表组合器 | — | Compose up to 10 images into an image list |
| 图像加载器 | — | Load image with filename, path and mask output |
| SynVow 透明PNG保存预览 | — | Save original image URLs as RGBA PNG files and preview the result |

### 💫SynVow_api/Utils

| Node | Model | Description |
|------|-------|-------------|
| 文件夹扫描器 | — | Scan folder and output path list, filter by type (images/video/audio/txt) |
| 加载视频（输出路径） | — | Load video file and output its path |
| 加载音频（输出路径） | — | Load audio file and output its path |
| SynVow 视频预览 | — | Preview generated video inside the node |

---

## Installation

1. Clone this repo into your ComfyUI `custom_nodes` directory:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/AJbeckliy/Comfyui_SynVow_api.git
   ```

2. Restart ComfyUI.
3. Log in with your SynVow account via the menu bar (SynVow icon).

---

## Requirements

- Python `requests`, `aiohttp`, `Pillow`, `numpy` (usually already available in ComfyUI environment)

---

## Usage

1. Click the SynVow icon in the ComfyUI menu bar to log in.
2. Add any SynVow node to your workflow.
3. Connect inputs and run. Videos/images are saved to the configured output path.

---

## License

MIT

YMAI nodes are integrated into the existing SynVow API structure. Node code lives under `py/api/ymai_*.py`, and prompt resources live under `py/prompts/ymai_*`.
