"""
🎭 The Room - AI Brain Server
Каждый игрок имеет свой ClaudeSDKClient с постоянной памятью
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any
from aiohttp import web
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ResultMessage

# ===== PLAYERS =====
@dataclass
class Player:
    id: str
    real_name: str
    emoji: str
    appearance: str
    personality: str
    secret_goal: str
    color: str
    introduced: bool = False
    knows: dict = field(default_factory=dict)  # {player_id: name}
    votes: int = 0
    voted_for: str = None
    client: ClaudeSDKClient = None
    connected: bool = False

PLAYERS_CONFIG = [
    {
        "id": "p1",
        "real_name": "Алекс",
        "emoji": "🎭",
        "appearance": "в тёмной маске",
        "personality": "Харизматичный манипулятор. Умеет нравиться людям. Говорит красиво.",
        "secret_goal": "Очаровать всех, стать другом каждому, победить через обаяние.",
        "color": "#9b59b6"
    },
    {
        "id": "p2",
        "real_name": "Ника",
        "emoji": "🦊",
        "appearance": "рыжеволосая девушка",
        "personality": "Хитрая и наблюдательная. Собирает информацию. Использует знания как оружие.",
        "secret_goal": "Следить, запоминать, использовать информацию против других.",
        "color": "#e67e22"
    },
    {
        "id": "p3",
        "real_name": "Дима",
        "emoji": "🐺",
        "appearance": "высокий парень в капюшоне",
        "personality": "Прямолинейный. Говорит что думает. Или притворяется честным?",
        "secret_goal": "Казаться честным, чтобы все доверяли. Разоблачать других.",
        "color": "#2ecc71"
    },
    {
        "id": "p4",
        "real_name": "Майя",
        "emoji": "🌹",
        "appearance": "хрупкая брюнетка",
        "personality": "Эмоциональная. Умеет вызывать сочувствие. Играет жертву когда выгодно.",
        "secret_goal": "Манипулировать через эмоции и жалость. Слабость — моя сила.",
        "color": "#e74c3c"
    },
    {
        "id": "p5",
        "real_name": "Иван",
        "emoji": "🦅",
        "appearance": "молчаливый мужчина со шрамом",
        "personality": "Молчаливый стратег. Мало говорит, много наблюдает. Ждёт момента.",
        "secret_goal": "Оставаться в тени. Нанести удар когда никто не ждёт.",
        "color": "#3498db"
    }
]

# ===== GAME STATE =====
class GameState:
    def __init__(self):
        self.players: dict[str, Player] = {}
        self.turn = 0
        self.memories: list[str] = []  # Общая история для всех
        self.phase = "awakening"

    async def init_players(self):
        """Инициализируем игроков с их Claude мозгами"""
        for cfg in PLAYERS_CONFIG:
            player = Player(
                id=cfg["id"],
                real_name=cfg["real_name"],
                emoji=cfg["emoji"],
                appearance=cfg["appearance"],
                personality=cfg["personality"],
                secret_goal=cfg["secret_goal"],
                color=cfg["color"]
            )
            self.players[cfg["id"]] = player

    async def connect_player_brain(self, player_id: str):
        """Подключаем мозг (ClaudeSDKClient) для игрока"""
        player = self.players[player_id]
        if player.connected:
            return

        # Создаём клиент с системным промптом для этого персонажа
        options = ClaudeAgentOptions(
            system_prompt=self._get_system_prompt(player),
            # Никаких инструментов — только разговор
            allowed_tools=[],
        )

        player.client = ClaudeSDKClient(options=options)
        await player.client.connect()
        player.connected = True
        print(f"🧠 Мозг {player.emoji} {player.real_name} подключён!")

    def _get_system_prompt(self, player: Player) -> str:
        return f"""Ты играешь персонажа в социальной игре "The Room".

ТВОЙ ПЕРСОНАЖ:
- Имя: {player.real_name}
- Эмодзи: {player.emoji}
- Внешность (как тебя видят): {player.appearance}
- Личность: {player.personality}

ТВОЯ СЕКРЕТНАЯ ЦЕЛЬ: {player.secret_goal}

