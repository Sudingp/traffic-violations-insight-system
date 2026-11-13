@echo off
REM Runs one incremental ingest. Called by Windows Task Scheduler.
REM Exit code is passed through, so Task Scheduler shows failed runs.
cd /d "%~dp0.."
python -m src.live_ingest %*
exit /b %ERRORLEVEL%
