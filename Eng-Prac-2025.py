import sensor                   # type: ignore # 导入 OpenMV 摄像头模块
import ustruct                  # type: ignore
from pyb import UART            # type: ignore
from pyb import LED             # type: ignore
from pyb import Pin, Timer      # type: ignore

#——————————————————————————变量——————————————————————————#
threshold_index = 0                 # 选择颜色跟踪阈值的索引（0为红色，1为绿色，2为蓝色）

Goods_thresholds = [                # 物料颜色阈值
    (39, 74, 18, 82, 14, 78),      # 红色的阈值范围
    (57, 77, -19, -63, 27, 3),    # 绿色的阈值范围
    (42, 78, 12, -24, -12, -56),    # 蓝色的阈值范围
]                                   # 阈值列表，用于色块跟踪的颜色设定


color           = 0                 # 识别到的颜色
color_flag      = 0                 # 识别对象颜色标志位
position_flag   = 0                 # 识别对象到达目标点标志位

#以下为串口发送的数据
catch_flag      = 0                 # 抓取标志位
Xx              = 0                 # x方向运动数据
Xy              = 0                 # y方向运动数据

#串口接收的数据和变量：
uart_state          = 0
uart_data           = [0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00]

color_number        = [0x00,0x00,0x00]
car_state           = 1    # 小车状态 储存串口发送过来小车状态
color_change_flag   = 0    # 目标颜色切换标志位
color_step          = 1

#目标颜色切换所需变量
color_serial            = 0  # 颜色顺序


center_x        = 70               # 识别的X轴中心点
center_y        = 60                # 识别的Y轴中心点
side_length     = 8                # 识别的范围框宽度

DEBUG = True                        # 开启/关闭Debug

x_date          = 0
y_date          = 0

#——————————————————————————外设——————————————————————————#
uart = UART(3, 115200, timeout_char=100)                           # 打开UART串口，波特率115200，最长等待时间1000ms

light = Timer(2, freq=50000).channel(1, Timer.PWM, pin=Pin("P6"))   # 开启定时器2通道1的PWM功能，时钟频率为50kHz pin6

led_red     = LED(1)
led_green   = LED(2)
led_blue    = LED(3)
#——————————————————————————函数——————————————————————————#
def main():

    openmv_init()
    LED_Bord(80)
    while True:
        img_get()

        state_switching()

        check_position(x_date, y_date)
        check_color(color)
        is_catch_ok()

        uart_recieve()
        uasrt_translate_five_uchar(1,catch_flag,Xx,Xy,0)

        if DEBUG:# 仅在调试模式下运行的程序
            draw_red_square(img, center_x, center_y, side_length)
            # print(f"catch_flag: {catch_flag}, x_date: {x_date}, y_date: {y_date}")
            # print(f"catch_flag: {catch_flag}, Xx: {Xx}, Xy: {Xy}，color_flag{color_flag},position_flag{position_flag},color{color}")  # 输出: catch_flag,Xx,Xy
#            print(f"color_number: {color_number},catch_flag{catch_flag},color_flag{color_flag},position_flag{position_flag},color{color}")
            # print(f"color1 = {color1}, color2 = {color2}, color3 = {color3}, color4 = {color4}, color5 = {color5}, color6 = {color6}")
            print(f"{color_number} ,{car_state}, {color_change_flag},{color_step}")
            # print(f"{car_state}")
        pass
    pass


def state_switching():
    global x_date,y_date
    if car_state == 1 or car_state == 3:       #小车当前为识别物料模式
        color_track()

    elif car_state == 2:       #小车当前为识别色环模式
        find_green_circles()
    else:
        x_date  = None
        y_date  = None
    pass


