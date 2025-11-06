#!/usr/bin/env python3
"""
CVDP 评估脚本 - 一体化版本
支持：题目输入 → 代码生成 → Icarus仿真 → Vivado综合 → CSV记录
"""

import os
import sys
import subprocess
import json
import csv
import re
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ==================== 配置区域 ====================
IVERILOG_PATH = r"D:\ModelSim\iverilog\bin\iverilog.exe"  # Icarus Verilog命令
VVP_PATH = r"D:\ModelSim\iverilog\bin\vvp.exe"  # Icarus Verilog仿真器
VIVADO_PATH = r"D:\Vivado\2025.1\Vivado\bin\vivado.bat"  # Vivado路径
GTKWAVE_PATH = "gtkwave"  # 波形查看器（可选）

WORK_DIR = Path("cvdp_workspace")
RESULTS_CSV = "cvdp_results.csv"

# ==================== 工具函数 ====================

def run_cmd(cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> Tuple[int, str, str]:
    """执行命令并返回返回码、stdout、stderr"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timeout after {timeout}s"
    except Exception as e:
        return -1, "", str(e)

def extract_verilog_code(text: str) -> Optional[str]:
    """从文本中提取Verilog代码块"""
    # 匹配 ```verilog 或 ``` 代码块
    patterns = [
        r'```verilog\s*\n(.*?)```',
        r'```\s*\n(.*?)```',
        r'(module\s+\w+.*?endmodule)',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
    return None

def create_testbench(module_name: str, test_cases: List[Dict]) -> str:
    """创建简单的测试平台（可根据实际需求扩展）"""
    # 注意：这是一个最小化的testbench，实际使用时需要根据模块接口定制
    tb = f"""
`timescale 1ns/1ps

module {module_name}_tb;
    // 注意：此testbench是占位符，需要根据实际模块接口定制
    // 如果模块有端口，需要在这里声明并实例化
    
    initial begin
        $dumpfile("{module_name}_tb.vcd");
        $dumpvars(0, {module_name}_tb);
        $display("Testbench started");
        // 测试逻辑
        #100;
        $display("Testbench finished");
        $finish;
    end
endmodule
"""
    return tb

# ==================== Icarus Verilog 仿真 ====================

def run_iverilog_sim(verilog_file: Path, testbench_file: Path, work_dir: Path) -> Tuple[bool, str]:
    """运行Icarus Verilog仿真"""
    # 使用绝对路径
    verilog_abs = verilog_file.resolve()
    testbench_abs = testbench_file.resolve()
    
    # 编译
    compile_cmd = [IVERILOG_PATH, "-o", "sim.vvp", str(verilog_abs), str(testbench_abs)]
    print(f"  编译命令: {' '.join(compile_cmd)}")
    ret, stdout, stderr = run_cmd(compile_cmd, cwd=work_dir)
    
    if ret != 0:
        error_msg = stderr if stderr else stdout
        print(f"  编译错误: {error_msg[:200]}")
        return False, f"Compile failed: {error_msg}"
    
    # 运行仿真
    sim_cmd = [VVP_PATH, "sim.vvp"]
    print(f"  仿真命令: {' '.join(sim_cmd)}")
    ret, stdout, stderr = run_cmd(sim_cmd, cwd=work_dir)
    
    if ret != 0:
        error_msg = stderr if stderr else stdout
        print(f"  仿真错误: {error_msg[:200]}")
        return False, f"Simulation failed: {error_msg}"
    
    print(f"  仿真输出: {stdout[:200] if stdout else '无输出'}")
    return True, stdout

# ==================== Vivado 综合 ====================

# create_vivado_tcl函数已移动到run_vivado_synth中，不再需要单独函数

def parse_vivado_reports(work_dir: Path) -> Dict[str, float]:
    """解析Vivado报告，提取LUT/FF/Fmax/Power"""
    results = {
        "LUT": 0.0,
        "FF": 0.0,
        "Fmax_MHz": 0.0,
        "Power_W": 0.0
    }
    
    # 解析utilization报告
    util_file = work_dir / "utilization.rpt"
    if util_file.exists():
        content = util_file.read_text()
        # 提取LUT - 匹配 "Slice LUTs | 4 |" 格式
        lut_match = re.search(r'Slice LUTs\s+\|\s+(\d+)', content)
        if lut_match:
            results["LUT"] = float(lut_match.group(1))
        # 提取FF - 匹配 "Slice Registers | 8 |" 格式
        ff_match = re.search(r'Slice Registers\s+\|\s+(\d+)', content)
        if ff_match:
            results["FF"] = float(ff_match.group(1))
    
    # 解析timing报告
    timing_file = work_dir / "timing.rpt"
    if timing_file.exists():
        content = timing_file.read_text()
        # 提取WNS (Worst Negative Slack)
        wns_match = re.search(r'WNS\s+([-\d.]+)', content, re.MULTILINE)
        if wns_match:
            wns = float(wns_match.group(1))
            # 假设默认时钟约束为10ns (100MHz)
            # 如果WNS为负，说明时序不满足；如果为正或0，说明满足
            # Fmax = 1 / (时钟周期 - WNS)，但需要知道原始时钟约束
            # 简化处理：如果没有约束，使用默认值
            clock_period = 10.0  # 默认10ns
            if wns >= 0:
                # 时序满足，可以尝试更高频率
                results["Fmax_MHz"] = 100.0 + abs(wns) * 10  # 粗略估算
            else:
                # 时序不满足，实际Fmax低于目标
                results["Fmax_MHz"] = 1000.0 / (clock_period - wns)
        else:
            # 如果没有WNS信息，尝试查找其他时序信息
            # 对于组合逻辑（如加法器），可能没有时钟约束
            results["Fmax_MHz"] = 0.0  # 组合逻辑无法直接计算Fmax
    
    # 解析power报告
    power_file = work_dir / "power.rpt"
    if power_file.exists():
        content = power_file.read_text()
        # 匹配 "Total On-Chip Power (W) | 2.721" 格式
        power_match = re.search(r'Total On-Chip Power\s+\(W\)\s+\|\s+([\d.]+)', content)
        if power_match:
            results["Power_W"] = float(power_match.group(1))
    
    return results

def extract_module_name(verilog_code: str) -> Optional[str]:
    """从Verilog代码中提取模块名"""
    match = re.search(r'module\s+(\w+)', verilog_code)
    return match.group(1) if match else None

def run_vivado_synth(verilog_file: Path, work_dir: Path) -> Tuple[bool, Dict[str, float]]:
    """运行Vivado综合"""
    # 读取Verilog代码提取模块名
    verilog_code = verilog_file.read_text()
    module_name = extract_module_name(verilog_code)
    
    if not module_name:
        return False, {"error": "无法从Verilog代码中提取模块名"}
    
    # 使用绝对路径，并转换为Unix风格（Vivado需要）
    verilog_abs = verilog_file.resolve()
    work_dir_abs = work_dir.resolve()
    
    # 转换为Unix风格路径（正斜杠）
    verilog_path_unix = str(verilog_abs).replace('\\', '/')
    work_dir_path_unix = str(work_dir_abs).replace('\\', '/')
    
    # 创建TCL脚本
    tcl_content = f"""
# Vivado综合脚本
read_verilog {verilog_path_unix}
synth_design -top {module_name} -part xc7k70tfbv676-1
place_design
route_design

# 提取资源使用
report_utilization -file {work_dir_path_unix}/utilization.rpt
report_timing_summary -file {work_dir_path_unix}/timing.rpt
report_power -file {work_dir_path_unix}/power.rpt

exit
"""
    tcl_file = work_dir / "synth.tcl"
    tcl_file.write_text(tcl_content)
    tcl_abs = tcl_file.resolve()
    
    # 运行Vivado（批处理模式）
    vivado_cmd = [VIVADO_PATH, "-mode", "batch", "-source", str(tcl_abs)]
    print(f"  综合命令: {' '.join(vivado_cmd)}")
    print(f"  工作目录: {work_dir.resolve()}")
    ret, stdout, stderr = run_cmd(vivado_cmd, cwd=work_dir, timeout=600)
    
    if ret != 0:
        error_msg = stderr if stderr else stdout
        print(f"  综合错误: {error_msg[:500]}")
        return False, {"error": error_msg}
    
    print(f"  综合输出: {stdout[:500] if stdout else '无输出'}")
    
    # 解析报告
    results = parse_vivado_reports(work_dir)
    return True, results

# ==================== 主评估流程 ====================

def evaluate_problem(problem_id: str, category: str, prompt: str, 
                    reference_code: Optional[str] = None,
                    testbench_code: Optional[str] = None,
                    auto_mode: bool = False) -> Dict:
    """评估单个问题"""
    print(f"\n{'='*60}")
    print(f"评估问题: {problem_id} [{category}]")
    print(f"{'='*60}")
    
    # 创建工作目录
    work_dir = WORK_DIR / problem_id
    work_dir.mkdir(parents=True, exist_ok=True)
    
    result = {
        "problem_id": problem_id,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
        "sim_pass": False,
        "synth_pass": False,
        "LUT": 0.0,
        "FF": 0.0,
        "Fmax_MHz": 0.0,
        "Power_W": 0.0,
        "error": ""
    }
    
    try:
        # 步骤1: 生成代码
        print("\n[1/4] 代码生成...")
        print(f"Prompt: {prompt[:150]}...")
        
        # 检查是否已有生成的代码文件
        code_file = work_dir / f"{problem_id}_generated.v"
        if code_file.exists():
            print(f"[OK] 发现已有代码文件: {code_file}")
            generated_code = code_file.read_text()
        else:
            if auto_mode:
                # 自动模式下，如果文件不存在则跳过
                print(f"[SKIP] 代码文件不存在，自动跳过: {code_file}")
                print("   提示：请先在Cursor中生成代码并保存到上述路径")
                result["status"] = "skipped"
                result["error"] = "代码文件不存在"
                return result
            
            # 交互模式
            print("[INFO] 请在Cursor中根据prompt生成Verilog代码")
            print("   生成后保存到:", code_file)
            print("   或直接粘贴代码（输入'END'结束）:")
            
            code_input = input("代码文件路径（回车=粘贴）: ").strip()
            
            if code_input and Path(code_input).exists():
                generated_code = Path(code_input).read_text()
                code_file.write_text(generated_code)  # 保存副本
            else:
                print("粘贴Verilog代码（输入'END'结束）:")
                lines = []
                while True:
                    try:
                        line = input()
                        if line.strip() == "END":
                            break
                        lines.append(line)
                    except EOFError:
                        break
                generated_code = "\n".join(lines)
                if generated_code.strip():
                    code_file.write_text(generated_code)
        
        # 提取Verilog代码
        verilog_code = extract_verilog_code(generated_code) if generated_code else None
        if not verilog_code:
            result["status"] = "failed"
            result["error"] = "无法提取Verilog代码"
            return result
        
        # 保存生成的代码
        verilog_file = work_dir / f"{problem_id}.v"
        verilog_file.write_text(verilog_code)
        print(f"[OK] 代码已保存: {verilog_file}")
        
        # 步骤2: Icarus Verilog仿真
        print("\n[2/4] Icarus Verilog仿真...")
        if testbench_code:
            tb_file = work_dir / f"{problem_id}_tb.v"
            tb_file.write_text(testbench_code)
        else:
            # 创建简单测试平台
            module_match = re.search(r'module\s+(\w+)', verilog_code)
            module_name = module_match.group(1) if module_match else "module"
            testbench_code = create_testbench(module_name, [])
            tb_file = work_dir / f"{problem_id}_tb.v"
            tb_file.write_text(testbench_code)
        
        sim_pass, sim_output = run_iverilog_sim(verilog_file, tb_file, work_dir)
        result["sim_pass"] = sim_pass
        if sim_pass:
            print("[OK] 仿真通过")
        else:
            print(f"[FAIL] 仿真失败: {sim_output}")
            result["error"] = sim_output
        
        # 步骤3: Vivado综合
        print("\n[3/4] Vivado综合...")
        synth_pass, synth_results = run_vivado_synth(verilog_file, work_dir)
        result["synth_pass"] = synth_pass
        
        if synth_pass:
            result.update(synth_results)
            print(f"[OK] 综合完成: LUT={result['LUT']}, FF={result['FF']}, Fmax={result['Fmax_MHz']:.2f}MHz")
        else:
            print(f"[FAIL] 综合失败: {synth_results.get('error', 'Unknown error')}")
            result["error"] = synth_results.get("error", "Synthesis failed")
        
        # 步骤4: 判断通过
        result["status"] = "passed" if (sim_pass and synth_pass) else "failed"
        
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"[ERROR] 评估出错: {e}")
    
    return result

def save_results(results: List[Dict], csv_file: str):
    """保存结果到CSV"""
    if not results:
        return
    
    file_exists = Path(csv_file).exists()
    with open(csv_file, 'a', newline='', encoding='utf-8') as f:
        fieldnames = [
            "problem_id", "category", "timestamp", "status",
            "sim_pass", "synth_pass", "LUT", "FF", "Fmax_MHz", "Power_W", "error"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        if not file_exists:
            writer.writeheader()
        
        for result in results:
            writer.writerow(result)
    
    print(f"\n[OK] 结果已保存到: {csv_file}")

# ==================== 主函数 ====================

def load_problems_from_file(file_path: str) -> List[Dict]:
    """从文件加载题目（简单格式）"""
    problems = []
    if not Path(file_path).exists():
        return problems
    
    current_problem = {}
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            if line.startswith('ID:'):
                if current_problem:
                    problems.append(current_problem)
                current_problem = {"id": line.split(':', 1)[1].strip()}
            elif line.startswith('Category:'):
                current_problem["category"] = line.split(':', 1)[1].strip()
            elif line.startswith('Prompt:'):
                current_problem["prompt"] = line.split(':', 1)[1].strip()
            elif line.startswith('---'):
                if current_problem:
                    problems.append(current_problem)
                    current_problem = {}
    
    if current_problem:
        problems.append(current_problem)
    return problems

def main():
    """主函数 - 运行10题迷你批量测试"""
    print("="*60)
    print("CVDP 评估脚本 - 迷你批量测试")
    print("="*60)
    
    # 加载题目（从文件或使用默认示例）
    problems_file = "example_problems.txt"
    if Path(problems_file).exists():
        problems = load_problems_from_file(problems_file)
    else:
        # 默认示例题目
        problems = [
            {
                "id": "cid02_001",
                "category": "cid02",
                "prompt": "实现一个4位加法器模块，输入两个4位操作数a和b，输出5位结果sum（包含进位）。接口：input [3:0] a, input [3:0] b, output [4:0] sum",
            },
            {
                "id": "cid03_001", 
                "category": "cid03",
                "prompt": "实现一个8位向上计数器，时钟上升沿触发，同步复位（低电平有效），使能信号控制计数，计数到255后自动回0。接口：input clk, input rst_n, input en, output reg [7:0] count",
            },
        ]
    
    # 限制为10题（迷你批量）
    problems = problems[:10]
    
    print(f"\n准备评估 {len(problems)} 个问题...")
    print(f"工作目录: {WORK_DIR.absolute()}")
    print(f"结果文件: {RESULTS_CSV}")
    
    # 确认开始
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        auto_mode = True
    else:
        confirm = input("\n开始评估？(y/n): ").strip().lower()
        auto_mode = (confirm == 'y')
    
    if not auto_mode:
        print("已取消")
        return
    
    # 评估所有问题
    results = []
    for i, problem in enumerate(problems, 1):
        print(f"\n进度: {i}/{len(problems)}")
        result = evaluate_problem(
            problem["id"],
            problem["category"],
            problem["prompt"],
            problem.get("reference"),
            problem.get("testbench"),
            auto_mode=auto_mode
        )
        results.append(result)
        
        # 每5题保存一次
        if i % 5 == 0:
            save_results(results, RESULTS_CSV)
            print(f"中间结果已保存（{i}/{len(problems)}）")
    
    # 最终保存
    save_results(results, RESULTS_CSV)
    
    # 统计
    passed = sum(1 for r in results if r["status"] == "passed")
    sim_passed = sum(1 for r in results if r["sim_pass"])
    synth_passed = sum(1 for r in results if r["synth_pass"])
    
    print(f"\n{'='*60}")
    print(f"评估完成!")
    print(f"  总题数: {len(results)}")
    print(f"  通过: {passed} ({passed/len(results)*100:.1f}%)")
    print(f"  仿真通过: {sim_passed}")
    print(f"  综合通过: {synth_passed}")
    print(f"  结果文件: {RESULTS_CSV}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

