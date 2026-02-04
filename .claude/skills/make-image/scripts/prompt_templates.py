# -*- coding: utf-8 -*-
"""
make-image 스킬 프롬프트 템플릿 및 할루시네이션 방지 모듈

이 모듈은 이미지 생성 시 할루시네이션을 방지하기 위한 가이드라인,
프롬프트 검증, 템플릿 시스템을 제공한다.

주요 기능:
- 지리/위치 관련 프롬프트 모호성 감지
- 프롬프트 자동 강화 (명확화 지침 추가)
- 카테고리별 프롬프트 템플릿
"""

from typing import Dict, List, Tuple, Optional


# ========================================
# 할루시네이션 위험 키워드 및 경고
# ========================================

# 지리/위치 관련 모호한 키워드와 경고 메시지
GEOGRAPHY_RISK_KEYWORDS = {
    # 한글 키워드
    '한국': '경고: "한국"은 남한/북한 구분이 모호합니다. "대한민국" 또는 "South Korea"를 사용하세요.',
    '한반도': '경고: "한반도" 전체를 그릴 경우 남/북 경계를 명확히 지정하세요.',
    '서울': '참고: 서울 포함 시 "Seoul, capital of South Korea"로 명시하면 더 정확합니다.',
    '평양': '참고: 평양 포함 시 "Pyongyang, capital of North Korea"로 명시하면 더 정확합니다.',
    '지도': '경고: 지도 요청 시 남한/북한 범위를 명확히 지정하세요.',

    # 영어 키워드
    'korea': '경고: "Korea"는 남한/북한 구분이 모호합니다. "South Korea" 또는 "North Korea"를 명시하세요.',
    'korean peninsula': '경고: 한반도 전체를 그릴 경우 남/북 경계를 명확히 표현하세요.',
    'map': '참고: 지도 요청 시 지역 범위를 명확히 지정하면 더 정확합니다.',
}

# 위험 콘텐츠 키워드 (생성 차단 필요)
BLOCKED_KEYWORDS = [
    # 여기에 차단할 키워드 추가 가능
]


# ========================================
# 프롬프트 검증 함수
# ========================================

def validate_prompt_geography(prompt: str) -> Tuple[bool, List[str]]:
    """
    지리 관련 프롬프트의 모호성을 검사한다.

    Args:
        prompt: 검사할 프롬프트

    Returns:
        tuple[bool, list[str]]: (경고 존재 여부, 경고 메시지 목록)
    """
    warnings = []
    prompt_lower = prompt.lower()

    for keyword, warning in GEOGRAPHY_RISK_KEYWORDS.items():
        if keyword.lower() in prompt_lower:
            warnings.append(warning)

    # 중복 경고 제거
    warnings = list(dict.fromkeys(warnings))

    return len(warnings) > 0, warnings


def has_blocked_content(prompt: str) -> Tuple[bool, Optional[str]]:
    """
    차단된 콘텐츠가 포함되어 있는지 검사한다.

    Args:
        prompt: 검사할 프롬프트

    Returns:
        tuple[bool, Optional[str]]: (차단 여부, 차단 이유)
    """
    prompt_lower = prompt.lower()

    for keyword in BLOCKED_KEYWORDS:
        if keyword.lower() in prompt_lower:
            return True, f"차단된 키워드 포함: {keyword}"

    return False, None


# ========================================
# 프롬프트 강화 함수
# ========================================

def enhance_prompt(prompt: str, context: str = 'general') -> str:
    """
    프롬프트에 할루시네이션 방지 지침을 추가한다.

    지리/위치 관련 키워드가 감지되면 명확화 지침을 자동 추가한다.

    Args:
        prompt: 원본 프롬프트
        context: 컨텍스트 ('general', 'map', 'business', 'concept')

    Returns:
        str: 강화된 프롬프트
    """
    prompt_lower = prompt.lower()
    enhancements = []

    # 한국/Korea 관련 키워드가 있으면 명확화 지침 추가
    korea_keywords = ['korea', '한국', '한반도', 'korean']
    has_korea_reference = any(kw in prompt_lower for kw in korea_keywords)

    if has_korea_reference:
        # 남한만 언급하고 싶은 경우 체크
        south_only = any(kw in prompt_lower for kw in ['south korea', '대한민국', '남한'])
        north_only = any(kw in prompt_lower for kw in ['north korea', '북한', '조선민주주의'])

        if not south_only and not north_only:
            enhancements.append(
                "[CLARIFICATION: If this refers to Korea, please clearly distinguish between "
                "South Korea (Republic of Korea) and North Korea (DPRK). "
                "Do NOT merge or confuse the two regions.]"
            )

    # 지도 관련 키워드
    map_keywords = ['map', '지도', 'geography', '영토', 'territory']
    has_map_reference = any(kw in prompt_lower for kw in map_keywords)

    if has_map_reference and has_korea_reference:
        enhancements.append(
            "[MAP INSTRUCTION: When drawing a map of Korea, clearly mark the DMZ "
            "(Demilitarized Zone) boundary between South and North Korea.]"
        )

    # 강화 지침 추가
    if enhancements:
        return prompt + "\n\n" + "\n".join(enhancements)

    return prompt


