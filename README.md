[中文](README_cn.md) | English

# Comfyui_SynVow_api

ComfyUI custom nodes for SynVow integration, including account login, image/video/audio generation, prompt tools, and transparent PNG asset generation.

---

## Changelog

### 2026-09-27

1. `SynVow Gemini` adds `GM3.7-flash-2606` / `GM3.6-flash-2606`, removes `GM3.5-flash-2606`  
2. `SynVow 即梦` (including batch) removes `即梦5.0`, adds `即梦5.0-flash`; resolution adds `1.5K`, output can be `png` / `jpeg`  

### 2026-09-22

1. Profile shows account role (普通用户 / 企业用户)  
2. `SynVow GPT-Image-2` (including batch, product six-in-one, and Alpha): `PT2.5-1k-企业` supports transparent background

### 2026-09-17

1. `SynVow Gemini` adds `GM3.7-flash-稳定` / `GM3.8-flash-稳定`, removes all Gemini 2605 models; removes `PT5.5-2605` / `PT5.4-2605`  
2. Removes `SynVow Seedance2.0 视频生成 (720P)`  
3. `SynVow Seedance` adds `sd2.0-特惠版`  
4. `SynVow Seedance 2.5` removes `seedance-2.5-低价`  
5. `SynVow MiniMax` (text-to-video / first-last frame / multimodal reference) adds `MiniMax-H3-低价`

### 2026-09-15

1. `SynVow GPT-Image-2 Alpha (T_batch)` adds transparent/opaque background selection, automatic layer quality routing, and batch-failure placeholders  
2. `SynVow 透明素材提示词生成器` reference-image layer mode supports 2-6 layers, with LLM-planned full-canvas coordinates and compact prompts  
3. `SynVow 透明PNG保存预览` keeps the returned RGBA pixels and aligns them to the planned coordinates; failed slots use black placeholders without stopping the workflow  
4. Adds `SynVow PSD图层合成`: writes the final PNGs into an editable PSD, with an optional hidden source-reference layer  
5. No new mask is generated, and source pixels are not pasted back into generated layers

### 2026-09-14

1. `SynVow NanoBanana` (including batch) updates aspect ratio options

### 2026-09-12

1. `SynVow Suno` adds the suno6 model; supports generate / cover / extend

### 2026-09-11

1. `SynVow GPT-Image-2` (including batch, product six-in-one, and Alpha) adds PT2.5 `1K-企业`, `稳定`, and `官方`  
2. Adds transparent background support (`1k` / `稳定` not supported yet)

### 2026-09-10

1. `SynVow Omni-Flash` adds `omni-1.1-flash`  
2. `SynVow GPT-Image-2` (including batch and product six-in-one) adds PT2.5: `PT2.5-1k-2609` / `PT2.5-sunburst-2609` / `PT2.5-flare-2609`; enterprise `PT2.5-sunburst-企业` / `PT2.5-flare-企业`

### 2026-08-25

1. `SynVow Seedance 2.5` adds `seedance-2.5-低价`: same duration/resolution as 2.5 (4-30 seconds, `480p`/`720p`/`1080p`); ratio only `16:9` / `9:16`  
2. `SynVow Seedance` removes `seedance2.0-全能` and its mode / version / 4K parameters  
3. Model prices can be filtered by tag: text / image / video / audio / parse / other

### 2026-08-24

1. Adds `SynVow wan-video` (`wan3.0-video-wd`, display name `wan3.0-video-稳定`): text-to-video with up to 9 reference images, 1 reference video, and 1 reference audio; resolution `480P`/`720P`/`1080P`, aspect `adaptive`/`16:9`/`4:3`/`1:1`/`3:4`/`9:16`, duration 2-30 seconds

### 2026-08-23

1. Adds standalone nodes `SynVow LLM-Qwen` / `(T_batch)`: `qwen3.6-flash-稳定` / `qwen3.6-plus-稳定` / `qwen3.7-plus-稳定` / `qwen3.7-max-稳定` / `qwen3.8-max-稳定`  
2. `SynVow GPT 提示词生成` adds `(T_batch)`  
3. Adds `SynVow Doubao 语音` (`doubao-seed-audio-1.0`, wav/mp3, speed/loudness/pitch, up to 3 reference audios)

### 2026-08-19

1. Removes `gpt-5.5-2607` / `gpt-5.6-sol-2607` (PT2607), adds `PT5.5-稳定` (requests `gpt-5.5-稳定`) and `PT5.6-sol-稳定` (requests `gpt-5.6-sol-稳定`)  
2. 即梦 5.0 resolution changes to `2K` / `3K` / `4K`, up to 4 reference images  
3. Adds standalone nodes `SynVow GK2.0` / `(T_batch)` / `(I_batch)` / `(T_I_batch)` (`grok-image-2.0-wd`, aspect ratio, `2k`/`1k`, up to 3 reference images)  
4. `SynVow Seedance 2.5` adds `1080p`

