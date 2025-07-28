import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import random
from typing import Optional

# 봇 및 인텐트 설정
intents = discord.Intents.default()
intents.message_content = False  # 슬래시 커맨드만 사용하므로 메시지 내용은 불필요
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 데이터 파일 경로
DATA_FILE = "economy_data.json"

# 기본 배율 설정
DEFAULT_MULTIPLIERS = {
    "slot": {
        "jackpot": 10,  # 3개 모두 일치
        "two_match": 2  # 2개 일치
    },
    "dice": {
        "win": 2  # 승리 시
    },
    "blackjack": {
        "win": 2,  # 일반 승리
        "blackjack": 2.5  # 블랙잭으로 승리 (21)
    },
    "coinflip": {
        "win": 2  # 승리 시
    }
}

# 경제 데이터 로드 또는 초기화
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        economy_data = json.load(f)
    # 배율 설정이 없으면 추가
    if "multipliers" not in economy_data:
        economy_data["multipliers"] = DEFAULT_MULTIPLIERS
else:
    economy_data = {
        "users": {},
        "multipliers": DEFAULT_MULTIPLIERS
    }

# 기본 시작 잔액
DEFAULT_START_BALANCE = 1000

# 유저 데이터 가져오기 (없으면 초기화)
def get_user_data(user_id: int) -> dict:
    uid = str(user_id)
    if uid not in economy_data["users"]:
        economy_data["users"][uid] = {
            "balance": DEFAULT_START_BALANCE,
            "stats": {
                "slot": {"played": 0, "won": 0},
                "dice": {"played": 0, "won": 0},
                "blackjack": {"played": 0, "won": 0},
                "bet": {"played": 0, "won": 0}
            }
        }
    return economy_data["users"][uid]

# 배율 가져오기
def get_multipliers():
    return economy_data.get("multipliers", DEFAULT_MULTIPLIERS)

# 데이터 저장 함수
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(economy_data, f, indent=4, ensure_ascii=False)

# 봇 준비 완료 이벤트
@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ 슬래시 커맨드 동기화 완료")
    except Exception as e:
        print(f"❌ 커맨드 동기화 실패: {e}")
    print(f"🎰 {bot.user} 로그인 완료 (ID: {bot.user.id})")

# ========================
# 기본 경제 명령어
# ========================

@bot.tree.command(name="잔액", description="내 코인 잔액 확인")
async def balance_cmd(interaction: discord.Interaction):
    """유저의 현재 잔액을 확인합니다."""
    user_data = get_user_data(interaction.user.id)
    bal = user_data["balance"]
    await interaction.response.send_message(
        f"💰 **{interaction.user.display_name}**님의 잔액: **{bal:,}** 코인"
    )

# ========================
# 🎰 슬롯머신 게임
# ========================

SLOT_SYMBOLS = ["🍒", "🍋", "🔔", "🍀", "⭐", "💎", "🍇"]

class SlotMachineView(discord.ui.View):
    def __init__(self, player: discord.User, bet: int):
        super().__init__(timeout=30)
        self.player = player
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.send_message(
                "❌ 다른 사람의 슬롯머신입니다!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎲 돌리기", style=discord.ButtonStyle.primary)
    async def spin_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_data = get_user_data(self.player.id)
        multipliers = get_multipliers()
        
        # 3개의 심볼 랜덤 선택
        result = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        
        # 결과 판정
        if result[0] == result[1] == result[2]:
            # 잭팟! 3개 모두 일치
            mult = multipliers["slot"]["jackpot"]
            payout = int(mult * self.bet)
            user_data["balance"] += payout
            user_data["stats"]["slot"]["won"] += 1
            outcome_text = f"🎉 **잭팟!** {' '.join(result)}\n모두 일치! **{payout:,}** 코인 획득! (배율: {mult}x)"
        elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
            # 2개 일치
            mult = multipliers["slot"]["two_match"]
            payout = int(mult * self.bet)
            user_data["balance"] += payout
            user_data["stats"]["slot"]["won"] += 1
            outcome_text = f"✨ **승리!** {' '.join(result)}\n2개 일치! **{payout:,}** 코인 획득! (배율: {mult}x)"
        else:
            # 패배
            user_data["balance"] -= self.bet
            outcome_text = f"💸 **패배** {' '.join(result)}\n일치하지 않음. **{self.bet:,}** 코인 잃음."
        
        user_data["stats"]["slot"]["played"] += 1
        save_data()
        
        button.disabled = True
        await interaction.response.edit_message(content=outcome_text, view=self)

