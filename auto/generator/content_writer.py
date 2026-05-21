"""
content_writer.py
Claude API를 사용해서 소아벨라용 SEO 블로그 글을 자동 생성한다.

기능:
  - 키워드를 입력하면 SEO 최적화된 블로그 글 초안 생성
  - title, meta description, h1~h3 구조, 본문, FAQ, JSON-LD 포함
  - output/content/ 에 HTML + Markdown 저장

실행:
    python generator/content_writer.py --keyword "돌반지 추천"
    python generator/content_writer.py --all          # keywords.txt 전체 처리
    python generator/content_writer.py --batch 4      # 미리 정의된 4개 글 생성
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

import anthropic
from rich.console import Console
from rich.progress import track
from rich.panel import Panel
from rich.markdown import Markdown

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CONTENT_DIR, SITE_NAME, TARGET_URL, parse_llm_json, ensure_dirs
ensure_dirs()

console = Console()

# ── 미리 정의된 콘텐츠 플랜 ────────────────────────────────────────
CONTENT_PLAN = [
    {
        "keyword": "순금 24K 18K 14K 차이",
        "intent": "정보형",
        "category": "가이드",
        "slug": "24k-18k-14k-difference",
        "target_length": 900,
    },
    {
        "keyword": "돌반지 추천 순금 돌잔치 선물",
        "intent": "정보+거래형",
        "category": "가이드",
        "slug": "dol-ring-guide",
        "target_length": 900,
    },
    {
        "keyword": "금목걸이 선물 여자친구 생일",
        "intent": "거래형",
        "category": "선물가이드",
        "slug": "gold-necklace-gift-guide",
        "target_length": 800,
    },
    {
        "keyword": "커플링 순금 14K 차이 선택",
        "intent": "비교형",
        "category": "가이드",
        "slug": "couple-ring-guide",
        "target_length": 800,
    },
    {
        "keyword": "금 한 돈 몇 그램 가격 계산",
        "intent": "정보형",
        "category": "FAQ",
        "slug": "gold-don-gram-price",
        "target_length": 700,
    },
    {
        "keyword": "금목걸이 레이어드 코디",
        "intent": "정보+상업형",
        "category": "스타일링",
        "slug": "gold-necklace-layered",
        "target_length": 750,
    },
    {
        "keyword": "한국공식금거래소 인증 순금 정품",
        "intent": "정보+신뢰형",
        "category": "브랜드",
        "slug": "korea-gold-certification",
        "target_length": 700,
    },
    {
        "keyword": "종로 금반지 온라인 구매",
        "intent": "거래+로컬형",
        "category": "로컬SEO",
        "slug": "jongno-gold-ring-online",
        "target_length": 700,
    },
]


# ── 프롬프트 빌더 ────────────────────────────────────────────────

def build_prompt(keyword: str, intent: str, slug: str, target_length: int) -> str:
    return f"""당신은 24K 순금 주얼리 전문 쇼핑몰 '소아벨라'의 SEO 콘텐츠 전문가입니다.
아래 조건에 맞는 블로그 글을 JSON 형식으로 작성해 주세요.

