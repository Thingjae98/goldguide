"""
competitor_spy.py
경쟁사 사이트의 SEO 전략을 자동으로 분석한다.
- title/description 패턴
- h1/h2 키워드
- 구조화 데이터 타입
- 내부 링크 구조

실행:
    python crawler/competitor_spy.py
    python crawler/competitor_spy.py --urls https://example.com https://example2.com
"""

import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import COMPETITORS, HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY, AUDIT_DIR, TARGET_URL

console = Console()


@dataclass
class CompetitorData:
    url: str
    status_code: int = 0
    title: str = ""
    title_len: int = 0
    meta_description: str = ""
    desc_len: int = 0
    canonical: str = ""
    h1: str = ""
    h2s: list = None
    og_title: str = ""
    og_image: str = ""
    json_ld_types: list = None
    keyword_density: dict = None  # 주요 단어 출현 빈도
    image_count: int = 0
    alt_coverage: float = 0.0    # alt 있는 이미지 비율
    internal_links: int = 0
    schema_types: list = None
    analyzed_at: str = ""

    def __post_init__(self):
        if self.h2s is None:         self.h2s = []
        if self.json_ld_types is None: self.json_ld_types = []
        if self.keyword_density is None: self.keyword_density = {}
        if self.schema_types is None: self.schema_types = []
        if not self.analyzed_at: self.analyzed_at = datetime.now().isoformat()


class CompetitorSpy:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.results: list[CompetitorData] = []

    def fetch(self, url: str):
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            return BeautifulSoup(r.text, "lxml"), r.status_code
        except Exception as e:
            console.print(f"[red]fetch 오류: {e}[/red]")
            return None, 0

    def keyword_count(self, soup: BeautifulSoup, keywords: list[str]) -> dict:
        """페이지 전체 텍스트에서 키워드 출현 횟수."""
        text = soup.get_text().lower()
        return {kw: text.count(kw.lower()) for kw in keywords}

    def analyze(self, url: str) -> CompetitorData:
        console.print(f"  분석 중: [cyan]{url}[/cyan]")
        data = CompetitorData(url=url)
        soup, status = self.fetch(url)
        data.status_code = status

        if soup is None:
            return data

        # title
        t = soup.find("title")
        data.title = t.get_text(strip=True) if t else ""
        data.title_len = len(data.title)

        # meta description
        m = soup.find("meta", attrs={"name": "description"})
        data.meta_description = m.get("content", "").strip() if m else ""
        data.desc_len = len(data.meta_description)

        # canonical
        c = soup.find("link", attrs={"rel": "canonical"})
        data.canonical = c.get("href", "") if c else ""

        # h1, h2
        h1 = soup.find("h1")
        data.h1 = h1.get_text(strip=True) if h1 else ""
        data.h2s = [t.get_text(strip=True) for t in soup.find_all("h2")][:5]

        # OG
        og_t = soup.find("meta", property="og:title")
        og_i = soup.find("meta", property="og:image")
        data.og_title = og_t.get("content", "") if og_t else ""
        data.og_image = og_i.get("content", "") if og_i else ""

        # JSON-LD
        for s in soup.find_all("script", type="application/ld+json"):
            try:
                d = json.loads(s.string or "")
                tp = d.get("@type", "")
                if tp: data.json_ld_types.append(tp)
            except Exception:
                pass

        # 이미지 alt 커버리지
        imgs = soup.find_all("img")
        data.image_count = len(imgs)
        has_alt = sum(1 for i in imgs if i.get("alt") is not None)
        data.alt_coverage = round(has_alt / len(imgs) * 100, 1) if imgs else 0.0

        # 키워드 밀도
        gold_keywords = ["금반지", "금목걸이", "금팔찌", "순금", "14k", "18k", "24k", "주얼리", "골드"]
        data.keyword_density = self.keyword_count(soup, gold_keywords)

        # 내부 링크
        base = url.split("/")[0] + "//" + url.split("/")[2]
        data.internal_links = len([
            a for a in soup.find_all("a", href=True)
            if base in a["href"] or a["href"].startswith("/")
        ])

        return data

    def analyze_all(self, urls: list[str] = None) -> list[CompetitorData]:
        targets = urls or COMPETITORS
        if not targets:
            console.print("[yellow]경쟁사 URL이 설정되지 않았습니다. .env의 COMPETITORS를 확인하세요.[/yellow]")
            return []

        # 소아벨라 자신도 비교 기준으로 포함
        all_urls = [TARGET_URL] + [u for u in targets if u != TARGET_URL]

        console.rule("[bold]경쟁사 분석 시작[/bold]")
        for url in all_urls:
            result = self.analyze(url)
            self.results.append(result)
            time.sleep(REQUEST_DELAY)

        return self.results

    def print_comparison(self):
        """소아벨라 vs 경쟁사 비교 테이블 출력."""
        table = Table(title="SEO 경쟁사 비교 분석", show_lines=True)
        table.add_column("항목", style="bold", min_width=14)
        for r in self.results:
            label = "소아벨라 (우리)" if r.url == TARGET_URL else r.url.split("/")[2]
            table.add_column(label, max_width=28)

        rows = [
            ("title 길이",      lambda r: f"{r.title_len}자"),
            ("description",     lambda r: f"{r.desc_len}자" if r.desc_len else "[red]없음[/red]"),
            ("canonical",       lambda r: "[green]✓[/green]" if r.canonical else "[red]✗[/red]"),
            ("h1",              lambda r: r.h1[:20] + "..." if len(r.h1) > 20 else (r.h1 or "[red]없음[/red]")),
            ("OG 태그",         lambda r: "[green]✓[/green]" if r.og_title else "[red]✗[/red]"),
            ("JSON-LD",         lambda r: ", ".join(r.json_ld_types) if r.json_ld_types else "[red]없음[/red]"),
            ("이미지 alt 커버리지", lambda r: f"{r.alt_coverage}%"),
            ("내부 링크 수",    lambda r: str(r.internal_links)),
            ("'순금' 출현",     lambda r: str(r.keyword_density.get("순금", 0)) + "회"),
            ("'금반지' 출현",   lambda r: str(r.keyword_density.get("금반지", 0)) + "회"),
        ]

        for label, fn in rows:
            table.add_row(label, *[fn(r) for r in self.results])

        console.print(table)

    def save_json(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = AUDIT_DIR / f"competitor_{ts}.json"
        path.write_text(
            json.dumps([asdict(r) for r in self.results], ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        console.print(f"[green]경쟁사 분석 저장:[/green] {path}")
        return path


def main():
    parser = argparse.ArgumentParser(description="경쟁사 SEO 자동 분석")
    parser.add_argument("--urls", nargs="+", help="분석할 URL 목록")
    args = parser.parse_args()

    spy = CompetitorSpy()
    spy.analyze_all(urls=args.urls)
    spy.print_comparison()
    spy.save_json()
    console.print("\n[bold green]경쟁사 분석 완료![/bold green]")


if __name__ == "__main__":
    main()
