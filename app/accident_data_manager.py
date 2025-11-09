"""
타협제로 - CSV 기반 사고 데이터 관리 모듈 (FastAPI)
app/accident_data_manager.py
"""
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
import os
from pathlib import Path


class AccidentDataManager:
    """4개 CSV 파일 기반 사고 데이터 통합 관리"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 경로 설정
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / 'data'
        
        # CSV 파일 경로
        self.csv_files = {
            'pedestrian': self.data_dir / '19_24_pedstrians.csv',  # 보행자 사고
            'bicycle': self.data_dir / '12_24_bicycle.csv',        # 자전거 사고
            'schoolzone': self.data_dir / '12_24_schoolzone.csv',  # 어린이보호구역
            'local_gov': self.data_dir / '17_24_lg.csv'            # 지자체별 사고
        }
        
        # 데이터 저장소
        self.data = {}
        self._initialized = True
        self.load_all_data()
    
    def load_all_data(self):
        """4개 CSV 파일 모두 로드"""
        print("\n" + "="*60)
        print("🚀 타협제로 - 데이터 로딩 시작")
        print("="*60)
        
        for key, filepath in self.csv_files.items():
            try:
                if filepath.exists():
                    try:
                        df = pd.read_csv(filepath, encoding='utf-8-sig')
                    except UnicodeDecodeError:
                        print(f"⚠️ {key:12} | utf-8-sig 디코딩 실패, cp949로 재시도 | {filepath.name}")
                        df = pd.read_csv(filepath, encoding='cp949')
                    self.data[key] = df
                    print(f"✅ {key:12} | {len(df):4}건 | {filepath.name}")
                else:
                    print(f"⚠️  {key:12} | 파일 없음 | {filepath.name}")
                    self.data[key] = pd.DataFrame()
            except Exception as e:
                print(f"❌ {key:12} | 로드 실패 | {e}")
                self.data[key] = pd.DataFrame()
        
        total_records = sum(len(df) for df in self.data.values())
        print(f"\n📊 총 {total_records}건의 사고 데이터 로드 완료")
        print("="*60 + "\n")
        # Debug: Print columns of loaded dataframes
        for key, df in self.data.items():
            if not df.empty:
                print(f"DEBUG: {key} DataFrame columns: {df.columns.tolist()}")
            else:
                print(f"DEBUG: {key} DataFrame is empty.")
    
    def get_nearby_accidents(self, lat: float, lon: float, radius_km: float = 0.5) -> Dict:
        """
        좌표 주변의 사고 다발지역 검색
        
        Args:
            lat: 위도
            lon: 경도
            radius_km: 검색 반경 (km)
        
        Returns:
            주변 사고 정보 및 위험도
        """
        nearby_data = {
            'pedestrian': [],
            'bicycle': [],
            'schoolzone': [],
            'local_gov': []
        }
        
        # 각 데이터셋에서 근처 사고 지역 찾기
        for data_type, df in self.data.items():
            if df.empty:
                continue
            
            # 좌표 컬럼 확인 (데이터마다 컬럼명이 다를 수 있음)
            lat_col = self._find_lat_column(df)
            lon_col = self._find_lon_column(df)
            
            if lat_col and lon_col:
                # 거리 계산 (간단한 유클리드 거리)
                df['distance'] = ((df[lat_col] - lat)**2 + (df[lon_col] - lon)**2)**0.5
                
                # 반경 내 데이터 필터링 (대략 0.01 = 1km)
                nearby = df[df['distance'] < (radius_km * 0.01)].copy()
                
                if not nearby.empty:
                    nearby_data[data_type] = nearby.to_dict('records')
        
        # 위험도 계산
        risk_score = self._calculate_risk_from_nearby(nearby_data)
        
        return {
            'risk_score': risk_score,
            'nearby_accidents': nearby_data,
            'search_radius_km': radius_km,
            'location': {'lat': lat, 'lon': lon}
        }
    
    def get_region_risk(self, sido: str, gugun: str, dong: str = None) -> Dict:
        """
        지역명 기반 위험도 조회
        """
        print(f"\nDEBUG: get_region_risk called for sido='{sido}', gugun='{gugun}', dong='{dong}'")
        risk_data = {
            'pedestrian_risk': 0,
            'bicycle_risk': 0,
            'schoolzone_risk': 0,
            'local_gov_risk': 0
        }
        
        details = []
        
        # 각 데이터셋에서 지역 매칭
        for data_type, df in self.data.items():
            if df.empty:
                print(f"DEBUG: {data_type} DataFrame is empty, skipping.")
                continue
            
            # 지역명 컬럼 찾기
            region_matches = self._find_region_matches(df, sido, gugun, dong)
            print(f"DEBUG: {data_type} region_matches count: {len(region_matches)}")
            
            if not region_matches.empty:
                risk = self._calculate_risk_from_df(region_matches, data_type)
                risk_data[f'{data_type}_risk'] = risk
                
                details.append({
                    'type': data_type,
                    'count': len(region_matches),
                    'risk': risk,
                    'locations': region_matches.head(3).to_dict('records')
                })
        
        # 총 위험도 (가중 평균)
        total_risk = (
            risk_data['pedestrian_risk'] * 2.0 +  # 보행자 사고 가중치 높음
            risk_data['bicycle_risk'] * 1.5 +
            risk_data['schoolzone_risk'] * 2.5 +   # 어린이보호구역 가중치 높음
            risk_data['local_gov_risk'] * 1.0
        ) / 7.0
        
        print(f"DEBUG: Calculated total_risk (raw): {total_risk}")
        final_total_risk = min(int(total_risk), 100) # Max 100 for consistency
        print(f"DEBUG: Final total_risk (capped at 100): {final_total_risk}")

        return {
            'total_risk': final_total_risk,
            'region': f"{sido} {gugun} {dong if dong else ''}".strip(),
            'risk_breakdown': risk_data,
            'details': details,
            'data_source': 'csv_multi'
        }
    
    def _find_lat_column(self, df: pd.DataFrame) -> Optional[str]:
        """위도 컬럼 찾기"""
        possible_names = ['lat', 'latitude', '위도', 'la_crd', 'y_coor', 'y좌표']
        for col in df.columns:
            if any(name in col.lower() for name in possible_names):
                return col
        return None
    
    def _find_lon_column(self, df: pd.DataFrame) -> Optional[str]:
        """경도 컬럼 찾기"""
        possible_names = ['lon', 'lng', 'longitude', '경도', 'lo_crd', 'x_coor', 'x좌표']
        for col in df.columns:
            if any(name in col.lower() for name in possible_names):
                return col
        return None
    
    def _find_region_matches(self, df: pd.DataFrame, sido: str, gugun: str, dong: str = None) -> pd.DataFrame:
        """데이터프레임에서 지역 매칭"""
        print(f"DEBUG: _find_region_matches called for sido='{sido}', gugun='{gugun}', dong='{dong}'")
        result = df.copy()
        
        # 실제 컬럼명 찾기 (우선순위: 정확한 컬럼명 -> '시도시군구명' -> 부분 문자열)
        found_sido_col = next((col for col in df.columns if col in ['시도명', '시도']), None)
        found_gugun_col = next((col for col in df.columns if col in ['시군구명', '시군구', '구군']), None)
        found_dong_col = next((col for col in df.columns if col in ['읍면동명', '읍면동', '동', '법정동코드', '도로명']), None)
        found_sido_gugun_combined_col = next((col for col in df.columns if '시도시군구명' == col), None)

        print(f"DEBUG: Identified columns: found_sido_col='{found_sido_col}', found_gugun_col='{found_gugun_col}', found_dong_col='{found_dong_col}', found_sido_gugun_combined_col='{found_sido_gugun_combined_col}'")

        # 1. 개별 시도, 시군구 컬럼이 명확히 분리되어 있는 경우
        if found_sido_col and found_gugun_col:
            initial_len = len(result)
            result = result[result[found_sido_col].astype(str).str.contains(sido, na=False)]
            print(f"DEBUG: After sido filter (col: {found_sido_col}), len: {len(result)} (filtered from {initial_len})")
            
            initial_len = len(result)
            result = result[result[found_gugun_col].astype(str).str.contains(gugun, na=False)]
            print(f"DEBUG: After gugun filter (col: {found_gugun_col}), len: {len(result)} (filtered from {initial_len})")
        
        # 2. '시도시군구명' 컬럼에 시도와 시군구가 함께 있는 경우
        elif found_sido_gugun_combined_col:
            # '부산 강서구'와 같이 띄어쓰기 포함하여 매칭 시도
            combined_search_str = f"{sido}.*{gugun}" 
            initial_len = len(result)
            result = result[result[found_sido_gugun_combined_col].astype(str).str.contains(combined_search_str, regex=True, na=False)]
            print(f"DEBUG: After combined sido+gugun filter (col: {found_sido_gugun_combined_col}), len: {len(result)} (filtered from {initial_len})")
        
        # 3. 동 매칭 (개별 컬럼 또는 combined_col 사용 후)
        if found_dong_col and dong:
            initial_len = len(result)
            result = result[result[found_dong_col].astype(str).str.contains(dong, na=False)]
            print(f"DEBUG: After dong filter (col: {found_dong_col}), len: {len(result)} (filtered from {initial_len})")
        
        return result
    
    def _calculate_risk_from_df(self, df: pd.DataFrame, data_type: str) -> int:
        """데이터프레임에서 위험도 계산"""
        if df.empty:
            print(f"DEBUG: _calculate_risk_from_df for {data_type} received empty DataFrame.")
            return 0
        
        # 사고 건수 관련 컬럼 찾기
        count_cols = [col for col in df.columns if '건수' in col or 'count' in col.lower() or '발생' in col]
        print(f"DEBUG: _calculate_risk_from_df for {data_type}, count_cols: {count_cols}")
        
        if count_cols:
            # Ensure the count column is numeric, coercing errors to NaN then filling with 0
            total_count = df[count_cols[0]].apply(pd.to_numeric, errors='coerce').fillna(0).sum()
            print(f"DEBUG: {data_type} total_count: {total_count}")
            
            # 데이터 타입별 가중치
            weights = {
                'pedestrian': 2.0,
                'bicycle': 1.5,
                'schoolzone': 2.5,
                'local_gov': 1.0
            }
            
            base_risk = total_count * weights.get(data_type, 1.0)
            print(f"DEBUG: {data_type} base_risk (raw): {base_risk}")
            return min(int(base_risk), 50) # Capped at 50 for individual data type risk
        
        print(f"DEBUG: No count columns found for {data_type}. Returning len(df) * 2.")
        return len(df) * 2  # 건수 컬럼이 없으면 단순 개수
    
    def _calculate_risk_from_nearby(self, nearby_data: Dict) -> int:
        """주변 데이터에서 위험도 계산"""
        risk = 0
        
        weights = {
            'pedestrian': 3,
            'bicycle': 2,
            'schoolzone': 5,
            'local_gov': 2
        }
        
        for data_type, items in nearby_data.items():
            count = len(items)
            risk += count * weights.get(data_type, 1)
        
        return min(risk, 50)
    
    def apply_time_weight(self, base_risk: int, hour: Optional[int] = None) -> int:
        """시간대별 가중치"""
        if hour is None:
            hour = datetime.now().hour
        
        if (7 <= hour <= 9) or (18 <= hour <= 20):
            return int(base_risk * 1.3)
        elif hour >= 22 or hour <= 6:
            return int(base_risk * 1.5)
        return base_risk
    
    def apply_weather_weight(self, base_risk: float, weather_condition: str) -> float:
        """
        날씨 조건에 따른 위험도 가중치를 적용합니다.
        """
        weighted_risk = base_risk
        if "비" in weather_condition:
            weighted_risk *= 1.4 # 40% 증가
        elif "눈" in weather_condition:
            weighted_risk *= 1.6 # 60% 증가
        elif "안개" in weather_condition:
            weighted_risk *= 1.5 # 50% 증가
        return round(weighted_risk, 1)
    
    def get_statistics(self) -> Dict:
        """전체 통계"""
        stats = {}
        
        for data_type, df in self.data.items():
            if not df.empty:
                stats[data_type] = {
                    'total_records': len(df),
                    'columns': list(df.columns),
                    'sample': df.head(1).to_dict('records')[0] if len(df) > 0 else {}
                }
        
        return stats
    
    def get_top_risk_areas(self, limit: int = 10) -> pd.DataFrame:
        """
        로드된 모든 데이터에서 가장 위험한 지역 상위 N개를 반환합니다.
        """
        all_regions_data = []

        # 모든 데이터프레임에서 고유한 시도-시군구 조합 추출 및 위험도 계산
        for data_type, df in self.data.items():
            if df.empty:
                continue
            
            sido_cols = [col for col in df.columns if '시도' in col or 'sido' in col.lower()]
            gugun_cols = [col for col in df.columns if '시군구' in col or '구군' in col or 'gugun' in col.lower()]

            if sido_cols and gugun_cols:
                # 고유한 시도-시군구 조합 추출
                unique_regions = df[[sido_cols[0], gugun_cols[0]]].drop_duplicates().values.tolist()
                
                for sido, gugun in unique_regions:
                    # get_region_risk를 사용하여 각 지역의 위험도 계산
                    # dong은 None으로 전달하여 시군구 단위 위험도 계산
                    region_risk_info = self.get_region_risk(sido, gugun, dong=None)
                    
                    all_regions_data.append({
                        '시도': sido,
                        '시군구': gugun,
                        'total_risk': region_risk_info['total_risk'],
                        'pedestrian_risk': region_risk_info['risk_breakdown'].get('pedestrian_risk', 0),
                        'bicycle_risk': region_risk_info['risk_breakdown'].get('bicycle_risk', 0),
                        'schoolzone_risk': region_risk_info['risk_breakdown'].get('schoolzone_risk', 0),
                        'local_gov_risk': region_risk_info['risk_breakdown'].get('local_gov_risk', 0),
                        'data_source': region_risk_info['data_source']
                    })
        
        if not all_regions_data:
            return pd.DataFrame(columns=['시도', '시군구', 'total_risk'])

        # DataFrame으로 변환 후 total_risk 기준으로 정렬
        all_regions_df = pd.DataFrame(all_regions_data)
        # 중복 지역에 대한 위험도 합산 (예: 여러 CSV에 걸쳐 있는 경우)
        grouped_regions = all_regions_df.groupby(['시도', '시군구']).agg(
            total_risk=('total_risk', 'mean'), # 평균 위험도 사용
            pedestrian_risk=('pedestrian_risk', 'sum'),
            bicycle_risk=('bicycle_risk', 'sum'),
            schoolzone_risk=('schoolzone_risk', 'sum'),
            local_gov_risk=('local_gov_risk', 'sum')
        ).reset_index()

        # 최종 total_risk 재계산 (가중 평균)
        grouped_regions['final_total_risk'] = (
            grouped_regions['pedestrian_risk'] * 2.0 +
            grouped_regions['bicycle_risk'] * 1.5 +
            grouped_regions['schoolzone_risk'] * 2.5 +
            grouped_regions['local_gov_risk'] * 1.0
        ) / 7.0
        grouped_regions['final_total_risk'] = grouped_regions['final_total_risk'].apply(lambda x: min(int(x), 50))


        top_areas = grouped_regions.sort_values(by='final_total_risk', ascending=False).head(limit)
        return top_areas[['시도', '시군구', 'final_total_risk', 'pedestrian_risk', 'bicycle_risk', 'schoolzone_risk', 'local_gov_risk']]
    
    def reload_data(self) -> Dict:
        """데이터 재로드"""
        self.load_all_data()
        return {
            'status': 'success',
            'loaded_files': {k: len(v) for k, v in self.data.items()},
            'timestamp': datetime.now().isoformat()
        }


# 전역 싱글톤 인스턴스
accident_manager = AccidentDataManager()