# GPT-5.6 处理图片任务配方(2026-09-08 实测:隔玻璃反光去除)

用户原话纠正:「不是用api调用gpt5.6sol,是用之前调用codex的方式」→ 让 GPT-5.6 处理图片 =
`codex exec -i <原图> -s danger-full-access` 让它自己写脚本并运行。

## 调用骨架(bash)
```bash
mkdir -p /c/Users/Administrator/<task_dir> && cd /c/Users/Administrator/<task_dir>
cp "$LOCALAPPDATA/hermes/cache/images/img_*.jpg" input.jpg   # 拷成干净名
uv venv .venv && uv pip install --python .venv/Scripts/python.exe opencv-python-headless numpy  # 本机 pip 缺失,用 uv 建专用 venv,勿装 hermes venv
CODEX="$LOCALAPPDATA/OpenAI/Codex/bin/$(ls "$LOCALAPPDATA/OpenAI/Codex/bin" | head -1)/codex.exe"
export HTTP_PROXY=http://127.0.0.1:10808 HTTPS_PROXY=http://127.0.0.1:10808
"$CODEX" exec --skip-git-repo-check --sandbox danger-full-access -C "C:/Users/Administrator/<task_dir>" \
  -c 'model="gpt-5.6-sol"' -i "C:/Users/Administrator/<task_dir>/input.jpg" < prompt.txt
```
注:--sandbox 需 danger-full-access 才能让 codex 写/跑脚本;read-only 只够审查。

## Prompt 关键要素
- 目标边界写死:保分辨率/保原画面细节,只处理 X;禁止调色/锐化/改构图/新增内容
- 给出预先目检到的缺陷区域描述(供定位)+ 要求"用代码精确判定,勿误删真实内容"
- 指明 venv python 绝对路径(防它调用无依赖的系统 python)、输入/输出绝对路径、JPEG quality=95
- 要求脚本独立可运行、stdout 打印处理组数/耗时/最终尺寸;输出分辨率须与原图一致
- 限定工作目录,勿碰外部文件

## 验证(不信 codex 自报)
1. cv2.imread 核对输出 shape == 原图 shape(分辨率保真)
2. 自己重跑一遍脚本看 stdout(组数/耗时/尺寸)
3. 做 before/after 上下对比图(vconcat+copyMakeBorder+putText 标签)→ vision_analyze 目检三问:反光是否减、有无副作用(模糊/色斑/细节破坏)、目标达成度
4. 交付 MEDIA: 路径;如实说明残留(单帧隔玻璃反光是加法叠加,物理上无法 100% 还原玻璃下画面,残留属正常)

## 反光去除技法(本次 opencv 实测有效,供复用作参考)
- 硬性条带反光:ROI 内 top-hat + Canny + HoughLinesP 按角度/长度过滤 → line mask → cv2.inpaint(TELEA)
- 光斑/眩光:天空 ROI 内 (亮度-大σ背景)>阈值 & 低饱和 → connectedComponents 按面积过滤 → HoughCircles + 共线校验 → inpaint
- 大范围半透明雾膜:**只修低频层**(GaussianBlur 出低频 → 对低频 inpaint 估底色 → delta×feather(alpha) 加回原图),保留原高频纹理——大面积直接 inpaint 会抹掉真实细节
- 色偏膜:L*a*b* 通道只把 a/b 向邻域中性化(alpha 0.1 级),不动 L 亮度
- mask 边缘 feather + dilate,防 inpaint 采样把反光 halo 拷回修复区

## 坑
- 前台 timeout(420s)先于 codex 完成:判定看产物文件,不看命令退出码;长任务用 background
- 跑完 `ps aux | grep codex` 查残留进程
- codex 输出仍走 codex\n…tokens used 结构;ANSI 清洗姿势同 SKILL.md 正文
