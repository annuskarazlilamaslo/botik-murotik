import discord

from playback_selection import select_all_folders, select_folders
from user_folders import get_all_folders


class FolderSelect(discord.ui.Select):
    """Выпадающий список для выбора папок пользователей"""

    def __init__(self, options, player):
        super().__init__(
            placeholder="Выбери, чьи папки играть",
            min_values=1,
            max_values=len(options),
            options=options,
        )
        self.player = player

    async def callback(self, interaction: discord.Interaction):
        """Обрабатывает выбор папок пользователем"""

        selected = self.values
        select_folders(selected)
        await self.player.load_playlist()
        await interaction.response.send_message(
            f"🎯 Теперь играют только: {', '.join(selected)}"
        )


class FolderSelectView(discord.ui.View):
    """Вью для выбора папок пользователей"""

    def __init__(self, options, player):
        super().__init__(timeout=60)
        self.add_item(FolderSelect(options, player))


def setup_playback_filter_commands(bot, player):
    """Регистрирует команды выбора папок для проигрывания"""

    @bot.command(name="играть_папки")
    async def cmd_select_folders_from_voice(ctx):
        """
        Выбрать, чьи папки играть, из тех,
        кто сейчас в голосовом канале с ботом
        """

        voice_client = ctx.guild.voice_client
        if voice_client is None or voice_client.channel is None:
            return await ctx.send("❌ Я сейчас не в голосовом канале.")

        voice_members = [m for m in voice_client.channel.members if not m.bot]
        if not voice_members:
            return await ctx.send(
                "❌ В голосовом канале со мной сейчас никого нет.")

        folders = get_all_folders()
        options = []
        for member in voice_members:
            folder_name = folders.get(str(member.id))
            if folder_name:
                options.append(
                    discord.SelectOption(label=folder_name, value=folder_name)
                )

        if not options:
            return await ctx.send(
                "❌ Ни у кого из присутствующих"
                " в канале нет привязанной папки."
            )

        view = FolderSelectView(options, player)
        await ctx.send("Кого включить в проигрывание?", view=view)

    @bot.command(name="играть_все")
    async def cmd_select_all_folders(ctx):
        """Вернуть проигрывание всех папок"""

        select_all_folders()
        await player.load_playlist()
        await ctx.send("🎵 Теперь играют все папки")
