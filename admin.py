import discord

from cloud_manager import delete_from_cloud, list_folder_contents
from config import ADMIN_IDS
from user_folders import (
    admin_set_folder_name,
    get_all_folders,
    get_folder_name,
    remove_folder_binding,
)


def is_admin(ctx):
    """Проверяет, является ли пользователь админом (по ID)"""

    return ctx.author.id in ADMIN_IDS


def setup_admin_commands(bot, player):
    """Подключает к боту все команды администратора."""

    @bot.command(name="админ_имя")
    async def admin_set_folder(ctx, member: discord.Member, *, name):
        """[АДМИН] Меняет привязку имени папки."""

        if not is_admin(ctx):
            return await ctx.send("❌ У тебя нет прав на эту команду.")
        success, message = admin_set_folder_name(member.id, name)
        prefix = "✅" if success else "❌"
        await ctx.send(
            f"{prefix} {message} (пользователь: {member.display_name})"
        )

    @bot.command(name="админ_снести")
    async def admin_delete_folder(
        ctx,
        member: discord.Member,
        confirm=None
    ):
        """[АДМИН] Удаляет папку пользователя вместе со всеми треками."""

        if not is_admin(ctx):
            return await ctx.send("❌ У тебя нет прав на эту команду.")
        folder_name = get_folder_name(member.id)
        if folder_name is None:
            return await ctx.send(
                "❌ У этого пользователя нет привязанной папки."
            )
        if confirm != "confirm":
            return await ctx.send(
                f"⚠️ Это удалит папку `{folder_name}` "
                f"СО ВСЕМИ ТРЕКАМИ безвозвратно.\n"
                f"Чтобы подтвердить, напиши:\n"
                f"`!админ_снести {member.mention} confirm`"
            )
        folder_path = f"disk:/music/{folder_name}"
        success, message = await delete_from_cloud(
            folder_path,
            permanently=True
        )
        if success:
            remove_folder_binding(member.id)
            await player.load_playlist()
            await ctx.send(
                f"✅ Папка `{folder_name}` удалена с Диска, привязка снята."
            )
        else:
            await ctx.send(f"❌ Ошибка удаления папки: {message}")

    @bot.command(name="админ_треки")
    async def admin_delete_track(
        ctx,
        member: discord.Member,
        *,
        filename=None
    ):
        """[АДМИН] Показывает/удаляет треки пользователя."""

        if not is_admin(ctx):
            return await ctx.send("❌ У тебя нет прав на эту команду.")
        folder_name = get_folder_name(member.id)

        if folder_name is None:
            return await ctx.send(
                "❌ У этого пользователя нет привязанной папки."
            )
        folder_path = f"disk:/music/{folder_name}"

        if filename is None:
            success, files = await list_folder_contents(folder_path)
            if not success or not files:
                return await ctx.send(
                    f"В папке `{folder_name}` треков не найдено."
                )
            file_list = "\n".join(f"• {file}" for file in files)
            return await ctx.send(
                f"📁 Треки в папке `{folder_name}`:\n{file_list}\n\n"
                f"Чтобы удалить, укажи точное имя файла:\n"
                f"`!админ_треки {member.mention} имя_файла.mp3`"
            )
        track_path = f"{folder_path}/{filename}"
        success, message = await delete_from_cloud(track_path, permanently=True)
        if success:
            await player.load_playlist()
            await ctx.send(
                f"✅ Трек `{filename}` удалён из папки `{folder_name}`."
            )
        else:
            await ctx.send(f"❌ Ошибка удаления трека: {message}")

    @bot.command(name="админ_список")
    async def admin_list_folders(ctx):
        """
        [АДМИН] Показывает список всех пользователей и их привязанные папки.
        """

        if not is_admin(ctx):
            return await ctx.send("❌ У тебя нет прав на эту команду.")
        folders = get_all_folders()
        if not folders:
            return await ctx.send("Список привязок пуст.")
        lines = []
        for discord_id, folder_name in folders.items():
            member = ctx.guild.get_member(int(discord_id))
            display = member.display_name if member else f"ID:{discord_id}"
            lines.append(f"`{display}` -> `{folder_name}`")
        await ctx.send("📋 Привязки:\n" + "\n".join(lines))
