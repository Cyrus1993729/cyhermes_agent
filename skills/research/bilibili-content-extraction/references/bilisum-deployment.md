# BiliSum — B站视频 AI 理解工具部署记录

## 项目信息

- **仓库**: https://github.com/lycohana/BiliSum (★329, MIT)
- **版本**: v1.19.1 (2026-06-15)
- **定位**: 本地优先的 B站/YouTube 视频 AI 总结与知识库桌面应用
- **部署路径**: `C:\Users\Administrator\BiliSum\`

## 部署环境

| 组件 | 详情 |
|:---|:---|
| OS | Windows 10 |
| Python | 3.12.13 (通过 `uv python install 3.12` 安装) |
| 后端 | FastAPI + SQLite |
| 端口 | `127.0.0.1:3838` |
| 数据目录 | `C:\Users\Administrator\AppData\Local\bilisum\data\` |
| Token 文件 | `data/auth.json`（自动生成） |

## 启动命令

```bash
# 必须清除代理（B站需要直连）
unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
cd C:/Users/Administrator/BiliSum
.venv/Scripts/python.exe -m video_sum_service
```

## 配置（.env）

```env
VIDEO_SUM_HOST=127.0.0.1
VIDEO_SUM_PORT=3838
VIDEO_SUM_TRANSCRIPTION_PROVIDER=faster-whisper
VIDEO_SUM_WHISPER_MODEL=small
VIDEO_SUM_WHISPER_DEVICE=cpu
VIDEO_SUM_LLM_ENABLED=true
VIDEO_SUM_LLM_PROVIDER=openai-compatible
VIDEO_SUM_LLM_BASE_URL=https://api.deepseek.com/v1
VIDEO_SUM_LLM_MODEL=deepseek-chat
VIDEO_SUM_LLM_API_KEY=<DeepSeek key>
# VLM 视觉理解（Kimi 2.6）
VIDEO_SUM_VISUAL_NOTE_MODE=vlm_integrated
VIDEO_SUM_VISUAL_VLM_PROVIDER=openai-compatible
VIDEO_SUM_VISUAL_EVIDENCE_BASE_URL=https://api.moonshot.cn/v1
VIDEO_SUM_VISUAL_EVIDENCE_MODEL=<Kimi vision model>
VIDEO_SUM_VISUAL_EVIDENCE_API_KEY=<Kimi key>
```

## 运行时依赖安装

BiliSum 的 Python 依赖默认不包含 ASR/知识库等大组件，需要运行时安装：

- **本地 Whisper**: `POST /api/v1/asr/local/install`（安装 faster-whisper + torch）
- **知识库**: `POST /api/v1/knowledge/install`（安装 chromadb + sentence-transformers）
- **FunASR**: `POST /api/v1/asr/funasr/install`

## B站 风控处理

1. 确保后端启动时**不带** HTTP_PROXY/HTTPS_PROXY 环境变量（B站需直连）
2. 通过 BiliSum 内置扫码登录：`POST /api/v1/bilibili/cookies/qrcode`
3. 二维码有效期 180 秒
4. 登录后 cookies 自动保存，后续请求无需重复

## API 工作流

```
POST   /api/v1/auth/session          → 获取访问 token
POST   /api/v1/videos/probe          → 探测视频 URL（B站/YouTube）
POST   /api/v1/videos/{id}/tasks     → 创建处理任务（转写+摘要）
GET    /api/v1/tasks/{id}/events/stream → SSE 进度流
GET    /api/v1/tasks/{id}/result     → 获取结果（结构化 JSON）
POST   /api/v1/tasks/{id}/visual-evidence → 触发 VLM 画面分析
POST   /api/v1/tasks/{id}/exports/markdown → 导出 Markdown
```

## VLM 成本估算

10 分钟视频，12 帧画面，一次完整 VLM 分析：
- 总 token：~8,000-19,000
- 按 Kimi 2.6 价格：约 ¥0.02-0.04/次
