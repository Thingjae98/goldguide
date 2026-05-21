"""
rank_tracker.py
타겟 키워드를 구글/네이버에서 검색해서 soavela.com의 순위를 추적한다.
결과를 JSON으로 누적 저장하고 변화(상승/하락)를 표시한다.

실행:
    python monitor/rank_tracker.py               # 전체 키워드 추적
    python monitor/rank_tracker.py --keyword 금반지  # 단일 키워드
    python monitor/rank_tracker.py --history     # 과거 순위 변화 출력

주의:
    - 구글/네이버 자동 크롤링은 이용약관 위반 가능성이 있음
    - 개발/테스트 목적으로만 사용
    - 실제 운영은 Google Search Console API 사용 권장
"""

import sys
import json
import time
import random
import argparse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import KEYWORDS, TARGET_URL, HEADERS, RANK_DIR, ensure_dirs
ensure_dirs()

console = Console()

GOOGLE_SEARCH_URL = "https://www.google.com/search"
NAVER_SEARCH_URL  = "https://search.naver.com/search.naver"

# 추적 히스토리 파일 (누적)
HISTORY_FILE = RANK_DIR / "rank_history.json"


# ── 검색 순위 추적 ───────────────────────────────────────────────

class RankTracker:
    def __init__(self, target_domain: str = "soavela.com"):
        self.target = target_domain
        self.session = requests.Session()
        # 봇 탐지 우회를 위한 헤더 (교육/테스트 목적)
        self.session.headers.update({
            **HEADERS,
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
        })

    def _delay(self):
        """요청 간 랜덤 딜레이로 서버 부하 방지."""
        time.sleep(random.uniform(2.5, 5.0))

    def check_google(self, keyword: str, pages: int = 3) -> dict:
        """구글에서 키워드 검색 후 soavela.com 순위 반환."""
        result = {"engine": "google", "keyword": keyword, "rank": -1, "url": "", "found_on_page": -1}

        for page in range(pages):
            try:
                params = {"q": keyword, "hl": "ko", "gl": "kr", "start": page * 10}
                resp = self.session.get(GOOGLE_SEARCH_URL, params=params, timeout=10)

                if resp.status_code != 200:
                    console.print(f"  [yellow]구글 응답 이상: {resp.status_code}[/yellow]")
                    break

                soup = BeautifulSoup(resp.text, "lxml")

                # 구글 검색 결과 링크 추출
                links = soup.select("div.g a[href]")
                if not links:
                    # 구글이 봇으로 감지한 경우 다른 selector 시도
                    links = soup.select("a[href*='http']")

                for i, link in enumerate(links):
                    href = link.get("href", "")
                    if self.target in href:
                        rank = page * 10 + i + 1
                        result["rank"] = rank
                        result["url"] = href
                        result["found_on_page"] = page + 1
                        return result

                self._delay()

            except Exception as e:
                console.print(f"  [red]구글 검색 오류: {e}[/red]")
                break

        return result

    def check_naver(self, keyword: str, pages: int = 3) -> dict:
        """네이버에서 키워드 검색 후 soavela.com 순위 반환."""
        result = {"engine": "naver", "keyword": keyword, "rank": -1, "url": "", "found_on_page": -1}

        for page in range(1, pages + 1):
            try:
                params = {"query": keyword, "where": "web", "start": (page - 1) * 10 + 1}
                resp = self.session.get(NAVER_SEARCH_URL, params=params, timeout=10)

                if resp.status_code != 200:
                    break

                soup = BeautifulSoup(resp.text, "lxml")

                # 네이버 웹 검색 결과 링크
                links = soup.select(".total_wrap a.link_tit") or \
                        soup.select(".api_subject_bx a") or \
                        soup.select("a.total_tit")

                for i, link in enumerate(links):
                    href = link.get("href", "")
                    if self.target in href:
                        rank = (page - 1) * 10 + i + 1
                        result["rank"] = rank
                        result["url"] = href
                        result["found_on_page"] = page
                        return result

                self._delay()

            except Exception as e:
                console.print(f"  [red]네이버 검색 오류: {e}[/red]")
                break

        return result

    def track_keywords(self, keywords: list[str], engines: list[str] = ("google", "naver")) -> list[dict]:
        """전체 키워드 순위 추적."""
        results = []
        total = len(keywords) * len(engines)
        done = 0

        for keyword in keywords:
            for engine in engines:
                console.print(f"  [{done+1}/{total}] {engine}: [cyan]{keyword}[/cyan]")
                if engine == "google":
                    r = self.check_google(keyword)
                else:
                    r = self.check_naver(keyword)

                r["checked_at"] = datetime.now().isoformat()
                results.append(r)
                done += 1
                self._delay()

        return results

    # ── 히스토리 관리 ──────────────────────────────────────────────

    def load_history(self) -> list[dict]:
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return []

    def save_history(self, new_results: list[dict]):
        history = self.load_history()
        history.extend(new_results)
        HISTORY_FILE.write_text(
            json.dumps(history, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_previous_rank(self, keyword: str, engine: str) -> int:
        """히스토리에서 이전 순위 반환. 없으면 -1."""
        history = self.load_history()
        for item in reversed(history):
            if item.get("keyword") == keyword and item.get("engine") == engine:
                return item.get("rank", -1)
        return -1

    # ── 출력 ──────────────────────────────────────────────────────

    def print_results(self, results: list[dict]):
        table = Table(title=f"soavela.com 키워드 순위 추적 — {datetime.now().strftime('%Y.%m.%d %H:%M')}", show_lines=True)
        table.add_column("키워드", style="cyan", min_width=18)
        table.add_column("검색엔진", justify="center")
        table.add_column("현재 순위", justify="center")
        table.add_column("변화", justify="center")
        table.add_column("URL", max_width=35, overflow="ellipsis")

        for r in results:
            rank = r.get("rank", -1)
            engine = r.get("engine", "")
            keyword = r.get("keyword", "")
            prev = self.get_previous_rank(keyword, engine)

            if rank == -1:
                rank_str = "[dim]30위+[/dim]"
            elif rank <= 3:
                rank_str = f"[bold green]{rank}위[/bold green]"
            elif rank <= 10:
                rank_str = f"[green]{rank}위[/green]"
            elif rank <= 20:
                rank_str = f"[yellow]{rank}위[/yellow]"
            else:
                rank_str = f"[red]{rank}위[/red]"

            if prev == -1 or rank == -1:
                change_str = "[dim]—[/dim]"
            elif rank < prev:
                diff = prev - rank
                change_str = f"[green]▲{diff}[/green]"
            elif rank > prev:
                diff = rank - prev
                change_str = f"[red]▼{diff}[/red]"
            else:
                change_str = "[dim]→[/dim]"

            engine_icon = "🔍" if engine == "google" else "🟢"
            url_str = r.get("url", "")[:35] or "[dim]미노출[/dim]"

            table.add_row(keyword, f"{engine_icon} {engine}", rank_str, change_str, url_str)

        console.print(table)

    def print_history_summary(self):
        """키워드별 순위 변화 추세 출력."""
        history = self.load_history()
        if not history:
            console.print("[yellow]아직 추적 데이터가 없습니다.[/yellow]")
            return

        # 키워드 × 엔진별 그룹
        groups = {}
        for item in history:
            key = (item["keyword"], item["engine"])
            groups.setdefault(key, []).append(item)

        table = Table(title="순위 추적 히스토리", show_lines=True)
        table.add_column("키워드")
        table.add_column("엔진")
        table.add_column("첫 측정")
        table.add_column("최근 순위")
        table.add_column("최고 순위")
        table.add_column("추세")

        for (kw, eng), items in sorted(groups.items()):
            ranks = [i["rank"] for i in items if i["rank"] != -1]
            first_rank = items[0]["rank"] if items else -1
            last_rank  = items[-1]["rank"]
            best_rank  = min(ranks) if ranks else -1
            first_date = items[0]["checked_at"][:10]

            trend = "—"
            if len(ranks) >= 2:
                if ranks[-1] < ranks[0]:
                    trend = f"[green]▲ 상승[/green]"
                elif ranks[-1] > ranks[0]:
                    trend = f"[red]▼ 하락[/red]"
                else:
                    trend = "[dim]→ 유지[/dim]"

            def fmt(r):
                return f"{r}위" if r != -1 else "30위+"

            table.add_row(kw, eng, first_date, fmt(last_rank), fmt(best_rank), trend)

        console.print(table)


# ── 진입점 ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="소아벨라 키워드 순위 추적기")
    parser.add_argument("--keyword", help="단일 키워드 추적")
    parser.add_argument("--engine",  default="both", choices=["google", "naver", "both"])
    parser.add_argument("--history", action="store_true", help="히스토리 요약 출력")
    args = parser.parse_args()

    tracker = RankTracker()

    if args.history:
        tracker.print_history_summary()
        return

    engines = ["google", "naver"] if args.engine == "both" else [args.engine]
    keywords = [args.keyword] if args.keyword else KEYWORDS

    console.rule(f"[bold]소아벨라 키워드 순위 추적 ({len(keywords)}개 키워드)[/bold]")
    console.print(f"엔진: {', '.join(engines)}\n")

    results = tracker.track_keywords(keywords, engines)
    tracker.print_results(results)
    tracker.save_history(results)

    # 단일 날짜 스냅샷도 저장
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap_path = RANK_DIR / f"rank_{ts}.json"
    snap_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"\n[green]순위 데이터 저장:[/green] {snap_path}")
    console.print(f"[green]히스토리 누적:[/green] {HISTORY_FILE}")


if __name__ == "__main__":
    main()
