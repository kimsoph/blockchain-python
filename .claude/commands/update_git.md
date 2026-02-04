# /update_git

블록체인 프로젝트 Git 커밋 워크플로우

## 자동 실행 (순서대로)

1. **`.gitignore` 확인/생성**
   - Python 프로젝트용 .gitignore가 없으면 생성
   - 제외 항목: `__pycache__/`, `*.pyc`, `.env`, `venv/`, `.idea/`, `*.egg-info/`

2. **`README.md` 확인/업데이트**
   - 없으면 프로젝트 구조 분석 후 자동 생성
   - 포함 내용: 프로젝트 설명, 설치 방법, 사용법, 파일 구조
   - 있으면 파일 구조 변경 시 업데이트

3. **`CLAUDE.md` 확인/업데이트**
   - 없으면 프로젝트용 CLAUDE.md 생성
   - 포함 내용: 프로젝트 개요, 주요 파일, 개발 가이드, 실행 방법
   - 있으면 구조 변경 시 업데이트

4. **변경사항 확인**: `git status`
   - 추적되지 않은 파일 확인
   - 수정된 파일 확인
   - 민감 파일(.env, credentials 등) 포함 여부 확인

5. **변경 내용 검토**: `git diff`
   - staged/unstaged 변경사항 확인
   - 의도치 않은 변경 확인

6. **파일 스테이징**
   - 소스 파일: `*.py`
   - 문서 파일: `README.md`, `CLAUDE.md`
   - 설정 파일: `requirements.txt`, `.gitignore`
   - 민감 파일 제외 확인

7. **커밋 메시지 작성 및 커밋**
   - 변경 내용에 맞는 커밋 메시지 자동 생성
   - Conventional Commits 형식 사용
   ```
   git commit -m "type: 변경 내용 요약"
   ```

8. **Git Push** (선택)
   ```
   git push origin main
   ```
   - 사용자 확인 후 실행
   - 충돌 발생 시 `git pull --rebase` 필요

## 커밋 타입 가이드

| 타입 | 설명 |
|------|------|
| feat | 새로운 기능 추가 |
| fix | 버그 수정 |
| docs | 문서 변경 |
| refactor | 코드 리팩토링 |
| test | 테스트 추가/수정 |
| chore | 기타 변경 (빌드, 설정 등) |
