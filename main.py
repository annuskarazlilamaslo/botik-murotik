import os
import asyncio
import discord
from discord.ext import commands
import random
import re
import requests

import config
from cloud_manager import get_download_url, upload_track_to_cloud
from music_player import MusicPlayer
from texts import HELP_TEXT, QUOTES

bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
bot.remove_command("help")

player = MusicPlayer()

is_skipping_backward = False
skip_event = asyncio.Event()


def download_track(url, filename):
    path = f"/tmp/{filename}"
    r = requests.get(url, stream=True, timeout=60)
    r.raise_for_status()

    with open(path, "wb") as f:
        for chunk in r.iter_content(1024 * 256):
            f.write(chunk)

    return path


def pretty_name(filename):
    return re.sub(r"\(.*?\)", "", filename)\
        .replace("_", " ")\
        .replace(".mp3", "")\
        .replace(".wav", "")\
        .replace(".ogg", "")\
        .strip()


async def play_playlist(ctx, voice):
    print("🟢 START LOOP") #
    global is_skipping_backward
    
    print(f"🎧 PLAY INDEX: {player.current_index}") #

    while True:
        
        if not ctx.voice_client or not voice or not voice.is_connected():
            print("❌ Voice disconnected")
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
        print(
            "🎵 NEXT TRACK:",
            player.current_index,
            track["name"] #
        )

        filename = track["name"]
        user = track.get("user", "Общий")
        
        try:

            stream_url = get_download_url(track["path"])

            local_file = await asyncio.to_thread(
                download_track, stream_url, filename
            )
        except Exception as e:
            print("❌ DOWNLOAD ERROR:", e)

            await asyncio.sleep(5)
            continue

        event = asyncio.Event()

        def after_play(err):
            if err:
                print("FFMPEG ERROR:", err)

        bot.loop.call_soon_threadsafe(event.set)

        source = discord.FFmpegPCMAudio(
            executable=config.FFMPEG_PATH,
            source=local_file,
            #options="-vn -loglevel quiet"
            options="-vn -loglevel verbose"
        )
        
        if not ctx.voice_client or not voice or not voice.is_connected():
            return

        print("▶️ voice.play()") #
        try:
            voice.play(source, after=after_play)
        except Exception as e:
            print("❌ PLAY ERROR:", e)
            await asyncio.sleep(5)
            continue
        print("⏳ waiting event")

        await ctx.send(
            f"▶️ Из папки **[{user}]** играет: `{pretty_name(filename)}`"
        )

        await event.wait()
        print("✅ event finished") #
        print(
            "VOICE:",
            voice.is_connected(),
            voice.is_playing()
        )

        try:
            os.remove(local_file)
        except Exception:
            pass
        print("💀 AFTER TRACK CLEANUP")#

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
    """Проверка работоспособности бота"""
    
    await ctx.send("Мяу! 🐾")


@bot.command(name="игра", aliases=["play", "start", "begin", "играть"])
async def play(ctx):
    """Играть музыку"""
    
    if not ctx.author.voice:
        return await ctx.send("Зайди в голосовой канал")

    voice = ctx.voice_client or await ctx.author.voice.channel.connect()

    if voice.is_paused():
        voice.resume()
        return await ctx.send("▶️ Продолжаю играть")

    if voice.is_playing():
        return await ctx.send(
            "🎶 Эй! Музыка уже играет. Зачем ты жмёшь эту кнопочку? 😿"
        )

    if not player.playlist:
        player.load_playlist()

    if not player.playlist:
        return await ctx.send("В папке music пусто 😿")

    await ctx.send(f"🎶 Треков: {len(player.playlist)}")
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
        except:
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

@bot.command(name="дальше", aliases=["next"])
async def next(ctx):
    """Пропустить текущий трек (вперёд)"""
    
    global is_skipping_backward
    is_skipping_backward = False
    ctx.voice_client.stop()
    player.current_index += 1


@bot.command(name="прошлый", aliases=["prev"])
async def prev(ctx):
    """Вернуться к предыдущему треку"""
    
    global is_skipping_backward
    
    if player.current_index > 0:
        player.current_index -= 1

    is_skipping_backward = True
    ctx.voice_client.stop()
    await ctx.send("⏮ Ну вот твой предыдущий трек")


@bot.command(name="помощь", aliases=["help"])
async def help(ctx):
    """Выводит список команд"""
    
    await ctx.send(HELP_TEXT)
    
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