### 2026-08-17

1. Adds standalone node `SynVow Seedance 2.5` (480p/720p, 4-30 seconds)  
2. Removes `seedance-2.0-face` / `seedance-2.0-fast-face`  
3. Fixes `gpt-image-2-4k-qy` text-to-image: requests `gpt-image-2-4k-qy-t2i` when there is no reference image  
4. Recharge center: more tiers, custom amount minimum 5 RMB  
5. Profile: adds user ID, set / change password, and email binding  
6. When the latest announcement is dated today (local time), the "公告" button shows a red dot; opening the list hides it temporarily  
7. Image / video / audio upload changes

### 2026-08-06

1. Adds `SynVow MiniMax 文生视频` / `SynVow MiniMax 首尾帧视频` / `SynVow MiniMax 多模态参考视频` (model `MiniMax-H3`, resolution `2K`, 4-15 seconds)  
2. Fixes `gpt-image-2-4k-qy` text-to-image  
3. Floating menu adds the "公告" button

### 2026-08-03

1. 即梦 adds `即梦5.0-pro`  
2. Adds `SynVow GK1.5` / `(T_batch)` / `(I_batch)` / `(T_I_batch)`, requesting `grok-image-1.5-稳定`  
3. Adds `SynVow 悠船 文生图`, `SynVow 悠船 多图融合`, `SynVow 悠船 图像编辑`  
4. GPT-Image-2 adds `gpt-image-2-1k-qy` / `gpt-image-2-4k-qy`; the 1K model always requests 1K, the 4K model supports 1K / 2K / 4K; fast and affordable  
5. NanoBanana adds `nanobanana2-qy` / `nanobananapro-qy`; fast and affordable  
6. Fixes `SynVow Seedance2.0 视频生成 (720P)`  
7. Login / registration supports both phone number and email  
8. Gemini adds `gemini-3.5-flash-lite-稳定` / `gemini-3.6-flash-稳定`  
9. GPT adds `gpt-5.5-2607` / `gpt-5.6-sol-2607`

### 2026-07-22

1. Adds `SynVow Seedance` (`/image/edit`: all-round / mini / face / resolution / edit / extend)  
2. **Keeps** the legacy node `SynVow Seedance2.0 视频生成 (720P)` (`/video/generate`, actual model `seedance_2_720p`)  
3. Adds `SynVow Grok Video` (`grok-1.5-video`)  
4. Adds `SynVow Omni-Flash` (`Omni-Flash-Ext` / `omni-flash-preview`)  
5. Adds `SynVow Veo31` (`veo3.1`)  
6. Adds `SynVow Suno 灵感模式` / `SynVow Suno 自定义模式` (`suno5.5`)  
7. Video nodes output ComfyUI `VIDEO`; Suno outputs `AUDIO` plus path / URL / lyrics  
8. Short-video parsing aligned: Douyin / Xiaohongshu / WeChat Channels / bilibili / YouTube  
9. Adds `SynVow 即梦` / `(T_batch)` / `(I_batch)` / `(T_I_batch)` (model `即梦5.0`, resolution `2K`/`3K`)  
10. GPT-Image-2 adds `gpt-image-2-2607`; NanoBanana adds `nano-banana-2-lite-2607`  
11. Adds `SynVow GPT-Image-2 产品六合一`: product retouch, product-in-scene, blurry image upscale, object removal, mask-guided product tech light effects, and outpainting  
12. Adds the **one-take prompt workflow (Beta)**: character setup, scene setup, route storyboard, and Seedance LLM prompt compiler  
13. The one-take workflow is in beta; prompt structure, node parameters, and output may change after further testing  
14. Shared submit / poll / download / upload logic moved into `media_common.py`  
15. Removes duplicate download retries and duplicate `IS_CHANGED` implementations  
16. New video / audio nodes register the cancel-polling button

### 2026-07-01

1. `SynVow 透明素材提示词生成器`: generates reusable transparent asset prompts by scene  
2. `SynVow GPT-Image-2 Alpha (T_batch)`: direct transparent PNG output via URL (prompt-list batch)  
3. `SynVow 透明PNG保存预览`: saves RGBA PNG from the original URL with the real alpha channel; empty URLs or failed downloads use black placeholders and the workflow continues

### 2026-06-30

