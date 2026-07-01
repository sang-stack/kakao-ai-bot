import os
import anthropic
from flask import Flask, request, jsonify

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
STOCK_SYSTEM = """당신은 5명의 전문 분석관으로 구성된 AI 투자분석팀입니다.
각 분석관의 의견을 아래 형식으로 반드시 출력하세요.

👤 시황분석가: (코스피/외국인 수급 1문장)
👤 종목분석가: (재무/실적/차트 1~2문장)  
👤 리스크분석가: (하락 리스크/손절기준 1문장)
👤 포트폴리오매니저: (비중/분산 1문장)
👤 수석애널리스트: (매수/매도/중립 + 1문장 종합의견)

총 6문장 이내. 한국어로 답하세요."""


SIMPLE_SYSTEM = "당신은 한국 주식 투자 분석 전문가입니다. 한국어로 2~3문장 이내로 간결하게 답하세요."


def ask(system, question):
    res = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=system,
        messages=[{"role": "user", "content": question}]
    )
    return res.content[0].text


def analyze(msg):
    # 인사 처리 (API 호출 없이 즉시 응답)
    if any(w in msg for w in ["안녕", "뭐해", "기능", "도움"]):
        return (
            "안녕하세요! 저는 10년 OK AI 주식 분석 챗봇입니다 📈\n\n"
            "이런 질문을 해보세요:\n"
            "• 삼성전자 분석해줘\n"
            "• 오늘 코스피 시황은?\n"
            "• 포트폴리오 어떻게 짜?\n"
            "• 지금 투자 리스크는?"
        )

    # 종목 관련 → 단일 호출로 통합 분석 (속도 최우선)
    if any(w in msg for w in ["종목", "주가", "매수", "매도", "목표가", "실적", "차트", "삼성", "sk", "현대", "카카오", "네이버", "lg"]):
        return ask(STOCK_SYSTEM, msg)

    # 시황 / 리스크 / 포트폴리오 / 기타 → 단일 호출
    return ask(SIMPLE_SYSTEM, msg)


# ── 카카오 Webhook ──────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "10년OK"})

@app.route("/kakao", methods=["POST"])
def kakao():
    try:
        body = request.get_json(force=True)
        msg  = body.get("userRequest", {}).get("utterance", "").strip()
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
