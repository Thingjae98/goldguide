# soavela SEO 자동화 도구 모음

소아벨라(soavela.com) 사이트를 **외부에서** 분석·개선하는 Python 자동화 스크립트 모음입니다.  
사이트 내부(Cafe24 스킨)를 건드리지 않고 Claude Code에서 단독 실행됩니다.

---

## 폴더 구조

```
auto/
├── run_all.py                  # 전체 파이프라인 실행기
├── config.py                   # 공통 설정 (URL, 키워드, API 키 등)
├── requirements.txt            # 패키지 목록
├── .env.example                # 환경변수 템플릿
├── .env                        # 실제 API 키 (Git 비공개)
│
├── crawler/
│   ├── site_auditor.py         # SEO 감사: title·meta·canonical·OG·JSON-LD·이미지alt
│   ├── competitor_spy.py       # 경쟁사 SEO 신호 비교 분석
│   ├── page_speed.py           # Google PageSpeed Insights API로 CWV 자동 측정
│   ├── link_analyzer.py        # 내부 링크 구조·깨진 링크·앵커 텍스트 분석
│   ├── jsonld_validator.py     # JSON-LD 구조화 데이터 필수 프로퍼티 검증
│   └── keyword_density.py      # 페이지 내 키워드 밀도 분석 (title/h1/h2/description 포함 여부)
│
├── generator/
│   ├── content_writer.py       # Claude API로 SEO 블로그 콘텐츠 자동 생성
│   ├── meta_generator.py       # Claude API로 상품 title·description·alt 일괄 생성
│   ├── serp_preview.py         # 실시간 크롤로 Google·Naver SERP 미리보기 HTML 생성
│   └── sitemap_gen.py          # 사이트 크롤로 sitemap.xml + gzip 자동 생성
│
├── monitor/
│   ├── rank_tracker.py         # Google·네이버 키워드 순위 추적 (누적 히스토리)
│   └── scheduler.py            # 주기적 자동 실행 스케줄 데몬
│
├── report/
│   └── report_builder.py       # 감사 JSON → 시각적 HTML 리포트
│
└── output/                     # 생성된 파일 저장 (Git 비공개)
    ├── audits/                 # audit_TIMESTAMP.json, report_TIMESTAMP.html
    ├── content/                # content_KEYWORD_TIMESTAMP.{json,html,md}
    ├── meta/                   # meta_TIMESTAMP.{json,csv,html}
    └── ranks/                  # rank_TIMESTAMP.json, rank_history.json
```

---

## 빠른 시작

### 1. 환경 설정

```bash
# auto/ 폴더로 이동
cd auto

# 패키지 설치
pip install -r requirements.txt

# .env 파일 생성
copy .env.example .env   # Windows
# cp .env.example .env   # macOS/Linux
```

`.env` 파일을 열고 필수 값 입력:

```ini
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxx   # 필수 (Claude API 사용 시)
TARGET_URL=https://soavela.com              # 기본값 유지
```

### 2. 전체 파이프라인 실행

```bash
# auto/ 폴더 안에서
python run_all.py
```

약 **10~20분** 소요 (순위 추적이 딜레이를 포함하므로).  
완료 후 `output/audits/report_TIMESTAMP.html`을 브라우저로 열어 확인.

---

## 개별 도구 사용법

### Core Web Vitals 측정 (`page_speed.py`)

```bash
python crawler/page_speed.py                            # 홈 + 카테고리 전체
python crawler/page_speed.py --url https://soavela.com/category/ring/
python crawler/page_speed.py --mobile-only
python crawler/page_speed.py --desktop-only
```

- Google PageSpeed Insights API 사용 (무료, API 키 불필요)
- LCP · CLS · FCP · TBT · Speed Index 측정 + 기준값 색상 표시
- 결과: `output/audits/pagespeed_TIMESTAMP.json`

### 내부 링크 분석 (`link_analyzer.py`)

```bash
python crawler/link_analyzer.py
python crawler/link_analyzer.py --depth 2      # 크롤 깊이 (기본 2)
python crawler/link_analyzer.py --no-check     # 깨진 링크 검사 생략
```

- 내부/외부 링크 수, 깨진 링크(404) 탐지
- 앵커 텍스트 키워드 분포 분석
- 결과: `output/audits/links_TIMESTAMP.json`

### SERP 미리보기 (`serp_preview.py`)

```bash
python generator/serp_preview.py
python generator/serp_preview.py --url https://soavela.com/product/list.html?cate_no=25
```

- 실시간 크롤로 현재 title·description 가져와 Google·Naver 검색결과 모양 시뮬레이션
- Claude API 불필요
- 결과: `output/meta/serp_preview_TIMESTAMP.html`

### JSON-LD 검증 (`jsonld_validator.py`)

```bash
python crawler/jsonld_validator.py
python crawler/jsonld_validator.py --url https://soavela.com/product/detail.html?product_no=123
python crawler/jsonld_validator.py --show-raw   # 원본 JSON 출력
```

