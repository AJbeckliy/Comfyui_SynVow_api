# Comfyui_SynVow_api

ComfyUI 用于 SynVow 集成的自定义节点，支持账号登录、图像/视频/音频生成、提示词工具和透明 PNG 素材生成。

---

## 更新日志

### 2026-08-06
- **视频节点**
  - 新增 `SynVow MiniMax 文生视频` / `SynVow MiniMax 首尾帧视频` / `SynVow MiniMax 多模态参考视频`（模型 `MiniMax-H3`，分辨率 `2K`，时长 4～15 秒）
- **图像节点**
  - 修复 `gpt-image-2-4k-qy`模型问生图问题。 
- **账号 / Web**
  - 悬浮菜单新增「公告」按钮。

### 2026-08-03
- **图像节点**
  - 即梦新增 `即梦5.0-pro`；
  - 新增 `SynVow GK1.5` / `(T_batch)` / `(I_batch)` / `(T_I_batch)`，请求模型为 `grok-image-1.5-稳定`
  - 新增 `SynVow 悠船 文生图`、`SynVow 悠船 多图融合`、`SynVow 悠船 图像编辑`
  - GPT-Image-2 新增 `gpt-image-2-1k-qy` / `gpt-image-2-4k-qy`；1K 模型固定按 1K 请求，4K 模型支持 1K / 2K / 4K，速度快，价格实惠。
  - NanoBanana 新增 `nanobanana2-qy` / `nanobananapro-qy`；速度快，价格实惠。
- **视频节点**
  - `SynVow Seedance2.0 视频生成 (720P)` 修复。
- **账号 / Web**
  - 登录 / 注册支持手机号与邮箱双通道
- **文本模型**
  - Gemini 新增 `gemini-3.5-flash-lite-稳定` / `gemini-3.6-flash-稳定`
  - GPT 新增 `gpt-5.5-2607` / `gpt-5.6-sol-2607`

### 2026-07-22
- **视频 / 音频节点更新**
  - 新增 `SynVow Seedance`（`/image/edit`：全能 / mini / face / 分辨率 / 编辑 / 延长）
  - **保留**旧接口节点 `SynVow Seedance2.0 视频生成 (720P)`（`/video/generate`，实际模型 `seedance_2_720p`）
  - 新增 `SynVow Grok Video`（`grok-1.5-video`）
  - 新增 `SynVow Omni-Flash`（`Omni-Flash-Ext` / `omni-flash-preview`）
  - 新增 `SynVow Veo31`（`veo3.1`）
  - 新增 `SynVow Suno 灵感模式` / `SynVow Suno 自定义模式`（`suno5.5`）
  - 视频节点输出 ComfyUI `VIDEO`；Suno 输出 `AUDIO` 及路径/链接/歌词
  - 短视频解析模型对齐：抖音 / 小红书 / 视频号 / bilibili / YouTube
- **图像节点**
  - 新增 `SynVow 即梦` / `(T_batch)` / `(I_batch)` / `(T_I_batch)`（模型 `即梦5.0`，分辨率 `2K`/`3K`）
  - GPT-Image-2 新增 `gpt-image-2-2607`；NanoBanana 新增 `nano-banana-2-lite-2607`
- **GPT-Image-2 产品与提示词工作流**
  - 新增 `SynVow GPT-Image-2 产品六合一`：产品精修、产品融入场景、模糊图片高清、移除物品、蒙版引导产品功能科技光效和扩图
  - 新增 **一镜到底提示词工作流（测试版 / Beta）**：人物设定、场景设定、路线分镜和 Seedance LLM 提示词编译器
  - 一镜到底当前为测试版本，提示词结构、节点参数和输出效果后续会根据实际测试继续调整
- **代码清理**
  - 提交/轮询/下载/上传公共逻辑收敛到 `media_common.py`
  - 删除重复下载重试与重复的 `IS_CHANGED` 实现
  - 新视频/音频节点已注册取消轮询按钮

