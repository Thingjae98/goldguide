"""
공통 설정 및 상수.
모든 모듈이 이 파일을 import해서 설정을 읽는다.
"""
import json as _json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── 경로 ──────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"

AUDIT_DIR   = OUTPUT_DIR / "audits"
CONTENT_DIR = OUTPUT_DIR / "content"
META_DIR    = OUTPUT_DIR / "meta"
RANK_DIR    = OUTPUT_DIR / "ranks"


def ensure_dirs():
    for d in (AUDIT_DIR, CONTENT_DIR, META_DIR, RANK_DIR):
        d.mkdir(parents=True, exist_ok=True)

# ── API ──────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL      = "claude-sonnet-4-6"

# ── 사이트 ───────────────────────────────────────
TARGET_URL  = os.getenv("TARGET_URL", "https://soavela.com")
SITE_NAME   = "소아벨라"

# soavela.com 카테고리 구조
CATEGORIES = [
    {"name": "24K순금",   "url": f"{TARGET_URL}/product/list.html?cate_no=221", "cate_no": 221},
    {"name": "BEST",      "url": f"{TARGET_URL}/product/list.html?cate_no=24",  "cate_no": 24},
    {"name": "반지",      "url": f"{TARGET_URL}/product/list.html?cate_no=25",  "cate_no": 25},
    {"name": "귀걸이",    "url": f"{TARGET_URL}/product/list.html?cate_no=26",  "cate_no": 26},
    {"name": "목걸이",    "url": f"{TARGET_URL}/product/list.html?cate_no=27",  "cate_no": 27},
    {"name": "팔찌&발찌", "url": f"{TARGET_URL}/product/list.html?cate_no=28",  "cate_no": 28},
    {"name": "커플링",    "url": f"{TARGET_URL}/product/list.html?cate_no=42",  "cate_no": 42},
]

# ── 키워드 ───────────────────────────────────────
raw = os.getenv("KEYWORDS", "금반지,금목걸이,금팔찌,순금반지,순금목걸이,돌반지,커플링,24k순금반지")
KEYWORDS = [k.strip() for k in raw.split(",") if k.strip()]

# ── 경쟁사 ───────────────────────────────────────
raw_comp = os.getenv("COMPETITORS", "")
COMPETITORS = [c.strip() for c in raw_comp.split(",") if c.strip()]

# ── HTTP 요청 공통 헤더 ───────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

REQUEST_TIMEOUT = 15  # seconds
REQUEST_DELAY   = 1.5 # 요청 간 딜레이 (서버 부하 방지)


def parse_llm_json(raw: str):
    """LLM 응답에서 JSON을 추출한다. 코드블록 래퍼를 자동 제거."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1] if len(parts) > 1 else text
        if text.startswith("json"):
            text = text[4:]
    return _json.loads(text.strip().rstrip("```").strip())
