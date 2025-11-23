# 타협제로 (타협除路) - 데이터 기반 실시간 보행 위험도 분석 서비스

![Python](https://img.shields.io/badge/python-3.9-blue.svg) ![FastAPI](https://img.shields.io/badge/FastAPI-0.103-green.svg) ![JavaScript](https://img.shields.io/badge/javascript-ES6-yellow.svg)

**"과거의 통계"를 "나의 실시간 안전 정보"로 전환하여, 사용자가 능동적으로 안전한 경로를 선택하고 보행자 사고를 예방하도록 돕는 웹 서비스입니다.**

---

## 🎥 프로젝트 데모 영상

https://youtu.be/14mf6V7k8Lo

---

## ✨ 주요 기능

- **🗺️ 지도 기반 경로 시각화:** 출발지와 도착지를 입력하면, 카카오맵 위에 추천 경로와 대안 경로를 시각적으로 표시합니다.
- **💯 데이터 기반 위험도 분석:** 경찰청 사고 다발 지역 데이터, 실시간 날씨, 시간대(야간/출퇴근) 등 다양한 요소를 종합하여 경로의 위험도를 계산합니다.
- **🤖 AI 같은 상세 분석:** 왜 해당 점수가 나왔는지, 경로의 어떤 부분이 위험한지 상세 내역(예: 보행자 사고 다발 지역, 날씨 가중치)을 제공하여 사용자의 이해를 돕습니다.
- **↪️ 최적의 안전 경로 추천:** 여러 대안 경로 중, 자체 분석 알고리즘을 통해 가장 안전하다고 판단되는 경로를 '추천 경로'(파란색)로 제안합니다.
- **📊 데이터 분석 리포트:** 프로젝트의 기반이 된 공공데이터 분석 과정과 인사이트를 그래프로 시각화한 리포트 페이지를 제공합니다.
- **📢 사용자 위험 제보:** 사용자가 직접 실시간 위험(공사, 시위 등)을 제보하고 다른 사용자와 공유할 수 있습니다.

---

## 🛠️ 기술 스택

- **Backend:**
  - Python, FastAPI, Uvicorn
- **Frontend:**
  - HTML, CSS, JavaScript (Vanilla JS)
- **Data Handling & Analysis:**
  - Pandas, Google Colab, Matplotlib, Seaborn
- **External APIs & Data:**
  - Kakao Maps API, Kakao Mobility & Local API
  - 공공데이터포털 (경찰청 TAAS, 기상청 초단기실황)

---

## ⚙️ 설치 및 실행 방법

1.  **프로젝트 클론:**
    ```bash
    git clone [이 저장소의 URL]
    cd [프로젝트 폴더명]
    ```

2.  **가상환경 생성 및 활성화 (권장):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # macOS/Linux
    # venv\Scripts\activate    # Windows
    ```

3.  **의존성 설치:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **.env 파일 생성:**
    프로젝트 루트 디렉터리에 `.env` 파일을 생성하고, 아래와 같이 발급받은 API 키를 입력합니다.
    ```
    # Kakao API Keys
    KAKAO_API_KEY=여기에_카카오_REST_API_키를_입력하세요
    KAKAO_JS_KEY=여기에_카카오_JavaScript_키를_입력하세요

    # KMA API Key
    KMA_API_KEY=여기에_기상청_API_키를_입력하세요
    ```

5.  **서버 실행:**
    ```bash
    python app/main.py
    ```
    또는 Uvicorn을 직접 사용할 경우:
    ```bash
    uvicorn app.main:app --reload
    ```

6.  **서비스 접속:**
    웹 브라우저를 열고 `http://127.0.0.1:8000` 주소로 접속합니다.

---

## 📂 데이터 출처

- **사고 다발 지역:** 경찰청 교통사고분석시스템 (TAAS)
- **실시간 날씨:** 기상청 (초단기실황조회)
- **지도 및 길찾기:** 카카오 (Kakao Mobility & Local API)
