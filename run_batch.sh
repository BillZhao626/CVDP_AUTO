#!/bin/bash
# CVDP批量评估 - Linux/Mac脚本
# 用法: ./run_batch.sh [题目数量]

MAX_PROBLEMS=${1:-10}

echo "========================================"
echo "CVDP 评估 - 批量运行"
echo "========================================"
echo ""

python3 cvdp_eval.py --auto

