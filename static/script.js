let map = null; // 지도 인스턴스를 저장할 전역 변수
const polylines = []; // 폴리라인들을 저장할 배열

document.getElementById('route-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    
    const loadingIndicator = document.getElementById('loading-indicator');
    const mapContainer = document.getElementById('map');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');
    const resultBreakdown = document.getElementById('result-breakdown');
    const legend = document.getElementById('map-legend');

    // 로딩 표시 및 이전 결과 숨기기
    loadingIndicator.style.display = 'block';
    mapContainer.style.display = 'none';
    resultContainer.style.display = 'none';
    legend.style.display = 'none';
    resultText.innerHTML = '';
    resultBreakdown.innerHTML = '';
    clearPolylines();

    try {
        const response = await fetch('/calculate-risk', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.message || `HTTP error! status: ${response.status}`);
        }

        if (result.status === 'success' && result.routes && result.routes.length > 0) {
            mapContainer.style.display = 'block';
            initMap();

            const bounds = new kakao.maps.LatLngBounds();
            let recommendedRoute = null;

            result.routes.forEach(route => {
                const path = route.path.map(coord => new kakao.maps.LatLng(coord[0], coord[1]));
                
                const polyline = new kakao.maps.Polyline({
                    path: path,
                    strokeWeight: 6,
                    strokeColor: route.color,
                    strokeOpacity: 0.8,
                    strokeStyle: route.is_recommended ? 'solid' : 'shortdash'
                });

                polyline.setMap(map);
                polylines.push(polyline);

                path.forEach(p => bounds.extend(p));
                
                if (route.is_recommended) {
                    recommendedRoute = route;
                }
            });

            map.setBounds(bounds);

            // 범례 생성
            legend.innerHTML = `
                <h5>범례</h5>
                <ul>
                    <li><span class="legend-color" style="background-color: blue;"></span> 추천 경로</li>
                    <li><span class="legend-color" style="background-color: red;"></span> 위험 경로</li>
                    <li><span class="legend-color" style="background-color: orange;"></span> 주의 경로</li>
                    <li><span class="legend-color" style="background-color: green;"></span> 보통 경로</li>
                </ul>
            `;
            legend.style.display = 'block';

            // 추천 경로 정보 및 상세 분석 표시
            if (recommendedRoute) {
                let resultHtml = `
                    <p><strong>추천 경로 위험도:</strong> <span class="risk-score ${recommendedRoute.color}">${recommendedRoute.risk_score}점 (${recommendedRoute.risk_level})</span></p>
                    <p>${result.safety_message}</p>
                    <p><strong>경로 정보:</strong> ${recommendedRoute.summary}</p>
                `;
                resultText.innerHTML = resultHtml;

                if (result.breakdown && result.breakdown.length > 0) {
                    let breakdownHtml = '<h4>추천 경로의 주요 위험 요소</h4><ul class="breakdown-list">';
                    result.breakdown.forEach(item => {
                        breakdownHtml += `<li>
                            <span class="reason">${item.reason}</span>
                            <span class="score">+${item.score}점</span>
                        </li>`;
                    });
                    breakdownHtml += '</ul>';
                    resultBreakdown.innerHTML = breakdownHtml;
                }
            }
            resultContainer.style.display = 'block';
        } else {
            throw new Error(result.error || '경로를 찾을 수 없거나 분석에 실패했습니다.');
        }

    } catch (error) {
        console.error('Error:', error);
        resultText.innerHTML = `<p style="color: red;"><strong>오류 발생:</strong> ${error.message}</p>`;
        resultContainer.style.display = 'block';
    } finally {
        loadingIndicator.style.display = 'none';
    }
});

function initMap() {
    if (!map) {
        const mapContainer = document.getElementById('map');
        const mapOption = {
            center: new kakao.maps.LatLng(37.566826, 126.9786567), // 서울시청
            level: 8
        };
        map = new kakao.maps.Map(mapContainer, mapOption);
    }
}

function clearPolylines() {
    for (let i = 0; i < polylines.length; i++) {
        polylines[i].setMap(null);
    }
    polylines.length = 0;
}
