"""
serp_preview.py
현재 소아벨라 사이트의 title/description을 실시간으로 가져와
구글·네이버 검색 결과 스니펫이 어떻게 보이는지 HTML로 미리보기를 생성한다.
Claude API 불필요, 사이트 크롤링만으로 동작.

실행:
    python generator/serp_preview.py               # 홈 + 전체 카테고리
    python generator/serp_preview.py --url https://soavela.com/category/ring/
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, CATEGORIES, HEADERS, REQUEST_TIMEOUT, META_DIR

console = Console()


@dataclass
class SerpEntry:
    url: str
    title: str
    description: str
    og_title: str
    og_description: str
    og_image: str
    canonical: str
    title_len: int = 0
    desc_len: int = 0

    def __post_init__(self):
        self.title_len = len(self.title)
        self.desc_len  = len(self.description)


def fetch_serp_data(url: str) -> SerpEntry:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "lxml")

        def meta(name=None, prop=None):
            if name:
                tag = soup.find("meta", attrs={"name": name})
                return tag.get("content", "").strip() if tag else ""
            if prop:
                tag = soup.find("meta", property=prop)
                return tag.get("content", "").strip() if tag else ""
            return ""

        title_tag = soup.find("title")
        title     = title_tag.get_text(strip=True) if title_tag else ""

        canon_tag = soup.find("link", attrs={"rel": "canonical"})
        canonical = canon_tag.get("href", "") if canon_tag else ""

        return SerpEntry(
            url=url,
            title=title,
            description=meta(name="description"),
            og_title=meta(prop="og:title"),
            og_description=meta(prop="og:description"),
            og_image=meta(prop="og:image"),
            canonical=canonical,
        )
    except Exception as e:
        console.print(f"[red]fetch 오류 ({url}): {e}[/red]")
        return SerpEntry(url=url, title="", description="", og_title="",
                         og_description="", og_image="", canonical="")


def len_color(n: int, good_lo: int, good_hi: int) -> str:
    if good_lo <= n <= good_hi: return "green"
    if n == 0: return "red"
    return "yellow"


def print_table(entries: list[SerpEntry]):
    table = Table(title="SERP 스니펫 현황", show_lines=True)
    table.add_column("URL", max_width=30, overflow="ellipsis")
    table.add_column("title 길이", justify="center")
    table.add_column("description 길이", justify="center")
    table.add_column("OG", justify="center")
    table.add_column("canonical", justify="center")

    for e in entries:
        short = e.url.replace(TARGET_URL, "") or "/"
        tc = len_color(e.title_len, 30, 60)
        dc = len_color(e.desc_len, 80, 160)
        og_ok = "[green]✓[/green]" if e.og_title else "[red]✗[/red]"
        can_ok = "[green]✓[/green]" if e.canonical else "[red]✗[/red]"

        table.add_row(
            short,
            f"[{tc}]{e.title_len}자[/{tc}]",
            f"[{dc}]{e.desc_len}자[/{dc}]",
            og_ok, can_ok,
        )

    console.print(table)


def build_html(entries: list[SerpEntry]) -> str:
    def bar_color(n, lo, hi):
        if n == 0: return "#e53e3e"
        if lo <= n <= hi: return "#38a169"
        return "#d69e2e"

    def bar_width(n, maximum):
        return min(100, int(n / maximum * 100))

    cards = ""
    for e in entries:
        short_url = e.url.replace(TARGET_URL, "") or "/"
        truncated_title = e.title[:57] + "..." if len(e.title) > 60 else e.title
        truncated_desc  = e.description[:150] + "..." if len(e.description) > 160 else e.description

        # title 길이 바
        tc   = bar_color(e.title_len, 30, 60)
        tw   = bar_width(e.title_len, 70)
        # desc 길이 바
        dc   = bar_color(e.desc_len, 80, 160)
        dw   = bar_width(e.desc_len, 180)

        og_badge = ('<span style="background:#38a169;color:#fff;font-size:.68rem;'
                    'padding:.1rem .4rem;border-radius:4px;font-weight:700;">OG ✓</span>'
                    if e.og_title else
                    '<span style="background:#e53e3e;color:#fff;font-size:.68rem;'
                    'padding:.1rem .4rem;border-radius:4px;font-weight:700;">OG ✗</span>')
        can_badge = ('<span style="background:#38a169;color:#fff;font-size:.68rem;'
                     'padding:.1rem .4rem;border-radius:4px;font-weight:700;">canonical ✓</span>'
                     if e.canonical else
                     '<span style="background:#e53e3e;color:#fff;font-size:.68rem;'
                     'padding:.1rem .4rem;border-radius:4px;font-weight:700;">canonical ✗</span>')

        # 구글 SERP 시뮬레이션
        google_block = f"""
