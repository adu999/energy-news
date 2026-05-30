#!/usr/bin/env python3
"""
energy-news 抓取脚本
- 读取 sources.json 中的 RSS 列表
- 抓取最新文章，调用 DeepSeek API 翻译标题为中文
- 结果写入 data/articles.json
- 调用 build.py 生成静态 HTML
"""

import json
import os
import hashlib
import time
import re
import random
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path

import feedparser
import httpx

# ── 配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

ARTICLES_FILE = DATA_DIR / "articles.json"
SOURCES_FILE = BASE_DIR / "sources.json"

# 翻译服务配置（优先百度免费翻译，其次 DeepSeek）
BAIDU_APP_ID = os.environ.get("BAIDU_APP_ID", "")
BAIDU_SECRET_KEY = os.environ.get("BAIDU_SECRET_KEY", "")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

TRANSLATE_ENABLED = bool(BAIDU_APP_ID and BAIDU_SECRET_KEY) or bool(DEEPSEEK_API_KEY)

# 保留最新文章数量
MAX_ARTICLES = 500
# 单次抓取每个源最多取几条
MAX_PER_SOURCE = 10
# 翻译批量大小（减少 API 调用次数）
TRANSLATE_BATCH = 20

# ── 工具函数 ──────────────────────────────────────────
def article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_dt(entry) -> datetime:
    """解析 feedparser entry 的发布时间，统一为 UTC datetime"""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return datetime.now(timezone.utc)

def load_existing() -> dict:
    if ARTICLES_FILE.exists():
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_articles(articles: dict):
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def load_sources() -> list:
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ── 翻译 ──────────────────────────────────────────────
def translate_baidu(titles: list[str]) -> list[str]:
    """百度翻译 API（免费 200万字符/月）"""
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    q = "\n".join(titles)
    salt = "".join(random.choices(string.digits, k=8))
    sign = hashlib.md5(f"{BAIDU_APP_ID}{q}{salt}{BAIDU_SECRET_KEY}".encode()).hexdigest()

    params = {
        "q": q,
        "from": "en",
        "to": "zh",
        "appid": BAIDU_APP_ID,
        "salt": salt,
        "sign": sign,
    }
    try:
        resp = httpx.get(url, params=params, timeout=30)
        data = resp.json()
        if "trans_result" in data:
            results = data["trans_result"]
            return [r["dst"].strip() for r in results]
        elif "error_code" in data:
            print(f"[百度翻译错误] {data['error_code']}: {data.get('error_msg')}")
    except Exception as e:
        print(f"[百度翻译请求失败] {e}")
    return titles  # 失败回退


def translate_deepseek(titles: list[str]) -> list[str]:
    """DeepSeek 翻译（备用付费方案）"""
    from openai import OpenAI
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com/v1")

    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))
    prompt = (
        "请将以下英文新闻标题翻译为简洁的中文，保持专业术语准确，"
        "每行一个，保留原编号，不要额外解释。\n\n" + numbered
    )
    try:
        resp = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        lines = [re.sub(r"^\d+\.\s*", "", l).strip() for l in raw.splitlines() if l.strip()]
        if len(lines) == len(titles):
            return lines
    except Exception as e:
        print(f"[DeepSeek 翻译失败] {e}")
    return titles


def translate_batch(titles: list[str]) -> list[str]:
    """优先百度翻译（免费），其次 DeepSeek"""
    if not TRANSLATE_ENABLED or not titles:
        return titles

    # 优先百度免费翻译
    if BAIDU_APP_ID and BAIDU_SECRET_KEY:
        return translate_baidu(titles)

    # 备用 DeepSeek
    if DEEPSEEK_API_KEY:
        return translate_deepseek(titles)

    return titles

# ── 抓取 ──────────────────────────────────────────────
def fetch_source(source: dict, existing_ids: set) -> list:
    """抓取单个 RSS 源，返回新文章列表"""
    name = source["name"]
    url = source["url"]
    category = source["category"]

    print(f"  抓取: {name}")
    try:
        feed = feedparser.parse(url, agent="Mozilla/5.0 (compatible; energy-news-bot/1.0)")
    except Exception as e:
        print(f"    [错误] {e}")
        return []

    new_articles = []
    for entry in feed.entries[:MAX_PER_SOURCE]:
        link = getattr(entry, "link", "")
        if not link:
            continue
        aid = article_id(link)
        if aid in existing_ids:
            continue

        title_en = getattr(entry, "title", "").strip()
        pub_dt = parse_dt(entry)

        new_articles.append({
            "id": aid,
            "title_en": title_en,
            "title_zh": "",          # 待翻译填充
            "url": link,
            "source": name,
            "category": category,
            "pub_ts": pub_dt.isoformat(),
        })

    return new_articles

def fetch_all() -> list:
    sources = load_sources()
    existing = load_existing()
    existing_ids = set(existing.keys())

    all_new = []
    for source in sources:
        new = fetch_source(source, existing_ids)
        all_new.extend(new)
        time.sleep(0.5)  # 礼貌性延迟

    print(f"\n共抓取到 {len(all_new)} 条新文章")
    return all_new, existing

# ── 翻译新文章 ─────────────────────────────────────────
def translate_new(articles: list) -> list:
    """分批翻译新文章标题"""
    if not TRANSLATE_ENABLED:
        print("[跳过翻译] 未配置 DEEPSEEK_API_KEY")
        for a in articles:
            a["title_zh"] = a["title_en"]
        return articles

    print(f"\n开始翻译 {len(articles)} 条标题...")
    for i in range(0, len(articles), TRANSLATE_BATCH):
        batch = articles[i:i + TRANSLATE_BATCH]
        titles_en = [a["title_en"] for a in batch]
        titles_zh = translate_batch(titles_en)
        for j, a in enumerate(batch):
            a["title_zh"] = titles_zh[j]
        print(f"  翻译进度: {min(i + TRANSLATE_BATCH, len(articles))}/{len(articles)}")
        time.sleep(1)  # 避免速率限制

    return articles

# ── 主流程 ────────────────────────────────────────────
def main():
    print("=" * 50)
    print(f"energy-news 抓取开始 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    new_articles, existing = fetch_all()

    if new_articles:
        new_articles = translate_new(new_articles)

        # 合并到现有数据
        for a in new_articles:
            existing[a["id"]] = a

        # 按时间排序，保留最新 MAX_ARTICLES 条
        sorted_items = sorted(
            existing.values(),
            key=lambda x: x["pub_ts"],
            reverse=True
        )[:MAX_ARTICLES]

        existing = {a["id"]: a for a in sorted_items}
        save_articles(existing)
        print(f"\n数据已保存，当前共 {len(existing)} 条文章")
    else:
        print("\n没有新文章，跳过保存")

    print("\n开始生成静态页面...")
    import build
    build.build()
    print("完成！")

if __name__ == "__main__":
    main()