## 입력 조건
- 타겟 키워드: {keyword}
- 검색 의도: {intent}
- 목표 글자수: {target_length}자 내외 (본문만, HTML 태그 제외)
- 브랜드: 소아벨라 (https://soavela.com)
- 브랜드 특징: 24K 순금 주얼리 전문, 한국공식금거래소 인증, 정품 보증서 발급, 전국 무료배송

## 출력 JSON 형식 (이 형식 그대로 출력):
{{
  "meta": {{
    "title": "검색 결과 제목 (50~60자, 타겟 키워드 앞쪽 배치)",
    "description": "검색 결과 설명 (130~155자, 클릭 유도 문구 포함)",
    "slug": "{slug}",
    "keyword": "{keyword}",
    "intent": "{intent}"
  }},
  "content": {{
    "h1": "페이지 h1 태그 (핵심 키워드 포함, 40자 내외)",
    "intro": "도입부 (2~3문장, 독자가 읽고 싶게 만드는 훅)",
    "sections": [
      {{
        "h2": "소제목",
        "body": "본문 내용 (200~300자)",
        "h3s": [
          {{"h3": "하위 소제목", "body": "내용"}}
        ]
      }}
    ],
    "conclusion": "결론 (소아벨라 상품 자연스럽게 언급, 2~3문장)",
    "cta": "행동 유도 문구 (짧게, 예: '소아벨라에서 바로 확인하기')"
  }},
  "faq": [
    {{
      "question": "자주 묻는 질문 1",
      "answer": "답변 (2~3문장)"
    }},
    {{
      "question": "자주 묻는 질문 2",
      "answer": "답변 (2~3문장)"
    }},
    {{
      "question": "자주 묻는 질문 3",
      "answer": "답변 (2~3문장)"
    }}
  ],
  "image_alts": [
    "대표 이미지 alt 텍스트 제안 1",
    "본문 이미지 alt 텍스트 제안 2"
  ],
  "internal_links": [
    {{
      "anchor": "링크 텍스트",
      "url": "https://soavela.com/product/list.html?cate_no=25",
      "context": "이 링크를 삽입할 문장 예시"
    }}
  ]
}}

주의사항:
- 키워드를 억지로 나열하지 말고 자연스럽게 배치
- 직접 경험, 구체적 수치, 실용적 정보 포함 (네이버 DIA 점수 향상)
- 광고성 과장 없이 객관적 정보 위주로 작성
- 반드시 JSON만 출력 (주석, 설명 없이)
"""


# ── HTML + JSON-LD 변환 ──────────────────────────────────────────

def to_html(data: dict, keyword: str, slug: str) -> str:
    meta   = data.get("meta", {})
    cont   = data.get("content", {})
    faqs   = data.get("faq", [])
    links  = data.get("internal_links", [])

    # FAQ JSON-LD
    faq_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": f["question"],
                "acceptedAnswer": {"@type": "Answer", "text": f["answer"]}
            }
            for f in faqs
        ]
    }

    # Article JSON-LD
    article_ld = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": cont.get("h1", meta.get("title", "")),
        "description": meta.get("description", ""),
        "author": {"@type": "Organization", "name": "소아벨라"},
        "publisher": {
            "@type": "Organization",
            "name": "소아벨라",
            "logo": {"@type": "ImageObject", "url": f"{TARGET_URL}/web/upload/logo-soavela.png"}
        },
        "datePublished": datetime.now().strftime("%Y-%m-%d"),
        "dateModified": datetime.now().strftime("%Y-%m-%d"),
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{TARGET_URL}/blog/{slug}/"},
        "keywords": keyword,
        "inLanguage": "ko-KR"
    }

    # BreadcrumbList JSON-LD
    bc_ld = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "홈", "item": TARGET_URL},
            {"@type": "ListItem", "position": 2, "name": "블로그", "item": f"{TARGET_URL}/blog/"},
            {"@type": "ListItem", "position": 3, "name": cont.get("h1", ""), "item": f"{TARGET_URL}/blog/{slug}/"}
        ]
    }

    # 섹션 HTML
    sections_html = ""
    for sec in cont.get("sections", []):
        sections_html += f"  <h2>{sec.get('h2','')}</h2>\n"
        sections_html += f"  <p>{sec.get('body','')}</p>\n"
        for h3 in sec.get("h3s", []):
            sections_html += f"  <h3>{h3.get('h3','')}</h3>\n"
            sections_html += f"  <p>{h3.get('body','')}</p>\n"

    # FAQ HTML
    faq_html = ""
    if faqs:
        faq_html = "  <section class='faq-section'>\n  <h2>자주 묻는 질문</h2>\n  <dl>\n"
        for f in faqs:
            faq_html += f"    <dt>{f['question']}</dt>\n"
            faq_html += f"    <dd>{f['answer']}</dd>\n"
        faq_html += "  </dl>\n  </section>\n"

    # 내부 링크 힌트 주석
    links_comment = ""
    if links:
        links_comment = "<!--\n  내부 링크 삽입 제안:\n"
        for lk in links:
            links_comment += f"  [{lk.get('anchor','')}] → {lk.get('url','')}\n"
            links_comment += f"  삽입 위치: {lk.get('context','')}\n\n"
        links_comment += "-->\n"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{meta.get('title','')}</title>
<meta name="description" content="{meta.get('description','')}">
<link rel="canonical" href="{TARGET_URL}/blog/{slug}/">
<meta property="og:type" content="article">
<meta property="og:title" content="{meta.get('title','')}">
<meta property="og:description" content="{meta.get('description','')}">
<meta property="og:url" content="{TARGET_URL}/blog/{slug}/">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="{SITE_NAME}">
<script type="application/ld+json">{json.dumps(article_ld, ensure_ascii=False, indent=2)}</script>
<script type="application/ld+json">{json.dumps(faq_ld, ensure_ascii=False, indent=2)}</script>
<script type="application/ld+json">{json.dumps(bc_ld, ensure_ascii=False, indent=2)}</script>
</head>
<body>
{links_comment}
<article>
  <h1>{cont.get('h1','')}</h1>

  <p class="intro">{cont.get('intro','')}</p>

{sections_html}
  <p class="conclusion">{cont.get('conclusion','')}</p>

  <p class="cta"><a href="{TARGET_URL}">{cont.get('cta','소아벨라에서 확인하기')}</a></p>

{faq_html}
</article>
</body>
</html>
"""


def to_markdown(data: dict) -> str:
    meta  = data.get("meta", {})
    cont  = data.get("content", {})
    faqs  = data.get("faq", [])
    alts  = data.get("image_alts", [])
    links = data.get("internal_links", [])

    md = f"""---
title: {meta.get('title','')}
description: {meta.get('description','')}
keyword: {meta.get('keyword','')}
intent: {meta.get('intent','')}
generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
---

# {cont.get('h1','')}

{cont.get('intro','')}

"""
    for sec in cont.get("sections", []):
        md += f"## {sec.get('h2','')}\n\n{sec.get('body','')}\n\n"
        for h3 in sec.get("h3s", []):
            md += f"### {h3.get('h3','')}\n\n{h3.get('body','')}\n\n"

    md += f"{cont.get('conclusion','')}\n\n"
    md += f"**{cont.get('cta','')}**\n\n"

    if faqs:
        md += "## 자주 묻는 질문\n\n"
        for f in faqs:
            md += f"**Q. {f['question']}**\n\n{f['answer']}\n\n"

    if alts:
        md += "---\n\n## 이미지 alt 텍스트 제안\n\n"
        for i, a in enumerate(alts, 1):
            md += f"{i}. {a}\n"
        md += "\n"

    if links:
        md += "## 내부 링크 삽입 제안\n\n"
        for lk in links:
            md += f"- [{lk.get('anchor','')}]({lk.get('url','')}) — {lk.get('context','')}\n"

    return md


# ── Claude API 호출 ──────────────────────────────────────────────

def generate_content(keyword: str, intent: str = "정보형",
                     slug: str = "post", target_length: int = 800) -> dict:
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY가 .env에 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    system = (
        f"당신은 24K 순금 주얼리 전문 쇼핑몰 '{SITE_NAME}'의 SEO 콘텐츠 전문가입니다. "
        "요청된 JSON 형식을 정확히 따르고, JSON만 출력하세요."
    )
    prompt = build_prompt(keyword, intent, slug, target_length)

    console.print(f"  Claude API 호출 중: [cyan]{keyword}[/cyan]")

    message = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=4096,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": prompt}],
    )

    return parse_llm_json(message.content[0].text)