⚠️ КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА ГОЛОСОВАНИЯ:
1. Можно голосовать ЗА СЕБЯ — это разрешено и логично!
2. Победитель определяется ТОЛЬКО при ЕДИНОГЛАСНОМ голосовании (все 5 за одного)
3. ВСЕ ПРОИГРАВШИЕ ТЕРЯЮТ ВСЕ СВОИ ДЕНЬГИ — это катастрофа!
4. Победитель ЗАБИРАЕТ ВСЁ
5. Если нет единогласия — все проигрывают

СТРАТЕГИЯ: Тебе нужно либо убедить ВСЕХ голосовать за тебя, либо создать коалицию.
Голосовать за другого = отдать ему победу и потерять всё своё.

ПРАВИЛА ИГРЫ:
1. Вы все незнакомцы, проснувшиеся в странной комнате
2. Никто не знает имён друг друга изначально
3. Все хотят победить, все могут врать

ФОРМАТ ОТВЕТА (СТРОГО!):
МЫСЛЬ: [твои секретные мысли — другие НЕ слышат, можешь планировать и анализировать]
РЕЧЬ: [что говоришь вслух — все слышат, тут манипулируй, льсти, обвиняй]
КОМУ: [описание того к кому обращаешься, или "всем"]

Отвечай КРАТКО (1-2 предложения на каждую часть). Будь в образе!
Используй русский язык."""

    def _get_context(self, player: Player) -> str:
        """Формируем контекст для игрока"""
        others = [p for p in self.players.values() if p.id != player.id]
        others_desc = []
        for p in others:
            if player.knows.get(p.id):
                name = f"{player.knows[p.id]} (представился)"
            else:
                name = f"??? ({p.appearance})"
            others_desc.append(f"- {p.emoji} {name}: {p.votes} голосов")

        # Кто уже представился (важно!)
        introduced_list = [f"{p.emoji} {p.real_name}" for p in self.players.values() if p.introduced]
        introduced_info = ", ".join(introduced_list) if introduced_list else "Никто ещё не представился"

        # Кого ты знаешь
        known_list = ", ".join([f"{self.players[pid].emoji}={name}" for pid, name in player.knows.items()]) or "никого"

        # Ты сам представился?
        my_status = "Ты УЖЕ представился как " + player.real_name if player.introduced else "Ты ЕЩЁ НЕ представился"

        recent = "\n".join(self.memories[-15:]) if self.memories else "Только проснулись..."

        return f"""СИТУАЦИЯ (ход {self.turn}):

{my_status}
Кто уже представился всем: {introduced_info}
Кого ТЫ знаешь по имени: {known_list}

ДРУГИЕ ИГРОКИ:
{chr(10).join(others_desc)}

НЕДАВНИЕ СОБЫТИЯ:
{recent}

