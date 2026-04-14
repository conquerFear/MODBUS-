"""
MODBUS协议核心工具
"""

class ModbusMemory:
    """MODBUS从站内存"""
    def __init__(self):
        # 线圈内存 (地址0-65535)
        self.coils = [0] * 65536
        # 保持寄存器内存 (地址0-65535)
        self.holding_registers = [0] * 65536

        # 初始化从站特定地址
        self.coils[0] = 0  # 地址0: 运行指示灯
        self.holding_registers[0] = 0  # 地址0: 启动次数计数器

    def read_coil(self, address):
        """读取单个线圈"""
        if 0 <= address < len(self.coils):
            return self.coils[address]
        return 0

    def write_coil(self, address, value):
        """写入单个线圈"""
        if 0 <= address < len(self.coils):
            old_value = self.coils[address]
            self.coils[address] = 1 if value else 0

            # 如果写入运行指示灯地址(0)且从OFF变ON，增加启动次数
            if address == 0 and old_value == 0 and value == 1:
                self.holding_registers[0] += 1

            return True
        return False

    def read_holding_register(self, address):
        """读取单个保持寄存器"""
        if 0 <= address < len(self.holding_registers):
            return self.holding_registers[address]
        return 0

    def write_holding_register(self, address, value):
        """写入单个保持寄存器"""
        if 0 <= address < len(self.holding_registers):
            self.holding_registers[address] = value
            return True
        return False

class ModbusFrame:
    """MODBUS帧处理"""

    @staticmethod
    def create_request(slave_id, function_code, address, value=None):
        """创建MODBUS TCP请求帧"""
        # 事务标识 (2字节)
        transaction_id = b'\x00\x01'
        # 协议标识 (2字节，MODBUS协议为0)
        protocol_id = b'\x00\x00'
        # 单元标识 (从站ID)
        unit_id = slave_id.to_bytes(1, 'big')

        if function_code == 0x01:  # 读线圈
            # PDU: 功能码(1) + 起始地址(2) + 线圈数量(2)
            pdu = function_code.to_bytes(1, 'big') + address.to_bytes(2, 'big') + b'\x00\x01'

        elif function_code == 0x03:  # 读保持寄存器
            # PDU: 功能码(3) + 起始地址(2) + 寄存器数量(2)
            pdu = function_code.to_bytes(1, 'big') + address.to_bytes(2, 'big') + b'\x00\x01'

        elif function_code == 0x05:  # 写单个线圈
            # PDU: 功能码(5) + 线圈地址(2) + 值(2, 0xFF00=ON, 0x0000=OFF)
            coil_value = b'\xFF\x00' if value else b'\x00\x00'
            pdu = function_code.to_bytes(1, 'big') + address.to_bytes(2, 'big') + coil_value

        elif function_code == 0x06:  # 写单个寄存器
            # PDU: 功能码(6) + 寄存器地址(2) + 值(2)
            pdu = function_code.to_bytes(1, 'big') + address.to_bytes(2, 'big') + value.to_bytes(2, 'big')

        else:
            raise ValueError(f"不支持的函数码: {function_code}")

        # 计算长度 (单元标识长度 + PDU长度)
        length = (len(unit_id) + len(pdu)).to_bytes(2, 'big')

        # 完整的MODBUS TCP帧
        frame = transaction_id + protocol_id + length + unit_id + pdu
        return frame

    @staticmethod
    def parse_response(frame, expected_function):
        """解析MODBUS响应帧"""
        if len(frame) < 8:
            raise ValueError("响应帧太短")

        # 跳过头部 (事务ID2 + 协议ID2 + 长度2 + 单元ID1)
        pdu_start = 7

        # 检查异常响应
        if frame[pdu_start] == expected_function + 0x80:
            if len(frame) >= pdu_start + 2:
                error_code = frame[pdu_start + 1]
                raise Exception(f"MODBUS异常响应，错误码: {error_code}")

        # 正常响应
        if frame[pdu_start] != expected_function:
            raise ValueError(f"响应函数码不匹配，期望: {expected_function}，实际: {frame[pdu_start]}")

        # 根据功能码解析数据
        if expected_function == 0x01:  # 读线圈
            byte_count = frame[pdu_start + 1]
            if byte_count == 1:
                coil_value = frame[pdu_start + 2]
                return bool(coil_value & 0x01)

        elif expected_function == 0x03:  # 读保持寄存器
            byte_count = frame[pdu_start + 1]
            if byte_count == 2:
                register_value = int.from_bytes(frame[pdu_start + 2:pdu_start + 4], 'big')
                return register_value

        elif expected_function in (0x05, 0x06):  # 写线圈或写寄存器
            # 返回写入的地址和值
            address = int.from_bytes(frame[pdu_start + 1:pdu_start + 3], 'big')
            value = int.from_bytes(frame[pdu_start + 3:pdu_start + 5], 'big')
            if expected_function == 0x05:
                value = bool(value == 0xFF00)  # 转换为布尔值
            return address, value

        raise ValueError("无法解析响应帧")