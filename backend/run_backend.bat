@echo off
echo ==========================================
echo Starting Spring Boot Backend (Port 8080)
echo ==========================================
cd /d "%~dp0"
C:\Users\user\apache-maven-3.9.9\bin\mvn.cmd spring-boot:run
pause

