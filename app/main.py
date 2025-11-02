from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import uvicorn

# app 폴더 내의 서비스 모듈 import
from app import services

app = FastAPI()

# 정적 파일(CSS, JS) 및 템플릿(HTML) 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    메인 페이지(index.html)를 렌더링합니다.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/calculate-risk")
async def calculate_risk_endpoint(start_address: str = Form(...), end_address: str = Form(...)):
    """
    프론트엔드에서 받은 출발지/도착지 주소를 services.calculate_risk_score로 전달하고
    결과를 JSON 형태로 반환하는 API 엔드포인트입니다.
    """
    print(f"API 요청 수신: {start_address} -> {end_address}")
    
    # 핵심 로직은 services.py의 함수에 위임
    result = services.calculate_risk_score(start_address, end_address)

    # 주소 변환 실패 시 에러 메시지 반환
    if "error" in result:
        return JSONResponse(status_code=400, content={"message": result["error"]})

    return result

if __name__ == "__main__":
    # 개발 중에는 reload=True 옵션을 사용하면 코드 변경 시 서버가 자동 재시작되어 편리합니다.
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
