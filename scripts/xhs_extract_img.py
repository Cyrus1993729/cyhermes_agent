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
    image_list = note.get("imageList", [])
    for i, img in enumerate(image_list):
        url_list = img.get("urlList", [])
        print(f"Image {i}: {len(url_list)} URLs")
        for j, u in enumerate(url_list):
            url = u.get('url', '?')
            print(f"  URL {j}: {url}")
            # Download first URL
            if j == 0:
                img_path = os.path.expanduser(f"~/xhs_cover_{i}.jpg")
                import subprocess
                subprocess.run([
                    "curl", "-s", "--max-time", "15", "-o", img_path, url
                ], check=False)
                if os.path.exists(img_path):
                    sz = os.path.getsize(img_path)
                    print(f"  Downloaded: {img_path} ({sz} bytes)")
                else:
                    print(f"  Download FAILED")
        print(f"  Size: {img.get('width', '?')}x{img.get('height', '?')}")