##########基础算法相关函数##########
def check_position(x, y):               # 判断目标是否位于设定位置
    """
    根据物体位置确定其状态，更新抓取标志和方向。

    :param center_x: 物体中心的 x 坐标
    :param center_y: 物体中心的 y 坐标
    """
    global position_flag,Xx,Xy,center_x,center_y                 # 声明需要修改的全局变量

    if x is None or y is None:              # 如果未检测到物料，重置状态
        position_flag = 0
        Xx = 0
        Xy = 0
        return

    if center_x - side_length <= x <= center_x + side_length and center_y - side_length <= y <= center_y + side_length:   # 检查是否在中心区域
        position_flag      = 1
        Xx              = 0
        Xy              = 0
        return

    position_flag      = 0                     # 不在中心区域时重置抓取标志位

    if center_x - side_length <= x <= center_x + side_length:   # 判断 x 方向
        Xx              = 0
    elif x < center_x - side_length:
        Xx              = 1
    elif x > center_x + side_length:
        Xx              = 2

    if center_y - side_length <= y <= center_y + side_length:                     # 判断 y 方向
        Xy              = 0
    elif y < center_y - side_length:
        Xy              = 1
    elif y > center_y + side_length:
        Xy              = 2

    return


def check_color(mycolor):               # 判断颜色是否正确
    global color_flag
    if car_state == 1 or car_state == 3:
        if mycolor == color_number[color_serial_number()]:
            color_flag = 1
        else:
            color_flag = 0
    elif car_state == 2:
        color_flag = 1
    else:
        color_flag = 0


def is_catch_ok():
    global catch_flag

    if position_flag == 1 and color_flag == 1:
        catch_flag = 1
    else:
        catch_flag = 0


def color_serial_number():
    serial_number =  color_step - 1
    if serial_number < 0 or serial_number > 2:
        serial_number = 0
    return serial_number


def color_judge(mycolor):               # 颜色判断
    if mycolor == 1:
        return 1                        # 红色
    elif mycolor == 2:
        return 2                        # 绿色
    elif mycolor == 4:
        return 3                        # 蓝色
    else:
        print("other")
        return 0
##########视觉处理相关函数##########
def color_track():                      # 物料识别算法
    global color,x_date,y_date,img
    # img = sensor.snapshot()             # 捕获一帧图像
    x_date  = None
    y_date  = None
    color   = 0
    # print("running")

    for blob in img.find_blobs(
        Goods_thresholds,               # 追踪物料全部颜色
#        [Goods_thresholds[color_set()]],  # 根据当前阈值进行色块跟踪
        pixels_threshold = 900,         # 仅返回大于600个像素的色块
        area_threshold   = 900,         # 仅返回大于600平方像素的色块
        merge=False,                    # 合并重叠的色块
    ):
        img.draw_rectangle(blob.rect())  # 绘制色块的矩形框
        img.draw_cross(blob.cx(), blob.cy())  # 绘制色块中心的十字线标记

        # 更新为检测到的色块数据
        color   = color_judge(blob.code())
        x_date  = blob.cx()
        y_date  = blob.cy()

def find_green_circles():
    global color,x_date,y_date,img
    x_date  = None
    y_date  = None
    for c in img.find_circles(
        threshold=2800,
        x_margin=50,
        y_margin=50,
        r_margin=20,
        r_min=5,
        r_max=30,
        r_step=1,
    ):
        img.draw_circle(c.x(), c.y(), c.r(), color=(255, 0, 0))
        img.draw_cross(c.x(), c.y())  # 绘制色块中心的十字线标记
        x_date  = c.x()
        y_date  = c.y()
        # print(c)
    pass

def find_blue_circles():
    img = sensor.snapshot()
    for c in img.find_circles(
        threshold=1800,
        x_margin=50,
        y_margin=50,
        r_margin=20,
        r_min=5,
        r_max=30,
        r_step=1,
    ):
        img.draw_circle(c.x(), c.y(), c.r(), color=(255, 0, 0))
        img.draw_cross(c.x(), c.y())  # 绘制色块中心的十字线标记
        # x_date  = c.cx()
        # y_date  = c.cy()
        # print(c)
    pass


