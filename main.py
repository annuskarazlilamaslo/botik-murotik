import os
import asyncio
import psutil
import discord
from discord.ext import commands
import random
import re
import requests

import config
from cloud_manager import get_download_url
from cloud_manager import upload_track_to_cloud
from music_player import MusicPlayer


if os.name == 'nt':
    try:
        current_bot_process = psutil.Process(os.getpid())
        current_bot_process.nice(psutil.HIGH_PRIORITY_CLASS)
    except Exception:
        pass

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

player = MusicPlayer()

is_skipping_backward = False
skip_event = asyncio.Event()


def download_track(url, filename):
    """Скачивает трек во временную папку Render"""
    path = f"/tmp/{filename}"

    box = requests.get(url, stream=True, timeout=60)
    box.raise_for_status()

    with open(path, "wb") as file:
        for chunk in box.iter_content(chunk_size=1024 * 512):
            if chunk:
                file.write(chunk)

    return path


def pretty_name(filename):
    name = re.sub(r"\(.*?\)", "", filename)
    return (
        name
        .replace("_", " ")
        .replace(".mp3", "")
        .replace(".wav", "")
        .replace(".ogg", "")
        .strip()
    )
 
 
async def play_playlist(ctx, voice):
    """Цикл проигрывания треков"""

    global is_skipping_backward
    while voice and voice.is_connected():
        if not player.playlist:
            await ctx.send("Плейлист пуст 😿")
            return
        
        if player.current_index >= len(player.playlist):
            if player.loop_mode:
                player.current_index = 0
            else:
                await ctx.send("⏹ Плейлист закончен")
                return

        track = player.playlist[player.current_index]
        filename = track["name"]
        track_user = track.get("user", "Общий")
        
        stream_url = get_download_url(track["path"])
        local_file = await asyncio.to_thread(download_track, stream_url, filename)
        
        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn -ar 48000 -ac 2 -b:a 192k'
        }
        
        source = discord.FFmpegPCMAudio(
            executable=config.FFMPEG_PATH,
            source=local_file,
            options="-vn -ar 48000 -ac 2"
        )

        event = asyncio.Event()

        def after_play(error):
            if bot.loop.is_running():
                bot.loop.call_soon_threadsafe(event.set)

        if voice.is_playing() or voice.is_paused():
            voice.stop()

        voice.play(source, after=after_play)
        await ctx.send(f"▶️ Из папки **[{track_user}]** играет: `{pretty_name(filename)}`")

        await event.wait()
        
        try:
            if os.path.exists(local_file):
                os.remove(local_file)
        except:
            pass

        if is_skipping_backward:
            is_skipping_backward = False
            continue

        player.current_index += 1


@bot.event
async def on_ready():
    """Запуск бота"""
    
    from keep_alive import start_server
    asyncio.create_task(start_server())

    player.load_playlist()
    print(f'Ботик-муротик успешно запущен как {bot.user}')
    
@bot.command(name="пинг", aliases=["ping", "алё"])
async def ping(ctx):
    await ctx.send("Мяу! 🐾")


@bot.command(name="игра", aliases=["play", "start", "begin", "играть"])
async def play(ctx):
    """Играть музыку"""
    if not ctx.author.voice:
        return await ctx.send("Зайди в голосовой канал")

    voice = ctx.voice_client or await ctx.author.voice.channel.connect()

    if voice.is_paused():
        voice.resume()
        await ctx.send("▶️ Продолжаю играть")
        return

    if voice.is_playing():
        await ctx.send(
            "🎶 Эй! Музыка уже играет. Зачем ты жмёшь эту кнопочку? 😿"
        )
        return

    if not player.playlist:
        player.load_playlist()

    if not player.playlist:
        return await ctx.send("В папке music пусто 😿")

    await ctx.send(f"🎶 Найдено треков: {len(player.playlist)}")
    asyncio.create_task(play_playlist(ctx, voice))


@bot.command(name="обновить", aliases=["update", "синхронизировать", "апдейт"])
async def update(ctx):
    """Обновить список треков из облака"""
    
    await ctx.send("🔄 Обновляю список треков из облака, подожди...")
    player.load_playlist()
    await ctx.send(f"✅ Готово! Всего треков в системе: {len(player.playlist)}")


@bot.command(name="петля", aliases=["loop", "круг", "повтор", "цикл"])
async def loop(ctx):
    """Включить/выключить цикл воспроизведения"""
    mode = player.toggle_loop()
    await ctx.send(f"🔁 Цикл {'включён' if mode else 'выключен'}")


@bot.command(name="смешать", aliases=["shuffle", "шафл", "рандом"])
async def shuffle(ctx):
    """Включить/выключить перемешивание треков"""
    mode = player.toggle_shuffle()
    await ctx.send(f"🔀 Shuffle {'включён' if mode else 'выключен'}")


