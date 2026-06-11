#!/bin/bash
# ============================================================================
# GitHub Pages 同步脚本
#
# 用途：改完 index.html / manifest.json 并提交到 main 后，运行本脚本把
#       阅读器骨架（代码 + 搜索索引）同步到 gh-pages 分支并推送。
#       语料正文不进 Pages，线上通过 raw.githubusercontent.com 按需加载。
#
# 用法：
#         cd ~/workspace/guwen-reader
#         bash sync_pages.sh
#
# 说明：
#   - 同步的是 **main 分支上已提交** 的版本，不是工作区；改完记得先 commit。
#   - 用 git plumbing 直接构建 gh-pages 提交，不切分支、不碰工作区。
#   - 内容无变化时自动跳过，不会产生空提交。
# ============================================================================
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

BRANCH=gh-pages
FILES=(index.html manifest.json favicon.ico README.md)

# ---- 1) 用临时 index 从 main 的 blob 构建 Pages 树（骨架 + .nojekyll）----
GIT_INDEX_FILE=$(mktemp)
export GIT_INDEX_FILE
trap 'rm -f "$GIT_INDEX_FILE"' EXIT
git read-tree --empty
for f in "${FILES[@]}"; do
  blob=$(git rev-parse "main:$f" 2>/dev/null) || { echo "❌ main 分支上找不到 $f"; exit 1; }
  git update-index --add --cacheinfo "100644,$blob,$f"
done
empty=$(git hash-object -w /dev/null)
git update-index --add --cacheinfo "100644,$empty,.nojekyll"
tree=$(git write-tree)

# ---- 2) 与现有 gh-pages 比较，有变化才提交 ----
if [ "$tree" = "$(git rev-parse "$BRANCH^{tree}" 2>/dev/null || true)" ]; then
  echo "gh-pages 内容已是最新，无需新提交。"
else
  parent=$(git rev-parse "$BRANCH" 2>/dev/null || true)
  commit=$(git commit-tree "$tree" ${parent:+-p "$parent"} \
           -m "Pages 同步：$(git log -1 --format=%s main)")
  git branch -f "$BRANCH" "$commit"
  echo "✅ gh-pages -> $commit"
fi

# ---- 3) 推送 gh-pages（已最新时为 no-op）----
git push origin "$BRANCH"

# ---- 4) 一致性提醒：线上正文走 raw（origin/main）----
if [ -n "$(git rev-list origin/main..main 2>/dev/null)" ]; then
  echo "⚠️  本地 main 领先 origin/main：线上索引已更新，但 raw 语料还是旧的。"
  echo "    记得 git push origin main，否则新增/改名的书会 404。"
fi

echo "🎉 完成。线上地址：https://hoveychen.github.io/guwen-reader/"
