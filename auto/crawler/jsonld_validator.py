"""
jsonld_validator.py
소아벨라 페이지의 JSON-LD 구조화 데이터를 추출하고 유효성을 검증한다.
- @type 존재 여부
- 필수 프로퍼티 검사 (Product: name·offers, Organization: name·url 등)
- 중첩 오류 탐지 (JSON 파싱 실패)
- Rich Snippets 미리보기 텍스트 출력

실행:
    python crawler/jsonld_validator.py
    python crawler/jsonld_validator.py --url https://soavela.com/product/detail.html?product_no=123
    python crawler/jsonld_validator.py --show-raw   # 원본 JSON 출력
"""

import sys
import json
import argparse
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import TARGET_URL, CATEGORIES, HEADERS, REQUEST_TIMEOUT, AUDIT_DIR

console = Console()


# ── 스키마별 필수 프로퍼티 정의 ──────────────────────────────────────

REQUIRED_PROPS: dict[str, list[str]] = {
    "Product":          ["name", "offers"],
    "Offer":            ["price", "priceCurrency"],
    "Organization":     ["name", "url"],
    "WebSite":          ["name", "url"],
    "BreadcrumbList":   ["itemListElement"],
    "ListItem":         ["position", "name"],
    "Article":          ["headline", "author", "datePublished"],
    "FAQPage":          ["mainEntity"],
    "Question":         ["name", "acceptedAnswer"],
    "Answer":           ["text"],
    "LocalBusiness":    ["name", "address"],
    "Restaurant":       ["name", "address"],
    "ItemList":         ["itemListElement"],
}

RECOMMENDED_PROPS: dict[str, list[str]] = {
    "Product":      ["image", "description", "brand", "sku"],
    "Organization": ["logo", "contactPoint", "sameAs"],
    "Article":      ["image", "dateModified", "publisher"],
    "WebSite":      ["potentialAction"],
}


@dataclass
class SchemaValidation:
    url: str
    type_: str
    raw_json: dict
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_valid: bool = True
    snippet_preview: str = ""


def validate_schema(obj: dict, url: str, parent_type: str = "") -> SchemaValidation:
    type_ = obj.get("@type", "")
    result = SchemaValidation(url=url, type_=type_, raw_json=obj)

    if not type_:
        result.errors.append("@type 미설정")
        result.is_valid = False
        return result

    # 필수 프로퍼티 검사
    required = REQUIRED_PROPS.get(type_, [])
    for prop in required:
        if prop not in obj:
            result.errors.append(f"필수 프로퍼티 누락: {prop}")
            result.is_valid = False

    # 권장 프로퍼티 검사
    recommended = RECOMMENDED_PROPS.get(type_, [])
    for prop in recommended:
        if prop not in obj:
            result.warnings.append(f"권장 프로퍼티 없음: {prop}")

    # 타입별 스니펫 미리보기
    if type_ == "Product":
        name   = obj.get("name", "—")
        offers = obj.get("offers", {})
        price  = offers.get("price", "—") if isinstance(offers, dict) else "—"
        curr   = offers.get("priceCurrency", "") if isinstance(offers, dict) else ""
        result.snippet_preview = f"📦 {name} | {price}{curr}"

    elif type_ == "Organization":
        result.snippet_preview = (
            f"🏢 {obj.get('name','—')} | {obj.get('url','—')}"
        )

    elif type_ == "BreadcrumbList":
        items = obj.get("itemListElement", [])
        crumbs = " > ".join(
            (i.get("name","?") if isinstance(i, dict) else str(i))
            for i in items
        )
        result.snippet_preview = f"🍞 {crumbs}"

    elif type_ == "FAQPage":
        entities = obj.get("mainEntity", [])
        count = len(entities) if isinstance(entities, list) else 1
        result.snippet_preview = f"❓ FAQ {count}개 항목"

    elif type_ == "WebSite":
        action = obj.get("potentialAction", {})
        has_search = isinstance(action, dict) and action.get("@type") == "SearchAction"
        result.snippet_preview = (
            f"🌐 {obj.get('name','—')} {'| 사이트 내 검색박스 ✓' if has_search else ''}"
        )

    return result


