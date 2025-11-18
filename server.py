

import os
import json
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import google.generativeai as genai


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("⚠️  GEMINI_API_KEY / GOOGLE_API_KEY 가 .env 에 없습니다. (AI Studio 키 사용)")

genai.configure(api_key=GEMINI_API_KEY)

app = FastAPI(title="AI 여행 플래너 API (Gemini)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


SYSTEM = (
    "너는 여행 코스 플래너다. 사용자의 선호를 정리하고, 필요하면 1~2문장만 추가로 묻는다. "
    """반드시 아래 JSON만 출력해라(문장·설명·코드블록 금지, 유효 JSON).

{
  "type": "itinerary_v1",
  "summary": "<한 줄 요약>",
  "days": [
    {
      "label": "1일차",
      "date": "2025-11-20",
      "segments": [
        {
          "time": "09:00",
          "title": "경복궁",
          "kind": "명소",
          "move_text": "도보 8분 (600m)",   // 이동/거리 요약
          "rating": 4.8,                   // 없으면 생략
          "reviews": 2345,                 // 없으면 생략
          "note": ""                       // 선택
        }
      ]
    }
  ]
}

규칙:
- 키 이름과 구조는 그대로 유지. 불필요한 키 추가 금지.
- label은 '1일차/2일차' 등으로, date는 YYYY-MM-DD 가능하면 채움.
- move_text는 '도보/차량 n분 (x.xkm|xxxm)' 형식 선호.
- 한국어 값만 사용.
- 상단 summary는 1~2문장.
"""
)


PREFERRED = [
    "models/gemini-2.5-flash",         
    "models/gemini-flash-latest",
    "models/gemini-2.0-flash",
    "models/gemini-pro-latest",
    "models/gemini-2.5-pro",
]

def pick_available_model() -> str:
    """계정에서 generateContent 지원 모델 중 선호순으로 선택."""
    available = []
    for m in genai.list_models():
        caps = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in caps:
            available.append(m.name)

    for name in PREFERRED:
        if name in available:
            return name

    if available:
        return available[0]

    raise RuntimeError("사용 가능한 Gemini 모델을 찾지 못했습니다. 키/권한/지역을 확인하세요.")

MODEL_NAME = pick_available_model()
print(f"✅ Using Gemini model: {MODEL_NAME}")


class ChatIn(BaseModel):
    message: str
    history: Optional[List[dict]] = []  

def to_contents(history: Optional[List[dict]], user_message: str):
    contents = []
    if history:
        for h in history:
            role = "user" if h.get("role") == "user" else "model"
            text = h.get("content", "")
            if text:
                contents.append({"role": role, "parts": [{"text": text}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    return contents

@app.get("/")
def root():
    return {"ok": True, "model": MODEL_NAME, "hint": "POST /chat", "docs": "/docs", "health": "/health"}

@app.get("/health")
def health():
    return {"status": "up", "model": MODEL_NAME}

@app.get("/models")
def models():
    # 디버깅용: 사용 가능한 모델 목록 반환
    out = []
    for m in genai.list_models():
        caps = getattr(m, "supported_generation_methods", []) or []
        out.append({"name": m.name, "supports": caps})
    return out

@app.post("/chat")
def chat(inp: ChatIn):
    try:
        model = genai.GenerativeModel(model_name=MODEL_NAME, system_instruction=SYSTEM)
        resp = model.generate_content(to_contents(inp.history, inp.message))
        text = (resp.text or "").strip()

        try:
            return json.loads(text)
        except Exception:
            return {"type": "message", "text": text}

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Gemini 호출 실패: {e}")
