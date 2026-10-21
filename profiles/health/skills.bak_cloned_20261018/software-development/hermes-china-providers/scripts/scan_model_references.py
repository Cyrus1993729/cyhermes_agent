# -*- coding: utf-8 -*-
"""扫全库找某个模型名/配置值的所有活跃引用点（换模型名、换 provider 时用）。

为什么要这个脚本：手工列清单必漏。 2026-10-08 换 deepseek-v4-flash -> deepseek-v4.1-flash 时，
手写的"四步"清单只盖住 config.yaml + 3 个脚本，实际漏了 cron/jobs.json 的 prompt 正文文本、
models.json、TrendRadar 的 config、以及 user 之前用 `| head -20` 把 skills/ 结果截断掉的那批。

用法：
    python scan_model_references.py deepseek-v4-flash
    python scan_model_references.py deepseek-v4-flash deepseek-chat   # 多个词
    python scan_model_references.py deepseek-v4-flash --docs           # 连技能文档一起扫
    python scan_model_references.py deepseek-v4-flash --root D:\\Workspace

退出码：0 = 无命中（干净），1 = 有命中。改名后重跑一次，看是否归零。

注意（实测坑）：
  * 默认**不扫** skills/**.md —— 技能文档/复盘里提到旧模型名是**历史记录**，不是要改的配置。
    只有当你想知道"哪份文档的说法过时了"时才加 --docs。
  * 也不要拿 `grep ... | head -20` 去数残留：会被截断，看起来像扫过了实际没扫完。
    这个脚本自己汇总总数，不会截断。
"""
import os
import sys

HERMES = os.path.expanduser(r"~\AppData\Local\hermes")

# 目录名黑名单：备份 / 会话 / 缓存 / 内核源码 / 构建产物
SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".venv-*",
    "backups", "state-snapshots", "sessions", "cache", "tmp", "logs",
    "desktop", ".curator_backups", "hermes-agent", "hermes-agent_backup_周日202606",
    ".hub", "output", "archives", "dist", "build",
}
# 文件名前缀/后缀黑名单：备份、缓存、快照
SKIP_FILE_PREFIX = ("backup_", "models.json.bak", "config.yaml.bak")
SKIP_FILE_EXACT = {
    "auth.json", "channel_directory.json", "gateway_state.json",
    "models_dev_cache.json", "ollama_cloud_models_cache.json", "provider_models_cache.json",
    "pip_freeze_old.txt",
}
SCAN_EXT = {".py", ".json", ".yaml", ".yml", ".sh", ".bat", ".env", ".toml", ".ini", ".cmd"}
DOC_EXT = {".md"}


def should_skip_dir(name):
    if name in SKIP_DIRS:
        return True
    return name.startswith("backup_") or name.endswith(".bak")


def walk(root, needles, include_docs):
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not should_skip_dir(d)]
        for fn in filenames:
            if fn in SKIP_FILE_EXACT or fn.startswith(SKIP_FILE_PREFIX):
                continue
            ext = os.path.splitext(fn)[1].lower()
            ok = ext in SCAN_EXT or (include_docs and ext in DOC_EXT)
            if not ok:
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, 1):
                        for nd in needles:
                            if nd in line:
                                hits.append((path, i, nd, line.strip()[:160]))
                                break
            except (OSError, UnicodeError):
                continue
    return hits


def main():
    args = [a for a in sys.argv[1:]]
    include_docs = "--docs" in args
    args = [a for a in args if not a.startswith("--")]
    roots = [HERMES]
    if "--root" in sys.argv:
        idx = sys.argv.index("--root")
        if idx + 1 < len(sys.argv):
            roots.append(sys.argv[idx + 1])
        args = [a for a in args if a != sys.argv[idx + 1]] if idx + 1 < len(sys.argv) else args
    if not args:
        print(__doc__)
        return 2

    total = 0
    for root in roots:
        if not os.path.isdir(root):
            print(f"[跳过] 目录不存在: {root}")
            continue
        hits = walk(root, args, include_docs)
        total += len(hits)
        if hits:
            print(f"\n=== {root} （{len(hits)} 处）===")
            for path, ln, nd, snippet in sorted(hits):
                rel = os.path.relpath(path, root)
                print(f"  {rel}:{ln}  [{nd}]  {snippet}")

    print(f"\n合计命中: {total}")
    if total:
        print("提示：逐个确认是否属于「活跃配置」（要改）还是「历史文档/旧名兼容过滤」（保留）。")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
