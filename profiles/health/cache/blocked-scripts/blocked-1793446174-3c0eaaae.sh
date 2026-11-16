#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash C:\Users\Administrator\AppData\Local\hermes\profiles\health\cache\blocked-scripts\blocked-1793446174-3c0eaaae.sh
cd ~/health && ls AppData/Local/hermes/profiles/health/skills/*/references/ 2>/dev/null | head; echo "==="; find ~/AppData/Local/hermes -name "bone-in-and-caliber-carryover-2026-10-23.md" 2>/dev/null; echo "=== 10-24 加餐 ==="; sed -n "$(grep -n '## 加餐' diet/2026-10-24.md | head -1 | cut -d: -f1),+45p" diet/2026-10-24.md
