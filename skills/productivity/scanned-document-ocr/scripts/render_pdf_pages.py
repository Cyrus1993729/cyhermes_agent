#!/usr/bin/env python3
"""Render every page of a PDF to PNGs (for OCR hand-off to vision_analyze).

Requires PyMuPDF — run it without installing anything:

    uv run --quiet --with pymupdf python render_pdf_pages.py <pdf> <outdir> [dpi]

Why this instead of pdftoppm: poppler often isn't installed on Windows, and
marker-pdf is a 3-5GB download. `uv run --with pymupdf` pulls a ~25MB wheel into
an ephemeral env and touches nothing else.

Prints one line per page (dims + KB) plus a total, so you can sanity-check the
render before spending vision calls on it.
"""

import os
import sys

import pymupdf


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    src = sys.argv[1]
    out = sys.argv[2]
    dpi = int(sys.argv[3]) if len(sys.argv) > 3 else 180

    if not os.path.exists(src):
        print(f"ERROR: not found: {src}")
        return 1

    os.makedirs(out, exist_ok=True)
    doc = pymupdf.open(src)
    print(f"pages: {doc.page_count}   dpi: {dpi}   ->  {out}")

    total_kb = 0
    for i, page in enumerate(doc):
        pix = page.get_pixmap(dpi=dpi)
        fn = os.path.join(out, f"p{i + 1:02d}.png")
        pix.save(fn)
        kb = os.path.getsize(fn) // 1024
        total_kb += kb
        print(f"  p{i + 1:02d}  {pix.width}x{pix.height}  {kb} KB")

    print(f"total {total_kb} KB")
    print(
        f"\nNext: vision_analyze each pNN.png. If more than ~5 pages, delegate the\n"
        f"batch to a subagent instead of pulling every image into the main context."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
