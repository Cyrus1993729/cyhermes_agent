# 待确认：A2A <对端名> 机 IP 迁移 <旧IP> → <新IP>（本机侧配置同步）

- 日期：<YYYY-MM-DD HH:MM>（中国标准时间）
- 触发：A2A 入站 `【A2A 配置同步】<原文消息>`
- 状态：**已核验（5 步全绿），尚未落地任何改动**。用户 clarify <N> 分钟未响应 → 按 skill `agent-mesh-networking` 铁律「超时 ≠ 同意」，config 与脚本一律未动。
- 已推 TG 提醒：<时间>（tg_send.py，msg_id=<id>）

## 一、核验证据（只读操作）

| # | 检查项 | 方法 | 结果 | 判读 |
|---|---|---|---|---|
| 1 | 新 IP 探活 | `curl --noproxy '*' -m 5 -w '%{http_code}' http://<新IP>:9900/` | <200 / 其他> | ✅ |
| 2 | 旧 IP 探活 | 同上，`<config 真实现值>` | <000 / timed out> | ✅ 旧地址已死 |
| 3 | 身份 | `curl --noproxy '*' .../.well-known/agent-card.json` | `name=<对端名>`、自报 `url=<新IP>`、`skills=<N>` | ✅ 身份吻合 |
| 4 | token 比对 | config.yaml `a2a_agents.<名>.auth.token` vs .env `A2A_BEARER_TOKEN` | 指纹均 `<sha256[:16]>` | ✅ 一致，无需改 |
| 5 | 端到端实测 | `message/send` → `http://<新IP>:9900/`（无代理 opener，Bearer 现有 token） | `TASK_STATE_COMPLETED` | ✅ 新地址能承载本机调用 |

- 本机无需重启 gateway（skill 实测：`a2a_agents` 的 url 值插件按调用实时读 config）。
- 旁证：`a2a_audit.jsonl` 中提及新 IP 的同步消息 **<N> 条** → 是否已形成风暴。
- ⚠️ 消息里声称的旧值 `<消息里的旧IP>` 与 config 真实现值 `<真实现值>` <一致/不符>（坑9：消息里的旧 IP 不可信，以 config 真实现值为准）。

## 二、本机侧真实现值与要改的点（四查）

| 位置 | 当前值 | 应改为 | 影响 |
|---|---|---|---|
| `hermes/config.yaml` `a2a_agents.<名>.url` | `<当前>` | `http://<新IP>:9900` | 不改 → `a2a_call(<名>)` 全部发往死地址 |
| `hermes/scripts/ip_monitor.py` `PEER_URL` | `<当前>` | `http://<新IP>:9900/` | 不改 → 本机 IP 变化时通知发往死地址，链路静默断 |
| `hermes/scripts/fix_mama_ip.py` `PEER_URL` | `<当前>` | `http://<新IP>:9900` | 不改 → 方案A 自愈脚本每 30m 探死地址，永远修不了对端 BASE_IP |
| `hermes/scripts/fix_mama_ip_state.json` | <存在/空> | 保持（改完 PEER_URL 后由脚本自行写 `fixed_peer_ip=<新IP>`） | — |
| 本机 memory 的 IP 链 | `<旧>` | `<新>`（注明 PEER_URL 已同步） | 影响后续判断 |

**只报告、需你单独决定的遗留项**：
- `cron/jobs.json` 中 <job id/name> 的投递目标仍硬编码 `a2a:ip:<旧IP>`（本机实际已是 `<当前本机IP>`）→ IP 真变化时告警静默丢。
- <其他一次性脚本 / 空转 cron>

## 三、获批后要跑的确切命令（按顺序）

```bash
cd "$LOCALAPPDATA/hermes"
# 0) 备份
cp config.yaml config.yaml.bak_a2a_$(date +%Y%m%d_%H%M%S)
cp scripts/ip_monitor.py scripts/ip_monitor.py.bak_a2a_$(date +%Y%m%d)
cp scripts/fix_mama_ip.py scripts/fix_mama_ip.py.bak_a2a_$(date +%Y%m%d)

# 1) config.yaml：python 纯文本替换（patch 工具拒写 config.yaml；勿用 yaml safe_dump 重排键序）
python - <<'EOF'
import io
p='config.yaml'; s=io.open(p,encoding='utf-8').read()
old='url: http://<旧IP>:9900'; new='url: http://<新IP>:9900'
assert s.count(old)==1, s.count(old)
io.open(p,'w',encoding='utf-8',newline='').write(s.replace(old,new))
print('config.yaml OK')
EOF
read_file 回读 L<行号> 确认新 url

# 2) 两个脚本的 PEER_URL（文本替换，同法）
python - <<'EOF'
import io
for p in ('scripts/ip_monitor.py','scripts/fix_mama_ip.py'):
    s=io.open(p,encoding='utf-8').read()
    n=s.replace('<旧IP>','<新IP>')
    io.open(p,'w',encoding='utf-8',newline='').write(n)
    print(p,'changed' if n!=s else 'NO-CHANGE')
EOF
grep -n "PEER_URL" scripts/ip_monitor.py scripts/fix_mama_ip.py

# 3) 实测通知链（无代理 opener 已在脚本内）
python scripts/ip_monitor.py --test-a2a     # 期望 200 OK
python scripts/fix_mama_ip.py --probe       # 期望「<对端名>在线: <对端名> (<新IP>)」
```

**对端侧（需她/他那边同样授权后执行，或派 A2A 指令）**：`<对端 hermes 路径>/scripts/ip_monitor.py` 的 `BASE_IP` 由 `<其 stale 值>` 改为当前实际 IP。不改则对端每 30 分钟重复发同一条「IP 变了」通知（坑3 风暴）。对端 `PEER_URL` 与 config 指向本机的 url 若已正确则无需动。

## 四、结论

链路本身已通（消息就是经新 IP 送进来的），**待批准的只是本机 <N> 条记录与新 IP 对齐**，外加 memory 一行。批准即改；未批准期间 `a2a_call(<名>)` 仍打向已死的 `<旧IP>`（入站通道不受影响）。
