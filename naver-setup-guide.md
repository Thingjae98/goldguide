# 네이버 서치어드바이저 등록 가이드

> 라이브 URL 기준 절차. 로그인·코드 발급만 직접 하시면 Claude가 코드 삽입·push를 대신합니다.
> **등록할 사이트 URL: `https://thingjae98.github.io/goldguide/`**

---

## 1단계: 서치어드바이저 접속 및 사이트 등록  ← 직접

1. [https://searchadvisor.naver.com](https://searchadvisor.naver.com) 접속
2. 네이버 계정으로 로그인 (보안상 Claude가 대신 못 함)
3. **웹마스터 도구 → 사이트 등록** 클릭
4. 사이트 URL 입력: `https://thingjae98.github.io/goldguide/`

---

## 2단계: 소유권 인증

**방법 B(메타태그) 권장** — Claude가 git으로 바로 처리 가능:

### 방법 B: 메타태그 삽입 (권장)
1. 소유확인 화면에서 "HTML 태그" 선택 → 아래 형태의 코드가 나옴
   ```html
   <meta name="naver-site-verification" content="abc123...실제코드" />
   ```
2. **`content="..."` 안의 코드 문자열만 복사해서 Claude에게 전달**
3. Claude가 9개 HTML의 `REPLACE_WITH_NAVER_VERIFICATION_CODE`를 실제 코드로 교체 → push (자동)
4. GitHub Pages 재배포(~1분) 후 네이버에서 **소유확인** 클릭

### 방법 A: HTML 파일 업로드 (대안)
1. 서치어드바이저에서 `naverXXXX.html` 다운로드
2. 파일을 Claude에게 전달 → repo 루트에 추가·push
3. 네이버에서 **확인** 클릭

---

## 3단계: sitemap.xml 제출  ← 직접

1. 서치어드바이저 → **요청 → 사이트맵 제출**
2. `sitemap.xml` 입력 후 제출 (전체: `https://thingjae98.github.io/goldguide/sitemap.xml`)

---

## 4단계: 수집 요청 (색인 촉진)

1. 서치어드바이저 → **요청 → 웹 페이지 수집**
2. 중요 URL 개별 입력하여 빠른 크롤링 요청
3. 하루 최대 100개 URL 요청 가능

---

## 5단계: 정기 점검 항목

| 항목 | 확인 주기 |
|------|----------|
| 수집 현황 (색인된 페이지 수) | 주 1회 |
| 검색어 통계 (유입 키워드) | 주 1회 |
| 오류 페이지 (404, 500) | 주 1회 |
| 사이트맵 오류 | 월 1회 |

---

## 네이버 검색 알고리즘 대응 체크리스트

- [ ] 페이지당 핵심 키워드 3~5개 자연스럽게 포함
- [ ] 제목(h1)에 타겟 키워드 배치
- [ ] 본문 첫 단락에 키워드 포함
- [ ] 이미지 alt 텍스트에 키워드 포함
- [ ] 최소 600자 이상의 본문 (네이버 D.I.A. 점수 향상)
- [ ] 직접 경험·수치·날짜 포함 (C-Rank 신뢰도 향상)
- [ ] 네이버 블로그/카페 내부 링크 유도 (선택)
- [ ] 모바일 최적화 확인