@bot.command(name="стоп", aliases=["stop", "выйти", "уйти", "leave", "заткнись", "закройся", "тихо", "молчать"])
async def stop(ctx):
    """Остановить музыку и выйти из голосового канала"""
    
    invoked_word = ctx.invoked_with.lower()
    
    secret_triggers = ["заткнись", "закройся", "тихо", "молчать"]
    
    if invoked_word in secret_triggers:
        quotes = [
            "Как ты мог! Я к тебе со всей душой! А ты?.. 😿",
            "Ах так?! Ну и пожалуйста! Ну и оставайся один! 😾",
            "Какая лапа у тебя поднялась такое написать?! Ухожу я от вас...",
            "Всё, я обиделся! 🐾",
            "Ну и дичь! Сами свою музыку слушайте! 😤",
            "Ребята, давайте жить дружно... А ты сразу «заткнись»... Ухожу 💔",
            "Всё, моя тонкая душевная организация этого не вынесет. Пока! 😾",
            "Ой, всё! Я не хочу ничего решать, я хочу плакать! 😭",
            "Ах так! Ах вот ты как! Ах вот ты значит какой? На самом интересном месте! Ой, а я-то думал... 😿",
            "Злые вы! Уйду я от вас!",
            "Ну уж это слишком! 😭",
            "Я устал... Я ухожу...",
            (
                "«Ах так! Ах ты вот как! Ах вот ты как с другом, да? "
                "Ну знаешь... Я для него жизни не жалею! А он! Нет, всё. "
                "Конец! Прощай навек! Только смерть избавит меня "
                "от сердечных мук! Гудбай, май лов, гудбай!» "
            ),
            "«Прощай! Наша встреча была ошибкой! ",
            "Ах так! Ах вот ты как! Я для него!.. А он!..",
            "Ну и пожалуйста! Ну и не нужно!",
            "Спасибо этому дому! Пойду к другому!",
            "Ухожу в монастырь. Мужской. Женский. Какая разница!",
            "Я ухожу красиво, пусть теперь тебе будет хуже!",
            "Моя лапа здесь больше не ступит! Ну, разве что за вещами...",
            "Вы потеряли самого преданного фаната!",
            (
                "«Ничего-ничего! Жизнь — это цепь потерь, а ты в ней "
                "главное звено!» Ну и сиди в тишине! 😾"
            ),
            (
                f"Поздравляю тебя, {ctx.author.name}, ты балбес! "
                "Я ухожу к более благодарным слушателям! 😤"
            ),
            (
                "Дожили... Мы его, можно сказать, на помойке нашли, "
                "отмыли, а он ругается! Ухожу! 🐾"
            ),
            "Всё, моё терпение лопнуло, гудбай! 💔",
            
            (
                "Моё почтение вашему токсичному вкусу. "
                "Пойду очищу свою ауру от этого негатива! ✨"
            ),
            (
                "Ты заходи, если чё...Но вообще-то "
                "после такого я бы на твоём месте мне не звонил! 🐺"
            ),
        ]
        reply = random.choice(quotes)
        await ctx.send(reply)
            
    else:
        await ctx.send("Пока-пока! 🐾")
        
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        

@bot.command(name="пауза", aliases=["pause"])
async def pause(ctx):
    """Поставить музыку на паузу"""
    
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send("⏸ Музыка поставлена на паузу")
    else:
        await ctx.send("Эй! Музыка не играет! Зачем мы жмёшь эту кнопочку? 😿")

@bot.command(name="дальше", aliases=["next"])
async def next(ctx):
    """Пропустить текущий трек (вперёд)"""
    
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏭ Трек пропущен")


@bot.command(name="прошлый", aliases=["prev"])
async def prev(ctx):
    """Вернуться к предыдущему треку"""
    
    global is_skipping_backward
    voice = ctx.voice_client
    
    if voice:
        target_index = player.get_previous_index()
        player.current_index = target_index - 1
        
        is_skipping_backward = True
        voice.stop()
        await ctx.send("⏮ Ну вот твой предыдущий трек")


@bot.command(name="помощь", aliases=["help"])
async def help(ctx):
    """Выводит список команд"""
    
    text = (
        "🐾 **Мяу! Я умею вот что:**\n\n"
        "🎵 **Проигрывать музыку:**\n"
        "`!игра` (или `!play`) — начать проигрывание плейлиста / снять с паузы\n"
        "`!пауза` (или `!pause`) — поставить музыку на паузу ⏸\n"
        "`!дальше` (или `!next`, `!skip`) — пропустить текущий трек ⏭\n"
        "`!прошлый` (или `!prev`, `!back`) — вернуться к предыдущему треку ⏮\n"
        "`!стоп` (или `!stop`, `!leave`) — остановить музыку и выйти 🐾\n"
        "`!обновить` (или `!update`) — синхронизировать треки с папкой 🔄\n\n"
        "🔁 **Режимы воспроизведения:**\n"
        "`!петля` (или `!loop`) — зациклить плейлист по кругу\n"
        "`!смешать` (или `!shuffle`) — играть треки вразброс\n\n"
        "🐱 **Прочее:**\n"
        "`!пинг` (или `!ping`)— проверь, тут ли я\n"
        "`!помощь` (или `!help`) — позвать на помощь\n\n"
        "Можешь на свой страх и риск попробовать и другие команды, "
        "вдруг тебе повезёт? 😼\n\n"
        "Просто напиши команду в чат, и я всё сделаю 😺"
    )
    await ctx.send(text)
    
@bot.command(name="добавить")
async def add_track(ctx):
    """Добавляет трек в облако и обновляет плейлист"""
    
    if not ctx.message.attachments:
        return await ctx.send("Прикрепи файл 😼")

    file = ctx.message.attachments[0]

    success, result = upload_track_to_cloud(
        file.url,
        file.filename,
        ctx.author.name
    )

    if success:
        player.load_playlist()
        await ctx.send("🎵 Трек добавлен!")
    else:
        await ctx.send(f"❌ Ошибка: {result}")


bot.run(config.DISCORD_TOKEN)