### 2026-07-01
- **新增透明 PNG 素材工作流节点**
  - `SynVow 透明素材提示词生成器`：按场景生成可复用透明素材提示词
  - `SynVow GPT-Image-2 Alpha (T_batch)`：URL 直出透明 PNG 生成（提示词列表批量）
  - `SynVow 透明PNG保存预览`：按原始 URL 保存 RGBA PNG，保留真实透明通道

### 2026-06-30
- **代码清理**：删除无用/重复/失效代码，统一逻辑，行为保持不变
  - 删除失效的模型池筛选脚本、孤立的后端接口及相关死代码
  - 音视频加载、分页样式、时间/请求工具等重复逻辑统一收敛
- **模型与界面对齐前端**
  - GPT-Image-2 新增 `gpt-image-2-官方` 模型，图像输入扩展至 9 张
  - Gemini 模型列表与默认模型对齐
  - 模型价格弹窗改为卡片网格样式，显示名只取真实模型名
- **修复消费记录"资源"打开**：按模型类型（图/视/音）正确解析链接，修复视频、音频记录取不到链接的问题

### 2026-06-23
- **集成 YMAI 提示词节点**：新增 `YM-爆款封面`、`YM-故事板`、`YM-人物情绪`、`YM-角色卡`，复用 SynVow 登录与接口，无需额外配置

### 2026-06-01
- **新增模型 `nano-banana-2-低价`、`nano-banana-pro-低价`**（NanoBanana 系列节点：单图生成、T_batch、I_batch、TI_batch）
  - 低价版采用 `ratio` / `resolution` / `files` 请求结构，结果从 `result.url` 解析

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
| SynVow 即梦 | 即梦5.0 / 即梦5.0-pro | 文生图·图生图 |
| SynVow 即梦 (T_batch) | 即梦5.0 / 即梦5.0-pro | 提示词列表批量 |
| SynVow 即梦 (I_batch) | 即梦5.0 / 即梦5.0-pro | 提示词 × 多组图批量 |
| SynVow 即梦 (T_I_batch) | 即梦5.0 / 即梦5.0-pro | 提示词与图像组配对批量 |
| SynVow GK1.5 | grok-image-1.5-稳定 | 文生图·图生图（最多 1 张参考图） |
| SynVow GK1.5 (T_batch) | grok-image-1.5-稳定 | 提示词列表批量 |
| SynVow GK1.5 (I_batch) | grok-image-1.5-稳定 | 提示词 × 图像列表批量 |
| SynVow GK1.5 (T_I_batch) | grok-image-1.5-稳定 | 提示词与图像配对批量 |
| SynVow 悠船 文生图 | Midjourney_文生图 | 文生图（支持 oref/sref/dref） |
| SynVow 悠船 多图融合 | Midjourney_多图融合 | 2–4 张图融合 |
| SynVow 悠船 图像编辑 | Midjourney_图像编辑 | 单图编辑（支持 oref/sref/dref） |
| SynVow GPT-Image-2 | gpt-image-2 | 文生图·图生图 |
| SynVow GPT-Image-2 (T_batch) | gpt-image-2 | 批量文生图 |
| SynVow GPT-Image-2 (I_batch) | gpt-image-2 | 批量图生图 |
| SynVow GPT-Image-2 (T_I_batch) | gpt-image-2 | 文生图 + 图生图混合批量 |
| SynVow GPT-Image-2 Alpha (T_batch) | gpt-image-2 | URL 直出透明 PNG（提示词列表批量） |
| SynVow GPT-Image-2 产品六合一 | gpt-image-2 | 产品精修 / 融入场景 / 高清 / 移除 / 光效 / 扩图 |

