# Comfyui_SynVow_api

ComfyUI custom nodes for SynVow integration, including account login, image/video/audio generation, prompt tools, and transparent PNG asset generation.

---

## Changelog

### 2026-08-19
- **Text models**
  - Removed `gpt-5.5-2607` / `gpt-5.6-sol-2607` (PT2607); added `PT5.5-稳定` (requests `gpt-5.5-稳定`) and `PT5.6-sol-稳定` (requests `gpt-5.6-sol-稳定`)
- **Image nodes**
  - Jimeng 5.0 resolution is now `2K` / `3K` / `4K`, with up to 4 reference images
  - Added standalone node `SynVow GK2.0` / `(T_batch)` / `(I_batch)` / `(T_I_batch)` (`grok-image-2.0-wd`; aspect ratio, `2k`/`1k`, up to 3 reference images)
- **Video nodes**
  - `SynVow Seedance 2.5` adds `1080p`

### 2026-08-17
- **Video nodes**
  - Added standalone node `SynVow Seedance 2.5` (480p/720p, duration 4–30 seconds)
  - Removed `seedance-2.0-face` / `seedance-2.0-fast-face`
- **Image nodes**
  - Fixed `gpt-image-2-4k-qy` text-to-image: requests `gpt-image-2-4k-qy-t2i` when there is no reference image
- **Account / Web**
  - Recharge center: added more amount tiers; custom amount minimum 5 RMB
  - Profile: added user ID, set/change password, bind email
  - Announcements button shows a red dot when the latest item’s date is today (local); opening the list clears the dot for now
- **Upload**
  - Image/video/audio upload behavior updated

### 2026-08-06
- **Video nodes**
  - Added `SynVow MiniMax 文生视频` / `SynVow MiniMax 首尾帧视频` / `SynVow MiniMax 多模态参考视频` (model `MiniMax-H3`, resolution `2K`, duration 4–15 seconds)
- **Image nodes**
  - Fixed text-to-image for the `gpt-image-2-4k-qy` model
- **Account / Web**
  - Added an Announcements button to the floating menu

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
  - Shared submit/poll/download/upload logic consolidated into `media_common.py`
  - Removed duplicate download retry and duplicate `IS_CHANGED` implementations
  - New video/audio nodes registered with cancel-poll buttons

### 2026-07-01
- **Added transparent PNG asset workflow nodes**
  - `SynVow 透明素材提示词生成器`: generate reusable transparent-asset prompts by scene
  - `SynVow GPT-Image-2 Alpha (T_batch)`: URL-direct transparent PNG generation (prompt-list batch)
  - `SynVow 透明PNG保存预览`: save RGBA PNG from the original URL and keep the real alpha channel

### 2026-06-30
- **Code cleanup**: removed unused / duplicate / dead code and unified logic without changing behavior
  - Removed obsolete model-pool filter scripts, orphaned backend endpoints, and related dead code
  - Consolidated duplicated audio/video loading, pagination styles, and time/request helpers
- **Model and UI aligned with the frontend**
  - GPT-Image-2 adds `gpt-image-2-官方`, with image inputs expanded to 9
  - Gemini model list and defaults aligned
  - Model price dialog switched to a card-grid layout; display names use the real model name only
- **Fixed opening consumption-record "resources"**: parse links by model type (image/video/audio); fixed missing video/audio URLs

### 2026-06-23
- **Integrated YMAI prompt nodes**: added `YM-爆款封面`, `YM-故事板`, `YM-人物情绪`, `YM-角色卡`; reuse SynVow login and APIs with no extra setup

### 2026-06-01
- **Added models `nano-banana-2-低价`, `nano-banana-pro-低价`** (NanoBanana series: single / T_batch / I_batch / TI_batch)
  - Low-price variants use `ratio` / `resolution` / `files` request structure and parse results from `result.url`

### 2026-05-29
- **Added models `gpt-5.5-2606`, `gpt-5.4-2606`** (SynVow GPT prompt generation, GPT-Image-2 text-to-image prompt controller, image-to-image prompt controller)
  - Default model updated to `gpt-5.5-2606`
