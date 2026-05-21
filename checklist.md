# SEO 배포 전 최종 점검 체크리스트

> 도메인 확정 후, 호스팅 배포 직전에 이 체크리스트를 순서대로 진행합니다.
> 각 항목 완료 시 [ ] → [x] 로 표시.

---

## 1. 도메인 & HTTPS

- [ ] 실제 도메인 구입 (가비아, 카페24, Namecheap 등)
- [ ] HTTPS(SSL 인증서) 적용 확인 — 브라우저 주소창 자물쇠 아이콘
- [ ] `http://` 접속 시 `https://`로 자동 리다이렉트 확인
- [ ] `www.` 포함/미포함 중 하나로 통일 후 canonical 태그 일치 확인

---

## 2. 메타태그 전수 확인

각 페이지마다 아래 항목 검사:

- [ ] `<title>` — 50~60자, 핵심 키워드 앞쪽, 페이지마다 고유
- [ ] `<meta name="description">` — 150~160자, 페이지마다 고유
- [ ] `<link rel="canonical">` — 실제 도메인 URL로 교체
- [ ] Open Graph 4종 (`og:title`, `og:description`, `og:image`, `og:url`) — 실제 URL로 교체
- [ ] `og:image` — 1200×630px 파일 존재 확인
- [ ] `<meta name="naver-site-verification">` — 실제 인증 코드로 교체

**빠른 확인 도구:**
- [https://metatags.io](https://metatags.io) — OG 미리보기
- [https://cards-dev.twitter.com/validator](https://cards-dev.twitter.com/validator) — Twitter Card 확인

---

## 3. 구조화 데이터 (JSON-LD) 검증

- [ ] [https://validator.schema.org](https://validator.schema.org) — 오류 없음 확인
- [ ] [https://search.google.com/test/rich-results](https://search.google.com/test/rich-results) — 리치 결과 미리보기 확인
- [ ] `Article`: `datePublished`, `dateModified` ISO 8601 형식 확인
- [ ] `FAQPage`: HTML 본문과 JSON-LD 내용 일치 확인
- [ ] `Restaurant`: 영업시간, 주소, 좌표 실제 데이터로 교체

---

## 4. Core Web Vitals

**측정:** [https://pagespeed.web.dev](https://pagespeed.web.dev) 에 실제 URL 입력

| 지표 | 목표 | 현재 측정값 |
|------|------|-----------|
| LCP | ≤ 2.5초 | |
| CLS | ≤ 0.1 | |
| INP | ≤ 200ms | |
| TTFB | ≤ 800ms | |
| Performance 점수 | ≥ 90 | |

**LCP 점수가 낮을 때 점검 항목:**
- [ ] 히어로 이미지 WebP 변환 완료
- [ ] 히어로 이미지에 `fetchpriority="high"` 적용 확인
- [ ] 크리티컬 CSS 인라인 확인
- [ ] 서버 응답 시간(TTFB) 800ms 이내

**CLS 점수가 높을 때 점검 항목:**
- [ ] 모든 `<img>` 태그에 `width` + `height` 속성 명시 확인
- [ ] 구글 폰트 `font-display=swap` 확인
- [ ] 동적으로 삽입되는 광고/배너 공간 미리 확보 (`min-height` 지정)

---

## 5. 크롤링 & 색인

- [ ] `robots.txt` 접근 확인 — `https://내도메인.com/robots.txt`
- [ ] `sitemap.xml` 접근 및 유효성 확인 — `https://내도메인.com/sitemap.xml`
- [ ] [https://www.xml-sitemaps.com/validate-xml-sitemap.html](https://www.xml-sitemaps.com/validate-xml-sitemap.html) — XML 문법 오류 없음
- [ ] `sitemap.xml` 내 모든 URL이 실제 도메인으로 교체됨

---

## 6. 구글 Search Console 등록

1. [https://search.google.com/search-console](https://search.google.com/search-console) 접속
2. 속성 추가 → URL 접두어 방식으로 `https://내도메인.com/` 입력
3. 소유권 인증 (HTML 파일 업로드 또는 메타태그)
4. sitemap.xml 제출: **색인 → Sitemaps → 새 사이트맵 추가**
5. URL 검사 도구로 홈 페이지 색인 요청

- [ ] Search Console 등록 완료
- [ ] sitemap.xml 제출 완료
- [ ] 색인 요청 완료 (홈, 카테고리, 주요 글)

---

## 7. 네이버 서치어드바이저 등록

`naver-setup-guide.md` 참조

- [ ] 서치어드바이저 사이트 등록 완료
- [ ] 소유권 인증 완료 (HTML 파일 또는 메타태그)
- [ ] sitemap.xml 제출 완료
- [ ] 웹 페이지 수집 요청 완료 (주요 URL)

---

## 8. 모바일 최적화

- [ ] Chrome DevTools → Toggle device toolbar → 모바일 뷰 깨짐 없음 확인
- [ ] [https://search.google.com/test/mobile-friendly](https://search.google.com/test/mobile-friendly) — "모바일 친화적" 판정
- [ ] 버튼/링크 터치 영역 최소 44×44px 확인
- [ ] 텍스트 최소 16px (모바일 확대 불필요)

---

## 9. HTML 유효성

- [ ] [https://validator.w3.org](https://validator.w3.org) — 오류 없음 (경고는 허용)
- [ ] `<h1>` 페이지당 1개만 사용 확인
- [ ] `<img>` 모든 태그에 `alt` 속성 있음
- [ ] `<a>` 모든 링크에 명확한 텍스트 (빈 링크 없음)

---

## 10. 최종 배포 후 확인

배포 후 1~3일 내:
- [ ] `site:내도메인.com` 구글 검색 → 색인 페이지 확인
- [ ] Search Console → Coverage 리포트 오류 없음
- [ ] vitals.js 콘솔 출력으로 LCP/CLS/INP 실측값 확인
- [ ] 404 오류 페이지 없음 (Search Console Coverage 탭 확인)

배포 후 2~4주:
- [ ] Search Console → 검색어 통계에 타겟 키워드 진입 확인
- [ ] 네이버 서치어드바이저 → 수집 현황 확인
- [ ] PageSpeed 재측정 — 초기 대비 개선 여부 비교