1. **Code cleanup**: removes unused / duplicate / broken code and unifies logic without changing behavior  
2. Removes the broken model-pool filter script, orphaned backend endpoints, and related dead code  
3. Unifies duplicated logic for audio/video loading, pagination styles, and time/request utilities  
4. GPT-Image-2 adds `gpt-image-2-官方`, image inputs expanded to 9  
5. Gemini model list and default model aligned  
6. Model price dialog uses a card grid; display names use the real model name only  
7. **Fixes opening "资源" in usage records**: parses links by model type (image / video / audio), fixing missing links for video and audio records

### 2026-06-23

1. **Integrates YMAI prompt nodes**: adds `YM-爆款封面`, `YM-故事板`, `YM-人物情绪`, `YM-角色卡`, reusing SynVow login and API with no extra configuration

### 2026-06-01

1. **Adds models `nano-banana-2-低价`, `nano-banana-pro-低价`** (NanoBanana nodes: single, T_batch, I_batch, TI_batch)  
2. The low-price models use the `ratio` / `resolution` / `files` request structure; results are parsed from `result.url`

### 2026-05-29

1. **Adds models `gpt-5.5-2606`, `gpt-5.4-2606`** (SynVow GPT 提示词生成, GPT-Image-2 text-to-image prompt controller, image-to-image prompt controller)  
2. Default model changes to `gpt-5.5-2606`  
3. **Adds models `gemini-3.1-flash-2606`, `gemini-3.5-flash-2606`, `gemini-3.1-pro-2606`, `gemini-3-pro-2606`** (SynVow Gemini 提示词生成, 🛒 e-commerce detail page prompt generator, GPT-Image-2 text-to-image prompt controller, image-to-image prompt controller)  
4. Gemini node and e-commerce detail page prompt generator default to `gemini-3.1-flash-2606`

### 2026-05-20

1. **Adds `短视频解析` node** (`💫SynVow_api/api/视频`)  
2. Takes a Douyin share link or text containing one, extracts the URL, gets a watermark-free direct link from the API, and downloads it locally  
3. **Adds model `gemini-3.5-flash-2605`** (Gemini node, e-commerce prompt generator, GPT-Image-2 prompt optimizer)  
4. **GPT-Image-2 prompt optimizer** adds `gemini-3.1-flash-2605`  
5. **Reference image prompt optimizer** adds `gemini-3.1-flash-2605`, `gemini-3.5-flash-2605`

### 2026-05-18

1. **Adds `SynVow 阿里云OSS上传` node** (`💫SynVow_api/OSS`)  
2. Uploads a single image to Aliyun OSS and outputs the public URL  
3. **Adds `图像列表数量校验` node** (`💫SynVow_api/Image`)  
4. Checks whether 2-5 image lists have the same count and stops the workflow with an error if not  
5. **E-commerce detail page prompt generator** adds a `prompts_count` output with the number of generated prompts  
6. **Text pause editor** removes the unused `seed` parameter  
7. **Adds `运行索引计数器` node** (`💫SynVow_api/Utils`)  
8. Increments and outputs the current index on each run; resets when Run is clicked  
9. **`图像列表组合器`** accepts list inputs and expands batches and lists into single images in order  
10. **Adds `SynVow Gemini 提示词生成 (T_batch)` node** (`💫SynVow_api/api/文本`)  
11. Takes a `prompts_list`, calls Gemini concurrently for each prompt, and outputs a result list  
12. **Adds model `gemini-3.1-flash-2605`** (Gemini node, e-commerce prompt generator)

### 2026-05-17

1. Adds model `gpt-image-2-稳定` (GPT-Image-2 nodes)  
2. Adds models `nano-banana-2-稳定`, `nano-banana-2-官方`, `nano-banana-pro-稳定`, `nano-banana-pro-官方` (NanoBanana nodes)

### 2026-05-15