- `@type`별 필수·권장 프로퍼티 자동 검사 (Product, Organization, FAQPage 등)
- Rich Snippets 미리보기 텍스트 출력
- 결과: `output/audits/jsonld_TIMESTAMP.json`

### 키워드 밀도 분석 (`keyword_density.py`)

```bash
python crawler/keyword_density.py
python crawler/keyword_density.py --url https://soavela.com/product/list.html?cate_no=25
python crawler/keyword_density.py --keyword "순금반지,돌잔치반지"  # 추가 키워드
```

- 순금·금반지 등 16개 골드 키워드 밀도(%) 분석
- title·H1·H2·description 포함 여부 매트릭스
- 이상 밀도(0.5~3%) 색상 표시
- 결과: `output/audits/keyword_density_TIMESTAMP.json`

### 사이트맵 생성 (`sitemap_gen.py`)

```bash
python generator/sitemap_gen.py               # 사이트맵 생성
python generator/sitemap_gen.py --check       # 기존 sitemap.xml 검증
python generator/sitemap_gen.py --ping-google # Google에 핑 전송
```

- 사이트 크롤 후 URL 자동 수집 + 우선순위·변경 주기 자동 설정
- `output/sitemaps/sitemap.xml` + `.xml.gz` 저장
- 생성 후 Cafe24 FTP 루트에 업로드 필요

### 스케줄 데몬 (`scheduler.py`)

```bash
python monitor/scheduler.py             # 데몬 시작 (Ctrl+C로 종료)
python monitor/scheduler.py --once      # 즉시 전체 1회 실행
python monitor/scheduler.py --show      # 등록 스케줄 확인
python monitor/scheduler.py --audit-now # 감사만 즉시
python monitor/scheduler.py --rank-now  # 순위 추적만 즉시
```

- 매주 월요일 09:00 감사, 화·목 10:00 순위 추적, 격주 경쟁사 분석
- 실행 로그: `output/scheduler.log`

### 사이트 감사 (`site_auditor.py`)

```bash
python crawler/site_auditor.py
```

- 홈페이지 + 7개 카테고리 페이지 순회
- title·meta description·canonical·OG 4종·h1 수·이미지 alt·JSON-LD 검사
- 결과: `output/audits/audit_TIMESTAMP.json` + HTML 리포트 자동 생성

### 경쟁사 분석 (`competitor_spy.py`)

```bash
python crawler/competitor_spy.py
python crawler/competitor_spy.py --urls https://goldshop.com https://goldjewelry.co.kr
```

- `.env`의 `COMPETITORS` 또는 `--urls` 인수로 경쟁사 지정
- 소아벨라 대비 title 길이·description·canonical·OG·JSON-LD·alt 커버리지·키워드 밀도 비교
- 결과: `output/audits/competitor_TIMESTAMP.json`

### SEO 블로그 콘텐츠 생성 (`content_writer.py`)

```bash
# 내장 키워드 중 1개
python generator/content_writer.py --keyword "금반지 선물"

# 내장 계획 중 처음 N개 배치
python generator/content_writer.py --batch 3

# 전체 8개 키워드 일괄 (시간 소요)
python generator/content_writer.py --all
```

- Claude API(`claude-sonnet-4-6`)로 2000~2500자 SEO 최적화 한국어 블로그 포스트 생성
- 결과: `output/content/content_KEYWORD_TIMESTAMP.{json,html,md}`
- HTML 파일에는 Article + FAQPage + BreadcrumbList JSON-LD 자동 삽입

### 상품 메타태그 생성 (`meta_generator.py`)

```bash
# 내장 8개 샘플 상품으로 즉시 실행
python generator/meta_generator.py --sample

# CSV 파일에서 상품 목록 읽기 (name, price, category 컬럼)
python generator/meta_generator.py --csv products.csv

# 단일 상품
python generator/meta_generator.py --name "24k 순금 하트 반지 1.875g" --price 574000 --category 반지
```

- title(45~60자) / meta description(130~155자) / alt 3종 / og_title / og_description 생성
- 결과:
  - `output/meta/meta_TIMESTAMP.json` — 전체 데이터
  - `output/meta/meta_TIMESTAMP.csv` — **Cafe24 일괄 업로드용** (UTF-8 BOM)
  - `output/meta/meta_preview_TIMESTAMP.html` — 구글 SERP 시뮬레이션 미리보기

### 키워드 순위 추적 (`rank_tracker.py`)

```bash
# 전체 키워드 추적 (Google + Naver)
python monitor/rank_tracker.py

# 단일 키워드
python monitor/rank_tracker.py --keyword 금반지

# 특정 엔진만
python monitor/rank_tracker.py --engine naver

# 과거 순위 변화 요약
python monitor/rank_tracker.py --history
```

- 순위 히스토리를 `output/ranks/rank_history.json`에 누적 저장
- 전회 측정 대비 ▲상승 / ▼하락 / →유지 표시
- **주의**: 검색엔진 이용약관상 자동 크롤링 제한 가능. 개발·테스트 목적으로만 사용.

### HTML 리포트 생성 (`report_builder.py`)

