@echo off
title Backup Agil - Instalador

echo.
echo ================================================
echo   Backup Agil - Verificando Python...
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado!
    echo.
    echo Baixe em: https://www.python.org/downloads/
    echo IMPORTANTE: Marque "Add Python to PATH" na instalacao.
    echo.
    pause
    exit /b 1
)

echo [OK] Python encontrado.
echo Instalando dependencias...

pip install schedule --quiet

echo [OK] Dependencias instaladas.
echo.
echo Iniciando Backup Agil...
echo.

python "%~dp0backup_agil.py"

if errorlevel 1 (
    echo.
    echo [ERRO] Falha ao iniciar.
    echo Verifique se backup_agil.py esta na mesma pasta que este .bat
    pause
)
