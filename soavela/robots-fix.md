# robots.txt 발견된 문제 및 수정안

---

## 발견된 문제

현재 `Sitemap:` 경로가 **bingbot 섹션에만** 존재합니다.

```
User-agent: bingbot   ← 여기만 있음
  Sitemap: https://soavela.com/sitemap.xml
```

**결과:** Googlebot과 Yeti(네이버봇)는 robots.txt에서 sitemap 위치를 찾을 수 없음.
→ 크롤러가 sitemap을 발견하기까지 시간이 더 걸림.

---

## 수정안

Cafe24 robots.txt는 직접 편집 불가능한 경우가 많습니다.
대신 아래 2가지 방법으로 동일한 효과를 냅니다:

### 방법 1 (권장): Search Console에서 직접 제출
→ `apply-guide.md` STEP 7 참고
→ Googlebot이 robots.txt보다 Search Console 제출을 더 신뢰함

### 방법 2: Cafe24 고객센터에 robots.txt 수정 요청
전역 섹션(`User-agent: *`)에 아래 한 줄 추가 요청:
```
Sitemap: https://soavela.com/sitemap.xml
```

---

## sitemap.xml 현황 (정상)

- `sitemap.xml` 접근 가능 ✅
- sitemap index 방식: `sitemap0.xml.gz` + `sitemap1.xml.gz` 두 파일로 분리
- 마지막 수정일: 2025-05-06 ✅ (최신 상태)
- Cafe24 자동 생성이므로 별도 수동 관리 불필요

---

## robots.txt 추가 확인 사항 (모두 정상)

- 상품 페이지 차단 여부: 차단 없음 ✅
- 카테고리 페이지 차단 여부: 차단 없음 ✅
- `?srsltid=` 파라미터 차단: 없음 → canonical로 해결 필요 (homepage-meta.html에 적용됨) ✅
- sort/filter 파라미터 차단: `Disallow: /*?*sort=`, `Disallow: /*?*filter=` ✅ (중복 페이지 방지)
