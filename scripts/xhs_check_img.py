import re, json, os

page_path = os.path.expanduser("~/xhs_page.html")
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
    
    # Check imageList structure
    image_list = note.get("imageList", [])
    if image_list:
        print("=== imageList[0] keys ===")
        img = image_list[0]
        print(list(img.keys()))
        # Print first 500 chars of JSON
        print(json.dumps(img, ensure_ascii=False)[:1000])
    else:
        print("No imageList")
    
    # Check video cover
    video = note.get("video", {})
    if video:
        print("\n=== Video keys ===")
        print(list(video.keys()))
        image = video.get("image", {})
        print("video.image keys:", list(image.keys()) if image else "None")
        if image:
            print(json.dumps(image, ensure_ascii=False)[:1000])
