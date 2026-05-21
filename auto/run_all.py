"""
run_all.py
소아벨라 SEO 자동화 전체 파이프라인 실행기.
site_auditor → competitor_spy → page_speed → link_analyzer →
serp_preview → meta_generator → rank_tracker → report_builder
순서로 실행하고, 최종 통합 리포트를 생성한다.

실행:
    python run_all.py               # 전체 파이프라인
    python run_all.py --skip-rank   # 순위 추적 제외 (빠른 실행)
    python run_all.py --audit-only  # 감사 계열만 실행
    python run_all.py --report-only # 최신 JSON으로 리포트만 재생성
    python run_all.py --fast        # 핵심 단계만 (감사+리포트)
"""

import sys
import time
import argparse
import traceback
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich import print as rprint

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    AUDIT_DIR, CONTENT_DIR, META_DIR, RANK_DIR, OUTPUT_DIR,
    SITE_NAME, TARGET_URL, KEYWORDS, ensure_dirs
)
ensure_dirs()

console = Console()

STEP_RESULTS: dict[str, dict] = {}


def section(title: str):
    console.print()
    console.rule(f"[bold cyan]{title}[/bold cyan]")
    console.print()


def ok(label: str, detail: str = ""):
    msg = f"[bold green]✓[/bold green] {label}"
    if detail:
        msg += f" [dim]{detail}[/dim]"
    console.print(msg)


def fail(label: str, err: str = ""):
    msg = f"[bold red]✗[/bold red] {label}"
    if err:
        msg += f" [dim red]{err}[/dim red]"
    console.print(msg)


def warn(label: str):
    console.print(f"[bold yellow]⚠[/bold yellow] {label}")


# ── Step 1: 사이트 감사 ──────────────────────────────────────────────

def run_audit() -> dict:
    section("Step 1 — 사이트 SEO 감사")
    try:
        from crawler.site_auditor import SiteAuditor
        auditor = SiteAuditor()
        pages = auditor.audit_site()
        auditor.print_summary()
        path = auditor.save_json()
        ok("감사 완료", str(path))
        summary = {
            "total_critical": sum(
                sum(1 for i in r.issues if i["severity"] == "critical") for r in auditor.results
            ),
            "total_warning": sum(
                sum(1 for i in r.issues if i["severity"] == "warning") for r in auditor.results
            ),
        }
        return {"status": "ok", "path": str(path), "summary": summary, "pages": pages}
    except Exception as e:
        fail("감사 실패", str(e))
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Step 2: 경쟁사 분석 ─────────────────────────────────────────────

def run_competitor() -> dict:
    section("Step 2 — 경쟁사 분석")
    try:
        from crawler.competitor_spy import CompetitorSpy
        spy = CompetitorSpy()
        results = spy.analyze_all()
        if results:
            spy.print_comparison()
            path = spy.save_json()
            ok("경쟁사 분석 완료", str(path))
            return {"status": "ok", "path": str(path), "count": len(results)}
        else:
            warn("경쟁사 URL 미설정 — .env의 COMPETITORS를 확인하세요")
            return {"status": "skipped"}
    except Exception as e:
        fail("경쟁사 분석 실패", str(e))
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Step 3: 메타태그 생성 ────────────────────────────────────────────

def run_meta_generator() -> dict:
    section("Step 3 — 상품 메타태그 자동 생성")
    try:
        from generator.meta_generator import SAMPLE_PRODUCTS, generate_meta_batch, save_results
        console.print(f"샘플 {len(SAMPLE_PRODUCTS)}개 상품으로 메타태그 생성 중...")
        results = generate_meta_batch(SAMPLE_PRODUCTS)
        paths = save_results(results)
        ok("메타태그 생성 완료")
        console.print(f"  JSON : {paths['json']}")
        console.print(f"  CSV  : {paths['csv']}  (Cafe24 일괄 업로드용)")
        console.print(f"  HTML : {paths['html']}")
        return {"status": "ok", "paths": paths, "count": len(results)}
    except Exception as e:
        fail("메타태그 생성 실패", str(e))
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Step 4: 키워드 순위 추적 ─────────────────────────────────────────

