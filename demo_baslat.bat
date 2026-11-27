@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=src"

set "PY_BIN=C:\Users\bugra\AppData\Local\Python\bin\python.exe"
if not exist "%PY_BIN%" set "PY_BIN=python"

echo === Kohort ve Funnel Analizi Demosu Baslatiliyor ===
"%PY_BIN%" -m cohort_funnel.cli demo
if errorlevel 1 (
    echo.
    echo [HATA] Demo calistirilirken bir sorun olustu.
    pause
    exit /b 1
)

echo.
echo Grafikler varsayilan goruntuleyicide aciliyor...
start "" "%~dp0output\funnel_chart.svg"
start "" "%~dp0output\cohort_heatmap.svg"

echo.
echo Tamamlandi! Raporlar output\ klasorune kaydedildi.
pause
