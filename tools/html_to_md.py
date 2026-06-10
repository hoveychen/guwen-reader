#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清洗脚本：把格式化成 HTML 的古籍还原为 markdown。

用法:
    python3 tools/html_to_md.py                 # 清洗全部「藏」目录到 markdown/
    python3 tools/html_to_md.py 易藏            # 只清洗指定的藏
    python3 tools/html_to_md.py --out out_dir   # 自定义输出目录

行为:
  - 每本书的所有分页 (书名.html, 书名_page2.html ...) 按页码合并成一个完整的 书名.md
  - 输出到镜像目录 markdown/<藏>/<子类>/书名.md，原 HTML 保持不动
  - 每个目录的 index.html 转成 markdown 书单 (index.md)，链接 .html → .md
  - 丢弃导航栏、分页器、内联样式，只保留 <h1> 标题和 <div class="content"> 正文
"""

import os
import re
import sys
import html
import argparse

# 顶层「藏」目录（其余如 md/、random_pages/、翻译价值分档/ 不是书，跳过）
ZANG = ['佛藏', '儒藏', '医藏', '史藏', '子藏', '易藏', '艺藏', '诗藏', '道藏', '集藏']

H1_RE = re.compile(r'<h1[^>]*>(.*?)</h1>', re.S)
CONTENT_RE = re.compile(r'<div class="content">(.*?)</div>', re.S)
A_RE = re.compile(r'<a\s+href="([^"]+)"[^>]*>\s*(.*?)\s*</a>', re.S)
# 部分源文件（如古今图书集成）的 content 里嵌入了转义后的页面 furniture
# (&lt;div class="pagination"&gt;...&lt;/html&gt;)，需在此截断。
FURNITURE_RE = re.compile(
    r'(?:&lt;|<)\s*/?\s*(?:div\s+class="pagination"|body|html)\b', re.I)
# 只匹配 ASCII 名的 HTML 标签，保留正文里的 CJK 尖括号（如 <经部,易类,易通>）。
ASCII_TAG_RE = re.compile(r'</?[a-zA-Z!][^>]*>')
# 部分书把网页导航条以纯文本烤进了正文，需剥离。形态有：
#   上一页1234567...下一页 / 上一页　目录页　下一页 / 上一页 回目录 下一页
#   以及独立的 返回目录 / 回目录 / 目录页。这些都是网页 nav，古文正文不会出现。
NAV_RE = re.compile(
    r'上一[页頁][\d.…\s]*(?:返?回目[录錄]|目[录錄]页)?[\d.…\s]*下一[页頁]'  # 完整导航条
    r'|上一[页頁][\d.…\s]*'      # 上一页+页码（缺下一页）
    r'|[\d.…]*\s*下一[页頁]'     # 页码+下一页（缺上一页）
    r'|返回目[录錄]|回目[录錄]|目[录錄]页')
# 文件名中的分页后缀: 书名_page12.html
PAGE_FILE_RE = re.compile(r'^(?P<base>.+?)_page(?P<n>\d+)\.html$')
# <h1> 里的分页后缀: "易通 - 第 4 页/共 11 页"
PAGE_TITLE_RE = re.compile(r'\s*[-—–]\s*第\s*\d+\s*页\s*/\s*共\s*\d+\s*页\s*$')
TAG_RE = re.compile(r'<[^>]+>')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)


def clean_text(raw):
    """把一段 HTML 内联文本还原成纯文本：去标签、反转义实体、规整空白。"""
    s = TAG_RE.sub('', raw)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def page_title(htmltext):
    """从 <h1> 取书名，去掉 '- 第 N 页/共 M 页' 后缀。"""
    m = H1_RE.search(htmltext)
    if not m:
        return ''
    t = clean_text(m.group(1))
    return PAGE_TITLE_RE.sub('', t).strip()


def content_to_md(raw):
    """<div class="content"> 的内文（pre-wrap，换行有意义）→ markdown 段落。

    每个原始换行是一处有意义的断句/段落，转成空行分隔的 markdown 段落；
    prettify 留下的首行 ASCII 缩进和全角缩进 (　　) 一并去掉。
    """
    m = FURNITURE_RE.search(raw)
    if m:
        raw = raw[:m.start()]
    text = html.unescape(TAG_RE.sub('', raw))
    text = ASCII_TAG_RE.sub('', text)  # 去掉 unescape 后漏出的 ASCII 标签
    text = NAV_RE.sub('', text)        # 剥离烤进正文的网页导航条
    paras = [ln.strip() for ln in text.split('\n')]
    return '\n\n'.join(p for p in paras if p)


def base_and_page(filename):
    """书名.html -> (书名, 1); 书名_page7.html -> (书名, 7)。"""
    m = PAGE_FILE_RE.match(filename)
    if m:
        return m.group('base'), int(m.group('n'))
    return filename[:-5], 1


def convert_index(htmltext):
    """目录页 index.html → markdown 书单。只保留正文区相对链接，重写 .html→.md。"""
    m = H1_RE.search(htmltext)
    heading = clean_text(m.group(1)) if m else '目录'
    items = []
    seen = set()
    for href, label in A_RE.findall(htmltext):
        # 跳过全站导航 (绝对 /GuWen/...) 和外链
        if href.startswith('/') or '://' in href or href.startswith('#'):
            continue
        label = clean_text(label)
        if not label or label in ('上一页', '下一页', '返回目录'):
            continue
        href_md = re.sub(r'\.html$', '.md', href)
        if href_md in seen:
            continue
        seen.add(href_md)
        items.append((label, href_md))
    lines = ['# ' + heading, '']
    lines += ['- [{}]({})'.format(lbl, h) for lbl, h in items]
    return '\n'.join(lines) + '\n'


def process_root(root, outroot, stats):
    for dirpath, _dirs, files in os.walk(root):
        rel = os.path.relpath(dirpath, '.')
        outdir = os.path.join(outroot, rel)

        groups = {}  # base -> [(page_no, filename)]
        for fn in files:
            if not fn.endswith('.html'):
                continue
            if fn == 'index.html':
                md = convert_index(read(os.path.join(dirpath, fn)))
                write(os.path.join(outdir, 'index.md'), md)
                stats['index'] += 1
                continue
            base, n = base_and_page(fn)
            groups.setdefault(base, []).append((n, fn))

        for base, parts in groups.items():
            parts.sort()
            title = base
            bodies = []
            for i, (_n, fn) in enumerate(parts):
                txt = read(os.path.join(dirpath, fn))
                if i == 0:
                    t = page_title(txt)
                    if t:
                        title = t
                cm = CONTENT_RE.search(txt)
                if cm:
                    body = content_to_md(cm.group(1))
                    if body:
                        bodies.append(body)
            md = '# {}\n\n{}\n'.format(title, '\n\n'.join(bodies))
            write(os.path.join(outdir, base + '.md'), md)
            stats['books'] += 1
            stats['pages'] += len(parts)


def main():
    ap = argparse.ArgumentParser(description='把 HTML 古籍还原为 markdown')
    ap.add_argument('roots', nargs='*', help='要清洗的藏目录（默认全部）')
    ap.add_argument('--out', default='markdown', help='输出根目录（默认 markdown/）')
    args = ap.parse_args()

    roots = args.roots or ZANG
    roots = [r for r in roots if os.path.isdir(r)]
    if not roots:
        print('没有找到要处理的目录', file=sys.stderr)
        return 1

    stats = {'books': 0, 'pages': 0, 'index': 0}
    for root in roots:
        print('清洗 {} ...'.format(root))
        process_root(root, args.out, stats)

    print('\n完成 → {}/'.format(args.out))
    print('  书籍 {} 本（合并 {} 个分页 HTML）'.format(stats['books'], stats['pages']))
    print('  目录页 {} 个'.format(stats['index']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
