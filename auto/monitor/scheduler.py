"""
scheduler.py
SEO 자동화 작업을 주기적으로 실행하는 스케줄 데몬.
백그라운드로 실행해 두면 설정된 시간마다 자동으로 감사·순위 추적을 수행한다.

실행:
    python monitor/scheduler.py             # 스케줄 데몬 시작
    python monitor/scheduler.py --once      # 즉시 1회 실행 후 종료
    python monitor/scheduler.py --show      # 등록된 스케줄 확인
"""

import sys
import time
import signal
import argparse
import logging
from datetime import datetime
from pathlib import Path

import schedule
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import OUTPUT_DIR, SITE_NAME

console = Console()

# 로그 파일
LOG_FILE = OUTPUT_DIR / "scheduler.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)

_running = True


def handle_stop(sig, frame):
    global _running
    console.print("\n[yellow]스케줄러 종료 신호 수신 — 현재 작업 완료 후 종료합니다.[/yellow]")
    _running = False


signal.signal(signal.SIGINT, handle_stop)
if hasattr(signal, "SIGTERM"):
    signal.signal(signal.SIGTERM, handle_stop)


# ── 작업 함수들 ──────────────────────────────────────────────────────

def job_audit():
    """사이트 SEO 감사 + HTML 리포트 생성."""
    log.info("=== 사이트 감사 시작 ===")
    try:
        from crawler.site_auditor import SiteAuditor
        from report.report_builder import build_audit_report

        auditor = SiteAuditor()
        auditor.audit_site()
        json_path = auditor.save_json()
        report_path = build_audit_report(json_path)
        log.info(f"감사 완료 → {report_path}")
        console.print(f"[green]✓ 감사 완료[/green] {report_path}")
    except Exception as e:
        log.error(f"감사 실패: {e}")
        console.print(f"[red]✗ 감사 실패: {e}[/red]")


def job_rank():
    """키워드 순위 추적."""
    log.info("=== 순위 추적 시작 ===")
    try:
        import json
        from monitor.rank_tracker import RankTracker
        from config import KEYWORDS, RANK_DIR

        tracker = RankTracker()
        results = tracker.track_keywords(KEYWORDS)
        tracker.save_history(results)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        snap = RANK_DIR / f"rank_{ts}.json"
        snap.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info(f"순위 추적 완료 → {snap}")
        console.print(f"[green]✓ 순위 추적 완료[/green] {snap}")
    except Exception as e:
        log.error(f"순위 추적 실패: {e}")
        console.print(f"[red]✗ 순위 추적 실패: {e}[/red]")


def job_competitor():
    """경쟁사 분석."""
    log.info("=== 경쟁사 분석 시작 ===")
    try:
        from crawler.competitor_spy import CompetitorSpy

        spy = CompetitorSpy()
        results = spy.analyze_all()
        if results:
            spy.save_json()
            log.info("경쟁사 분석 완료")
            console.print("[green]✓ 경쟁사 분석 완료[/green]")
        else:
            log.warning("경쟁사 URL 미설정")
    except Exception as e:
        log.error(f"경쟁사 분석 실패: {e}")
        console.print(f"[red]✗ 경쟁사 분석 실패: {e}[/red]")


# ── 스케줄 등록 ──────────────────────────────────────────────────────

def setup_schedules():
    """
    기본 스케줄:
    - 매주 월요일 09:00 — 사이트 감사 + 리포트
    - 매주 화·목요일 10:00 — 키워드 순위 추적
    - 격주 월요일 10:00 — 경쟁사 분석 (2주 간격 near-enough: 매 14일)
    """
    schedule.every().monday.at("09:00").do(job_audit).tag("audit")
    schedule.every().tuesday.at("10:00").do(job_rank).tag("rank")
    schedule.every().thursday.at("10:00").do(job_rank).tag("rank")
    schedule.every(14).days.do(job_competitor).tag("competitor")


def print_schedule():
    table = Table(title="등록된 SEO 자동화 스케줄", show_lines=True)
    table.add_column("태그", style="cyan")
    table.add_column("다음 실행 예정", style="yellow")
    table.add_column("작업")

    tag_labels = {
        "audit":      "사이트 감사 + 리포트",
        "rank":       "키워드 순위 추적",
        "competitor": "경쟁사 분석",
    }

    seen = set()
    for job in schedule.get_jobs():
        tag = next(iter(job.tags), "unknown")
        if tag in seen:
            continue
        seen.add(tag)
        next_run = str(job.next_run)[:16] if job.next_run else "—"
        table.add_row(tag, next_run, tag_labels.get(tag, tag))

    console.print(table)


# ── 진입점 ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="SEO 자동화 스케줄 데몬")
    parser.add_argument("--once", action="store_true", help="즉시 전체 1회 실행 후 종료")
    parser.add_argument("--show", action="store_true", help="등록된 스케줄 확인")
    parser.add_argument("--audit-now", action="store_true", help="감사 즉시 1회 실행")
    parser.add_argument("--rank-now",  action="store_true", help="순위 추적 즉시 1회 실행")
    args = parser.parse_args()

    setup_schedules()

    if args.show:
        print_schedule()
        return

    if args.audit_now:
        job_audit()
        return

    if args.rank_now:
        job_rank()
        return

    if args.once:
        console.print("[bold]즉시 전체 실행 모드[/bold]")
        job_audit()
        job_rank()
        job_competitor()
        return

    # 데몬 모드
    console.print(Panel(
        f"[bold]{SITE_NAME} SEO 자동화 스케줄 데몬[/bold]\n"
        f"종료: Ctrl+C\n"
        f"로그: {LOG_FILE}",
        border_style="blue"
    ))
    print_schedule()
    console.print("\n[dim]스케줄 대기 중...[/dim]")

    while _running:
        schedule.run_pending()
        time.sleep(30)

    console.print("[yellow]스케줄러가 정상 종료되었습니다.[/yellow]")


if __name__ == "__main__":
    main()
