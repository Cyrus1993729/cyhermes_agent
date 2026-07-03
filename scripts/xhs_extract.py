import re, json, os

page_path = os.path.expanduser("~/xhs_page.html")

with open(page_path, "r", encoding="utf-8", errors="replace") as f:
    html = f.read()

m = re.search(r"window\.__INITIAL_STATE__\s*=\s*", html)
if not m:
    print("NOT FOUND")
    exit(1)

start = m.end()
depth = 0
end = start
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
print(f"JSON parsed OK, top-level keys: {list(data.keys())[:20]}")

# Try note path
note_data = data.get("note", {}).get("noteDetailMap", {})
note_ids = list(note_data.keys())
print(f"noteDetailMap keys: {note_ids}")

for nid, nd in note_data.items():
    note = nd.get("note", {})
    desc = note.get("desc", "")
    title = note.get("title", "")
    type_ = note.get("type", "")
    print(f"\n=== Note ID: {nid} ===")
    print(f"Title: {title}")
    print(f"Type: {type_}")
    print(f"Desc length: {len(desc)}")
    print(f"Desc preview: {desc[:300]}")
    
    user = note.get("user", {})
    print(f"Author: {user.get('nickname', '?')} (ID: {user.get('userId', '?')})")
    
    interact = note.get("interactInfo", {})
    print(f"Likes: {interact.get('likedCount', '?')}, Collects: {interact.get('collectedCount', '?')}, Comments: {interact.get('commentCount', '?')}, Shares: {interact.get('shareCount', '?')}")
    
    video = note.get("video", {})
    if video:
        media = video.get("media", {})
        stream = media.get("stream", {})
        h264 = stream.get("h264", [])
        if h264:
            print(f"Video URL: {h264[0].get('masterUrl', '?')[:150]}")
        print(f"Video duration: {video.get('duration', '?')}s")
        image = video.get("image", {})
        if image:
            print(f"Cover image URLs count: {len(image.get('urlList', []))}")
            for u in image.get("urlList", [])[:2]:
                print(f"  Cover: {u.get('url', '')[:150]}")
    
    image_list = note.get("imageList", [])
    if image_list:
        print(f"Image list: {len(image_list)} images")
    
    print(f"\n=== FULL DESC ===")
    print(desc)
