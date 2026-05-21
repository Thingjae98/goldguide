"""
site_auditor.py
soavela.com을 자동으로 크롤링해서 SEO 문제를 감지하고
JSON + HTML 리포트를 output/audits/ 에 저장한다.

실행:
    python crawler/site_auditor.py
    python crawler/site_auditor.py --url https://soavela.com/product/list.html?cate_no=25
"""

import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.progress import track
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    TARGET_URL, CATEGORIES, HEADERS,
    REQUEST_TIMEOUT, REQUEST_DELAY, AUDIT_DIR, SITE_NAME, ensure_dirs
)
ensure_dirs()

console = Console()


# ── 데이터 구조 ──────────────────────────────────────────────────

@dataclass
class PageIssue:
    severity: str        # "critical" | "warning" | "info"
    category: str        # "meta" | "heading" | "image" | "link" | "performance"
    message: str
    detail: str = ""


@dataclass
class PageResult:
    url: str
    page_type: str       # "home" | "category" | "product" | "other"
    status_code: int = 0
    title: str = ""
    h1_count: int = 0
    h1_texts: list = field(default_factory=list)
    meta_description: str = ""
    canonical: str = ""
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    robots_meta: str = ""
    images_total: int = 0
    images_missing_alt: int = 0
    images_empty_alt: int = 0
    json_ld_types: list = field(default_factory=list)
    internal_links: int = 0
    broken_links: list = field(default_factory=list)
    issues: list = field(default_factory=list)
    crawled_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ── 크롤러 ───────────────────────────────────────────────────────

