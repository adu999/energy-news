#!/usr/bin/env python3
"""
静态页面生成器
读取 data/articles.json → 渲染 templates/ → 输出到 docs/
"""

import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "docs"
OUTPUT_DIR.mkdir(exist_ok=True)

CATEGORIES = ["全部", "太阳能", "风电", "储能", "氢能", "电网", "电力", "油气", "核能", "EV", "综合", "政策"]

# 北京时间偏移
CST = timezone(timedelta(hours=8))


def load_articles() -> list:
    f = DATA_DIR / "articles.json"
    if not f.exists():
        return []
    with open(f, "r", encoding="utf-8") as fp:
        data = json.load(fp)
    articles = sorted(data.values(), key=lambda x: x["pub_ts"], reverse=True)
    # 格式化时间为北京时间
    for a in articles:
        try:
            dt = datetime.fromisoformat(a["pub_ts"]).astimezone(CST)
            a["pub_date"] = dt.strftime("%m-%d")
            a["pub_time"] = dt.strftime("%H:%M")
            a["pub_full"] = dt.strftime("%Y-%m-%d %H:%M")
        except Exception:
            a["pub_date"] = ""
            a["pub_time"] = ""
            a["pub_full"] = ""
    return articles


def build():
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    articles = load_articles()

    # 按分类分组
    by_cat = defaultdict(list)
    for a in articles:
        by_cat[a["category"]].append(a)

    update_time = datetime.now(CST).strftime("%Y-%m-%d %H:%M")

    # ── 首页（全部 + 分类标签栏）──
    tmpl = env.get_template("index.html")
    html = tmpl.render(
        articles=articles[:200],
        by_cat=by_cat,
        categories=CATEGORIES,
        current_cat="全部",
        update_time=update_time,
        total=len(articles),
    )
    (OUTPUT_DIR / "index.html").write_text(html, encoding="utf-8")

    # ── 分类页 ──
    for cat in CATEGORIES[1:]:
        cat_articles = by_cat.get(cat, [])
        html = tmpl.render(
            articles=cat_articles[:200],
            by_cat=by_cat,
            categories=CATEGORIES,
            current_cat=cat,
            update_time=update_time,
            total=len(articles),
        )
        safe_name = cat.replace("/", "_")
        (OUTPUT_DIR / f"{safe_name}.html").write_text(html, encoding="utf-8")

    print(f"  生成 {1 + len(CATEGORIES) - 1} 个页面，共 {len(articles)} 条文章")


if __name__ == "__main__":
    build()
