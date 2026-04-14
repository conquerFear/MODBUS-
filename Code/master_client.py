"""
MODBUS主站客户端
可以分别控制两个从站的运行指示灯
并显示两个从站的启动次数
"""

import socket
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from modbus_utils import ModbusFrame

class ModbusClient:
    """MODBUS客户端"""

    def __init__(self, slave_id, host, port):
        self.slave_id = slave_id
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False

    def connect(self):
        """连接到从站"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(3)
            self.socket.connect((self.host, self.port))
            self.connected = True
            return True
        except Exception as e:
            print(f"连接从站 {self.slave_id} 失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
        self.connected = False

    def send_request(self, request_frame):
        """发送请求并接收响应"""
        if not self.connected:
            raise Exception("未连接到从站")

        try:
            self.socket.sendall(request_frame)
            response = self.socket.recv(256)
            return response
        except Exception as e:
            self.connected = False
            raise Exception(f"通信错误: {str(e)}")

    def read_coil(self, address):
        """读取线圈"""
        request = ModbusFrame.create_request(self.slave_id, 0x01, address)
        response = self.send_request(request)
        return ModbusFrame.parse_response(response, 0x01)

    def write_coil(self, address, value):
        """写入线圈"""
        request = ModbusFrame.create_request(self.slave_id, 0x05, address, value)
        response = self.send_request(request)
        return ModbusFrame.parse_response(response, 0x05)

    def read_register(self, address):
        """读取寄存器"""
        request = ModbusFrame.create_request(self.slave_id, 0x03, address)
        response = self.send_request(request)
        return ModbusFrame.parse_response(response, 0x03)

class MasterGUI:
    """主站GUI"""

    def __init__(self):
        # 创建两个从站客户端
        self.slave1 = ModbusClient(slave_id=1, host='127.0.0.1', port=5021)
        self.slave2 = ModbusClient(slave_id=2, host='127.0.0.1', port=5022)

        # 状态变量
        self.slave1_status = {
            'connected': False,
            'run_light': False,
            'start_count': 0,
            'error': None
        }

        self.slave2_status = {
            'connected': False,
            'run_light': False,
            'start_count': 0,
            'error': None
        }

        # 运行标志
        self.running = False
        self.polling_thread = None

        # GUI控件存储
        self.slave_widgets = {
            1: {},
            2: {}
        }

        # 创建主窗口
        self.root = tk.Tk()
        self.root.title("MODBUS主站控制系统")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.setup_gui()

        # 启动状态更新
        self.update_status()

    def setup_gui(self):
        """设置主站GUI"""
        # 顶部标题
        title_frame = tk.Frame(self.root, bg="#2c3e50")
        title_frame.pack(fill="x")

        title_label = tk.Label(
            title_frame,
            text="MODBUS主站控制系统",
            font=("Arial", 18, "bold"),
            fg="white",
            bg="#2c3e50",
            pady=15
        )
        title_label.pack()

        # 主内容区域
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # 创建两个从站控制面板
        slaves_frame = tk.Frame(main_frame)
        slaves_frame.pack(fill="both", expand=True)

        # 从站1控制面板
        slave1_frame = self.create_slave_panel(slaves_frame, 1, "从站1", "设备A", "127.0.0.1:5021")
        slave1_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

        # 从站2控制面板
        slave2_frame = self.create_slave_panel(slaves_frame, 2, "从站2", "设备B", "127.0.0.1:5022")
        slave2_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

        slaves_frame.grid_columnconfigure(0, weight=1)
        slaves_frame.grid_columnconfigure(1, weight=1)
        slaves_frame.grid_rowconfigure(0, weight=1)

        # 全局控制面板
        control_frame = ttk.LabelFrame(self.root, text="全局控制", padding=10)
        control_frame.pack(fill="x", padx=10, pady=10)

        # 连接按钮
        self.connect_button = tk.Button(
            control_frame,
            text="连接所有从站",
            command=self.toggle_connection,
            font=("Arial", 10, "bold"),
            bg="#3498db",
            fg="white",
            padx=15,
            pady=8
        )
        self.connect_button.pack(side="left", padx=5)

        # 启动所有按钮
        self.start_all_button = tk.Button(
            control_frame,
            text="启动所有",
            command=self.start_all_lights,
            font=("Arial", 10, "bold"),
            bg="#27ae60",
            fg="white",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.start_all_button.pack(side="left", padx=5)

        # 停止所有按钮
        self.stop_all_button = tk.Button(
            control_frame,
            text="停止所有",
            command=self.stop_all_lights,
            font=("Arial", 10, "bold"),
            bg="#e74c3c",
            fg="white",
            padx=15,
            pady=8,
            state="disabled"
        )
        self.stop_all_button.pack(side="left", padx=5)

        # 日志区域
        log_frame = ttk.LabelFrame(self.root, text="操作日志", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.log_text = tk.Text(log_frame, height=8, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 清空日志按钮
        tk.Button(
            log_frame,
            text="清空日志",
            command=self.clear_log,
            font=("Arial", 9),
            padx=10,
            pady=5
        ).pack(side="bottom", pady=5)

    def create_slave_panel(self, parent, slave_id, name, description, address):
        """创建从站控制面板"""
        frame = ttk.LabelFrame(parent, text=name, padding=15)

        # 从站信息
        tk.Label(frame, text=description, font=("Arial", 12)).pack(anchor="w")
        tk.Label(frame, text=f"地址: {address}", font=("Arial", 10)).pack(anchor="w", pady=2)
        tk.Label(frame, text=f"从站ID: {slave_id}", font=("Arial", 10)).pack(anchor="w", pady=2)

        # 连接状态
        status_frame = tk.Frame(frame)
        status_frame.pack(fill="x", pady=10)

        tk.Label(status_frame, text="状态:", font=("Arial", 10)).pack(side="left")
        status_label = tk.Label(
            status_frame,
            text="未连接",
            font=("Arial", 10, "bold"),
            fg="red"
        )
        status_label.pack(side="left", padx=10)

        # 运行指示灯
        light_frame = tk.Frame(frame)
        light_frame.pack(fill="x", pady=10)

        tk.Label(light_frame, text="运行指示灯:", font=("Arial", 11)).pack(side="left")

        # 指示灯画布
        light_canvas = tk.Canvas(light_frame, width=40, height=40, bg="white")
        light_canvas.pack(side="left", padx=10)
        light_indicator = light_canvas.create_oval(10, 10, 30, 30, fill="red", outline="black", width=2)

        light_label = tk.Label(light_frame, text="OFF", font=("Arial", 11, "bold"), fg="red")
        light_label.pack(side="left")

        # 启动次数
        count_frame = tk.Frame(frame)
        count_frame.pack(fill="x", pady=10)

        tk.Label(count_frame, text="启动次数:", font=("Arial", 11)).pack(side="left")
        count_label = tk.Label(
            count_frame,
            text="0",
            font=("Arial", 16, "bold"),
            fg="blue"
        )
        count_label.pack(side="left", padx=10)

        # 控制按钮
        button_frame = tk.Frame(frame)
        button_frame.pack(fill="x", pady=15)

        start_button = tk.Button(
            button_frame,
            text="启动",
            command=lambda: self.control_slave_light(slave_id, True),
            font=("Arial", 10),
            bg="#27ae60",
            fg="white",
            padx=15,
            pady=5,
            state="disabled"
        )
        start_button.pack(side="left", padx=5)

        stop_button = tk.Button(
            button_frame,
            text="停止",
            command=lambda: self.control_slave_light(slave_id, False),
            font=("Arial", 10),
            bg="#e74c3c",
            fg="white",
            padx=15,
            pady=5,
            state="disabled"
        )
        stop_button.pack(side="left", padx=5)

        # 错误信息
        error_label = tk.Label(
            frame,
            text="",
            font=("Arial", 9),
            fg="red"
        )
        error_label.pack(fill="x", pady=5)

        # 保存控件引用
        self.slave_widgets[slave_id] = {
            'status_label': status_label,
            'light_canvas': light_canvas,
            'light_indicator': light_indicator,
            'light_label': light_label,
            'count_label': count_label,
            'start_button': start_button,
            'stop_button': stop_button,
            'error_label': error_label
        }

        return frame

    def log_message(self, message):
        """添加日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)

    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)

    def toggle_connection(self):
        """切换连接状态"""
        if self.slave1.connected or self.slave2.connected:
            self.disconnect_all()
        else:
            self.connect_all()

    def connect_all(self):
        """连接所有从站"""
        self.log_message("正在连接所有从站...")

        # 连接从站1
        self.log_message("连接从站1...")
        if self.slave1.connect():
            self.slave1_status['connected'] = True
            self.slave1_status['error'] = None
            self.slave_widgets[1]['status_label'].config(text="已连接", fg="green")
            self.log_message("从站1连接成功")
        else:
            self.slave1_status['connected'] = False
            self.slave1_status['error'] = "连接失败"
            self.slave_widgets[1]['status_label'].config(text="连接失败", fg="red")
            self.log_message("从站1连接失败")

        # 连接从站2
        self.log_message("连接从站2...")
        if self.slave2.connect():
            self.slave2_status['connected'] = True
            self.slave2_status['error'] = None
            self.slave_widgets[2]['status_label'].config(text="已连接", fg="green")
            self.log_message("从站2连接成功")
        else:
            self.slave2_status['connected'] = False
            self.slave2_status['error'] = "连接失败"
            self.slave_widgets[2]['status_label'].config(text="连接失败", fg="red")
            self.log_message("从站2连接失败")

        # 检查是否有从站连接成功
        if self.slave1.connected or self.slave2.connected:
            # 更新UI
            self.connect_button.config(text="断开所有连接", bg="#e74c3c")
            self.start_all_button.config(state="normal")
            self.stop_all_button.config(state="normal")

            # 启用已连接从站的按钮
            if self.slave1.connected:
                self.slave_widgets[1]['start_button'].config(state="normal")
                self.slave_widgets[1]['stop_button'].config(state="normal")

            if self.slave2.connected:
                self.slave_widgets[2]['start_button'].config(state="normal")
                self.slave_widgets[2]['stop_button'].config(state="normal")

            # 开始轮询状态
            self.start_polling()

            self.log_message("从站连接完成")
        else:
            self.log_message("所有从站连接失败")
            messagebox.showerror("连接错误", "无法连接到任何从站")

    def disconnect_all(self):
        """断开所有从站连接"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2)

        self.slave1.disconnect()
        self.slave2.disconnect()

        # 重置状态
        self.slave1_status = {'connected': False, 'run_light': False, 'start_count': 0, 'error': None}
        self.slave2_status = {'connected': False, 'run_light': False, 'start_count': 0, 'error': None}

        # 更新UI
        self.connect_button.config(text="连接所有从站", bg="#3498db")
        self.start_all_button.config(state="disabled")
        self.stop_all_button.config(state="disabled")

        for slave_id in [1, 2]:
            self.slave_widgets[slave_id]['status_label'].config(text="未连接", fg="red")
            self.slave_widgets[slave_id]['start_button'].config(state="disabled")
            self.slave_widgets[slave_id]['stop_button'].config(state="disabled")

            # 重置指示灯状态
            self.slave_widgets[slave_id]['light_canvas'].itemconfig(
                self.slave_widgets[slave_id]['light_indicator'],
                fill="red"
            )
            self.slave_widgets[slave_id]['light_label'].config(text="OFF", fg="red")
            self.slave_widgets[slave_id]['count_label'].config(text="0")
            self.slave_widgets[slave_id]['error_label'].config(text="")

        self.log_message("已断开所有从站连接")

    def start_polling(self):
        """开始轮询从站状态"""
        self.running = True

        def poll_loop():
            while self.running:
                try:
                    # 轮询从站1
                    if self.slave1.connected:
                        try:
                            run_light = self.slave1.read_coil(0)
                            start_count = self.slave1.read_register(0)

                            self.slave1_status['run_light'] = run_light
                            self.slave1_status['start_count'] = start_count
                            self.slave1_status['error'] = None

                        except Exception as e:
                            self.slave1_status['error'] = str(e)

                    # 轮询从站2
                    if self.slave2.connected:
                        try:
                            run_light = self.slave2.read_coil(0)
                            start_count = self.slave2.read_register(0)

                            self.slave2_status['run_light'] = run_light
                            self.slave2_status['start_count'] = start_count
                            self.slave2_status['error'] = None

                        except Exception as e:
                            self.slave2_status['error'] = str(e)

                    # 更新GUI
                    self.root.after(0, self.update_slave_displays)

                except Exception as e:
                    pass

                time.sleep(1)  # 每秒轮询一次

        self.polling_thread = threading.Thread(target=poll_loop, daemon=True)
        self.polling_thread.start()
        self.log_message("开始轮询从站状态")

    def update_slave_displays(self):
        """更新从站显示"""
        # 更新从站1显示
        if self.slave1_status['connected']:
            # 更新指示灯
            light_color = "green" if self.slave1_status['run_light'] else "red"
            light_text = "ON" if self.slave1_status['run_light'] else "OFF"
            light_fg = "green" if self.slave1_status['run_light'] else "red"

            self.slave_widgets[1]['light_canvas'].itemconfig(
                self.slave_widgets[1]['light_indicator'],
                fill=light_color
            )
            self.slave_widgets[1]['light_label'].config(text=light_text, fg=light_fg)

            # 更新启动次数
            self.slave_widgets[1]['count_label'].config(text=str(self.slave1_status['start_count']))

            # 更新错误信息
            if self.slave1_status['error']:
                self.slave_widgets[1]['error_label'].config(text=f"错误: {self.slave1_status['error']}")
            else:
                self.slave_widgets[1]['error_label'].config(text="")

        # 更新从站2显示
        if self.slave2_status['connected']:
            # 更新指示灯
            light_color = "green" if self.slave2_status['run_light'] else "red"
            light_text = "ON" if self.slave2_status['run_light'] else "OFF"
            light_fg = "green" if self.slave2_status['run_light'] else "red"

            self.slave_widgets[2]['light_canvas'].itemconfig(
                self.slave_widgets[2]['light_indicator'],
                fill=light_color
            )
            self.slave_widgets[2]['light_label'].config(text=light_text, fg=light_fg)

            # 更新启动次数
            self.slave_widgets[2]['count_label'].config(text=str(self.slave2_status['start_count']))

            # 更新错误信息
            if self.slave2_status['error']:
                self.slave_widgets[2]['error_label'].config(text=f"错误: {self.slave2_status['error']}")
            else:
                self.slave_widgets[2]['error_label'].config(text="")

    def start_all_lights(self):
        """启动所有从站的指示灯"""
        self.log_message("正在启动所有从站的运行指示灯...")

        if self.slave1.connected:
            try:
                self.slave1.write_coil(0, True)
                self.log_message("从站1: 启动命令发送成功")
            except Exception as e:
                self.log_message(f"从站1: 启动失败 - {str(e)}")

        if self.slave2.connected:
            try:
                self.slave2.write_coil(0, True)
                self.log_message("从站2: 启动命令发送成功")
            except Exception as e:
                self.log_message(f"从站2: 启动失败 - {str(e)}")

    def stop_all_lights(self):
        """停止所有从站的指示灯"""
        self.log_message("正在停止所有从站的运行指示灯...")

        if self.slave1.connected:
            try:
                self.slave1.write_coil(0, False)
                self.log_message("从站1: 停止命令发送成功")
            except Exception as e:
                self.log_message(f"从站1: 停止失败 - {str(e)}")

        if self.slave2.connected:
            try:
                self.slave2.write_coil(0, False)
                self.log_message("从站2: 停止命令发送成功")
            except Exception as e:
                self.log_message(f"从站2: 停止失败 - {str(e)}")

    def control_slave_light(self, slave_id, turn_on):
        """控制单个从站的指示灯"""
        action = "启动" if turn_on else "停止"
        self.log_message(f"正在{action}从站{slave_id}的运行指示灯...")

        try:
            if slave_id == 1 and self.slave1.connected:
                self.slave1.write_coil(0, turn_on)
                self.log_message(f"从站1: {action}命令发送成功")
            elif slave_id == 2 and self.slave2.connected:
                self.slave2.write_coil(0, turn_on)
                self.log_message(f"从站2: {action}命令发送成功")
            else:
                self.log_message(f"从站{slave_id}: 未连接，无法控制")
        except Exception as e:
            self.log_message(f"从站{slave_id}: {action}失败 - {str(e)}")

    def update_status(self):
        """更新状态"""
        self.root.after(1000, self.update_status)

    def on_closing(self):
        """窗口关闭事件"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=2)

        self.slave1.disconnect()
        self.slave2.disconnect()

        self.root.destroy()

    def run(self):
        """运行GUI"""
        self.root.mainloop()

def main():
    """主函数"""
    print("=" * 60)
    print("MODBUS主站控制系统")
    print("=" * 60)
    print("系统配置:")
    print("  从站1: ID=1, 地址=127.0.0.1:5021")
    print("  从站2: ID=2, 地址=127.0.0.1:5022")
    print("=" * 60)

    app = MasterGUI()
    app.run()

if __name__ == "__main__":
    main()
