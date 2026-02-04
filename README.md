# Blockchain Python

Python으로 구현한 블록체인 학습용 프로젝트입니다.

## 주요 기능

- **블록 생성 및 채굴**: SHA-256 해시 기반 작업 증명(PoW)
- **트랜잭션 처리**: 발신자/수신자 간 거래 생성 및 검증
- **체인 검증**: 블록체인 무결성 검사
- **잔액 조회**: 주소별 잔액 계산
- **변조 탐지**: 데이터 위변조 시 자동 감지

## 파일 구조

```
blockChain/
├── src/
│   ├── __init__.py       # 패키지 초기화
│   ├── block.py          # Block 클래스 - 블록 정의, 해시 계산, 채굴
│   ├── blockchain.py     # Blockchain 클래스 - 체인 관리, 트랜잭션
│   ├── transaction.py    # Transaction 클래스 - 거래 정의
│   └── main.py           # CLI 인터페이스
├── CLAUDE.md
└── README.md
```

## 설치 및 실행

```bash
# Python 3.7+ 필요
python -m src.main
```

## 사용법

### CLI 모드
프로그램 실행 후 메뉴에서 원하는 기능 선택:
1. 블록 추가
2. 트랜잭션 생성
3. 펜딩 트랜잭션 채굴
4. 잔액 조회
5. 블록체인 전체 조회
6. 유효성 검사
7. 변조 테스트

### 데모 모드
실행 시 `y` 입력하면 자동으로 주요 기능을 시연합니다.

## 핵심 개념

| 개념 | 설명 |
|------|------|
| Block | 데이터를 담는 기본 단위 (index, timestamp, data, hash) |
| Chain | 블록들의 연결 리스트, previous_hash로 연결 |
| PoW | 작업 증명 - 난이도만큼 0으로 시작하는 해시 찾기 |
| Nonce | PoW에서 해시 조건을 맞추기 위해 변경하는 값 |
| Genesis | 체인의 첫 번째 블록 (previous_hash = "0") |

## 기술 스택

- Python 3.7+
- hashlib (SHA-256)
- 외부 라이브러리 없음
