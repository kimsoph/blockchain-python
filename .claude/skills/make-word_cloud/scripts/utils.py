# -*- coding: utf-8 -*-
"""
make-word_cloud 스킬 유틸리티
- 한글 폰트 설정
- 출력 경로 관리
- 불용어 리스트
"""

import platform
from pathlib import Path
from datetime import datetime
import os


def get_korean_font() -> str:
    """운영체제별 한글 폰트 반환"""
    system = platform.system()
    if system == 'Windows':
        return 'Malgun Gothic'
    elif system == 'Darwin':  # macOS
        return 'AppleGothic'
    else:  # Linux
        return 'NanumGothic'


def get_korean_font_path() -> str:
    """한글 폰트 파일 경로 반환 (wordcloud용)"""
    system = platform.system()
    if system == 'Windows':
        # Windows 폰트 경로들
        font_paths = [
            'C:/Windows/Fonts/malgun.ttf',
            'C:/Windows/Fonts/malgunbd.ttf',
            'C:/Windows/Fonts/NanumGothic.ttf',
        ]
        for path in font_paths:
            if os.path.exists(path):
                return path
        return 'C:/Windows/Fonts/malgun.ttf'  # 기본값
    elif system == 'Darwin':  # macOS
        return '/System/Library/Fonts/AppleGothic.ttf'
    else:  # Linux
        return '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'


def get_output_dir() -> Path:
    """출력 디렉토리 경로 반환: 9_Attachments/images/{YYYYMM}/"""
    current = Path(__file__).resolve()
    # .claude/skills/make-word_cloud/scripts/utils.py → ZK-PARA/
    vault_root = current.parents[4]

    output_dir = vault_root / '9_Attachments' / 'images' / datetime.now().strftime('%Y%m')
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def generate_filename(name: str, prefix: str = 'wc') -> str:
    """타임스탬프가 포함된 파일명 생성"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에 사용 불가능한 문자 제거
    safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_', '가-힣')).strip()
    safe_name = safe_name.replace(' ', '_')
    return f"{prefix}_{safe_name}_{timestamp}.png"


def setup_mecab():
    """Mecab 환경 설정 (Windows용)"""
    mecab_path = r'C:\mecab'
    mecab_bin = r'C:\mecab\bin'

    if platform.system() == 'Windows' and os.path.exists(mecab_path):
        # Python 3.8+ DLL 디렉토리 추가 (필수)
        if hasattr(os, 'add_dll_directory') and os.path.exists(mecab_bin):
            os.add_dll_directory(mecab_bin)

        # 환경변수 설정
        os.environ['MECAB_PATH'] = os.path.join(mecab_path, 'mecab.exe')
        # PATH에 추가
        if mecab_bin not in os.environ.get('PATH', ''):
            os.environ['PATH'] = mecab_bin + ';' + mecab_path + ';' + os.environ.get('PATH', '')


def get_mecab_dicpath() -> str:
    """Mecab 딕셔너리 경로 반환 (슬래시 사용)"""
    return 'C:/mecab/mecab-ko-dic'


# 한글 불용어 리스트
KOREAN_STOPWORDS = {
    # 조사
    '이', '가', '은', '는', '을', '를', '의', '에', '에서', '으로', '로', '와', '과',
    '도', '만', '부터', '까지', '에게', '한테', '께', '보다', '처럼', '같이', '마다',
    '이나', '나', '든지', '든가', '라도', '이라도', '야', '아', '이여', '여',

    # 어미/접사
    '하다', '되다', '있다', '없다', '않다', '이다', '아니다',
    '것', '수', '등', '들', '및', '더', '또', '또는', '그', '저', '이런', '그런',

    # 대명사
    '나', '너', '우리', '저희', '그', '그녀', '그들', '이것', '저것', '그것',
    '여기', '저기', '거기', '어디', '누구', '무엇', '언제', '어떻게', '왜',

    # 부사/접속사
    '매우', '아주', '너무', '정말', '참', '꽤', '상당히', '대단히',
    '그리고', '그러나', '그래서', '따라서', '하지만', '그러므로', '왜냐하면',
    '만약', '비록', '설령', '만일', '가령',

    # 일반적인 동사/형용사 어간
    '하', '되', '있', '없', '같', '보', '알', '말', '생각', '사람',

    # 기타 자주 등장하지만 의미 없는 단어
    '때', '곳', '바', '점', '중', '년', '월', '일', '번', '개', '명', '원',
    '위', '아래', '앞', '뒤', '옆', '사이', '안', '밖', '속',
}

# 추가 불용어 (문서 유형별로 확장 가능)
SPEECH_STOPWORDS = {
    '존경', '국민', '여러분', '감사', '오늘', '우리', '대한민국', '나라',
}


def get_stopwords(include_speech: bool = True) -> set:
    """불용어 세트 반환"""
    stopwords = KOREAN_STOPWORDS.copy()
    if include_speech:
        stopwords.update(SPEECH_STOPWORDS)
    return stopwords
