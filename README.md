# Comfyui_SynVow_api

ComfyUI custom nodes for SynVow integration.

---

## Changelog

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

### 💫SynVow_api/api/Image

| Node | Model | Description |
|------|-------|-------------|
| SynVow NanoBanana | nanobanana | Text-to-image |
| SynVow NanoBanana (T_batch) | nanobanana | Batch text-to-image |
| SynVow NanoBanana (I_batch) | nanobanana | Batch image-to-image |
| SynVow NanoBanana (T_I_batch) | nanobanana | Batch T2I + I2I |
| SynVow GPT-Image-2 | gpt-image-2 | Text-to-image & image-to-image |
| SynVow GPT-Image-2 (T_batch) | gpt-image-2 | Batch text-to-image |
| SynVow GPT-Image-2 (I_batch) | gpt-image-2 | Batch image-to-image |
| SynVow GPT-Image-2 (T_I_batch) | gpt-image-2 | Batch T2I + I2I |

### 💫SynVow_api/api/Video

| Node | Model | Description |
|------|-------|-------------|
| SynVow Seedance2.0 视频生成 | seedance2 | Text/image to video |
| SynVow Seedance2.0 批量视频生成 | seedance2 | Batch video generation |

### 💫SynVow_api/api/Text

| Node | Model | Description |
|------|-------|-------------|
| SynVow Gemini 提示词生成 | gemini-* | Prompt generation via Gemini |
| SynVow GPT 提示词生成 | gpt-* | Prompt generation via GPT |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | Optimize image generation prompts via LLM |
| 图生图提示词控制器 | gemini-* / gpt-* | Reference image prompt optimizer |
| 🛒 电商详情页提示词生成器 | gemini-* | Multi-screen e-commerce detail page prompt generator |

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

- Python `requests`, `aiohttp` (usually already available in ComfyUI environment)

---

## Usage

1. Click the SynVow icon in the ComfyUI menu bar to log in.
2. Add any SynVow node to your workflow.
3. Connect inputs and run. Videos/images are saved to the configured output path.

---

## License

MIT
