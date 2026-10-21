---
name: pdf-processing
description: PDF page extraction, image-based/scanned PDF handling, watermark removal, and document image cleanup.
version: 1.0.0
platforms: [windows]
metadata:
  hermes:
    tags: [pdf, image-processing, watermark, document]
---

# PDF Processing

Extract pages as images, handle scanned/image-based PDFs, remove watermarks and overlays from document screenshots.

## Triggers

- User sends a PDF and needs pages extracted as images
- User asks to remove watermarks/annotations from document images
- PDF text extraction fails (PyPDF2/pdfplumber returns empty) — the PDF is likely image-based

## Toolchain

| Tool | Purpose |
|------|---------|
| PyMuPDF (`fitz`) | Page-to-image extraction. **Preferred** over pdf2image (needs poppler, often missing on Windows). |
| PIL/Pillow + numpy | Pixel-level analysis and image manipulation |
| `vision_analyze` | Visual inspection of pages, watermark location, verification |

Install: `uv pip install PyMuPDF Pillow numpy`

## Workflow

### Step 1: Extract pages as images

```python
import fitz, os

doc = fitz.open(pdf_path)
page = doc[page_num]  # 0-indexed
pix = page.get_pixmap(dpi=300)  # 300 DPI for high quality
pix.save(output_path)
doc.close()
```

### Step 2: Locate watermarks

Use `vision_analyze` with `annotate=true` to get a rough location, then refine with pixel analysis:

```python
from PIL import Image
import numpy as np

img = Image.open(image_path)
arr = np.array(img)

# Watermark text on white bg appears as gray pixels (~150-235 range)
# Scan specific regions for non-white clusters
wm_mask = (arr[:,:,0] >= 140) & (arr[:,:,0] <= 235)
# ... narrow down to precise bbox
```

### Step 3: Remove watermarks

For watermarks on white/light background — simplest: paint white over the region.

```python
arr[y_start:y_end, x_start:x_end] = [255, 255, 255]
Image.fromarray(arr).save(output_path)
```

For watermarks on colored/chart backgrounds, use `vision_analyze` to verify the fill doesn't damage data.

### Step 4: Verify

Always run `vision_analyze` on the output to confirm:
- Watermarks fully removed
- Chart data intact
- No visible fill artifacts

## Pitfalls

| Pitfall | Solution |
|:---|:---|
| **Unicode filenames on Windows** | PDF filenames with full-width characters (：U+FF1A etc.) break literal paths. Use `os.listdir()` + `for f in os.listdir(dir): if 'keyword' in f: path = os.path.join(dir, f)` instead of hardcoded paths. |
| **Bash interprets `&` in Python** | In MSYS2/git-bash, `&` in inline Python (bitwise AND) is parsed as shell background operator. Write Python to a `.py` file with `write_file` then `python script.py` — never inline complex numpy/PIL operations. |
| **pdf2image needs poppler** | Not available on Windows by default. Always prefer PyMuPDF (`fitz`). |
| **Text extraction returns empty** | Scanned/image-based PDFs have no embedded text. Use `page.get_pixmap()` → `vision_analyze` instead. |
| **Large PDFs (20MB+)** | Extract only target pages via `fitz.open(pdf)[page_num]`, don't render the whole document. |
| **Watermark fill leaves visible blocks** | Match fill color to local background. For white backgrounds use pure white [255,255,255]. For off-white pages, sample the local bg color first. |

## Verified Patterns

- J.P. Morgan Chartbook (67 pages, 24MB, scanned): single-page extraction at 300 DPI, two watermarks removed (white fill on white bg), verified clean.