- **Added models `gemini-3.1-flash-2606`, `gemini-3.5-flash-2606`, `gemini-3.1-pro-2606`, `gemini-3-pro-2606`** (SynVow Gemini prompt generation, 🛒 ecommerce detail-page prompt generator, GPT-Image-2 text-to-image prompt controller, image-to-image prompt controller)
  - Gemini node and ecommerce detail-page prompt generator defaults updated to `gemini-3.1-flash-2606`

### 2026-05-20
- **Added `短视频解析` node** (`💫SynVow_api/api/视频`)
  - Accepts a Douyin share link or text containing a link, extracts the URL, calls the API for a watermark-free direct link, and downloads locally
- **Added model `gemini-3.5-flash-2605`** (Gemini node, ecommerce prompt generator, GPT-Image-2 prompt optimizer)
- **GPT-Image-2 prompt optimizer** adds `gemini-3.1-flash-2605`
- **Reference-image prompt optimizer** adds `gemini-3.1-flash-2605`, `gemini-3.5-flash-2605`

### 2026-05-18
- **Added `SynVow 阿里云OSS上传` node** (`💫SynVow_api/OSS`)
  - Upload a single image to Aliyun OSS and output a public URL
- **Added `图像列表数量校验` node** (`💫SynVow_api/Image`)
  - Validate that 2–5 image lists have matching counts; stop the workflow on mismatch
- **Ecommerce detail-page prompt generator** adds a `prompts_count` output for the actual number of generated prompts
- **Text stay editor** removes unused `seed` parameter
- **Added `运行索引计数器` node** (`💫SynVow_api/Utils`)
  - Auto-increments the current index on each run, and resets to zero when Run is clicked
- **`图像列表组合器`** supports list inputs and expands batches/lists into ordered single images
- **Added `SynVow Gemini 提示词生成 (T_batch)` node** (`💫SynVow_api/api/文本`)
  - Accepts a `prompts_list`, calls Gemini concurrently for each prompt, and outputs a result list
- **Added model `gemini-3.1-flash-2605`** (Gemini nodes, ecommerce prompt generation nodes)

### 2026-05-17
- Added model `gpt-image-2-稳定` (GPT-Image-2 series)
- Added models `nano-banana-2-稳定`, `nano-banana-2-官方`, `nano-banana-pro-稳定`, `nano-banana-pro-官方` (NanoBanana series)

### 2026-05-15
- **All nodes in the repository were refactored; previous nodes are deprecated**
- **Added `字符串范围提取器` node** (`💫SynVow_api/Text`)
  - Supports plain marker mode (`{|}`) and JSON field extraction (`{[field]}`)
  - Outputs matched fragment lists, with single-item or full-list selection by index
- **Added `列表批次转换器` node** (`💫SynVow_api/Text`)
  - Groups multi-line text or JSON arrays by `batch_size`, separated by `---`
- **Added `提示词范围选择器` node** (`💫SynVow_api/Text`)
  - Selects a subset from a text list by start/end index, with automatic clipping
- **Added `提示词选择器` node** (`💫SynVow_api/Text`)
  - Selects a single text item by index; returns the last item when out of range
- **Added `TXT文件加载器` node** (`💫SynVow_api/Text`)
  - Reads one or more TXT files by path; supports `file_index` for a single file
- **Added `文件夹扫描器` node** (`💫SynVow_api/Utils`)
  - Recursively scans a folder and outputs path list plus count
  - Supports `file_type` filters: `all` / `images` / `txt` / `video` / `audio`
  - Supports natural / time sorting and max-depth limits
- **Added `批次图像加载器` node** (`💫SynVow_api/Image`)
  - Loads images from a folder by batch index; outputs tensors, count, and filenames
- **Added `文件夹图像列表加载器` node** (`💫SynVow_api/Image`)
  - Loads an image list from a folder by group index; outputs images, filenames, total groups, and current group frame count
- **Added `图像范围选择器` node** (`💫SynVow_api/Image`)
  - Selects images within a start/end index range from a list or batch
- **Added `图像列表组合器` node** (`💫SynVow_api/Image`)
  - Combines up to 10 image inputs into an ordered image list
- **Added `图像加载器` node** (`💫SynVow_api/Image`)
  - Loads a single image and also outputs filename, full path, folder path, and mask

---

## Node List

### 💫SynVow_api/api/图像

