"""
타협제로 - 서비스 로직
CSV 데이터 기반 위험도 계산
"""
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import os
import json
import math # Added for KMA grid conversion
from .accident_data_manager import accident_manager

# 환경 변수에서 API 키 가져오기
KAKAO_API_KEY = os.getenv('KAKAO_API_KEY', '')
KMA_API_KEY = os.getenv('KMA_API_KEY', '') # Added for KMA API


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


def _latlon_to_kma_grid(lat, lon):
    """
    위도/경도를 기상청 격자 좌표(X, Y)로 변환합니다.
    LCC DFS 지구 좌표 변환 ( code from : https://gist.github.com/fronteer-kr/14d7f779d52a21ac2f56 )
    """
    RE = 6371.00877  # 지구 반경(km)
    GRID = 5.0      # 격자 간격(km)
    SLAT1 = 30.0    # 투영 위도1(도)
    SLAT2 = 60.0    # 투영 위도2(도)
    OLON = 126.0    # 기준점 경도(도)
    OLAT = 38.0     # 기준점 위도(도)
    XO = 43         # 기준점 X좌표(격자)
    YO = 136        # 기준점 Y좌표(격자)
    
    DEGRAD = math.pi / 180.0
    
    re = RE / GRID
    slat1 = SLAT1 * DEGRAD
    slat2 = SLAT2 * DEGRAD
    olon = OLON * DEGRAD
    olat = OLAT * DEGRAD

    sn = math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(sn)
    sf = math.tan(math.pi * 0.25 + slat1 * 0.5)
    sf = math.pow(sf, sn) * math.cos(slat1) / sn
    ro = math.tan(math.pi * 0.25 + olat * 0.5)
    ro = re * sf / math.pow(ro, sn)

    ra = math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5)
    ra = re * sf / math.pow(ra, sn)
    theta = lon * DEGRAD - olon
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= sn

    nx = math.floor(ra * math.sin(theta) + XO + 0.5)
    ny = math.floor(ro - ra * math.cos(theta) + YO + 0.5)
    
    return int(nx), int(ny)


