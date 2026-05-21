# soavela.com SEO 개선 설계서

> 플랫폼: Cafe24 | 업종: 24K 순금 주얼리 쇼핑몰 | 분석일: 2025-05-07

---

## 현황 진단 요약

| 항목 | 현재 상태 | 심각도 |
|------|----------|--------|
| `<h1>` 태그 | 없음 (h2로 대체) | 🔴 Critical |
| `meta description` | 없음 | 🔴 Critical |
| `canonical` 태그 | 없음 → `?srsltid=` 파라미터 중복 색인 | 🔴 Critical |
| Open Graph 태그 | 없음 | 🔴 Critical |
| JSON-LD 구조화 데이터 | 없음 | 🔴 Critical |
| 상품 이미지 alt 텍스트 | 40개+ 전부 없음 | 🔴 Critical |
| 시맨틱 HTML | div 기반, 시맨틱 태그 없음 | 🟡 Warning |
| preconnect / preload | 없음 | 🟡 Warning |
| robots.txt | 미확인 | 🟡 Warning |
| sitemap.xml | 미확인 (Cafe24 자동 생성 확인 필요) | 🟡 Warning |

---

## 전체 로드맵

```
Week 1 (즉시 효과)
├── [A] 홈페이지 메타태그: title/description/canonical/OG
├── [B] 카테고리 페이지 메타태그 템플릿
└── [C] robots.txt + sitemap.xml 확인 및 제출

Week 2 (리치 스니펫 준비)
├── [D] 상품 페이지 JSON-LD (Product + BreadcrumbList)
├── [E] 홈페이지 JSON-LD (Organization + WebSite)
└── [F] 이미지 alt 텍스트 일괄 작성

Week 3~4 (트래픽 확장)
├── [G] 롱테일 키워드 콘텐츠 4편
└── [H] Google Search Console + 네이버 서치어드바이저 등록

Month 2+ (지속 성장)
├── [I] 리뷰 콘텐츠 구조화 (AggregateRating)
├── [J] 백링크 전략 (귀금속 커뮤니티, 뷰티 블로그 협업)
└── [K] Core Web Vitals 점수 측정 및 이미지 최적화
```

---

## 예상 효과 타임라인

| 기간 | 예상 효과 |
|------|----------|
| 1~2주 | 구글 Search Console 색인 오류 감소, SNS 공유 카드 정상화 |
| 1개월 | 이미지 검색("금반지", "순금목걸이") 유입 시작 |
| 2~3개월 | 상품 페이지 리치 스니펫(별점·가격) 검색 결과 표시 |
| 3~6개월 | 롱테일 키워드("24K 순금반지 돌잔치 선물") 1페이지 진입 |
| 6개월+ | "금반지", "금목걸이" 메인 키워드 순위 상승 가시화 |

---

## Cafe24 적용 경로 안내

모든 코드는 **Cafe24 관리자 → 디자인 → 내 디자인 → HTML 편집**에서 적용.

| 파일명 | Cafe24 편집 대상 |
|--------|----------------|
| `homepage-meta.html` | `index.html` (홈페이지 스킨) |
| `category-meta.html` | `product/list.html` (카테고리 스킨) |
| `product-jsonld.html` | `product/detail.html` (상품 상세 스킨) |
| `homepage-jsonld.html` | `index.html` `</body>` 직전 |
| `apply-guide.md` | 적용 순서 텍스트 가이드 |
