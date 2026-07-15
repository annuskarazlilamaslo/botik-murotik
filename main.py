import asyncio
import os
import random
import re

import discord
from discord.ext import commands

import config
from admin import is_admin, setup_admin_commands
from cloud_manager import (
    get_download_url, list_folder_contents, upload_track_to_cloud
)
from music_player import MusicPlayer
from texts import ADMIN_HELP_TEXT, HELP_TEXT, QUOTES
from user_folders import (
    get_folder_name,
    load_user_folders,
    save_user_folders,
)
from voice_folder_select import setup_playback_filter_commands

os.environ["NO_PROXY"] = config.YANDEX_DISK_API_DOMAIN

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
bot.remove_command("help")

player = MusicPlayer()

setup_admin_commands(bot, player)
setup_playback_filter_commands(bot, player)

is_skipping_backward = False


def pretty_name(filename):
    """Возвращает красивое имя трека без расширения и лишних символов"""

    return (
        re.sub(r"\(.*?\)", "", filename)
        .replace("_", " ")
        .replace(".mp3", "")
        .replace(".wav", "")
        .replace(".ogg", "")
        .strip()
    )


async def play_playlist(ctx, voice):
    """Воспроизводит треки из плейлиста по очереди"""

    global is_skipping_backward

    while True:

        if not ctx.voice_client or not voice or not voice.is_connected():
            return

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
        user = track.get("user", "Общий")

        try:
            stream_url = await get_download_url(track["path"])

        except Exception as e:
            print("❌ URL ERROR:", e)
            await asyncio.sleep(5)
            continue

        event = asyncio.Event()

        def after_play(error):
            """Вызывается после окончания трека или при ошибке"""

            if error:
                print("FFMPEG ERROR:", error)

            bot.loop.call_soon_threadsafe(event.set)

        source = discord.FFmpegPCMAudio(
            executable=config.FFMPEG_PATH,
            source=stream_url,
            before_options=(
                "-reconnect 1 "
                "-reconnect_streamed 1 "
                "-reconnect_delay_max 5"
            ),
            options="-vn",
        )

        await asyncio.to_thread(source.read)

        if not ctx.voice_client or not voice or not voice.is_connected():
            return

        try:
            voice.play(source, after=after_play)
        except Exception as e:
            print("❌ PLAY ERROR:", e)
            await asyncio.sleep(5)
            continue

        await ctx.send(
            f"▶️ Из папки **[{user}]** играет: `{pretty_name(filename)}`"
        )

        await event.wait()

        if is_skipping_backward:
            is_skipping_backward = False
            continue

        player.current_index += 1


@bot.event
async def on_ready():
    """Запуск бота"""

    await player.load_playlist()
    print(f"Ботик-муротик запущен как {bot.user}")


@bot.command(name="пинг", aliases=["ping", "алё"])
async def ping(ctx):
    """Проверка работоспособности бота"""

    await ctx.send("Мяу! 🐾")


@bot.command(name="игра", aliases=["play", "start", "begin", "играть"])
async def play(ctx):
    """Играть музыку"""

    if not ctx.author.voice:
        return await ctx.send("Зайди в голосовой канал")

    voice = ctx.voice_client

    if not voice:
        voice = await ctx.author.voice.channel.connect()

    if voice.is_paused():
        voice.resume()
        return await ctx.send("▶️ Продолжаю играть")

    if voice.is_playing():
        return await ctx.send(
            "🎶 Эй! Музыка уже играет. Зачем ты жмёшь эту кнопочку? 😿"
        )

    if not player.playlist:
        await player.load_playlist()

    if not player.playlist:
        return await ctx.send("В папке music пусто 😿")

    await ctx.send(f"🎶 Треков: {len(player.playlist)}")
    asyncio.create_task(play_playlist(ctx, voice))


@bot.command(name="обновить", aliases=["update", "синхронизировать", "апдейт"])
async def update(ctx):
    """Обновить список треков из облака"""

    await ctx.send("🔄 Обновляю список треков из облака, подожди...")
    await player.load_playlist()
    await ctx.send(
        f"✅ Готово! Всего треков в системе: {len(player.playlist)}"
    )


@bot.command(name="петля", aliases=["loop", "круг", "повтор", "цикл"])
async def loop(ctx):
    """Включить/выключить цикл воспроизведения по кругу"""

    mode = player.toggle_loop()
    await ctx.send(f"🔁 Цикл {'включён' if mode else 'выключен'}")


@bot.command(name="смешать", aliases=["shuffle", "шафл", "рандом"])
async def shuffle(ctx):
    """Включить/выключить перемешивание треков"""

    mode = player.toggle_shuffle()
    await ctx.send(f"🔀 Shuffle {'включён' if mode else 'выключен'}")


@bot.command(
    name="стоп",
    aliases=[
        "stop",
        "выйти",
        "уйти",
        "leave",
        "заткнись",
        "закройся",
        "тихо",
        "молчать",
        "уйди",
        "брысь",
    ],
)
async def stop(ctx):
    """Остановить музыку и выйти из голосового канала"""

    invoked_word = ctx.invoked_with.lower()

    secret_triggers = [
        "заткнись",
        "закройся",
        "тихо",
        "молчать"
        "уйди"
        "брысь"
        ]

    if invoked_word in secret_triggers:
        reply = random.choice(QUOTES)
        reply = reply.replace("{user}", ctx.author.name)
        await ctx.send(reply)
    else:
        await ctx.send("Пока-пока! 🐾")

    voice = ctx.voice_client
    if voice:
        try:
            if voice.is_playing() or voice.is_paused():
                voice.stop()
        except Exception:
            pass

        await voice.disconnect()


