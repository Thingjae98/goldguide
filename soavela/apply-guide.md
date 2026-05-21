# Cafe24 SEO 코드 적용 순서 매뉴얼

> 개발자 없이 Cafe24 관리자 패널만으로 적용 가능한 순서입니다.
> 각 단계 완료 후 [ ] → [x] 표시

---

## 사전 준비 (적용 전)

- [ ] OG 이미지 제작: 1200×630px, 대표 상품 + 소아벨라 로고 + "24K 순금 주얼리" 문구
      → 저장 경로: Cafe24 파일관리자 `/web/upload/og-image-soavela.jpg`
- [ ] 네이버 서치어드바이저 가입: https://searchadvisor.naver.com
      → 인증 코드 발급 대기
- [ ] Google Search Console 가입: https://search.google.com/search-console
      → 인증 파일 또는 메타태그 코드 발급

---

## STEP 1 — 홈페이지 메타태그 (homepage-meta.html)

**예상 소요 시간: 10분**

1. Cafe24 관리자 로그인
2. 상단 메뉴 **디자인 → 내 디자인**
3. 현재 사용 중인 스킨 우측 **편집** 클릭
4. 파일 목록에서 `index.html` 클릭
5. `<head>` 태그 안 기존 `<title>` 찾아 전체 교체
6. `homepage-meta.html` 내용 붙여넣기
7. **저장** 후 https://metatags.io 에서 미리보기 확인

**검증:** 브라우저 탭에 새 타이틀 표시 + 카카오톡으로 URL 공유 시 이미지 카드 표시

---

## STEP 2 — 카테고리 메타태그 (category-meta.html)

**예상 소요 시간: 15분**

1. 스킨 편집 → `product/list.html` 열기
2. `<head>` 안에 `category-meta.html` 내용 삽입
3. **body 영역**에 h1 태그 추가 (상품 목록 제목 위에):
   ```html
   <h1 style="font-size:1.5rem; font-weight:700; margin-bottom:1rem;">
     {$category_name}
   </h1>
   ```
4. 저장

**검증:** 반지 카테고리 페이지 소스보기(Ctrl+U) → `<title>반지 추천 | 소아벨라` 확인

---

## STEP 3 — 상품 페이지 메타태그 + JSON-LD (product-jsonld.html)

**예상 소요 시간: 20분**

1. 스킨 편집 → `product/detail.html` 열기
2. `<head>` 안에 product-jsonld.html 주석 처리된 ① 메타태그 부분 삽입
3. `</body>` 직전에 ②③ JSON-LD 스크립트 삽입
4. 저장

**검증:** 임의 상품 URL을 https://search.google.com/test/rich-results 에 입력
→ "상품" 유형이 감지되면 성공

**주의:** `{$review_avg}`가 0이면 `aggregateRating` 블록 전체 제거

---

## STEP 4 — 홈페이지 JSON-LD (homepage-jsonld.html)

**예상 소요 시간: 10분**

1. 스킨 편집 → `index.html` 열기
2. `</body>` 직전에 `homepage-jsonld.html` 전체 내용 삽입
3. TODO 항목 교체:
   - 로고 이미지 URL
   - SNS 계정 URL (Instagram, Facebook, YouTube)
   - 베스트셀러 상품 번호 3개 (Cafe24 관리자 → 상품 번호 확인)
4. 저장

**검증:** https://validator.schema.org 에 홈 URL 입력 → 오류 없음 확인

---

## STEP 5 — 이미지 alt 텍스트 일괄 적용

**예상 소요 시간: 1~2시간 (상품 수에 따라)**

### 방법 A: 스킨 변수 자동화 (5분, 즉시)
1. `product/detail.html` 에서 대표 이미지 태그 찾기
2. alt 없는 img 태그에 `alt="소아벨라 {$product_name}"` 추가
3. 목록 페이지(`product/list.html`)도 동일 적용

### 방법 B: 상품별 개별 입력 (정확도 높음, 시간 소요)
1. Cafe24 관리자 → 상품 관리 → 상품 목록
2. 각 상품 편집 → 이미지 alt 텍스트 입력란 작성
3. `alt-text-guide.md`의 작성 공식 참고

---

## STEP 6 — robots.txt + sitemap.xml 확인

**예상 소요 시간: 10분**

### robots.txt 확인
브라우저에서 https://soavela.com/robots.txt 접속
- Cafe24는 자동으로 생성함
- `Disallow: /` 같은 차단 규칙이 없는지 확인
- sitemap 경로가 명시되어 있는지 확인

### sitemap.xml 확인
브라우저에서 https://soavela.com/sitemap.xml 접속
- Cafe24는 자동으로 상품·카테고리 URL을 포함한 sitemap 생성
- 접근 가능하면 정상

---

## STEP 7 — Google Search Console 등록

1. https://search.google.com/search-console 접속
2. **URL 접두어** 방식으로 `https://soavela.com/` 등록
3. 소유권 인증: HTML 파일 업로드 방식 권장
   - Cafe24 파일관리자 → 인증 파일 루트에 업로드
4. **Sitemaps 메뉴** → `https://soavela.com/sitemap.xml` 제출
5. **URL 검사** → 홈, 주요 카테고리, 베스트셀러 상품 URL 색인 요청

---

## STEP 8 — 네이버 서치어드바이저 등록

1. https://searchadvisor.naver.com 접속
2. 사이트 등록 → `https://soavela.com`
3. 소유권 인증 코드를 `homepage-meta.html`의
   `NAVER_VERIFICATION_CODE_HERE` 자리에 교체 후 저장
4. 사이트맵 제출: `https://soavela.com/sitemap.xml`
5. 수집 요청: 주요 상품 URL 10~20개 수동 등록

---

## 적용 후 모니터링 체크포인트

| 시점 | 확인 항목 |
|------|----------|
| 적용 직후 | rich-results 테스트, metatags.io 카드 확인 |
| 1주일 후 | Search Console Coverage 탭 — 색인 오류 감소 확인 |
| 2주일 후 | Search Console 검색어 탭 — 새 키워드 유입 시작 |
| 1개월 후 | 이미지 검색 "소아벨라 금반지" 결과 확인 |
| 2~3개월 후 | 롱테일 키워드 순위 Google/Naver에서 확인 |

---

## 긴급 점검: 지금 당장 할 수 있는 것 (5분)

브라우저에서 다음을 확인:
```
1. https://soavela.com/robots.txt — 접근 가능한지
2. https://soavela.com/sitemap.xml — 접근 가능한지
3. site:soavela.com 구글 검색 — 현재 색인 페이지 수 확인
```