@bot.tree.command(name="슬롯", description="슬롯머신 게임을 플레이합니다")
@app_commands.describe(배팅금액="슬롯머신에 배팅할 코인 수")
async def slot_cmd(interaction: discord.Interaction, 배팅금액: int):
    user_data = get_user_data(interaction.user.id)
    
    if 배팅금액 <= 0:
        await interaction.response.send_message("❌ 배팅금액은 0보다 커야 합니다!", ephemeral=True)
        return
    
    if user_data["balance"] < 배팅금액:
        await interaction.response.send_message("❌ 잔액이 부족합니다!", ephemeral=True)
        return
    
    view = SlotMachineView(interaction.user, 배팅금액)
    multipliers = get_multipliers()
    
    await interaction.response.send_message(
        f"🎰 **슬롯머신** - 배팅: **{배팅금액:,}** 코인\n"
        f"잭팟 배율: {multipliers['slot']['jackpot']}x | 2개 일치 배율: {multipliers['slot']['two_match']}x\n"
        f"**돌리기** 버튼을 눌러주세요!",
        view=view
    )

# ========================
# 🎲 주사위 게임
# ========================

class DiceGameView(discord.ui.View):
    def __init__(self, player: discord.User, bet: int):
        super().__init__(timeout=20)
        self.player = player
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.send_message(
                "❌ 다른 사람의 게임입니다!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="🎲 주사위 굴리기", style=discord.ButtonStyle.success)
    async def roll_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_data = get_user_data(self.player.id)
        multipliers = get_multipliers()
        
        player_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)
        
        result_msg = f"🎲 당신: **{player_roll}** vs 봇: **{bot_roll}**\n"
        
        if player_roll > bot_roll:
            mult = multipliers["dice"]["win"]
            winnings = int((mult - 1) * self.bet)  # 배팅금액은 이미 차감되므로 순수익만 더함
            user_data["balance"] += self.bet + winnings
            user_data["stats"]["dice"]["won"] += 1
            result_msg += f"✅ 승리! **{self.bet + winnings:,}** 코인 획득! (배율: {mult}x)"
        elif player_roll < bot_roll:
            user_data["balance"] -= self.bet
            result_msg += f"❌ 패배! **{self.bet:,}** 코인 잃음."
        else:
            result_msg += "🤝 무승부! 코인 변동 없음."
        
        user_data["stats"]["dice"]["played"] += 1
        save_data()
        
        button.disabled = True
        await interaction.response.edit_message(content=result_msg, view=self)

@bot.tree.command(name="주사위", description="봇과 주사위 대결을 합니다")
@app_commands.describe(배팅금액="주사위 게임에 배팅할 코인 수")
async def dice_cmd(interaction: discord.Interaction, 배팅금액: int):
    user_data = get_user_data(interaction.user.id)
    
    if 배팅금액 <= 0:
        await interaction.response.send_message("❌ 배팅금액은 0보다 커야 합니다!", ephemeral=True)
        return
    
    if user_data["balance"] < 배팅금액:
        await interaction.response.send_message("❌ 잔액이 부족합니다!", ephemeral=True)
        return
    
    view = DiceGameView(interaction.user, 배팅금액)
    multipliers = get_multipliers()
    
    await interaction.response.send_message(
        f"🎲 **주사위 게임** - 배팅: **{배팅금액:,}** 코인\n"
        f"승리 배율: {multipliers['dice']['win']}x\n"
        f"더 높은 숫자를 굴려 이기세요!",
        view=view
    )

# ========================
# 🃏 블랙잭 게임
# ========================

def calculate_total(cards: list[int]) -> int:
    """블랙잭 카드 합계 계산 (에이스 조정 포함)"""
    total = sum(cards)
    aces = cards.count(11)
    
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    
    return total

