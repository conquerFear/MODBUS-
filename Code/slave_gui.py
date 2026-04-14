#!/usr/bin/env python3
"""
从站GUI界面 - 显示从站自身状态
这个GUI连接本地的从站服务器，显示从站的状态
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
import socket
import argparse


class SlaveGUI:
    """从站GUI界面"""

    def __init__(self, slave_id, name, port, host='127.0.0.1'):
        self.slave_id = slave_id
        self.name = name
        self.host = host
        self.port = port

        # 状态变量
        self.run_light = False
        self.start_count = 0
        self.connected_clients = 0
        self.server_running = False
        self.last_operation = ""

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title(f"{self.name} - MODBUS从站")
        self.root.geometry("500x400")

        self.setup_ui()
        self.start_status_update()

    def setup_ui(self):
        """设置UI界面"""
        # 标题栏
        title_frame = tk.Frame(self.root, bg="#3498db")
        title_frame.pack(fill="x")

        title_label = tk.Label(
            title_frame,
            text=f"{self.name} (ID: {self.slave_id})",
            font=("Arial", 16, "bold"),
            fg="white",
            bg="#3498db",
            pady=10
        )
        title_label.pack()

        # 基本信息面板
        info_frame = ttk.LabelFrame(self.root, text="从站信息", padding=10)
        info_frame.pack(fill="x", padx=15, pady=10)

        tk.Label(info_frame, text=f"设备ID: {self.slave_id}", font=("Arial", 10)).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"服务端口: {self.port}", font=("Arial", 10)).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"运行指示灯地址: 0", font=("Arial", 10)).pack(anchor="w", pady=2)
        tk.Label(info_frame, text=f"启动次数地址: 0", font=("Arial", 10)).pack(anchor="w", pady=2)

        # 状态显示面板
        status_frame = ttk.LabelFrame(self.root, text="当前状态", padding=15)
        status_frame.pack(fill="x", padx=15, pady=10)

        # 服务器运行状态
        server_frame = tk.Frame(status_frame)
        server_frame.pack(fill="x", pady=5)

        tk.Label(server_frame, text="服务器状态:", font=("Arial", 10)).pack(side="left")
        self.server_status_label = tk.Label(
            server_frame,
            text="运行中",
            font=("Arial", 10, "bold"),
            fg="green"
        )
        self.server_status_label.pack(side="left", padx=10)

        # 运行指示灯
        light_frame = tk.Frame(status_frame)
        light_frame.pack(fill="x", pady=10)

        tk.Label(light_frame, text="运行指示灯:", font=("Arial", 11)).pack(side="left")

        self.light_canvas = tk.Canvas(light_frame, width=50, height=50, bg="white", highlightthickness=1,
                                      highlightbackground="black")
        self.light_canvas.pack(side="left", padx=15)
        self.light_indicator = self.light_canvas.create_oval(
            10, 10, 40, 40,
            fill="red",
            outline="black",
            width=2
        )

        self.light_label = tk.Label(light_frame, text="OFF", font=("Arial", 12, "bold"), fg="red")
        self.light_label.pack(side="left")

        # 启动次数
        count_frame = tk.Frame(status_frame)
        count_frame.pack(fill="x", pady=10)

        tk.Label(count_frame, text="启动次数:", font=("Arial", 11)).pack(side="left")
        self.count_label = tk.Label(
            count_frame,
            text="0",
            font=("Arial", 16, "bold"),
            fg="blue"
        )
        self.count_label.pack(side="left", padx=15)

        # 客户端连接数
        client_frame = tk.Frame(status_frame)
        client_frame.pack(fill="x", pady=5)

        tk.Label(client_frame, text="客户端连接:", font=("Arial", 10)).pack(side="left")
        self.client_label = tk.Label(
            client_frame,
            text="0",
            font=("Arial", 10, "bold")
        )
        self.client_label.pack(side="left", padx=10)

        # 操作记录面板
        log_frame = ttk.LabelFrame(self.root, text="最近操作", padding=10)
        log_frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_text = tk.Text(log_frame, height=6, width=50, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 初始信息
        self.log_text.insert(tk.END, f"{self.name} GUI已启动\n")
        self.log_text.insert(tk.END, f"等待连接到服务器 {self.host}:{self.port}\n")

    def update_log(self, message):
        """更新日志"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

    def check_server_connection(self):
        """检查服务器连接状态"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, self.port))
            sock.close()
            return result == 0
        except:
            return False

    def update_status_from_server(self):
        """模拟从服务器获取状态更新"""
        # 在实际实现中，这里应该通过TCP连接或共享内存从服务器获取状态
        # 这里我们模拟状态变化

        # 检查服务器是否运行
        server_online = self.check_server_connection()

        if server_online != self.server_running:
            self.server_running = server_online
            if server_online:
                self.server_status_label.config(text="运行中", fg="green")
                self.update_log("服务器连接成功")
            else:
                self.server_status_label.config(text="未连接", fg="red")
                self.update_log("服务器连接失败")

        # 模拟一些状态变化（在实际中应该从服务器获取真实数据）
        if server_online:
            # 在实际实现中，这里应该通过TCP连接从服务器获取真实状态
            # 这里我们只是模拟一些随机变化以演示效果
            import random

            # 随机变化指示灯状态（低概率）
            if random.random() < 0.1:
                self.run_light = not self.run_light

            # 随机增加启动次数（更低概率）
            if random.random() < 0.05 and self.run_light:
                self.start_count += 1

            # 随机变化客户端连接数
            if random.random() < 0.2:
                change = random.choice([-1, 0, 1])
                self.connected_clients = max(0, self.connected_clients + change)

    def update_gui(self):
        """更新GUI显示"""
        # 更新运行指示灯
        light_color = "green" if self.run_light else "red"
        light_text = "ON" if self.run_light else "OFF"
        light_fg = "green" if self.run_light else "red"

        self.light_canvas.itemconfig(self.light_indicator, fill=light_color)
        self.light_label.config(text=light_text, fg=light_fg)

        # 更新启动次数
        self.count_label.config(text=str(self.start_count))

        # 更新客户端连接数
        self.client_label.config(text=str(self.connected_clients))

    def start_status_update(self):
        """启动状态更新线程"""

        def update_loop():
            while True:
                self.update_status_from_server()
                self.update_gui()
                time.sleep(1)  # 每秒更新一次

        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()

    def run(self):
        """运行GUI"""
        self.root.mainloop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='MODBUS从站GUI界面')
    parser.add_argument('--id', type=int, default=1, help='从站ID')
    parser.add_argument('--name', type=str, default=None, help='从站名称')
    parser.add_argument('--port', type=int, default=5021, help='从站服务器端口')
    parser.add_argument('--host', type=str, default='127.0.0.1', help='从站服务器主机')

    args = parser.parse_args()

    # 构建配置
    name = args.name or f"从站{args.id}"

    print("=" * 60)
    print(f"启动MODBUS从站GUI - {name}")
    print("=" * 60)
    print(f"从站ID: {args.id}")
    print(f"服务器地址: {args.host}:{args.port}")
    print("=" * 60)
    print("提示: 请确保从站服务器已启动")
    print("      python slave_server.py --id {args.id} --port {args.port}")
    print("=" * 60)

    app = SlaveGUI(
        slave_id=args.id,
        name=name,
        host=args.host,
        port=args.port
    )
    app.run()


if __name__ == "__main__":
    main()