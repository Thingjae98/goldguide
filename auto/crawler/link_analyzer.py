"""
link_analyzer.py
소아벨라 사이트의 내부 링크 구조를 분석한다.
- 각 페이지의 내부/외부 링크 수
- 깨진 링크(404) 탐지
- 링크 깊이(홈에서 몇 클릭 거리)
- 앵커 텍스트 키워드 분포

실행:
    python crawler/link_analyzer.py
    python crawler/link_analyzer.py --depth 2     # 크롤 깊이
    python crawler/link_analyzer.py --no-check    # 깨진 링크 검사 생략
"""

import sys
import json
import time
import argparse
from collections import defaultdict, Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY, AUDIT_DIR

console = Console()


@dataclass
class LinkInfo:
    source_url: str
    target_url: str
    anchor_text: str
    is_internal: bool
    depth: int = 0
    status_code: int = 0
    is_broken: bool = False


@dataclass
class PageLinkSummary:
    url: str
    depth: int
    internal_links: list = field(default_factory=list)
    external_links: list = field(default_factory=list)
    broken_links: list = field(default_factory=list)
    anchor_keywords: list = field(default_factory=list)


class LinkAnalyzer:
    def __init__(self, base_url: str = TARGET_URL, max_depth: int = 2, check_broken: bool = True):
        self.base_url   = base_url.rstrip("/")
        self.base_host  = urlparse(base_url).netloc
        self.max_depth  = max_depth
        self.check_broken = check_broken

        self.session = requests.Session()
        self.session.headers.update(HEADERS)

        self.visited: set[str] = set()
        self.all_links: list[LinkInfo] = []
        self.page_summaries: list[PageLinkSummary] = []

    def is_internal(self, url: str) -> bool:
        return urlparse(url).netloc in ("", self.base_host)

    def normalize(self, url: str, base: str) -> str:
        full = urljoin(base, url)
        # 프래그먼트 제거
        parsed = urlparse(full)
        return parsed._replace(fragment="").geturl()

    def fetch(self, url: str):
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            return r, r.status_code
        except Exception:
            return None, 0

    def check_url(self, url: str) -> int:
        try:
            r = self.session.head(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            return r.status_code
        except Exception:
            return 0

    def crawl(self, url: str, depth: int = 0):
        if url in self.visited or depth > self.max_depth:
            return
        self.visited.add(url)

        console.print(f"  [dim](깊이 {depth})[/dim] [cyan]{url}[/cyan]")
        resp, status = self.fetch(url)
        if resp is None or status != 200:
            return

        soup   = BeautifulSoup(resp.text, "lxml")
        summary = PageLinkSummary(url=url, depth=depth)
        anchor_texts = []

        for a in soup.find_all("a", href=True):
            href   = a["href"].strip()
            text   = a.get_text(strip=True)[:60]

            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue

            target = self.normalize(href, url)
            internal = self.is_internal(target)

            link = LinkInfo(
                source_url=url,
                target_url=target,
                anchor_text=text,
                is_internal=internal,
                depth=depth,
            )

            if internal:
                summary.internal_links.append(target)
                if text:
                    anchor_texts.append(text)
                # 내부 링크만 재귀 크롤
                if target not in self.visited:
                    time.sleep(REQUEST_DELAY)
                    self.crawl(target, depth + 1)
            else:
                summary.external_links.append(target)

            self.all_links.append(link)

        # 깨진 링크 검사 (외부 링크 중 HEAD 요청)
        if self.check_broken:
            for ext_url in summary.external_links[:10]:  # 외부 링크 최대 10개
                code = self.check_url(ext_url)
                if code in (0, 404, 410):
                    summary.broken_links.append({"url": ext_url, "status": code})
                    for lnk in self.all_links:
                        if lnk.target_url == ext_url:
                            lnk.status_code = code
                            lnk.is_broken   = True

        summary.anchor_keywords = anchor_texts
        self.page_summaries.append(summary)

    def analyze(self) -> dict:
        console.rule("[bold]내부 링크 구조 분석[/bold]")
        self.crawl(self.base_url, depth=0)

        # 통계
        all_anchor_words: list[str] = []
        for s in self.page_summaries:
            all_anchor_words.extend(s.anchor_keywords)

        word_freq: Counter = Counter()
        for text in all_anchor_words:
            for word in text.split():
                if len(word) >= 2:
                    word_freq[word] += 1

        broken_all = [l for l in self.all_links if l.is_broken]
        internal_all = [l for l in self.all_links if l.is_internal]

        return {
            "base_url":          self.base_url,
            "pages_crawled":     len(self.page_summaries),
            "total_links":       len(self.all_links),
            "internal_links":    len(internal_all),
            "external_links":    len(self.all_links) - len(internal_all),
            "broken_links":      len(broken_all),
            "top_anchor_words":  word_freq.most_common(20),
            "pages":             [asdict(s) for s in self.page_summaries],
            "broken_details":    [asdict(l) for l in broken_all],
            "analyzed_at":       datetime.now().isoformat(),
        }

    def print_report(self, result: dict):
        # 페이지별 요약
        table = Table(title="페이지별 링크 현황", show_lines=True)
        table.add_column("URL", max_width=38, overflow="ellipsis")
        table.add_column("깊이", justify="center")
        table.add_column("내부↩", justify="center")
        table.add_column("외부↗", justify="center")
        table.add_column("깨진", justify="center")

        for s in self.page_summaries:
            short = s["url"].replace(self.base_url, "") or "/"
            broken_str = (f"[red]{len(s['broken_links'])}[/red]"
                          if s["broken_links"] else "[green]0[/green]")
            table.add_row(
                short,
                str(s["depth"]),
                str(len(s["internal_links"])),
                str(len(s["external_links"])),
                broken_str,
            )
        console.print(table)

        # 앵커 텍스트 상위 키워드
        console.print("\n[bold]앵커 텍스트 상위 키워드[/bold]")
        kw_table = Table(show_lines=True)
        kw_table.add_column("키워드")
        kw_table.add_column("출현 횟수", justify="right")

        for word, cnt in result["top_anchor_words"][:10]:
            kw_table.add_row(word, str(cnt))
        console.print(kw_table)

        # 깨진 링크
        if result["broken_links"] > 0:
            broken_list = "\n".join(
                f"  • {b['target_url']} (HTTP {b['status_code']}) ← {b['source_url']}"
                for b in result["broken_details"]
            )
            console.print(Panel(broken_list, title=f"⚠ 깨진 링크 {result['broken_links']}개", border_style="red"))
        else:
            console.print("\n[green]✓ 깨진 링크 없음[/green]")

        # 요약
        console.print(
            f"\n크롤 페이지 {result['pages_crawled']}개 | "
            f"전체 링크 {result['total_links']}개 "
            f"(내부 {result['internal_links']} / 외부 {result['external_links']})"
        )

    def save(self, result: dict) -> Path:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = AUDIT_DIR / f"links_{ts}.json"
        path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]링크 분석 저장:[/green] {path}")
        return path


def main():
    parser = argparse.ArgumentParser(description="소아벨라 내부 링크 구조 분석")
    parser.add_argument("--depth",    type=int, default=2, help="크롤 깊이 (기본 2)")
    parser.add_argument("--no-check", action="store_true", help="깨진 링크 검사 생략")
    args = parser.parse_args()

    analyzer = LinkAnalyzer(max_depth=args.depth, check_broken=not args.no_check)
    result = analyzer.analyze()
    analyzer.print_report(result)
    analyzer.save(result)


if __name__ == "__main__":
    main()
