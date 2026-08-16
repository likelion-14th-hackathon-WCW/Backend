import json

from django.conf import settings
from openai import OpenAI

from ..models import Component, Item, Product

# OpenAI 클라이언트는 모듈이 처음 로드될 때 한 번만 생성해서 계속 재사용
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# OpenAI API 호출 분기
def recommend_components(keyword: str, exclude_combinations=None):
    """MAKE_01(노리개 제작) - 사용자가 입력한 키워드를 보고 매듭+장식 조합과 의미 설명을 추천.
    USE_MOCK_AI 설정에 따라 실제 API 호출 대신 가짜 데이터 반환 가능.
    """

    if settings.USE_MOCK_AI:
        return _mock_recommend(keyword)
    return _call_openai_recommend(keyword, exclude_combinations or []) # 실제 OpenAI 호출 로직


# mock OpenAI 호출할 경우
def _mock_recommend(keyword: str):
    """팀원 테스트용 고정 응답 - 실제 AI 호출 없이 항상 아래 같은 값을 반환"""
    return {
        "knot": 1,
        "decoration": 7,
        "reason": f"(Mock) '{keyword}'에 어울리는 조합으로 국화 매듭과 골드 타이거 장식을 추천합니다.",
        "suggested_title": "(Mock) 골든 국화 앙상블",
    }

# 실제 OpenAI 호출 로직
def _call_openai_recommend(keyword: str, exclude_combinations):
    # AI한테 골라달라고 할 후보 목록을 DB에서 가져옴
    # TODO: 지금은 가짜 더미 데이터 components_seed.py 사용
    # AI가 존재하지 않는 매듭을 지어내지 못하게, 실제 후보만 프롬프트에 넣음
    knots = Component.objects.filter(type="knot")
    decorations = Component.objects.filter(type="decoration")

    options_text = "매듭 목록:\n" + "\n".join(
        f"- id={c.id}, 이름={c.name}, 의미={c.meaning}" for c in knots
    )
    options_text += "\n\n장식 목록:\n" + "\n".join(
        f"- id={c.id}, 이름={c.name}, 의미={c.meaning}" for c in decorations
    )

    # 지금까지 추천했던 조합 전부 프롬프트에 넣어서, 어떤 것도 다시 안 나오게 함
    exclude_text = ""
    if exclude_combinations:
        combos = "\n".join(
            f"- 매듭 id={c.get('knot')}, 장식 id={c.get('decoration')}"
            for c in exclude_combinations
        )
        exclude_text = f"\n\n아래는 이미 추천했던 조합들입니다. 전부 제외하고 다른 조합으로 추천해주세요:\n{combos}"

    prompt = f"""사용자가 입력한 소망/키워드: "{keyword}"

아래 매듭과 장식 목록 중에서, 이 키워드와 가장 잘 어울리는 매듭 1개와 장식 1개를 골라주세요.
{options_text}
{exclude_text}

또한 이 조합에 어울리는 짧고 감성적인 제목도 하나 지어주세요 (예: "미드나잇 앰버 앙상블"처럼 15자 내외).

반드시 아래 JSON 형식으로만 답변하세요. 목록에 없는 id는 절대로 사용하지 마세요.
{{"knot": <매듭 id>, "decoration": <장식 id>, "reason": "<두 조합이 왜 이 소망과 어울리는지 2~3문장 설명>, "suggested_title": "<조합 제목>""}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],

        # json_object로 강제해서 무조건 파싱 가능한 JSON 형태로만 응답함
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)

    # 실제 DB에 존재하는 id인지 한 번 더 검증
    valid_knot_ids = {c.id for c in knots}
    valid_decoration_ids = {c.id for c in decorations}
    if result.get("knot") not in valid_knot_ids or result.get("decoration") not in valid_decoration_ids:
        raise ValueError("AI가 목록에 없는 컴포넌트를 추천했습니다.")

    return result

def recommend_products(item_id: int):
    """MAKE_02(커스텀 에디터) - 완성된 노리개 보고 어울리는 MCM 상품 추천."""
    if settings.USE_MOCK_AI:
        return _mock_products()
    return _call_openai_recommend_products(item_id) # 실제 OpenAI 호출 로직


def _mock_products():
    return [1, 2] # Product pk 목록 - fixtures에 넣어둔 상품 있으면 그 id로


def _call_openai_recommend_products(item_id: int):
    # select_related로 knot/tassel/decoration을 한 번의 쿼리로 같이 가져옴
    item = Item.objects.select_related("knot", "tassel", "decoration").get(pk=item_id)
    products = Product.objects.all()

    # 추천할 상품 자체가 없으면 AI 호출할 필요도 없이 바로 빈 배열 반환
    if not products.exists():
        return []

    products_text = "\n".join(f"- id={p.id}, 이름={p.name}, 가격={p.price}원" for p in products)

    prompt = f"""완성된 노리개 정보:
- 매듭: {item.knot.name} ({item.knot.color})
- 장식: {item.decoration.name} ({item.decoration.color})
- 술: {item.tassel.name}
- 선택 색상: {item.color}

아래 상품 목록 중에서, 이 노리개의 색상·분위기와 가장 잘 어울릴 만한 상품을 가장 잘 어울리는
순서대로 최대 3개까지 골라주세요 (배열의 첫 번째가 가장 잘 어울리는 상품입니다).
완벽하게 어울리는 게 없더라도, 색상 계열이나 전체적인 톤이 비슷한 것 중 가장 가까운
것들을 최소 1개 이상 골라주세요. 아래 목록에 상품이 하나라도 있다면 빈 배열을 반환하지 마세요.
{products_text}

반드시 아래 JSON 형식으로만 답변하세요. 목록에 없는 id는 절대 사용하지 마세요.
{{"product_ids": [<id>, <id>, ...]}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    result = json.loads(response.choices[0].message.content)
    print("AI 원본 응답:", result)  # 확인 후 지우기

    # AI가 준 id 중 실제로 존재하는 상품만 걸러서 반환
    valid_ids = {p.id for p in products}
    filtered = [pid for pid in result.get("product_ids", []) if pid in valid_ids]
    return filtered[:3]  # AI가 지시를 안 지켜도 최대 3개로 강제

# AI 추천 의미 설명 요약
def summarize_description(symbol_reason: str):
    """저장 시점에 symbol_reason(전통 의미 설명)을 짧게 요약해서 카드용 description으로 만듦"""
    if not symbol_reason:
        return None
    if settings.USE_MOCK_AI:
        return f"(Mock 요약) {symbol_reason[:30]}"
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"다음 설명을 한 문장으로, 카드에 어울리게 짧고 감성적으로 요약해줘 (30자 내외) 추가로 이모지는 넣지 말아줘: {symbol_reason}",
        }],
    )
    return response.choices[0].message.content.strip()