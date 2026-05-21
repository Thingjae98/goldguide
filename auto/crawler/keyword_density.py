"""
keyword_density.py
소아벨라 페이지에서 타겟 키워드 밀도를 분석한다.
- 페이지 내 키워드 출현 횟수 및 밀도(%)
- title/h1/h2/description에 키워드 포함 여부
- 이상적인 밀도(1~3%) 대비 현재 상태
- TF-IDF 스타일 중요도 점수

실행:
    python crawler/keyword_density.py
    python crawler/keyword_density.py --url https://soavela.com/product/list.html?cate_no=25
    python crawler/keyword_density.py --keyword "순금반지"
"""

import sys
import json
import re
import argparse
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, CATEGORIES, KEYWORDS, HEADERS, REQUEST_TIMEOUT, AUDIT_DIR

console = Console()

GOLD_KEYWORDS = [
    "순금", "24k", "24K", "14k", "14K", "18k", "18K",
    "금반지", "금목걸이", "금팔찌", "금귀걸이", "금커플링",
    "돌반지", "주얼리", "골드", "소아벨라",
]


@dataclass
class KeywordResult:
    keyword: str
    count: int
    density: float
    in_title: bool
    in_h1: bool
    in_h2: bool
    in_description: bool
    in_canonical_path: bool

    @property
    def coverage_score(self) -> int:
        """title·h1·h2·description 포함 여부 합산 (최대 4점)."""
        return sum([self.in_title, self.in_h1, self.in_h2, self.in_description])


@dataclass
class PageDensityReport:
    url: str
    word_count: int
    title: str
    h1: str
    keyword_results: list[KeywordResult] = field(default_factory=list)
    analyzed_at: str = ""

    def __post_init__(self):
        if not self.analyzed_at:
            self.analyzed_at = datetime.now().isoformat()


def extract_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator=" ")


def count_keyword(text: str, keyword: str) -> int:
    return len(re.findall(re.escape(keyword), text, re.IGNORECASE))


def analyze_page(url: str, keywords: list[str]) -> PageDensityReport:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        console.print(f"[red]fetch 오류 ({url}): {e}[/red]")
        return PageDensityReport(url=url, word_count=0, title="", h1="")

    text = extract_text(BeautifulSoup(resp.text, "lxml"))
    words = text.split()
    word_count = len(words)

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else ""

    h1_tag = soup.find("h1")
    h1 = h1_tag.get_text(strip=True) if h1_tag else ""

    h2_texts = " ".join(t.get_text(strip=True) for t in soup.find_all("h2"))

    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = desc_tag.get("content", "") if desc_tag else ""

    canon_tag = soup.find("link", attrs={"rel": "canonical"})
    canonical_path = (canon_tag.get("href", "") if canon_tag else url).lower()

    report = PageDensityReport(url=url, word_count=word_count, title=title, h1=h1)

    for kw in keywords:
        kw_lower = kw.lower()
        cnt = count_keyword(text, kw)
        density = round(cnt / word_count * 100, 2) if word_count else 0.0

        result = KeywordResult(
            keyword=kw,
            count=cnt,
            density=density,
            in_title=kw_lower in title.lower(),
            in_h1=kw_lower in h1.lower(),
            in_h2=kw_lower in h2_texts.lower(),
            in_description=kw_lower in description.lower(),
            in_canonical_path=kw_lower in canonical_path,
        )
        report.keyword_results.append(result)

    return report


def density_color(density: float) -> str:
    if density == 0:     return "red"
    if density < 0.5:    return "yellow"
    if density <= 3.0:   return "green"
    return "orange3"  # 과도한 키워드 스터핑


def print_report(reports: list[PageDensityReport], top_n: int = 8):
    for rpt in reports:
        short_url = rpt.url.replace(TARGET_URL, "") or "/"
        table = Table(
            title=f"키워드 밀도 — {short_url} (총 단어 {rpt.word_count}개)",
            show_lines=True
        )
        table.add_column("키워드", style="cyan")
        table.add_column("출현", justify="right")
        table.add_column("밀도", justify="right")
        table.add_column("title", justify="center")
        table.add_column("H1", justify="center")
        table.add_column("H2", justify="center")
        table.add_column("description", justify="center")
        table.add_column("점수", justify="center")

        chk = lambda v: "[green]✓[/green]" if v else "[red]✗[/red]"

        # 출현 횟수 상위 N개
        top = sorted(rpt.keyword_results, key=lambda r: r.count, reverse=True)[:top_n]
        for r in top:
            dc = density_color(r.density)
            table.add_row(
                r.keyword,
                str(r.count),
                f"[{dc}]{r.density:.2f}%[/{dc}]",
                chk(r.in_title),
                chk(r.in_h1),
                chk(r.in_h2),
                chk(r.in_description),
                f"{'★' * r.coverage_score}{'☆' * (4 - r.coverage_score)}",
            )

        console.print(table)

    console.print("[dim]밀도 기준: 0% = 빨강 / 0.5% 미만 = 노랑 / 0.5~3% = 초록 / 3% 초과 = 과도[/dim]")


def save_reports(reports: list[PageDensityReport]) -> Path:
    data = []
    for r in reports:
        d = asdict(r)
        data.append(d)

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = AUDIT_DIR / f"keyword_density_{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]키워드 밀도 분석 저장:[/green] {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="키워드 밀도 분석")
    parser.add_argument("--url",     help="특정 URL 분석")
    parser.add_argument("--keyword", help="추가 키워드 (쉼표 구분)")
    args = parser.parse_args()

    keywords = list(GOLD_KEYWORDS)
    if args.keyword:
        extra = [k.strip() for k in args.keyword.split(",") if k.strip()]
        keywords = list(dict.fromkeys(extra + keywords))

    if args.url:
        urls = [args.url]
    else:
        urls = [TARGET_URL] + [c["url"] for c in CATEGORIES[:3]]  # 홈 + 상위 3개 카테고리

    console.rule("[bold]키워드 밀도 분석[/bold]")

    reports = []
    for i, url in enumerate(urls, 1):
        console.print(f"  [{i}/{len(urls)}] [cyan]{url}[/cyan]")
        rpt = analyze_page(url, keywords)
        reports.append(rpt)

    print_report(reports)
    save_reports(reports)

    # 핵심 키워드 미포함 경고
    missing = []
    core = ["순금", "금반지", "소아벨라"]
    for rpt in reports:
        short = rpt.url.replace(TARGET_URL, "") or "/"
        for kw in core:
            res = next((r for r in rpt.keyword_results if r.keyword == kw), None)
            if res and res.count == 0:
                missing.append(f"{short} → '{kw}' 미출현")

    if missing:
        console.print(Panel(
            "\n".join(f"• {m}" for m in missing),
            title="⚠ 핵심 키워드 미포함 페이지",
            border_style="yellow"
        ))


if __name__ == "__main__":
    main()
