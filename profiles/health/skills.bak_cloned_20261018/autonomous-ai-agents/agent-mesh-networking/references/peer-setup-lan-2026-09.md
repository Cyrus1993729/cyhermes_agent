# hermes peer 双机接线实操（2026-09-02 本机实测记录）

## 本机实测状态（老机，LAN 192.168.0.112）

- Hermes **v0.21.0** (2026.8.31 发行，upstream c5c9aa8d / local 86b50fb4)；`hermes peer --help` 有 add/set/list/remove/dm/run/status/stop 子命令
- gateway 运行中：Windows 计划任务 `Hermes_Gateway` → VBS (`$LOCALAPPDATA\hermes\gateway-service\Hermes_Gateway.vbs`) → `pythonw -m hermes_cli.main gateway run`
- api_server 平台已启用，但 **host=127.0.0.1, port=8642**（config.yaml `platforms.api_server.extra`）——只监听回环，跨机不可达，这是接线最大阻塞点
- `hermes peer list` → `No peers registered`（未注册任何 peer）

## 只读诊断路径（先跑这些再动手）

1. `hermes --version`；`hermes peer --help` —— 确认 v0.21+ 且命令存在
2. `hermes gateway status` —— 进程在不在（计划任务名 Hermes_Gateway）
3. 读 config.yaml `platforms.api_server` 段：`enabled` / `extra.host` / `extra.port` ← host 必须 0.0.0.0 才能跨机
4. `ipconfig | grep IPv4` —— 本机 LAN IP（GBK 中文系统 ipconfig 输出中文，用 `grep -a IPv4`）
5. `netstat -ano | grep <port>` —— 确认监听 + 绑定地址（绑 127.0.0.1 说明没改 host）
6. key 位置：`.env` 里没有 → `reg query "HKCU\Environment" /v API_SERVER_KEY`（64 位 hex）；或 psutil 读 gateway 进程 environ
7. 鉴权测试：`curl http://127.0.0.1:<port>/health`（公开，返回 ok）；`curl /v1/models` 无 key → 401 `{"error":{"message":"Invalid gateway API key (API_SERVER_KEY)"}}`

## 接线步骤（每台机各做）

1. api_server `extra.host` 改 `0.0.0.0`（config.yaml，或 `API_SERVER_HOST` 环境变量覆盖）
2. Windows 防火墙放行入站 TCP <port>（本机 8642；专用网络配置文件）
3. 重启 gateway 使配置生效（Windows 上需用户手动：杀 PID 后 `schtasks /run` 或重启电脑）
4. 双方各执行一次：`hermes peer add <名字> --url http://<对方LAN-IP>:<port> --key <对方API_SERVER_KEY>`（name 为小写 slug；key 写入 ~/.hermes/.env）
5. `hermes peer list` 确认双边互见
6. 验证：`hermes peer dm <对方名> "test"` → 消息进对方 canonical Bot Chat 并回回复即打通

## 坑

- **host=127.0.0.1 只绑回环**：本机 curl 通、对面连不上——先看 netstat 绑定地址再怀疑防火墙
- key 不在 .env 时别急着生成新的：先查 `HKCU\Environment`；gateway 进程环境里也有（64 位）
- Windows 防火墙默认拦入站（同网段也拦），需显式放行端口
- peer 是**异步交棒**：消息不实时插入对面运行中的对话，等对方执行完回传——「老机派活、新机执行」模式正匹配
- 跨机共享另一台机的 IP：同 WiFi 直接用 LAN IP；`hermes peer add --url` 例子为 http://spark.lan:8377（端口按实际，本机 8642）
