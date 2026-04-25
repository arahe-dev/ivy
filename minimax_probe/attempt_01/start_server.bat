@echo off
set SERVER=C:\Users\arahe\dev\llama.cpp\build\bin\Release\llama-server.exe
set MODEL=C:\minimax_2_7\MiniMax-M2.7-UD-IQ2_XXS-00001-of-00003.gguf
set PORT=8090
set ERRLOG=C:\ivy\minimax_probe\attempt_01\server_stderr.txt
set OUTLOG=C:\ivy\minimax_probe\attempt_01\server_stdout.txt

start /b cmd /c "%SERVER% -m %MODEL% -c 2048 --cpu-moe -ngl 0 --port %PORT% 2>%ERRLOG% >%OUTLOG%"
timeout /t 60 /nobreak >nul