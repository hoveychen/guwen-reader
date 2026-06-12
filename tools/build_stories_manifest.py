#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""扫描 stories/ 下逐篇短剧 markdown，抽取元数据生成 stories/index.json，供 duanju.html 短剧站消费。

每篇 markdown 约定结构（由翻译流程产出）：
    # 标题（《情史·情X类》）
    > 原著：（明）冯梦龙《情史》　·　类目：情X类　·　短剧类型：a/b/c
    ## 一、白话故事
    正文……
    ## 二、短剧改编
    **一句话钩子：** ……
"""
import os, re, json, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORIES = os.path.join(ROOT, "stories")

# 24 类按原书卷次排序，决定站点分类顺序
CATEGORY_ORDER = [
    "情贞类", "情缘类", "情私类", "情侠类", "情豪类", "情爱类", "情痴类", "情感类",
    "情幻类", "情灵类", "情化类", "情媒类", "情憾类", "情仇类", "情芽类", "情报类",
    "情秽类", "情累类", "情疑类", "情鬼类", "情妖类", "情外类", "情通类", "情迹类",
]
# 一句话点题，给每个类目一句导语
CATEGORY_TAGLINE = {
    "情贞类": "乱世守誓，至死不渝", "情缘类": "天意牵线，破镜重圆", "情私类": "墙里墙外，私订终身",
    "情侠类": "义气干云，侠骨柔肠", "情豪类": "豪情一掷，倾盖如故", "情爱类": "痴心一片，生死相许",
    "情痴类": "情之所钟，虽死不悔", "情感类": "至诚动天，幽明感通", "情幻类": "魂梦相寻，借体还阳",
    "情灵类": "一灵不灭，重续前缘", "情化类": "化作连枝，金石同心", "情媒类": "天作之合，巧成姻缘",
    "情憾类": "有情无缘，抱恨终身", "情仇类": "爱极成仇，血溅鸳鸯", "情芽类": "情窦初萌，暗渡春心",
    "情报类": "负心薄幸，天理昭彰", "情秽类": "宫闱秘事，权欲翻覆", "情累类": "情丝缠祸，一念成灾",
    "情疑类": "奇缘难辨，真假莫测", "情鬼类": "幽冥结契，鬼亦多情", "情妖类": "异类含情，痴胜世人",
    "情外类": "断袖余桃，别样痴缠", "情通类": "灵犀暗通，物我交感", "情迹类": "情史留痕，余韵悠长",
}

# 首页热榜：自带 IP 光环、改编潜力最强的精选（按展示顺序）
FEATURED = [
    "杜十娘", "玉堂春", "古押衙", "卓文君", "崔英", "申屠氏",
    "张幼谦", "任氏", "李益", "珍珠衫", "唐高宗武后", "金三妻",
]

def clean_inline(s):
    s = re.sub(r"\[\^[^\]]+\]", "", s)          # 去脚注标记
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)        # 去粗体
    s = re.sub(r"\[(.+?)\]\([^)]*\)", r"\1", s)   # 去链接
    s = s.replace("　", " ").strip()
    return s

def parse(path):
    raw = open(path, encoding="utf-8").read()
    lines = raw.split("\n")
    title = category = hook = ""
    genres = []
    # 标题
    for l in lines:
        m = re.match(r"^#\s+(.+)$", l)
        if m:
            title = re.split(r"[（(]", m.group(1).strip())[0].strip()
            break
    # 元信息行
    for l in lines:
        if "类目：" in l or "类目:" in l:
            mc = re.search(r"类目[：:]\s*([^\s　·]+)", l)
            if mc: category = mc.group(1)
            mg = re.search(r"短剧类型[：:]\s*([^\s　·]+)", l)
            if mg: genres = [g for g in re.split(r"[/／、]", mg.group(1).strip()) if g]
            break
    # 钩子
    for l in lines:
        if "一句话钩子" in l:
            hook = clean_inline(re.sub(r"^.*钩子[：:]\**\s*", "", l))
            break
    # 摘要：白话故事首段
    excerpt = ""
    in_body = False
    for l in lines:
        if re.match(r"^##\s*一", l):
            in_body = True; continue
        if in_body:
            s = l.strip()
            if not s or s.startswith(("#", ">", "---", "|", "*", "-")):
                if excerpt: break
                continue
            excerpt = clean_inline(s)
            break
    if len(excerpt) > 88:
        excerpt = excerpt[:88] + "…"
    return {
        "file": os.path.basename(path),
        "title": title,
        "category": category,
        "genres": genres,
        "hook": hook,
        "excerpt": excerpt,
    }

def main():
    items = []
    for p in glob.glob(os.path.join(STORIES, "*.md")):
        if os.path.basename(p) == "README.md":
            continue
        it = parse(p)
        if it["title"]:
            items.append(it)
    # 排序：先按类目卷次，再按标题
    cat_idx = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    items.sort(key=lambda x: (cat_idx.get(x["category"], 99), x["title"]))

    # 收集出现过的全部类型标签（按频次）
    from collections import Counter
    gc = Counter(g for it in items for g in it["genres"])
    genre_tags = [g for g, _ in gc.most_common()]

    # 类目（仅保留有内容的，按卷次）
    present = [c for c in CATEGORY_ORDER if any(it["category"] == c for it in items)]
    categories = [{"name": c, "tagline": CATEGORY_TAGLINE.get(c, ""),
                   "count": sum(1 for it in items if it["category"] == c)} for c in present]

    title_set = {it["title"] for it in items}
    featured = [t for t in FEATURED if t in title_set]

    out = {
        "site": "情史 · 短剧选",
        "subtitle": "明·冯梦龙《情史》中最宜改编现代短剧的故事",
        "total": len(items),
        "featured": featured,
        "genres": genre_tags,
        "categories": categories,
        "stories": items,
    }
    dst = os.path.join(STORIES, "index.json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {dst}: {len(items)} stories, {len(genre_tags)} genres, {len(categories)} categories, {len(featured)} featured")

if __name__ == "__main__":
    main()
