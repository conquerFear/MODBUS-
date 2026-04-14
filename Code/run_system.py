#!/usr/bin/env python3
"""
启动整个MODBUS系统
支持单独启动从站1、从站2或主站
"""

import subprocess
import time
import sys
import os
import argparse


def run_slave(slave_id, name, port):
    """启动从站 - 使用pythonw以避免弹出控制台窗口"""
    print(f"启动{name} (ID: {slave_id}, 端口: {port})...")
    cmd = [sys.executable, "slave_server.py", "--id", str(slave_id), "--name", name, "--port", str(port)]

    # 在Windows上，使用CREATE_NO_WINDOW标志避免弹出控制台窗口
    if sys.platform == 'win32':
        # 使用subprocess.DETACHED_PROCESS和CREATE_NO_WINDOW来避免弹出控制台
        return subprocess.Popen(cmd,
                                creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
    else:
        # 在Linux/macOS上，使用nohup或直接运行
        return subprocess.Popen(cmd,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                                start_new_session=True)


def run_master():
    """启动主站"""
    print("启动主站控制系统...")
    cmd = [sys.executable, "master_client.py"]
    return subprocess.Popen(cmd)


def check_slave_running(port):
    """检查从站是否已经在运行"""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='启动MODBUS系统')
    parser.add_argument('--slave1', action='store_true', help='只启动从站1')
    parser.add_argument('--slave2', action='store_true', help='只启动从站2')
    parser.add_argument('--master', action='store_true', help='只启动主站')
    parser.add_argument('--all', action='store_true', help='启动所有组件（默认）')

    args = parser.parse_args()

    # 如果没有指定任何参数，默认启动所有
    if not (args.slave1 or args.slave2 or args.master):
        args.all = True

    print("=" * 60)
    print("MODBUS系统启动器")
    print("=" * 60)

    processes = []

    try:
        # 启动从站1
        if args.slave1 or args.all:
            if check_slave_running(5021):
                print("从站1已经在运行，跳过启动...")
            else:
                p1 = run_slave(1, "从站1", 5021)
                processes.append(p1)
                time.sleep(2)  # 等待从站启动

        # 启动从站2
        if args.slave2 or args.all:
            if check_slave_running(5022):
                print("从站2已经在运行，跳过启动...")
            else:
                p2 = run_slave(2, "从站2", 5022)
                processes.append(p2)
                time.sleep(2)  # 等待从站启动

        # 启动主站
        if args.master or args.all:
            p3 = run_master()
            processes.append(p3)

        print("\n" + "=" * 60)
        print("启动完成!")
        print("使用方法:")
        print("1. 在主站窗口中点击'连接所有从站'")
        print("2. 使用'启动'/'停止'按钮控制从站指示灯")
        print("3. 观察从站窗口中的指示灯状态和启动次数")
        print("=" * 60)

        if args.master or args.all:
            print("注意: 主站窗口已打开，请操作主站界面")
        else:
            print("从站已启动，请手动启动主站:")
            print("  python master_client.py")

        print("=" * 60)

        # 如果启动了主站，等待主站进程结束
        # 否则，等待用户按Enter键
        if args.master or args.all:
            # 等待主站进程
            for p in processes:
                if p == p3:  # 主站进程
                    p.wait()
        else:
            input("\n按Enter键停止所有从站...")

    except KeyboardInterrupt:
        print("\n正在停止所有进程...")
    except Exception as e:
        print(f"启动错误: {e}")
    finally:
        # 停止所有进程（除了主站，因为它可能已经退出）
        for p in processes:
            try:
                if p.poll() is None:  # 进程还在运行
                    p.terminate()
            except:
                pass

        print("所有进程已停止")


if __name__ == "__main__":
    main()