def run_rank_tracker() -> dict:
    section("Step 4 — 키워드 순위 추적")
    try:
        from monitor.rank_tracker import RankTracker
        tracker = RankTracker()
        console.print(f"{len(KEYWORDS)}개 키워드 × Google+Naver 추적 시작...")
        console.print("[yellow]⚠ 검색엔진 봇 탐지로 인해 일부 결과가 누락될 수 있습니다.[/yellow]")
        results = tracker.track_keywords(KEYWORDS)
        tracker.print_results(results)
        tracker.save_history(results)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snap_path = RANK_DIR / f"rank_{ts}.json"
        import json
        snap_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        ok("순위 추적 완료", str(snap_path))
        return {"status": "ok", "path": str(snap_path), "count": len(results)}
    except Exception as e:
        fail("순위 추적 실패", str(e))
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── Step 3b: PageSpeed Insights 측정 ────────────────────────────────

def run_pagespeed() -> dict:
    section("Step 5 — Core Web Vitals 측정")
    try:
        from crawler.page_speed import measure_page, print_results, save_results
        urls = [TARGET_URL]
        results = []
        for url in urls:
            console.print(f"  측정 중: [cyan]{url}[/cyan]")
            r = measure_page(url, "mobile")
            results.append(r)
            r2 = measure_page(url, "desktop")
            results.append(r2)

        print_results(results)
        path = save_results(results)
        ok("PageSpeed 측정 완료", str(path))
        return {"status": "ok", "path": str(path), "count": len(results)}
    except Exception as e:
        fail("PageSpeed 측정 실패", str(e))
        return {"status": "error", "error": str(e)}


# ── Step 3c: 내부 링크 분석 ──────────────────────────────────────────

def run_link_analyzer() -> dict:
    section("Step 6 — 내부 링크 구조 분석")
    try:
        from crawler.link_analyzer import LinkAnalyzer
        analyzer = LinkAnalyzer(max_depth=1, check_broken=False)
        result = analyzer.analyze()
        analyzer.print_report(result)
        path = analyzer.save(result)
        ok("링크 분석 완료", str(path))
        return {"status": "ok", "path": str(path),
                "broken": result.get("broken_links", 0)}
    except Exception as e:
        fail("링크 분석 실패", str(e))
        return {"status": "error", "error": str(e)}


# ── Step 3d: SERP 미리보기 ───────────────────────────────────────────

def run_serp_preview() -> dict:
    section("Step 7 — SERP 스니펫 미리보기")
    try:
        from generator.serp_preview import fetch_serp_data, build_html, print_table
        from config import CATEGORIES, META_DIR

        urls = [TARGET_URL] + [c["url"] for c in CATEGORIES]
        entries = []
        for url in urls:
            entries.append(fetch_serp_data(url))

        print_table(entries)
        html  = build_html(entries)
        ts    = datetime.now().strftime("%Y%m%d_%H%M%S")
        path  = META_DIR / f"serp_preview_{ts}.html"
        path.write_text(html, encoding="utf-8")
        ok("SERP 미리보기 생성 완료", str(path))
        return {"status": "ok", "path": str(path)}
    except Exception as e:
        fail("SERP 미리보기 실패", str(e))
        return {"status": "error", "error": str(e)}


# ── Step 5: HTML 리포트 생성 ─────────────────────────────────────────

def run_report(audit_path: Path = None) -> dict:
    section("Step 8 — HTML 리포트 생성")
    try:
        from report.report_builder import build_audit_report
        path = build_audit_report(audit_path)
        ok("HTML 리포트 생성 완료", str(path))
        return {"status": "ok", "path": str(path)}
    except Exception as e:
        fail("리포트 생성 실패", str(e))
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


# ── 최종 요약 출력 ───────────────────────────────────────────────────

