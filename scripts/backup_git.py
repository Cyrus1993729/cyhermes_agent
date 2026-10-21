"""Hermes auto backup — triggered daily by cron (no_agent)

凭证脱敏：提交前把 config.yaml 里 api_key / token / secret 之类的值替换成
***REDACTED***。只改 git index 里的那份，工作区原文件一个字都不动。
（副作用：git status 会一直显示 config.yaml 已修改，这是正常的——
  index 里是脱敏版，工作区是真版，不要以为是没提交。）

安全护栏：提交前会回读 index 中的 config.yaml，若仍能匹配到真实密钥特征，
中止并报警，绝不在脱敏失效的情况下把密钥推上去。
"""
import os
import re
import subprocess
import sys

HERMES_DIR = os.path.join(os.environ["LOCALAPPDATA"], "hermes")
CONFIG = "config.yaml"
REDACTED = "***REDACTED***"

# 行级匹配："  api_key: sk-xxx" / "- token: abc" / "password: p@ss"
SENSITIVE_LINE = re.compile(
    r"^(?P<lead>\s*(?:-\s+)?(?:api_key|api_secret|access_key|secret_key|"
    r"secret|token|password)\s*:\s*)(?P<val>.+?)\s*$",
    re.IGNORECASE,
)
# 真实密钥特征（用于提交前自检）
LEAK_PATTERN = re.compile(r"(oc_sk_[A-Za-z0-9_]{16,}|sk-[A-Za-z0-9_\-]{20,}|sk-ws-[A-Za-z0-9_\-]{10,})")


def redact_text(text):
    out = []
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        m = SENSITIVE_LINE.match(body)
        if m:
            val = m.group("val")
            if val not in ('""', "''", "null", "~") and not val.startswith(REDACTED):
                if line.endswith("\r\n"):
                    ending = "\r\n"
                elif line.endswith("\n"):
                    ending = "\n"
                else:
                    ending = ""
                out.append('%s"%s"%s' % (m.group("lead"), REDACTED, ending))
                continue
        out.append(line)
    return "".join(out)


def stage_redacted_config():
    """把脱敏后的 config.yaml 放进 index，工作区文件保持原样。"""
    src = os.path.join(HERMES_DIR, CONFIG)
    if not os.path.exists(src):
        return "missing"
    with open(src, encoding="utf-8", errors="replace") as f:
        raw = f.read()
    red = redact_text(raw)
    if red == raw:
        return "nochange"
    blob = subprocess.run(["git", "hash-object", "-w", "--stdin"],
                          input=red.encode("utf-8"), capture_output=True).stdout.decode().strip()
    if not re.fullmatch(r"[a-f0-9]{40,64}", blob or ""):
        return "blobfail"
    r = subprocess.run(["git", "update-index", "--add", "--cacheinfo",
                        "100644,%s,%s" % (blob, CONFIG)], capture_output=True)
    return "ok" if r.returncode == 0 else "indexfail"


def index_leaks():
    """回读 index 里的 config.yaml，检查是否还留有真实密钥。"""
    r = subprocess.run(["git", "show", ":" + CONFIG], capture_output=True)
    text = r.stdout.decode("utf-8", "replace")
    hits = LEAK_PATTERN.findall(text)
    return hits


def main():
    os.chdir(HERMES_DIR)

    subprocess.run(["git", "add", "-A"], capture_output=True)
    state = stage_redacted_config()

    if state in ("blobfail", "indexfail"):
        print("BACKUP ABORTED: config.yaml 脱敏失败（%s），未提交，避免泄露密钥" % state)
        return 1

    leaks = index_leaks()
    if leaks:
        print("BACKUP ABORTED: 暂存区 config.yaml 仍含 %d 处疑似密钥，未提交" % len(leaks))
        return 1

    r = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True)
    if r.returncode == 0:
        return 0  # 无变化，静默

    c = subprocess.run(["git", "commit", "-m", "auto backup"], capture_output=True)
    if c.returncode != 0:
        print("BACKUP FAILED: git commit error")
        print(c.stderr.decode("utf-8", "replace")[:500])
        return 1

    p = subprocess.run(["git", "push"], capture_output=True, text=True)
    if p.returncode != 0:
        print("BACKUP FAILED: git push error")
        print((p.stderr or "")[:600])
        print("Manual: cd %LOCALAPPDATA%\\hermes && git push")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
