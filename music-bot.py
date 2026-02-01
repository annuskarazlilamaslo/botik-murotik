import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import random
from config import DISCORD_TOKEN


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
bot.remove_command("help")

playlist = []
current_index = 0
loop_mode = False
shuffle_mode = False


def load_playlist():
    return [
        f for f in os.listdir("music")
        if f.lower().endswith((".mp3", ".wav", ".ogg"))
    ]


async def play_playlist(ctx, voice):
    global current_index

    while True:
        if not playlist:
            await ctx.send("Плейлист пуст 😿")
            return

        filename = playlist[current_index]
        path = os.path.join("music", filename)

        source = discord.FFmpegPCMAudio(
            executable="ffmpeg.exe",
            source=path,
            options="-vn -ac 2 -ar 48000"
        )

        voice.play(source)
        await ctx.send(f"▶️ Играю: {filename}")

        while voice.is_playing():
            await asyncio.sleep(1)

        # выбираем следующий трек
        if shuffle_mode:
            current_index = random.randint(0, len(playlist) - 1)
        else:
            current_index += 1
            if current_index >= len(playlist):
                if loop_mode:
                    current_index = 0
                else:
                    await ctx.send("⏹ Плейлист закончен")
                    return


@bot.event
async def on_ready():
    print(f'Ботик-муротик запущен как {bot.user}')


@bot.command()
async def ping(ctx):
    await ctx.send("Мяу! 🐾")
    
@bot.command()
async def help(ctx):
    text = (
        "🐾 **Мяу! Я умею вот что:**\n\n"
        "🎵 **Проигрывать музыку из папки `music`:**\n"
        "`!play` — начну проигрывать плейлист\n"
        "`!next` — пропущу текущий трек\n"
        "`!stop` — остановлю музыку и выйду из голосового канала\n\n"
        "🔁 **Режимы воспроизведения:**\n"
        "`!loop` — зациклить плейлист\n"
        "`!shuffle` — играть треки вразброс\n\n"
        "🐱 **Прочее:**\n"
        "`!ping` — проверь, тут ли я\n\n"
        "Просто напиши команду в чат — я всё сделаю 😺"
    )

    await ctx.send(text)


@bot.command()
async def play(ctx):
    global playlist, current_index

    if not ctx.author.voice:
        await ctx.send("Зайди в голосовой канал")
        return

    voice = ctx.voice_client or await ctx.author.voice.channel.connect()

    playlist = load_playlist()
    current_index = 0

    if not playlist:
        await ctx.send("В папке music нет аудиофайлов 😿")
        return

    await ctx.send(f"🎶 Найдено треков: {len(playlist)}")
    await play_playlist(ctx, voice)


@bot.command()
async def loop(ctx):
    global loop_mode
    loop_mode = not loop_mode
    await ctx.send(f"🔁 Цикл {'включён' if loop_mode else 'выключен'}")


@bot.command()
async def shuffle(ctx):
    global shuffle_mode
    shuffle_mode = not shuffle_mode
    await ctx.send(f"🔀 Shuffle {'включён' if shuffle_mode else 'выключен'}")


@bot.command()
async def next(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        await ctx.send("⏭ Трек пропущен")


@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Отключился от голосового канала 😿")
        


bot.run(DISCORD_TOKEN)

