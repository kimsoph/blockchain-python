# -*- coding: utf-8 -*-
"""
암호화 유틸리티 모듈

ECDSA 서명 생성/검증 및 해시 관련 유틸리티를 제공합니다.
"""

import hashlib
import hmac
import secrets
from typing import Tuple, Optional


# secp256k1 곡선 파라미터 (비트코인에서 사용하는 곡선)
# y^2 = x^3 + 7 (mod p)
SECP256K1_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
SECP256K1_A = 0
SECP256K1_B = 7
SECP256K1_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
SECP256K1_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8


def mod_inverse(a: int, m: int) -> int:
    """모듈러 역원 계산 (확장 유클리드 알고리즘)"""
    if a < 0:
        a = a % m
    g, x, _ = extended_gcd(a, m)
    if g != 1:
        raise ValueError("모듈러 역원이 존재하지 않습니다")
    return x % m


def extended_gcd(a: int, b: int) -> Tuple[int, int, int]:
    """확장 유클리드 알고리즘"""
    if a == 0:
        return b, 0, 1
    gcd, x1, y1 = extended_gcd(b % a, a)
    x = y1 - (b // a) * x1
    y = x1
    return gcd, x, y


class ECPoint:
    """타원 곡선 위의 점"""

    def __init__(self, x: Optional[int], y: Optional[int], curve_p: int = SECP256K1_P):
        self.x = x
        self.y = y
        self.p = curve_p

    def is_infinity(self) -> bool:
        """무한원점인지 확인"""
        return self.x is None and self.y is None

    @staticmethod
    def infinity(curve_p: int = SECP256K1_P) -> 'ECPoint':
        """무한원점 반환"""
        return ECPoint(None, None, curve_p)

    def __eq__(self, other: 'ECPoint') -> bool:
        return self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        if self.is_infinity():
            return "ECPoint(infinity)"
        return f"ECPoint({self.x}, {self.y})"


def point_add(p1: ECPoint, p2: ECPoint) -> ECPoint:
    """타원 곡선 점 덧셈"""
    if p1.is_infinity():
        return p2
    if p2.is_infinity():
        return p1

    if p1.x == p2.x and p1.y != p2.y:
        return ECPoint.infinity()

    if p1.x == p2.x:
        # 점 더블링
        s = (3 * p1.x * p1.x + SECP256K1_A) * mod_inverse(2 * p1.y, SECP256K1_P) % SECP256K1_P
    else:
        # 일반 덧셈
        s = (p2.y - p1.y) * mod_inverse(p2.x - p1.x, SECP256K1_P) % SECP256K1_P

    x3 = (s * s - p1.x - p2.x) % SECP256K1_P
    y3 = (s * (p1.x - x3) - p1.y) % SECP256K1_P

    return ECPoint(x3, y3)


def point_multiply(k: int, point: ECPoint) -> ECPoint:
    """타원 곡선 스칼라 곱셈 (double-and-add)"""
    if k == 0 or point.is_infinity():
        return ECPoint.infinity()

    if k < 0:
        k = -k
        point = ECPoint(point.x, (-point.y) % SECP256K1_P)

    result = ECPoint.infinity()
    addend = point

    while k:
        if k & 1:
            result = point_add(result, addend)
        addend = point_add(addend, addend)
        k >>= 1

    return result


# 생성점 G
G = ECPoint(SECP256K1_GX, SECP256K1_GY)


def generate_private_key() -> int:
    """개인키 생성 (256비트 난수)"""
    while True:
        key = secrets.randbelow(SECP256K1_N)
        if key > 0:
            return key


def private_key_to_public_key(private_key: int) -> Tuple[int, int]:
    """개인키로부터 공개키 생성"""
    public_point = point_multiply(private_key, G)
    return (public_point.x, public_point.y)


def public_key_to_address(public_key: Tuple[int, int]) -> str:
    """공개키를 주소로 변환 (SHA256 + RIPEMD160 시뮬레이션)"""
    # 공개키를 바이트로 변환
    pub_bytes = public_key[0].to_bytes(32, 'big') + public_key[1].to_bytes(32, 'big')

    # SHA256 해시
    sha256_hash = hashlib.sha256(pub_bytes).digest()

    # RIPEMD160 대신 SHA256의 앞 20바이트 사용 (학습용 단순화)
    address_bytes = hashlib.sha256(sha256_hash).digest()[:20]

    # 16진수 문자열로 변환
    return address_bytes.hex()


def hash_message(message: str) -> int:
    """메시지를 해시하여 정수로 변환"""
    message_bytes = message.encode('utf-8')
    hash_bytes = hashlib.sha256(message_bytes).digest()
    return int.from_bytes(hash_bytes, 'big')


def sign_message(private_key: int, message: str) -> Tuple[int, int]:
    """
    ECDSA 서명 생성

    Args:
        private_key: 개인키
        message: 서명할 메시지

    Returns:
        (r, s) 서명 튜플
    """
    z = hash_message(message) % SECP256K1_N

    while True:
        k = secrets.randbelow(SECP256K1_N)
        if k == 0:
            continue

        # R = k * G
        R = point_multiply(k, G)
        r = R.x % SECP256K1_N

        if r == 0:
            continue

        # s = k^(-1) * (z + r * private_key) mod n
        k_inv = mod_inverse(k, SECP256K1_N)
        s = (k_inv * (z + r * private_key)) % SECP256K1_N

        if s == 0:
            continue

        return (r, s)


def verify_signature(public_key: Tuple[int, int], message: str, signature: Tuple[int, int]) -> bool:
    """
    ECDSA 서명 검증

    Args:
        public_key: 공개키 (x, y)
        message: 원본 메시지
        signature: (r, s) 서명

    Returns:
        서명이 유효하면 True
    """
    r, s = signature

    # 범위 검사
    if not (1 <= r < SECP256K1_N and 1 <= s < SECP256K1_N):
        return False

    z = hash_message(message) % SECP256K1_N

    # s^(-1) mod n
    s_inv = mod_inverse(s, SECP256K1_N)

    # u1 = z * s^(-1) mod n
    u1 = (z * s_inv) % SECP256K1_N

    # u2 = r * s^(-1) mod n
    u2 = (r * s_inv) % SECP256K1_N

    # P = u1 * G + u2 * public_key
    pub_point = ECPoint(public_key[0], public_key[1])
    point1 = point_multiply(u1, G)
    point2 = point_multiply(u2, pub_point)
    P = point_add(point1, point2)

    if P.is_infinity():
        return False

    # r == P.x mod n 이면 유효한 서명
    return r == P.x % SECP256K1_N


def bytes_to_hex(data: bytes) -> str:
    """바이트를 16진수 문자열로 변환"""
    return data.hex()


def hex_to_bytes(hex_str: str) -> bytes:
    """16진수 문자열을 바이트로 변환"""
    return bytes.fromhex(hex_str)


def int_to_hex(value: int, length: int = 32) -> str:
    """정수를 고정 길이 16진수 문자열로 변환"""
    return value.to_bytes(length, 'big').hex()


def hex_to_int(hex_str: str) -> int:
    """16진수 문자열을 정수로 변환"""
    return int(hex_str, 16)
