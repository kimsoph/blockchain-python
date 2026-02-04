# -*- coding: utf-8 -*-
"""
블록체인 CLI 인터페이스

블록체인과 상호작용할 수 있는 명령줄 인터페이스를 제공합니다.
"""

from .blockchain import Blockchain
from .transaction import Transaction


def print_menu():
    """메뉴를 출력합니다."""
    print("\n" + "=" * 50)
    print("        블록체인 실습 CLI")
    print("=" * 50)
    print("1. 블록 추가 (간단한 데이터)")
    print("2. 트랜잭션 생성")
    print("3. 펜딩 트랜잭션 채굴")
    print("4. 잔액 조회")
    print("5. 블록체인 전체 조회")
    print("6. 블록체인 유효성 검사")
    print("7. 블록 데이터 변조 테스트")
    print("8. 종료")
    print("=" * 50)


def add_simple_block(blockchain: Blockchain):
    """간단한 데이터로 블록을 추가합니다."""
    print("\n--- 블록 추가 ---")
    data = input("블록에 저장할 데이터를 입력하세요: ")
    if data:
        blockchain.add_block(data)
    else:
        print("데이터가 입력되지 않았습니다.")


def create_transaction(blockchain: Blockchain):
    """새 트랜잭션을 생성합니다."""
    print("\n--- 트랜잭션 생성 ---")
    sender = input("보내는 주소: ")
    recipient = input("받는 주소: ")
    try:
        amount = float(input("금액: "))
        tx = Transaction(sender, recipient, amount)
        if tx.is_valid():
            block_index = blockchain.add_transaction(tx)
            print(f"트랜잭션이 생성되었습니다. 블록 #{block_index}에 포함될 예정입니다.")
            print(f"현재 펜딩 트랜잭션 수: {len(blockchain.pending_transactions)}")
        else:
            print("유효하지 않은 트랜잭션입니다.")
    except ValueError as e:
        print(f"오류: {e}")


def mine_transactions(blockchain: Blockchain):
    """펜딩 트랜잭션을 채굴합니다."""
    print("\n--- 트랜잭션 채굴 ---")
    miner_address = input("채굴 보상을 받을 주소: ")
    if miner_address:
        print("\n채굴 중...")
        blockchain.mine_pending_transactions(miner_address)
    else:
        print("주소가 입력되지 않았습니다.")


def check_balance(blockchain: Blockchain):
    """잔액을 조회합니다."""
    print("\n--- 잔액 조회 ---")
    address = input("조회할 주소: ")
    if address:
        balance = blockchain.get_balance(address)
        print(f"\n{address}의 잔액: {balance}")
    else:
        print("주소가 입력되지 않았습니다.")


def tampering_test(blockchain: Blockchain):
    """블록 데이터 변조 테스트를 수행합니다."""
    print("\n--- 블록 데이터 변조 테스트 ---")

    if len(blockchain) < 2:
        print("변조 테스트를 위해서는 최소 2개의 블록이 필요합니다.")
        print("먼저 블록을 추가해주세요.")
        return

    print("이 테스트는 블록의 데이터를 임의로 변경한 후")
    print("블록체인 유효성 검사가 실패하는지 확인합니다.\n")

    # 변조 전 상태 확인
    print("변조 전 유효성 검사:")
    blockchain.is_chain_valid()

    # 블록 데이터 변조
    target_index = 1  # 제네시스 블록 다음 블록
    original_data = blockchain.chain[target_index].data
    blockchain.chain[target_index].data = "변조된 데이터!"

    print(f"\n블록 #{target_index}의 데이터를 변조했습니다.")
    print(f"  원본: {original_data}")
    print(f"  변조: {blockchain.chain[target_index].data}")

    # 변조 후 상태 확인
    print("\n변조 후 유효성 검사:")
    is_valid = blockchain.is_chain_valid()

    if not is_valid:
        print("\n변조가 감지되었습니다! 블록체인이 무효화되었습니다.")
    else:
        print("\n경고: 변조가 감지되지 않았습니다!")

    # 원본 데이터 복원
    blockchain.chain[target_index].data = original_data
    print("\n원본 데이터를 복원했습니다.")


def demo_mode(blockchain: Blockchain):
    """데모 모드 - 블록체인의 주요 기능을 자동으로 시연합니다."""
    print("\n" + "=" * 60)
    print("            블록체인 데모 모드")
    print("=" * 60)

    # 1. 간단한 블록 추가
    print("\n[1단계] 간단한 블록 추가")
    print("-" * 40)
    blockchain.add_block("첫 번째 데이터 블록")
    blockchain.add_block("두 번째 데이터 블록")

    # 2. 트랜잭션 생성 및 채굴
    print("\n[2단계] 트랜잭션 생성")
    print("-" * 40)
    tx1 = Transaction("Alice", "Bob", 50)
    tx2 = Transaction("Bob", "Charlie", 25)
    blockchain.add_transaction(tx1)
    print(f"트랜잭션 추가: {tx1}")
    blockchain.add_transaction(tx2)
    print(f"트랜잭션 추가: {tx2}")

    print("\n[3단계] 트랜잭션 채굴")
    print("-" * 40)
    blockchain.mine_pending_transactions("Miner1")

    # 채굴 보상 트랜잭션 채굴
    print("\n[4단계] 채굴 보상 수령 (다음 블록에 포함)")
    print("-" * 40)
    blockchain.mine_pending_transactions("Miner1")

    # 3. 잔액 조회
    print("\n[5단계] 잔액 조회")
    print("-" * 40)
    for address in ["Alice", "Bob", "Charlie", "Miner1"]:
        balance = blockchain.get_balance(address)
        print(f"  {address}의 잔액: {balance}")

    # 4. 블록체인 조회
    print("\n[6단계] 블록체인 전체 조회")
    blockchain.print_chain()

    # 5. 유효성 검사
    print("\n[7단계] 블록체인 유효성 검사")
    print("-" * 40)
    blockchain.is_chain_valid()

    # 6. 변조 테스트
    print("\n[8단계] 변조 테스트")
    print("-" * 40)
    tampering_test(blockchain)

    print("\n데모가 완료되었습니다!")


def main():
    """메인 함수 - CLI를 실행합니다."""
    print("\n블록체인을 초기화하는 중...")
    print("(난이도 4 = 해시가 '0000'으로 시작해야 함)\n")

    # 블록체인 생성 (난이도 4)
    blockchain = Blockchain(difficulty=4)

    # 데모 모드 여부 확인
    demo = input("데모 모드로 실행하시겠습니까? (y/n): ").lower().strip()
    if demo == 'y':
        demo_mode(blockchain)
        return

    # 일반 CLI 모드
    while True:
        print_menu()
        choice = input("선택: ").strip()

        if choice == '1':
            add_simple_block(blockchain)
        elif choice == '2':
            create_transaction(blockchain)
        elif choice == '3':
            mine_transactions(blockchain)
        elif choice == '4':
            check_balance(blockchain)
        elif choice == '5':
            blockchain.print_chain()
        elif choice == '6':
            blockchain.is_chain_valid()
        elif choice == '7':
            tampering_test(blockchain)
        elif choice == '8':
            print("\n블록체인 CLI를 종료합니다. 감사합니다!")
            break
        else:
            print("\n잘못된 선택입니다. 다시 선택해주세요.")


if __name__ == "__main__":
    main()
