import re, json, os

page_path = os.path.expanduser("~/xhs_page2.html")
with open(page_path, "r", encoding="utf-8", errors="replace") as f:
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
    desc = note.get("desc", "")
    title = note.get("title", "")
    type_ = note.get("type", "")
    print(f"Title: {title}")
    print(f"Type: {type_}")
    print(f"Desc length: {len(desc)}")
    
    user = note.get("user", {})
    print(f"Author: {user.get('nickname', '?')}")
    
    interact = note.get("interactInfo", {})
    print(f"Likes: {interact.get('likedCount', '?')}, Collects: {interact.get('collectedCount', '?')}, Shares: {interact.get('shareCount', '?')}")
    
    video = note.get("video", {})
    if video:
        media = video.get("media", {})
        stream = media.get("stream", {})
        h264 = stream.get("h264", [])
        if h264:
            print(f"Video URL: {h264[0].get('masterUrl', '?')[:120]}")
        dur = video.get("duration")
        print(f"Duration: {dur}s" if dur else "Duration: unknown")
        # Cover image
        image = video.get("image", {})
        if image:
            for ul in image.get("urlList", []):
                print(f"Cover: {ul.get('url', '')[:150]}")
    
    # imageList
    image_list = note.get("imageList", [])
    for i, img in enumerate(image_list[:3]):
        info_list = img.get("infoList", [])
        for il in info_list:
            if il.get("imageScene") == "WB_DFT":
                print(f"Image {i} DFT: {il.get('url', '')[:150]}")
    
    print(f"\n=== FULL DESC ===")
    print(desc)
