"""
meta_generator.py
상품명 목록을 입력받아 Claude API로 SEO 최적화된
title / meta description / alt 텍스트를 일괄 생성한다.

실행:
    # 내장된 소아벨라 상품 샘플로 즉시 실행
    python generator/meta_generator.py --sample

    # CSV 파일에서 상품 목록 읽기
    python generator/meta_generator.py --csv products.csv

    # 단일 상품
    python generator/meta_generator.py --name "24k 순금 슈가 하트 반지 1.875g" --price 574000 --category 반지
"""

import sys
import csv
import json
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict

import anthropic
from rich.console import Console
from rich.table import Table
from rich.progress import track

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, META_DIR, SITE_NAME, parse_llm_json, ensure_dirs
ensure_dirs()

console = Console()


# ── 소아벨라 실제 상품 샘플 ────────────────────────────────────────
SAMPLE_PRODUCTS = [
    {"name": "24k 순금 슈가 하트 반지 1.875g", "price": 574000, "original_price": 707000,
     "category": "반지", "subcategory": "24K순금", "weight": "1.875g"},
    {"name": "24k 순금 퓨어 리본 목걸이 3.75g", "price": 1279000, "original_price": 1484000,
     "category": "목걸이", "subcategory": "24K순금", "weight": "3.75g"},
    {"name": "14k 18k 럭스 링크 큐빅 목걸이", "price": 1017000, "original_price": 1129000,
     "category": "목걸이", "subcategory": "14K/18K", "weight": ""},
    {"name": "14k 18k 러프 하트 레이스 반지", "price": 429000, "original_price": 429000,
     "category": "반지", "subcategory": "14K/18K", "weight": ""},
    {"name": "14k 18k 동전 실반지", "price": 261000, "original_price": 261000,
     "category": "반지", "subcategory": "14K/18K", "weight": ""},
    {"name": "24k 순금 커플링 세트 1돈", "price": 748000, "original_price": 860000,
     "category": "커플링", "subcategory": "24K순금", "weight": "3.75g (세트)"},
    {"name": "14k 18k 로쉐 스파클 볼륨 반지", "price": 1139000, "original_price": 1139000,
     "category": "반지", "subcategory": "14K/18K", "weight": ""},
    {"name": "24k 순금 물방울 팔찌 1돈", "price": 748000, "original_price": 860000,
     "category": "팔찌", "subcategory": "24K순금", "weight": "3.75g"},
]


@dataclass
class ProductMeta:
    name: str
    category: str
    price: int
    title: str = ""
    meta_description: str = ""
    alt_main: str = ""         # 대표 이미지 alt
    alt_detail: str = ""       # 상세 이미지 alt
    alt_lifestyle: str = ""    # 착용 이미지 alt
    og_title: str = ""
    og_description: str = ""
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


def build_meta_prompt(products: list[dict]) -> str:
    product_list = json.dumps(products, ensure_ascii=False, indent=2)
    return f"""당신은 24K 순금 주얼리 쇼핑몰 '소아벨라'의 SEO 전문가입니다.
아래 상품 목록에 대해 SEO 최적화된 메타태그와 이미지 alt 텍스트를 생성해 주세요.

## 상품 목록
{product_list}

## 출력 형식 (JSON 배열, 입력 순서와 동일):
[
  {{
    "name": "입력받은 상품명 그대로",
    "title": "title 태그 (45~60자, 키워드+브랜드+차별화, 예: '24K 순금 하트 반지 1.875g | 소아벨라 정품 보증')",
    "meta_description": "meta description (130~155자, 구매 유도+핵심 정보, 예: '소아벨라 24K 순금 하트 반지...')",
    "alt_main": "대표 이미지 alt (상품 특징+용도, 예: '소아벨라 24K 순금반지 하트 디자인 1.875g 돌잔치 선물')",
    "alt_detail": "상세 이미지 alt (재질+디테일, 예: '24K 순금 99.9% 하트 커팅 디테일 클로즈업')",
    "alt_lifestyle": "착용 이미지 alt (착용 상황+스타일링, 예: '순금 하트 반지 손가락 착용 모습 돌잔치 기념')",
    "og_title": "OG title (40~50자, SNS 공유용)",
    "og_description": "OG description (80~100자, 클릭 유도)"
  }}
]

규칙:
- 키워드 나열 금지 (자연스럽게 포함)
- 브랜드명 '소아벨라' 반드시 포함
- 가격은 title/description에 넣지 않음 (변동 가능성)
- alt 텍스트는 한국어로, 125자 이내
- 반드시 JSON 배열만 출력
"""


