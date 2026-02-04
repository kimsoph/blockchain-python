# -*- coding: utf-8 -*-
"""
make-image 스킬 메인 모듈
나노바나나(Gemini) API를 사용하여 텍스트 기반 이미지를 생성한다.

지원 기능:
- 텍스트 프롬프트로 이미지 생성
- 텍스트 파일(.txt, .md, .csv)에서 프롬프트 추출 후 이미지 생성
- 다양한 가로세로 비율 및 해상도 지원
- 한글 프롬프트 완벽 지원

사용법:
    from nanobanana import NanoBananaClient

    client = NanoBananaClient()
    result = client.generate_image("귀여운 고양이가 책을 읽는 모습")
    print(f"이미지 저장 위치: {result['path']}")
"""

import os
import sys
import base64
from pathlib import Path
from typing import Optional, Dict, Any, Union, List

# 현재 스크립트 경로를 기준으로 utils 모듈 import
script_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(script_dir))

from utils import (
    get_gemini_api_key,
    generate_filename,
    get_output_dir,
    parse_prompt_from_file,
    sanitize_prompt,
    is_supported_text_file,
    validate_aspect_ratio,
    validate_image_size,
    SUPPORTED_ASPECT_RATIOS,
    SUPPORTED_IMAGE_SIZES,
)

from prompt_templates import (
    validate_prompt_geography,
    enhance_prompt,
    has_blocked_content,
)


# ============================================================
# 커스텀 예외 클래스
# ============================================================

class NanoBananaError(Exception):
    """NanoBanana 기본 예외 클래스"""
    pass


class APIKeyError(NanoBananaError):
    """API 키 관련 오류"""
    pass


class PromptValidationError(NanoBananaError):
    """프롬프트 검증 실패"""
    pass


class ImageGenerationError(NanoBananaError):
    """이미지 생성 실패"""
    pass


class BlockedContentError(NanoBananaError):
    """차단된 콘텐츠 감지"""
    pass


