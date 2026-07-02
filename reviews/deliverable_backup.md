# Hermes 备份方案（v2 — 经千问审查修正）

## 要保护的资产

| 资产 | 价值 | 丢了就 |
|:---|:---|:---|
| `memories/` | 18条，数月偏好/习惯/决策规则 | 从头调教 |
| `skills/` | 30+个（审查/契约/MoA等） | 重写几个月 |
| `scripts/` | qwen_review / mem_gc / review_trend | 审查系统失效 |
| `config.yaml` | 模型/网关/MCP/代理 | 重新配半天 |
| `reviews/` | 审查日志，纵向评估 | 趋势归零 |
| `lessons.md` `safety_invariants.md` `model_routing.md` | 知识沉淀 | 重新沉淀 |
| cron 状态 | 3个定时任务 | 全部重建 |

## 备份方式：GitHub 私有仓库

```
~/.hermes/ → git init → GitHub 私有仓库 → cron 每天 git push
```

## .gitignore

```
cache/         # 几百MB缓存，可重新下载
auth.json      # API密钥，不进git
.env           # API密钥
logs/          # 网关日志
hermes-agent/  # 源码，可重新安装
__pycache__/
*.pyc
*.key          # 兜底：密钥文件
*.pem
*secret*
```

## Cron：每天自动备份

```
cron: 0 8 * * *（每天早8点，与黄金周报/记忆体检同窗口）
动作: cd ~/.hermes && git add -A && git commit -m "backup $(date +%Y-%m-%d)" && git push
```

> Git 凭证前提：需在 Windows 上配置 SSH key 或 GitHub PAT，否则 cron 自动 push 会静默失败。
> 配置后验证：`ssh -T git@github.com`

## 恢复流程（换电脑后）

1. 安装 Hermes：`curl -fsSL https://... | bash`
2. Clone 到数据目录：`git clone <私有仓库> ~/.hermes/`
   - Windows 上 `~/.hermes/` 即 `%LOCALAPPDATA%\hermes\`
3. 配置 Git 凭证：SSH key 或 PAT
4. 重设 API 认证：`hermes auth`
5. 检查代理配置：确认 config.yaml 中代理地址
6. 启动网关：`hermes gateway start`

## 执行原则

出方案 → 用户确认 → 执行。不自动操作。