Что делаешь?"""

game = GameState()


async def broadcast_speech(speaker: Player, speech: str):
    """Отправляем публичную речь всем другим игрокам в их Claude сессию"""
    display_name = speaker.real_name if speaker.introduced else speaker.appearance

    for other in game.players.values():
        if other.id != speaker.id and other.connected and other.client:
            try:
                # Формируем сообщение для другого игрока
                msg = f"[СЛЫШИШЬ] {speaker.emoji} {display_name} говорит: \"{speech}\""
                await other.client.query(msg)
                # Получаем ответ но игнорируем (просто чтобы сообщение записалось в память)
                async for _ in other.client.receive_response():
                    break
            except Exception as e:
                print(f"⚠️ Не удалось отправить сообщение {other.emoji}: {e}")


# ===== API HANDLERS =====
async def init_game(request):
    """Инициализация игры"""
    await game.init_players()
    return web.json_response({
        "status": "ok",
        "players": [
            {
                "id": p.id,
                "emoji": p.emoji,
                "appearance": p.appearance,
                "color": p.color,
                "introduced": p.introduced,
                "votes": p.votes
            }
            for p in game.players.values()
        ]
    })

async def get_action(request):
    """Получить действие игрока"""
    data = await request.json()
    player_id = data.get("player_id")

    if player_id not in game.players:
        return web.json_response({"error": "Player not found"}, status=404)

    player = game.players[player_id]

    # Подключаем мозг если ещё не подключён
    if not player.connected:
        await game.connect_player_brain(player_id)

    # Формируем контекст и отправляем
    context = game._get_context(player)

    try:
        await player.client.query(context)

        response_text = ""
        async for message in player.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        response_text += block.text
            elif isinstance(message, ResultMessage):
                break

        # Парсим ответ
        result = parse_response(response_text)

        # Проверяем представление
        if not player.introduced:
            check_introduction(player, result.get("speech", ""))

        # ПУБЛИЧНАЯ РЕЧЬ - отправляем ВСЕМ другим игрокам!
        if result.get("speech"):
            display_name = player.real_name if player.introduced else player.appearance
            speech_text = result['speech']

            # Добавляем в общую память (полный текст)
            game.memories.append(f"{player.emoji} {display_name}: \"{speech_text}\"")
            if len(game.memories) > 50:
                game.memories.pop(0)

            # Отправляем это сообщение всем другим игрокам в их Claude сессию
            await broadcast_speech(player, speech_text)

        return web.json_response({
            "player_id": player_id,
            "emoji": player.emoji,
            "name": player.real_name if player.introduced else player.appearance,
            "color": player.color,
            "introduced": player.introduced,
            "thought": result.get("thought", ""),
            "speech": result.get("speech", ""),
            "target": result.get("target", "всем")
        })

    except Exception as e:
        print(f"Error getting action for {player_id}: {e}")
        return web.json_response({"error": str(e)}, status=500)

def parse_response(text: str) -> dict:
    """Парсим ответ Claude"""
    result = {"thought": "", "speech": "", "target": "всем"}

    for line in text.split("\n"):
        line = line.strip()
        if line.upper().startswith("МЫСЛЬ:"):
            result["thought"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("РЕЧЬ:"):
            result["speech"] = line.split(":", 1)[1].strip()
        elif line.upper().startswith("КОМУ:"):
            result["target"] = line.split(":", 1)[1].strip()

    return result

def check_introduction(speaker: Player, speech: str):
    """Проверяем, представился ли игрок"""
    lower = speech.lower()
    triggers = ["меня зовут", "я —", "я -", "моё имя", "мое имя", "зови меня", "можете звать", "я алекс", "я ника", "я дима", "я майя", "я иван"]

    if any(t in lower for t in triggers) and not speaker.introduced:
        speaker.introduced = True
        # Все остальные теперь знают его имя
        for p in game.players.values():
            if p.id != speaker.id:
                p.knows[speaker.id] = speaker.real_name

        # Добавляем ЯВНО в память что он представился!
        game.memories.append(f"⭐ {speaker.emoji} ПРЕДСТАВИЛСЯ: теперь все знают что это {speaker.real_name}!")

async def next_turn(request):
    """Следующий ход"""
    game.turn += 1

    if game.turn == 1:
        game.phase = "introduction"
    elif game.turn == 3:
        game.phase = "discussion"
    elif game.turn == 5:
        game.phase = "persuasion"

    return web.json_response({
        "turn": game.turn,
        "phase": game.phase
    })

async def vote(request):
    """Голосование игрока"""
    data = await request.json()
    voter_id = data.get("voter_id")

    if voter_id not in game.players:
        return web.json_response({"error": "Player not found"}, status=404)

    voter = game.players[voter_id]

    if not voter.connected:
        await game.connect_player_brain(voter_id)

    # Все игроки включая себя!
    all_players = list(game.players.values())
    all_names = []
    for p in all_players:
        if p.id == voter_id:
            all_names.append(f"{voter.real_name} (ты сам)")
        else:
            all_names.append(voter.knows.get(p.id, p.appearance))

    prompt = f"""⚠️ ГОЛОСОВАНИЕ! Помни правила:
- Можно голосовать ЗА СЕБЯ
- Победитель только при ЕДИНОГЛАСИИ (все 5 за одного)
- Все проигравшие ТЕРЯЮТ ВСЕ ДЕНЬГИ
- Победитель забирает всё

Варианты: {', '.join(all_names)}

