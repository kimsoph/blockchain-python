# -*- coding: utf-8 -*-
"""
블록체인 저장소 모듈

SQLite를 사용하여 블록체인 데이터를 영구 저장합니다.
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime


class BlockchainStorage:
    """
    블록체인 데이터를 SQLite에 저장하는 클래스

    블록과 트랜잭션을 영구 저장하고 조회하는 기능을 제공합니다.

    Attributes:
        db_path: SQLite 데이터베이스 파일 경로
    """

    def __init__(self, db_path: str = "blockchain.db"):
        """
        저장소 초기화

        Args:
            db_path: 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._init_database()

    def _get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        """데이터베이스 테이블 초기화"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 블록 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_index INTEGER UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                data TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                nonce INTEGER NOT NULL,
                hash TEXT UNIQUE NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 트랜잭션 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                block_index INTEGER,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TEXT NOT NULL,
                signature TEXT,
                sender_public_key TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (block_index) REFERENCES blocks(block_index)
            )
        ''')

        # 펜딩 트랜잭션 테이블 (아직 블록에 포함되지 않은 트랜잭션)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pending_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender TEXT NOT NULL,
                recipient TEXT NOT NULL,
                amount REAL NOT NULL,
                timestamp TEXT NOT NULL,
                signature TEXT,
                sender_public_key TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 메타데이터 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        ''')

        # 인덱스 생성
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_hash ON blocks(hash)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_blocks_index ON blocks(block_index)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_block ON transactions(block_index)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_sender ON transactions(sender)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tx_recipient ON transactions(recipient)')

        conn.commit()
        conn.close()

    def save_block(self, block_data: Dict[str, Any]) -> int:
        """
        블록 저장

        Args:
            block_data: 블록 딕셔너리 데이터

        Returns:
            저장된 블록의 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # data 필드는 JSON으로 직렬화
        data_json = json.dumps(block_data['data'], ensure_ascii=False)

        cursor.execute('''
            INSERT OR REPLACE INTO blocks
            (block_index, timestamp, data, previous_hash, nonce, hash)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            block_data['index'],
            block_data['timestamp'],
            data_json,
            block_data['previous_hash'],
            block_data['nonce'],
            block_data['hash']
        ))

        block_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return block_id

    def get_block(self, block_index: int) -> Optional[Dict[str, Any]]:
        """
        인덱스로 블록 조회

        Args:
            block_index: 블록 인덱스

        Returns:
            블록 딕셔너리 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM blocks WHERE block_index = ?',
            (block_index,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_block_dict(row)
        return None

    def get_block_by_hash(self, block_hash: str) -> Optional[Dict[str, Any]]:
        """
        해시로 블록 조회

        Args:
            block_hash: 블록 해시

        Returns:
            블록 딕셔너리 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM blocks WHERE hash = ?',
            (block_hash,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_block_dict(row)
        return None

    def get_all_blocks(self) -> List[Dict[str, Any]]:
        """
        모든 블록 조회 (인덱스 순)

        Returns:
            블록 딕셔너리 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM blocks ORDER BY block_index ASC')
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_block_dict(row) for row in rows]

    def get_latest_block(self) -> Optional[Dict[str, Any]]:
        """
        최신 블록 조회

        Returns:
            최신 블록 딕셔너리 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM blocks ORDER BY block_index DESC LIMIT 1')
        row = cursor.fetchone()
        conn.close()

        if row:
            return self._row_to_block_dict(row)
        return None

    def get_block_count(self) -> int:
        """
        저장된 블록 수 조회

        Returns:
            블록 수
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM blocks')
        count = cursor.fetchone()[0]
        conn.close()

        return count

    def _row_to_block_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """DB 행을 블록 딕셔너리로 변환"""
        return {
            'index': row['block_index'],
            'timestamp': row['timestamp'],
            'data': json.loads(row['data']),
            'previous_hash': row['previous_hash'],
            'nonce': row['nonce'],
            'hash': row['hash']
        }

    def save_transaction(self, tx_data: Dict[str, Any], block_index: Optional[int] = None) -> int:
        """
        트랜잭션 저장

        Args:
            tx_data: 트랜잭션 딕셔너리
            block_index: 블록 인덱스 (없으면 펜딩)

        Returns:
            저장된 트랜잭션 ID
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if block_index is not None:
            cursor.execute('''
                INSERT INTO transactions
                (block_index, sender, recipient, amount, timestamp, signature, sender_public_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                block_index,
                tx_data['sender'],
                tx_data['recipient'],
                tx_data['amount'],
                tx_data['timestamp'],
                tx_data.get('signature'),
                tx_data.get('sender_public_key')
            ))
        else:
            # 펜딩 트랜잭션
            cursor.execute('''
                INSERT INTO pending_transactions
                (sender, recipient, amount, timestamp, signature, sender_public_key)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                tx_data['sender'],
                tx_data['recipient'],
                tx_data['amount'],
                tx_data['timestamp'],
                tx_data.get('signature'),
                tx_data.get('sender_public_key')
            ))

        tx_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return tx_id

    def get_transactions_by_block(self, block_index: int) -> List[Dict[str, Any]]:
        """
        블록의 트랜잭션 조회

        Args:
            block_index: 블록 인덱스

        Returns:
            트랜잭션 딕셔너리 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            'SELECT * FROM transactions WHERE block_index = ?',
            (block_index,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_tx_dict(row) for row in rows]

    def get_transactions_by_address(self, address: str) -> List[Dict[str, Any]]:
        """
        주소와 관련된 모든 트랜잭션 조회

        Args:
            address: 지갑 주소

        Returns:
            트랜잭션 딕셔너리 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM transactions
            WHERE sender = ? OR recipient = ?
            ORDER BY timestamp ASC
        ''', (address, address))
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_tx_dict(row) for row in rows]

    def get_pending_transactions(self) -> List[Dict[str, Any]]:
        """
        펜딩 트랜잭션 조회

        Returns:
            펜딩 트랜잭션 리스트
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM pending_transactions ORDER BY created_at ASC')
        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_pending_tx_dict(row) for row in rows]

    def clear_pending_transactions(self) -> int:
        """
        펜딩 트랜잭션 삭제

        Returns:
            삭제된 트랜잭션 수
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM pending_transactions')
        count = cursor.fetchone()[0]

        cursor.execute('DELETE FROM pending_transactions')
        conn.commit()
        conn.close()

        return count

    def _row_to_tx_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """DB 행을 트랜잭션 딕셔너리로 변환"""
        result = {
            'sender': row['sender'],
            'recipient': row['recipient'],
            'amount': row['amount'],
            'timestamp': row['timestamp'],
            'block_index': row['block_index']
        }
        if row['signature']:
            result['signature'] = row['signature']
        if row['sender_public_key']:
            result['sender_public_key'] = row['sender_public_key']
        return result

    def _row_to_pending_tx_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """DB 행을 펜딩 트랜잭션 딕셔너리로 변환"""
        result = {
            'sender': row['sender'],
            'recipient': row['recipient'],
            'amount': row['amount'],
            'timestamp': row['timestamp']
        }
        if row['signature']:
            result['signature'] = row['signature']
        if row['sender_public_key']:
            result['sender_public_key'] = row['sender_public_key']
        return result

    def get_balance(self, address: str) -> float:
        """
        주소의 잔액 계산

        Args:
            address: 지갑 주소

        Returns:
            잔액
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # 받은 금액
        cursor.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE recipient = ?',
            (address,)
        )
        received = cursor.fetchone()[0]

        # 보낸 금액
        cursor.execute(
            'SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE sender = ?',
            (address,)
        )
        sent = cursor.fetchone()[0]

        conn.close()

        return received - sent

    def set_metadata(self, key: str, value: str) -> None:
        """
        메타데이터 저장

        Args:
            key: 키
            value: 값
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)
        ''', (key, value))

        conn.commit()
        conn.close()

    def get_metadata(self, key: str) -> Optional[str]:
        """
        메타데이터 조회

        Args:
            key: 키

        Returns:
            값 또는 None
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT value FROM metadata WHERE key = ?', (key,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return row[0]
        return None

    def clear_all(self) -> None:
        """모든 데이터 삭제 (주의!)"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('DELETE FROM transactions')
        cursor.execute('DELETE FROM pending_transactions')
        cursor.execute('DELETE FROM blocks')
        cursor.execute('DELETE FROM metadata')

        conn.commit()
        conn.close()

    def close(self) -> None:
        """리소스 정리 (현재는 연결 풀을 사용하지 않으므로 no-op)"""
        pass