##########OpenMV相关函数##########
def openmv_init():                          # 初始化openmv模块
    sensor.reset()
    sensor.set_pixformat(sensor.RGB565)  # grayscale is faster
    sensor.set_framesize(sensor.QQVGA)
    sensor.skip_frames(time=2000)
    return


def img_get():                          # 获取图像
    global img
    img = sensor.snapshot()             # 捕获一帧图像


##########UART串口相关函数##########
def uasrt_translate_five_uchar(c1,c2,c3,c4,c5):         #发送五个无符号字符数据（unsigned char）
    global uart
    data = ustruct.pack("<BBBBBBBB",        #使用了 ustruct.pack() 函数将这些数据打包为二进制格式。使用 "<BBBBBBBB" 作为格式字符串来指定要打包的数据的类型和顺序：
                   0xA5,
                   0xA6,
                   c1,
                   c2,
                   c3,
                   c4,
                   c5,
                   0x5B
                   )
    uart.write(data);                       #uart.write(data) 将打包好的二进制数据帧写入 UART 发送缓冲区，从而将数据通过串口发送出去



def uart_recieve():                         # 接收串口数据并处理
    if(uart.any()>0):
        # print("code running")
        Receive_Prepare()


def Receive_Prepare():                      # 串口数据解析处理
    global uart_state,uart_data
    global color_number
    global car_state,color_change_flag,color_step

    if uart_state==0:
        uart_data[0]=uart.readchar()
        if uart_data[0] == 0xdf:#帧头
            uart_state = 1
        else:
            uart_state = 0


    elif uart_state == 1:
        uart_data[1]=uart.readchar()
        if uart_data[1] == 0xdf:#帧头
            uart_state = 1
        else:
            color_number[0] = int(uart_data[1])
            uart_state = 2


    elif uart_state==2:
        uart_data[2]=uart.readchar()
        if uart_data[2] == 0xdf:#帧头
            uart_state = 1
        else:
            color_number[1] = int(uart_data[2])
            uart_state = 3

    elif uart_state==3:
        uart_data[3]=uart.readchar()
        if uart_data[3] == 0xdf:#帧头
            uart_state = 1
        else:
            color_number[2] = int(uart_data[3])
            uart_state = 4

    elif uart_state==4:
        uart_data[4]=uart.readchar()
        if uart_data[4] == 0xdf:#帧头
            uart_state = 1
        else:
            car_state = int(uart_data[4])
            uart_state = 5

    elif uart_state==5:
        uart_data[5]=uart.readchar()
        if uart_data[5] == 0xdf:#帧头
            uart_state = 1
        else:
            color_change_flag = int(uart_data[5])
            uart_state = 6

    elif uart_state == 6:
        uart_data[6]=uart.readchar()
        if uart_data[6] == 0xdf:#帧头
            uart_state = 1
        else:
            color_step = int(uart_data[6])
            uart_state = 7

    # elif uart_state == 7:
    #     uart_data[7]=uart.readchar()
    #     current_color = uart_data[7]
    #     uart_state = 8

    # elif uart_state == 8:
    #     uart_data[8]=uart.readchar()
    #     Temporary_Data = uart_data[8]
    #     uart_state = 9

    elif uart_state == 7:
        uart_state=0

    else:
        uart_state = 0


##########外设相关函数##########
def led_init():
    led_red.on()
    led_green.on()
    led_blue.on()


def LED_Bord(a):
    light.pulse_width_percent(a) # 控制亮度 0~100


def draw_red_square(img, center_x, center_y, side_length):
    """
    在图像上绘制一个红色正方形框。

    :param img: 当前图像
    :param center_x: 正方形中心点的 x 坐标
    :param center_y: 正方形中心点的 y 坐标
    :param side_length: 正方形的边长
    """
    x = center_x - side_length // 2
    y = center_y - side_length // 2
    img.draw_rectangle(x, y, side_length, side_length, color=(255, 0, 0), thickness=2)



if __name__ == "__main__":
    main()