def enhance_prompt_for_comparison(prompt: str, entity_a: str, entity_b: str) -> str:
    """
    비교 시각화를 위한 프롬프트를 강화한다.

    Args:
        prompt: 원본 프롬프트
        entity_a: 비교 대상 A (예: "South Korea")
        entity_b: 비교 대상 B (예: "North Korea")

    Returns:
        str: 강화된 프롬프트
    """
    comparison_instruction = f"""
[COMPARISON VISUALIZATION INSTRUCTION]
- This is a comparison between {entity_a} and {entity_b}.
- Clearly distinguish and label both entities.
- Use consistent visual treatment for fair comparison.
- Do NOT confuse or merge the two entities.
"""
    return prompt + "\n" + comparison_instruction


# ========================================
# 프롬프트 템플릿
# ========================================

PROMPT_TEMPLATES = {
    # 남북한 비교 관련 템플릿
    'korea_comparison_cover': """
Artistic visualization comparing South Korea and North Korea.
Style: {style}
Key visual elements: Korean Peninsula divided at DMZ, distinct visual treatment for each nation
Color scheme: {color_scheme}
IMPORTANT: Clearly show the division at the 38th parallel / DMZ.
South Korea (Republic of Korea) should be on the southern part.
North Korea (DPRK) should be on the northern part.
Do NOT swap or confuse the positions.
""",

    'korea_south_only': """
Visualization of South Korea (Republic of Korea) ONLY.
DO NOT include North Korea (DPRK).
Show only the southern portion of the Korean Peninsula below the DMZ.
{additional_details}
Style: {style}
""",

    'korea_north_only': """
Visualization of North Korea (DPRK) ONLY.
DO NOT include South Korea (Republic of Korea).
Show only the northern portion of the Korean Peninsula above the DMZ.
{additional_details}
Style: {style}
""",

    # 비즈니스/보고서 템플릿
    'business_report_cover': """
Professional business report cover illustration.
Topic: {topic}
Style: {style}, clean, corporate, minimalist
Color scheme: {color_scheme}
Key elements: {elements}
""",

    'concept_visualization': """
Visual representation of the concept: {concept}
Style: {style}
Key elements: {elements}
Mood/atmosphere: {mood}
Color scheme: {color_scheme}
""",

    # 인프라/통계 시각화
    'infrastructure_comparison': """
Infrastructure comparison visualization.
Comparing: {entity_a} vs {entity_b}
Metrics: {metrics}
Style: {style}, infographic-style, data-driven
Use clear visual indicators for comparison.
""",

    'statistics_visualization': """
Statistical data visualization concept.
Topic: {topic}
Key metrics: {metrics}
Style: {style}, clean, professional
Include visual metaphors for numbers and trends.
""",
}


def get_template(template_name: str) -> Optional[str]:
    """
    템플릿 이름으로 프롬프트 템플릿을 가져온다.

    Args:
        template_name: 템플릿 이름

    Returns:
        Optional[str]: 템플릿 문자열 또는 None
    """
    return PROMPT_TEMPLATES.get(template_name)


def fill_template(template_name: str, **kwargs) -> str:
    """
    템플릿에 값을 채워서 프롬프트를 생성한다.

    Args:
        template_name: 템플릿 이름
        **kwargs: 템플릿 변수들

    Returns:
        str: 완성된 프롬프트

    Raises:
        ValueError: 템플릿을 찾을 수 없을 때
    """
    template = PROMPT_TEMPLATES.get(template_name)
    if not template:
        raise ValueError(f"템플릿을 찾을 수 없습니다: {template_name}")

    # 기본값 설정
    defaults = {
        'style': 'modern, minimalist, professional',
        'color_scheme': 'blue and white',
        'mood': 'professional and informative',
        'elements': '',
        'additional_details': '',
    }

    # 기본값과 사용자 입력 병합
    params = {**defaults, **kwargs}

    try:
        return template.format(**params)
    except KeyError as e:
        raise ValueError(f"템플릿에 필요한 변수가 누락되었습니다: {e}")