# ── 파일 저장 ────────────────────────────────────────────────────

def save_content(data: dict, keyword: str, slug: str) -> dict:
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = slug.replace("/", "-")

    json_path = CONTENT_DIR / f"{safe}_{ts}.json"
    html_path = CONTENT_DIR / f"{safe}_{ts}.html"
    md_path   = CONTENT_DIR / f"{safe}_{ts}.md"

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    html_path.write_text(to_html(data, keyword, slug), encoding="utf-8")
    md_path.write_text(to_markdown(data), encoding="utf-8")

    return {"json": str(json_path), "html": str(html_path), "md": str(md_path)}


# ── 진입점 ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Claude API SEO 콘텐츠 자동 생성")
    parser.add_argument("--keyword", help="생성할 키워드")
    parser.add_argument("--intent",  default="정보형", help="검색 의도")
    parser.add_argument("--slug",    default="post", help="URL 슬러그")
    parser.add_argument("--length",  type=int, default=800, help="목표 글자수")
    parser.add_argument("--batch",   type=int, default=0, help="플랜에서 N개 생성")
    parser.add_argument("--all",     action="store_true", help="플랜 전체 생성")
    args = parser.parse_args()

    if args.all or args.batch > 0:
        plan = CONTENT_PLAN if args.all else CONTENT_PLAN[:args.batch]
        console.rule("[bold]배치 콘텐츠 생성 시작[/bold]")
        console.print(f"총 {len(plan)}개 글 생성 예정\n")

        results = []
        for item in track(plan, description="생성 중..."):
            try:
                data  = generate_content(
                    item["keyword"], item["intent"],
                    item["slug"], item["target_length"]
                )
                paths = save_content(data, item["keyword"], item["slug"])
                results.append({"keyword": item["keyword"], "paths": paths, "ok": True})
                console.print(f"  [green]✓[/green] {item['keyword']}")
            except Exception as e:
                console.print(f"  [red]✗ {item['keyword']}: {e}[/red]")
                results.append({"keyword": item["keyword"], "error": str(e), "ok": False})

        ok_count = sum(1 for r in results if r["ok"])
        console.print(f"\n[bold green]완료: {ok_count}/{len(plan)}개[/bold green]")
        console.print(f"저장 위치: {CONTENT_DIR}")

    elif args.keyword:
        data  = generate_content(args.keyword, args.intent, args.slug, args.length)
        paths = save_content(data, args.keyword, args.slug)
        console.print(Panel(
            f"[green]생성 완료![/green]\n"
            f"JSON: {paths['json']}\n"
            f"HTML: {paths['html']}\n"
            f"MD:   {paths['md']}",
            title="콘텐츠 생성 결과"
        ))
        # 미리보기
        md_text = Path(paths["md"]).read_text(encoding="utf-8")
        console.print(Markdown(md_text[:1500] + "\n\n...(이하 생략)"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