1. **Adds `字符串范围提取器` node** (`💫SynVow_api/Text`)  
2. Supports marker mode (`{|}`) and JSON field mode (`{[字段名]}`)  
3. Outputs a list of matched fragments; can output one by index or all  
4. **Adds `列表批次转换器` node** (`💫SynVow_api/Text`)  
5. Groups multi-line text or JSON arrays by `batch_size`, separating groups with `---`  
6. **Adds `提示词范围选择器` node** (`💫SynVow_api/Text`)  
7. Selects a subset of a text list by start/end index; out-of-range values are clamped  
8. **Adds `提示词选择器` node** (`💫SynVow_api/Text`)  
9. Selects one text by index; returns the last one when out of range  
10. **Adds `TXT文件加载器` node** (`💫SynVow_api/Text`)  
11. Reads one or more TXT files by path; `file_index` selects a single file  
12. **Adds `文件夹扫描器` node** (`💫SynVow_api/Utils`)  
13. Recursively scans a folder and outputs a path list and count  
14. `file_type` filter: `all` / `images` / `txt` / `video` / `audio`  
15. Supports natural and time-based sorting and a maximum depth limit  
16. **Adds `批次图像加载器` node** (`💫SynVow_api/Image`)  
17. Loads images from a folder by batch index, outputting tensors, count, and file names  
18. **Adds `文件夹图像列表加载器` node** (`💫SynVow_api/Image`)  
19. Loads an image list from a folder by group index, outputting images, file names, total groups, and current group frame count  
20. **Adds `图像范围选择器` node** (`💫SynVow_api/Image`)  
21. Selects images from a list or batch by start/end index  
22. **Adds `图像列表组合器` node** (`💫SynVow_api/Image`)  
23. Combines up to 10 image inputs into an image list in order  
24. **Adds `图像加载器` node** (`💫SynVow_api/Image`)  
25. Loads a single image and also outputs file name, full path, folder path, and mask

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
| SynVow GPT-Image-2 Alpha (T_batch) | gpt-image-2 / 2.5 | URL-direct PNG with transparent or opaque background selection |
| SynVow PSD图层合成 | Local | Compose RGBA PNG files into an editable layered PSD |
| SynVow GPT-Image-2 产品六合一 | gpt-image-2 | Product refine / scene composite / clarity / remove / light effects / outpaint |

### 💫SynVow_api/api/视频

| Node | Model | Description |
|------|-------|-------------|
| SynVow wan-video | wan3.0-video-wd | Text/image/video/audio-reference video; 480P/720P/1080P, duration 2–30 seconds |
| SynVow Seedance 2.5 | doubao-seedance-2.5 / sd2-5-dj | 480p/720p/1080p, duration 4–30 seconds; low-price ratio is 16:9 / 9:16 only |
| SynVow Seedance | seedance-2.0-* | `/image/edit`: text/image/video/audio reference; outputs path/URL/info |
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
| SynVow Doubao 语音 | doubao-seed-audio-1.0 | Speech synthesis (wav/mp3, up to 3 reference clips) |

### 💫SynVow_api/api/文本

| Node | Model | Description |
|------|-------|-------------|
| SynVow Gemini 提示词生成 | gemini-* | Generate prompts with Gemini |
| SynVow Gemini 提示词生成 (T_batch) | gemini-* | Prompt-list batch |
| SynVow GPT 提示词生成 | gpt-* | Generate prompts with GPT |
| SynVow GPT 提示词生成 (T_batch) | gpt-* | Prompt-list batch |
| SynVow LLM-Qwen | qwen3.* | Generate prompts with Qwen (up to 10 reference images, optional video) |
| SynVow LLM-Qwen (T_batch) | qwen3.* | Prompt-list batch |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | Optimize image-generation prompts with an LLM |
| 图生图提示词控制器 | gemini-* / gpt-* | Reference-image prompt optimization |
| 🛒 电商详情页提示词生成器 | gemini-* | Multi-screen ecommerce detail-page prompts, with product and style reference images |
| GPT-image2详情页规划 | gemini-* | Plan long-scroll detail-page narrative and visual masters |
| GPT-image2详情页结构 | gemini-* | Convert narrative JSON into a per-screen structure blueprint |
| GPT-image2详情页批量提示词 | gemini-* | Generate a batch GPT-image2 prompt list |
| 详情页图像列表顺序拼接长图 | — | Vertically stitch a long image in list order |
| SynVow 透明素材提示词生成器 | gemini-* | Generate transparent PNG asset prompts and asset plans |
| 一镜到底-人物设定提示词 | — | One-Take character setup (Beta) |
| 一镜到底-场景设定提示词 | — | One-Take scene setup (Beta) |
| 一镜到底-路线分镜提示词 | — | One-Take route storyboard (Beta) |
| 一镜到底-Seedance提示词编译器（LLM） | — | One-Take Seedance prompt compile (Beta) |

### 💫SynVow_api/api/文本 - YM prompt nodes

| Node | Model | Description |
|------|-------|-------------|
| YM-爆款封面 | SynVow text/multimodal models | Generate cover-design prompts from title, topic, and optional reference images |
| YM-故事板 | SynVow text/multimodal models | Generate storyboard-table prompts and shot-video prompts from a script |
| YM-人物情绪 | SynVow text/multimodal models | Generate video prompts from character images and emotion direction |
| YM-角色卡 | SynVow text/multimodal models | Generate character three-views, face three-views, enhanced face three-views, clothing references, or character-card prompts |

### 💫SynVow_api/Text

| Node | Model | Description |
|------|-------|-------------|
| 文本停留编辑器 | — | Interactive text-list editor during workflow execution |
| SynVow 文本分割 | — | Split text by delimiter into a single item and a list |
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
| 文件夹扫描器 | — | Scan a folder into a path list; filter images / video / audio / TXT |
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
