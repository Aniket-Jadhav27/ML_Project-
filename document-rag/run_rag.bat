@echo off
echo ==========================================
echo Starting Python Document RAG Engine (Port 8000)
echo ==========================================
cd /d "%~dp0"
.venv\Scripts\python.exe rag_server.py
pause