class SiteAuditor:
    def __init__(self, base_url: str = TARGET_URL):
        self.base_url = base_url.rstrip("/")
        self.session  = requests.Session()
        self.session.headers.update(HEADERS)
        self.results: list[PageResult] = []

    def fetch(self, url: str) -> tuple[Optional[BeautifulSoup], int]:
        """URL을 가져와 BeautifulSoup 반환. 실패 시 (None, status_code)."""
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "lxml")
                return soup, resp.status_code
            return None, resp.status_code
        except Exception as e:
            console.print(f"  [red]fetch 오류 {url}: {e}[/red]")
            return None, 0

    def audit_page(self, url: str, page_type: str = "other") -> PageResult:
        """단일 페이지를 감사하고 PageResult 반환."""
        result = PageResult(url=url, page_type=page_type)
        soup, status = self.fetch(url)
        result.status_code = status

        if soup is None:
            result.issues.append(asdict(PageIssue(
                severity="critical",
                category="access",
                message=f"페이지 접근 불가 (HTTP {status})",
                detail=url
            )))
            return result

        # ── title ────────────────────────────────────
        tag = soup.find("title")
        result.title = tag.get_text(strip=True) if tag else ""
        title_len = len(result.title)

        if not result.title:
            result.issues.append(asdict(PageIssue("critical", "meta",
                "title 태그 없음", "검색 결과 제목이 표시되지 않음")))
        elif title_len < 10:
            result.issues.append(asdict(PageIssue("warning", "meta",
                f"title 너무 짧음 ({title_len}자)", "30~60자 권장")))
        elif title_len > 65:
            result.issues.append(asdict(PageIssue("warning", "meta",
                f"title 너무 김 ({title_len}자)", "60자 초과 시 검색 결과에서 잘림")))

        # ── meta description ─────────────────────────
        tag = soup.find("meta", attrs={"name": "description"})
        result.meta_description = tag.get("content", "").strip() if tag else ""
        desc_len = len(result.meta_description)

        if not result.meta_description:
            result.issues.append(asdict(PageIssue("critical", "meta",
                "meta description 없음", "클릭률(CTR) 20~30% 손실")))
        elif desc_len < 50:
            result.issues.append(asdict(PageIssue("warning", "meta",
                f"meta description 너무 짧음 ({desc_len}자)", "120~160자 권장")))
        elif desc_len > 165:
            result.issues.append(asdict(PageIssue("warning", "meta",
                f"meta description 너무 김 ({desc_len}자)", "160자 초과 시 잘림")))

        # ── canonical ────────────────────────────────
        tag = soup.find("link", attrs={"rel": "canonical"})
        result.canonical = tag.get("href", "").strip() if tag else ""

        if not result.canonical:
            result.issues.append(asdict(PageIssue("critical", "meta",
                "canonical 태그 없음", "파라미터 URL 중복 색인 위험")))

        # ── Open Graph ───────────────────────────────
        for prop in ("og:title", "og:description", "og:image"):
            tag = soup.find("meta", property=prop)
            val = tag.get("content", "").strip() if tag else ""
            if prop == "og:title":       result.og_title = val
            elif prop == "og:description": result.og_description = val
            elif prop == "og:image":      result.og_image = val

        missing_og = [p for p, v in {
            "og:title": result.og_title,
            "og:description": result.og_description,
            "og:image": result.og_image
        }.items() if not v]

        if missing_og:
            result.issues.append(asdict(PageIssue("critical", "meta",
                f"Open Graph 태그 없음: {', '.join(missing_og)}",
                "SNS 공유 시 미리보기 카드 표시 불가")))

        # ── h1 ──────────────────────────────────────
        h1_tags = soup.find_all("h1")
        result.h1_count = len(h1_tags)
        result.h1_texts = [t.get_text(strip=True) for t in h1_tags]

        if result.h1_count == 0:
            result.issues.append(asdict(PageIssue("critical", "heading",
                "h1 태그 없음", "검색엔진이 페이지 주제를 파악 불가")))
        elif result.h1_count > 1:
            result.issues.append(asdict(PageIssue("warning", "heading",
                f"h1 태그 {result.h1_count}개 (1개만 권장)",
                f"텍스트: {' / '.join(result.h1_texts)}")))

        # ── 이미지 alt ───────────────────────────────
        imgs = soup.find_all("img")
        result.images_total = len(imgs)
        for img in imgs:
            alt = img.get("alt")
            if alt is None:
                result.images_missing_alt += 1
            elif alt.strip() == "":
                # 장식용 이미지(alt="")는 이슈 아님
                pass

        if result.images_missing_alt > 0:
            result.issues.append(asdict(PageIssue("critical", "image",
                f"alt 텍스트 없는 이미지 {result.images_missing_alt}개 / 전체 {result.images_total}개",
                "이미지 검색 노출 불가, 접근성 법적 요건 미충족")))

        # ── JSON-LD ──────────────────────────────────
        ld_scripts = soup.find_all("script", type="application/ld+json")
        for s in ld_scripts:
            try:
                data = json.loads(s.string or "")
                t = data.get("@type", "")
                if t:
                    result.json_ld_types.append(t)
            except Exception:
                pass

        if not result.json_ld_types:
            result.issues.append(asdict(PageIssue("critical", "structured_data",
                "JSON-LD 구조화 데이터 없음",
                "리치 스니펫(별점·가격·FAQ) 검색 노출 불가")))

        # ── robots meta ──────────────────────────────
        tag = soup.find("meta", attrs={"name": "robots"})
        result.robots_meta = tag.get("content", "").lower() if tag else ""
        if "noindex" in result.robots_meta:
            result.issues.append(asdict(PageIssue("critical", "meta",
                "robots=noindex — 색인 차단됨!", "검색 결과에 표시 안 됨")))

        # ── 내부 링크 수 ─────────────────────────────
        result.internal_links = len([
            a for a in soup.find_all("a", href=True)
            if self.base_url in a["href"] or a["href"].startswith("/")
        ])

        return result

    def audit_site(self, extra_urls: list[str] = None) -> list[PageResult]:
        """홈 + 카테고리 전체 감사. extra_urls 추가 가능."""
        urls_to_audit = [(self.base_url, "home")]
        for cat in CATEGORIES:
            urls_to_audit.append((cat["url"], "category"))
        if extra_urls:
            for u in extra_urls:
                urls_to_audit.append((u, "other"))

        console.rule("[bold]soavela.com SEO 자동 감사 시작[/bold]")
        console.print(f"대상 페이지: {len(urls_to_audit)}개\n")

        for url, ptype in track(urls_to_audit, description="크롤링 중..."):
            result = self.audit_page(url, ptype)
            self.results.append(result)
            time.sleep(REQUEST_DELAY)

        return self.results

    # ── 리포트 출력 ──────────────────────────────────────────────

    def print_summary(self):
        """터미널에 요약 테이블 출력."""
        table = Table(title=f"{SITE_NAME} SEO 감사 결과", show_lines=True)
        table.add_column("페이지", style="cyan", max_width=40)
        table.add_column("상태", justify="center")
        table.add_column("Critical", justify="center", style="red")
        table.add_column("Warning", justify="center", style="yellow")
        table.add_column("h1", justify="center")
        table.add_column("alt누락", justify="center")
        table.add_column("JSON-LD", justify="center")

        for r in self.results:
            criticals = sum(1 for i in r.issues if i["severity"] == "critical")
            warnings  = sum(1 for i in r.issues if i["severity"] == "warning")
            status_str = f"[green]{r.status_code}[/green]" if r.status_code == 200 \
                         else f"[red]{r.status_code}[/red]"
            table.add_row(
                r.url.replace(self.base_url, ""),
                status_str,
                str(criticals) if criticals else "[dim]0[/dim]",
                str(warnings)  if warnings  else "[dim]0[/dim]",
                f"[red]{r.h1_count}[/red]" if r.h1_count == 0 else str(r.h1_count),
                f"[red]{r.images_missing_alt}[/red]" if r.images_missing_alt else "[dim]0[/dim]",
                "[green]✓[/green]" if r.json_ld_types else "[red]✗[/red]",
            )

        console.print(table)

        total_critical = sum(
            sum(1 for i in r.issues if i["severity"] == "critical")
            for r in self.results
        )
        total_warning = sum(
            sum(1 for i in r.issues if i["severity"] == "warning")
            for r in self.results
        )
        console.print(f"\n[bold red]Critical 합계: {total_critical}[/bold red]  "
                      f"[bold yellow]Warning 합계: {total_warning}[/bold yellow]\n")

    def save_json(self) -> Path:
        """감사 결과를 JSON으로 저장."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = AUDIT_DIR / f"audit_{timestamp}.json"
        data = {
            "site": TARGET_URL,
            "audited_at": datetime.now().isoformat(),
            "summary": {
                "pages": len(self.results),
                "total_critical": sum(
                    sum(1 for i in r.issues if i["severity"] == "critical")
                    for r in self.results
                ),
                "total_warning": sum(
                    sum(1 for i in r.issues if i["severity"] == "warning")
                    for r in self.results
                ),
            },
            "pages": [asdict(r) for r in self.results],
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]JSON 저장:[/green] {path}")
        return path


# ── 진입점 ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="soavela.com SEO 자동 감사")
    parser.add_argument("--url", help="추가로 감사할 URL (단일)", default=None)
    parser.add_argument("--single", action="store_true", help="--url 하나만 감사")
    args = parser.parse_args()

    auditor = SiteAuditor()

    if args.single and args.url:
        result = auditor.audit_page(args.url)
        auditor.results = [result]
    else:
        extra = [args.url] if args.url else []
        auditor.audit_site(extra_urls=extra)

    auditor.print_summary()
    json_path = auditor.save_json()

    # report_builder가 있으면 HTML 리포트도 자동 생성
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from report.report_builder import build_audit_report
        html_path = build_audit_report(json_path)
        console.print(f"[green]HTML 리포트:[/green] {html_path}")
    except ImportError:
        pass

    console.print("\n[bold green]감사 완료![/bold green]")


if __name__ == "__main__":
    main()
