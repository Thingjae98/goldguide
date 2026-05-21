"""
sitemap_gen.py
소아벨라 사이트를 크롤해서 sitemap.xml을 자동 생성한다.
사이트맵을 Google Search Console / 네이버 서치어드바이저에 제출하기 위한 파일.

실행:
    python generator/sitemap_gen.py               # 전체 사이트맵 생성
    python generator/sitemap_gen.py --check       # 현재 sitemap.xml 검증만
    python generator/sitemap_gen.py --ping-google # 생성 후 Google에 핑 전송
"""

import sys
import re
import time
import gzip
import shutil
import argparse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, CATEGORIES, HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY, OUTPUT_DIR

console = Console()

SITEMAP_DIR  = OUTPUT_DIR / "sitemaps"
SITEMAP_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class SitemapURL:
    loc: str
    lastmod: str = ""
    changefreq: str = "weekly"
    priority: float = 0.5
    page_type: str = ""


# 우선순위 정책
PRIORITY_MAP = {
    "home":      (1.0, "daily"),
    "category":  (0.8, "weekly"),
    "product":   (0.7, "weekly"),
    "content":   (0.6, "monthly"),
    "other":     (0.4, "monthly"),
}


def classify_url(url: str) -> str:
    base = urlparse(TARGET_URL).netloc
    path = urlparse(url).path.lower()

    if url.rstrip("/") == TARGET_URL.rstrip("/"):
        return "home"
    if "product/list" in path or "category" in path:
        return "category"
    if "product/detail" in path or re.search(r"/product/\d+", path):
        return "product"
    if any(k in path for k in ("/board/", "/blog/", "/notice/", "/faq/")):
        return "content"
    return "other"