def generate_meta_batch(products: list[dict]) -> list[ProductMeta]:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 .env에 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 한 번에 최대 10개씩 처리 (프롬프트 길이 관리)
    batch_size = 10
    all_results = []

    for i in range(0, len(products), batch_size):
        batch = products[i:i + batch_size]
        console.print(f"  배치 처리 중 {i+1}~{i+len(batch)} / {len(products)}개...")

        prompt = build_meta_prompt(batch)
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=4096,
            system=[{
                "type": "text",
                "text": f"당신은 {SITE_NAME} SEO 전문가입니다. JSON 배열만 출력하세요.",
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": prompt}],
        )

        items = parse_llm_json(message.content[0].text)
        for item, prod in zip(items, batch):
            pm = ProductMeta(
                name=prod["name"],
                category=prod.get("category", ""),
                price=prod.get("price", 0),
                title=item.get("title", ""),
                meta_description=item.get("meta_description", ""),
                alt_main=item.get("alt_main", ""),
                alt_detail=item.get("alt_detail", ""),
                alt_lifestyle=item.get("alt_lifestyle", ""),
                og_title=item.get("og_title", ""),
                og_description=item.get("og_description", ""),
            )
            all_results.append(pm)

    return all_results


def save_results(results: list[ProductMeta]) -> dict:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON
    json_path = META_DIR / f"meta_{ts}.json"
    json_path.write_text(
        json.dumps([asdict(r) for r in results], ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    # CSV (Cafe24 일괄 등록 형식)
    csv_path = META_DIR / f"meta_{ts}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "상품명", "title", "meta_description",
            "이미지alt_대표", "이미지alt_상세", "이미지alt_착용",
            "og_title", "og_description"
        ])
        writer.writeheader()
        for r in results:
            writer.writerow({
                "상품명":          r.name,
                "title":           r.title,
                "meta_description": r.meta_description,
                "이미지alt_대표":  r.alt_main,
                "이미지alt_상세":  r.alt_detail,
                "이미지alt_착용":  r.alt_lifestyle,
                "og_title":        r.og_title,
                "og_description":  r.og_description,
            })

    # HTML 미리보기 (검색 결과 스니펫 시뮬레이션)
    html_path = META_DIR / f"meta_preview_{ts}.html"
    html = build_preview_html(results)
    html_path.write_text(html, encoding="utf-8")

    return {"json": str(json_path), "csv": str(csv_path), "html": str(html_path)}


def build_preview_html(results: list[ProductMeta]) -> str:
    """구글 검색 결과처럼 생성된 메타태그 미리보기 HTML."""
    items_html = ""
    for r in results:
        title_len = len(r.title)
        desc_len  = len(r.meta_description)
        tlen_color = "green" if 45 <= title_len <= 60 else "orange" if title_len < 45 else "red"
        dlen_color = "green" if 120 <= desc_len <= 160 else "orange" if desc_len < 100 else "red"

        items_html += f"""
<div class="card">
  <div class="product-name">📦 {r.name}</div>
  <div class="serp">
    <div class="serp-url">soavela.com › {r.category.lower()}</div>
    <div class="serp-title">{r.title}</div>
    <div class="serp-desc">{r.meta_description}</div>
  </div>
  <div class="meta-detail">
    <div class="meta-row">
      <span class="label">title</span>
      <span class="value">{r.title}</span>
      <span class="len" style="color:{tlen_color}">{title_len}자</span>
    </div>
    <div class="meta-row">
      <span class="label">description</span>
      <span class="value">{r.meta_description}</span>
      <span class="len" style="color:{dlen_color}">{desc_len}자</span>
    </div>
    <div class="meta-row">
      <span class="label">alt (대표)</span>
      <span class="value">{r.alt_main}</span>
    </div>
    <div class="meta-row">
      <span class="label">alt (상세)</span>
      <span class="value">{r.alt_detail}</span>
    </div>
    <div class="meta-row">
      <span class="label">alt (착용)</span>
      <span class="value">{r.alt_lifestyle}</span>
    </div>
  </div>
</div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>소아벨라 상품 메타태그 미리보기 — {datetime.now().strftime('%Y.%m.%d')}</title>
<style>
  body {{ font-family: 'Apple SD Gothic Neo',sans-serif; background:#f7fafc; color:#1a202c; padding:2rem; }}
  h1   {{ font-size:1.4rem; margin-bottom:0.5rem; }}
  .sub {{ color:#718096; font-size:0.85rem; margin-bottom:2rem; }}
  .card {{ background:#fff; border:1px solid #e2e8f0; border-radius:12px; padding:1.5rem; margin-bottom:1.5rem; box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  .product-name {{ font-size:0.8rem; font-weight:700; color:#718096; margin-bottom:0.75rem; }}
  .serp {{ background:#fff; border:1px solid #e8eaed; border-radius:8px; padding:1rem 1.25rem; margin-bottom:1rem; font-family:Arial,sans-serif; }}
  .serp-url   {{ font-size:0.75rem; color:#3c4043; margin-bottom:0.1rem; }}
  .serp-title {{ font-size:1.05rem; color:#1a0dab; margin-bottom:0.15rem; }}
  .serp-desc  {{ font-size:0.83rem; color:#3c4043; line-height:1.5; }}
  .meta-detail {{ display:flex; flex-direction:column; gap:0.4rem; }}
  .meta-row    {{ display:grid; grid-template-columns:100px 1fr 40px; gap:0.5rem; font-size:0.8rem; align-items:start; padding:0.3rem 0; border-bottom:1px solid #f0f0f0; }}
  .label {{ font-weight:700; color:#4a5568; white-space:nowrap; }}
  .value {{ color:#2d3748; }}
  .len   {{ font-weight:700; text-align:right; white-space:nowrap; }}
</style>
</head>
<body>
<h1>소아벨라 상품 메타태그 자동 생성 결과</h1>
<p class="sub">생성일: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M')} | 총 {len(results)}개 상품</p>
{items_html}
</body>
</html>"""


def main():
    parser = argparse.ArgumentParser(description="소아벨라 상품 메타태그 자동 생성")
    parser.add_argument("--sample", action="store_true", help="내장 샘플 상품으로 실행")
    parser.add_argument("--csv",    help="상품 CSV 파일 경로 (name,price,category 컬럼)")
    parser.add_argument("--name",   help="단일 상품명")
    parser.add_argument("--price",  type=int, default=0)
    parser.add_argument("--category", default="")
    args = parser.parse_args()

    if args.sample:
        products = SAMPLE_PRODUCTS
        console.rule("[bold]소아벨라 샘플 상품 메타태그 생성[/bold]")
    elif args.csv:
        with open(args.csv, encoding="utf-8-sig") as f:
            products = list(csv.DictReader(f))
        console.rule(f"[bold]CSV 상품 메타태그 생성 ({len(products)}개)[/bold]")
    elif args.name:
        products = [{"name": args.name, "price": args.price, "category": args.category}]
        console.rule("[bold]단일 상품 메타태그 생성[/bold]")
    else:
        parser.print_help()
        return

    console.print(f"총 [cyan]{len(products)}[/cyan]개 상품 처리 예정\n")

    results = generate_meta_batch(products)

    # 터미널 미리보기 테이블
    table = Table(title="생성된 메타태그 요약", show_lines=True)
    table.add_column("상품명", max_width=25)
    table.add_column("title", max_width=35)
    table.add_column("길이", justify="center")
    table.add_column("alt (대표)", max_width=30)

    for r in results:
        tlen = len(r.title)
        color = "green" if 45 <= tlen <= 60 else "yellow"
        table.add_row(
            r.name[:22] + "..." if len(r.name) > 22 else r.name,
            r.title[:32] + "..." if len(r.title) > 32 else r.title,
            f"[{color}]{tlen}[/{color}]",
            r.alt_main[:28] + "..." if len(r.alt_main) > 28 else r.alt_main,
        )

    console.print(table)

    paths = save_results(results)
    console.print(f"\n[green]✓ JSON:[/green]    {paths['json']}")
    console.print(f"[green]✓ CSV:[/green]     {paths['csv']}  (Cafe24 일괄 업로드용)")
    console.print(f"[green]✓ HTML 미리보기:[/green] {paths['html']}")


if __name__ == "__main__":
    main()
