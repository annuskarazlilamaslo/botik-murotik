@echo off
echo Proveryayu obnovleniya...
:: Обновляем библиотеки внутри вашего venv
call venv\Scripts\activate
python -m pip install -U discord.py[voice] yt-dlp
echo Zapuskayu botika...
python music-bot.py
pause