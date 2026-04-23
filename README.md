# 운영 요청 DB 트리맵 대시보드

노션 운영 요청 DB를 트리맵 형태로 팀 공용 화면으로 보여주는 정적 대시보드입니다.
GitHub Actions가 10분마다 노션 API를 조회해 `docs/index.html` 을 자동 갱신하고,
GitHub Pages가 그 URL을 공개합니다. 그 URL을 노션 페이지에 `/embed` 로 끼워 넣으면
팀원 누구나 최신 상태를 볼 수 있습니다.

---

## 준비물

- 노션 워크스페이스 관리 권한 (Integration 생성용)
- GitHub 계정 (리포지토리 호스팅용)

---

## 1단계 — 노션 Integration 생성 & 토큰 발급

1. https://www.notion.so/profile/integrations 접속
2. **New integration** 클릭
3. 이름: `Ops Request Dashboard` (원하는 이름), Type: **Internal**, Workspace 선택 후 **Save**
4. 생성된 Integration 페이지에서 **Internal Integration Secret** 복사 (한 번만 보이니 바로 메모)
   - 형식: `ntn_XXXXXXXXXXXXXXXX...`

## 2단계 — Integration에 운영 요청 DB 접근 권한 주기

1. 노션에서 **📥 운영 요청 DB** 페이지 열기
2. 오른쪽 상단 `⋯` → **Connections** → `+ Add connections` → 방금 만든 Integration 선택 → **Confirm**
3. 이걸로 그 Integration은 이 DB만 읽을 수 있게 됩니다. 다른 DB는 접근 불가.

## 3단계 — GitHub 리포지토리 만들기

1. https://github.com/new 로 새 리포 생성
   - 이름: `ops-request-dashboard` (원하는 이름)
   - **Public** (GitHub Pages 무료 플랜은 공개 리포가 필요)
   - README, .gitignore 등은 비워두기
2. 로컬에서 이 폴더(`notion-ops-treemap/`)의 내용을 해당 리포에 업로드
   - 가장 쉬운 방법: 리포 페이지에서 **uploading an existing file** → 이 폴더 안의 파일들을 드래그
   - 업로드 대상 파일: `build.py`, `template.html`, `.github/workflows/refresh.yml`, `docs/index.html`

## 4단계 — GitHub Secret 등록 (노션 토큰 보관)

1. 리포 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Name: `NOTION_TOKEN`
3. Secret: 1단계에서 복사한 Internal Integration Secret 붙여넣기
4. **Add secret** 클릭

이 토큰은 GitHub Actions 실행 중에만 환경변수로 주입되고, 로그나 결과물(`docs/index.html`)에는 절대 노출되지 않습니다.

## 5단계 — GitHub Pages 활성화

1. 리포 → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / `/docs` 선택 → **Save**
4. 잠시 후 상단에 배포 URL이 표시됩니다. 예시:
   `https://<your-user>.github.io/ops-request-dashboard/`
5. 해당 URL을 브라우저로 열어 트리맵이 보이는지 확인

> 배포 후 몇 분 기다려야 첫 URL이 활성화될 수 있어요. 500 에러가 뜨면 1~2분 후 재시도.

## 6단계 — 자동 갱신 확인

1. 리포 → **Actions** 탭 → `Refresh dashboard` 워크플로우
2. **Run workflow** (수동 실행) 버튼을 눌러 최초 1회 실행 → 성공(✓) 확인
3. 이후에는 10분마다 자동으로 돌아가고, 노션 DB에 변화가 있으면 `docs/index.html` 을 갱신 커밋합니다.
4. 변경이 없으면 커밋을 남기지 않습니다 (리포 히스토리가 깨끗하게 유지됨).

## 7단계 — 노션 페이지에 임베드

1. 대시보드를 보여줄 노션 페이지 열기
2. 빈 줄에서 `/embed` 입력 → **Embed** 블록 선택
3. 5단계에서 확인한 GitHub Pages URL 붙여넣기 → **Embed link**
4. 임베드 블록 크기를 적당히 조절 (세로 650px 정도 권장)

완료입니다. 이제 팀원 누구나 해당 노션 페이지만 열면 거의 실시간 트리맵을 볼 수 있습니다.

---

## 동작 방식

```
[GitHub Actions 스케줄] ─10분─▶ build.py 실행
                                    │
                                    ▼
                           Notion API 호출 (NOTION_TOKEN)
                                    │
                                    ▼
                        template.html + 데이터 → docs/index.html
                                    │
                                    ▼
                              자동 git commit & push
                                    │
                                    ▼
                              GitHub Pages 재배포
                                    │
                                    ▼
                          노션 /embed 블록이 최신 페이지 로드
```

## 설정 변경

### 갱신 주기 바꾸기

`.github/workflows/refresh.yml` 의 cron 수정:
- `*/5 * * * *` — 5분마다
- `*/10 * * * *` — 10분마다 (기본)
- `0 * * * *` — 매 정시
- `0 9,13,17 * * *` — 업무시간 3회

> GitHub Actions cron은 부하 상황에 따라 몇 분 지연될 수 있습니다.

### 색 기준 기본값 바꾸기

`template.html` 에서 `let currentMode = "prio";` 를 `"status"` 나 `"p"` 로 변경.

### 타일 사이즈 기준 바꾸기

`build.py` 의 `transform()` 에서 `rice` 대신 다른 숫자 필드를 채우거나,
`template.html` 의 `_v: Math.max(d.rice || 0, 80)` 를 수정.

---

## 트러블슈팅

**Actions 실행이 실패한다**
- `NOTION_TOKEN` Secret 이름이 정확한지 확인 (대소문자 주의)
- 노션 DB에 Integration이 연결되어 있는지 재확인 (2단계)

**페이지는 뜨는데 트리맵이 비어있다**
- DB에 데이터가 실제로 있는지, 그리고 Integration이 그 DB를 볼 수 있는지 확인
- 브라우저 콘솔에 에러가 있는지 확인

**노션 임베드가 "This content can't be embedded"로 뜬다**
- GitHub Pages URL이 정확한지, 퍼블릭 리포인지 확인
- 리포가 Private이면 Pages도 제한되어 임베드가 실패할 수 있음

**토큰을 교체하려면**
- 노션 Integration 페이지에서 Secret 재발급 → GitHub Secret `NOTION_TOKEN` 값을 업데이트
