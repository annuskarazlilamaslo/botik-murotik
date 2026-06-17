from aiohttp import web


async def handle(request):
    """Простой обработчик для проверки работоспособности сервера"""
    return web.Response(text="Бот работает!")


async def start_server():
    """Запуск сервера для поддержания бота активным"""
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    import os
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()