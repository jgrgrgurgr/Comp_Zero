"""
타협제로 - 서비스 로직
CSV 데이터 기반 위험도 계산
"""
import requests
from typing import Dict, Optional, List
from datetime import datetime
import os
import json # Added for JSON file operations
from .accident_data_manager import accident_manager

# 환경 변수에서 API 키 가져오기
KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')

# 위험 제보 파일 경로
RISK_REPORTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'risk_reports.json')



def get_coords_from_address(address: str) -> Optional[Dict]:
    """
    Kakao Local API를 통해 주소를 좌표로 변환
    """
    if not KAKAO_API_KEY:
        print("⚠️ KAKAO_API_KEY가 설정되지 않았습니다.")
        return None
    
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"query": address}
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('documents'):
                first_doc = data['documents'][0]
                return {
                    'latitude': float(first_doc.get('y', 0)),
                    'longitude': float(first_doc.get('x', 0))
                }
    except Exception as e:
        print(f"❌ 주소 → 좌표 변환 실패: {e}")
    
    return None


def get_address_from_coords(lat: float, lon: float) -> Optional[Dict]:
    """
    Kakao Local API를 통해 좌표를 주소로 변환
    """
    if not KAKAO_API_KEY:
        print("⚠️ KAKAO_API_KEY가 설정되지 않았습니다.")
        return None
    
    try:
        url = "https://dapi.kakao.com/v2/local/geo/coord2address.json"
        headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
        params = {"x": lon, "y": lat}
        
        response = requests.get(url, headers=headers, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('documents'):
                address_info = data['documents'][0].get('address', {})
                return {
                    'region_1depth_name': address_info.get('region_1depth_name', ''),
                    'region_2depth_name': address_info.get('region_2depth_name', ''),
                    'region_3depth_name': address_info.get('region_3depth_name', '')
                }
    except Exception as e:
        print(f"❌ 좌표 변환 실패: {e}")
    
    return None


def get_weather_data(lat: float, lon: float) -> Dict:
    """
    기상청 API를 통해 날씨 정보 조회
    실제 API 연동 또는 기본값 반환
    """
    # TODO: 실제 기상청 API 연동
    # 현재는 시간대 기반 간단한 추정
    hour = datetime.now().hour
    
    # 간단한 날씨 추정 (실제로는 API 사용)
    condition = "맑음"
    risk_factor = 0
    
    if 6 <= hour <= 18:
        condition = "맑음"
        risk_factor = 0
    else:
        condition = "야간"
        risk_factor = 5
    
    # 임시로 비/눈/안개 조건 추가 (테스트용)
    # if datetime.now().minute % 3 == 0:
    #     condition = "비"
    #     risk_factor = 10
    # elif datetime.now().minute % 5 == 0:
    #     condition = "눈"
    #     risk_factor = 15
    # elif datetime.now().minute % 7 == 0:
    #     condition = "안개"
    #     risk_factor = 12
    
    return {
        "condition": condition,
        "risk_factor": risk_factor,
        "temperature": 15,  # 기본값
        "humidity": 60,     # 기본값
        "source": "estimated"
    }


def get_accident_data(lat: float, lon: float) -> Dict:
    """
    좌표 기반 사고 위험도 조회 (CSV 데이터 활용)
    기존 API 방식 대신 CSV 데이터 사용
    """
    # 1. 좌표 → 주소 변환
    address_info = get_address_from_coords(lat, lon)
    
    if not address_info:
        return {
            "total_risk": 5,
            "region": "주소 변환 실패",
            "details": [],
            "source": "fallback",
            "error": "좌표를 주소로 변환할 수 없습니다."
        }
    
    sido_name = address_info.get('region_1depth_name', '')
    gugun_name = address_info.get('region_2depth_name', '')
    dong_name = address_info.get('region_3depth_name', '')
    
    # 2. CSV 데이터에서 지역별 위험도 조회
    # accident_manager의 get_region_risk는 이미 가중치를 포함한 total_risk를 반환
    risk_data_from_csv = accident_manager.get_region_risk(sido_name, gugun_name, dong_name)
    base_risk = risk_data_from_csv['total_risk']
    
    # 3. 시간대 가중치 적용
    current_hour = datetime.now().hour
    time_weighted_risk = accident_manager.apply_time_weight(base_risk, current_hour)
    
    # 4. 날씨 가중치 적용
    weather = get_weather_data(lat, lon)
    weather_weighted_risk = accident_manager.apply_weather_weight(
        time_weighted_risk, 
        weather.get('condition', '맑음')
    )
    
    # 5. 최종 위험도 (최대 100점)
    final_risk = min(round(weather_weighted_risk, 1), 100.0)
    
    # 6. 결과 반환
    return {
        "total_risk": final_risk,
        "base_risk": base_risk,
        "time_weighted_risk": time_weighted_risk,
        "weather_weighted_risk": weather_weighted_risk,
        "region": risk_data_from_csv['region'],
        "match_level": risk_data_from_csv.get('match_level', 'unknown'),
        "details": [{
            "location": risk_data_from_csv['region'],
            "accident_count": risk_data_from_csv.get('accident_count', 0),
            "death_count": risk_data_from_csv.get('death_count', 0),
            "serious_injury": risk_data_from_csv.get('serious_injury', 0),
            "minor_injury": risk_data_from_csv.get('minor_injury', 0),
            "note": f"CSV 데이터 기반 ({risk_data_from_csv.get('match_level', 'unknown')})"
        }],
        "weather": weather,
        "time_factor": {
            "current_hour": current_hour,
            "is_rush_hour": (7 <= current_hour <= 9) or (18 <= current_hour <= 20),
            "is_night": current_hour >= 22 or current_hour <= 6
        },
        "source": "csv_data",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def calculate_route_risk(start_coords: tuple, end_coords: tuple, waypoints: list = None) -> Dict:
    """
    경로 전체의 위험도 계산
    
    Args:
        start_coords: (lat, lon) 출발지 좌표
        end_coords: (lat, lon) 도착지 좌표
        waypoints: [(lat, lon), ...] 경유지 좌표 리스트
    
    Returns:
        Dict: 경로 위험도 정보
    """
    all_points = [start_coords]
    if waypoints:
        all_points.extend(waypoints)
    all_points.append(end_coords)
    
    route_risks = []
    total_risk = 0
    
    # 각 지점의 위험도 계산
    for i, (lat, lon) in enumerate(all_points):
        point_risk = get_accident_data(lat, lon)
        
        route_risks.append({
            "point_index": i,
            "lat": lat,
            "lon": lon,
            "risk_score": point_risk['total_risk'],
            "region": point_risk['region'],
            "details": point_risk['details'][0] if point_risk['details'] else {}
        })
        
        total_risk += point_risk['total_risk']
    
    # 평균 위험도 계산
    avg_risk = total_risk / len(all_points) if all_points else 0
    
    # 위험 등급 판정 (100점 기준)
    if avg_risk < 20:
        risk_level = "안전"
        risk_color = "green"
    elif avg_risk < 40:
        risk_level = "보통"
        risk_color = "yellow"
    elif avg_risk < 60:
        risk_level = "주의"
        risk_color = "orange"
    else:
        risk_level = "위험"
        risk_color = "red"
    
    debug_info_str = f"평균 위험도: {round(avg_risk, 1)}, 총 위험도 합계: {total_risk}, 타임스탬프: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

    return {
        "status": "success", # Added status field
        "route_risk_score": round(avg_risk, 1),
        "risk_level": risk_level,
        "risk_color": risk_color,
        "total_risk": total_risk,
        "point_count": len(all_points),
        "route_risks": route_risks,
        "recommendation": get_safety_recommendation(avg_risk),
        "alternative_route": "대안 경로 기능은 아직 구현되지 않았습니다. (MVP)", # Placeholder
        "debug_info": debug_info_str # Changed to string
    }


def get_safety_recommendation(risk_score: float) -> str:
    """위험도에 따른 안전 권고사항"""
    if risk_score < 20:
        return "안전한 경로입니다. 즐거운 보행 되세요."
    elif risk_score < 40:
        return "보통 수준의 위험도입니다. 주변을 살피며 이동하세요."
    elif risk_score < 60:
        return "주의가 필요한 경로입니다. 가능하면 우회 경로를 고려하세요."
    else:
        return "고위험 경로입니다. 다른 경로를 이용하시거나, 이동 시 각별히 주의하세요."


def get_all_risk_reports() -> List[Dict]:
    """
    저장된 모든 위험 정보 제보를 JSON 파일에서 읽어 반환합니다.
    """
    if not os.path.exists(RISK_REPORTS_FILE):
        return []
    try:
        with open(RISK_REPORTS_FILE, 'r', encoding='utf-8') as f:
            reports = json.load(f)
        return reports
    except json.JSONDecodeError:
        print(f"❌ {RISK_REPORTS_FILE} 파일이 손상되었거나 비어 있습니다.")
        return []
    except Exception as e:
        print(f"❌ 위험 제보 파일을 읽는 중 오류 발생: {e}")
        return []

def save_risk_report(report: Dict) -> Dict:
    """
    새로운 위험 정보를 JSON 파일에 저장합니다.
    """
    reports = get_all_risk_reports()
    
    # 주소에서 좌표 획득
    coords = get_coords_from_address(report['address'])
    if coords:
        report['latitude'] = coords['latitude']
        report['longitude'] = coords['longitude']
    else:
        report['latitude'] = None
        report['longitude'] = None
        print(f"⚠️ 제보 주소 '{report['address']}'에 대한 좌표를 찾을 수 없습니다.")

    report['timestamp'] = datetime.now().isoformat()
    reports.append(report)
    
    try:
        with open(RISK_REPORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(reports, f, ensure_ascii=False, indent=4)
        return {"status": "success", "message": "위험 제보가 성공적으로 저장되었습니다."}
    except Exception as e:
        print(f"❌ 위험 제보 파일을 저장하는 중 오류 발생: {e}")
        return {"status": "error", "message": f"위험 제보 저장 실패: {e}"}


def get_statistics() -> Dict:
    """전체 통계 데이터 조회"""
    try:
        # accident_manager의 get_top_risk_areas를 호출
        top_areas_df = accident_manager.get_top_risk_areas(10)
        
        return {
            "total_records": sum(len(df) for df in accident_manager.data.values()),
            "top_risk_areas": top_areas_df.to_dict('records') if not top_areas_df.empty else [],
            "data_updated": datetime.now().strftime('%Y-%m-%d'),
            "status": "active"
        }
    except Exception as e:
        print(f"❌ 통계 조회 실패: {e}")
        return {
            "total_records": 0,
            "top_risk_areas": [],
            "error": str(e),
            "status": "error"
        }