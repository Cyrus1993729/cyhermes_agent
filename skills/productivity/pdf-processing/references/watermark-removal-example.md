# Watermark Removal Reference

## Pattern: white-fill on light backgrounds

This was the exact workflow for removing two watermarks ("研报免费" top-right, "YouTube @老厉害" bottom-right) from a J.P. Morgan Chartbook page.

### Locating watermarks with pixel analysis

```python
from PIL import Image
import numpy as np

img = Image.open('page.png')
arr = np.array(img)

# Scan for gray watermark text on white background
# Watermarks typically render as RGB(150-235) on RGB(239-255) backgrounds
# Scan specific regions by y-slices to find text-like pixel clusters

for y in range(y_start, y_end, 3):
    row = arr[y, :, 0]
    dark_idx = np.where(row < 200)[0]
    if len(dark_idx) > 3:
        # Found potential watermark row
        gaps = np.diff(dark_idx)
        # Split into text segments
        ...
```

### Removal: white fill

```python
# Watermark 1: bottom right, precise coordinates from pixel analysis
arr[2228:2290, 2935:3250] = [255, 255, 255]

# Watermark 2: top right faint gray band
arr[0:135, 2740:2980] = [255, 255, 255]

Image.fromarray(arr).save('clean.png')
```

### Verification

Always run `vision_analyze` after to confirm:
- No watermark residue
- Chart data intact
- No visible fill artifacts