### 💫SynVow_api/api/视频

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow Seedance | seedance2.0-* | `/image/edit`：文/图/视频/音频参考；输出路径/URL/信息 |
| SynVow Seedance2.0 视频生成 (720P) | seedance_2_720p | `/image/edit` + `content[]`，固定 720P；输出路径/URL/信息 |
| SynVow Grok Video | grok-1.5-video | 文/图生视频（最多 6 张参考图） |
| SynVow Omni-Flash | Omni-Flash-Ext / omni-flash-preview | 图/视频参考生视频 |
| SynVow Veo31 | veo3.1 | 文/图生视频（最多 2 张参考图，1080p） |
| 短视频解析 | 平台解析 | 抖音 / 小红书 / 视频号 / bilibili / YouTube 无水印下载 |

### 💫SynVow_api/api/音频

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow Suno 灵感模式 | suno5.5 | 灵感模式音乐生成（输出 `AUDIO`） |
| SynVow Suno 自定义模式 | suno5.5 | 自定义模式音乐生成（标题/标签，输出 `AUDIO`） |

### 💫SynVow_api/api/文本

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| SynVow Gemini 提示词生成 | gemini-* | 通过 Gemini 生成提示词 |
| SynVow Gemini 提示词生成 (T_batch) | gemini-* | 提示词列表批量 |
| SynVow GPT 提示词生成 | gpt-* | 通过 GPT 生成提示词 |
| GPT-Image-2 文生图提示词控制器 | gemini-* / gpt-* | 通过 LLM 优化图像生成提示词 |
| 图生图提示词控制器 | gemini-* / gpt-* | 参考图提示词优化 |
| 🛒 电商详情页提示词生成器 | gemini-* | 多屏电商详情页提示词生成，支持产品参考图与风格参考图 |
| GPT-image2详情页规划 | gemini-* | 规划长卷详情页叙事与视觉母版 |
| GPT-image2详情页结构 | gemini-* | 将叙事 JSON 转为分屏结构蓝图 |
| GPT-image2详情页批量提示词 | gemini-* | 生成批量 GPT-image2 提示词列表 |
| 详情页图像列表顺序拼接长图 | — | 按列表顺序纵向拼接长图 |
| SynVow 透明素材提示词生成器 | gemini-* | 生成透明 PNG 素材提示词与素材规划 |
| 一镜到底-人物设定提示词 | — | 一镜到底人物设定（测试版） |
| 一镜到底-场景设定提示词 | — | 一镜到底场景设定（测试版） |
| 一镜到底-路线分镜提示词 | — | 一镜到底路线分镜（测试版） |
| 一镜到底-Seedance提示词编译器（LLM） | — | 一镜到底 Seedance 提示词编译（测试版） |

### 💫SynVow_api/api/文本 - YM 提示词节点

| 节点名称 | 模型 | 描述 |
|----------|------|------|
| YM-爆款封面 | SynVow 文本/多模态模型 | 根据标题、主题和可选参考图生成封面设计提示词 |
| YM-故事板 | SynVow 文本/多模态模型 | 根据脚本生成分镜表提示词和分镜视频提示词 |
| YM-人物情绪 | SynVow 文本/多模态模型 | 根据人物图片和情绪方向生成视频提示词 |
| YM-角色卡 | SynVow 文本/多模态模型 | 生成人物三视图、面部三视图、面部增强三视图、服装参考或角色卡提示词 |

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
| SynVow 透明PNG保存预览 | — | 按原始 URL 保存 RGBA PNG 并预览 |

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

- Python `requests`、`aiohttp`、`Pillow`、`numpy`（ComfyUI 环境通常已自带）

---

## 使用方法

1. 点击菜单栏 SynVow 图标登录。
2. 将所需节点添加到工作流。
3. 连接输入并运行，视频/图片保存到配置的输出路径。

---

## License

MIT

YMAI 节点已融合进现有 SynVow API 项目结构。节点代码位于 `py/api/ymai_*.py`，提示词资源位于 `py/prompts/ymai_*`。