def fetch_and_validate(url: str) -> list[SchemaValidation]:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        console.print(f"[red]fetch 오류 ({url}): {e}[/red]")
        return []

    results = []
    scripts = soup.find_all("script", type="application/ld+json")

    if not scripts:
        dummy = SchemaValidation(url=url, type_="(없음)", raw_json={})
        dummy.errors.append("JSON-LD 스크립트 없음")
        dummy.is_valid = False
        results.append(dummy)
        return results

    for script in scripts:
        try:
            data = json.loads(script.string or "")
        except json.JSONDecodeError as e:
            bad = SchemaValidation(url=url, type_="(파싱 오류)", raw_json={})
            bad.errors.append(f"JSON 파싱 실패: {e}")
            bad.is_valid = False
            results.append(bad)
            continue

        # @graph 지원
        if "@graph" in data:
            for item in data["@graph"]:
                results.append(validate_schema(item, url))
        else:
            results.append(validate_schema(data, url))

    return results


def print_report(all_results: dict[str, list[SchemaValidation]], show_raw: bool = False):
    for url, validations in all_results.items():
        short = url.replace(TARGET_URL, "") or "/"

        table = Table(title=f"JSON-LD — {short}", show_lines=True)
        table.add_column("@type", style="bold")
        table.add_column("상태", justify="center")
        table.add_column("오류")
        table.add_column("경고")
        table.add_column("스니펫 미리보기", max_width=40)

        for v in validations:
            if v.is_valid and not v.warnings:
                status = "[green]✓ 정상[/green]"
            elif v.errors:
                status = "[red]✗ 오류[/red]"
            else:
                status = "[yellow]⚠ 경고[/yellow]"

            err_str  = "\n".join(v.errors)  or "—"
            warn_str = "\n".join(v.warnings) or "—"

            table.add_row(v.type_, status, err_str, warn_str, v.snippet_preview or "—")

        console.print(table)

        if show_raw:
            for v in validations:
                if v.raw_json:
                    console.print(
                        Syntax(
                            json.dumps(v.raw_json, ensure_ascii=False, indent=2),
                            "json", theme="monokai", line_numbers=True
                        )
                    )


def save_report(all_results: dict[str, list[SchemaValidation]]) -> Path:
    output = []
    for url, validations in all_results.items():
        for v in validations:
            output.append({
                "url":        v.url,
                "type":       v.type_,
                "is_valid":   v.is_valid,
                "errors":     v.errors,
                "warnings":   v.warnings,
                "snippet":    v.snippet_preview,
            })

    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = AUDIT_DIR / f"jsonld_{ts}.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    console.print(f"[green]JSON-LD 검증 결과 저장:[/green] {path}")
    return path


def summary_panel(all_results: dict[str, list[SchemaValidation]]):
    total = sum(len(v) for v in all_results.values())
    errors   = sum(1 for vs in all_results.values() for v in vs if v.errors)
    warnings = sum(1 for vs in all_results.values() for v in vs if v.warnings and not v.errors)
    ok_count = total - errors - warnings

    console.print(Panel(
        f"총 스키마: {total}개 | "
        f"[green]✓ 정상 {ok_count}[/green] | "
        f"[yellow]⚠ 경고 {warnings}[/yellow] | "
        f"[red]✗ 오류 {errors}[/red]",
        title="JSON-LD 검증 요약",
        border_style="cyan"
    ))


def main():
    parser = argparse.ArgumentParser(description="소아벨라 JSON-LD 구조화 데이터 검증")
    parser.add_argument("--url",      help="특정 URL 검증")
    parser.add_argument("--show-raw", action="store_true", help="원본 JSON 출력")
    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    else:
        urls = [TARGET_URL] + [c["url"] for c in CATEGORIES]

    console.rule("[bold]JSON-LD 구조화 데이터 검증[/bold]")

    all_results: dict[str, list[SchemaValidation]] = {}
    for i, url in enumerate(urls, 1):
        console.print(f"  [{i}/{len(urls)}] [cyan]{url}[/cyan]")
        all_results[url] = fetch_and_validate(url)

    print_report(all_results, show_raw=args.show_raw)
    summary_panel(all_results)
    save_report(all_results)


if __name__ == "__main__":
    main()
