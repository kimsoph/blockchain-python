# -*- coding: utf-8 -*-
"""
블록체인 시각화 모듈

블록체인 구조, 트랜잭션 흐름, 잔액 변화를 시각화합니다.
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    import matplotlib
    matplotlib.use('Agg')  # GUI 없이 사용
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.patches import FancyBboxPatch, ConnectionPatch
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class BlockchainVisualizer:
    """
    블록체인 시각화 클래스

    블록체인 데이터를 다양한 차트와 다이어그램으로 시각화합니다.
    """

    def __init__(self, output_dir: str = "visualizations"):
        """
        시각화 클래스 초기화

        Args:
            output_dir: 출력 디렉토리
        """
        self.output_dir = output_dir
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # 한글 폰트 설정
        if MATPLOTLIB_AVAILABLE:
            self._setup_korean_font()

    def _setup_korean_font(self) -> None:
        """한글 폰트 설정"""
        import matplotlib.font_manager as fm

        # Windows에서 사용 가능한 한글 폰트 목록
        korean_fonts = ['Malgun Gothic', 'NanumGothic', 'NanumBarunGothic', 'Gulim']

        for font_name in korean_fonts:
            try:
                # 폰트가 시스템에 있는지 확인
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if font_path and 'DejaVu' not in font_path:
                    plt.rcParams['font.family'] = font_name
                    plt.rcParams['axes.unicode_minus'] = False
                    return
            except Exception:
                continue

        # 폰트를 찾지 못하면 기본값 사용
        plt.rcParams['axes.unicode_minus'] = False

    def is_available(self) -> bool:
        """matplotlib 사용 가능 여부"""
        return MATPLOTLIB_AVAILABLE

    def draw_blockchain_structure(self, blocks: List[Dict[str, Any]],
                                   filename: str = "blockchain_structure.png") -> str:
        """
        블록체인 구조 다이어그램 생성

        Args:
            blocks: 블록 데이터 리스트
            filename: 출력 파일명

        Returns:
            저장된 파일 경로
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("matplotlib가 설치되지 않았습니다")

        num_blocks = len(blocks)
        if num_blocks == 0:
            raise ValueError("블록이 없습니다")

        # 그림 크기 계산
        fig_width = max(12, num_blocks * 3)
        fig, ax = plt.subplots(figsize=(fig_width, 6))

        # 블록 그리기
        block_width = 2.0
        block_height = 3.0
        spacing = 1.5
        y_center = 3

        for i, block in enumerate(blocks):
            x = i * (block_width + spacing)

            # 블록 박스
            color = '#4CAF50' if i == 0 else '#2196F3'  # 제네시스 블록은 녹색
            rect = FancyBboxPatch(
                (x, y_center - block_height/2),
                block_width, block_height,
                boxstyle="round,pad=0.05,rounding_size=0.1",
                facecolor=color,
                edgecolor='black',
                linewidth=2,
                alpha=0.8
            )
            ax.add_patch(rect)

            # 블록 정보 텍스트
            ax.text(x + block_width/2, y_center + 1,
                   f"Block #{block['index']}", ha='center', va='center',
                   fontsize=10, fontweight='bold', color='white')

            ax.text(x + block_width/2, y_center + 0.3,
                   f"Nonce: {block['nonce']}", ha='center', va='center',
                   fontsize=8, color='white')

            ax.text(x + block_width/2, y_center - 0.3,
                   f"Hash: {block['hash'][:8]}...", ha='center', va='center',
                   fontsize=7, color='white')

            ax.text(x + block_width/2, y_center - 0.9,
                   f"Prev: {block['previous_hash'][:8]}...", ha='center', va='center',
                   fontsize=7, color='white')

            # 연결선 (다음 블록으로)
            if i < num_blocks - 1:
                ax.annotate(
                    '', xy=(x + block_width + spacing, y_center),
                    xytext=(x + block_width, y_center),
                    arrowprops=dict(arrowstyle='->', color='#333', lw=2)
                )

        # 축 설정
        ax.set_xlim(-0.5, num_blocks * (block_width + spacing))
        ax.set_ylim(0, 6)
        ax.set_aspect('equal')
        ax.axis('off')

        plt.title('블록체인 구조', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def draw_transaction_flow(self, transactions: List[Dict[str, Any]],
                               filename: str = "transaction_flow.png") -> str:
        """
        트랜잭션 흐름 다이어그램 생성

        Args:
            transactions: 트랜잭션 데이터 리스트
            filename: 출력 파일명

        Returns:
            저장된 파일 경로
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("matplotlib가 설치되지 않았습니다")

        if not transactions:
            raise ValueError("트랜잭션이 없습니다")

        # 고유 주소 추출
        addresses = set()
        for tx in transactions:
            addresses.add(tx['sender'])
            addresses.add(tx['recipient'])
        addresses = list(addresses)

        # 위치 계산
        num_addresses = len(addresses)
        fig, ax = plt.subplots(figsize=(12, max(6, num_addresses * 0.8)))

        # 주소별 y 좌표
        address_y = {addr: i for i, addr in enumerate(addresses)}

        # 트랜잭션 화살표 그리기
        colors = plt.cm.Set3(range(len(transactions)))

        for i, tx in enumerate(transactions):
            sender_y = address_y[tx['sender']]
            recipient_y = address_y[tx['recipient']]

            # 화살표
            ax.annotate(
                '', xy=(0.7, recipient_y),
                xytext=(0.3, sender_y),
                arrowprops=dict(
                    arrowstyle='-|>',
                    color=colors[i % len(colors)],
                    lw=2,
                    connectionstyle="arc3,rad=0.1"
                )
            )

            # 금액 표시
            mid_y = (sender_y + recipient_y) / 2
            ax.text(0.5, mid_y + 0.1, f"{tx['amount']}",
                   ha='center', va='bottom', fontsize=9,
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))

        # 주소 레이블
        for addr, y in address_y.items():
            display_addr = addr if len(addr) <= 15 else f"{addr[:12]}..."
            ax.text(0.1, y, display_addr, ha='right', va='center', fontsize=10)
            ax.text(0.9, y, display_addr, ha='left', va='center', fontsize=10)
            ax.plot([0.15, 0.25], [y, y], 'k-', lw=1)
            ax.plot([0.75, 0.85], [y, y], 'k-', lw=1)

        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, num_addresses - 0.5)
        ax.axis('off')

        plt.title('트랜잭션 흐름', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def draw_balance_chart(self, balance_history: Dict[str, List[Tuple[int, float]]],
                           filename: str = "balance_chart.png") -> str:
        """
        잔액 변화 그래프 생성

        Args:
            balance_history: 주소별 (블록인덱스, 잔액) 리스트
            filename: 출력 파일명

        Returns:
            저장된 파일 경로
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("matplotlib가 설치되지 않았습니다")

        if not balance_history:
            raise ValueError("잔액 데이터가 없습니다")

        fig, ax = plt.subplots(figsize=(10, 6))

        colors = plt.cm.tab10(range(len(balance_history)))

        for (address, history), color in zip(balance_history.items(), colors):
            if not history:
                continue

            blocks = [h[0] for h in history]
            balances = [h[1] for h in history]

            display_addr = address if len(address) <= 12 else f"{address[:10]}..."
            ax.plot(blocks, balances, 'o-', label=display_addr,
                   color=color, linewidth=2, markersize=6)

        ax.set_xlabel('블록 인덱스', fontsize=11)
        ax.set_ylabel('잔액', fontsize=11)
        ax.set_title('주소별 잔액 변화', fontsize=14, fontweight='bold')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)

        # x축을 정수로
        ax.xaxis.set_major_locator(plt.MaxNLocator(integer=True))

        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def draw_mining_stats(self, blocks: List[Dict[str, Any]],
                          filename: str = "mining_stats.png") -> str:
        """
        채굴 통계 차트 생성

        Args:
            blocks: 블록 데이터 리스트
            filename: 출력 파일명

        Returns:
            저장된 파일 경로
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("matplotlib가 설치되지 않았습니다")

        if len(blocks) < 2:
            raise ValueError("통계를 위해 최소 2개의 블록이 필요합니다")

        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 1. Nonce 분포
        ax1 = axes[0]
        indices = [b['index'] for b in blocks]
        nonces = [b['nonce'] for b in blocks]

        ax1.bar(indices, nonces, color='#3498db', alpha=0.7, edgecolor='black')
        ax1.set_xlabel('블록 인덱스', fontsize=11)
        ax1.set_ylabel('Nonce 값', fontsize=11)
        ax1.set_title('블록별 Nonce 값', fontsize=12, fontweight='bold')
        ax1.grid(True, alpha=0.3, axis='y')

        # 2. 해시 앞자리 0 개수 분포
        ax2 = axes[1]
        leading_zeros = []
        for b in blocks:
            count = 0
            for c in b['hash']:
                if c == '0':
                    count += 1
                else:
                    break
            leading_zeros.append(count)

        ax2.bar(indices, leading_zeros, color='#e74c3c', alpha=0.7, edgecolor='black')
        ax2.set_xlabel('블록 인덱스', fontsize=11)
        ax2.set_ylabel('선행 0의 개수', fontsize=11)
        ax2.set_title('해시의 선행 0 개수 (난이도)', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def draw_network_topology(self, nodes: List[str],
                               connections: List[Tuple[str, str]] = None,
                               filename: str = "network_topology.png") -> str:
        """
        네트워크 토폴로지 다이어그램

        Args:
            nodes: 노드 주소 리스트
            connections: 연결 정보 (노드1, 노드2) 리스트
            filename: 출력 파일명

        Returns:
            저장된 파일 경로
        """
        if not MATPLOTLIB_AVAILABLE:
            raise RuntimeError("matplotlib가 설치되지 않았습니다")

        if not nodes:
            raise ValueError("노드가 없습니다")

        import math

        fig, ax = plt.subplots(figsize=(10, 10))

        num_nodes = len(nodes)
        radius = 3

        # 원형 배치
        node_positions = {}
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / num_nodes - math.pi / 2
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            node_positions[node] = (x, y)

            # 노드 그리기
            circle = plt.Circle((x, y), 0.4, color='#3498db', ec='black', lw=2)
            ax.add_patch(circle)

            # 레이블
            label_radius = radius + 0.7
            lx = label_radius * math.cos(angle)
            ly = label_radius * math.sin(angle)

            display_node = node if len(node) <= 15 else f"{node[:12]}..."
            ax.text(lx, ly, display_node, ha='center', va='center', fontsize=9)

        # 연결선 그리기 (기본: 모든 노드 연결)
        if connections is None:
            connections = [(nodes[i], nodes[j])
                          for i in range(num_nodes)
                          for j in range(i+1, num_nodes)]

        for n1, n2 in connections:
            if n1 in node_positions and n2 in node_positions:
                x1, y1 = node_positions[n1]
                x2, y2 = node_positions[n2]
                ax.plot([x1, x2], [y1, y2], 'k-', alpha=0.3, lw=1)

        ax.set_xlim(-5, 5)
        ax.set_ylim(-5, 5)
        ax.set_aspect('equal')
        ax.axis('off')

        plt.title('블록체인 네트워크 토폴로지', fontsize=14, fontweight='bold', pad=20)
        plt.tight_layout()

        filepath = os.path.join(self.output_dir, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight',
                   facecolor='white', edgecolor='none')
        plt.close()

        return filepath

    def generate_all_visualizations(self, blockchain_data: Dict[str, Any]) -> Dict[str, str]:
        """
        모든 시각화 생성

        Args:
            blockchain_data: 블록체인 전체 데이터
                - blocks: 블록 리스트
                - transactions: 트랜잭션 리스트
                - balance_history: 잔액 히스토리
                - nodes: 노드 리스트 (선택)

        Returns:
            생성된 파일 경로 딕셔너리
        """
        results = {}

        blocks = blockchain_data.get('blocks', [])
        transactions = blockchain_data.get('transactions', [])
        balance_history = blockchain_data.get('balance_history', {})
        nodes = blockchain_data.get('nodes', [])

        # 블록체인 구조
        if blocks:
            try:
                results['structure'] = self.draw_blockchain_structure(blocks)
            except Exception as e:
                results['structure_error'] = str(e)

        # 트랜잭션 흐름
        if transactions:
            try:
                results['transaction_flow'] = self.draw_transaction_flow(transactions)
            except Exception as e:
                results['transaction_flow_error'] = str(e)

        # 잔액 변화
        if balance_history:
            try:
                results['balance'] = self.draw_balance_chart(balance_history)
            except Exception as e:
                results['balance_error'] = str(e)

        # 채굴 통계
        if len(blocks) >= 2:
            try:
                results['mining_stats'] = self.draw_mining_stats(blocks)
            except Exception as e:
                results['mining_stats_error'] = str(e)

        # 네트워크 토폴로지
        if nodes:
            try:
                results['network'] = self.draw_network_topology(nodes)
            except Exception as e:
                results['network_error'] = str(e)

        return results