| Node | Model | Description |
|------|-------|-------------|
| SynVow NanoBanana | nanobanana | Text-to-image |
| SynVow NanoBanana (T_batch) | nanobanana | Batch text-to-image |
| SynVow NanoBanana (I_batch) | nanobanana | Batch image-to-image |
| SynVow NanoBanana (T_I_batch) | nanobanana | Mixed text-to-image + image-to-image batch |
| SynVow 即梦 | 即梦5.0 / 即梦5.0-pro | Text-to-image / image-to-image |
| SynVow 即梦 (T_batch) | 即梦5.0 / 即梦5.0-pro | Prompt-list batch |
| SynVow 即梦 (I_batch) | 即梦5.0 / 即梦5.0-pro | Prompt × multi-image-group batch |
| SynVow 即梦 (T_I_batch) | 即梦5.0 / 即梦5.0-pro | Paired prompt and image-group batch |
| SynVow GK1.5 | grok-image-1.5-稳定 | Text-to-image / image-to-image (up to 1 reference image) |
| SynVow GK1.5 (T_batch) | grok-image-1.5-稳定 | Prompt-list batch |
| SynVow GK1.5 (I_batch) | grok-image-1.5-稳定 | Prompt × image-list batch |
| SynVow GK1.5 (T_I_batch) | grok-image-1.5-稳定 | Paired prompt and image batch |
| SynVow GK2.0 | grok-image-2.0-wd | Text-to-image / image-to-image (aspect ratio, 2k/1k, up to 3 reference images) |
| SynVow GK2.0 (T_batch) | grok-image-2.0-wd | Prompt-list batch |
| SynVow GK2.0 (I_batch) | grok-image-2.0-wd | Prompt × image-list batch |
| SynVow GK2.0 (T_I_batch) | grok-image-2.0-wd | Paired prompt and image batch |
| SynVow 悠船 文生图 | Midjourney_文生图 | Text-to-image (supports oref/sref/dref) |
| SynVow 悠船 多图融合 | Midjourney_多图融合 | Blend 2–4 images |
| SynVow 悠船 图像编辑 | Midjourney_图像编辑 | Single-image edit (supports oref/sref/dref) |
| SynVow GPT-Image-2 | gpt-image-2 | Text-to-image / image-to-image |
| SynVow GPT-Image-2 (T_batch) | gpt-image-2 | Batch text-to-image |
| SynVow GPT-Image-2 (I_batch) | gpt-image-2 | Batch image-to-image |
| SynVow GPT-Image-2 (T_I_batch) | gpt-image-2 | Mixed text-to-image + image-to-image batch |
| SynVow GPT-Image-2 Alpha (T_batch) | gpt-image-2 | URL-direct transparent PNG (prompt-list batch) |
| SynVow GPT-Image-2 产品六合一 | gpt-image-2 | Product refine / scene composite / clarity / remove / light effects / outpaint |

### 💫SynVow_api/api/视频

| Node | Model | Description |
|------|-------|-------------|
| SynVow Seedance 2.5 | doubao-seedance-2.5 | 480p/720p/1080p, duration 4–30 seconds |
| SynVow Seedance | seedance2.0-* | `/image/edit`: text/image/video/audio reference; outputs path/URL/info |
| SynVow Seedance2.0 视频生成 (720P) | seedance_2_720p | `/image/edit` + `content[]`, fixed 720P; outputs path/URL/info |
| SynVow Grok Video | grok-1.5-video | Text/image-to-video (up to 6 reference images) |
| SynVow Omni-Flash | Omni-Flash-Ext / omni-flash-preview | Image/video-reference video generation |
| SynVow Veo31 | veo3.1 | Text/image-to-video (up to 2 reference images, 1080p) |
| 短视频解析 | platform parse | Watermark-free download for Douyin / Xiaohongshu / Channels / bilibili / YouTube |

### 💫SynVow_api/api/音频

| Node | Model | Description |
|------|-------|-------------|
| SynVow Suno 灵感模式 | suno5.5 | Inspiration-mode music generation (outputs `AUDIO`) |
| SynVow Suno 自定义模式 | suno5.5 | Custom-mode music generation (title/tags, outputs `AUDIO`) |

### 💫SynVow_api/api/文本

