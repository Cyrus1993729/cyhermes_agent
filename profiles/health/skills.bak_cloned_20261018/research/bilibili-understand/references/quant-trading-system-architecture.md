# 量化回测系统 - 架构评审总结

> 来源: BV1fUQZBxEZN (小宇量化 "我用AI搭了一套量化交易回测系统")
> 日期: 2026-06-16

## 技术堆栈

- Java 21 + Spring Boot 4.0.3 + Maven + Clean Architecture
- TimescaleDB (PostgreSQL 时序扩展) — Docker 部署
- React 19 + TypeScript + Vite 7 + ECharts 5 + Bootstrap 5
- FMP API 作为美股数据源

## 架构

```
web-app (:3000) → web-service (:8181) → market-data-service (:8182) → [TimescaleDB | FMP API]
                    BFF 层                  Clean Architecture 四层
```

## Claude Code (Opus 4.8) 金融视角评审

**综合评分: 2/10（作为"AI 工程演示"6/10）**

致命问题:
- 16笔交易样本，标准误 ≈9.8%，置信区间 [62%, 100%] — 无法区分真实优势和运气
- 高收益+超高胜率+极少交易 = Bailey & López de Prado 过拟合三件套
- 无滑点、无交易成本、无基准对比(S&P 500)、无样本外测试
- 没有夏普比率、索提诺比率、卡玛比率
- FMP API 单一数据源，未验证复权处理

## 对黄金投资者的适用性

**完全错配（三重错配: 标的×市场×频率）**

用户是黄金ETF/积存金低频投资者（一年1-2次操作），该系统为美股日线短线设计。
更有价值的方向: 黄金定投 vs 一次性投入回测（Python + AkShare，几十行代码）。

## 5个提示词结构

1. 项目骨架 (Java+Maven+TimescaleDB+trading-common)
2. 市场数据服务 (FMP API → DB 缓存)
3. BFF 服务 (web-service，CORS)
4. React 前端 (深色主题K线图)
5. 一键启动脚本

提示词从 https://download.jzhu.net 获取，需邮箱验证。
