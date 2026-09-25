#!/usr/bin/env bash
# 从运行中的 MeTube 抓取原版前端资源，供 metube_zh.py 汉化使用。
# 用法： ./fetch-original.sh http://192.168.1.38:7878 ./dist-orig
set -euo pipefail

BASE="${1:-http://127.0.0.1:7878}"
OUT="${2:-./dist-orig}"

mkdir -p "$OUT/assets/icons"

# index.html 里有带 hash 的实际文件名，先抓它再照着拉
curl -fsS "$BASE/" -o "$OUT/index.html"
grep -oE '(main|polyfills|styles)-[A-Z0-9]+\.js' "$OUT/index.html" | sort -u | while read -r f; do
    echo "  + $f"
    curl -fsS "$BASE/$f" -o "$OUT/$f"
done
grep -oE 'styles-[A-Z0-9]+\.css' "$OUT/index.html" | sort -u | while read -r f; do
    echo "  + $f"
    curl -fsS "$BASE/$f" -o "$OUT/$f"
done

for f in favicon.ico manifest.webmanifest \
         assets/icons/apple-touch-icon.png \
         assets/icons/favicon-32x32.png \
         assets/icons/favicon-16x16.png \
         assets/icons/safari-pinned-tab.svg \
         assets/icons/browserconfig.xml \
         assets/icons/android-chrome-192x192.png \
         assets/icons/android-chrome-384x384.png \
         assets/icons/mstile-150x150.png; do
    curl -fsS "$BASE/$f" -o "$OUT/$f" || echo "  (跳过，不存在) $f"
done

echo "完成 -> $OUT"
echo "下一步： python3 tools/metube_zh.py $OUT --out ./dist"