class NanoBananaClient:
    """
    나노바나나(Gemini) API 클라이언트
    텍스트 기반 이미지 생성을 수행한다.
    """

    # 사용 가능한 이미지 생성 모델
    MODELS = {
        'flash': 'gemini-2.5-flash-image',     # 빠른 모델 (Nano Banana)
        'pro': 'nano-banana-pro-preview',      # 고품질 모델 (Nano Banana Pro)
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = 'flash',
        output_dir: Optional[str] = None
    ):
        """
        NanoBananaClient 초기화

        Args:
            api_key: Gemini API 키 (기본: 환경변수/파일에서 로드)
            model: 사용할 모델 ('flash' 또는 'pro')
            output_dir: 이미지 저장 디렉토리 (기본: 9_Attachments/Images/AI_generates/)
        """
        self.api_key = api_key or get_gemini_api_key()
        if not self.api_key:
            raise APIKeyError(
                "GEMINI_API_KEY가 설정되지 않았습니다.\n"
                "설정 방법: .claude/.env 파일에 GEMINI_API_KEY=\"your_key\" 추가"
            )

        self.model_name = self.MODELS.get(model, self.MODELS['flash'])
        self.output_dir = Path(output_dir) if output_dir else get_output_dir()

        # Google GenAI 클라이언트 초기화
        self._client = None
        self._init_client()

    def _init_client(self):
        """Google GenAI 클라이언트를 초기화한다."""
        try:
            from google import genai
            self._client = genai.Client(api_key=self.api_key)
            print(f"[OK] NanoBananaClient 초기화 완료 (모델: {self.model_name})")
        except ImportError:
            raise ImportError(
                "google-genai 패키지가 설치되지 않았습니다.\n"
                "설치: pip install google-genai"
            )

    def generate_image(
        self,
        prompt: str,
        filename: Optional[str] = None,
        aspect_ratio: str = '1:1',
        image_size: str = '1K',
        save_image: bool = True
    ) -> Dict[str, Any]:
        """
        텍스트 프롬프트로 이미지를 생성한다.

        Args:
            prompt: 이미지 생성 프롬프트 (한글/영어 모두 가능)
            filename: 저장할 파일명 (기본: 자동 생성)
            aspect_ratio: 가로세로 비율 ('1:1', '16:9', '9:16', '4:3', '3:4')
            image_size: 이미지 크기 ('1K', '2K', '4K')
            save_image: 이미지 저장 여부

        Returns:
            dict: {
                'success': bool,
                'path': str (저장된 파일 경로),
                'filename': str,
                'prompt': str,
                'obsidian_embed': str (옵시디언 삽입 코드),
                'error': str (오류 시)
            }
        """
        from google.genai import types

        # 프롬프트 정제
        prompt = sanitize_prompt(prompt)
        if not prompt:
            return {
                'success': False,
                'error': '프롬프트가 비어있습니다.',
                'prompt': prompt
            }

        # 차단된 콘텐츠 검사
        is_blocked, block_reason = has_blocked_content(prompt)
        if is_blocked:
            return {
                'success': False,
                'error': f'차단된 콘텐츠: {block_reason}',
                'prompt': prompt
            }

        # 지리/위치 관련 프롬프트 검증 및 경고
        has_warnings, warnings = validate_prompt_geography(prompt)
        if has_warnings:
            print("[할루시네이션 경고] 지리/위치 관련 모호성 감지:")
            for w in warnings:
                print(f"  - {w}")

        # 프롬프트 강화 (할루시네이션 방지 지침 추가)
        original_prompt = prompt
        prompt = enhance_prompt(prompt)
        if prompt != original_prompt:
            print("[INFO] 할루시네이션 방지를 위해 프롬프트가 강화되었습니다.")

        # 파라미터 검증
        aspect_ratio = validate_aspect_ratio(aspect_ratio)
        image_size = validate_image_size(image_size)

        try:
            # aspect_ratio를 프롬프트에 포함 (API에서 직접 지원하지 않는 경우)
            aspect_instruction = f"[Image aspect ratio: {aspect_ratio}]"
            enhanced_prompt = f"{prompt}\n\n{aspect_instruction}"

            # 이미지 생성 요청
            # 참조: https://ai.google.dev/gemini-api/docs/image-generation
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=enhanced_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=['IMAGE'],
                )
            )

            # 응답에서 이미지 추출
            image_data = None
            text_response = None

            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    image_data = part.inline_data.data
                elif hasattr(part, 'text') and part.text:
                    text_response = part.text

            if not image_data:
                return {
                    'success': False,
                    'error': '이미지를 생성하지 못했습니다.',
                    'prompt': prompt,
                    'text_response': text_response
                }

            # 이미지 저장
            if save_image:
                if not filename:
                    filename = generate_filename('img_nanobanana', 'png')
                elif not filename.endswith('.png'):
                    # img_ 접두사 추가
                    if not filename.startswith('img_'):
                        filename = f"img_{filename}"
                    filename = f"{filename}.png"
                else:
                    # img_ 접두사 추가
                    if not filename.startswith('img_'):
                        filename = f"img_{filename[:-4]}.png"

                output_path = self.output_dir / filename

                # 바이트 데이터인 경우 직접 저장
                if isinstance(image_data, bytes):
                    with open(output_path, 'wb') as f:
                        f.write(image_data)
                # base64 문자열인 경우 디코딩 후 저장
                elif isinstance(image_data, str):
                    with open(output_path, 'wb') as f:
                        f.write(base64.b64decode(image_data))

                print(f"[OK] 이미지 저장 완료: {output_path}")

                # 옵시디언 삽입 코드 생성 (년월 서브폴더 포함)
                from datetime import datetime
                current_ym = datetime.now().strftime('%Y%m')
                obsidian_embed = f"![[images/{current_ym}/{filename}]]"

                return {
                    'success': True,
                    'path': str(output_path),
                    'filename': filename,
                    'prompt': prompt,
                    'obsidian_embed': obsidian_embed,
                    'text_response': text_response
                }
            else:
                return {
                    'success': True,
                    'image_data': image_data,
                    'prompt': prompt,
                    'text_response': text_response
                }

        except Exception as e:
            error_msg = str(e)
            print(f"[오류] 이미지 생성 실패: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'prompt': prompt
            }

    def generate_from_file(
        self,
        file_path: str,
        filename: Optional[str] = None,
        aspect_ratio: str = '1:1',
        image_size: str = '1K',
        max_prompt_length: int = 2000
    ) -> Dict[str, Any]:
        """
        텍스트 파일에서 프롬프트를 추출하여 이미지를 생성한다.

        Args:
            file_path: 텍스트 파일 경로 (.txt, .md, .csv 등)
            filename: 저장할 파일명 (기본: 자동 생성)
            aspect_ratio: 가로세로 비율
            image_size: 이미지 크기
            max_prompt_length: 최대 프롬프트 길이

        Returns:
            dict: generate_image()와 동일한 형식
        """
        file_path = Path(file_path)

        if not file_path.exists():
            return {
                'success': False,
                'error': f'파일을 찾을 수 없습니다: {file_path}',
                'source_file': str(file_path)
            }

        if not is_supported_text_file(str(file_path)):
            return {
                'success': False,
                'error': f'지원되지 않는 파일 형식입니다: {file_path.suffix}',
                'source_file': str(file_path)
            }

        try:
            # 파일에서 프롬프트 추출
            prompt = parse_prompt_from_file(str(file_path), max_prompt_length)

            if not prompt:
                return {
                    'success': False,
                    'error': '파일에서 프롬프트를 추출할 수 없습니다.',
                    'source_file': str(file_path)
                }

            # 파일명 생성 (원본 파일명 기반)
            if not filename:
                base_name = file_path.stem
                # 파일명에서 특수문자 제거
                safe_name = "".join(
                    c for c in base_name if c.isalnum() or c in ('_', '-')
                )
                filename = generate_filename(safe_name or 'nanobanana', 'png')

            # 이미지 생성
            result = self.generate_image(
                prompt=prompt,
                filename=filename,
                aspect_ratio=aspect_ratio,
                image_size=image_size
            )

            result['source_file'] = str(file_path)
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'source_file': str(file_path)
            }

    def generate_batch(
        self,
        prompts: List[str],
        filename_prefix: str = 'batch',
        aspect_ratio: str = '1:1',
        image_size: str = '1K'
    ) -> List[Dict[str, Any]]:
        """
        여러 프롬프트로 이미지를 일괄 생성한다.

        Args:
            prompts: 프롬프트 목록
            filename_prefix: 파일명 접두사
            aspect_ratio: 가로세로 비율
            image_size: 이미지 크기

        Returns:
            list: 각 이미지 생성 결과 목록
        """
        results = []

        for i, prompt in enumerate(prompts, 1):
            print(f"\n[{i}/{len(prompts)}] 이미지 생성 중...")
            filename = generate_filename(f"{filename_prefix}_{i:03d}", 'png')

            result = self.generate_image(
                prompt=prompt,
                filename=filename,
                aspect_ratio=aspect_ratio,
                image_size=image_size
            )
            results.append(result)

        # 요약 출력
        success_count = sum(1 for r in results if r.get('success'))
        print(f"\n=== 일괄 생성 완료: {success_count}/{len(prompts)} 성공 ===")

        return results


def main():
    """테스트용 메인 함수"""
    print("=== NanoBanana API 테스트 ===\n")

    try:
        client = NanoBananaClient()

        # 테스트 1: 간단한 한글 프롬프트
        print("\n--- 테스트 1: 한글 프롬프트 ---")
        result = client.generate_image(
            prompt="귀여운 고양이가 책상에서 노트북을 타이핑하는 모습, 디지털 아트 스타일",
            filename="test_korean_prompt"
        )

        if result['success']:
            print(f"성공! 저장 위치: {result['path']}")
            print(f"옵시디언 삽입: {result['obsidian_embed']}")
        else:
            print(f"실패: {result.get('error')}")

        # 테스트 2: 영어 프롬프트
        print("\n--- 테스트 2: 영어 프롬프트 ---")
        result = client.generate_image(
            prompt="A futuristic cityscape at sunset with flying cars, digital art style",
            filename="test_english_prompt"
        )

        if result['success']:
            print(f"성공! 저장 위치: {result['path']}")
        else:
            print(f"실패: {result.get('error')}")

    except Exception as e:
        print(f"테스트 실패: {e}")


if __name__ == '__main__':
    main()
