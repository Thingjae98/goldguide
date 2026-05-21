"""
keyword_cluster.py
금(골드) 관련 키워드를 검색 의도·경쟁도 기준으로 클러스터링하고
'지금 당장 상위 진입이 가능한' 키워드를 선별해서 콘텐츠 로드맵을 출력한다.

Claude API를 사용해 추가 키워드 확장 + 클러스터 설명을 생성한다.
(ANTHROPIC_API_KEY 없으면 내장 데이터만으로 동작)

실행:
    python generator/keyword_cluster.py          # 내장 데이터 분석
    python generator/keyword_cluster.py --expand # Claude API로 키워드 확장
    python generator/keyword_cluster.py --report # HTML 리포트 저장
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, OUTPUT_DIR

console = Console()

KEYWORD_DIR = OUTPUT_DIR / "keywords"
KEYWORD_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────
# 내장 키워드 데이터
# competition: low / medium / high
# intent: informational / commercial / navigational / transactional
# monthly_est: 네이버 기준 월간 추정 검색량 (K=천)
# winnable: 6개월 내 1페이지 진입 가능 여부 판단
# ──────────────────────────────────────────────────────────────────────

KEYWORDS = [
    # ── 클러스터 A: 금 캐럿·순도 정보 (정보성, 경쟁 낮음) ─────────────
    {"kw": "14k 18k 24k 차이",        "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "5K",  "winnable": True},
    {"kw": "금 순도 차이",             "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "금 캐럿 차이",             "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "3K",  "winnable": True},
    {"kw": "순금이란",                  "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "24k 순금 뜻",              "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금반지 14k 18k 차이",      "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "18k 금반지 특징",           "cluster": "A", "intent": "informational", "competition": "low",    "monthly_est": "500", "winnable": True},
    {"kw": "금 도금 차이",             "cluster": "A", "intent": "informational", "competition": "medium", "monthly_est": "2K",  "winnable": True},

    # ── 클러스터 B: 금반지 구매 가이드 (상업적 의도, 경쟁 중간) ────────
    {"kw": "금반지 선물 추천",          "cluster": "B", "intent": "commercial",    "competition": "medium", "monthly_est": "8K",  "winnable": True},
    {"kw": "돌잔치 금반지 추천",        "cluster": "B", "intent": "commercial",    "competition": "medium", "monthly_est": "5K",  "winnable": True},
    {"kw": "커플 금반지 추천",          "cluster": "B", "intent": "commercial",    "competition": "medium", "monthly_est": "3K",  "winnable": True},
    {"kw": "금반지 고르는 법",          "cluster": "B", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "돌반지 순금 무게",          "cluster": "B", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "금반지 무게 추천",          "cluster": "B", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금반지 1돈 무게",           "cluster": "B", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금팔찌 1돈 가격",          "cluster": "B", "intent": "commercial",    "competition": "medium", "monthly_est": "2K",  "winnable": True},
    {"kw": "금목걸이 추천",             "cluster": "B", "intent": "commercial",    "competition": "high",   "monthly_est": "10K", "winnable": False},

    # ── 클러스터 C: 금 시세·가격 (시의성 높음) ──────────────────────────
    {"kw": "오늘 금 시세",             "cluster": "C", "intent": "informational", "competition": "high",   "monthly_est": "50K", "winnable": False},
    {"kw": "금 시세 확인",             "cluster": "C", "intent": "informational", "competition": "high",   "monthly_est": "20K", "winnable": False},
    {"kw": "금반지 1돈 가격 2025",     "cluster": "C", "intent": "commercial",    "competition": "medium", "monthly_est": "5K",  "winnable": True},
    {"kw": "금 1그램 가격",            "cluster": "C", "intent": "informational", "competition": "medium", "monthly_est": "8K",  "winnable": True},
    {"kw": "14k 금반지 가격",          "cluster": "C", "intent": "commercial",    "competition": "medium", "monthly_est": "4K",  "winnable": True},
    {"kw": "18k 금팔찌 가격",          "cluster": "C", "intent": "commercial",    "competition": "medium", "monthly_est": "2K",  "winnable": True},
    {"kw": "금반지 시세 계산",          "cluster": "C", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금 매입 시세",             "cluster": "C", "intent": "commercial",    "competition": "high",   "monthly_est": "15K", "winnable": False},

    # ── 클러스터 D: 종로 지역 SEO ───────────────────────────────────────
    {"kw": "종로 금방 추천",            "cluster": "D", "intent": "commercial",    "competition": "medium", "monthly_est": "3K",  "winnable": True},
    {"kw": "종로 귀금속 상가",          "cluster": "D", "intent": "commercial",    "competition": "medium", "monthly_est": "4K",  "winnable": True},
    {"kw": "종로 금방 가격",            "cluster": "D", "intent": "commercial",    "competition": "medium", "monthly_est": "2K",  "winnable": True},
    {"kw": "종로 금방 거리",            "cluster": "D", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "종로 귀금속 거리 위치",     "cluster": "D", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "종로3가 금반지",            "cluster": "D", "intent": "commercial",    "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "종로 금방 영업시간",        "cluster": "D", "intent": "informational", "competition": "low",    "monthly_est": "500", "winnable": True},
    {"kw": "서울 금방 추천",            "cluster": "D", "intent": "commercial",    "competition": "medium", "monthly_est": "3K",  "winnable": True},

    # ── 클러스터 E: 안양 지역 SEO ───────────────────────────────────────
    {"kw": "안양 금방 추천",            "cluster": "E", "intent": "commercial",    "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "안양 귀금속 상가",          "cluster": "E", "intent": "commercial",    "competition": "low",    "monthly_est": "500", "winnable": True},
    {"kw": "안양 금반지",               "cluster": "E", "intent": "commercial",    "competition": "low",    "monthly_est": "500", "winnable": True},
    {"kw": "경기도 금방 추천",          "cluster": "E", "intent": "commercial",    "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "안양 귀금속 가격",          "cluster": "E", "intent": "commercial",    "competition": "low",    "monthly_est": "300", "winnable": True},

    # ── 클러스터 F: 금 악세서리 케어·관리 ─────────────────────────────
    {"kw": "금반지 관리법",             "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "금목걸이 변색 방지",        "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "2K",  "winnable": True},
    {"kw": "금팔찌 세척법",             "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금반지 크기 조절",          "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "3K",  "winnable": True},
    {"kw": "금 악세서리 보관 방법",     "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},
    {"kw": "금귀걸이 알레르기",         "cluster": "F", "intent": "informational", "competition": "low",    "monthly_est": "1K",  "winnable": True},

    # ── 클러스터 G: 메인 트래픽 키워드 (경쟁 높음, 장기 목표) ──────────
    {"kw": "금반지",                    "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "100K","winnable": False},
    {"kw": "순금반지",                  "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "30K", "winnable": False},
    {"kw": "금목걸이",                  "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "50K", "winnable": False},
    {"kw": "금팔찌",                    "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "30K", "winnable": False},
    {"kw": "금 악세서리",               "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "20K", "winnable": False},
    {"kw": "돌반지",                    "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "40K", "winnable": False},
    {"kw": "종로 금방",                 "cluster": "G", "intent": "commercial",    "competition": "high",   "monthly_est": "20K", "winnable": False},
]

CLUSTER_META = {
    "A": {"name": "금 캐럿·순도 정보",    "color": "green",  "priority": 1, "content_type": "가이드/정보"},
    "B": {"name": "금반지 구매 가이드",    "color": "cyan",   "priority": 2, "content_type": "쇼핑 가이드"},
    "C": {"name": "금 시세·가격 정보",    "color": "yellow", "priority": 3, "content_type": "가격 계산기/가이드"},
    "D": {"name": "종로 지역 SEO",        "color": "blue",   "priority": 2, "content_type": "로컬 SEO 페이지"},
    "E": {"name": "안양 지역 SEO",        "color": "blue",   "priority": 3, "content_type": "로컬 SEO 페이지"},
    "F": {"name": "금 악세서리 케어",     "color": "magenta","priority": 4, "content_type": "정보성 블로그"},
    "G": {"name": "메인 트래픽 (장기)",   "color": "red",    "priority": 5, "content_type": "도메인 권위 누적 후"},
}


def analyze():
    winnable = [k for k in KEYWORDS if k["winnable"]]
    by_cluster: dict[str, list] = {}
    for kw in winnable:
        by_cluster.setdefault(kw["cluster"], []).append(kw)

    # ── 요약 테이블
    console.print()
    console.rule("[bold]금 관련 키워드 클러스터 분석[/bold]")

    summary = Table(title="클러스터별 요약", show_lines=True)
    summary.add_column("클러스터", justify="center", style="bold")
    summary.add_column("주제")
    summary.add_column("승리 가능 키워드", justify="right")
    summary.add_column("예상 월 검색량 합계", justify="right")
    summary.add_column("우선순위", justify="center")
    summary.add_column("콘텐츠 유형")

    for cid in sorted(CLUSTER_META.keys()):
        meta  = CLUSTER_META[cid]
        items = by_cluster.get(cid, [])
        if not items:
            continue
        total_vol = 0
        for k in items:
            v = k["monthly_est"].replace("K","000").replace("500","500")
            try:
                total_vol += int(v)
            except Exception:
                pass
        vol_str = f"{total_vol:,}"
        col = meta["color"]
        summary.add_row(
            f"[{col}]{cid}[/{col}]",
            meta["name"],
            str(len(items)),
            vol_str,
            f"P{meta['priority']}",
            meta["content_type"],
        )

    console.print(summary)

    # ── 승리 가능 키워드 상세
    detail = Table(title="즉시 공략 가능한 키워드 (경쟁 낮음·중간)", show_lines=True)
    detail.add_column("클러스터", justify="center")
    detail.add_column("키워드", style="cyan")
    detail.add_column("의도", justify="center")
    detail.add_column("경쟁도", justify="center")
    detail.add_column("월 검색", justify="right")

    for kw in sorted(winnable, key=lambda x: (x["cluster"], x["competition"])):
        meta = CLUSTER_META[kw["cluster"]]
        col  = meta["color"]
        comp = kw["competition"]
        comp_str = (
            "[green]낮음[/green]" if comp == "low" else
            "[yellow]중간[/yellow]" if comp == "medium" else
            "[red]높음[/red]"
        )
        detail.add_row(
            f"[{col}]{kw['cluster']}: {meta['name'][:8]}[/{col}]",
            kw["kw"],
            kw["intent"][:4],
            comp_str,
            kw["monthly_est"],
        )

    console.print(detail)

    # ── 콘텐츠 로드맵
    console.print()
    console.print(Panel(
        "[bold]즉시 제작할 콘텐츠 로드맵[/bold] (구글 1페이지 목표)\n\n"
        "[green]✅ 이미 있음[/green]\n"
        "  • /blog/14k-18k-24k-difference/ — 클러스터 A (캐럿 차이)\n"
        "  • /jongno/                       — 클러스터 D (종로 지역)\n"
        "  • /anyang/                       — 클러스터 E (안양 지역)\n\n"
        "[cyan]🔨 즉시 제작 필요 (P1~P2)[/cyan]\n"
        "  1. /blog/gold-price-guide/       — 클러스터 C: 금반지 1돈 가격 계산법 2025\n"
        "  2. /blog/gold-ring-buying-guide/ — 클러스터 B: 돌잔치·선물용 금반지 고르는 법\n"
        "  3. /blog/gold-care-guide/        — 클러스터 F: 금 악세서리 관리·세척법\n"
        "  4. /blog/gold-ring-size-guide/   — 클러스터 B: 금반지 무게·사이즈 가이드\n\n"
        "[yellow]📅 추후 제작 (P3~P4)[/yellow]\n"
        "  5. /blog/jongno-gold-guide-2025/ — 클러스터 D: 종로 금방 완전 가이드\n"
        "  6. /blog/gold-necklace-guide/    — 클러스터 B: 금목걸이 구매 가이드",
        border_style="cyan",
        title="📋 콘텐츠 로드맵",
    ))

    return winnable, by_cluster


def expand_with_claude(winnable: list) -> list:
    """Claude API로 키워드 확장."""
    if not ANTHROPIC_API_KEY:
        console.print("[yellow]ANTHROPIC_API_KEY 없음 — 확장 생략[/yellow]")
        return []

    import anthropic
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    sample = [k["kw"] for k in winnable[:20]]
    prompt = f"""다음은 금(골드) 악세서리 관련 한국어 SEO 키워드 목록입니다:
{json.dumps(sample, ensure_ascii=False)}

