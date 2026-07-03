import re, json, os

with open(os.path.expanduser("~/xhs_page2b.html"), "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

m = re.search(r"window\.__INITIAL_STATE__\s*=\s*", html)
start = m.end()
depth = 0
for i in range(start, min(len(html), start + 5000000)):
    if html[i] == "{": depth += 1
    elif html[i] == "}":
        depth -= 1
        if depth == 0:
            end = i + 1
            break

json_str = html[start:end]
json_str = re.sub(r":\s*undefined", ":null", json_str)
data = json.loads(json_str)
note_data = data.get("note", {}).get("noteDetailMap", {})
for nid, nd in note_data.items():
    note = nd.get("note", {})
    video = note.get("video", {})
    h264 = video.get("media", {}).get("stream", {}).get("h264", [])
    if h264:
        url = h264[0].get("masterUrl", "")
        # Save fresh URL
        with open(os.path.expanduser("~/xhs_video_url2.txt"), "w") as f:
            f.write(url)
        print(f"FRESH_URL: {url[:150]}")
    else:
        print("NO H264 URL")
