# Google Calendar API 초기 설정 가이드

이 문서는 Google Calendar API를 사용하기 위한 초기 설정 방법을 설명합니다.

## 1. Google Cloud Console 설정

### 1.1 프로젝트 생성

1. [Google Cloud Console](https://console.cloud.google.com/)에 접속
2. 새 프로젝트 생성 또는 기존 프로젝트 선택
3. 프로젝트 이름 입력 (예: "My Calendar App")

### 1.2 Google Calendar API 활성화

1. 좌측 메뉴에서 **API 및 서비스 > 라이브러리** 선택
2. "Google Calendar API" 검색
3. **Google Calendar API** 선택 후 **사용 설정** 클릭

### 1.3 OAuth 2.0 자격 증명 생성

1. 좌측 메뉴에서 **API 및 서비스 > 사용자 인증 정보** 선택
2. 상단의 **+ 사용자 인증 정보 만들기** 클릭
3. **OAuth 클라이언트 ID** 선택
4. 애플리케이션 유형: **데스크톱 앱** 선택
5. 이름 입력 (예: "Calendar Desktop Client")
6. **만들기** 클릭

### 1.4 credentials.json 다운로드

1. 생성된 OAuth 2.0 클라이언트 ID 옆의 **다운로드** 아이콘 클릭
2. JSON 파일을 `credentials.json`으로 저장
3. 이 파일을 스크립트와 같은 디렉토리에 배치

## 2. Python 환경 설정

### 2.1 필수 라이브러리 설치

```bash
pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

또는 requirements.txt 사용:

```bash
pip install -r requirements.txt
```

**requirements.txt 내용:**
```
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=0.5.0
pytz>=2023.0
```

### 2.2 디렉토리 구조

```
your-project/
├── credentials.json          # Google Cloud Console에서 다운로드
├── token.pickle              # 인증 후 자동 생성됨
└── scripts/
    ├── auth.py
    ├── list_events.py
    ├── create_event.py
    ├── update_event.py
    └── delete_event.py
```

## 3. 인증 프로세스

### 3.1 최초 인증

1. 스크립트를 처음 실행하면 브라우저가 자동으로 열림
2. Google 계정으로 로그인
3. 앱에 캘린더 접근 권한 부여
4. 인증 완료 후 `token.pickle` 파일 자동 생성

### 3.2 인증 테스트

```bash
python scripts/auth.py
```

성공 시 사용 가능한 캘린더 목록이 출력됩니다.

## 4. 권한 범위 (Scopes)

현재 설정된 권한:

- `https://www.googleapis.com/auth/calendar` - 캘린더 읽기/쓰기 전체 권한

필요에 따라 권한을 조정할 수 있습니다:

- `https://www.googleapis.com/auth/calendar.readonly` - 읽기 전용
- `https://www.googleapis.com/auth/calendar.events` - 일정만 관리

**주의:** 권한 변경 시 `token.pickle` 파일을 삭제하고 재인증해야 합니다.

## 5. 문제 해결

### 5.1 "credentials.json not found"

- `credentials.json` 파일이 스크립트와 같은 디렉토리에 있는지 확인
- 파일 이름이 정확한지 확인

### 5.2 "Access blocked: This app's request is invalid"

- OAuth 동의 화면 설정이 필요할 수 있음
- Google Cloud Console > API 및 서비스 > OAuth 동의 화면에서 설정

### 5.3 "The caller does not have permission"

- Google Calendar API가 활성화되어 있는지 확인
- 올바른 프로젝트를 선택했는지 확인

### 5.4 인증 재설정

```bash
# token.pickle 삭제 후 재인증
rm token.pickle
python scripts/auth.py
```

## 6. 보안 주의사항

1. **credentials.json 보안**
   - 이 파일에는 민감한 정보가 포함되어 있음
   - Git에 커밋하지 말 것 (.gitignore에 추가)
   - 외부에 공유하지 말 것

2. **token.pickle 보안**
   - 이 파일은 인증 토큰을 포함
   - Git에 커밋하지 말 것
   - 주기적으로 갱신됨

3. **.gitignore 예시**
```
credentials.json
token.pickle
*.pickle
```

## 7. 다음 단계

설정이 완료되면:

1. `list_events.py`로 일정 조회 테스트
2. `create_event.py`로 일정 생성 테스트
3. 필요한 기능을 스크립트로 구현하거나 Claude에게 요청
