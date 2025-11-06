# CVDP 快速开始指南

## 一键运行（10题迷你批量）

### Windows
```bash
python cvdp_eval.py
# 或自动模式
python cvdp_eval.py --auto
```

### Linux/Mac
```bash
python3 cvdp_eval.py
# 或自动模式  
python3 cvdp_eval.py --auto
```

## 使用流程

### 1. 准备题目
编辑 `example_problems.txt`，添加题目：
```
ID: cid02_001
Category: cid02
Prompt: 实现一个4位加法器...
---
```

### 2. 运行评估
```bash
python cvdp_eval.py
```

### 3. 代码生成
脚本会提示：
- 在Cursor中根据prompt生成Verilog代码
- 保存到 `cvdp_workspace/{problem_id}/{problem_id}_generated.v`
- 或直接粘贴代码

### 4. 自动评估
脚本自动执行：
- ✅ Icarus Verilog仿真
- ✅ Vivado综合（提取LUT/FF/Fmax/Power）
- ✅ 结果记录到CSV

### 5. 查看结果
打开 `cvdp_results.csv` 查看评估结果

## 配置修改

编辑 `cvdp_eval.py` 顶部配置：
```python
IVERILOG_PATH = "iverilog"  # 修改为实际路径
VIVADO_PATH = r"C:\Xilinx\Vivado\2025.1\bin\vivado.bat"  # 修改为实际路径
```

## 输出文件

- `cvdp_results.csv`: 评估结果（追加模式，支持断点续跑）
- `cvdp_workspace/`: 每个题目的工作目录
  - `{problem_id}.v`: 生成的Verilog代码
  - `{problem_id}_tb.v`: 测试平台
  - `utilization.rpt`: Vivado资源报告
  - `timing.rpt`: Vivado时序报告
  - `power.rpt`: Vivado功耗报告

## 注意事项

1. **首次运行**：建议先用1-2题测试
2. **Vivado路径**：确保Vivado路径正确
3. **测试平台**：可能需要根据题目定制testbench
4. **断点续跑**：结果追加到CSV，可随时中断继续

## 故障排查

### Icarus Verilog未找到
```bash
# Windows: 添加到PATH或使用完整路径
IVERILOG_PATH = r"C:\iverilog\bin\iverilog.exe"
```

### Vivado未找到
```bash
# 检查Vivado安装路径
# Windows: C:\Xilinx\Vivado\2025.1\bin\vivado.bat
# Linux: /opt/Xilinx/Vivado/2025.1/bin/vivado
```

### 综合失败
- 检查器件型号（默认xc7k70tfbv676-1）
- 检查代码语法
- 查看 `cvdp_workspace/{problem_id}/` 中的错误日志