def print_final_summary(results: dict, elapsed: float):
    console.print()
    console.rule("[bold]파이프라인 실행 완료[/bold]")
    console.print()

    table = Table(title=f"{SITE_NAME} SEO 자동화 실행 결과", show_lines=True)
    table.add_column("단계", style="bold")
    table.add_column("상태", justify="center")
    table.add_column("결과물")

    step_labels = {
        "audit":      "1. 사이트 감사",
        "competitor": "2. 경쟁사 분석",
        "pagespeed":  "3. PageSpeed 측정",
        "links":      "4. 링크 구조 분석",
        "serp":       "5. SERP 미리보기",
        "meta":       "6. 메타태그 생성",
        "rank":       "7. 순위 추적",
        "report":     "8. HTML 리포트",
    }

    for key, label in step_labels.items():
        r = results.get(key, {})
        status = r.get("status", "skipped")
        if status == "ok":
            status_str = "[green]✓ 완료[/green]"
        elif status == "skipped":
            status_str = "[dim]— 건너뜀[/dim]"
        else:
            status_str = "[red]✗ 오류[/red]"

        detail = ""
        if status == "ok":
            if key == "audit" and "summary" in r:
                s = r["summary"]
                detail = f"Critical {s.get('total_critical',0)} / Warning {s.get('total_warning',0)}"
            elif key == "competitor":
                detail = f"{r.get('count',0)}개 사이트 분석"
            elif key == "pagespeed":
                detail = f"{r.get('count',0)}건 측정"
            elif key == "links":
                broken = r.get("broken", 0)
                detail = f"깨진 링크 {broken}개" if broken else "깨진 링크 없음"
            elif key == "serp":
                detail = r.get("path", "")
            elif key == "meta":
                detail = f"{r.get('count',0)}개 상품 처리"
            elif key == "rank":
                detail = f"{r.get('count',0)}건 추적"
            elif key == "report":
                detail = r.get("path", "")

        table.add_row(label, status_str, detail)

    console.print(table)
    console.print(f"\n[dim]총 소요 시간: {elapsed:.1f}초[/dim]")

    # 리포트 열기 안내
    report_path = results.get("report", {}).get("path")
    if report_path:
        console.print()
        console.print(Panel(
            f"[bold]HTML 리포트:[/bold] {report_path}\n"
            f"브라우저에서 위 파일을 열어 전체 감사 결과를 확인하세요.",
            title="📊 결과 확인",
            border_style="green"
        ))


# ── 진입점 ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="소아벨라 SEO 자동화 전체 파이프라인")
    parser.add_argument("--skip-rank",       action="store_true", help="순위 추적 건너뜀 (빠른 실행)")
    parser.add_argument("--skip-meta",       action="store_true", help="메타태그 생성 건너뜀")
    parser.add_argument("--skip-competitor", action="store_true", help="경쟁사 분석 건너뜀")
    parser.add_argument("--skip-pagespeed", action="store_true", help="PageSpeed 측정 건너뜀")
    parser.add_argument("--skip-links",      action="store_true", help="링크 분석 건너뜀")
    parser.add_argument("--audit-only",      action="store_true", help="감사 계열 + 리포트만 실행")
    parser.add_argument("--report-only",     action="store_true", help="최신 JSON으로 리포트만 재생성")
    parser.add_argument("--fast",            action="store_true", help="사이트 감사 + SERP 미리보기 + 리포트만")
    args = parser.parse_args()

    start_time = time.time()

    console.print(Panel(
        f"[bold]{SITE_NAME} SEO 자동화 파이프라인[/bold]\n"
        f"대상: [cyan]{TARGET_URL}[/cyan]\n"
        f"시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        border_style="blue"
    ))

    results = {}

    if args.report_only:
        results["report"] = run_report()

    elif args.fast:
        results["audit"]  = run_audit()
        results["serp"]   = run_serp_preview()
        audit_path = Path(results["audit"]["path"]) if results["audit"]["status"] == "ok" else None
        results["report"] = run_report(audit_path)

    elif args.audit_only:
        results["audit"]     = run_audit()
        results["pagespeed"] = run_pagespeed() if not args.skip_pagespeed else {"status": "skipped"}
        results["links"]     = run_link_analyzer() if not args.skip_links else {"status": "skipped"}
        results["serp"]      = run_serp_preview()
        if results["audit"]["status"] == "ok":
            results["report"] = run_report(Path(results["audit"]["path"]))

    else:
        # 전체 파이프라인
        results["audit"] = run_audit()

        if not args.skip_competitor:
            results["competitor"] = run_competitor()

        if not args.skip_pagespeed:
            results["pagespeed"] = run_pagespeed()

        if not args.skip_links:
            results["links"] = run_link_analyzer()

        results["serp"] = run_serp_preview()

        if not args.skip_meta:
            results["meta"] = run_meta_generator()

        if not args.skip_rank:
            results["rank"] = run_rank_tracker()

        audit_path = None
        if results["audit"]["status"] == "ok":
            audit_path = Path(results["audit"]["path"])
        results["report"] = run_report(audit_path)

    elapsed = time.time() - start_time
    print_final_summary(results, elapsed)


if __name__ == "__main__":
    main()
