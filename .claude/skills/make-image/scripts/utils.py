# -*- coding: utf-8 -*-
"""
make-image 스킬 유틸리티 모듈
환경변수 로드, 파일명 생성, 경로 관리, 한글 처리 등
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional


def load_env_file(env_path: Optional[str] = None) -> dict:
    """
    .env 파일을 로드하여 환경변수 딕셔너리를 반환한다.

    Args:
        env_path: .env 파일 경로 (기본: .claude/.env)

    Returns:
        dict: 환경변수 딕셔너리
    """
    if env_path is None:
        # 스크립트 위치 기준으로 .env 파일 찾기
        current = Path(__file__).resolve()
        # .claude/skills/make-image/scripts/utils.py 에서 .claude/.env 찾기
        # parents[0]=scripts, [1]=make-image, [2]=skills, [3]=.claude
        env_path = current.parents[3] / '.env'
    else:
        env_path = Path(env_path)

    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 주석 및 빈 줄 건너뛰기
                if not line or line.startswith('#'):
                    continue
                # KEY=VALUE 형식 파싱
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 따옴표 제거
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
    else:
        print(f"[경고] .env 파일을 찾을 수 없습니다: {env_path}")

    return env_vars


def get_gemini_api_key() -> Optional[str]:
    """
    GEMINI_API_KEY를 환경변수 또는 .env 파일에서 가져온다.

    Returns:
        str: API 키 또는 None
    """
    # 먼저 환경변수 확인
    api_key = os.environ.get('GEMINI_API_KEY')

    if not api_key:
        # .env 파일에서 로드
        env_vars = load_env_file()
        api_key = env_vars.get('GEMINI_API_KEY')

    if not api_key:
        print("[오류] GEMINI_API_KEY를 찾을 수 없습니다.")
        print("       .claude/.env 파일에 GEMINI_API_KEY를 설정해주세요.")

    return api_key


def generate_filename(prefix: str = 'nanobanana', extension: str = 'png') -> str:
    """
    타임스탬프가 포함된 파일명을 생성한다.

    Args:
        prefix: 파일명 접두사 (기본: 'nanobanana')
        extension: 파일 확장자 (기본: 'png')

    Returns:
        str: 생성된 파일명 (예: 'nanobanana_20260102_143025.png')
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # 파일명에서 특수문자 제거 (알파벳, 숫자, _, - 만 허용)
    safe_prefix = "".join(c for c in prefix if c.isalnum() or c in ('_', '-'))
    if not safe_prefix:
        safe_prefix = 'nanobanana'
    return f"{safe_prefix}_{timestamp}.{extension}"


def get_output_dir(base_path: Optional[str] = None) -> Path:
    """
    이미지 출력 디렉토리 경로를 반환한다.
    디렉토리가 없으면 생성한다.
    년월(YYYYMM) 서브폴더에 자동 저장된다.

    Args:
        base_path: 기본 경로 (기본: 볼트 루트)

    Returns:
        Path: 출력 디렉토리 경로 (예: .../images/202601/)
    """
    # 현재 년월 (YYYYMM)
    current_ym = datetime.now().strftime('%Y%m')

    if base_path:
        output_dir = Path(base_path) / '9_Attachments' / 'images' / current_ym
    else:
        # 스크립트 위치 기준으로 볼트 루트 찾기
        current = Path(__file__).resolve()
        # .claude/skills/make-image/scripts/ 에서 4단계 위로
        vault_root = current.parents[4]
        output_dir = vault_root / '9_Attachments' / 'images' / current_ym

    # 디렉토리 생성
    output_dir.mkdir(parents=True, exist_ok=True)

    return output_dir


def ensure_output_dir(output_path: str) -> Path:
    """
    출력 경로의 디렉토리가 존재하는지 확인하고, 없으면 생성한다.

    Args:
        output_path: 출력 파일 경로

    Returns:
        Path: 출력 디렉토리 경로
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def read_text_file(file_path: str) -> str:
    """
    텍스트 파일을 UTF-8로 읽어서 내용을 반환한다.

    Args:
        file_path: 파일 경로

    Returns:
        str: 파일 내용

    Raises:
        FileNotFoundError: 파일이 존재하지 않을 때
        UnicodeDecodeError: 인코딩 오류 시
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")

    # 여러 인코딩 시도
    encodings = ['utf-8', 'utf-8-sig', 'cp949', 'euc-kr']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            return content
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        'unknown', b'', 0, 1,
        f"파일 인코딩을 인식할 수 없습니다: {file_path}"
    )


def truncate_prompt_safely(content: str, max_length: int = 2000) -> str:
    """
    프롬프트를 안전하게 절단한다. 문장/단락 경계에서 자른다.

    Args:
        content: 원본 콘텐츠
        max_length: 최대 길이

    Returns:
        str: 절단된 콘텐츠
    """
    if len(content) <= max_length:
        return content

    truncated = content[:max_length]

    # 마지막 완전한 문장 찾기 (한글/영어 문장 부호 모두 고려)
    sentence_endings = ['.', '。', '!', '?', '\n\n']
    last_end = -1

    for ending in sentence_endings:
        pos = truncated.rfind(ending)
        if pos > last_end:
            last_end = pos

    # 70% 이상 보존되는 경우에만 문장 경계에서 자르기
    if last_end > max_length * 0.7:
        return truncated[:last_end + 1].strip()

    # 그렇지 않으면 단어 경계에서 자르기
    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:
        return truncated[:last_space].strip() + '...'

    return truncated.strip() + '...'


