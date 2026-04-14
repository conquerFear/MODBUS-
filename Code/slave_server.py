"""
MODBUS从站服务器
每个从站运行独立的服务器实例
"""

import socket
import threading
import time
import tkinter as tk
from tkinter import ttk
from modbus_utils import ModbusMemory, ModbusFrame


class ModbusSlave:
    """MODBUS从站"""

    def __init__(self, slave_id, name, port):
        self.slave_id = slave_id
        self.name = name
        self.port = port
        self.memory = ModbusMemory()
        self.running = False
        self.server_socket = None
        self.connections = []

        # GUI相关
        self.root = None
        self.light_label = None
        self.count_label = None
        self.status_label = None

        print(f"从站 {name} (ID: {slave_id}) 初始化完成，端口: {port}")

    def start_server(self):
        """启动服务器"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            print(f"{self.name} 服务器启动，监听端口 {self.port}")

            # 启动GUI
            self.start_gui()

            # 接受客户端连接
            accept_thread = threading.Thread(target=self.accept_connections, daemon=True)
            accept_thread.start()

            # 运行GUI主循环
            self.root.mainloop()

        except Exception as e:
            print(f"{self.name} 服务器启动失败: {e}")
            self.stop_server()

    def stop_server(self):
        """停止服务器"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()

        for conn in self.connections:
            conn.close()

        if self.root:
            self.root.quit()

        print(f"{self.name} 服务器已停止")

    def accept_connections(self):
        """接受客户端连接"""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"{self.name}: 客户端连接: {client_address}")

                # 为每个客户端创建处理线程
                client_thread = threading.Thread(
                    target=self.handle_client,
                    args=(client_socket,),
                    daemon=True
                )
                client_thread.start()

                self.connections.append(client_socket)

            except Exception as e:
                if self.running:
                    print(f"{self.name}: 接受连接错误: {e}")

    def handle_client(self, client_socket):
        """处理客户端请求"""
        try:
            while self.running:
                # 接收请求
                data = client_socket.recv(256)
                if not data:
                    break

                # 处理MODBUS请求
                response = self.process_modbus_request(data)

                # 发送响应
                if response:
                    client_socket.send(response)

        except Exception as e:
            pass
        finally:
            client_socket.close()
            if client_socket in self.connections:
                self.connections.remove(client_socket)

    def process_modbus_request(self, request_data):
        """处理MODBUS请求"""
        try:
            # 解析请求头
            if len(request_data) < 8:
                return None

            # 提取从站ID
            slave_id = request_data[6]

            # 检查从站ID是否匹配
            if slave_id != self.slave_id:
                return None

            # 提取功能码
            function_code = request_data[7]

            # 根据功能码处理请求
            if function_code == 0x01:  # 读线圈
                return self.handle_read_coil(request_data)
            elif function_code == 0x03:  # 读保持寄存器
                return self.handle_read_register(request_data)
            elif function_code == 0x05:  # 写单个线圈
                return self.handle_write_coil(request_data)
            elif function_code == 0x06:  # 写单个寄存器
                return self.handle_write_register(request_data)
            else:
                # 不支持的函数码
                return self.create_error_response(function_code, 0x01)

        except Exception as e:
            print(f"处理MODBUS请求错误: {e}")
            return None

    def handle_read_coil(self, request_data):
        """处理读线圈请求"""
        try:
            # 提取地址
            address = int.from_bytes(request_data[8:10], 'big')

            # 读取线圈值
            coil_value = self.memory.read_coil(address)

            # 构建响应
            response = bytearray(request_data[:7])  # 复制头部
            response[4:6] = b'\x00\x04'  # 更新长度
            response.append(0x01)  # 功能码
            response.append(0x01)  # 字节数
            response.append(0xFF if coil_value else 0x00)  # 线圈值

            return bytes(response)

        except Exception as e:
            print(f"处理读线圈错误: {e}")
            return self.create_error_response(0x01, 0x04)

    def handle_read_register(self, request_data):
        """处理读寄存器请求"""
        try:
            # 提取地址
            address = int.from_bytes(request_data[8:10], 'big')

            # 读取寄存器值
            register_value = self.memory.read_holding_register(address)

            # 构建响应
            response = bytearray(request_data[:7])  # 复制头部
            response[4:6] = b'\x00\x05'  # 更新长度
            response.append(0x03)  # 功能码
            response.append(0x02)  # 字节数
            response.extend(register_value.to_bytes(2, 'big'))  # 寄存器值

            return bytes(response)

        except Exception as e:
            print(f"处理读寄存器错误: {e}")
            return self.create_error_response(0x03, 0x04)

    def handle_write_coil(self, request_data):
        """处理写线圈请求"""
        try:
            # 提取地址和值
            address = int.from_bytes(request_data[8:10], 'big')
            value = int.from_bytes(request_data[10:12], 'big')

            # 检查值是否有效
            if value not in (0x0000, 0xFF00):
                return self.create_error_response(0x05, 0x03)

            # 写入线圈
            coil_state = (value == 0xFF00)
            self.memory.write_coil(address, coil_state)

            # 更新GUI显示
            self.update_gui_display()

            # 构建响应 (回显请求)
            return request_data

        except Exception as e:
            print(f"处理写线圈错误: {e}")
            return self.create_error_response(0x05, 0x04)

    def handle_write_register(self, request_data):
        """处理写寄存器请求"""
        try:
            # 提取地址和值
            address = int.from_bytes(request_data[8:10], 'big')
            value = int.from_bytes(request_data[10:12], 'big')

            # 写入寄存器
            self.memory.write_holding_register(address, value)

            # 更新GUI显示
            self.update_gui_display()

            # 构建响应 (回显请求)
            return request_data

        except Exception as e:
            print(f"处理写寄存器错误: {e}")
            return self.create_error_response(0x06, 0x04)

    def create_error_response(self, function_code, error_code):
        """创建错误响应"""
        response = bytearray(b'\x00\x01\x00\x00\x00\x03')
        response.append(self.slave_id)
        response.append(function_code + 0x80)  # 异常功能码
        response.append(error_code)  # 异常代码
        return bytes(response)

    def start_gui(self):
        """启动从站GUI"""
        self.root = tk.Tk()
        self.root.title(f"{self.name} - MODBUS从站")
        self.root.geometry("400x300")

        # 设置UI
        self.setup_gui()

        # 初始更新显示
        self.update_gui_display()

    def setup_gui(self):
        """设置从站GUI"""
        # 标题
        title_label = tk.Label(
            self.root,
            text=self.name,
            font=("Arial", 16, "bold"),
            pady=20
        )
        title_label.pack()

        # 从站信息
        info_frame = ttk.Frame(self.root)
        info_frame.pack(pady=10)

        tk.Label(info_frame, text=f"从站ID: {self.slave_id}", font=("Arial", 10)).pack(anchor="w")
        tk.Label(info_frame, text=f"端口: {self.port}", font=("Arial", 10)).pack(anchor="w")

        # 运行指示灯
        light_frame = ttk.LabelFrame(self.root, text="运行指示灯", padding=10)
        light_frame.pack(pady=10, padx=20, fill="x")

        self.light_canvas = tk.Canvas(light_frame, width=50, height=50, bg="white")
        self.light_canvas.pack()
        self.light_indicator = self.light_canvas.create_oval(10, 10, 40, 40, fill="red", outline="black", width=2)

        self.light_label = tk.Label(light_frame, text="OFF", font=("Arial", 12, "bold"), fg="red")
        self.light_label.pack()

        # 启动次数
        count_frame = ttk.LabelFrame(self.root, text="启动次数", padding=10)
        count_frame.pack(pady=10, padx=20, fill="x")

        self.count_label = tk.Label(
            count_frame,
            text="0",
            font=("Arial", 20, "bold"),
            fg="blue"
        )
        self.count_label.pack()

        # 状态信息
        status_frame = ttk.Frame(self.root)
        status_frame.pack(pady=10)

        self.status_label = tk.Label(status_frame, text="等待连接...", font=("Arial", 10), fg="gray")
        self.status_label.pack()

    def update_gui_display(self):
        """更新GUI显示"""
        if not self.root:
            return

        # 更新运行指示灯
        light_state = self.memory.read_coil(0)
        light_color = "green" if light_state else "red"
        light_text = "ON" if light_state else "OFF"
        light_fg = "green" if light_state else "red"

        self.light_canvas.itemconfig(self.light_indicator, fill=light_color)
        self.light_label.config(text=light_text, fg=light_fg)

        # 更新启动次数
        start_count = self.memory.read_holding_register(0)
        self.count_label.config(text=str(start_count))

        # 更新状态
        if len(self.connections) > 0:
            self.status_label.config(text=f"已连接客户端: {len(self.connections)}", fg="green")
        else:
            self.status_label.config(text="等待连接...", fg="gray")


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='MODBUS从站服务器')
    parser.add_argument('--id', type=int, required=True, help='从站ID')
    parser.add_argument('--name', type=str, required=True, help='从站名称')
    parser.add_argument('--port', type=int, required=True, help='监听端口')

    args = parser.parse_args()

    print("=" * 50)
    print(f"启动MODBUS从站 - {args.name}")
    print("=" * 50)
    print(f"从站ID: {args.id}")
    print(f"监听端口: {args.port}")
    print("=" * 50)

    slave = ModbusSlave(slave_id=args.id, name=args.name, port=args.port)

    try:
        slave.start_server()
    except KeyboardInterrupt:
        print("\n正在停止从站...")
        slave.stop_server()


if __name__ == "__main__":
    main()