```bash
# 최신 감사 결과로 리포트 재생성
python report/report_builder.py

# 특정 JSON 파일 지정
python report/report_builder.py --json output/audits/audit_20250508_120000.json
```

---

## 파이프라인 옵션

```bash
# 핵심 단계만 (~3분): 감사 + SERP 미리보기 + 리포트
python run_all.py --fast

# 감사 계열 전체 (PageSpeed + 링크 + SERP 포함), 메타 생성·순위 추적 제외
python run_all.py --audit-only

# 순위 추적 제외
python run_all.py --skip-rank

# PageSpeed 측정 제외
python run_all.py --skip-pagespeed

# 경쟁사 분석 제외
python run_all.py --skip-competitor

# 최신 JSON으로 리포트만 재생성
python run_all.py --report-only
```

---

## 출력 파일 설명

| 파일 | 용도 |
|------|------|
| `output/audits/audit_*.json` | 페이지별 SEO 이슈 원본 데이터 |
| `output/audits/report_*.html` | 브라우저로 열어 보는 감사 리포트 |
| `output/audits/competitor_*.json` | 경쟁사 분석 원본 데이터 |
| `output/audits/pagespeed_*.json` | Core Web Vitals 측정 원본 데이터 |
| `output/audits/links_*.json` | 내부 링크 구조 분석 원본 데이터 |
| `output/audits/jsonld_*.json` | JSON-LD 검증 결과 |
| `output/audits/keyword_density_*.json` | 키워드 밀도 분석 결과 |
| `output/sitemaps/sitemap.xml` | 최신 사이트맵 (Google·Naver 제출용) |
| `output/sitemaps/sitemap_*.xml.gz` | 타임스탬프별 사이트맵 Gzip 압축본 |
| `output/content/content_*.html` | JSON-LD 포함 블로그 포스트 (바로 게시 가능) |
| `output/content/content_*.md` | 마크다운 버전 (노션·블로그 에디터용) |
| `output/meta/meta_*.csv` | Cafe24 상품 메타태그 일괄 업로드용 CSV |
| `output/meta/meta_preview_*.html` | 구글 SERP 스니펫 시뮬레이션 |
| `output/meta/serp_preview_*.html` | 실시간 Google·Naver SERP 미리보기 |
| `output/ranks/rank_history.json` | 키워드별 순위 누적 히스토리 |
| `output/scheduler.log` | 스케줄 데몬 실행 로그 |

---

## 환경변수 전체 목록 (`.env`)

| 변수 | 필수 | 기본값 | 설명 |
|------|------|--------|------|
| `ANTHROPIC_API_KEY` | content/meta 생성 시 필수 | — | Anthropic API 키 |
| `TARGET_URL` | — | `https://soavela.com` | 감사 대상 URL |
| `KEYWORDS` | — | 내장 14개 | 쉼표 구분 추적 키워드 |
| `SEARCH_ENGINES` | — | `google,naver` | 순위 추적 엔진 |
| `COMPETITORS` | — | 빈값 | 쉼표 구분 경쟁사 URL |
| `OUTPUT_DIR` | — | `./output` | 결과 저장 폴더 |

---

## 주의사항

1. **Cafe24 내부 미수정**: 이 도구들은 사이트를 직접 변경하지 않습니다. 생성된 파일(HTML 스니펫, CSV 등)을 직접 Cafe24 관리자에 적용해야 합니다.
2. **검색엔진 크롤링**: `rank_tracker.py`의 SERP 크롤링은 Google·Naver 이용약관에 위반될 수 있습니다. 실제 운영 시 Google Search Console API 또는 네이버 서치어드바이저 API 사용을 권장합니다.
3. **API 비용**: `content_writer.py`, `meta_generator.py`는 Claude API를 호출합니다. 사용량에 따라 비용이 발생합니다.
4. **딜레이**: 순위 추적 시 요청 간 2.5~5초 딜레이가 적용됩니다. 전체 파이프라인 실행 시 키워드 수에 따라 소요 시간이 달라집니다.

---

## 권장 실행 주기

| 도구 | 권장 주기 | 소요 시간 |
|------|----------|----------|
| `site_auditor` | 주 1회 (사이트 변경 후 즉시) | ~1분 |
| `page_speed` | 주 1회 | ~2분 |
| `serp_preview` | 주 1회 | ~30초 |
| `link_analyzer` | 월 1회 | ~3분 |
| `jsonld_validator` | 주 1회 | ~1분 |
| `keyword_density` | 주 1회 | ~1분 |
| `sitemap_gen` | 월 1회 또는 콘텐츠 추가 시 | ~2분 |
| `competitor_spy` | 격주 1회 | ~2분 |
| `content_writer` | 월 2~4회 (블로그 포스트 계획에 따라) | ~3분/편 |
| `meta_generator` | 신상품 등록 시 | ~1분 |
| `rank_tracker` | 주 2~3회 | ~10분 |

> `scheduler.py --once`로 즉시 핵심 도구를 한꺼번에 실행할 수 있습니다.