| Node | Model | Description |
|------|-------|-------------|
| SynVow Gemini 提示词生成 | gemini-* | Generate prompts with Gemini |
| SynVow Gemini 提示词生成 (T_batch) | gemini-* | Prompt-list batch |
| SynVow GPT 提示词生成 | gpt-* | Generate prompts with GPT |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | Optimize image-generation prompts with an LLM |
| 图生图提示词控制器 | gemini-* / gpt-* | Reference-image prompt optimization |
| 🛒 电商详情页提示词生成器 | gemini-* | Multi-screen ecommerce detail-page prompts, with product and style references |
| GPT-image2详情页规划 | gemini-* | Plan long-scroll detail-page narrative and visual masters |
| GPT-image2详情页结构 | gemini-* | Convert narrative JSON into a screen-structure blueprint |
| GPT-image2详情页批量提示词 | gemini-* | Generate batch GPT-image2 prompt lists |
| 详情页图像列表顺序拼接长图 | — | Vertically stitch a long image in list order |
| SynVow 透明素材提示词生成器 | gemini-* | Generate transparent PNG asset prompts and asset plans |
| 一镜到底-人物设定提示词 | — | One-Take character setup (Beta) |
| 一镜到底-场景设定提示词 | — | One-Take scene setup (Beta) |
| 一镜到底-路线分镜提示词 | — | One-Take route storyboard (Beta) |
| 一镜到底-Seedance提示词编译器（LLM） | — | One-Take Seedance prompt compiler (Beta) |

### 💫SynVow_api/api/文本 - YM Prompt Nodes

| Node | Model | Description |
|------|-------|-------------|
| YM-爆款封面 | SynVow text/multimodal models | Generate cover-design prompts from title, topic, and optional references |
| YM-故事板 | SynVow text/multimodal models | Generate storyboard-table and shot-video prompts from a script |
| YM-人物情绪 | SynVow text/multimodal models | Generate video prompts from character images and emotion direction |
| YM-角色卡 | SynVow text/multimodal models | Generate character three-views, face three-views, enhanced face three-views, clothing references, or character-card prompts |

### 💫SynVow_api/Text

| Node | Model | Description |
|------|-------|-------------|
| 文本停留编辑器 | — | Interactive text-list editor during workflow execution |
| SynVow 文本分割 | — | Split text by delimiter into single items and lists |
| 文本重复 | — | Repeat text output N times |
| 字符串范围提取器 | — | Extract text fragments by marker or JSON field |
| 列表批次转换器 | — | Group a text list by batch size |
| 提示词范围选择器 | — | Select a subset from a text list by index range |
| 提示词选择器 | — | Select a single text item from a list by index |
| TXT文件加载器 | — | Read one or more TXT files by path |

### 💫SynVow_api/Image

| Node | Model | Description |
|------|-------|-------------|
| 批次图像加载器 | — | Load images from a folder by batch index |
| 文件夹图像列表加载器 | — | Load an image list from a folder by group index |
| 图像范围选择器 | — | Select an image subset by index range |
| 图像列表组合器 | — | Combine up to 10 images into an image list |
| 图像加载器 | — | Load an image and output filename, path, and mask |
| SynVow 透明PNG保存预览 | — | Save RGBA PNG from the original URL and preview it |

### 💫SynVow_api/Utils

| Node | Model | Description |
|------|-------|-------------|
| 文件夹扫描器 | — | Scan a folder into a path list; filter images/video/audio/TXT |
| 加载视频（输出路径） | — | Load a video file and output its path |
| 加载音频（输出路径） | — | Load an audio file and output its path |
| SynVow 视频预览 | — | Preview video inside the node |

---

## Installation

1. Clone this repository into ComfyUI `custom_nodes`:

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/AJbeckliy/Comfyui_SynVow_api.git
   ```

2. Restart ComfyUI.
3. Click the SynVow icon in the menu bar and sign in with your SynVow account.

---

## Dependencies

- Python `requests`, `aiohttp`, `Pillow`, `numpy` (usually already available in the ComfyUI environment)

---

## Usage

1. Click the SynVow icon in the menu bar to sign in.
2. Add the nodes you need to your workflow.
3. Connect inputs and run; videos/images are saved to the configured output path.

---

## License

MIT

YMAI nodes are integrated into the existing SynVow API project structure. Node code lives in `py/api/ymai_*.py`, and prompt assets live in `py/prompts/ymai_*`.
