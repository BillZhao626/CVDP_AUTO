# CVDP 评估脚本

NVIDIA CVDP论文复现 - 一体化评估脚本

## 快速开始

```bash
# 1. 确保工具已安装
iverilog -v  # 检查Icarus Verilog
vivado -version  # 检查Vivado

# 2. 运行评估（10题迷你批量）
python cvdp_eval.py
```

## 功能

- ✅ 题目输入 → 代码生成 → Icarus仿真 → Vivado综合 → CSV记录
- ✅ 支持Non-Agentic 617题评估
- ✅ 自动提取LUT/FF/Fmax/Power指标
- ✅ 结果追加到CSV，支持断点续跑

## 配置

编辑脚本顶部配置区域：
- `IVERILOG_PATH`: Icarus Verilog路径
- `VIVADO_PATH`: Vivado路径（Windows）
- `WORK_DIR`: 工作目录
- `RESULTS_CSV`: 结果CSV文件

## 使用流程

1. **准备题目**：根据论文附录A.1，在脚本中添加题目
2. **运行脚本**：`python cvdp_eval.py`
3. **代码生成**：脚本会提示在Cursor中生成代码
4. **自动评估**：仿真+综合+记录结果

## 输出

- `cvdp_results.csv`: 评估结果CSV
- `cvdp_workspace/`: 每个题目的工作目录（代码、报告等）

## 注意事项

- Vivado综合需要Xilinx器件（默认xc7k70tfbv676-1）
- 测试平台需要根据题目定制
- 首次运行建议先用1-2题测试

