document.addEventListener('DOMContentLoaded', () => {
    const reportListContainer = document.getElementById('report-list-container');
    const reportForm = document.getElementById('report-form');
    const reportResult = document.getElementById('report-result');

    // 제보 목록을 불러와 화면에 표시하는 함수
    async function loadReports() {
        try {
            const response = await fetch('/api/reports');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const reports = await response.json();

            if (reports.length === 0) {
                reportListContainer.innerHTML = '<p>아직 제보된 위험 정보가 없습니다.</p>';
                return;
            }

            // 최신 제보가 위로 오도록 정렬
            reports.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            let reportsHtml = '<ul>';
            for (const report of reports) {
                reportsHtml += `
                    <li>
                        <p><strong>위치:</strong> ${report.address}</p>
                        <p><strong>내용:</strong> ${report.description}</p>
                        <p class="timestamp">제보 시간: ${new Date(report.timestamp).toLocaleString()}</p>
                    </li>
                `;
            }
            reportsHtml += '</ul>';
            reportListContainer.innerHTML = reportsHtml;

        } catch (error) {
            console.error('Error loading reports:', error);
            reportListContainer.innerHTML = `<p style="color: red;">제보 목록을 불러오는 중 오류가 발생했습니다.</p>`;
        }
    }

    // 위험 제보 양식 제출 처리
    reportForm.addEventListener('submit', async function(event) {
        event.preventDefault();

        const address = document.getElementById('report-address').value;
        const description = document.getElementById('report-description').value;

        if (!address || !description) {
            reportResult.innerHTML = `<p style="color: red;">주소와 위험 내용을 모두 입력해주세요.</p>`;
            return;
        }

        reportResult.innerHTML = `<p>제보를 전송 중입니다...</p>`;

        try {
            const response = await fetch('/report-risk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ address, description })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.message || `HTTP error! status: ${response.status}`);
            }

            reportResult.innerHTML = `<p style="color: green;"><strong>성공:</strong> ${result.message}</p>`;
            reportForm.reset(); // 성공 시 입력 필드 초기화

            // 제보 목록 새로고침
            await loadReports();

        } catch (error) {
            console.error('Error reporting risk:', error);
            reportResult.innerHTML = `<p style="color: red;"><strong>오류:</strong> ${error.message}</p>`;
        }
    });

    // 페이지 로드 시 제보 목록을 처음으로 불러옵니다.
    loadReports();
});
