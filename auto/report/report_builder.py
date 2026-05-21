"""
report_builder.py
site_auditor의 JSON 결과를 읽어서 시각적인 HTML 리포트를 자동 생성한다.
run_all.py에서도 호출됨.

실행:
    python report/report_builder.py                         # 최신 감사 결과로 리포트 생성
    python report/report_builder.py --json output/audits/audit_20250508_120000.json
"""

import sys
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import AUDIT_DIR, OUTPUT_DIR, SITE_NAME, TARGET_URL

console_width = 80


def load_latest_audit() -> tuple[dict, Path]:
    """output/audits/ 에서 가장 최신 audit_*.json 반환."""
    files = sorted(AUDIT_DIR.glob("audit_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise FileNotFoundError(f"{AUDIT_DIR} 에 감사 결과 파일이 없습니다. 먼저 site_auditor.py를 실행하세요.")
    path = files[0]
    return json.loads(path.read_text(encoding="utf-8")), path


def severity_badge(sev: str) -> str:
    colors = {"critical": "#e53e3e", "warning": "#d69e2e", "info": "#3182ce"}
    labels = {"critical": "CRITICAL", "warning": "WARNING", "info": "INFO"}
    c = colors.get(sev, "#718096")
    l = labels.get(sev, sev.upper())
    return (f'<span style="background:{c};color:#fff;font-size:0.68rem;'
            f'font-weight:700;padding:0.15rem 0.45rem;border-radius:4px;'
            f'letter-spacing:0.04em;">{l}</span>')


def category_icon(cat: str) -> str:
    icons = {"meta": "🏷", "heading": "📝", "image": "🖼", "structured_data": "🔗",
             "access": "🚫", "performance": "⚡", "link": "🔗"}
    return icons.get(cat, "⚠")


def build_audit_report(json_path: Path = None) -> Path:
    if json_path is None:
        data, json_path = load_latest_audit()
    else:
        data = json.loads(json_path.read_text(encoding="utf-8"))

    pages      = data.get("pages", [])
    summary    = data.get("summary", {})
    audited_at = data.get("audited_at", "")[:16].replace("T", " ")

    total_critical = summary.get("total_critical", 0)
    total_warning  = summary.get("total_warning", 0)
    total_pages    = summary.get("pages", len(pages))

    # ── 페이지별 카드 HTML ──────────────────────────────────────
    page_cards = ""
    for page in pages:
        url        = page.get("url", "")
        p_type     = page.get("page_type", "")
        status     = page.get("status_code", 0)
        title      = page.get("title", "")
        h1_count   = page.get("h1_count", 0)
        meta_desc  = page.get("meta_description", "")
        canonical  = page.get("canonical", "")
        og_title   = page.get("og_title", "")
        img_total  = page.get("images_total", 0)
        img_miss   = page.get("images_missing_alt", 0)
        ld_types   = page.get("json_ld_types", [])
        issues     = page.get("issues", [])

        criticals = [i for i in issues if i.get("severity") == "critical"]
        warnings  = [i for i in issues if i.get("severity") == "warning"]

        status_color = "#38a169" if status == 200 else "#e53e3e"
        border_color = "#e53e3e" if criticals else ("#d69e2e" if warnings else "#38a169")

        short_url = url.replace(TARGET_URL, "") or "/"

        # 이슈 리스트
        issues_html = ""
        for iss in issues:
            sev  = iss.get("severity", "info")
            cat  = iss.get("category", "")
            msg  = iss.get("message", "")
            det  = iss.get("detail", "")
            issues_html += f"""
        <div style="display:flex;gap:.5rem;align-items:flex-start;padding:.5rem 0;border-bottom:1px solid #f0f0f0;">
          {severity_badge(sev)}
          <div>
            <div style="font-size:.83rem;font-weight:600;">{category_icon(cat)} {msg}</div>
            {"<div style='font-size:.75rem;color:#718096;margin-top:.1rem;'>" + det + "</div>" if det else ""}
          </div>
        </div>"""

        # 메타 요약 표
        def chk(val):
            return '<span style="color:#38a169;font-weight:700;">✓</span>' if val \
                   else '<span style="color:#e53e3e;font-weight:700;">✗</span>'

        meta_rows = [
            ("title",        title[:50] + "..." if len(title) > 50 else title, chk(title)),
            ("description",  meta_desc[:50] + "..." if len(meta_desc) > 50 else meta_desc or "없음", chk(meta_desc)),
            ("canonical",    canonical[:50] if canonical else "없음", chk(canonical)),
            ("og:title",     og_title[:50] if og_title else "없음", chk(og_title)),
            ("h1 수",        str(h1_count), chk(h1_count == 1)),
            ("JSON-LD",      ", ".join(ld_types) if ld_types else "없음", chk(ld_types)),
            ("이미지 alt 누락", f"{img_miss}개 / 전체 {img_total}개", chk(img_miss == 0)),
        ]

        meta_table = ""
        for label, val, ok in meta_rows:
            meta_table += f"""
          <tr>
            <td style="padding:.35rem .6rem;font-size:.78rem;font-weight:600;color:#4a5568;border-bottom:1px solid #f0f0f0;white-space:nowrap;">{label}</td>
            <td style="padding:.35rem .6rem;font-size:.78rem;color:#2d3748;border-bottom:1px solid #f0f0f0;">{val}</td>
            <td style="padding:.35rem .6rem;text-align:center;border-bottom:1px solid #f0f0f0;">{ok}</td>
          </tr>"""

        page_cards += f"""
    <div style="background:#fff;border:1px solid #e2e8f0;border-left:4px solid {border_color};
                border-radius:10px;padding:1.25rem;margin-bottom:1.25rem;
                box-shadow:0 1px 3px rgba(0,0,0,.05);">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.75rem;flex-wrap:wrap;gap:.5rem;">
        <div>
          <span style="font-size:.7rem;background:#f0f0f0;padding:.15rem .5rem;border-radius:4px;color:#718096;margin-right:.5rem;">{p_type}</span>
          <span style="font-size:.88rem;font-weight:700;color:#3182ce;">{short_url}</span>
        </div>
        <div style="display:flex;gap:.5rem;align-items:center;">
          <span style="font-size:.75rem;font-weight:700;color:{status_color};">HTTP {status}</span>
          {"<span style='font-size:.75rem;background:#fff5f5;color:#e53e3e;font-weight:700;padding:.15rem .45rem;border-radius:4px;'>Critical " + str(len(criticals)) + "</span>" if criticals else ""}
          {"<span style='font-size:.75rem;background:#fffff0;color:#d69e2e;font-weight:700;padding:.15rem .45rem;border-radius:4px;'>Warning " + str(len(warnings)) + "</span>" if warnings else ""}
          {"<span style='font-size:.75rem;background:#f0fff4;color:#38a169;font-weight:700;padding:.15rem .45rem;border-radius:4px;'>이슈 없음</span>" if not issues else ""}
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;">
        <div>
          <div style="font-size:.78rem;font-weight:700;color:#718096;margin-bottom:.4rem;">메타태그 현황</div>
          <table style="width:100%;border-collapse:collapse;">{meta_table}</table>
        </div>
        <div>
          <div style="font-size:.78rem;font-weight:700;color:#718096;margin-bottom:.4rem;">발견된 이슈</div>
          {"<div style='font-size:.83rem;color:#38a169;padding:.5rem 0;'>✓ 이슈 없음</div>" if not issues else issues_html}
        </div>
      </div>
    </div>"""

    # ── 전체 HTML ───────────────────────────────────────────────
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{SITE_NAME} SEO 자동 감사 리포트 — {audited_at}</title>
<style>
  body {{ font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
          background:#f7fafc;color:#1a202c;margin:0;padding:0; }}
  .header {{ background:linear-gradient(135deg,#1a202c,#2d3748);
             color:#fff;padding:2.5rem 2rem;text-align:center; }}
  .header h1 {{ font-size:1.6rem;font-weight:800;margin:0 0 .4rem; }}
  .header p  {{ color:#a0aec0;font-size:.9rem;margin:0; }}
  .scorecard {{ display:grid;grid-template-columns:repeat(4,1fr);
                gap:1rem;max-width:860px;margin:1.5rem auto;padding:0 1.5rem; }}
  .sc {{ background:#fff;border:1px solid #e2e8f0;border-radius:10px;
         padding:1.1rem;text-align:center;box-shadow:0 1px 3px rgba(0,0,0,.05); }}
  .sc .num {{ font-size:2rem;font-weight:800;line-height:1;margin-bottom:.3rem; }}
  .sc .lbl {{ font-size:.75rem;color:#718096; }}
  .content {{ max-width:860px;margin:0 auto;padding:0 1.5rem 3rem; }}
  .section-title {{ font-size:1rem;font-weight:800;padding:.6rem 0;
                    border-bottom:2px solid #e2e8f0;margin-bottom:1rem;
                    display:flex;align-items:center;gap:.5rem; }}
  @media(max-width:600px) {{
    .scorecard {{ grid-template-columns:repeat(2,1fr); }}
  }}
</style>
</head>
<body>

<div class="header">
  <div style="font-size:.72rem;background:#e53e3e;display:inline-block;
              padding:.2rem .6rem;border-radius:999px;margin-bottom:.75rem;
              font-weight:700;letter-spacing:.06em;">AUTO SEO AUDIT</div>
  <h1>{SITE_NAME} SEO 자동 감사 리포트</h1>
  <p>감사 일시: {audited_at} &nbsp;|&nbsp; 대상: <a href="{TARGET_URL}" style="color:#90cdf4;">{TARGET_URL}</a></p>
</div>

<div class="scorecard">
  <div class="sc">
    <div class="num" style="color:#e53e3e;">{total_critical}</div>
    <div class="lbl">Critical 오류</div>
  </div>
  <div class="sc">
    <div class="num" style="color:#d69e2e;">{total_warning}</div>
    <div class="lbl">Warning</div>
  </div>
  <div class="sc">
    <div class="num" style="color:#3182ce;">{total_pages}</div>
    <div class="lbl">감사한 페이지</div>
  </div>
  <div class="sc">
    <div class="num" style="color:#38a169;">{max(0, total_pages - sum(1 for p in pages if p.get("issues")))}</div>
    <div class="lbl">이슈 없는 페이지</div>
  </div>
</div>

<div class="content">
  <div class="section-title">📋 페이지별 상세 결과</div>
  {page_cards}

  <div class="section-title">📌 다음 단계</div>
  <div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;
              padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.05);">
    <ol style="padding-left:1.25rem;line-height:2;font-size:.88rem;color:#2d3748;">
      <li>Critical 오류 우선 수정 — Cafe24 스킨 편집기에서 <code>homepage-meta.html</code> 적용</li>
      <li>카테고리별 메타태그 — <code>category-meta.html</code> product/list.html에 삽입</li>
      <li>상품 JSON-LD — <code>product-jsonld.html</code> product/detail.html에 삽입</li>
      <li>이미지 alt 텍스트 — <code>meta_generator.py --sample</code> 실행 후 CSV 업로드</li>
      <li>Google Search Console + 네이버 서치어드바이저 sitemap 제출</li>
    </ol>
    <p style="font-size:.8rem;color:#718096;margin-top:.75rem;">
      📁 적용 파일 위치: <code>soavela/</code> 폴더 내 html 파일들
    </p>
  </div>
</div>

</body>
</html>"""

    ts        = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path  = AUDIT_DIR / f"report_{ts}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main():
    parser = argparse.ArgumentParser(description="SEO 감사 HTML 리포트 생성")
    parser.add_argument("--json", help="감사 JSON 파일 경로 (없으면 최신 파일 사용)")
    args = parser.parse_args()

    json_path = Path(args.json) if args.json else None
    path = build_audit_report(json_path)
    print(f"HTML 리포트 생성 완료: {path}")


if __name__ == "__main__":
    main()
