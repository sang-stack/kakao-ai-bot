import os
import anthropic
from flask import Flask, request, jsonify

app = Flask(__name__)
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# ── 5개 에이전트 역할 정의 ──────────────────────────────
AGENTS = {
    "market": "당신은 한국 주식시장 시황 분석 전문가입니다. 코스피/코스닥 흐름, 외국인·기관 수급, 거시경제를 분석합니다. 한국어로 3문장 이내로 답하세요.",
    "stock":  "당신은 한국 개별 종목 전문가입니다. 재무제표, 실적, 밸류에이션, 차트를 분석합니다. 한국어로 3문장 이내로 답하세요.",
    "risk":   "당신은 투자 리스크 관리 전문가입니다. 하락 리스크, 변동성, 손절 기준을 분석합니다. 한국어로 3문장 이내로 답하세요.",
    "port":   "당신은 포트폴리오 구성 전문가입니다. 자산 배분, 분산투자, 리밸런싱을 제안합니다. 한국어로 3문장 이내로 답하세요.",
    "final":  "당신은 투자 보고서 전문가입니다. 여러 분석을 종합해 매수/매도/중립 의견과 이유를 명확히 작성합니다. 한국어로 답하세요.",
}

def ask(role_key, question, context=""):
    content = f"[참고]\n{context}\n\n[질문]\n{question}" if context else question
    res = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=AGENTS[role_key],
        messages=[{"role": "user", "content": content}]
    )
    return res.content[0].text

def analyze(msg):
    # 인사 처리
    if any(w in msg for w in ["안녕", "뭐해", "기능", "도움"]):
        return (
            "안녕하세요! 저는 10년 OK AI 주식 분석 챗봇입니다 📈\n\n"
            "이런 질문을 해보세요:\n"
            "• 삼성전자 분석해줘\n"
            "• 오늘 코스피 시황은?\n"
            "• 포트폴리오 어떻게 짜?\n"
            "• 지금 투자 리스크는?"
        )

    # 종목 관련 → 멀티에이전트 풀 분석
    if any(w in msg for w in ["종목", "주가", "매수", "매도", "목표가", "실적", "차트", "삼성", "sk", "현대", "카카오", "네이버", "lg"]):
        m = ask("market", msg)
        s = ask("stock",  msg, context=m)
        r = ask("risk",   msg, context=f"{m}\n{s}")
        f = ask("final",  msg, context=f"시황:{m}\n종목:{s}\n리스크:{r}")
        return f"📊 AI 멀티에이전트 분석\n\n🌍 시황\n{m}\n\n📈 종목\n{s}\n\n⚠️ 리스크\n{r}\n\n✅ 최종의견\n{f}"

    # 시황
    if any(w in msg for w in ["시황", "코스피", "코스닥", "지수", "외국인", "기관", "시장"]):
        return f"🌍 시황 분석\n\n{ask('market', msg)}"

    # 리스크
    if any(w in msg for w in ["리스크", "손절", "위험", "변동성"]):
        return f"⚠️ 리스크 분석\n\n{ask('risk', msg)}"

    # 포트폴리오
    if any(w in msg for w in ["포트폴리오", "배분", "비중", "분산"]):
        return f"💼 포트폴리오\n\n{ask('port', msg)}"

    # 기타
    return f"🤖 AI 분석\n\n{ask('final', msg)}"


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
