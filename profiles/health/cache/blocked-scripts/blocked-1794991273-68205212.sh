#!/bin/bash
# Auto-saved by Hermes: this command exceeded the inline command
# parser limit and was blocked from direct execution. Review it,
# then run it via: bash C:\Users\Administrator\AppData\Local\hermes\profiles\health\cache\blocked-scripts\blocked-1794991273-68205212.sh
cd ~/health && grep -rn "卡士" diet/*.md reviews/*.md records/*.md 2>/dev/null | head -5; echo "--- 结果行数：$(grep -rc 卡士 diet/*.md 2>/dev/null | grep -v ':0' | wc -l) ---"