class SitemapGenerator:
    def __init__(self, base_url: str = TARGET_URL):
        self.base_url  = base_url.rstrip("/")
        self.base_host = urlparse(base_url).netloc
        self.session   = requests.Session()
        self.session.headers.update(HEADERS)
        self.found_urls: dict[str, SitemapURL] = {}

    def is_same_domain(self, url: str) -> bool:
        return urlparse(url).netloc in ("", self.base_host)

    def normalize(self, url: str, base: str) -> str:
        full   = urljoin(base, url)
        parsed = urlparse(full)
        # 쿼리 파라미터 보존, 프래그먼트 제거
        return parsed._replace(fragment="").geturl()

    def fetch(self, url: str):
        try:
            r = self.session.get(url, timeout=REQUEST_TIMEOUT)
            return BeautifulSoup(r.text, "lxml"), r.status_code, r.headers
        except Exception as e:
            console.print(f"  [red]fetch 오류: {e}[/red]")
            return None, 0, {}

    def get_lastmod(self, headers: dict) -> str:
        last_mod = headers.get("Last-Modified", "")
        if last_mod:
            try:
                dt = datetime.strptime(last_mod, "%a, %d %b %Y %H:%M:%S %Z")
                return dt.strftime("%Y-%m-%d")
            except Exception:
                pass
        return date.today().isoformat()

    def add_url(self, url: str, page_type: str, lastmod: str = ""):
        if url in self.found_urls:
            return
        pri, freq = PRIORITY_MAP.get(page_type, PRIORITY_MAP["other"])
        self.found_urls[url] = SitemapURL(
            loc=url,
            lastmod=lastmod or date.today().isoformat(),
            changefreq=freq,
            priority=pri,
            page_type=page_type,
        )

    def crawl_page(self, url: str, depth: int = 0, max_depth: int = 2):
        if url in self.found_urls or depth > max_depth:
            return

        console.print(f"  [dim](깊이 {depth})[/dim] [cyan]{url}[/cyan]")
        soup, status, headers = self.fetch(url)
        if soup is None or status != 200:
            return

        page_type = classify_url(url)
        lastmod   = self.get_lastmod(headers)
        self.add_url(url, page_type, lastmod)

        if depth >= max_depth:
            return

        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                continue
            target = self.normalize(href, url)
            if not self.is_same_domain(target):
                continue
            if target not in self.found_urls:
                time.sleep(REQUEST_DELAY * 0.5)
                self.crawl_page(target, depth + 1, max_depth)

    def collect_known_urls(self):
        """config.py의 카테고리 URL을 직접 추가."""
        self.add_url(TARGET_URL, "home")
        for cat in CATEGORIES:
            self.add_url(cat["url"], "category")

    def generate(self, max_depth: int = 1) -> list[SitemapURL]:
        console.rule("[bold]사이트맵 URL 수집[/bold]")
        self.collect_known_urls()   # 알려진 URL 먼저 추가
        self.crawl_page(TARGET_URL, max_depth=max_depth)
        return list(self.found_urls.values())

    def build_xml(self, urls: list[SitemapURL]) -> str:
        root = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

        # 우선순위 높은 순으로 정렬
        sorted_urls = sorted(urls, key=lambda u: u.priority, reverse=True)

        for u in sorted_urls:
            url_el = ET.SubElement(root, "url")
            ET.SubElement(url_el, "loc").text         = u.loc
            ET.SubElement(url_el, "lastmod").text     = u.lastmod
            ET.SubElement(url_el, "changefreq").text  = u.changefreq
            ET.SubElement(url_el, "priority").text    = str(u.priority)

        ET.indent(root, space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")

    def save(self, urls: list[SitemapURL]) -> dict:
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        xml  = self.build_xml(urls)

        # 일반 XML
        xml_path = SITEMAP_DIR / f"sitemap_{ts}.xml"
        xml_path.write_text(xml, encoding="utf-8")

        # Gzip 압축
        gz_path = SITEMAP_DIR / f"sitemap_{ts}.xml.gz"
        with open(xml_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)

        # 최신본 복사 (sitemap.xml)
        latest = SITEMAP_DIR / "sitemap.xml"
        shutil.copy(xml_path, latest)

        console.print(f"[green]사이트맵 저장:[/green]")
        console.print(f"  XML  : {xml_path}")
        console.print(f"  GZIP : {gz_path}")
        console.print(f"  최신 : {latest}")
        return {"xml": str(xml_path), "gz": str(gz_path), "latest": str(latest)}

    def ping_google(self):
        """Google에 사이트맵 색인 요청 핑 전송."""
        sitemap_url = f"{self.base_url}/sitemap.xml"
        ping = f"https://www.google.com/ping?sitemap={sitemap_url}"
        try:
            r = requests.get(ping, timeout=10)
            if r.status_code == 200:
                console.print(f"[green]✓ Google 핑 성공[/green] ({ping})")
            else:
                console.print(f"[yellow]⚠ Google 핑 응답: {r.status_code}[/yellow]")
        except Exception as e:
            console.print(f"[red]✗ Google 핑 실패: {e}[/red]")


def validate_sitemap(path: Path):
    """기존 sitemap.xml의 URL 수와 형식을 검증."""
    if not path.exists():
        console.print(f"[red]파일 없음: {path}[/red]")
        return

    tree = ET.parse(path)
    root = tree.getroot()
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = root.findall("sm:url", ns)

    table = Table(title=f"사이트맵 검증: {path.name}", show_lines=True)
    table.add_column("loc", max_width=50, overflow="ellipsis")
    table.add_column("priority", justify="center")
    table.add_column("changefreq", justify="center")
    table.add_column("lastmod", justify="center")

    for url_el in urls[:30]:
        loc  = (url_el.find("sm:loc", ns) or ET.Element("x")).text or ""
        pri  = (url_el.find("sm:priority", ns) or ET.Element("x")).text or ""
        freq = (url_el.find("sm:changefreq", ns) or ET.Element("x")).text or ""
        lmod = (url_el.find("sm:lastmod", ns) or ET.Element("x")).text or ""
        table.add_row(loc, pri, freq, lmod)

    console.print(table)
    console.print(f"\n총 URL: {len(urls)}개 (표시 최대 30개)")


def print_url_table(urls: list[SitemapURL]):
    table = Table(title="수집된 URL 목록", show_lines=True)
    table.add_column("타입", justify="center")
    table.add_column("URL", max_width=50, overflow="ellipsis")
    table.add_column("우선순위", justify="center")
    table.add_column("변경 주기", justify="center")

    type_colors = {
        "home": "bold cyan", "category": "green",
        "product": "yellow", "content": "blue", "other": "dim"
    }
    for u in sorted(urls, key=lambda x: x.priority, reverse=True):
        col = type_colors.get(u.page_type, "dim")
        short = u.loc.replace(TARGET_URL, "") or "/"
        table.add_row(
            f"[{col}]{u.page_type}[/{col}]",
            short,
            str(u.priority),
            u.changefreq,
        )
    console.print(table)


def main():
    parser = argparse.ArgumentParser(description="소아벨라 사이트맵 자동 생성")
    parser.add_argument("--check",       action="store_true", help="기존 sitemap.xml 검증만")
    parser.add_argument("--ping-google", action="store_true", help="Google에 사이트맵 핑 전송")
    parser.add_argument("--depth",       type=int, default=1, help="크롤 깊이 (기본 1)")
    args = parser.parse_args()

    gen = SitemapGenerator()

    if args.check:
        validate_sitemap(SITEMAP_DIR / "sitemap.xml")
        return

    urls = gen.generate(max_depth=args.depth)
    print_url_table(urls)

    paths = gen.save(urls)
    console.print(f"\n[bold green]사이트맵 생성 완료![/bold green] 총 {len(urls)}개 URL")
    console.print(
        "\n[bold]다음 단계:[/bold]\n"
        "1. Google Search Console → 사이트맵 → URL 입력: soavela.com/sitemap.xml\n"
        "2. 네이버 서치어드바이저 → 웹마스터 도구 → 사이트맵 제출\n"
        f"3. 생성된 파일을 Cafe24 FTP 루트에 업로드: {paths['latest']}"
    )

    if args.ping_google:
        gen.ping_google()


if __name__ == "__main__":
    main()
