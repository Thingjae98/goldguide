"""
app.py
SEO 자동화 웹 대시보드 — 3탭 구조
  Tab 1. SEO 감사    : 사이트 감사 실행 + 이슈 리포트
  Tab 2. 콘텐츠 생성 : 키워드 입력 → Claude API 블로그 초안 자동 생성
  Tab 3. 순위 추적   : 키워드 × Google/Naver 순위 히스토리

실행:
    cd auto
    python app.py
    # → http://localhost:5000
"""

import json
import threading
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template_string, request, jsonify, redirect, url_for

import sys
sys.path.insert(0, str(Path(__file__).parent))
from config import (
    AUDIT_DIR, CONTENT_DIR, RANK_DIR, SITE_NAME, TARGET_URL,
    KEYWORDS, ANTHROPIC_API_KEY, ensure_dirs,
)

ensure_dirs()

app = Flask(__name__)

# ── 공통 레이아웃 ──────────────────────────────────────────────────

BASE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} — {{ site_name }} SEO 대시보드</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Apple SD Gothic Neo','Noto Sans KR',sans-serif;
       background:#f7fafc;color:#1a202c;min-height:100vh}
  .topbar{background:linear-gradient(135deg,#1a202c,#2d3748);
          color:#fff;padding:1rem 2rem;display:flex;align-items:center;gap:1.5rem}
  .topbar h1{font-size:1.1rem;font-weight:800;letter-spacing:-.01em}
  .topbar .sub{font-size:.78rem;color:#a0aec0}
  nav{background:#fff;border-bottom:1px solid #e2e8f0;
      display:flex;gap:0;padding:0 2rem}
  nav a{display:block;padding:.85rem 1.25rem;font-size:.88rem;font-weight:600;
        color:#718096;text-decoration:none;border-bottom:3px solid transparent;
        transition:color .15s,border-color .15s}
  nav a.active,nav a:hover{color:#3182ce;border-color:#3182ce}
  .container{max-width:960px;margin:2rem auto;padding:0 1.5rem}
  .card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;
        padding:1.5rem;margin-bottom:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,.05)}
  .card h2{font-size:1rem;font-weight:700;margin-bottom:1rem;color:#2d3748}
  label{display:block;font-size:.83rem;font-weight:600;color:#4a5568;margin-bottom:.35rem}
  input,select,textarea{width:100%;padding:.6rem .85rem;border:1px solid #e2e8f0;
    border-radius:8px;font-size:.9rem;font-family:inherit;outline:none;
    transition:border-color .15s}
  input:focus,select:focus,textarea:focus{border-color:#3182ce}
  .btn{display:inline-block;padding:.65rem 1.5rem;background:#3182ce;color:#fff;
       border:none;border-radius:8px;font-size:.9rem;font-weight:700;cursor:pointer;
       transition:background .15s}
  .btn:hover{background:#2b6cb0}
  .btn-sm{padding:.4rem 1rem;font-size:.8rem}
  .btn-red{background:#e53e3e}.btn-red:hover{background:#c53030}
  .badge{display:inline-block;font-size:.68rem;font-weight:700;padding:.15rem .45rem;
         border-radius:4px;letter-spacing:.04em}
  .badge-red{background:#fff5f5;color:#e53e3e}
  .badge-yellow{background:#fffff0;color:#d69e2e}
  .badge-green{background:#f0fff4;color:#38a169}
  .badge-blue{background:#ebf8ff;color:#3182ce}
  table{width:100%;border-collapse:collapse;font-size:.85rem}
  th{background:#f7fafc;padding:.5rem .75rem;font-size:.75rem;font-weight:700;
     color:#718096;text-align:left;border-bottom:2px solid #e2e8f0}
  td{padding:.5rem .75rem;border-bottom:1px solid #f0f0f0;vertical-align:top}
  tr:last-child td{border-bottom:none}
  .alert{padding:.85rem 1rem;border-radius:8px;font-size:.88rem;margin-bottom:1rem}
  .alert-info{background:#ebf8ff;color:#2b6cb0;border:1px solid #bee3f8}
  .alert-warn{background:#fffff0;color:#975a16;border:1px solid #faf089}
  .alert-error{background:#fff5f5;color:#c53030;border:1px solid #fed7d7}
  .alert-ok{background:#f0fff4;color:#276749;border:1px solid #c6f6d5}
  .spinner{display:none;width:20px;height:20px;border:3px solid #e2e8f0;
           border-top-color:#3182ce;border-radius:50%;animation:spin .7s linear infinite;
           margin-left:.75rem;vertical-align:middle}
  @keyframes spin{to{transform:rotate(360deg)}}
  .result-box{background:#f7fafc;border:1px solid #e2e8f0;border-radius:8px;
              padding:1rem;margin-top:1rem;font-size:.83rem;line-height:1.7;
              white-space:pre-wrap;max-height:400px;overflow-y:auto}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
  @media(max-width:600px){.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="topbar">
  <div>
    <h1>{{ site_name }} SEO 자동화 대시보드</h1>
    <div class="sub">대상: {{ target_url }}</div>
  </div>
</div>
<nav>
  <a href="/audit"   class="{{ 'active' if tab=='audit' }}">🔍 SEO 감사</a>
  <a href="/content" class="{{ 'active' if tab=='content' }}">✍️ 콘텐츠 생성</a>
  <a href="/rank"    class="{{ 'active' if tab=='rank' }}">📈 순위 추적</a>
</nav>
<div class="container">
  {% block body %}{% endblock %}
</div>
</body>
</html>"""

# ── 탭 1: SEO 감사 ──────────────────────────────────────────────

AUDIT_HTML = BASE_HTML.replace("{% block body %}{% endblock %}", """
<div class="card">
  <h2>🔍 SEO 감사 실행</h2>
  <p style="font-size:.85rem;color:#718096;margin-bottom:1rem">
    soavela.com 홈 + 카테고리 페이지를 크롤링해서 title·description·canonical·OG·JSON-LD·이미지alt를 자동 점검합니다.
  </p>
  <form id="auditForm" onsubmit="runAudit(event)">
    <div style="margin-bottom:1rem">
      <label>감사 대상 URL (비워두면 전체 사이트)</label>
      <input type="url" id="auditUrl" placeholder="https://soavela.com/product/list.html?cate_no=25">
    </div>
    <button class="btn" type="submit">감사 시작 <span class="spinner" id="auditSpinner"></span></button>
  </form>
</div>

<div id="auditResult"></div>

{% if reports %}
<div class="card">
  <h2>📋 최근 감사 리포트</h2>
  <table>
    <tr><th>생성일시</th><th>Critical</th><th>Warning</th><th>페이지</th><th></th></tr>
    {% for r in reports %}
    <tr>
      <td>{{ r.ts }}</td>
      <td><span class="badge badge-red">{{ r.critical }}</span></td>
      <td><span class="badge badge-yellow">{{ r.warning }}</span></td>
      <td>{{ r.pages }}</td>
      <td><a href="/report/{{ r.filename }}" target="_blank" class="btn btn-sm">열기</a></td>
    </tr>
    {% endfor %}
  </table>
</div>
{% endif %}

<script>
async function runAudit(e) {
  e.preventDefault();
  const url = document.getElementById('auditUrl').value;
  const spinner = document.getElementById('auditSpinner');
  const result = document.getElementById('auditResult');
  spinner.style.display = 'inline-block';
  result.innerHTML = '<div class="alert alert-info">감사 중입니다... (30초~2분 소요)</div>';
  try {
    const resp = await fetch('/api/audit', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({url: url || null})
    });
    const data = await resp.json();
    if (data.error) {
      result.innerHTML = `<div class="alert alert-error">오류: ${data.error}</div>`;
    } else {
      result.innerHTML = `
        <div class="alert alert-ok">감사 완료! Critical <strong>${data.critical}</strong> / Warning <strong>${data.warning}</strong> / ${data.pages}페이지</div>
        <div class="card">
          <h2>이슈 요약</h2>
          ${data.issues_html}
          <div style="margin-top:1rem">
            <a href="/report/${data.report_file}" target="_blank" class="btn">전체 리포트 열기</a>
          </div>
        </div>`;
    }
  } catch(err) {
    result.innerHTML = `<div class="alert alert-error">${err}</div>`;
  } finally {
    spinner.style.display = 'none';
    setTimeout(() => location.reload(), 3000);
  }
}
</script>
""")

# ── 탭 2: 콘텐츠 생성 ───────────────────────────────────────────

CONTENT_HTML = BASE_HTML.replace("{% block body %}{% endblock %}", """
<div class="card">
  <h2>✍️ SEO 블로그 콘텐츠 자동 생성</h2>
  <p style="font-size:.85rem;color:#718096;margin-bottom:1rem">
    키워드를 입력하면 Claude AI가 SEO 최적화된 블로그 글(title·H1~H3·FAQ·JSON-LD 포함)을 자동 생성합니다.
  </p>
  {% if not has_api_key %}
  <div class="alert alert-warn">⚠ ANTHROPIC_API_KEY가 .env에 설정되지 않았습니다. 콘텐츠 생성을 사용하려면 API 키가 필요합니다.</div>
  {% endif %}
  <form id="contentForm" onsubmit="generateContent(event)">
    <div class="grid2" style="margin-bottom:1rem">
      <div>
        <label>타겟 키워드 *</label>
        <input type="text" id="keyword" placeholder="예: 금반지 선물 추천" required>
      </div>
      <div>
        <label>검색 의도</label>
        <select id="intent">
          <option value="정보형">정보형 (how-to, 가이드)</option>
          <option value="거래형">거래형 (구매 유도)</option>
          <option value="비교형">비교형 (vs, 차이)</option>
          <option value="정보+거래형">정보+거래형 (혼합)</option>
        </select>
      </div>
    </div>
    <div class="grid2" style="margin-bottom:1rem">
      <div>
        <label>URL 슬러그</label>
        <input type="text" id="slug" placeholder="gold-ring-gift-guide">
      </div>
      <div>
        <label>목표 글자수</label>
        <select id="length">
          <option value="700">700자 (간결)</option>
          <option value="900" selected>900자 (표준)</option>
          <option value="1200">1200자 (상세)</option>
        </select>
      </div>
    </div>
    <button class="btn" type="submit" {% if not has_api_key %}disabled{% endif %}>
      콘텐츠 생성 <span class="spinner" id="contentSpinner"></span>
    </button>
  </form>
</div>

<div id="contentResult"></div>

{% if contents %}
<div class="card">
  <h2>📁 최근 생성 콘텐츠</h2>
  <table>
    <tr><th>키워드</th><th>생성일시</th><th>파일</th></tr>
    {% for c in contents %}
    <tr>
      <td><span class="badge badge-blue">{{ c.keyword }}</span></td>
      <td>{{ c.ts }}</td>
      <td>
        <a href="/content-file/{{ c.html_file }}" target="_blank" class="btn btn-sm">HTML</a>
        <a href="/content-file/{{ c.md_file }}"   target="_blank" class="btn btn-sm" style="margin-left:.25rem;background:#718096">MD</a>
      </td>
    </tr>
    {% endfor %}
  </table>
</div>
{% endif %}

<script>
async function generateContent(e) {
  e.preventDefault();
  const spinner = document.getElementById('contentSpinner');
  const result  = document.getElementById('contentResult');
  spinner.style.display = 'inline-block';
  result.innerHTML = '<div class="alert alert-info">Claude AI가 콘텐츠를 생성 중입니다... (10~30초 소요)</div>';
  const body = {
    keyword: document.getElementById('keyword').value,
    intent:  document.getElementById('intent').value,
    slug:    document.getElementById('slug').value || document.getElementById('keyword').value.replace(/\\s+/g, '-'),
    length:  parseInt(document.getElementById('length').value),
  };
  try {
    const resp = await fetch('/api/content', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.error) {
      result.innerHTML = `<div class="alert alert-error">오류: ${data.error}</div>`;
    } else {
      result.innerHTML = `
        <div class="alert alert-ok">생성 완료!</div>
        <div class="card">
          <h2>${data.h1}</h2>
          <p style="font-size:.83rem;color:#718096;margin-bottom:.5rem">
            title: <strong>${data.title}</strong> (${data.title.length}자)
          </p>
          <p style="font-size:.83rem;color:#718096;margin-bottom:1rem">
            description: ${data.description} (${data.description.length}자)
          </p>
          <div class="result-box">${data.preview}</div>
          <div style="margin-top:1rem">
            <a href="/content-file/${data.html_file}" target="_blank" class="btn">HTML 열기</a>
            <a href="/content-file/${data.md_file}"   target="_blank" class="btn" style="margin-left:.5rem;background:#718096">MD 열기</a>
          </div>
        </div>`;
      setTimeout(() => location.reload(), 5000);
    }
  } catch(err) {
    result.innerHTML = `<div class="alert alert-error">${err}</div>`;
  } finally {
    spinner.style.display = 'none';
  }
}
</script>
""")

# ── 탭 3: 순위 추적 ─────────────────────────────────────────────

RANK_HTML = BASE_HTML.replace("{% block body %}{% endblock %}", """
<div class="card">
  <h2>📈 키워드 순위 히스토리</h2>
  <p style="font-size:.85rem;color:#718096;margin-bottom:1rem">
    Google Search Console API 또는 수동 입력으로 순위를 기록합니다.
    <span class="badge badge-yellow">직접 크롤링은 이용약관 위반 가능 — 운영에서는 GSC API 권장</span>
  </p>
  <form id="rankForm" onsubmit="addRank(event)" style="margin-bottom:1.5rem">
    <div class="grid2" style="margin-bottom:1rem">
      <div>
        <label>키워드</label>
        <select id="rankKeyword">
          {% for kw in keywords %}
          <option>{{ kw }}</option>
          {% endfor %}
        </select>
      </div>
      <div>
        <label>검색엔진</label>
        <select id="rankEngine">
          <option value="google">Google</option>
          <option value="naver">Naver</option>
        </select>
      </div>
    </div>
    <div class="grid2" style="margin-bottom:1rem">
      <div>
        <label>현재 순위 (-1 = 30위+)</label>
        <input type="number" id="rankPos" value="-1" min="-1" max="100">
      </div>
      <div>
        <label>측정일 (비워두면 오늘)</label>
        <input type="date" id="rankDate">
      </div>
    </div>
    <button class="btn" type="submit">순위 기록 추가</button>
  </form>

  <div id="rankMsg"></div>
</div>

{% if history %}
<div class="card">
  <h2>순위 추적 결과</h2>
  <table>
    <tr><th>키워드</th><th>엔진</th><th>최근 순위</th><th>최고 순위</th><th>추세</th><th>측정일</th></tr>
    {% for row in history %}
    <tr>
      <td><strong>{{ row.keyword }}</strong></td>
      <td>{{ '🔍 Google' if row.engine == 'google' else '🟢 Naver' }}</td>
      <td>
        {% if row.rank == -1 %}
          <span class="badge badge-red">30위+</span>
        {% elif row.rank <= 3 %}
          <span class="badge badge-green">{{ row.rank }}위</span>
        {% elif row.rank <= 10 %}
          <span class="badge badge-blue">{{ row.rank }}위</span>
        {% else %}
          <span class="badge badge-yellow">{{ row.rank }}위</span>
        {% endif %}
      </td>
      <td>{{ row.best }}위</td>
      <td>{{ row.trend }}</td>
      <td style="color:#718096;font-size:.8rem">{{ row.date }}</td>
    </tr>
    {% endfor %}
  </table>
</div>
{% else %}
<div class="alert alert-info">아직 순위 데이터가 없습니다. 위 폼으로 첫 순위를 기록해보세요.</div>
{% endif %}

<script>
async function addRank(e) {
  e.preventDefault();
  const msg = document.getElementById('rankMsg');
  const body = {
    keyword: document.getElementById('rankKeyword').value,
    engine:  document.getElementById('rankEngine').value,
    rank:    parseInt(document.getElementById('rankPos').value),
    date:    document.getElementById('rankDate').value || new Date().toISOString().slice(0,10),
  };
  try {
    const resp = await fetch('/api/rank', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    const data = await resp.json();
    if (data.ok) {
      msg.innerHTML = '<div class="alert alert-ok">순위가 기록되었습니다.</div>';
      setTimeout(() => location.reload(), 1500);
    } else {
      msg.innerHTML = `<div class="alert alert-error">${data.error}</div>`;
    }
  } catch(err) {
    msg.innerHTML = `<div class="alert alert-error">${err}</div>`;
  }
}
</script>
""")


# ── 라우트 ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return redirect(url_for("audit"))


@app.route("/audit")
def audit():
    reports = _list_reports()
    return render_template_string(
        AUDIT_HTML,
        tab="audit", title="SEO 감사",
        site_name=SITE_NAME, target_url=TARGET_URL,
        reports=reports,
    )


@app.route("/content")
def content():
    contents = _list_contents()
    return render_template_string(
        CONTENT_HTML,
        tab="content", title="콘텐츠 생성",
        site_name=SITE_NAME, target_url=TARGET_URL,
        has_api_key=bool(ANTHROPIC_API_KEY),
        contents=contents,
    )


@app.route("/rank")
def rank():
    history = _rank_summary()
    return render_template_string(
        RANK_HTML,
        tab="rank", title="순위 추적",
        site_name=SITE_NAME, target_url=TARGET_URL,
        keywords=KEYWORDS,
        history=history,
    )


# ── API 엔드포인트 ───────────────────────────────────────────────

@app.route("/api/audit", methods=["POST"])
def api_audit():
    data = request.get_json()
    extra_url = data.get("url")
    try:
        from crawler.site_auditor import SiteAuditor
        from report.report_builder import build_audit_report
        from dataclasses import asdict

        auditor = SiteAuditor()
        if extra_url:
            auditor.results = [auditor.audit_page(extra_url, "other")]
        else:
            auditor.audit_site()

        json_path = auditor.save_json()
        report_path = build_audit_report(json_path)

        critical = sum(
            sum(1 for i in r.issues if i["severity"] == "critical")
            for r in auditor.results
        )
        warning = sum(
            sum(1 for i in r.issues if i["severity"] == "warning")
            for r in auditor.results
        )

        issues_html = _build_issues_html(auditor.results)

        return jsonify({
            "critical": critical,
            "warning": warning,
            "pages": len(auditor.results),
            "report_file": report_path.name,
            "issues_html": issues_html,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/content", methods=["POST"])
def api_content():
    data = request.get_json()
    keyword = data.get("keyword", "")
    intent  = data.get("intent", "정보형")
    slug    = data.get("slug", "post")
    length  = data.get("length", 900)

    try:
        from generator.content_writer import generate_content, save_content

        result = generate_content(keyword, intent, slug, length)
        paths  = save_content(result, keyword, slug)

        meta  = result.get("meta", {})
        cont  = result.get("content", {})
        secs  = cont.get("sections", [])

        preview_lines = [cont.get("intro", "")]
        for s in secs[:2]:
            preview_lines.append(f"\n[{s.get('h2','')}]\n{s.get('body','')[:150]}...")

        return jsonify({
            "title":       meta.get("title", ""),
            "description": meta.get("description", ""),
            "h1":          cont.get("h1", ""),
            "preview":     "\n".join(preview_lines),
            "html_file":   Path(paths["html"]).name,
            "md_file":     Path(paths["md"]).name,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/rank", methods=["POST"])
def api_rank():
    data = request.get_json()
    keyword = data.get("keyword", "")
    engine  = data.get("engine", "google")
    rank    = data.get("rank", -1)
    date    = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    history_file = RANK_DIR / "rank_history.json"
    try:
        history = json.loads(history_file.read_text(encoding="utf-8")) if history_file.exists() else []
        history.append({
            "keyword": keyword, "engine": engine,
            "rank": rank, "checked_at": date,
        })
        history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e), "ok": False}), 500


@app.route("/report/<filename>")
def view_report(filename):
    path = AUDIT_DIR / filename
    if not path.exists():
        return "리포트를 찾을 수 없습니다.", 404
    return path.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html; charset=utf-8"}


@app.route("/content-file/<filename>")
def view_content_file(filename):
    path = CONTENT_DIR / filename
    if not path.exists():
        return "파일을 찾을 수 없습니다.", 404
    content_type = "text/html; charset=utf-8" if filename.endswith(".html") else "text/plain; charset=utf-8"
    return path.read_text(encoding="utf-8"), 200, {"Content-Type": content_type}


# ── 헬퍼 ────────────────────────────────────────────────────────

def _list_reports() -> list[dict]:
    files = sorted(AUDIT_DIR.glob("report_*.html"), key=lambda p: p.stat().st_mtime, reverse=True)[:5]
    result = []
    for f in files:
        ts = f.stem.replace("report_", "")
        try:
            audit_json = AUDIT_DIR / f"audit_{ts}.json"
            if audit_json.exists():
                d = json.loads(audit_json.read_text(encoding="utf-8"))
                s = d.get("summary", {})
                result.append({
                    "ts": ts[:8] + " " + ts[9:15],
                    "critical": s.get("total_critical", "?"),
                    "warning":  s.get("total_warning", "?"),
                    "pages":    s.get("pages", "?"),
                    "filename": f.name,
                })
            else:
                result.append({"ts": ts, "critical": "?", "warning": "?", "pages": "?", "filename": f.name})
        except Exception:
            pass
    return result


def _list_contents() -> list[dict]:
    files = sorted(CONTENT_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:8]
    result = []
    for f in files:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            kw = d.get("meta", {}).get("keyword", f.stem)
            slug = d.get("meta", {}).get("slug", f.stem)
            ts_part = f.stem.split("_")[-2] + "_" + f.stem.split("_")[-1] if "_" in f.stem else f.stem
            result.append({
                "keyword":   kw,
                "ts":        ts_part,
                "html_file": f.stem + ".html",
                "md_file":   f.stem + ".md",
            })
        except Exception:
            pass
    return result


def _rank_summary() -> list[dict]:
    history_file = RANK_DIR / "rank_history.json"
    if not history_file.exists():
        return []
    try:
        history = json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        return []

    groups: dict[tuple, list] = {}
    for item in history:
        key = (item.get("keyword", ""), item.get("engine", "google"))
        groups.setdefault(key, []).append(item)

    rows = []
    for (kw, eng), items in sorted(groups.items()):
        ranks = [i["rank"] for i in items if i.get("rank", -1) != -1]
        last  = items[-1]
        best  = min(ranks) if ranks else -1

        if len(ranks) >= 2:
            trend = "▲ 상승" if ranks[-1] < ranks[0] else ("▼ 하락" if ranks[-1] > ranks[0] else "→ 유지")
        else:
            trend = "—"

        rows.append({
            "keyword": kw,
            "engine":  eng,
            "rank":    last.get("rank", -1),
            "best":    best if best != -1 else "30+",
            "trend":   trend,
            "date":    str(last.get("checked_at", ""))[:10],
        })
    return rows


def _build_issues_html(results) -> str:
    lines = []
    for r in results:
        criticals = [i for i in r.issues if i["severity"] == "critical"]
        if criticals:
            short = r.url.replace(TARGET_URL, "") or "/"
            lines.append(f"<div style='font-size:.83rem;font-weight:700;margin:.5rem 0 .2rem'>{short}</div>")
            for i in criticals:
                lines.append(
                    f"<div style='font-size:.8rem;padding:.2rem .5rem;color:#c53030'>"
                    f"• {i['message']}"
                    + (f" — {i['detail']}" if i.get('detail') else "")
                    + "</div>"
                )
    return "\n".join(lines) if lines else "<div style='color:#38a169'>✓ Critical 이슈 없음</div>"


# ── 진입점 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import webbrowser
    print(f"\n  {SITE_NAME} SEO 대시보드 시작")
    print(f"  → http://localhost:5000\n")
    threading.Timer(1.2, lambda: webbrowser.open("http://localhost:5000")).start()
    app.run(debug=False, port=5000)
