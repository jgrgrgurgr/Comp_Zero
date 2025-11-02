import os
import math
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from typing import Optional

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# --- API 키 설정 ---
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

# --- API URL 설정 ---
KAKAO_API_URL = "https://dapi.kakao.com/v2/local/search/address.json"

def get_coordinates(address: str) -> Optional[tuple[float, float]]:
    """
    카카오 주소 검색 API를 사용하여 주소를 위도, 경도 좌표로 변환합니다.
    """
    if not KAKAO_API_KEY:
        print("에러: .env 파일에 KAKAO_API_KEY가 설정되지 않았습니다.")
        return None
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address}
    try:
        response = requests.get(KAKAO_API_URL, headers=headers, params=params, timeout=5)
        response.raise_for_status()
        result = response.json()
        if not result.get("documents"):
            print(f"카카오 API 주소 변환 실패: '{address}'")
            return None
        doc = result["documents"][0]
        return (float(doc['y']), float(doc['x']))
    except requests.exceptions.RequestException as e:
        print(f"카카오 API 요청 중 에러 발생: {e}")
        return None
    except (KeyError, IndexError) as e:
        print(f"카카오 API 응답 처리 중 에러 발생: {e}")
        return None

def get_weather_data(lat: float, lon: float) -> dict:
    """
    (임시 조치) 기상청 API 연동 문제 해결 전까지 '맑음'을 반환합니다.
    """
    print("날씨 데이터: 임시로 '맑음'을 반환합니다.")
    return {"condition": "맑음"}

def get_accident_data(lat: float, lon: float) -> dict:
    """
    (임시 조치) TAAS API 연동 문제 해결 전까지 임시 데이터를 반환합니다.
    """
    print(f"사고 데이터 요청 (임시): ({lat}, {lon})")
    return {"accidents_last_year": 5}

def calculate_risk_score(start_address: str, end_address: str) -> dict:
    """
    출발지, 도착지 주소를 기반으로 경로의 위험도를 계산합니다.
    """
    start_coords = get_coordinates(start_address)
    end_coords = get_coordinates(end_address)

    if not start_coords or not end_coords:
        return {"error": "입력하신 주소를 좌표로 변환할 수 없습니다. 주소 형식을 확인해주세요."}

    lat, lon = start_coords
    weather_data = get_weather_data(lat, lon)
    accident_data = get_accident_data(lat, lon)

    # --- 임시 데이터 기반 위험도 계산 로직 ---
    risk_score = 50  # 기본 점수
    weather_condition = weather_data.get("condition")

    # 날씨에 따른 가중치
    if weather_condition in ['비', '비/눈', '눈', '소나기']:
        risk_score += 25
    elif weather_condition == '흐림':
        risk_score += 10

    # 과거 사고 데이터에 따른 가중치 (임시)
    risk_score += accident_data.get("accidents_last_year", 0) * 5

    risk_score = min(risk_score, 100)

    safety_message = f"분석 결과, 해당 경로의 위험 점수는 {risk_score}점입니다. (날씨: {weather_condition})"
    alternative_route_message = "현재 위치 기반 우회 경로는 아직 제안되지 않습니다. (구현 예정)"

    return {
        "risk_score": risk_score,
        "safety_message": safety_message,
        "alternative_route": alternative_route_message,
        "start_coords": start_coords,
        "end_coords": end_coords,
        "debug_info": f"출발지: {start_coords}, 도착지: {end_coords}"
    }