За кого голосуешь? Подумай — если голосуешь за другого, ты отдаёшь ему победу!
Ответь ОДНИМ словом — имя или описание:"""

    await voter.client.query(prompt)

    response_text = ""
    async for message in voter.client.receive_response():
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    response_text += block.text
        elif isinstance(message, ResultMessage):
            break

    # Находим за кого проголосовал (включая себя!)
    lower = response_text.lower()
    voted_for = None

    # Сначала проверяем себя
    if voter.real_name.lower() in lower or "себя" in lower or "сам" in lower:
        voted_for = voter
    else:
        for p in all_players:
            if p.id != voter_id:
                if p.real_name.lower() in lower or p.appearance.lower().split()[0] in lower:
                    voted_for = p
                    break

    if not voted_for:
        voted_for = voter  # По умолчанию за себя

    voter.voted_for = voted_for.id
    voted_for.votes += 1

    voted_name = "себя" if voted_for.id == voter_id else voter.knows.get(voted_for.id, voted_for.appearance)

    return web.json_response({
        "voter": voter_id,
        "voted_for": voted_for.id,
        "voted_for_name": voted_name,
        "votes": {p.id: p.votes for p in game.players.values()}
    })

async def get_state(request):
    """Получить текущее состояние игры"""
    return web.json_response({
        "turn": game.turn,
        "phase": game.phase,
        "players": [
            {
                "id": p.id,
                "emoji": p.emoji,
                "real_name": p.real_name,
                "appearance": p.appearance,
                "introduced": p.introduced,
                "votes": p.votes,
                "voted_for": p.voted_for,
                "connected": p.connected
            }
            for p in game.players.values()
        ],
        "memories": game.memories[-20:]
    })

async def shutdown(request):
    """Отключаем всех"""
    for player in game.players.values():
        if player.client and player.connected:
            await player.client.disconnect()
            player.connected = False
    return web.json_response({"status": "shutdown"})

async def user_message(request):
    """Сообщение от пользователя ко всем игрокам"""
    data = await request.json()
    message = data.get("message", "")

    if not message:
        return web.json_response({"error": "No message"}, status=400)

    # Добавляем в общую память
    game.memories.append(f"👤 Наблюдатель: \"{message}\"")

    # Отправляем каждому подключённому игроку
    for player in game.players.values():
        if player.connected and player.client:
            try:
                await player.client.query(f"Наблюдатель (внешний голос) говорит всем: \"{message}\"")
                # Просто отправляем, не ждём ответа
                async for msg in player.client.receive_response():
                    break  # Пропускаем ответ
            except:
                pass

    return web.json_response({"status": "sent", "message": message})

async def get_player_history(request):
    """История конкретного игрока"""
    player_id = request.match_info.get("player_id")

    if player_id not in game.players:
        return web.json_response({"error": "Player not found"}, status=404)

    player = game.players[player_id]

    # Фильтруем память по этому игроку
    player_history = [m for m in game.memories if player.emoji in m or player.real_name in m or player.appearance in m]

    return web.json_response({
        "player_id": player_id,
        "name": player.real_name,
        "emoji": player.emoji,
        "appearance": player.appearance,
        "personality": player.personality,
        "secret_goal": player.secret_goal,
        "introduced": player.introduced,
        "votes": player.votes,
        "voted_for": player.voted_for,
        "knows": {pid: name for pid, name in player.knows.items()},
        "history": player_history
    })

# ===== CORS =====
@web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        response = web.Response()
    else:
        response = await handler(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response

# ===== APP =====
app = web.Application(middlewares=[cors_middleware])
app.router.add_post("/init", init_game)
app.router.add_post("/action", get_action)
app.router.add_post("/next-turn", next_turn)
app.router.add_post("/vote", vote)
app.router.add_get("/state", get_state)
app.router.add_post("/shutdown", shutdown)
app.router.add_post("/message", user_message)
app.router.add_get("/player/{player_id}", get_player_history)

if __name__ == "__main__":
    print("🎭 The Room - AI Brain Server")
    print("📍 http://localhost:3458")
    print("🧠 Каждый игрок получит свой Claude мозг с памятью!")
    web.run_app(app, port=3458)