def parse_prompt_from_file(file_path: str, max_length: int = 2000) -> str:
    """
    파일에서 이미지 생성 프롬프트를 추출한다.

    Args:
        file_path: 파일 경로 (.txt, .md, .csv 등)
        max_length: 최대 프롬프트 길이 (기본: 2000자)

    Returns:
        str: 추출된 프롬프트
    """
    content = read_text_file(file_path)

    # 마크다운 메타데이터 제거 (---로 감싸진 부분)
    content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # 마크다운 링크 제거 [[...]]
    content = re.sub(r'\[\[.*?\]\]', '', content)

    # 마크다운 헤더 마크 제거
    content = re.sub(r'^#+\s*', '', content, flags=re.MULTILINE)

    # 여러 줄 바꿈을 하나로
    content = re.sub(r'\n{3,}', '\n\n', content)

    # 앞뒤 공백 제거
    content = content.strip()

    # 안전한 절단 (문장/단어 경계에서)
    content = truncate_prompt_safely(content, max_length)

    return content


def sanitize_prompt(prompt: str) -> str:
    """
    프롬프트를 API 전송에 적합하게 정제한다.

    Args:
        prompt: 원본 프롬프트

    Returns:
        str: 정제된 프롬프트
    """
    # 제어 문자 제거 (탭, 줄바꿈 제외)
    prompt = ''.join(
        char for char in prompt
        if char == '\t' or char == '\n' or (ord(char) >= 32)
    )

    # 연속 공백 정리
    prompt = re.sub(r'[ \t]+', ' ', prompt)

    # 앞뒤 공백 제거
    prompt = prompt.strip()

    return prompt


def get_file_extension(file_path: str) -> str:
    """
    파일 경로에서 확장자를 추출한다 (소문자).

    Args:
        file_path: 파일 경로

    Returns:
        str: 확장자 (점 포함, 예: '.txt')
    """
    return Path(file_path).suffix.lower()


def is_supported_text_file(file_path: str) -> bool:
    """
    지원되는 텍스트 파일인지 확인한다.

    Args:
        file_path: 파일 경로

    Returns:
        bool: 지원 여부
    """
    supported_extensions = {'.txt', '.md', '.csv', '.json', '.yaml', '.yml'}
    ext = get_file_extension(file_path)
    return ext in supported_extensions


# 지원되는 가로세로 비율 (Gemini 2.5 Flash Image 기준)
# 참조: https://developers.googleblog.com/gemini-2-5-flash-image-now-ready-for-production-with-new-aspect-ratios/
SUPPORTED_ASPECT_RATIOS = [
    '1:1',   # 정사각형 (아이콘, 프로필)
    '2:3',   # 세로 (인물 사진)
    '3:2',   # 가로 (풍경)
    '3:4',   # 세로 (문서)
    '4:3',   # 표준 (보고서)
    '4:5',   # 세로 (인스타그램)
    '5:4',   # 가로
    '9:16',  # 세로 (모바일, 스토리)
    '16:9',  # 와이드 (프레젠테이션)
    '21:9',  # 울트라와이드 (시네마틱)
]

# 지원되는 이미지 크기 (대문자 K 필수)
SUPPORTED_IMAGE_SIZES = ['1K', '2K', '4K']


def validate_aspect_ratio(aspect_ratio: str) -> str:
    """
    가로세로 비율이 유효한지 확인하고, 기본값을 반환한다.

    Args:
        aspect_ratio: 가로세로 비율 (예: '16:9')

    Returns:
        str: 유효한 가로세로 비율
    """
    if aspect_ratio in SUPPORTED_ASPECT_RATIOS:
        return aspect_ratio
    print(f"[경고] 지원되지 않는 비율 '{aspect_ratio}'. 기본값 '1:1' 사용.")
    return '1:1'


def validate_image_size(image_size: str) -> str:
    """
    이미지 크기가 유효한지 확인하고, 기본값을 반환한다.

    Args:
        image_size: 이미지 크기 (예: '2K')

    Returns:
        str: 유효한 이미지 크기
    """
    if image_size.upper() in SUPPORTED_IMAGE_SIZES:
        return image_size.upper()
    print(f"[경고] 지원되지 않는 크기 '{image_size}'. 기본값 '1K' 사용.")
    return '1K'


if __name__ == '__main__':
    # 테스트
    print("=== make-image utils.py 테스트 ===\n")

    print(f"GEMINI_API_KEY: {'설정됨' if get_gemini_api_key() else '미설정'}")
    print(f"파일명 예시: {generate_filename('test')}")
    print(f"출력 디렉토리: {get_output_dir()}")
    print(f"지원 비율: {SUPPORTED_ASPECT_RATIOS}")
    print(f"지원 크기: {SUPPORTED_IMAGE_SIZES}")
