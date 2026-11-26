@echo off
echo =======================================================
echo   Launching Document RAG Full-Stack Application
echo =======================================================
echo.
echo 1. Launching Python RAG Engine (Port 8000)...
start "1. Python RAG Engine" cmd /k "cd /d %~dp0document-rag && .venv\Scripts\python.exe rag_server.py"
timeout /t 3 /nobreak >nul

echo 2. Launching Spring Boot Backend (Port 8080)...
start "2. Spring Boot Backend" cmd /k "cd /d %~dp0backend && C:\Users\user\apache-maven-3.9.9\bin\mvn.cmd spring-boot:run"
timeout /t 6 /nobreak >nul

echo 3. Launching React MUI Frontend (Port 5173)...
start "3. React MUI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo =======================================================
echo   All 3 services are running!
echo   Frontend: http://localhost:5173
echo   Backend:  http://localhost:8080
echo   RAG API:  http://127.0.0.1:8000
echo =======================================================
pause