class BlackjackView(discord.ui.View):
    def __init__(self, player: discord.User, bet: int):
        super().__init__(timeout=60)
        self.player = player
        self.bet = bet
        self.doubled = False
        
        # 카드 뽑기 (A=11, J/Q/K=10)
        draw_card = lambda: random.choice([11, 10, 10, 10] + list(range(2, 10)))
        self.player_hand = [draw_card(), draw_card()]
        self.dealer_hand = [draw_card(), draw_card()]
        
        # 더블 버튼 비활성화 (잔액 부족시)
        if get_user_data(player.id)["balance"] < bet:
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.label == "더블":
                    item.disabled = True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.send_message(
                "❌ 다른 사람의 블랙잭 게임입니다!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="히트", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        card = random.choice([11, 10, 10, 10] + list(range(2, 10)))
        self.player_hand.append(card)
        player_total = calculate_total(self.player_hand)
        
        content = f"**당신의 패:** {self.player_hand} (합계: {player_total})\n"
        content += f"**딜러의 패:** [{self.dealer_hand[0]}, ?]"
        
        if player_total > 21:
            user_data = get_user_data(self.player.id)
            loss = self.bet * (2 if self.doubled else 1)
            user_data["balance"] -= loss
            user_data["stats"]["blackjack"]["played"] += 1
            save_data()
            
            content += f"\n\n💥 **버스트!** 21을 초과했습니다. **{loss:,}** 코인 잃음."
            
            for item in self.children:
                item.disabled = True
        else:
            content += "\n\n히트 또는 스탠드를 선택하세요."
            for item in self.children:
                if isinstance(item, discord.ui.Button) and item.label == "더블":
                    item.disabled = True
        
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="스탠드", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        player_total = calculate_total(self.player_hand)
        
        # 딜러는 17 이상까지 카드를 뽑음
        while calculate_total(self.dealer_hand) < 17:
            card = random.choice([11, 10, 10, 10] + list(range(2, 10)))
            self.dealer_hand.append(card)
        
        dealer_total = calculate_total(self.dealer_hand)
        
        user_data = get_user_data(self.player.id)
        multipliers = get_multipliers()
        base_bet = self.bet * (2 if self.doubled else 1)
        
        if dealer_total > 21 or player_total > dealer_total:
            # 블랙잭으로 이긴 경우 특별 배율
            if player_total == 21 and len(self.player_hand) == 2:
                mult = multipliers["blackjack"]["blackjack"]
                winnings = int(base_bet * mult)
                result = f"✅ **블랙잭!** {winnings:,} 코인 획득! (배율: {mult}x)"
            else:
                mult = multipliers["blackjack"]["win"]
                winnings = int(base_bet * mult)
                result = f"✅ **승리!** {winnings:,} 코인 획득! (배율: {mult}x)"
            
            user_data["balance"] += winnings
            user_data["stats"]["blackjack"]["won"] += 1
        elif dealer_total == player_total:
            result = "🤝 **푸시!** 무승부입니다."
        else:
            user_data["balance"] -= base_bet
            result = f"❌ **패배!** {base_bet:,} 코인 잃음."
        
        user_data["stats"]["blackjack"]["played"] += 1
        save_data()
        
        content = f"**당신의 패:** {self.player_hand} (합계: {player_total})\n"
        content += f"**딜러의 패:** {self.dealer_hand} (합계: {dealer_total})\n\n"
        content += result
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(content=content, view=self)

    @discord.ui.button(label="더블", style=discord.ButtonStyle.success)
    async def double_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.doubled = True
        user_data = get_user_data(self.player.id)
        user_data["balance"] -= self.bet  # 추가 배팅 차감
        
        card = random.choice([11, 10, 10, 10] + list(range(2, 10)))
        self.player_hand.append(card)
        
        # 자동으로 스탠드
        await self.stand_button.callback(self, interaction, button=None)

@bot.tree.command(name="블랙잭", description="딜러와 블랙잭 게임을 합니다")
@app_commands.describe(배팅금액="블랙잭에 배팅할 코인 수")
async def blackjack_cmd(interaction: discord.Interaction, 배팅금액: int):
    user_data = get_user_data(interaction.user.id)
    
    if 배팅금액 <= 0:
        await interaction.response.send_message("❌ 배팅금액은 0보다 커야 합니다!", ephemeral=True)
        return
    
    if user_data["balance"] < 배팅금액:
        await interaction.response.send_message("❌ 잔액이 부족합니다!", ephemeral=True)
        return
    
    view = BlackjackView(interaction.user, 배팅금액)
    multipliers = get_multipliers()
    
    initial_player_total = calculate_total(view.player_hand)
    dealer_upcard = view.dealer_hand[0]
    
    content = f"🃏 **블랙잭** - 배팅: **{배팅금액:,}** 코인\n"
    content += f"일반 승리: {multipliers['blackjack']['win']}x | 블랙잭: {multipliers['blackjack']['blackjack']}x\n\n"
    content += f"**당신의 패:** {view.player_hand} (합계: {initial_player_total})\n"
    content += f"**딜러의 패:** [{dealer_upcard}, ?]\n\n"
    content += "**히트**, **스탠드**, 또는 **더블**을 선택하세요."
    
    await interaction.response.send_message(content, view=view)

# ========================
# 🪙 동전 던지기
# ========================

class CoinFlipView(discord.ui.View):
    def __init__(self, player: discord.User, bet: int):
        super().__init__(timeout=15)
        self.player = player
        self.bet = bet

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.player:
            await interaction.response.send_message(
                "❌ 다른 사람의 게임입니다!", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="앞면", style=discord.ButtonStyle.secondary)
    async def heads_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve_bet(interaction, guess="앞면")

    @discord.ui.button(label="뒷면", style=discord.ButtonStyle.secondary)
    async def tails_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.resolve_bet(interaction, guess="뒷면")

    async def resolve_bet(self, interaction: discord.Interaction, guess: str):
        user_data = get_user_data(self.player.id)
        multipliers = get_multipliers()
        outcome = random.choice(["앞면", "뒷면"])
        
        if outcome == guess:
            mult = multipliers["coinflip"]["win"]
            winnings = int(self.bet * mult)
            user_data["balance"] += winnings
            user_data["stats"]["bet"]["won"] += 1
            result = f"✅ **{outcome}**! 정답! **{winnings:,}** 코인 획득! (배율: {mult}x)"
        else:
            user_data["balance"] -= self.bet
            result = f"❌ **{outcome}**. 틀렸습니다. **{self.bet:,}** 코인 잃음."
        
        user_data["stats"]["bet"]["played"] += 1
        save_data()
        
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(content=result, view=self)

@bot.tree.command(name="동전던지기", description="동전 던지기 게임 (앞면/뒷면)")
@app_commands.describe(배팅금액="동전 던지기에 배팅할 코인 수")
async def coinflip_cmd(interaction: discord.Interaction, 배팅금액: int):
    user_data = get_user_data(interaction.user.id)
    
    if 배팅금액 <= 0:
        await interaction.response.send_message("❌ 배팅금액은 0보다 커야 합니다!", ephemeral=True)
        return
    
    if user_data["balance"] < 배팅금액:
        await interaction.response.send_message("❌ 잔액이 부족합니다!", ephemeral=True)
        return
    
    view = CoinFlipView(interaction.user, 배팅금액)
    multipliers = get_multipliers()
    
    await interaction.response.send_message(
        f"🪙 **동전 던지기** - 배팅: **{배팅금액:,}** 코인\n"
        f"승리 배율: {multipliers['coinflip']['win']}x\n"
        f"앞면 또는 뒷면을 선택하세요!",
        view=view
    )

# ========================
# 관리자 명령어
# ========================

@bot.tree.command(name="배율설정", description="(관리자) 게임 배율 설정")
@app_commands.checks.has_any_role("관리자", "Admin", "Administrator")
@app_commands.describe(
    게임="설정할 게임 선택",
    종류="배율 종류",
    배율="새로운 배율 (예: 2.5)"
)
@app_commands.choices(
    게임=[
        app_commands.Choice(name="슬롯머신", value="slot"),
        app_commands.Choice(name="주사위", value="dice"),
        app_commands.Choice(name="블랙잭", value="blackjack"),
        app_commands.Choice(name="동전던지기", value="coinflip")
    ]
)
async def set_multiplier_cmd(interaction: discord.Interaction, 게임: str, 종류: str, 배율: float):
    multipliers = get_multipliers()
    
    # 유효한 종류인지 확인
    valid_types = {
        "slot": ["jackpot", "two_match"],
        "dice": ["win"],
        "blackjack": ["win", "blackjack"],
        "coinflip": ["win"]
    }
    
    if 종류 not in valid_types.get(게임, []):
        valid_list = ", ".join(valid_types.get(게임, []))
        await interaction.response.send_message(
            f"❌ '{게임}'의 유효한 종류: {valid_list}", 
            ephemeral=True
        )
        return
    
    if 배율 <= 0:
        await interaction.response.send_message("❌ 배율은 0보다 커야 합니다!", ephemeral=True)
        return
    
    # 배율 업데이트
    if 게임 not in multipliers:
        multipliers[게임] = {}
    multipliers[게임][종류] = 배율
    economy_data["multipliers"] = multipliers
    save_data()
    
    game_names = {"slot": "슬롯머신", "dice": "주사위", "blackjack": "블랙잭", "coinflip": "동전던지기"}
    type_names = {
        "jackpot": "잭팟", "two_match": "2개 일치", 
        "win": "승리", "blackjack": "블랙잭(21)"
    }
    
    await interaction.response.send_message(
        f"✅ **{game_names[게임]}**의 **{type_names.get(종류, 종류)}** 배율을 **{배율}x**로 설정했습니다!",
        ephemeral=True
    )

@bot.tree.command(name="배율확인", description="현재 게임 배율 확인")
async def check_multipliers_cmd(interaction: discord.Interaction):
    multipliers = get_multipliers()
    
    embed = discord.Embed(
        title="🎮 현재 게임 배율",
        color=discord.Color.gold()
    )
    
    # 슬롯머신
    embed.add_field(
        name="🎰 슬롯머신",
        value=f"잭팟 (3개): {multipliers['slot']['jackpot']}x\n2개 일치: {multipliers['slot']['two_match']}x",
        inline=True
    )
    
    # 주사위
    embed.add_field(
        name="🎲 주사위",
        value=f"승리: {multipliers['dice']['win']}x",
        inline=True
    )
    
    # 블랙잭
    embed.add_field(
        name="🃏 블랙잭",
        value=f"일반 승리: {multipliers['blackjack']['win']}x\n블랙잭(21): {multipliers['blackjack']['blackjack']}x",
        inline=True
    )
    
    # 동전던지기
    embed.add_field(
        name="🪙 동전던지기",
        value=f"승리: {multipliers['coinflip']['win']}x",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="잔액초기화", description="(관리자) 유저의 잔액을 초기값으로 리셋")
@app_commands.checks.has_any_role("관리자", "Admin", "Administrator")
@app_commands.describe(유저="잔액을 초기화할 유저")
async def reset_balance_cmd(interaction: discord.Interaction, 유저: discord.Member):
    user_data = get_user_data(유저.id)
    user_data["balance"] = DEFAULT_START_BALANCE
    user_data["stats"] = {
        "slot": {"played": 0, "won": 0},
        "dice": {"played": 0, "won": 0},
        "blackjack": {"played": 0, "won": 0},
        "bet": {"played": 0, "won": 0}
    }
    save_data()
    
    await interaction.response.send_message(
        f"✅ **{유저.display_name}**님의 잔액을 {DEFAULT_START_BALANCE:,} 코인으로 초기화했습니다.",
        ephemeral=True
    )

@bot.tree.command(name="코인지급", description="(관리자) 유저에게 코인 지급/차감")
@app_commands.checks.has_any_role("관리자", "Admin", "Administrator")
@app_commands.describe(
    유저="코인을 지급/차감할 유저",
    금액="지급할 코인 수 (음수로 차감 가능)"
)
async def givecoins_cmd(interaction: discord.Interaction, 유저: discord.Member, 금액: int):
    user_data = get_user_data(유저.id)
    user_data["balance"] += 금액
    
    if user_data["balance"] < 0:
        user_data["balance"] = 0
    
    save_data()
    
    if 금액 >= 0:
        msg = f"**{유저.display_name}**님에게 {금액:,} 코인을 지급했습니다. 현재 잔액: {user_data['balance']:,}"
    else:
        msg = f"**{유저.display_name}**님에게서 {abs(금액):,} 코인을 차감했습니다. 현재 잔액: {user_data['balance']:,}"
    
    await interaction.response.send_message(f"✅ {msg}", ephemeral=True)

@bot.tree.command(name="통계", description="(관리자) 유저의 도박 통계 확인")
@app_commands.checks.has_any_role("관리자", "Admin", "Administrator")
@app_commands.describe(유저="통계를 확인할 유저")
async def stats_cmd(interaction: discord.Interaction, 유저: discord.Member):
    user_data = get_user_data(유저.id)
    stats = user_data["stats"]
    
    embed = discord.Embed(
        title=f"📊 {유저.display_name}님의 도박 통계",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎰 슬롯머신",
        value=f"플레이: {stats['slot']['played']}회\n승리: {stats['slot']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🎲 주사위",
        value=f"플레이: {stats['dice']['played']}회\n승리: {stats['dice']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🃏 블랙잭",
        value=f"플레이: {stats['blackjack']['played']}회\n승리: {stats['blackjack']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🪙 동전던지기",
        value=f"플레이: {stats['bet']['played']}회\n승리: {stats['bet']['won']}회",
        inline=True
    )
    embed.add_field(
        name="💰 현재 잔액",
        value=f"{user_data['balance']:,} 코인",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ========================
# 추가 유용한 명령어
# ========================

@bot.tree.command(name="내통계", description="내 도박 통계 확인")
async def my_stats_cmd(interaction: discord.Interaction):
    """자신의 도박 통계를 확인합니다."""
    user_data = get_user_data(interaction.user.id)
    stats = user_data["stats"]
    
    embed = discord.Embed(
        title=f"📊 {interaction.user.display_name}님의 도박 통계",
        color=discord.Color.green()
    )
    
    total_played = sum(game["played"] for game in stats.values())
    total_won = sum(game["won"] for game in stats.values())
    win_rate = (total_won / total_played * 100) if total_played > 0 else 0
    
    embed.add_field(
        name="🎰 슬롯머신",
        value=f"플레이: {stats['slot']['played']}회\n승리: {stats['slot']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🎲 주사위",
        value=f"플레이: {stats['dice']['played']}회\n승리: {stats['dice']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🃏 블랙잭",
        value=f"플레이: {stats['blackjack']['played']}회\n승리: {stats['blackjack']['won']}회",
        inline=True
    )
    embed.add_field(
        name="🪙 동전던지기",
        value=f"플레이: {stats['bet']['played']}회\n승리: {stats['bet']['won']}회",
        inline=True
    )
    embed.add_field(
        name="📈 전체 통계",
        value=f"총 게임: {total_played}회\n총 승리: {total_won}회\n승률: {win_rate:.1f}%",
        inline=True
    )
    embed.add_field(
        name="💰 현재 잔액",
        value=f"{user_data['balance']:,} 코인",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="리더보드", description="코인 보유량 상위 10명")
async def leaderboard_cmd(interaction: discord.Interaction):
    """서버 내 코인 보유량 상위 10명을 표시합니다."""
    # 모든 유저 데이터를 잔액 기준으로 정렬
    sorted_users = sorted(
        economy_data["users"].items(),
        key=lambda x: x[1]["balance"],
        reverse=True
    )[:10]
    
    embed = discord.Embed(
        title="🏆 코인 리더보드 TOP 10",
        color=discord.Color.gold()
    )
    
    description = ""
    for idx, (user_id, data) in enumerate(sorted_users, 1):
        try:
            user = await bot.fetch_user(int(user_id))
            username = user.name
        except:
            username = f"Unknown User ({user_id})"
        
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"{idx}."
        description += f"{medal} **{username}** - {data['balance']:,} 코인\n"
    
    embed.description = description or "아직 플레이한 유저가 없습니다."
    await interaction.response.send_message(embed=embed)

# ========================
# 오류 처리
# ========================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingAnyRole):
        await interaction.response.send_message(
            "❌ 이 명령어를 사용할 권한이 없습니다! (관리자 전용)",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ 오류가 발생했습니다: {error}",
            ephemeral=True
        )

# ========================
# 봇 실행
# ========================

if __name__ == "__main__":
    # 봇 토큰을 여기에 입력하세요
    bot.run("TOKEN_HERE")