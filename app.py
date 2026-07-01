import os
import re
import json
import anthropic
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── 종목코드 매핑 ──────────────────────────────────────
STOCK_CODES = {
    "삼성전자": "005930",
    "sk하이닉스": "000660", "하이닉스": "000660",
    "lg에너지솔루션": "373220",
    "삼성바이오로직스": "207940",
    "현대차": "005380", "현대자동차": "005380",
    "기아": "000270",
    "카카오": "035720",
    "네이버": "035420",
    "셀트리온": "068270",
    "포스코": "005490", "포스코홀딩스": "005490",
    "삼성sdi": "006400",
    "lg화학": "051910",
    "kb금융": "105560",
    "신한지주": "055550",
    "하나금융지주": "086790",
    "카카오뱅크": "323410",
    "크래프톤": "259960",
    "현대모비스": "012330",
    "lg전자": "066570",
    "한화에어로스페이스": "012450", "한화": "012450",
}

def get_stock_price(code):
    """Yahoo Finance API로 실시간 주가 조회"""
    try:
        ticker = f"{code}.KS"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
        }
       res = requests.get(url, headers=headers, timeout=2)
        if res.status_code == 200:
            data = res.json()
            meta = data["chart"]["result"][0]["meta"]
            price = int(meta.get("regularMarketPrice", 0))
            prev  = int(meta.get("previousClose", price))
            diff  = price - prev
            pct   = round(diff / prev * 100, 2) if prev else 0
            sign  = "▲" if diff >= 0 else "▼"
            return {
                "price":  f"{price:,}",
                "change": f"{sign}{abs(diff):,}원 ({sign}{abs(pct)}%)",
                "code":   code
            }
    except Exception as e:
        print(f"Yahoo 오류: {e}")

    # Yahoo 실패 시 네이버 금융 시도
    try:
        url = f"https://finance.naver.com/item/main.naver?code={code}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = "euc-kr"
        html = res.text

        # 현재가 패턴 (여러 방법 시도)
        for pattern in [
            r'"_nowVal"[^>]*>([0-9,]+)<',
            r'class="no_today"[^>]*>.*?<em[^>]*>([0-9,]+)</em>',
            r'stockEndPrice["\s]*:["\s]*([0-9,]+)',
        ]:
            m = re.search(pattern, html, re.DOTALL)
            if m:
                price = m.group(1)
                return {"price": price, "change": "N/A", "code": code}
    except Exception as e:
        print(f"네이버 오류: {e}")

    return None


def find_stock(msg):
    msg_lower = msg.lower().replace(" ", "")
    for name, code in STOCK_CODES.items():
        if name.lower().replace(" ", "") in msg_lower:
            return name, code
    m = re.search(r'\b(\d{6})\b', msg)
    if m:
        return m.group(1), m.group(1)
    return None, None


# ── 시스템 프롬프트 ────────────────────────────────────
STOCK_SYSTEM = """당신은 5명의 전문 분석관으로 구성된 AI 투자분석팀입니다.
반드시 제공된 실시간 주가 데이터를 기반으로 분석하세요.
절대로 제공된 현재가와 다른 주가를 언급하지 마세요.

형식:
# {종목명}({종목코드}) 투자분석

👤 시황분석가: (코스피/외국인 수급 1문장)
👤 종목분석가: (현재가 {현재가}원 기준 재무/차트 분석 1~2문장)
👤 리스크분석가: (손절가 포함 하락 리스크 1문장)
👤 포트폴리오매니저: (비중/분산 1문장)
👤 수석애널리스트: (매수/매도/중립 + 목표가 1문장)

총 7문장 이내. 한국어로 답하세요."""

SIMPLE_SYSTEM = "당신은 한국 주식 투자 분석 전문가입니다. 한국어로 2~3문장 이내로 간결하게 답하세요."


def ask(system, question):
    res = requests.get(url, headers=headers, timeout=2)
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=system,
        messages=[{"role": "user", "content": question}]
    )
    return res.content[0].text


def analyze(msg):
    if any(w in msg for w in ["안녕", "뭐해", "기능", "도움"]):
        return (
            "안녕하세요! 저는 10년 OK AI 주식 분석 챗봇입니다 📈\n\n"
            "이런 질문을 해보세요:\n"
            "• 삼성전자 분석해줘\n"
            "• 카카오 지금 사도 돼?\n"
            "• 오늘 코스피 시황은?\n"
            "• 현대차 목표가 알려줘"
        )

    stock_keywords = ["종목", "주가", "매수", "매도", "목표가", "실적", "차트", "분석", "사도", "팔아", "어때"]
    name, code = find_stock(msg)

    if name or any(w in msg for w in stock_keywords):
        if code:
            data = get_stock_price(code)
            if data and data["price"] != "N/A":
                context = (
                    f"[실시간 데이터 - 반드시 이 데이터 기준으로 분석할 것]\n"
                    f"종목: {name}({code})\n"
                    f"현재가: {data['price']}원\n"
                    f"등락: {data['change']}\n\n"
                    f"[사용자 질문]\n{msg}"
                )
                print(f"실시간 데이터 조회 성공: {name} {data['price']}원")
            else:
                context = msg
                print(f"실시간 데이터 조회 실패: {code}")
        else:
            context = msg
        return ask(STOCK_SYSTEM, context)

    return ask(SIMPLE_SYSTEM, msg)


# ── 카카오 Webhook ─────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "10년OK"})

@app.route("/kakao", methods=["POST"])
def kakao():
    try:
        body = request.get_json(force=True)
        msg = body.get("userRequest", {}).get("utterance", "").strip()
        if not msg:
            return reply("메시지를 입력해주세요.")
        answer = analyze(msg)
        if len(answer) > 1000:
            answer = answer[:990] + "...\n(요약본입니다)"
        return reply(answer)
    except Exception as e:
        print(f"ERROR: {e}")
        return reply("오류가 발생했습니다. 잠시 후 다시 시도해주세요.")

def reply(text):
    return jsonify({
        "version": "2.0",
        "template": {"outputs": [{"simpleText": {"text": text}}]}
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
