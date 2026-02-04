# document-map-generator

ZK-PARA Vault의 전체 문서 인덱스(document-map.md)를 자동으로 생성하는 스킬

## 용도

- Vault 내 문서 변경 시 document-map.md 자동 업데이트
- `/update_git` 명령 실행 시 자동 호출됨
- 수동 실행도 가능

## 대상 폴더

| 폴더 | 설명 |
|------|------|
| 1_Projects | 진행 중 프로젝트 |
| 2_Areas | 지속 관리 영역 |
| 3_Resources | 참고 지식 |
| 4_Archive | 완료/비활성 항목 |
| 5_Zettelkasten | 지식 노트 |

## 사용법

### 자동 실행 (권장)
```
/update_git
```

### 수동 실행
```bash
python .claude/skills/document-map-generator/scripts/generate_docmap.py
```

또는 vault 경로 지정:
```bash
python generate_docmap.py /path/to/vault
```

## 출력 형식

`_Docs/document-map.md`에 다음 내용 생성:

1. **개요**: 총 문서 수, 프로젝트/영역/리소스 수
2. **폴더별 분포**: ASCII 프로그레스 바로 시각화
3. **1_Projects**: 프로젝트별 문서 목록
4. **2_Areas**: 영역별 문서 목록
5. **3_Resources**: 리소스별 문서 목록
6. **4_Archive**: 연도별 보관 문서
7. **5_Zettelkasten**: Fleeting/Literature/Permanent 분류
8. **통계 요약**: 카테고리별 문서 수

## 제외 파일

다음 시스템 파일은 인덱스에서 제외됨:
- CLAUDE.md
- tasks.md
- task.md
- prompts.md

## 정보 추출

각 프로젝트/영역/리소스의 설명은 해당 폴더의 CLAUDE.md에서 추출:
- `## 목표` 섹션 (프로젝트)
- `## 영역 정의` 섹션 (영역)
- `## 주제 설명` 섹션 (리소스)

## 주의사항

- UTF-8 인코딩 사용 (한글 지원)
- 각 섹션당 최대 10~15개 문서만 표시 (초과 시 "외 N개" 표시)
- 스크립트 실행 시 기존 document-map.md 덮어쓰기

## 파일 구조

```
.claude/skills/document-map-generator/
├── SKILL.md          # 이 문서
└── scripts/
    └── generate_docmap.py  # 메인 스크립트
```
