# -*- coding: utf-8 -*-
"""
Nonce 찾기 과정 시연
작업 증명(PoW)이 실제로 어떻게 동작하는지 보여줍니다.
"""

import hashlib
import time
import sys

# Windows 콘솔 인코딩 설정
sys.stdout.reconfigure(encoding='utf-8')


def find_nonce_demo(data: str, difficulty: int = 4):
    """
    Nonce 찾기 과정을 단계별로 보여줍니다.
    """
    target = "0" * difficulty
    nonce = 0

    print("=" * 70)
    print(f"[목표] 해시가 '{target}'으로 시작하는 nonce 찾기")
    print(f"[데이터] {data}")
    print("=" * 70)
    print()
    print(f"{'Nonce':>10} | {'해시 결과 (앞 20자)':^24} | {'결과'}")
    print("-" * 70)

    start_time = time.time()

    while True:
        # 데이터 + nonce를 합쳐서 해시 계산
        text = f"{data}{nonce}"
        hash_result = hashlib.sha256(text.encode('utf-8')).hexdigest()

        # 처음 20번, 그 후 1000번마다, 성공 시 출력
        if nonce < 20 or nonce % 1000 == 0 or hash_result.startswith(target):
            status = "[SUCCESS]" if hash_result.startswith(target) else "[X]"
            print(f"{nonce:>10} | {hash_result[:20]}... | {status}")

        # 성공 조건 확인
        if hash_result.startswith(target):
            elapsed = time.time() - start_time
            print("-" * 70)
            print()
            print("*** 채굴 성공! ***")
            print(f"   - 찾은 Nonce: {nonce}")
            print(f"   - 시도 횟수: {nonce + 1}번")
            print(f"   - 소요 시간: {elapsed:.4f}초")
            print(f"   - 최종 해시: {hash_result}")
            print()

            # 검증
            print("[검증]")
            print(f'   SHA256("{data}{nonce}")')
            print(f"   = {hash_result}")
            print(f"   앞 {difficulty}자리 = '{hash_result[:difficulty]}' == '{target}' (일치!)")

            return nonce, hash_result

        nonce += 1

        # 안전장치
        if nonce > 10_000_000:
            print("10,000,000번 시도 후 중단")
            return None, None


if __name__ == "__main__":
    print()
    print("=" * 70)
    print("      [작업 증명(Proof of Work) - Nonce 찾기 시연]")
    print("=" * 70)

    # 시연 1: 난이도 2
    print("\n\n### 시연 1: 난이도 2 (해시가 '00'으로 시작)\n")
    find_nonce_demo("Hello, Blockchain!", difficulty=2)

    # 시연 2: 난이도 3
    print("\n\n### 시연 2: 난이도 3 (해시가 '000'으로 시작)\n")
    find_nonce_demo("Hello, Blockchain!", difficulty=3)

    # 시연 3: 난이도 4
    print("\n\n### 시연 3: 난이도 4 (해시가 '0000'으로 시작)\n")
    find_nonce_demo("Hello, Blockchain!", difficulty=4)

    # 데이터가 조금만 바뀌어도 완전히 다른 nonce 필요
    print("\n\n### 시연 4: 데이터가 바뀌면? (난이도 3)")
    print("    '!' -> '?' 한 글자만 변경\n")
    find_nonce_demo("Hello, Blockchain?", difficulty=3)