위 키워드를 참고해서 아직 포함되지 않은 관련 롱테일 키워드 20개를 추가로 생성해주세요.
조건:
- 월 검색량 500~5000 수준 (너무 크지 않은 롱테일)
- 경쟁도가 낮거나 중간
- 구매 의도 또는 정보성
- 반드시 JSON 배열만 반환

예시 출력: ["14k 금반지 알레르기", "금팔찌 선물 포장", ...]"""

    msg = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )
    raw = msg.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip().rstrip("```").strip()

    extras = json.loads(raw)
    console.print(f"\n[green]Claude API 확장 키워드 {len(extras)}개:[/green]")
    for kw in extras:
        console.print(f"  • {kw}")
    return extras


def save_report(winnable: list, extras: list):
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    data = {
        "generated_at":  datetime.now().isoformat(),
        "total_keywords": len(KEYWORDS),
        "winnable_count": len(winnable),
        "clusters":       CLUSTER_META,
        "winnable":       winnable,
        "expanded":       extras,
    }
    path = KEYWORD_DIR / f"keyword_cluster_{ts}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"\n[green]키워드 클러스터 저장:[/green] {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description="금 관련 키워드 클러스터링")
    parser.add_argument("--expand", action="store_true", help="Claude API로 키워드 확장")
    parser.add_argument("--report", action="store_true", help="JSON 리포트 저장")
    args = parser.parse_args()

    winnable, by_cluster = analyze()
    extras = []
    if args.expand:
        extras = expand_with_claude(winnable)
    if args.report or args.expand:
        save_report(winnable, extras)

    # 항상 저장
    save_report(winnable, extras)


if __name__ == "__main__":
    main()
