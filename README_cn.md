# Comfyui_SynVow_api

ComfyUI 用于 SynVow 集成的自定义节点。

---

## 更新日志

### 2026-05-29
- **新增模型 `gpt-5.5-2606`、`gpt-5.4-2606`**（SynVow GPT 提示词生成、GPT-Image-2 文生图提示词控制器、图生图提示词控制器）
  - 默认模型更新为 `gpt-5.5-2606`
- **新增模型 `gemini-3.1-flash-2606`、`gemini-3.5-flash-2606`、`gemini-3.1-pro-2606`、`gemini-3-pro-2606`**（SynVow Gemini 提示词生成、🛒 电商详情页提示词生成器、GPT-Image-2 文生图提示词控制器、图生图提示词控制器）
  - Gemini 节点及电商详情页提示词生成器默认模型更新为 `gemini-3.1-flash-2606`

### 2026-05-20
- **新增 `短视频解析` 节点**（`💫SynVow_api/api/视频` 分类）
  - 输入抖音分享链接或含链接的文本，自动提取 URL，调用 API 返回无水印直链并下载至本地
- **新增模型 `gemini-3.5-flash-2605`**（Gemini 节点、电商提示词生成器、GPT-Image-2 提示词优化器）
- **GPT-Image-2 提示词优化器** 补入模型 `gemini-3.1-flash-2605`
- **参考图提示词优化器** 补入模型 `gemini-3.1-flash-2605`、`gemini-3.5-flash-2605`

### 2026-05-18
- **新增 `SynVow 阿里云OSS上传` 节点**（`💫SynVow_api/OSS` 分类）
  - 将单张图像上传至阿里云 OSS，输出公网访问 URL
- **新增 `图像列表数量校验` 节点**（`💫SynVow_api/Image` 分类）
  - 校验 2~5 组图像列表数量是否一致，不一致则报错阻断流程
- **电商详情页提示词生成器** 新增 `prompts_count` 输出端，输出实际生成的提示词条数
- **文本停留编辑器** 删除无用 `seed` 参数
- **新增 `运行索引计数器` 节点**（`💫SynVow_api/Utils` 分类）
  - 每次运行自动自增输出当前索引，点击运行时自动归零
- **`图像列表组合器`** 支持列表输入，自动展开 batch 和列表为单张顺序输出
- **新增 `SynVow Gemini 提示词生成 (T_batch)` 节点**（`💫SynVow_api/api/文本` 分类）
  - 接收 `prompts_list` 文本列表，对每条 prompt 并发调用 Gemini，输出结果列表
- **新增模型 `gemini-3.1-flash-2605`**（Gemini 节点、电商提示词生成节点）

### 2026-05-17
- 新增模型 `gpt-image-2-稳定`（GPT-Image-2 系列节点）
- 新增模型 `nano-banana-2-稳定`、`nano-banana-2-官方`、`nano-banana-pro-稳定`、`nano-banana-pro-官方`（NanoBanana 系列节点）

### 2026-05-15
- **仓库内所有节点进行重构，原有节点已废弃**
- **新增 `字符串范围提取器` 节点**（`💫SynVow_api/Text` 分类）
  - 支持普通标记模式（`{|}`）和 JSON 字段提取模式（`{[字段名]}`）
  - 输出匹配片段列表，支持按索引取单条或全部输出
- **新增 `列表批次转换器` 节点**（`💫SynVow_api/Text` 分类）
  - 将多行文本或 JSON 数组按 `batch_size` 分组，组间以 `---` 分隔输出
- **新增 `提示词范围选择器` 节点**（`💫SynVow_api/Text` 分类）
  - 按起始/结束索引从文本列表中选取子集，超出范围自动截断
- **新增 `提示词选择器` 节点**（`💫SynVow_api/Text` 分类）
  - 按索引从文本列表中选取单条文本，越界时自动返回最后一条
- **新增 `TXT文件加载器` 节点**（`💫SynVow_api/Text` 分类）
  - 按路径读取一个或多个 TXT 文件，支持 `file_index` 指定单文件
- **新增 `文件夹扫描器` 节点**（`💫SynVow_api/Utils` 分类）
  - 递归扫描文件夹，输出路径列表和数量
  - 支持 `file_type` 过滤：`all` / `images` / `txt` / `video` / `audio`
  - 支持自然序、时间序多种排序方式及最大深度限制
- **新增 `批次图像加载器` 节点**（`💫SynVow_api/Image` 分类）
  - 按批次索引从文件夹加载图像，输出张量、数量及文件名列表
