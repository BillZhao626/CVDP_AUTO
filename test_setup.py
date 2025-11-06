#!/usr/bin/env python3
"""
CVDP 环境检查脚本
检查工具是否已正确安装和配置
"""

import subprocess
import sys
from pathlib import Path

def check_command(cmd, name, is_vivado=False):
    """检查命令是否可用"""
    try:
        # 检查文件是否存在
        if Path(cmd).exists():
            print(f"[OK] {name}: 路径存在")
            # 尝试运行
            if is_vivado:
                result = subprocess.run(
                    [cmd, "-version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            else:
                result = subprocess.run(
                    [cmd, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
            if result.returncode == 0:
                print(f"[OK] {name}: 可以运行")
                if result.stdout:
                    version_line = result.stdout.split('\n')[0]
                    print(f"   版本信息: {version_line[:80]}")
                return True
            else:
                print(f"[WARN] {name}: 文件存在但运行失败")
                return False
        else:
            print(f"[FAIL] {name}: 路径不存在 - {cmd}")
            return False
    except Exception as e:
        print(f"[WARN] {name}: 检查出错 - {e}")
        return False

def main():
    print("="*60)
    print("CVDP 环境检查")
    print("="*60)
    print()
    
    # 检查Python版本
    print(f"Python版本: {sys.version}")
    print()
    
    # 从cvdp_eval.py读取配置的路径
    try:
        with open("cvdp_eval.py", "r", encoding="utf-8") as f:
            content = f.read()
            import re
            iverilog_match = re.search(r'IVERILOG_PATH\s*=\s*r?"([^"]+)"', content)
            vvp_match = re.search(r'VVP_PATH\s*=\s*r?"([^"]+)"', content)
            vivado_match = re.search(r'VIVADO_PATH\s*=\s*r?"([^"]+)"', content)
            
            iverilog_path = iverilog_match.group(1) if iverilog_match else "iverilog"
            vvp_path = vvp_match.group(1) if vvp_match else "vvp"
            vivado_path = vivado_match.group(1) if vivado_match else "vivado"
    except Exception as e:
        print(f"[WARN] 无法读取cvdp_eval.py配置: {e}")
        iverilog_path = "iverilog"
        vvp_path = "vvp"
        vivado_path = "vivado"
    
    # 检查工具
    tools = [
        (iverilog_path, "Icarus Verilog"),
        (vvp_path, "Icarus Verilog Simulator"),
        (vivado_path, "Vivado", True),
    ]
    
    results = {}
    for tool_info in tools:
        if len(tool_info) == 3:
            cmd, name, is_vivado = tool_info
            results[name] = check_command(cmd, name, is_vivado)
        else:
            cmd, name = tool_info
            results[name] = check_command(cmd, name)
    
    # 显示配置的路径
    print("\n配置的工具路径:")
    print(f"  Icarus Verilog: {iverilog_path}")
    print(f"  VVP Simulator: {vvp_path}")
    print(f"  Vivado: {vivado_path}")
    
    # 检查工作目录
    print("\n检查目录:")
    work_dir = Path("cvdp_workspace")
    if work_dir.exists():
        print(f"[OK] 工作目录存在: {work_dir.absolute()}")
    else:
        print(f"[INFO] 工作目录将自动创建: {work_dir.absolute()}")
    
    # 总结
    print("\n" + "="*60)
    all_ok = all(results.values())
    if all_ok:
        print("[OK] 环境检查通过！可以运行 cvdp_eval.py")
    else:
        print("[WARN] 部分工具未找到，请检查配置")
        print("   编辑 cvdp_eval.py 修改工具路径")
    print("="*60)

if __name__ == "__main__":
    main()

