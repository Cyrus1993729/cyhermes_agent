# Telegram DM 话题：分域会话 + 话题级 skill 绑定

源码核实于 2026-10-18（`~/.hermes/hermes-agent`，插件式适配器）。

## 配置格式

```yaml
platforms:
  telegram:
    extra:
      dm_topics:
        - chat_id: 8938729624          # 目标私聊的 chat_id
          topics:
            - name: "健康"
              skill: health-analysis   # ← 话题级 skill 绑定
              icon_color: 7322096      # 可选
              thread_id: 100           # 首次创建后由 bot 回写，勿手填
            - name: "投资"
              skill: null
```

## 行为（逐条源码证据）

### 1. bot 自动建话题，thread_id 回写 config

`plugins/platforms/telegram/adapter.py` → `_setup_dm_topics()`：
- 读 `config.extra['dm_topics']`（list of `{chat_id, topics:[...]}`）
- **已有 `thread_id` 的话题** → 直接载入内存缓存，不调 API
- **没有 `thread_id` 的** → 调 `createForumTopic` 创建，然后**把 thread_id 写回 `config.yaml`**
  （`atomic_config_write`，路径 `platforms.telegram.extra.dm_topics`）
- 结论：**只需在 config 里写 `name`，话题由 bot 自己建出来**，重启后靠回写的 thread_id 复用。

### 2. 话题 = 独立 session（上下文真隔离）

`gateway/run.py` 注释与实现：
> Telegram topic lanes persist a `(chat_id, thread_id) -> session_id` row

即每个话题各自映射到一个 session_id。**在该话题里说话，拿不到别的会话的对话历史。**
这正是用户要的「不会拿到平时聊的财经/美股上下文」。

### 3. 话题绑定的 skill 会自动加载

同文件：解析出 `topic_info.get("skill")` → `topic_skill` → 传给 `auto_skill=topic_skill`。
**每条消息都带上该 skill**，等价于「这个 bot 的操作手册」——
用户设想的「在 skill 里写清楚数据文件在哪」正是靠这个机制自动生效的。

### 4. 斜杠命令 `/topic`

`hermes_cli/commands.py` 命令注册表：
```python
CommandDef("topic", "Enable or inspect Telegram DM topic sessions", "Session",
           gateway_only=True, args_hint="[off|help|session-id]")
```
gateway-only；`_handle_topic_command` 在 `gateway/run.py`。
⚠️ 这是**要打命令**的路径，不满足本用户「零手动切换」的要求，
仅作调试/查看用。

### 5. 群组话题同理

`config.extra['group_topics']` 走同一套 skill 绑定逻辑（`gateway/run.py:10914` 附近）。

## 与独立 profile 的关系

| | DM 话题 | 独立 profile |
|:--|:--|:--|
| 进程 | 同一个 gateway | 独立实例 |
| 会话 | 独立 session | 独立 sessions 目录 |
| skill | 话题级（profile 的 skill 全集里挑） | profile 级全集 |
| memory | **共享**（同一 profile） | **独立** |
| bot token | 同一个 | 需另配（一个 profile 只认一个 `telegram.token`） |

**一个 profile 只能配一个 Telegram bot token** —— 想要第二个 bot 必须建第二个 profile。
这条决定了「同 bot 分域」与「独立 bot」是两条路，不能混。

## 🔴 未验证项（用前必测）

Telegram 的 DM 话题功能依赖客户端支持；Hermes 侧走 Bot API `createForumTopic`。
**本机（2026-10-18）尚未实测过这条通道。**
落地第一步应是「建一个测试话题看能不能出现」，而不是直接改正式配置。
若通道不通 → 退回独立 profile 方案（数据层已就绪，迁移零成本）。
