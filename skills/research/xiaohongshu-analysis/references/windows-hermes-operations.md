# Windows 上 Hermes 运维操作要点

## 🚨 核心铁律：不要通过微信通道执行 gateway stop

```
死循环模式：
  我（Hermes）发 → 你收到 → 你回 → 我收到 → 我准备执行 gateway stop
  → ⚡ 网关中断（微信限流或进程退出） → 会话恢复 → 执行窗口丢失
  → 回到起点
```

**正确做法**：写自包含的 `.bat` 脚本，用户双击运行，窗口显示实时输出。成功则无缝重连，失败则自动回滚。

## Python 版本升级（0.14 → 3.12）

Hermes 0.16+ 在 Python 3.11 上有已知 Bug（#42810，空流错误）。升级前先用 `uv python list` 确认是否有 3.12+：

```bash
# 创建新 venv
uv venv --python 3.12 ./venv312

# 从旧 venv 迁移包
~/old_venv/bin/pip freeze > pkgs.txt
uv pip install -r pkgs.txt --python ./venv312/bin/python

# 重新挂 editable
cd hermes-agent && uv pip install -e ".[all]" --python ./venv312/bin/python

# 验证完成后切换
mv venv venv_old && mv venv312 venv && restart gateway
```

## Windows 批处理脚本编码坑

中文 Windows 上 `.bat` 文件的 UTF-8 中文会被 cmd.exe 按 GBK 解析产生乱码。乱码文本被当成命令执行（如 `echo` → `iiii`，`findstr` → `indstr`）。

**修复**：
1. 全英文脚本 + `chcp 65001 >nul`（推荐）
2. 或 `encoding='gbk'` 写入

## 升级脚本模板

已通过 Claude Sonnet 两轮审查的 v5 模板（2026-06-21），核心要素：
- Step 0: 完整备份（robocopy /COPY:DAT）
- Step 1: 停止 Gateway（Get-CimInstance Win32_Process，非 Get-Process）
- Step 2: git fetch + checkout
- Step 3: pip install -e ".[all]"
- Step 4: hermes config check + migrate
- Step 5: 启动 Gateway（start cmd /c，注意嵌套引号问题）
- 回滚: robocopy 从备份恢复 + git stash pop

关键踩坑：
- `Get-Process` 没有 `CommandLine` 属性 → 用 `Get-CimInstance`
- `start` 命令中变量展开后的嵌套引号 → 变量不包额外引号
- `/COPYALL` 需管理员权限 → `/COPY:DAT`
- `%date%` 中文格式含空格 → `for /f` 提取安全日期
- `enabledelayedexpansion` 未使用但引入 `!` 风险 → 移除

## git 仓库损坏修复（2026.6.21 踩坑）

`git fetch + git checkout -B origin/main` 在仓库处于 `No commits yet` 状态时可能失败（本地 commit graph 和 object database 不一致）。症状：
```
fatal: Could not parse object 'origin/main'.
fatal: attempt to fetch <sha> which is in the commit graph but not in the object database.
```

**修复**（最可靠）：删 `.git` 重建，用浅克隆：
```bash
rm -rf .git && git init && git remote add origin <url>
git fetch --depth 1 origin main
git checkout FETCH_HEAD && git checkout -b main
```

如果遇到 "Device or resource busy"，先杀残留 git 进程：`taskkill /F /IM git.exe`

## pip 丢失修复（2026.6.21 踩坑）

git checkout 后 venv 中 pip 可能丢失。修复：
```bash
python -m ensurepip --upgrade
python -m pip install -e ".[all]"
```
