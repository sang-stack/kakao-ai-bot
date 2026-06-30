"""로컬에서 카카오 응답 테스트"""
import requests, json

def test(msg):
    res = requests.post("http://localhost:5000/kakao",
                        json={"userRequest": {"utterance": msg}})
    text = res.json()["template"]["outputs"][0]["simpleText"]["text"]
    print(f"\n[질문] {msg}\n[응답]\n{text}\n{'─'*50}")

test("안녕")
test("오늘 코스피 시황은?")
test("삼성전자 지금 매수해도 될까?")
