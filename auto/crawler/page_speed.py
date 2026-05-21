"""
page_speed.py
Google PageSpeed Insights API(무료, API 키 불필요)로
소아벨라 페이지의 Core Web Vitals 점수를 자동 측정한다.

실행:
    python crawler/page_speed.py                        # 홈페이지 + 카테고리 전체
    python crawler/page_speed.py --url https://soavela.com/category/ring/
    python crawler/page_speed.py --mobile-only
"""

import sys
import json
import time
import argparse
from datetime import datetime
from pathlib import Path

import requests
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, CATEGORIES, AUDIT_DIR, REQUEST_TIMEOUT

console = Console()

PSI_API = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

# Core Web Vitals 기준값
THRESHOLDS = {
    "performance":          {"good": 90, "needs": 50},
    "lcp_ms":               {"good": 2500, "needs": 4000},
    "cls":                  {"good": 0.1,  "needs": 0.25},
    "fcp_ms":               {"good": 1800, "needs": 3000},
    "tbt_ms":               {"good": 200,  "needs": 600},
    "speed_index_ms":       {"good": 3400, "needs": 5800},
}


def score_color(score: float, metric: str) -> str:
    t = THRESHOLDS.get(metric, {"good": 90, "needs": 50})
    if isinstance(score, float) and metric.endswith("_ms"):
        if score <= t["good"]: return "green"
        if score <= t["needs"]: return "yellow"
        return "red"
    else:
        if score >= t["good"]: return "green"
        if score >= t["needs"]: return "yellow"
        return "red"


def fmt_ms(val) -> str:
    if val is None: return "—"
    ms = int(val)
    if ms >= 1000:
        return f"{ms/1000:.1f}s"
    return f"{ms}ms"


def measure_page(url: str, strategy: str = "mobile") -> dict:
    """PageSpeed Insights API 호출."""
    params = {"url": url, "strategy": strategy}
    try:
        resp = requests.get(PSI_API, params=params, timeout=REQUEST_TIMEOUT * 2)
        if resp.status_code != 200:
            return {"url": url, "strategy": strategy, "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        cat   = data.get("lighthouseResult", {}).get("categories", {})
        auds  = data.get("lighthouseResult", {}).get("audits", {})

        perf_score = round((cat.get("performance", {}).get("score") or 0) * 100)

        def metric(key):
            return auds.get(key, {}).get("numericValue")

        return {
            "url":              url,
            "strategy":         strategy,
            "performance":      perf_score,
            "lcp_ms":           metric("largest-contentful-paint"),
            "cls":              metric("cumulative-layout-shift"),
            "fcp_ms":           metric("first-contentful-paint"),
            "tbt_ms":           metric("total-blocking-time"),
            "speed_index_ms":   metric("speed-index"),
            "measured_at":      datetime.now().isoformat(),
        }
    except Exception as e:
        return {"url": url, "strategy": strategy, "error": str(e)}


def print_results(results: list[dict]):
    table = Table(
        title=f"Core Web Vitals — {datetime.now().strftime('%Y.%m.%d %H:%M')}",
        show_lines=True
    )
    table.add_column("URL", max_width=32, overflow="ellipsis")
    table.add_column("기기", justify="center")
    table.add_column("성능점수", justify="center")
    table.add_column("LCP", justify="center")
    table.add_column("CLS", justify="center")
    table.add_column("FCP", justify="center")
    table.add_column("TBT", justify="center")

    for r in results:
        if "error" in r:
            table.add_row(r["url"], r["strategy"], f"[red]오류: {r['error']}[/red]",
                          "—", "—", "—", "—")
            continue

        short_url = r["url"].replace(TARGET_URL, "") or "/"
        strategy  = "📱 모바일" if r["strategy"] == "mobile" else "🖥 데스크톱"

        perf  = r.get("performance", 0)
        lcp   = r.get("lcp_ms")
        cls   = r.get("cls")
        fcp   = r.get("fcp_ms")
        tbt   = r.get("tbt_ms")

        def c(val, metric):
            col = score_color(val, metric) if val is not None else "dim"
            return col

        cls_str = f"{cls:.3f}" if cls is not None else "—"

        table.add_row(
            short_url,
            strategy,
            f"[{c(perf,'performance')}]{perf}[/{c(perf,'performance')}]",
            f"[{c(lcp,'lcp_ms')}]{fmt_ms(lcp)}[/{c(lcp,'lcp_ms')}]",
            f"[{c(cls,'cls')}]{cls_str}[/{c(cls,'cls')}]",
            f"[{c(fcp,'fcp_ms')}]{fmt_ms(fcp)}[/{c(fcp,'fcp_ms')}]",
            f"[{c(tbt,'tbt_ms')}]{fmt_ms(tbt)}[/{c(tbt,'tbt_ms')}]",
        )

    console.print(table)
    console.print(
        "[dim]기준: LCP ≤2.5s · CLS ≤0.1 · FCP ≤1.8s · TBT ≤200ms (녹색=통과, 노랑=개선필요, 빨강=실패)[/dim]"
    )


def save_results(results: list[dict]) -> Path:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = AUDIT_DIR / f"pagespeed_{ts}.json"
    path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]PageSpeed 결과 저장:[/green] {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="PageSpeed Insights 자동 측정")
    parser.add_argument("--url", help="특정 URL 측정")
    parser.add_argument("--mobile-only",  action="store_true")
    parser.add_argument("--desktop-only", action="store_true")
    args = parser.parse_args()

    strategies = ["mobile", "desktop"]
    if args.mobile_only:
        strategies = ["mobile"]
    elif args.desktop_only:
        strategies = ["desktop"]

    if args.url:
        urls = [args.url]
    else:
        urls = [TARGET_URL] + [c["url"] for c in CATEGORIES]

    all_results = []
    total = len(urls) * len(strategies)
    done  = 0

    console.rule("[bold]Core Web Vitals 자동 측정[/bold]")
    console.print(f"PageSpeed Insights API (무료, API 키 불필요)\n")

    for url in urls:
        for strategy in strategies:
            done += 1
            console.print(f"  [{done}/{total}] {strategy}: [cyan]{url}[/cyan]")
            r = measure_page(url, strategy)
            all_results.append(r)
            if done < total:
                time.sleep(1.5)   # API 과부하 방지

    print_results(all_results)
    save_results(all_results)

    # 개선 제안 요약
    fails = [r for r in all_results if r.get("performance", 100) < 50 and "error" not in r]
    if fails:
        console.print(Panel(
            "\n".join(f"• {r['url']} ({r['strategy']}): 성능점수 {r['performance']}"
                      for r in fails),
            title="⚠ 성능 점수 50 미만 페이지",
            border_style="red"
        ))


if __name__ == "__main__":
    main()
