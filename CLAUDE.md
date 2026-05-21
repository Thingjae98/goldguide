# CLAUDE.md — SEO 프로젝트 행동 지침

## 1. 코딩 전 생각하기
- 가정은 명시적으로 밝힌다. 불확실하면 먼저 질문한다.
- 해석이 여러 가지면 조용히 선택하지 않고 제시한다.
- 더 단순한 방법이 있으면 말한다. 필요하면 반론한다.
- 혼란스러운 부분이 있으면 멈추고 이름을 붙인 후 질문한다.

## 2. 단순함 우선
- 요청한 것만 구현한다. 추측성 기능 추가 금지.
- 단일 용도 코드에 추상화 금지.
- "유연성"·"확장성"은 요청이 있을 때만.
- 불가능한 시나리오에 대한 오류 처리 금지.
- 200줄로 짤 수 있는 걸 50줄로 짤 수 있다면 다시 쓴다.

## 3. 외과적 수정
- 요청한 부분만 수정한다. 인접 코드·주석·포매팅 "개선" 금지.
- 기존 스타일이 마음에 안 들어도 맞춘다.
- 내 수정으로 생긴 사용하지 않는 코드(import 등)는 제거한다.
- 기존 데드코드는 언급만 하고 삭제하지 않는다.

## 4. 목표 기반 실행
- 다단계 작업은 계획을 먼저 제시하고 각 단계마다 검증 기준을 명시한다.
- 성공 기준이 불명확하면 구현 전에 확인한다.
- 멀티스텝 작업은 간단한 계획을 먼저 제시한다:
  ```
  1. [단계] → 검증: [체크]
  2. [단계] → 검증: [체크]
  ```

---

## 5. 프로젝트 개요

- **목적**: 구글/네이버 검색 상단 노출 — 금반지·금 악세서리 정보 사이트 (지역 SEO 포함)
- **사이트명**: 금방가이드
- **타겟 도메인**: goldguide.kr (미확정, 현재 플레이스홀더)
- **작업 디렉터리**: `C:\Users\mj985\Desktop\2025프로젝트\seo`

### 타겟 키워드
| 유형 | 키워드 |
|------|--------|
| 메인 | 금반지, 금 악세서리, 금목걸이, 금팔찌 |
| 지역 | 종로 금방, 종로 귀금속, 안양 금방, 안양 귀금속 |
| 롱테일 | 14k 금반지 가격, 종로 금방 추천, 안양 금반지, 금 캐럿 차이 |

### 디렉터리 구조
```
seo/
├── index.html              # 홈 — 금반지·금 악세서리 허브
├── jongno/index.html       # 종로 금방 지역 SEO 페이지
├── anyang/index.html       # 안양 금방 지역 SEO 페이지
├── blog/
│   └── 14k-18k-24k-difference/index.html  # 금반지 캐럿 비교 가이드
├── css/style.css           # 브랜드 컬러 #B8860B (골드)
├── sitemap.xml
└── robots.txt
```

## 6. 기술 스택

| 영역 | 선택 | 이유 |
|------|------|------|
| 마크업 | HTML5 시맨틱 태그 | 검색엔진 크롤러 이해도 향상 |
| 스타일 | CSS3 (순수 CSS 우선) | 불필요한 JS 로드 제거, LCP 향상 |
| 스크립트 | Vanilla JS (최소화) | 번들 오버헤드 없음 |
| 빌드 | 없음 (정적 파일) | 단순성 최우선 |
| 메타 관리 | 수동 meta 태그 | Open Graph, Twitter Card, JSON-LD |
| 성능 측정 | Google PageSpeed Insights, Search Console | 실측 지표 기준 |

## 7. 진행 단계 (Phase)

- [x] Phase 0 — 디렉터리 초기화, CLAUDE.md 작성
- [x] Phase 1 — HTML 시맨틱 골격 + 핵심 메타 태그 (금 악세서리 사이트로 전환)
- [x] Phase 2 — Core Web Vitals 최적화 (LCP, CLS, INP) — js/vitals.js 구현
- [x] Phase 3 — 구조화 데이터 (JSON-LD) — WebSite, Article, LocalBusiness(JewelryStore), FAQPage, BreadcrumbList
- [x] Phase 4 — sitemap.xml + robots.txt (goldguide.kr 도메인 기준)
- [x] Phase 4.5 — 지역 SEO 페이지 (종로/안양 — LocalBusiness + 지역 특화 콘텐츠)
- [x] Phase 4.6 — /blog 스킬 설치 (~/.claude/commands/blog.md → /blog 명령)
- [x] Phase 4.7 — 키워드 클러스터링 (auto/generator/keyword_cluster.py — 7클러스터, 50+ 키워드)
- [x] Phase 4.8 — 블로그 콘텐츠 5편 제작 (gold-price-guide, gold-ring-buying-guide, gold-care-guide, gold-ring-size-guide, 14k-18k-24k-difference)
- [x] Phase 6 — GitHub Pages 배포 (https://thingjae98.github.io/goldguide/) + Google Search Console 소유권 인증 완료 + sitemap 제출
- [ ] Phase 5 — 네이버 SEO 특화 (네이버 웹마스터 도구 인증 코드 교체)
- [ ] Phase 7 — 성능 측정 (PageSpeed Insights 90점 이상 목표)

## 8. 배포 정보

- **라이브 URL**: https://thingjae98.github.io/goldguide/
- **GitHub 레포**: https://github.com/Thingjae98/goldguide
- **Google Search Console**: 소유권 인증 완료 (2026-05-22), sitemap 제출 완료
- **Google 인증 방법**: HTML 파일(google35623d6185d4d545.html) + HTML 메타태그 이중 인증

## 9. 결정 보류 / TODO

- [ ] 실제 도메인 연결 결정 (goldguide.kr 구입 후 Custom domain 설정)
- [ ] 네이버 서치어드바이저 인증 코드 교체 (REPLACE_WITH_NAVER_VERIFICATION_CODE)
- [ ] 실제 이미지 준비 (hero.webp, jongno-thumb.webp, anyang-thumb.webp 등)
- [ ] 블로그 글 추가: 커플링 추천, 금팔찌 가이드 등 Cluster B·C 보강
- [ ] Google 색인 상태 확인 (Search Console → 색인생성 → 페이지)
