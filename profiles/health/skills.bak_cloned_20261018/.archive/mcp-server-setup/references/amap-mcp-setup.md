# AMap (高德地图) MCP Server Setup

## Quick Config

```yaml
# ~/AppData/Local/hermes/config.yaml
mcp_servers:
  amap:
    command: "npx"
    args:
      - "-y"
      - "@amap/amap-maps-mcp-server"
    env:
      AMAP_MAPS_API_KEY: "your_key_here"
```

Restart Hermes. Tools appear as `mcp_amap_maps_*`.

## Getting an API Key

1. Go to https://lbs.amap.com/ → sign up/login
2. Console → Application Management → Create Application (or use existing)
3. **Add Key** → select **"Web服务"** as platform (NOT Android/iOS/JS API)
4. Check all needed services: 地理编码, 路径规划, 周边搜索, 天气查询, 关键字搜索, 逆地理编码
5. Submit → copy the key
6. Save key to `Desktop/各类api key/amap api key.txt`

### Critical Platform Selection Pitfall

The "Web服务" platform choice determines which APIs are available:

| Platform | What it gives you | Used for |
|----------|-------------------|----------|
| Android/iOS | Map SDK, Location SDK, Navigation SDK | Mobile apps only |
| **Web服务** ✅ | REST APIs (geo, directions, weather, search) | Server-side/MCP |
| Web (JS API) | Browser JavaScript API | Web pages |

Create a **new Key** under Web服务 — don't try to add Web APIs to an Android key. They're separate platforms with separate key types.

## Available MCP Tools

| Tool | Function |
|------|----------|
| `maps_geo` | Address → coordinates (geocoding) |
| `maps_regeocode` | Coordinates → address (reverse geocoding) |
| `maps_direction_driving` | Driving route with steps |
| `maps_direction_walking` | Walking route |
| `maps_direction_bicycling` | Cycling route |
| `maps_direction_transit_integrated` | Public transit route |
| `maps_distance` | Distance measurement |
| `maps_weather` | Weather by city/adcode |
| `maps_text_search` | Keyword POI search |
| `maps_around_search` | Nearby POI search (radius) |
| `maps_search_detail` | POI detail by ID |
| `maps_ip_location` | IP geolocation |

## Static Map API (direct REST call, not MCP)

The MCP server does NOT include a static map tool. Generate map images directly:

```
https://restapi.amap.com/v3/staticmap?key=KEY&location=lng,lat&zoom=16&size=800*600
```

### Static Map Parameters

| Param | Required | Format | Notes |
|-------|----------|--------|-------|
| `key` | ✅ | string | Same Web服务 key |
| `location` | ✅ | `lng,lat` | ⚠️ NOT `center`! This is the #1 bug cause |
| `zoom` | ✅ | 1-17 | 16-17 for building-level detail |
| `size` | ✅ | `W*H` | Use `*` not `x`, max ~1024 |
| `scale` | ❌ | 1 or 2 | 2 = retina quality |
| `markers` | ❌ | See below | Up to 10 |
| `labels` | ❌ | See below | Up to 10 |
| `paths` | ❌ | See below | Up to 4 polylines/polygons |
| `traffic` | ❌ | 0 or 1 | Show real-time traffic |

### Markers Format

```
markers=mid,color,label:lng,lat;lng,lat|large,color,label:lng,lat
```

- `mid` = medium icon, `large` = large, `small` = small
- Color: hex like `0xFF0000` (red), `0x43A047` (green), `0x1E88E5` (blue)
- Label: single char or digit (0-9, A-Z)

### Paths Format (for zone boundaries/polygons)

```
paths=weight,color,transparency,fillColor,fillTransparency:lng,lat;lng,lat;lng,lat
```

Example — red zone outline with semi-transparent fill:
```
paths=3,0xFF0000,1,0xFF0000,0.2:121.4877,31.1840;121.4915,31.1846;121.4922,31.1816;121.4884,31.1809
```

### Debugging Static Map

1. First test bare minimum to isolate the issue:
   ```bash
   curl -s "https://restapi.amap.com/v3/staticmap?key=KEY&location=116.40,39.90&zoom=10&size=200*200" | file -
   ```
2. If 20003 error: check that `location` param is used (not `center`)
3. If returns JSON error: read the error body for the actual error code
4. If returns valid PNG: add markers/paths incrementally

## Verifying the Key Works

Before configuring MCP, test with a simple API call:

```bash
# Weather API (simplest, always works if key is valid)
curl -s "https://restapi.amap.com/v3/weather/weatherInfo?key=KEY&city=310000&extensions=base&output=JSON"
# Expected: {"status":"1","info":"OK",...}
```

## Network Notes (China Environment)

- AMap APIs are domestic Chinese services — no proxy needed
- The `@amap/amap-maps-mcp-server` npm package is on npmjs.com — may need proxy for initial `npx -y` install
- After first install, npm cache handles subsequent starts
- DO NOT set HTTP_PROXY in the MCP server env for AMap — it goes direct
