# TTSService

전용 고성능 Microsoft Edge TTS 마이크로서비스 엔진입니다.  
`audiobible`, `audiobook`, `texttomp3` 등 모든 오디오 서비스의 백엔드 허브 역할을 담당하며, Microsoft 최신 엔드포인트(`api.msedgeservices.com`)를 기반으로 영구 무제한 고품질 음성 합성을 제공합니다.

---

## 주요 기능

1. **Emma 다국어 및 한국어 고품질 신경망 음성 지원**
   - `en-US-EmmaMultilingualNeural` (Emma, 영어/다국어)
   - `ko-KR-SunHiNeural` (선희, 한국어 여성)
   - `ko-KR-InJoonNeural` (인준, 한국어 남성)
   - `en-US-GuyNeural`, `en-US-JennyNeural` 등 다국어 지원

2. **완벽한 하위 호환 API**
   - `POST /api/tts` : 기존 `audiobible` 및 `texttowaw` 클라이언트 호환
   - `GET /api/tts?text=...&voice=...` : 빠른 쿼리 스트리밍 및 캐싱
   - `GET /health` : Watchdog 및 모니터링용 헬스체크
   - `GET /api/voices` : 지원 음성 목록 반환

3. **초고속 디스크 캐싱 (SHA256)**
   - 동일한 텍스트 및 음성 요청에 대해 로컬 캐시를 조회하여 **0.01초 이내 즉각 응답**
   - 외부 네트워크 부하 및 마이크로소프트 레이트 리밋 완벽 방지

4. **현대적인 Audio Studio 웹 UI 내장**
   - 접속 주소: `http://<서버IP>:8099/`
   - 긴 텍스트 / 성경 구절별 일괄 분할 변환
   - 브라우저 즉시 재생 및 MP3 개별 다운로드
   - **전체 MP3 ZIP 일괄 압축 다운로드 (JSZip)**

---

## 실행 방법

### 요구사항
- Python 3.9 이상
- 의존성 설치:
```bash
pip install -r requirements.txt
```

### 서버 시작
```bash
bash start.sh
# 또는 수동 실행:
python3 -m uvicorn app:app --host 0.0.0.0 --port 8099
```

### 서버 중지
```bash
bash stop.sh
```

---

## API 사용 예시

### 1. POST 방식
```bash
curl -X POST http://localhost:8099/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world", "voice": "en-US-EmmaMultilingualNeural"}' \
  --output hello.mp3
```

### 2. GET 방식
```bash
curl "http://localhost:8099/api/tts?text=안녕하세요&voice=ko-KR-SunHiNeural" \
  --output test.mp3
```
