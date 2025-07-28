# discord-GameBot
2025-07-28
# Discord 도박 봇 🎰

Discord 서버에서 사용할 수 있는 가상 화폐 기반 도박 봇입니다.

## 주요 기능

### 🎮 게임
- **슬롯머신** (`/슬롯`) - 3개의 심볼을 맞추는 게임
- **주사위** (`/주사위`) - 봇과 주사위 대결
- **블랙잭** (`/블랙잭`) - 딜러와의 블랙잭 게임
- **동전던지기** (`/동전던지기`) - 앞면/뒷면 맞추기

### 💰 경제 시스템
- **잔액 확인** (`/잔액`) - 현재 보유 코인 확인
- **통계 확인** (`/내통계`) - 개인 게임 통계
- **리더보드** (`/리더보드`) - 상위 10명 순위

### 🔧 관리자 기능
- **잔액 초기화** (`/잔액초기화`) - 유저 잔액 리셋
- **코인 지급** (`/코인지급`) - 코인 지급/차감
- **통계 확인** (`/통계`) - 특정 유저 통계 확인

## 설치 방법

### 1. 봇 생성
1. [Discord Developer Portal](https://discord.com/developers/applications)에 접속
2. "New Application" 클릭하여 애플리케이션 생성
3. "Bot" 섹션에서 봇 생성
4. 봇 토큰 복사 (Reset Token 클릭)

### 2. 봇 권한 설정
1. "OAuth2" → "URL Generator" 이동
2. Scopes에서 `bot`과 `applications.commands` 선택
3. Bot Permissions에서 다음 권한 선택:
   - Send Messages
   - Use Slash Commands
   - Embed Links
   - Read Message History
   - View Channels
4. 생성된 URL로 봇을 서버에 초대

### 3. 코드 설정
```bash
# 저장소 클론 또는 파일 다운로드
git clone [your-repo-url]
cd discord-gambling-bot

# 가상 환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt

# 봇 토큰 설정
# gambling_bot.py 파일의 맨 아래에서 YOUR_BOT_TOKEN을 실제 토큰으로 교체
```

### 4. 봇 실행
```bash
python gambling_bot.py
```

## 환경 변수 사용 (선택사항)

보안을 위해 `.env` 파일을 사용하여 토큰을 관리할 수 있습니다:

1. `.env` 파일 생성:
```env
BOT_TOKEN=your_bot_token_here
```

2. 코드 수정:
```python
import os
from dotenv import load_dotenv

load_dotenv()
bot.run(os.getenv('BOT_TOKEN'))
```

## 게임 규칙

### 🎰 슬롯머신
- 3개 모두 일치: 배팅금액 × 10
- 2개 일치: 배팅금액 × 2
- 불일치: 배팅금액 손실

### 🎲 주사위
- 높은 숫자 승리: 배팅금액 × 2
- 낮은 숫자 패배: 배팅금액 손실
- 무승부: 변동 없음

### 🃏 블랙잭
- 일반 승리: 배팅금액 × 2
- 더블 승리: 배팅금액 × 4
- 패배: 배팅금액 손실
- 푸시(무승부): 변동 없음

### 🪙 동전던지기
- 정답: 배팅금액 × 2
- 오답: 배팅금액 손실

## 데이터 저장

- 모든 유저 데이터는 `economy_data.json` 파일에 저장됩니다
- 봇을 재시작해도 데이터가 유지됩니다
- 백업을 위해 주기적으로 파일을 복사해두는 것을 권장합니다

## 관리자 설정

관리자 명령어를 사용하려면 Discord 서버에서 다음 중 하나의 역할이 필요합니다:
- `관리자`
- `Admin`
- `Administrator`

## 문제 해결

### 슬래시 커맨드가 보이지 않을 때
1. 봇을 서버에서 제거 후 다시 초대
2. Discord 클라이언트 재시작
3. 봇 권한 확인 (Use Slash Commands 필수)

### 봇이 응답하지 않을 때
1. 콘솔에서 오류 메시지 확인
2. 봇 토큰이 올바른지 확인
3. 인터넷 연결 상태 확인

## 주의사항

- 이 봇은 가상 화폐만을 사용하며, 실제 금전 거래와는 무관합니다
- 도박 중독 예방을 위해 적절한 휴식을 취하세요
- 서버 규칙에 따라 봇 사용을 제한할 수 있습니다