@bot.command(name="пауза", aliases=["pause"])
async def pause(ctx):
    """Поставить музыку на паузу"""

    voice = ctx.voice_client

    if not voice:
        return await ctx.send("Эй! Я вообще не в голосовом канале 😿")

    if voice.is_playing():
        voice.pause()
        return await ctx.send("⏸ Музыка поставлена на паузу")

    if voice.is_paused():
        return await ctx.send("⏸ Уже на паузе")

    await ctx.send("Эй! Музыка не играет! Зачем мы жмёшь эту кнопочку? 😿")


@bot.command(name="дальше", aliases=["next", "skip", "вперёд", "следующий"])
async def next(ctx):
    """Пропустить текущий трек (вперёд)"""

    global is_skipping_backward
    if not ctx.voice_client:
        return await ctx.send("Бот не подключен к голосовому каналу!")

    is_skipping_backward = False
    ctx.voice_client.stop()


@bot.command(name="назад", aliases=["prev", "back", "прошлый"])
async def prev(ctx):
    """Вернуться к предыдущему треку"""

    global is_skipping_backward

    if not ctx.voice_client:
        return await ctx.send("Бот не подключен к голосовому каналу!")

    if player.current_index > 0:
        player.current_index -= 1

    is_skipping_backward = True
    ctx.voice_client.stop()
    await ctx.send("⏮ Ну вот твой предыдущий трек")


@bot.command(name="помощь", aliases=["help"])
async def help(ctx):
    """Выводит список команд"""

    text = HELP_TEXT
    if is_admin(ctx):
        text += "\n\n" + ADMIN_HELP_TEXT

    await ctx.send(text)


@bot.command(name="добавить", aliases=["загрузить", "add", "upload"])
async def add_track(ctx):
    """Добавляет трек в облако и обновляет плейлист"""

    if not ctx.message.attachments:
        return await ctx.send(
            "🐱 Прикрепи файл **в этом же сообщении** вместе с командой "
                "`!добавить` — не отдельным сообщением, а сразу вместе, "
                "иначе я не смогу его отправить!\n"
                "Пример: набери `!добавить`, потом прикрепи файл "
                "кнопкой 📎 и отправь всё вместе."
            )

    folder_name = get_folder_name(ctx.author.id)
    if folder_name is None:
        return await ctx.send(
            "❌ У тебя ещё нет своей папки."
            " Сначала задай имя командой `!имя ТвоёИмя`"
        )

    folder_path = f"disk:/music/{folder_name}"

    success, files = await list_folder_contents(folder_path)
    if success and len(files) >= config.MAX_TRACKS_PER_USER:
        return await ctx.send(
            f"❌ У тебя уже {len(files)} треков — это максимум "
            f"({config.MAX_TRACKS_PER_USER}).\n"
            f"Хочешь посмотреть свой список? Нажми: `!треки`"
        )

    file = ctx.message.attachments[0]

    success, result = await upload_track_to_cloud(
        discord_file_url=file.url, filename=file.filename, username=folder_name
    )

    if success:
        await player.load_playlist()
        count = len(files) + 1 if files else 1
        await ctx.send(
            f"🎵 Трек добавлен! ({count}/{config.MAX_TRACKS_PER_USER})"
        )
    else:
        await ctx.send(f"❌ Ошибка: {result}")


@bot.command(name="имя")
async def set_folder_name(ctx, *, name: str):
    """Устанавливает имя папки для пользователя (можно только один раз)"""

    folders = load_user_folders()
    user_id = str(ctx.author.id)

    if user_id in folders:
        return await ctx.send(
            f"❌ У тебя уже есть папка `{folders[user_id]}`. "
            f"Поменять имя может только мой хозяин 🥸."
            f" Так что найди его, как правило, это админ канала."
            f" Возможно, их даже несколько..."
        )

    if name in folders.values():
        return await ctx.send(
            f"❌ Имя `{name}` уже занято другим пользователем."
        )

    folders[user_id] = name
    save_user_folders(folders)
    await ctx.send(
        f"✅ Твоя папка теперь называется `{name}`. Мм-р, мяу! 🐾"
    )


@bot.command(name="моя_папка")
async def my_folder(ctx):
    """Показывает имя своей папки"""

    folders = load_user_folders()
    user_id = str(ctx.author.id)

    if user_id not in folders:
        return await ctx.send(
            f"❌ У тебя ещё нет папки. Задай её командой `!имя ТвоёИмя`"
        )

    await ctx.send(f"📁 Твоя папка: `{folders[user_id]}`")


@bot.command(name="треки")
async def cmd_my_tracks(ctx):
    """Показывает список треков в папке пользователя"""

    folder_name = get_folder_name(ctx.author.id)

    if folder_name is None:
        return await ctx.send(
            f"❌ У тебя ещё нет своей папки."
            f" Сначала задай имя командой `!имя ТвоёИмя`"
        )

    folder_path = f"disk:/music/{folder_name}"
    success, files = await list_folder_contents(folder_path)

    if not success:
        return await ctx.send(
            f"❌ Не удалось получить список треков. Попробуй позже."
        )

    count = len(files)
    remaining = config.MAX_TRACKS_PER_USER - count

    if not files:
        return await ctx.send(
            f"📁 Папка `{folder_name}` пока пуста."
            f"Можешь загрузить {config.MAX_TRACKS_PER_USER} треков."
        )

    header = f"🎵 Твои треки (`{folder_name}`), всего: {len(files)}\n"
    await ctx.send(header)

    # Discord режет сообщения на 2000 символов - разбиваем список на части
    chunk = ""
    for i, name in enumerate(files, start=1):
        line = f"{i}. {name}\n"
        if len(chunk) + len(line) > 1900:
            await ctx.send(chunk)
            chunk = ""
        chunk += line

    if chunk:
        await ctx.send(chunk)


bot.run(config.DISCORD_TOKEN)
