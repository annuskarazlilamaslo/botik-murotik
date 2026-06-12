import os
import asyncio
import psutil
import discord
from discord.ext import commands

import config
from cloud_manager import sync_music_from_cloud
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

async def play_playlist(ctx, voice):
    """Фоновый цикл проигрывания треков"""
    global is_skipping_backward
    while voice and voice.is_connected():
        if not player.playlist:
            await ctx.send("Плейлист пуст 😿")
            break
        
        if player.current_index >= len(player.playlist):
            player.current_index = 0

        filename = player.playlist[player.current_index]
        path = os.path.join(config.MUSIC_DIR, filename)
        
        if not os.path.exists(path):
            await ctx.send(f"❌ Файл {filename} не найден, пропускаю...")
            player.current_index += 1
            continue
        
        if voice.is_playing():
            voice.stop()

        source = discord.FFmpegPCMAudio(
            executable=config.FFMPEG_PATH,
            source=path,
            options="-vn -ac 2 -ar 48000 -threads 2"
        )

        voice.play(source)
        await ctx.send(f"▶️ Играю: {filename}")
        await asyncio.sleep(1)

        while voice.is_playing() or voice.is_paused():
            await asyncio.sleep(1)
            if not voice.is_connected():
                return
        
        if is_skipping_backward:
            is_skipping_backward = False
            continue
        
        player.current_index += 1
        if player.current_index >= len(player.playlist):
            if player.loop_mode:
                player.current_index = 0
            else:
                await ctx.send("⏹ Плейлист закончен")
                break

@bot.event
async def on_ready():
    await asyncio.to_thread(sync_music_from_cloud)
    player.load_playlist()
    print(f'Ботик-муротик успешно запущен как {bot.user}')

@bot.command()
async def play(ctx):
    if not ctx.author.voice:
        return await ctx.send("Зайди в голосовой канал")

    voice = ctx.voice_client or await ctx.author.voice.channel.connect()

    player.load_playlist()
    if not player.playlist:
        return await ctx.send("В папке music пусто 😿")
    
    if voice.is_playing() or voice.is_paused():
        await ctx.send(f"🎶 Плейлист обновлен! Найдено треков: {len(player.playlist)}. Продолжаю играть.")
        return

    await ctx.send(f"🎶 Найдено треков: {len(player.playlist)}")
    await play_playlist(ctx, voice)

@bot.command()
async def update(ctx):
    await ctx.send("🔄 Скачиваю свежие треки из облака, подожди...")
    await asyncio.to_thread(sync_music_from_cloud)
    player.load_playlist()
    await ctx.send(f"✅ Готово! Всего треков в системе: {len(player.playlist)}")

@bot.command()
async def loop(ctx):
    mode = player.toggle_loop()
    await ctx.send(f"🔁 Цикл {'включён' if mode else 'выключен'}")

@bot.command()
async def shuffle(ctx):
    mode = player.toggle_shuffle()
    await ctx.send(f"🔀 Shuffle {'включён' if mode else 'выключен'}")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Пока-пока! 🐾")
        
@bot.command()
async def pause(ctx):
    """Поставить музыку на паузу"""
    voice = ctx.voice_client
    if voice and voice.is_playing():
        voice.pause()
        await ctx.send("⏸ Музыка поставлена на паузу")
    else:
        await ctx.send("Эй! Музыка не играет! Зачем мы жмёшь эту кнопочку? 😿")

@bot.command()
async def resume(ctx):
    """Продолжить воспроизведение с паузы"""
    voice = ctx.voice_client
    if voice and voice.is_paused():
        voice.resume()
        await ctx.send("▶️ Музыка продолжается")
    else:
        await ctx.send("Ну камон!Музыка не стоит на паузе!")

@bot.command()
async def next(ctx):
    """Пропустить текущий трек (вперед)"""
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏭ Трек пропущен")

@bot.command()
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

@bot.command()
async def help(ctx):
    text = (
        "🐾 **Мяу! Я умею вот что:**\n\n"
        "🎵 **Проигрывать музыку:**\n"
        "`!play` — начну проигрывать плейлист\n"
        "`!next` — пропущу текущий трек\n"
        "`!stop` — остановлю музыку и выйду\n"
        "`!update` — скачать новые треки из Google Диска 🔄\n\n"
        "🔁 **Режимы воспроизведения:**\n"
        "`!loop` — зацикливаю плейлист по кругу\n"
        "`!shuffle` — играю треки вразброс\n\n"
        "Просто напиши команду в чат 😺"
    )
    await ctx.send(text)
    
@bot.event
async def on_ready():
    """Выполняется при запуске бота"""
    from keep_alive import start_server
    asyncio.create_task(start_server())

    await asyncio.to_thread(sync_music_from_cloud)
    player.load_playlist()
    print(f'Ботик-муротик успешно запущен как {bot.user}')

bot.run(config.DISCORD_TOKEN)