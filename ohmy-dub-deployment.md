# OhMyDub-webui 部署与使用指南

> 全自动视频翻译配音系统 — YouTube/Bilibili 视频下载、人声分离、语音识别、翻译、TTS 配音、字幕合成一站式流水线。

---

## 目录

- [1. 项目架构](#1-项目架构)
- [2. 硬件与软件要求](#2-硬件与软件要求)
- [3. 部署步骤](#3-部署步骤)
  - [3.1 后端部署](#31-后端部署)
  - [3.2 前端部署](#32-前端部署)
  - [3.3 GPT-SoVITS 部署（可选但推荐）](#33-gpt-sovits-部署可选但推荐)
- [4. 环境配置](#4-环境配置)
  - [4.1 .env 文件](#41-env-文件)
  - [4.2 前端设置页面](#42-前端设置页面)
- [5. 使用方法](#5-使用方法)
  - [5.1 启动服务](#51-启动服务)
  - [5.2 提交流程](#52-提交流程)
  - [5.3 流水线各阶段说明](#53-流水线各阶段说明)
- [6. API 参考](#6-api-参考)
- [7. 最佳实践](#7-最佳实践)
  - [7.1 GPU 内存管理](#71-gpu-内存管理)
  - [7.2 TTS 参考音频](#72-tts-参考音频)
  - [7.3 字幕与字体](#73-字幕与字体)
  - [7.4 工作流策略](#74-工作流策略)
  - [7.5 断点续传与缓存](#75-断点续传与缓存)
- [8. 故障排除](#8-故障排除)
- [9. 开发指南](#9-开发指南)

---

## 1. 项目架构

```
┌──────────────────────────────────────────────────────────┐
│                     OhMyDub-webui                          │
│                                                           │
│  ┌──────────┐    ┌──────────┐    ┌────────────────────┐  │
│  │ Frontend  │───▶│ Backend  │───▶│  Pipeline Stages   │  │
│  │ Next.js   │    │ FastAPI  │    │   (9 stages)       │  │
│  │ :3000     │◀───│ :8000    │    └────────────────────┘  │
│  └──────────┘    └────┬─────┘           │                  │
│                        │                 │                  │
│                 ┌──────┴──────┐    ┌─────┴─────┐           │
│                 │   SQLite    │    │  Worker   │           │
│                 │  database   │    │  Thread   │           │
│                 └─────────────┘    └───────────┘           │
│                                                           │
│  ┌──────────────────────────────────────────────────┐     │
│  │              External Services                    │     │
│  │  GPT-SoVITS API (:9880)   │   OpenAI/DeepSeek    │     │
│  └──────────────────────────────────────────────────┘     │
└──────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16, React 19, Tailwind CSS 4, shadcn/ui |
| 后端 | Python 3.10+, FastAPI, uvicorn |
| 数据库 | SQLite (ohmy-dub.sqlite) |
| 翻译 | OpenAI-compatible API (默认 DeepSeek) |
| 语音识别 | Whisper (large-v3-turbo / small) 或 FunASR |
| 人声分离 | Demucs (HTDemucs) |
| TTS 引擎 | GPT-SoVITS（推荐中文）或 VoxCPM |
| 音视频处理 | ffmpeg 8.0+ |

### 流水线（9 个阶段）

```
download → separate → asr → asr_fix → translate
  → split_audio → tts → merge_audio → merge_video
```

---

## 2. 硬件与软件要求

### 最低硬件要求

| 组件 | 要求 |
|------|------|
| GPU | **NVIDIA RTX 4060 8GB** 或更高（推荐 12GB+） |
| 内存 | 16 GB RAM |
| 存储 | 50 GB 可用空间（用于模型缓存和工作目录） |
| CPU | 4 核以上 |

### GPU 显存分配（RTX 4060 8GB 实测）

| 组件 | 显存占用 | 说明 |
|------|----------|------|
| GPT-SoVITS | ~1.4 GB (FP16) | 常驻 GPU |
| Whisper large-v3-turbo | ~2 GB | 按需加载，阶段结束时释放 |
| Demucs | ~3 GB | 按需加载，阶段结束时释放 |
| 合计峰值 | ~6.4 GB | 8GB 卡可运行 |

### 软件要求

- **Windows 10/11**（推荐，项目主要在 Windows 上开发测试）
- **Python 3.10~3.11**（3.10.11 实测通过）
- **CUDA 12.1** + cuDNN（PyTorch 2.5.1+cu121 实测通过）
- **Node.js 20+**
- **ffmpeg 8.0+**（项目自动检测）
- **Git**（用于克隆子模块）

---

## 3. 部署步骤

### 3.1 后端部署

#### 步骤 1：克隆仓库

```bash
git clone https://github.com/your-repo/OhMyDub-webui.git
cd OhMyDub-webui
git submodule update --init --recursive
```

#### 步骤 2：创建 Python 虚拟环境

```bash
# 在项目根目录创建虚拟环境
python -m venv .venv
# 激活
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

#### 步骤 3：安装 PyTorch（CUDA 版本）

```bash
# CUDA 12.1 版本
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
```

> 请根据你的 CUDA 版本选择对应的 PyTorch 版本。CUDA 版本可用 `nvidia-smi` 查看。

#### 步骤 4：安装后端依赖

```bash
pip install -r requirements.txt
```

#### 步骤 5：安装 ffmpeg

项目启动时会自动在以下路径查找 ffmpeg：
- `ffmpeg/ffmpeg-8.0.1-essentials_build/bin/`
- `C:\Program Files\ffmpeg\bin\`
- WinGet 安装路径

推荐方式：将 ffmpeg 解压到项目根目录：

```bash
# 目录结构应为:
# OhMyDub-webui/
#   ffmpeg/
#     ffmpeg-8.0.1-essentials_build/
#       bin/
#         ffmpeg.exe
#         ffprobe.exe
```

也可从 https://www.gyan.dev/ffmpeg/builds/ 下载 `ffmpeg-essentials_build`。

#### 步骤 6：配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 OpenAI API Key 等配置
```

#### 步骤 7：启动后端

```bash
# 从项目根目录运行
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir backend
```

> **重要**：必须添加 `--app-dir backend` 参数，否则会出现 `ModuleNotFoundError: No module named 'app'` 错误。`WORKFOLDER` 路径是相对于项目根目录解析的，所以必须从根目录运行。

首次启动会自动：
- 创建 `data/` 目录（数据库、日志、Cookie）
- 创建 `workfolder/` 目录（任务工作目录）
- 初始化 SQLite 数据库表
- 将之前中断的活跃任务标记为失败

#### 验证后端

```bash
curl http://localhost:8000/api/health
# 返回: {"status":"ok"}
```

### 3.2 前端部署

#### 步骤 1：安装依赖

```bash
cd apps/web
npm install
cd ../..
```

#### 步骤 2：配置 API 地址（可选）

默认情况下前端自动连接 `http://localhost:8000`。如需修改：

```bash
# apps/web/.env.local
NEXT_PUBLIC_API_BASE_URL=http://your-host:8000
```

#### 步骤 3：构建前端

```bash
npm run build:web
# 或: npm --prefix apps/web run build
```

#### 步骤 4：启动前端

```bash
npm --prefix apps/web run start
# 或开发模式: npm --prefix apps/web run dev
```

访问 http://localhost:3000

### 3.3 GPT-SoVITS 部署（可选但推荐）

> 中文配音推荐使用 GPT-SoVITS，音质远超 VoxCPM。

#### 步骤 1：获取 GPT-SoVITS

```bash
git clone https://github.com/RVC-Boss/GPT-SoVITS.git
cd GPT-SoVITS
```

#### 步骤 2：创建独立虚拟环境

```bash
python -m venv .venv
.venv\Scripts\activate
```

#### 步骤 3：安装依赖

```bash
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

#### 步骤 4：安装 NLTK 数据（关键步骤）

GPT-SoVITS 需要 NLTK 的词性标注数据，否则会报错：

```bash
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
```

#### 步骤 5：启动 API 服务

```bash
python api_v2.py -a 0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

GPT-SoVITS 启动后会在第一个请求时加载模型，首次加载需要约 30-60 秒（下载模型权重）。

#### 系统结构

```
┌─────────────────────┐      HTTP TTS 请求       ┌──────────────────────┐
│  OhMyDub Backend     │ ───────────────────────▶  │  GPT-SoVITS API     │
│  (FastAPI :8000)    │ ◀───────────────────────  │  (uvicorn :9880)    │
│  共享 GPU（主机进程）│     返回 WAV 音频         │  独立 Python 进程   │
└─────────────────────┘                           └──────────────────────┘
```

关键要点：
- GPT-SoVITS 是**独立进程**，不是子进程或线程
- 两个进程共享同一张 GPU，各自分配自己的显存
- OhMyDub 通过 HTTP 调用 GPT-SoVITS（默认 `http://localhost:9880`）

---

## 4. 环境配置

### 4.1 .env 文件

完整配置项说明：

```ini
# ── 路径配置 ──
WORKFOLDER=./workfolder
# 工作目录，存储每个任务的视频、音频、字幕等
# 相对于项目根目录解析（不是 CWD！）

MODEL_CACHE_DIR=./data/modelscope
# 模型缓存目录，ModelScope 下载的模型存放位置

# ── GPU 设备 ──
DEVICE=cuda
# 可选: cuda, cuda:0, cuda:1, cpu
# 多 GPU 时指定具体编号

# ── 翻译 API（OpenAI 兼容）──
OPENAI_BASE_URL=https://api.deepseek.com
# 任何 OpenAI-compatible API 均可
# 常见选项:
#   - https://api.deepseek.com (DeepSeek)
#   - https://api.openai.com/v1 (OpenAI)
#   - http://localhost:1234/v1 (本地 LLM)

OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# API 密钥

OPENAI_MODEL=deepseek-v4-flash
# 模型名称

OPENAI_TRANSLATE_CONCURRENCY=50
# 翻译并发数，DeepSeek 等高并发 API 可设大值

# ── Whisper ASR ──
WHISPER_MODEL=small
# 可选: tiny, base, small, medium, large, large-v3-turbo
# small 约 2GB 显存，large-v3-turbo 约 4GB
# 8GB 显存推荐: small 或 medium

WHISPER_DOWNLOAD_ROOT=D:\AI\OhMyDub-webui\models\ASR\whisper
# Whisper 模型缓存路径

# ── FunASR（备选 ASR）──
FUNASR_MODEL=iic/SenseVoiceSmall
FUNASR_VAD_MODEL=fsmn-vad

# ── VoxCPM（备选 TTS）──
VOXCPM_MODEL=OpenBMB/VoxCPM2
VOXCPM_LOAD_DENOISER=false
VOXCPM_CFG_VALUE=2.0
VOXCPM_INFERENCE_TIMESTEPS=8
VOXCPM_MIN_REFERENCE_MS=1200

# ── GPT-SoVITS ──
GPT_SOVITS_API_URL=http://localhost:9880
# GPT-SoVITS API 地址

GPT_SOVITS_TIMEOUT=120
# 单次 TTS 请求超时（秒），长文本可能需要更长时间

GPT_SOVITS_REF_MIN_MS=3000
GPT_SOVITS_REF_MAX_MS=10000
# 参考音频时长范围（毫秒）
# GPT-SoVITS 要求 3~10 秒

# ── 代理（仅 yt-dlp 下载使用）──
HTTP_PROXY=
YTDLP_PROXY_PORT=
```

### 4.2 数据库设置

部分配置存储在 SQLite 数据库 `data/ohmy-dub.sqlite` 的 `settings` 表中，可通过前端页面或 API 修改：

| 键 | 说明 | 默认值 |
|----|------|--------|
| `tts.engine` | TTS 引擎选择 | `voxcpm` |
| `tts.gpt_sovits_api_url` | GPT-SoVITS API 地址 | `http://localhost:9880` |
| `openai.base_url` | OpenAI 兼容 API 地址 | 同 .env |
| `openai.api_key` | API 密钥 | 同 .env |
| `openai.model` | 翻译模型 | 同 .env |
| `ytdlp.proxy_port` | yt-dlp 代理端口 | 空 |

> **设置优先级**：数据库 settings 表 > .env 文件 > 代码默认值。前端修改的设置会保存到数据库。

---

## 5. 使用方法

### 5.1 启动服务

**一键启动（需要两个终端）**：

```bash
# 终端 1：后端
cd D:\AI\OhMyDub-webui
.venv\Scripts\activate
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --app-dir backend

# 终端 2：前端
cd D:\AI\OhMyDub-webui
npm --prefix apps/web run dev
```

**如使用 GPT-SoVITS（第三个终端）**：

```bash
cd D:\GPT-SoVITS
.venv\Scripts\activate
python api_v2.py -a 0.0.0.0:9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

### 5.2 提交流程

1. 打开浏览器访问 http://localhost:3000
2. 进入 **设置页面**：
   - 填入 OpenAI/DeepSeek API 信息（Base URL + API Key + 模型名）
   - 选择 TTS 引擎为 "GPT-SoVITS"（如已部署）
   - 如需代理，设置代理端口
3. 在首页输入 YouTube 或 Bilibili 视频 URL
4. 点击提交，系统自动开始流水线处理

也可直接使用 API 提交：

```bash
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=VIDEO_ID"}'
```

### 5.3 流水线各阶段说明

| 阶段 | 名称 | 功能 | 耗时参考 |
|------|------|------|----------|
| 1 | **download** | 下载视频 + 音频 | 取决于视频长度和网速 |
| 2 | **separate** | Demucs 人声分离 | 10 分钟视频约 54 秒 |
| 3 | **asr** | Whisper 语音识别 | 10 分钟视频约 49 秒 |
| 4 | **asr_fix** | 句子边界修正/重新分段 | 几秒 |
| 5 | **translate** | OpenAI 翻译 | 取决于句子数和 API 速度 |
| 6 | **split_audio** | 按翻译条目切分参考音频 | 几秒 |
| 7 | **tts** | TTS 生成配音 | GPT-SoVITS 每句 3~15 秒 |
| 8 | **merge_audio** | 配音 + BGM 混音 | 几秒 |
| 9 | **merge_video** | 视频 + 配音 + 字幕合成 | 几秒~几分钟 |

**总计**：10 分钟视频大约需要 **20~40 分钟**，其中 TTS 占大部分时间。

---

## 6. API 参考

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| POST | `/api/tasks` | 创建任务 |
| GET | `/api/tasks` | 任务列表（支持 `?limit=N`） |
| GET | `/api/tasks/current` | 当前任务 |
| GET | `/api/tasks/{id}` | 任务详情（含各阶段状态） |
| DELETE | `/api/tasks/{id}` | 删除任务（含文件） |
| POST | `/api/tasks/{id}/rerun` | 重新运行（清旧数据） |
| POST | `/api/tasks/{id}/resume` | 恢复失败任务 |
| GET | `/api/tasks/{id}/log` | 获取任务日志 |
| GET | `/api/tasks/{id}/artifact/final-video` | 下载/预览成品视频 |
| GET | `/api/cookies/youtube` | 查看 YouTube Cookie |
| POST | `/api/cookies/youtube` | 上传 YouTube Cookie |
| GET | `/api/settings/openai` | 获取 OpenAI 设置 |
| POST | `/api/settings/openai` | 保存 OpenAI 设置 |
| POST | `/api/settings/openai/models` | 列出可用模型 |
| GET | `/api/settings/tts` | 获取 TTS 设置 |
| POST | `/api/settings/tts` | 保存 TTS 设置 |
| GET | `/api/settings/ytdlp` | 获取代理设置 |
| POST | `/api/settings/ytdlp` | 保存代理设置 |

---

## 7. 最佳实践

### 7.1 GPU 内存管理

- 流水线会在每个阶段结束后调用 `torch.cuda.empty_cache()` 释放显存
- 如果 GPU 内存不足（OOM），尝试：
  - 使用较小的 Whisper 模型（`WHISPER_MODEL=small` 而非 `large-v3-turbo`）
  - 关闭其他占用 GPU 的程序
  - 为 GPT-SoVITS 添加启动参数 `--low_vram` 或使用 `--fp16`（实测 FP16 约 1.4GB）
- 8GB 显存是**刚好够用**的水平,不要在后台运行其他 GPU 应用

### 7.2 TTS 参考音频

- GPT-SoVITS 要求参考音频在 **3~10 秒**之间
- 系统会自动从人声分离结果中选取符合条件的片段作为参考音频
- 可能你依然会遇到"参考音频不符合要求"的问题：
  - 检查人声分离质量（过短的片段会被跳过）
  - 减少 `GPT_SOVITS_REF_MIN_MS` 但不要低于 2000
  - 增加 `GPT_SOVITS_REF_MAX_MS` 但不要超过 15000
- 建议将 `GPT_SOVITS_TIMEOUT` 设为 120 秒以上，长句子 TTS 生成可能需要较长时间

### 7.3 字幕与字体

- 中文硬字幕使用 `Microsoft YaHei UI` 字体（Windows 预装）
- 英文字幕使用 `Arial`
- 竖屏视频字幕字号大于横屏（portrait 24px vs landscape 18px）
- 中文字幕过大时可调整 `ffmpeg.py` 中的 `SUBTITLE_FONT_SIZES` 字典
- 字幕位置底部，竖屏 `MarginV=70`，横屏 `MarginV=5`

### 7.4 工作流策略

- **先小后大**：首次使用先测试 1~3 分钟的短视频
- **缓存利用**：已完成阶段的输出会被缓存。重复提交相同 URL 会直接使用缓存
- **断点续传**：失败的流水线可以恢复从失败阶段继续执行，不需要从头开始
- **重启安全**：后端重启后正在运行的任务会被标记为失败，恢复即可继续
- **多视频排队**：单线程 FIFO 队列，依次处理多个任务

### 7.5 断点续传与缓存

流水线缓存机制：

```
阶段成功完成 → 数据库标记 "succeeded" → 再次运行跳过执行
失败后恢复 → 失败阶段及之后阶段重置为 "pending"
已成功的阶段保留数据
```

- 调用 `POST /api/tasks/{id}/resume` 恢复失败任务
- 调用 `POST /api/tasks/{id}/rerun` 则清空全部数据重新开始
- 每个任务的工作目录在 `workfolder/{source_name}/{session_name}/`

---

## 8. 故障排除

### 常见错误及解决方案

#### 后端无法启动

```
ModuleNotFoundError: No module named 'app'
```

**原因**：uvicorn 从错误的工作目录启动，缺少 `--app-dir` 参数。

**解决**：
```bash
# 正确方式
uvicorn backend.app.main:app --app-dir backend --host 0.0.0.0 --port 8000
# 必须在项目根目录执行
```

#### WORKFOLDER 路径错误

```
工作目录解析为 backend/workfolder/ 而非预期的 workfolder/
```

**原因**：`.env` 中的 `WORKFOLDER=./workfolder` 原来相对于 CWD 解析，当 CWD 是 `backend/` 时路径出错。

**解决**：已修复为相对于 `REPO_ROOT`（项目根目录）解析。只需从项目根目录启动即可。

#### GPT-SoVITS 文件不存在

```
"workfolder/xxx/xxxx.wav not exists"
```

**原因**：数据库中的 `session_path` 存储的是相对路径，GPT-SoVITS 作为独立进程从不同工作目录运行，找不到文件。

**解决**：已修复为在 `gpt_sovits.py` 中对所有路径调用 `.resolve()` 转换为绝对路径。

#### ffmpeg 字幕合成失败

```
Exit code 4294967274 (0xFFFFFFFA / SIGABRT)
```

**原因**：Windows 路径中的 `D:` 盘符冒号被 ffmpeg filter 解析为选项分隔符。同时 `force_style` 参数值中的逗号被解析为 filter chain 分隔符。

**解决**：
- `subtitle_filter()` 改为返回 `(filter_string, cwd)` 元组
- ffmpeg 调用时指定 `cwd=subtitle_file.parent`，使用相对路径引用字幕文件
- 添加 `_escape_ass_style()` 转义 `force_style` 中的特殊字符（逗号、反斜杠、&）

#### GPT-SoVITS 参考音频超出范围

```
"参考音频在3~10秒范围外，请更换！"
```

**原因**：代码原来使用 2000ms 最小阈值，但 GPT-SoVITS 要求 3000~10000ms。

**解决**：
- 添加 `GPT_SOVITS_REF_MIN_MS=3000` 和 `GPT_SOVITS_REF_MAX_MS=10000` 配置
- `_find_reference()` 同时检查最小和最大时长
- 每个片段的参考音频也经过完整的范围校验

#### 翻译 API 报错

```
429 Too Many Requests 或 401 Unauthorized
```

**原因**：API 限频或密钥无效。

**解决**：
- 降低 `OPENAI_TRANSLATE_CONCURRENCY`（默认 50）
- 检查 API Key 和 Base URL
- 确认模型名称正确

#### Whisper 显存不足

```
CUDA out of memory
```

**解决**：
- 切换到更小的模型：`WHISPER_MODEL=small`
- 确保其他 GPU 进程已关闭
- 检查 GPT-SoVITS 是否使用 FP16 模式

---

## 9. 开发指南

### 项目结构

```
OhMyDub-webui/
├── apps/web/                  # Next.js 前端
│   └── src/
│       ├── app/               # 页面路由
│       ├── components/        # UI 组件
│       └── lib/api.ts         # API 客户端
├── backend/
│   └── app/
│       ├── main.py            # FastAPI 入口 + 路由
│       ├── config.py          # 配置管理（路径、设备、API）
│       ├── database.py        # SQLite 数据库操作
│       ├── pipeline.py        # 流水线编排器
│       ├── worker.py          # 后台工作线程
│       ├── stages.py          # 阶段定义
│       ├── sources.py         # 视频来源配置
│       ├── youtube.py         # URL 解析
│       └── adapters/          # 各阶段适配器
│           ├── ytdlp.py       # 视频下载
│           ├── demucs.py      # 人声分离
│           ├── whisper_asr.py # 语音识别
│           ├── openai_translate.py # 翻译
│           ├── gpt_sovits.py  # GPT-SoVITS TTS
│           ├── voxcpm.py      # VoxCPM TTS
│           ├── audio.py       # 音频处理
│           └── ffmpeg.py      # 字幕 + 视频合成
├── data/                      # 运行时数据
│   ├── ohmy-dub.sqlite          # SQLite 数据库
│   ├── cookies/               # Cookie 文件
│   └── logs/                  # 任务日志
├── workfolder/                # 任务工作目录
├── ffmpeg/                    # ffmpeg 可执行文件
└── .env                       # 环境变量
```

### 数据库 Schema

```sql
-- 任务表
CREATE TABLE tasks (
  id TEXT PRIMARY KEY,              -- 任务 ID(同时也是视频 ID)
  url TEXT NOT NULL,                -- 视频 URL
  title TEXT,                       -- 视频标题
  status TEXT NOT NULL,             -- queued/running/succeeded/failed
  current_stage TEXT,               -- 当前阶段名称
  session_path TEXT,                -- 工作目录路径
  final_video_path TEXT,            -- 成品视频路径
  error_message TEXT,               -- 错误信息
  created_at TEXT NOT NULL,         -- ISO 8601
  started_at TEXT,
  completed_at TEXT
);

-- 阶段表（FK → tasks.id CASCADE）
CREATE TABLE task_stages (
  task_id TEXT NOT NULL,
  name TEXT NOT NULL,               -- 阶段名称（英文标识）
  label TEXT NOT NULL,              -- 阶段显示名
  status TEXT NOT NULL,             -- pending/running/succeeded/failed
  started_at TEXT,
  completed_at TEXT,
  last_message TEXT,                -- 阶段最后消息
  error_message TEXT,               -- 错误信息
  PRIMARY KEY (task_id, name),
  FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
);

-- 设置表（键值存储）
CREATE TABLE settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
```

### 添加新的 TTS 引擎

1. 在 `backend/app/adapters/` 下创建新适配器，实现 `generate_tts(translation_file, vocals_dir, session) -> Path`
2. 在 `config.py` 的 `tts_engine_label()` 中添加标签映射
3. 在 `pipeline.py` 的 `_tts()` 中添加 import 分支
4. 在前端设置页面添加对应的配置项

### 添加新的视频来源

在 `sources.py` 中添加新的 `SourceConfig` 条目，指定：
- URL 匹配函数
- 是否使用代理
- Cookie 文件名
- ASR 语言和目标语言

---

> 最后更新: 2026-05-17