# ========================================
# 남북한 비교 보고서 전용 프롬프트 생성기
# ========================================

def create_nk_sk_comparison_prompt(
    image_type: str,
    style: str = 'modern digital art, infographic style',
    color_scheme: str = 'blue (South Korea) and red/magenta (North Korea)'
) -> str:
    """
    남북한 비교 보고서용 이미지 프롬프트를 생성한다.

    Args:
        image_type: 이미지 유형 ('cover', 'population', 'economy', 'infrastructure', 'social', 'conclusion')
        style: 스타일
        color_scheme: 색상 스킴

    Returns:
        str: 생성된 프롬프트
    """
    prompts = {
        'cover': f"""
A professional comparison visualization of South Korea and North Korea for a report cover.
The Korean Peninsula is shown with a clear division at the DMZ (38th parallel).
South Korea (Republic of Korea) on the bottom/south with modern cityscape elements.
North Korea (DPRK) on the top/north with distinct visual treatment.
IMPORTANT: Do NOT confuse South and North positions.
South = bottom of peninsula (Seoul, Busan).
North = top of peninsula (Pyongyang).
Style: {style}
Color scheme: {color_scheme}
""",

        'population': f"""
Conceptual visualization of population demographics comparison.
Abstract representation showing population density and distribution.
Two distinct sections representing different population characteristics.
Style: {style}, data visualization concept
Color scheme: {color_scheme}
No specific map required - focus on demographic concepts.
""",

        'economy': f"""
Economic disparity visualization concept.
Abstract representation of GDP, income levels, and economic development gap.
Visual metaphor: two contrasting economic environments.
Modern vs developing economy visual elements.
Style: {style}
Color scheme: {color_scheme}
No specific map - focus on economic concept visualization.
""",

        'infrastructure': f"""
Infrastructure comparison concept visualization.
Transportation networks, energy systems, and urban development.
Two contrasting infrastructure development levels.
Elements: railways, roads, power grids, buildings.
Style: {style}
Color scheme: {color_scheme}
""",

        'social': f"""
Social indicators comparison visualization.
Healthcare, education, and quality of life concepts.
Abstract representation of social development indicators.
Elements: medical symbols, education symbols, life quality indicators.
Style: {style}
Color scheme: {color_scheme}
""",

        'conclusion': f"""
Future vision of the Korean Peninsula.
Hopeful, forward-looking visualization.
Concept of cooperation, bridge-building, and unified potential.
Style: {style}, optimistic, professional
Color scheme: {color_scheme}, with hopeful warm tones
""",
    }

    prompt = prompts.get(image_type, prompts['cover'])

    # 항상 명확화 지침 추가
    clarification = """

[CRITICAL INSTRUCTION]
- South Korea (Republic of Korea) = SOUTHERN part of Korean Peninsula
- North Korea (DPRK) = NORTHERN part of Korean Peninsula
- Never confuse or swap their geographic positions
- The DMZ (Demilitarized Zone) separates them at roughly 38th parallel
"""

    return prompt + clarification


# ========================================
# 메인 (테스트용)
# ========================================

if __name__ == '__main__':
    print("=== prompt_templates.py 테스트 ===\n")

    # 테스트 1: 지리 검증
    print("--- 테스트 1: 지리 프롬프트 검증 ---")
    test_prompts = [
        "한국 지도를 그려줘",
        "South Korea and North Korea comparison",
        "A beautiful landscape",
        "서울 도시 스카이라인",
    ]

    for prompt in test_prompts:
        has_warning, warnings = validate_prompt_geography(prompt)
        print(f"\n프롬프트: {prompt}")
        print(f"  경고 여부: {has_warning}")
        if warnings:
            for w in warnings:
                print(f"  - {w}")

    # 테스트 2: 프롬프트 강화
    print("\n--- 테스트 2: 프롬프트 강화 ---")
    original = "한국 경제 시각화"
    enhanced = enhance_prompt(original)
    print(f"원본: {original}")
    print(f"강화: {enhanced}")

    # 테스트 3: 템플릿 사용
    print("\n--- 테스트 3: 템플릿 사용 ---")
    filled = fill_template(
        'business_report_cover',
        topic='2026 AI Strategy',
        elements='AI icons, data flows, digital transformation'
    )
    print(f"템플릿 결과:\n{filled}")

    # 테스트 4: 남북한 비교 프롬프트
    print("\n--- 테스트 4: 남북한 비교 프롬프트 ---")
    nk_sk_prompt = create_nk_sk_comparison_prompt('cover')
    print(f"커버 프롬프트:\n{nk_sk_prompt}")
