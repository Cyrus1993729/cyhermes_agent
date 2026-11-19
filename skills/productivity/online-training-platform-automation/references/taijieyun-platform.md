# 泰捷云学系培训平台：实测记录

适用站点（同一套系统，只换域名/学校名）：
- 苏州市顺通职业培训学校 `https://shuntong.taijieyun.com/userv3`（→ `/site/#/content`）
- 其他 `*.taijieyun.com` 站点结构和接口一致

> 以下均为 2026-11-18 实测。接口名/字段名可能随版本变，**先挂 XHR 钩子看清楚再写死**。

## 一、登录

```
入口   /userv3  → 重定向到 /site/#/content
       点「立即登录」→ /user/#/login
字段   input[placeholder*="手机号"]  input[placeholder*="密码"]
提交   button.login_btn
```

⚠️ **直接用 JS 设 `input.value` 不生效**（React 受控组件，state 不更新，点登录没反应）。
两种可行做法：
1. `fill_input(selector, text)` helper（会走真实输入事件）
2. 用原生 setter + 派发 input/change 事件，然后**用真实鼠标坐标** `click_at_xy` 点登录按钮

登录成功后 token 存在 **sessionStorage**（不是 localStorage），key 名不可靠 → 直接用请求头钩子抓。

## 二、关键接口

请求头需带：
```
MemberToken: <JWT，exp 很长>
MemberId: <useLearn.id，例如 2431>
```

| 用途 | 接口 |
|:---|:---|
| 知识点列表（含学时/状态） | `GET /index/material/mslist?msid=<subjectid>&applyid=<id>&cate=理论` |
| 知识点下的课程清单（含 length/progress/done） | `GET /index/material/list?msid=<msid>&file_type=&applyid=<id>&limit=10000&page=1` |
| 学习统计（学时） | `GET /index/user/tj?applyid=<id>` → `class_hour` / `aim_score` / `m_learn_count` / `m_count` 
| 学员档案 | `GET /index/user/userlearn?applyid=<id>` → `score` / `passit` / `pass_exam` / `exam_count_left` / `face_recog` |
| 进度上报 | `POST /index/material/addlog`（body AES 加密，**不要自己构造**） |
| 模拟/正式考试开考 | `GET /index/mock/start` 、正式考走 `#/exam_zs_page?examid=` |

**在页面上下文里查接口的写法**（`js()` 不 await Promise，必须用**同步** XHR）：

```python
def api(path):
    return js("""(() => { const x=new XMLHttpRequest();
      x.open('GET','https://shuntong.taijieyun.com%s', false);
      x.setRequestHeader('MemberToken','%s'); x.setRequestHeader('MemberId','2431');
      x.send(null); return x.responseText; })()""" % (path, TOKEN))
```

用 `async fetch` 包在 IIFE 里会返回 `None`。

## 三、进度语义（很重要）

- `mprogress`：0 ~ 1.00，`done=1` 表示看完
- **学时按知识点发放**：一个知识点下**所有课程**都 `done=1` 后才加该知识点的 `score` 学时（页面上那句「学完知识点下的所有课程方可增加对应的学时」是真的）
- 学时数 ≠ 视频总时长。实测：4 个知识点共 12 学时，底下 20 个视频加起来只有 6.18 小时
- `addlog` 的响应里能看到 `{mprogress, period, position, done, studyTime}` —— **派度是按视频播放位置记的**（`position/period`），但它照样有反快进风控

## 四、视频页 DOM

```
播放器      video.vjs-tech（aliplayer 包装 video.js）
侧边课程目录 .teacher_book_list_item  （title 属性 = 课程名）
考试/刷课题号导航 .card_item          （纯数字文本）
选项标签    label.ant-radio-wrapper   （innerText 就是「正确」「错误」或「A、xxx」）
```

⚠️ **侧边课程目录 `.teacher_book_list_item` 长度 = 0 时，说明播放器没完整初始化** → 结尾不会上报。
只改 hash 路由进入播放页容易碰到；**必须 reload 整个页面**，确认目录有内容再开始播。

## 五、可复用的守护脚本（只做这两件事）

```js
setInterval(() => {
  const btn = [...document.querySelectorAll('button')]
    .find(b => ['已知晓','我知道了'].includes((b.innerText||'').trim()));
  if (btn) btn.click();
  const v = document.querySelector('video');
  if (!v) return;
  // 🔴 只续播，绝对不要碰 playbackRate / currentTime
  if (!v.ended && v.paused && v.readyState >= 2) v.play().catch(()=>{});
}, 5000);
```

## 六、考试页结构差异（两个页面不一样，别套用）

| | 模拟考 `#/exam_mnks_page_actual?mockid=` | 正式考 `#/exam_zs_page?examid=` |
|:---|:---|:---|
| 题干起点标记 | `第N题` | `当前题`（题号不带「第N题」） |
| 切题 | `.card_item` 点击 | 同 |
| 交卷按钮 | `提交试卷` | `交 卷`（**中间有空格**，匹配要 `replace(/\\s/g,'')`） |
| 确认弹窗 | 「确定要交卷吗?」取消/确定 | 「确定交卷吗？」 |
| 结果 | 「我的成绩」+ 分 + 正确/错误/未做 | 同 |

抽题时用切片：从题面起点标记到 `上一题` 之间取 innerText，再按行拆。
单选选项格式：`A、` 和选项正文**分行**输出，解析时要 `+2` 跳。

## 七、实测数据点（2026-11-18 顺通·安全管理人员复审）

- 目标 12 学时，4 个知识点（3+3+4+2），20 个视频，总时长 6.18 小时
- 模拟考：94 分（错 6）
- 正式考：95 分（错 5），`passit=及格`、`pass_exam=是`，用时约 6 分钟 / 限时 120 分钟
- 两次风控弹窗均因倍速/倍速守护循环，**观看记录未被清空**（弹窗说的清空没真执行）