def get_weather_data(lat: float, lon: float) -> Dict:
    """
    기상청 초단기실황 API를 통해 현재 날씨 정보를 조회합니다.
    """
    if not KMA_API_KEY:
        print("⚠️ KMA_API_KEY가 설정되지 않았습니다. 기본값을 반환합니다.")
        return {"condition": "정보 없음", "source": "no_key"}

    nx, ny = _latlon_to_kma_grid(lat, lon)
    
    # 안정적인 데이터 수신을 위해 현재 시간보다 1시간 전 데이터를 요청
    now = datetime.now()
    target_time = now - timedelta(hours=1)
    base_date = target_time.strftime('%Y%m%d')
    base_time = target_time.strftime('%H00')

    url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"
    params = {
        "serviceKey": KMA_API_KEY,
        "pageNo": "1",
        "numOfRows": "10",
        "dataType": "JSON",
        "base_date": base_date,
        "base_time": base_time,
        "nx": str(nx),
        "ny": str(ny)
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get('response', {}).get('header', {}).get('resultCode') == '00':
            items = data['response']['body']['items']['item']
            pty_item = next((item for item in items if item['category'] == 'PTY'), None)
            
            if pty_item:
                pty_code = pty_item['obsrValue']
                pty_map = {
                    "0": "맑음", "1": "비", "2": "비/눈", "3": "눈",
                    "5": "빗방울", "6": "빗방울/눈날림", "7": "눈날림"
                }
                condition = pty_map.get(pty_code, "정보 없음")
                
                # 빗방울/눈날림도 위험 요소로 간주하여 '비' 또는 '눈'으로 단순화
                if "비" in condition:
                    condition = "비"
                elif "눈" in condition:
                    condition = "눈"
                else:
                    condition = "맑음"

                return {"condition": condition, "source": "kma_api"}
    
    except requests.exceptions.RequestException as e:
        print(f"❌ 기상청 API 호출 실패: {e}")
    except (KeyError, TypeError) as e:
        print(f"❌ 기상청 API 응답 처리 실패: {e}, 응답: {data}")

    # 실패 시 기본값 반환
    return {"condition": "정보 없음", "source": "api_error"}


def get_accident_data(lat: float, lon: float) -> Dict:
    """
    좌표 기반 사고 위험도와 상세 내역을 함께 조회합니다.
    """
    breakdown = []
    reason_map = {
        'pedestrian_risk': '보행자 사고',
        'bicycle_risk': '자전거 사고',
        'schoolzone_risk': '스쿨존 사고',
        'local_gov_risk': '지자체 통계'
    }

    address_info = get_address_from_coords(lat, lon)
    if not address_info:
        return {"total_risk": 5, "breakdown": [{'reason': '주소 변환 실패', 'score': 5}], "error": "좌표를 주소로 변환할 수 없습니다."}

    sido_name = address_info.get('region_1depth_name', '')
    gugun_name = address_info.get('region_2depth_name', '')
    dong_name = address_info.get('region_3depth_name', '')

    risk_data_from_csv = accident_manager.get_region_risk(sido_name, gugun_name, dong_name)
    
    # 1. 지역 기반 위험도 상세 내역 추가
    base_risk = risk_data_from_csv['total_risk']
    # risk_breakdown의 점수를 기반으로 상세 내역 추가
    for risk_type, risk_value in risk_data_from_csv['risk_breakdown'].items():
        if risk_value > 0:
            reason = reason_map.get(risk_type, '기타')
            # 실제 기여도를 반영하기 위해 가중치를 곱하지 않은 순수 점수를 추가
            breakdown.append({'reason': f'{reason} 다발 지역', 'score': int(risk_value)})

    # 2. 시간대 가중치 적용 및 상세 내역 추가
    current_hour = datetime.now().hour
    time_weighted_risk = accident_manager.apply_time_weight(base_risk, current_hour)
    time_added_risk = round(time_weighted_risk - base_risk, 1)
    if time_added_risk > 0:
        time_reason = "야간" if current_hour >= 22 or current_hour <= 6 else "출퇴근 시간"
        breakdown.append({'reason': f'{time_reason} 가중치', 'score': time_added_risk})

    # 3. 날씨 가중치 적용 및 상세 내역 추가
    weather = get_weather_data(lat, lon)
    weather_condition = weather.get('condition', '맑음')
    final_risk = accident_manager.apply_weather_weight(time_weighted_risk, weather_condition)
    weather_added_risk = round(final_risk - time_weighted_risk, 1)
    if weather_added_risk > 0:
        breakdown.append({'reason': f'날씨({weather_condition}) 가중치', 'score': weather_added_risk})

    # 최종 위험도 및 상세 내역 정렬
    final_risk = min(round(final_risk, 1), 100.0)
    breakdown.sort(key=lambda x: x['score'], reverse=True)

    return {
        "total_risk": final_risk,
        "region": risk_data_from_csv['region'],
        "breakdown": breakdown,
        "weather": weather,
        "source": "csv_data_breakdown",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def _calculate_risk_for_single_route(route_summary: list, sampling_points: int = 15) -> Dict:
    """
    하나의 경로(폴리라인)에 대한 위험도를 계산합니다.
    경로를 일정 개수의 점으로 샘플링하여 각 지점의 위험도를 평균냅니다.
    """
    # 1. 경로의 모든 좌표(vertexes)를 하나의 리스트로 추출
    all_coords = []
    for section in route_summary['sections']:
        for road in section['roads']:
            # vertexes는 [lon1, lat1, lon2, lat2, ...] 형태로 제공됨
            vertexes = road['vertexes']
            for i in range(0, len(vertexes), 2):
                all_coords.append((vertexes[i+1], vertexes[i])) # (lat, lon) 순서로 저장

    if not all_coords:
        return {"avg_risk": 0, "highest_risk_point": None, "waypoints": []}

    # 2. 경로를 일정 개수의 점으로 샘플링
    total_points = len(all_coords)
    if total_points <= sampling_points:
        waypoints = all_coords
    else:
        step = total_points / sampling_points
        waypoints = [all_coords[int(i * step)] for i in range(sampling_points)]
    
    # 3. 각 샘플링 지점의 위험도 계산
    total_risk_sum = 0
    highest_risk_point = {"risk_score": -1}

    for (lat, lon) in waypoints:
        point_risk_data = get_accident_data(lat, lon)
        if "error" in point_risk_data:
            continue # 특정 지점 오류는 무시하고 계속 진행

        total_risk_sum += point_risk_data['total_risk']
        
        if point_risk_data['total_risk'] > highest_risk_point['risk_score']:
            highest_risk_point = {
                "risk_score": point_risk_data['total_risk'],
                "region": point_risk_data['region'],
                "breakdown": point_risk_data.get('breakdown', [])
            }
            
    avg_risk = total_risk_sum / len(waypoints) if waypoints else 0
    
    return {
        "avg_risk": round(avg_risk, 1),
        "highest_risk_point": highest_risk_point,
        "waypoints": all_coords
    }


def calculate_route_risk(start_coords: tuple, end_coords: tuple) -> Dict:
    """
    카카오 길찾기 API를 사용하여 경로를 탐색하고, 각 경로의 위험도를 계산하여 비교합니다.
    """
    if not KAKAO_API_KEY:
        return {"status": "error", "error": "KAKAO_API_KEY가 설정되지 않았습니다."}

    # 카카오 길찾기 API 호출
    url = "https://apis-navi.kakaomobility.com/v1/directions"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {
        "origin": f"{start_coords[1]},{start_coords[0]}",
        "destination": f"{end_coords[1]},{end_coords[0]}",
        "alternatives": True,
        "road_details": False
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return {"status": "error", "error": f"카카오 길찾기 API 호출 실패: {e}"}
    
    if "routes" not in data or not data["routes"]:
        return {"status": "error", "error": "경로를 찾을 수 없습니다."}

    # 각 경로의 위험도 분석
    analyzed_routes = []
    for i, route in enumerate(data["routes"]):
        route_analysis = _calculate_risk_for_single_route(route)
        analyzed_routes.append({
            "route_index": i,
            "is_primary": i == 0,
            "summary": route['summary'],
            "risk_score": route_analysis['avg_risk'],
            "highest_risk_point": route_analysis['highest_risk_point'],
            "path": route_analysis['waypoints']
        })

    # 위험도가 가장 낮은 경로를 '추천' 경로로 선정
    if not analyzed_routes:
        return {"status": "error", "error": "경로 분석에 실패했습니다."}
        
    recommended_route = min(analyzed_routes, key=lambda x: x['risk_score'])
    
    # 프론트엔드로 보낼 경로 데이터 구성
    final_routes_data = []
    for route in analyzed_routes:
        is_recommended = route['route_index'] == recommended_route['route_index']
        
        # 위험 등급 판정
        if route['risk_score'] < 20: risk_level, risk_color = "안전", "blue"
        elif route['risk_score'] < 40: risk_level, risk_color = "보통", "green"
        elif route['risk_score'] < 60: risk_level, risk_color = "주의", "orange"
        else: risk_level, risk_color = "위험", "red"
        
        # 추천 경로는 항상 파란색으로 표시하고, 기본 경로는 위험도에 따라 색상 부여
        if is_recommended:
            color = "blue"
        else:
            color = risk_color

        final_routes_data.append({
            "path": route['path'],
            "risk_score": route['risk_score'],
            "risk_level": risk_level,
            "color": color,
            "is_recommended": is_recommended,
            "summary": f"거리: {route['summary']['distance'] // 1000}km, 시간: {route['summary']['duration'] // 60}분"
        })

    return {
        "status": "success",
        "routes": final_routes_data,
        "safety_message": get_safety_recommendation(recommended_route['risk_score']),
        "breakdown": recommended_route['highest_risk_point']['breakdown']
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