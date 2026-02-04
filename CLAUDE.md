# Blockchain Python Project

## 프로젝트 개요

Python으로 구현한 블록체인 학습용 CLI 애플리케이션.
작업 증명(PoW), 트랜잭션, 체인 검증 등 블록체인 핵심 개념을 구현.

## 중요 지침

### 한글 인코딩 (필수)

**모든 작업에서 한글 인코딩에 특히 주의할 것.**

- 모든 Python 파일 상단에 `# -*- coding: utf-8 -*-` 선언
- 파일 읽기/쓰기 시 `encoding='utf-8'` 명시
- JSON 직렬화 시 `ensure_ascii=False` 사용
- print 출력 시 Windows 콘솔 인코딩 고려
- 문자열 처리 시 `.encode('utf-8')` / `.decode('utf-8')` 명시

```python
# 파일 읽기
with open(file, 'r', encoding='utf-8') as f:
    content = f.read()

# JSON 저장
json.dumps(data, ensure_ascii=False)

# 해시 계산
hashlib.sha256(string.encode('utf-8')).hexdigest()
```

## 주요 파일

| 파일 | 역할 |
|------|------|
| `src/__init__.py` | 패키지 초기화, 모듈 export |
| `src/block.py` | Block 클래스 - 해시 계산, 채굴(PoW) |
| `src/blockchain.py` | Blockchain 클래스 - 체인 관리, 트랜잭션, 검증 |
| `src/transaction.py` | Transaction 클래스 - 거래 정의 및 유효성 검사 |
| `src/main.py` | CLI 메뉴 및 사용자 인터페이스 |

## 실행 방법

```bash
python -m src.main
```

- 데모 모드: 실행 시 `y` 입력
- CLI 모드: 실행 시 `n` 입력 후 메뉴 선택

## 개발 가이드

### 클래스 구조

```
Block
├── index, timestamp, data, previous_hash, nonce, hash
├── calculate_hash() → SHA-256 해시 계산
└── mine_block(difficulty) → PoW 수행

Blockchain
├── chain[], difficulty, pending_transactions[], mining_reward
├── add_block(data) → 블록 추가
├── add_transaction(tx) → 트랜잭션 추가
├── mine_pending_transactions(address) → 채굴
├── get_balance(address) → 잔액 조회
└── is_chain_valid() → 체인 검증

Transaction
├── sender, recipient, amount, timestamp
├── to_dict() → 딕셔너리 변환
└── is_valid() → 유효성 검사
```

### 난이도 설정

- 기본 난이도: 4 (해시가 "0000"으로 시작해야 함)
- `Blockchain(difficulty=N)`으로 조정 가능
- 난이도가 높을수록 채굴 시간 증가

## 테스트

```bash
# 데모 모드로 전체 기능 테스트
python -m src.main
# → y 입력
```

## 의존성

- Python 3.7+
- 외부 라이브러리 없음 (표준 라이브러리만 사용)
