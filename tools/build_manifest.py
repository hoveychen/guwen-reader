#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成古籍阅读器的书目索引 manifest.json。

遍历 markdown/ 下所有书籍（*.md，排除 index.md），提取：
  - t  书名（文件名去后缀，或首行 # 标题）
  - p  相对 markdown/ 的路径（fetch 用）
  - c  所属大藏（顶层目录）在 categories 数组中的下标
  - s  子分类（中间层目录，可为空）
  - a  作者/朝代等署名行（首行标题后的短行，便于检索，可为空）

输出结构：
  {
    "generated": <unix ts>,
    "count": <书籍总数>,
    "categories": ["佛藏", "儒藏", ...],
    "books": [ {t,p,c,s,a}, ... ]
  }
"""
import os
import json
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD_DIR = os.path.join(ROOT, "markdown")
OUT = os.path.join(ROOT, "manifest.json")

PUNCT = set("。！？；，、：「」『』《》（）()…—·.")


def first_lines(path, n=4):
    """读取文件前若干非空行，避免把整本读进内存。"""
    out = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                s = line.strip()
                if s:
                    out.append(s)
                    if len(out) >= n:
                        break
    except Exception:
        pass
    return out


def looks_like_attribution(line):
    """判断是否像署名行：较短、含朝代或常见署名字样、无明显正文标点。"""
    if not line or len(line) > 30:
        return False
    # 含句末标点的多半是正文
    if any(ch in PUNCT for ch in "。！？；："):
        return False
    dynasties = ("先秦", "汉", "魏", "晋", "南北朝", "隋", "唐", "五代", "宋", "辽",
                 "金", "元", "明", "清", "民国", "周", "春秋", "战国", "三国")
    markers = ("撰", "著", "编", "辑", "注", "释", "纂", "校", "译", "述", "卷")
    return any(d in line for d in dynasties) or any(m in line for m in markers)


def main():
    if not os.path.isdir(MD_DIR):
        print("找不到 markdown 目录：%s" % MD_DIR, file=sys.stderr)
        sys.exit(1)

    categories = sorted(
        d for d in os.listdir(MD_DIR)
        if os.path.isdir(os.path.join(MD_DIR, d)) and not d.startswith(".")
    )
    cat_index = {c: i for i, c in enumerate(categories)}

    books = []
    for dirpath, dirnames, filenames in os.walk(MD_DIR):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".md") or fn == "index.md":
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, MD_DIR)
            parts = rel.split(os.sep)
            cat = parts[0]
            if cat not in cat_index:
                continue
            sub = os.sep.join(parts[1:-1]).replace(os.sep, "/")  # 中间层为子分类
            title = fn[:-3]

            heads = first_lines(full, 4)
            # 首行若是 # 标题则用作书名
            if heads and heads[0].startswith("#"):
                t = heads[0].lstrip("#").strip()
                if t:
                    title = t
                rest = heads[1:]
            else:
                rest = heads
            attr = ""
            for ln in rest:
                if looks_like_attribution(ln):
                    attr = ln
                    break

            books.append({
                "t": title,
                "p": rel.replace(os.sep, "/"),
                "c": cat_index[cat],
                "s": sub,
                "a": attr,
            })

    books.sort(key=lambda b: (b["c"], b["s"], b["t"]))

    data = {
        "generated": int(time.time()),
        "count": len(books),
        "categories": categories,
        "books": books,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

    size_mb = os.path.getsize(OUT) / 1024 / 1024
    print("已生成 %s" % OUT)
    print("书籍总数：%d，分类：%d，文件大小：%.2f MB" % (
        len(books), len(categories), size_mb))
    for c in categories:
        n = sum(1 for b in books if categories[b["c"]] == c)
        print("  %s: %d" % (c, n))


if __name__ == "__main__":
    main()
