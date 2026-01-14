# OpenMV UART Serial Communication Test Code
# Author: Jees996 (Leexian)
# Description: 这是一个用于测试 OpenMV 与外部设备（如 STM32）进行串口通信的独立脚本。
#              包含了数据的打包发送（ustruct）和基于状态机的接收解析。
#              注意，这部分代码是从源程序中提取的独立模块，适合直接运行在 OpenMV 上进行测试。

import time
from pyb import UART # type: ignore
import ustruct # type: ignore

# —————————————————— 配置参数 —————————————————— #
# 串口波特率
BAUD_RATE = 115200

# 实例化 UART 对象
# UART(3) 对应 OpenMV 的 P4 (TX) 和 P5 (RX)
# timeout_char=100 表示字符之间的超时时间为 100ms
uart = UART(3, BAUD_RATE, timeout_char=100)

# —————————————————— 全局变量 —————————————————— #
# 接收相关变量
uart_state = 0              # 接收状态机的当前状态
uart_data = [0x00] * 9      # 暂存接收到的数据包（假设数据包长度为9字节，根据实际协议修改）

# 解析出的结果变量（示例）
rx_color_numbers = [0, 0, 0] # 接收到的颜色顺序
rx_car_state = 0             # 接收到的小车状态
rx_step = 0                  # 接收到的步骤信息

# —————————————————— 发送功能 —————————————————— #
def send_data_packet(c1, c2, c3, c4, c5):
    """
    功能：打包并发送5个数据字节
    协议格式：帧头(0xA5, 0xA6) + 数据(5字节) + 帧尾(0x5B)
    """
    global uart
    
    # ustruct.pack 用于将数据转换成二进制流
    # "<BBBBBBBB" 含义：
    # < : 小端模式 (Little Endian)
    # B : 无符号字符 (unsigned char, 1字节)
    data = ustruct.pack("<BBBBBBBB",
                   0xA5,    # 帧头1
                   0xA6,    # 帧头2
                   c1,      # 数据1 (例如：保留位)
                   c2,      # 数据2 (例如：抓取标志)
                   c3,      # 数据3 (例如：X轴偏差)
                   c4,      # 数据4 (例如：Y轴偏差)
                   c5,      # 数据5 (例如：保留位)
                   0x5B     # 帧尾
                   )
    
    # 发送数据
    uart.write(data)
    
    # Debug打印：显示发送的原始十六进制数据
    print(f"[TX Send] Hex: {[hex(b) for b in data]}")


# —————————————————— 接收功能 —————————————————— #
def receive_data_process():
    """
    功能：读取串口缓冲区并使用状态机解析数据
    协议格式（示例）：帧头(0xDF) + 数据...
    """
    global uart_state, uart_data
    global rx_color_numbers, rx_car_state, rx_step

    # 检查串口缓冲区是否有数据
    if uart.any() > 0:
        
        # 读取一个字节
        char_in = uart.readchar()
        
        # ———— 状态机解析逻辑 ———— #
        # 状态0：寻找帧头 0xDF
        if uart_state == 0:
            if char_in == 0xDF:
                uart_data[0] = char_in
                uart_state = 1
            else:
                uart_state = 0 # 没读到帧头，重置
        
        # 状态1：接收颜色1
        elif uart_state == 1:
            if char_in == 0xDF: # 防止帧头误判
                uart_state = 1
            else:
                uart_data[1] = char_in
                rx_color_numbers[0] = int(char_in)
                uart_state = 2
                
        # 状态2：接收颜色2
        elif uart_state == 2:
            if char_in == 0xDF:
                uart_state = 1
            else:
                uart_data[2] = char_in
                rx_color_numbers[1] = int(char_in)
                uart_state = 3

        # 状态3：接收颜色3
        elif uart_state == 3:
            if char_in == 0xDF:
                uart_state = 1
            else:
                uart_data[3] = char_in
                rx_color_numbers[2] = int(char_in)
                uart_state = 4

        # 状态4：接收小车状态 (car_state)
        elif uart_state == 4:
            if char_in == 0xDF:
                uart_state = 1
            else:
                uart_data[4] = char_in
                rx_car_state = int(char_in)
                uart_state = 5

        # 状态5：接收颜色切换标志 (color_change_flag) - 假设
        elif uart_state == 5:
            if char_in == 0xDF:
                uart_state = 1
            else:
                uart_data[5] = char_in
                uart_state = 6

        # 状态6：接收步骤 (color_step) - 结束并打印
        elif uart_state == 6:
            if char_in == 0xDF:
                uart_state = 1
            else:
                uart_data[6] = char_in
                rx_step = int(char_in)
                
                # —— 解析完成，执行相应操作 —— #
                # 这里可以添加数据校验逻辑
                
                # Debug打印：解析成功后的数据
                print(f"[RX Done] Colors:{rx_color_numbers}, State:{rx_car_state}, Step:{rx_step}")
                
                # 重置状态机，准备接收下一帧
                uart_state = 7 

        # 状态复位
        elif uart_state == 7:
            uart_state = 0
            
        else:
            uart_state = 0

# —————————————————— 主程序循环 —————————————————— #
def main():
    print("UART Communication Test Started...")
    print("Baudrate: 115200, Port: P4(TX)/P5(RX)")
    
    last_send_time = 0
    
    while True:
        # 1. 持续接收数据（必须在主循环中高频调用）
        receive_data_process()
        
        # 2. 定时发送测试数据（例如每1秒发一次）
        current_time = time.ticks_ms()
        if time.ticks_diff(current_time, last_send_time) > 1000:
            
            # 模拟数据：(保留, 允许抓取, X偏左, Y居中, 保留)
            # 对应协议变量: c1, catch_flag, Xx, Xy, c5
            send_data_packet(1, 1, 1, 0, 0)
            
            last_send_time = current_time

if __name__ == "__main__":
    main()