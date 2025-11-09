document.getElementById('route-form').addEventListener('submit', async function(event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData(form);
    const startAddress = formData.get('start_address');
    const endAddress = formData.get('end_address');

    const loadingIndicator = document.getElementById('loading-indicator');
    const resultContainer = document.getElementById('result-container');
    const resultText = document.getElementById('result-text');

    // 로딩 표시 및 이전 결과 숨기기
    loadingIndicator.style.display = 'block';
    resultContainer.style.display = 'none';
    resultText.innerHTML = '';

    try {
        const response = await fetch('/calculate-risk', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (!response.ok) {
            // 서버가 보낸 JSON 에러 메시지를 사용, 없으면 기본 HTTP 에러 메시지
            throw new Error(result.message || `HTTP error! status: ${response.status}`);
        }

        // 결과 표시
        let resultHtml = `
            <p><strong>경로 위험도:</strong> ${result.risk_score}점</p>
            <p>${result.safety_message}</p>
            <p><strong>대안 경로:</strong> ${result.alternative_route}</p>
        `;

        // 관련 위험 제보가 있을 경우 추가
        if (result.relevant_reports && result.relevant_reports.length > 0) {
            resultHtml += `
                <div class="relevant-reports">
                    <h4><br>관련 위험 제보</h4>
                    <ul>
            `;
            for (const report of result.relevant_reports) {
                resultHtml += `
                    <li>
                        <p><strong>위치:</strong> ${report.address}</p>
                        <p><strong>내용:</strong> ${report.description}</p>
                    </li>
                `;
            }
            resultHtml += `
                    </ul>
                </div>
            `;
        }

        resultHtml += `
            <hr>
            <p style="font-size:0.8em; color: #555;">디버그 정보: ${result.debug_info}</p>
        `;
        
        resultText.innerHTML = resultHtml;
        resultContainer.style.display = 'block';

    } catch (error) {
        console.error('Error:', error);
        // 에러 메시지를 좀 더 명확하게 표시
        resultText.innerHTML = `<p style="color: red;"><strong>오류 발생:</strong> ${error.message}</p>`;
        resultContainer.style.display = 'block';
    } finally {
        // 로딩 숨기기
        loadingIndicator.style.display = 'none';
    }
});