- **新增 `文件夹图像列表加载器` 节点**（`💫SynVow_api/Image` 分类）
  - 按组索引从文件夹加载图像列表，输出图像列表、文件名列表、总组数、当前组帧数
- **新增 `图像范围选择器` 节点**（`💫SynVow_api/Image` 分类）
  - 按起始/结束索引从图像列表或批次中选取范围内的图像
- **新增 `图像列表组合器` 节点**（`💫SynVow_api/Image` 分类）
  - 将最多 10 张图像输入按顺序组合为图像列表
- **新增 `图像加载器` 节点**（`💫SynVow_api/Image` 分类）
  - 加载单张图像，额外输出文件名、完整路径、所在文件夹路径及 mask

---

## 节点列表

### 💫SynVow_api/api/图像

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow NanoBanana | nanobanana | 文生图 |
| SynVow NanoBanana (T_batch) | nanobanana | 批量文生图 |
| SynVow NanoBanana (I_batch) | nanobanana | 批量图生图 |
| SynVow NanoBanana (T_I_batch) | nanobanana | 文生图 + 图生图混合批量 |
| SynVow GPT-Image-2 | gpt-image-2 | 文生图·图生图 |
| SynVow GPT-Image-2 (T_batch) | gpt-image-2 | 批量文生图 |
| SynVow GPT-Image-2 (I_batch) | gpt-image-2 | 批量图生图 |
| SynVow GPT-Image-2 (T_I_batch) | gpt-image-2 | 文生图 + 图生图混合批量 |

### 💫SynVow_api/api/视频

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow Seedance2.0 视频生成 | seedance2 | 文生视频·图生视频 |
| SynVow Seedance2.0 批量视频生成 | seedance2 | 批量视频生成 |

### 💫SynVow_api/api/文本

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow Gemini 提示词生成 | gemini-* | 通过 Gemini 生成提示词 |
| SynVow GPT 提示词生成 | gpt-* | 通过 GPT 生成提示词 |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | 通过 LLM 优化图像生成提示词 |
| 图生图提示词控制器 | gemini-* / gpt-* | 参考图提示词优化 |
| 🛒 电商详情页提示词生成器 | gemini-* | 多屏电商详情页提示词生成，支持产品参考图与风格参考图 |

### 💫SynVow_api/Text

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| 文本停留编辑器 | — | 工作流执行中弹出交互式文本列表编辑界面 |
| SynVow 文本分割 | — | 按分隔符切分文本，输出单条与列表 |
| 文本重复 | — | 将文本重复输出 N 次 |
| 字符串范围提取器 | — | 按标记或 JSON 字段提取文本片段 |
| 列表批次转换器 | — | 将文本列表按批次大小分组输出 |
| 提示词范围选择器 | — | 按索引范围从文本列表选取子集 |
| 提示词选择器 | — | 按索引从文本列表选取单条文本 |
| TXT文件加载器 | — | 按路径读取一个或多个 TXT 文件 |

### 💫SynVow_api/Image

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| 批次图像加载器 | — | 按批次索引从文件夹加载图像 |
| 文件夹图像列表加载器 | — | 按组索引从文件夹加载图像列表 |
| 图像范围选择器 | — | 按索引范围从图像列表选取子集 |
| 图像列表组合器 | — | 将最多 10 张图像组合为图像列表 |
| 图像加载器 | — | 加载图像并输出文件名、路径、mask |

### 💫SynVow_api/Utils

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| 文件夹扫描器 | — | 扫描文件夹输出路径列表，支持图片/视频/音频/TXT 过滤 |
| 加载视频（输出路径） | — | 加载视频文件并输出路径 |
| 加载音频（输出路径） | — | 加载音频文件并输出路径 |
| SynVow 视频预览 | — | 在节点内直接预览视频 |

---

## 安装

1. 将仓库克隆至 ComfyUI 的 `custom_nodes` 目录：

   ```bash
   cd ComfyUI/custom_nodes
   git clone https://github.com/AJbeckliy/Comfyui_SynVow_api.git
   ```

2. 重启 ComfyUI。
3. 点击菜单栏 SynVow 图标，使用 SynVow 账号登录。

---

## 依赖

- Python `requests`、`aiohttp`（ComfyUI 环境通常已自带）

---

## 使用方法

1. 点击菜单栏 SynVow 图标登录。
2. 将所需节点添加到工作流。
3. 连接输入并运行，视频/图片保存到配置的输出路径。

---

## License

MIT
