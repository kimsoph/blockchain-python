# Blockchain Python Project

## 프로젝트 개요

Python으로 구현한 블록체인 학습용 CLI 애플리케이션.
작업 증명(PoW), 트랜잭션, ECDSA 서명, 체인 검증 등 블록체인 핵심 개념을 구현.

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
| `src/transaction.py` | Transaction 클래스 - 거래 정의, 서명/검증 |
| `src/wallet.py` | Wallet 클래스 - ECDSA 키 쌍 관리, 서명 |
| `src/crypto_utils.py` | 암호화 유틸리티 - secp256k1 곡선 연산 |
| `src/storage.py` | BlockchainStorage 클래스 - SQLite 저장소 |
| `src/network.py` | Flask REST API 서버 |
| `src/node.py` | Node 클래스 - P2P 노드 관리, 합의 |
| `src/visualizer.py` | BlockchainVisualizer 클래스 - Matplotlib 시각화 |
| `src/main.py` | CLI 메뉴 및 사용자 인터페이스 |

## 실행 방법

```bash
# CLI 실행
python -m src.main

# 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src --cov-report=term-missing

# REST API 서버
python -c "from src.network import run_server; run_server(port=5000)"
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
├── sender, recipient, amount, timestamp, signature
├── to_dict() → 딕셔너리 변환
├── is_valid() → 유효성 검사
├── sign(wallet) → 지갑으로 서명
└── verify_signature() → 서명 검증

Wallet
├── private_key, public_key, address
├── sign(message) → 메시지 서명
├── verify(public_key, message, signature) → 서명 검증
└── from_private_key_hex(hex) → 개인키로 복원

BlockchainStorage
├── save_block(block_data) → 블록 저장
├── get_block(index) → 블록 조회
├── save_transaction(tx_data) → 트랜잭션 저장
└── get_balance(address) → 잔액 계산

Node
├── register_node(address) → 노드 등록
├── fetch_chain(node) → 체인 가져오기
└── find_longest_chain() → 합의 알고리즘

BlockchainVisualizer
├── draw_blockchain_structure() → 블록체인 구조 다이어그램
├── draw_transaction_flow() → 트랜잭션 흐름
├── draw_balance_chart() → 잔액 변화 그래프
└── draw_mining_stats() → 채굴 통계
```

### 난이도 설정

- 기본 난이도: 4 (해시가 "0000"으로 시작해야 함)
- `Blockchain(difficulty=N)`으로 조정 가능
- 난이도가 높을수록 채굴 시간 증가

## 테스트

```bash
# 전체 테스트
pytest

# 특정 모듈 테스트
pytest tests/test_wallet.py -v

# 커버리지 포함
pytest --cov=src --cov-report=term-missing
```

## 의존성

- Python 3.7+
- pytest (테스트)
- Flask (REST API)
- matplotlib (시각화)
- requests (HTTP 클라이언트)