<div style="font-family:Arial,sans-serif;max-width:600px;padding:1rem;
            background:#fff;border:1px solid #e0e0e0;border-radius:8px;margin-bottom:.75rem;">
  <div style="font-size:.8rem;color:#3c4043;margin-bottom:2px;">
    {e.url[:60]}{"…" if len(e.url)>60 else ""}
  </div>
  <div style="font-size:1.1rem;color:#1a0dab;margin-bottom:4px;line-height:1.3;">
    {truncated_title or '<span style="color:#999">title 없음</span>'}
  </div>
  <div style="font-size:.87rem;color:#3c4043;line-height:1.5;">
    {truncated_desc or '<span style="color:#999">description 없음</span>'}
  </div>
</div>"""

        # 네이버 SERP 시뮬레이션
        naver_block = f"""
<div style="font-family:'Apple SD Gothic Neo','Malgun Gothic',sans-serif;max-width:600px;
            padding:1rem;background:#fff;border:1px solid #e0e0e0;border-radius:8px;">
  <div style="font-size:1rem;color:#04c;margin-bottom:4px;font-weight:700;">
    {truncated_title or '<span style="color:#999">title 없음</span>'}
  </div>
  <div style="font-size:.85rem;color:#444;line-height:1.6;margin-bottom:6px;">
    {truncated_desc or '<span style="color:#999">description 없음</span>'}
  </div>
  <div style="font-size:.75rem;color:#1a7c00;">{e.url[:60]}</div>
</div>"""

        cards += f"""
<div class="card">
  <div class="card-header">
    <span class="page-label">{short_url}</span>
    <div style="display:flex;gap:.4rem;flex-wrap:wrap;">{og_badge}{can_badge}</div>
  </div>

  <div class="metrics">
    <div class="metric">
      <span class="metric-label">title ({e.title_len}자)</span>
      <div class="bar-track">
        <div style="width:{tw}%;background:{tc};height:100%;border-radius:3px;transition:width .3s;"></div>
      </div>
      <span class="metric-hint">30~60자 권장</span>
    </div>
    <div class="metric">
      <span class="metric-label">description ({e.desc_len}자)</span>
      <div class="bar-track">
        <div style="width:{dw}%;background:{dc};height:100%;border-radius:3px;transition:width .3s;"></div>
      </div>
      <span class="metric-hint">80~160자 권장</span>
    </div>
  </div>

  <div class="serp-grid">
    <div>
      <div class="engine-label">🔍 Google SERP 미리보기</div>
      {google_block}
    </div>
    <div>
      <div class="engine-label">🟢 Naver SERP 미리보기</div>
      {naver_block}
    </div>
  </div>
</div>"""

    ts = datetime.now().strftime("%Y년 %m월 %d일 %H:%M")
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>소아벨라 SERP 스니펫 미리보기 — {ts}</title>
<style>
  body {{ font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
          background:#f7fafc;color:#1a202c;margin:0;padding:2rem; }}
  h1   {{ font-size:1.4rem;margin-bottom:.3rem; }}
  .sub {{ color:#718096;font-size:.85rem;margin-bottom:2rem; }}
  .card {{ background:#fff;border:1px solid #e2e8f0;border-radius:12px;
           padding:1.5rem;margin-bottom:1.5rem;
           box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  .card-header {{ display:flex;justify-content:space-between;align-items:center;
                  margin-bottom:1rem;flex-wrap:wrap;gap:.5rem; }}
  .page-label {{ font-size:.85rem;font-weight:700;color:#3182ce;
                 background:#ebf8ff;padding:.2rem .6rem;border-radius:4px; }}
  .metrics {{ display:flex;gap:1.5rem;margin-bottom:1.25rem;flex-wrap:wrap; }}
  .metric  {{ flex:1;min-width:200px; }}
  .metric-label {{ font-size:.75rem;font-weight:700;color:#4a5568;display:block;margin-bottom:.3rem; }}
  .metric-hint  {{ font-size:.7rem;color:#718096; }}
  .bar-track {{ height:8px;background:#e2e8f0;border-radius:3px;margin:.3rem 0; }}
  .serp-grid {{ display:grid;grid-template-columns:1fr 1fr;gap:1.25rem; }}
  .engine-label {{ font-size:.75rem;font-weight:700;color:#718096;margin-bottom:.5rem; }}
  @media(max-width:768px) {{ .serp-grid {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<h1>소아벨라 SERP 스니펫 미리보기</h1>
<p class="sub">생성일: {ts} | 총 {len(entries)}개 페이지 | 실시간 크롤 기준</p>
{cards}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="SERP 스니펫 미리보기 생성")
    parser.add_argument("--url", help="특정 URL만 분석")
    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    else:
        urls = [TARGET_URL] + [c["url"] for c in CATEGORIES]

    console.rule("[bold]SERP 스니펫 현황 분석[/bold]")
    entries = []
    for i, url in enumerate(urls, 1):
        console.print(f"  [{i}/{len(urls)}] [cyan]{url}[/cyan]")
        entry = fetch_serp_data(url)
        entries.append(entry)

    print_table(entries)

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    html = build_html(entries)
    path = META_DIR / f"serp_preview_{ts}.html"
    path.write_text(html, encoding="utf-8")
    console.print(f"\n[green]SERP 미리보기 저장:[/green] {path}")
    console.print("브라우저로 열어 Google·Naver 노출 모습을 확인하세요.")


if __name__ == "__main__":
    main()
