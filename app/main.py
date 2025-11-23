from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv # Added
import os # Added

load_dotenv() # Added

# app 폴더 내의 서비스 모듈 import
from app import services

app = FastAPI()

# 정적 파일(CSS, JS) 및 템플릿(HTML) 설정
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- Pydantic 모델 정의 ---
class RiskReport(BaseModel):
    address: str
    description: str

# --- API 엔드포인트 ---

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """
    메인 페이지(index.html)를 렌더링하고, 지도 API 키를 전달합니다.
    """
    kakao_js_key = os.getenv("KAKAO_JS_KEY", "")
    return templates.TemplateResponse("index.html", {"request": request, "kakao_js_key": kakao_js_key})

@app.post("/calculate-risk")
async def calculate_risk_endpoint(start_address: str = Form(...), end_address: str = Form(...)):
    """
    프론트엔드에서 받은 출발지/도착지 주소를 services.calculate_route_risk로 전달하고
    결과를 JSON 형태로 반환하는 API 엔드포인트입니다.
    """
    print(f"API 요청 수신: {start_address} -> {end_address}")
    
    start_coords = services.get_coords_from_address(start_address)
    end_coords = services.get_coords_from_address(end_address)

    if not start_coords:
        return JSONResponse(status_code=400, content={"message": f"출발지 주소 '{start_address}'를 좌표로 변환할 수 없습니다."})
    if not end_coords:
        return JSONResponse(status_code=400, content={"message": f"도착지 주소 '{end_address}'를 좌표로 변환할 수 없습니다."})

    result = services.calculate_route_risk(
        (start_coords['latitude'], start_coords['longitude']),
        (end_coords['latitude'], end_coords['longitude'])
    )
    # Check for 'status' field from calculate_route_risk
    if result.get("status") == "error":
        return JSONResponse(status_code=400, content={"message": result.get("error", "경로 위험도 계산 중 알 수 없는 오류 발생")})
    
    # Also keep the existing 'error' check for backward compatibility or other error types
    if "error" in result:
        return JSONResponse(status_code=400, content={"message": result["error"]})
    
    return result

@app.get("/reports", response_class=HTMLResponse)
async def read_reports_page(request: Request):
    """
    사용자 제보를 확인하고 새로 제보할 수 있는 페이지를 렌더링합니다.
    """
    return templates.TemplateResponse("reports.html", {"request": request})


@app.get("/analysis", response_class=HTMLResponse)
async def read_analysis_page(request: Request):
    """
    데이터 분석 리포트 페이지(analysis.html)를 렌더링합니다.
    """
    return templates.TemplateResponse("analysis.html", {"request": request})


@app.get("/api/reports")
async def get_all_reports():
    """
    저장된 모든 위험 정보 제보를 JSON 형태로 반환합니다.
    """
    return services.get_all_risk_reports()

@app.post("/report-risk")
async def report_risk_endpoint(report: RiskReport):
    """
    사용자로부터 실시간 위험 정보를 제보받아 저장합니다.
    """
    print(f"위험 정보 제보 수신: {report.address} - {report.description}")
    result = services.save_risk_report(report.dict())
    if "error" in result:
        return JSONResponse(status_code=400, content={"message": result["error"]})
    return result

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
