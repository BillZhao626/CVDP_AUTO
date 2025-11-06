@echo off
REM CVDP批量评估 - Windows批处理脚本
REM 用法: run_batch.bat [题目数量]

set MAX_PROBLEMS=10
if "%1" neq "" set MAX_PROBLEMS=%1

echo ========================================
echo CVDP 评估 - 批量运行
echo ========================================
echo.

python cvdp_eval.py --auto

pause

