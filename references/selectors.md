# Site Selectors & Wait Strategies

수집 전 이 문서를 확인해, 대상 도메인에 규칙이 있으면 참고/적용한다.
새로 검증한 사이트는 아래 형식으로 추가한다.
(v0.1: 검증된 실제 사이트 없음 → 예시 외 비어 있음)

## 형식

도메인별 블록으로 기록한다:

- **domain**: 적용 호스트 (예: `news.example.com`)
- **content_selector**: 본문 영역 CSS 셀렉터 (없으면 전체 body)
- **wait_for**: goto 후 기다릴 셀렉터/조건 (선택)
- **auto_scroll**: 무한 스크롤/지연 로딩 여부 (true/false → `--auto-scroll`)
- **notes**: 특이사항(로그인 필요, 동적 로딩, 차단 회피 메모 등)

## 예시 (템플릿일 뿐, 실제 적용 규칙 아님)

### example.com
- content_selector: `main`
- wait_for: `h1`
- auto_scroll: false
- notes: 정적 데모 페이지. 형식 예시용.

### n.news.naver.com
- content_selector: `#dic_area` (기사 본문 영역)
- wait_for: `#dic_area`
- auto_scroll: false
- notes: 본문 외 네비게이션·댓글·관련기사 등 노이즈가 많음. `#dic_area` 셀렉터로 본문만 추출 권장. robots.txt 불허(warn 정책으로 진행). 로그인 불필요.

<!-- 첫 실제 사이트 검증 후 여기에 도메인 블록을 추가한다 -->