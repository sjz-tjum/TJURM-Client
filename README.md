MQTT H.264 视频接收端 (Windows 专用)

https://img.shields.io/badge/Python-3.8+-blue.svg](https://www.python.org/downloads/)
https://img.shields.io/badge/Platform-Windows-lightgrey.svg](https://www.microsoft.com/windows)

一个基于 PyQt5、MQTT 和 PyAV (FFmpeg) 的高性能 H.264 低延迟视频流接收与解码程序。专为 Windows 平台优化，支持从 MQTT 字节流中实时重组并显示视频。

📸 功能特性

•   🖥️ 图形化界面 (GUI): 基于 PyQt5 构建，提供直观的控制面板，包括连接状态指示灯、实时视频显示区和日志输出区。

•   📡 MQTT 通信: 支持连接 MQTT Broker，订阅指定主题接收视频数据包。

•   🎞️ H.264 实时解码: 使用 PyAV (FFmpeg 封装) 进行硬件加速友好的 H.264 解码。

•   📦 智能流重组: 自动处理 MQTT 分包发送的 H.264 NAL 单元，支持 SPS/PPS 参数集的提取与注入。

•   📊 实时统计: 显示接收包数、解码帧数、解码 FPS、显示 FPS 及网络丢包数。

•   ⚙️ Windows 优化: 专门针对 Windows 环境配置了 Qt 平台插件和高 DPI 支持。

🏗️ 系统架构

程序主要由以下几个模块构成：

1.  主窗口 (main_window.py): UI 控制中心，负责按钮事件、日志显示和视频渲染。
2.  MQTT 客户端 (mqtt_client/client.py): 负责与 MQTT Broker 建立连接、订阅主题并将接收到的消息放入队列。
3.  视频处理线程 (video/processor_thread.py):
    ◦   从 MQTT 队列中取出数据。

    ◦   进行丢包检测和序列号校验。

    ◦   关键步骤: 从视频流中提取 SPS/PPS（参数集），并转换为 avcC 格式注入解码器。

    ◦   管理解码缓冲区，进行软截断以防止内存溢出。

4.  H.264 解码器 (video/h264_decoder.py): 封装了 PyAV.CodecContext，负责实际的 H.264 码流解析和解码工作。
5.  工具类 (utils/): 包含常量定义和图像叠加工具（如准心绘制）。

🚀 快速开始

1. 环境准备

•   操作系统: Windows 10 / 11

•   Python: 3.8 或更高版本

•   MQTT Broker: 确保有一个运行中的 MQTT Broker（例如 Mosquitto）。

2. 安装依赖

建议使用虚拟环境（如 venv 或 conda）安装依赖。
# 克隆或下载本项目代码
cd mqttclient

# 安装所需库
pip install PyQt5 av opencv-python paho-mqtt psutil protobuf


3. 配置参数

在运行前，请根据您的实际情况修改以下配置：

•   MQTT Broker 地址:

    打开 ui/main_window.py，找到 _on_connect_clicked 方法，修改 broker 和 port。
    broker = "192.168.12.1"  # 修改为您的 MQTT Broker IP
    port = 3333             # 修改为您的 MQTT Broker 端口
    

•   视频分辨率:

    打开 utils/constants.py，修改 VIDEO_WIDTH 和 VIDEO_HEIGHT 以匹配发送端的视频源分辨率。
    VIDEO_WIDTH = 300
    VIDEO_HEIGHT = 300
    

4. 运行程序

python main.py


📖 使用说明

1.  启动程序: 运行 python main.py。
2.  输入 Client ID: 程序启动后会弹出一个对话框，输入 MQTT 客户端 ID（可留空自动生成）。
3.  连接 MQTT: 点击 "🔌 连接 MQTT" 按钮。状态指示灯变为绿色表示连接成功。
4.  开始解码: 连接成功后，点击 "▶ 开始解码" 启动视频处理线程。
5.  查看视频: 视频流将从 MQTT 主题接收并显示在主窗口的视频区域。
6.  查看日志: 底部日志区域会实时输出连接状态、丢包信息和错误信息。

💻 代码结构详解


mqttclient/
├── main.py                  # 程序入口，Qt 环境与字体配置
├── main_window.py           # PyQt5 主窗口 UI 与逻辑
├── constants.py             # 全局常量 (分辨率、包大小等)
│
├── mqtt_client/
│   └── client.py           # MQTT 接收客户端
│
├── video/
│   ├── processor_thread.py  # 视频处理核心线程 (重组、统计)
│   ├── h264_decoder.py      # H.264 解码器封装 (PyAV)
│   └── packet_reassembler.py (可选，当前未启用)
│
├── utils/
│   ├── overlay.py           # 图像绘制工具 (准心)
│   └── protobuf_parser.py   # Protobuf 解析器
│
└── CustomByteBlock_pb2.py  # Protobuf 生成的 Python 文件


⚠️ 常见问题 (Troubleshooting)

1. Qt 平台插件错误 (qt.qpa.plugin: Could not find the Qt platform plugin "windows")

解决方案: 程序已在 main.py 中设置了 Windows 专用环境变量。如果仍有问题，请确保您的 PyQt5 是通过 pip 正确安装的，且没有混用 Anaconda 的 Qt 库。

2. 视频花屏或解码失败

•   原因: 通常是因为缺少 SPS/PPS（参数集）。

•   解决: 确保发送端在视频流的开头发送了 SPS 和 PPS，或者检查 processor_thread.py 是否成功从 seq=0 的包中提取到了参数集。

3. 程序卡顿或 CPU 占用过高

•   解决: 尝试降低发送端的视频分辨率或帧率。在 h264_decoder.py 中，可以尝试调整 thread_count 参数。

📄 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件（如有）。

🙏 致谢

•   PyAV: 提供了强大的音视频处理能力。

•   PyQt5: 优秀的 GUI 框架。

•   Paho MQTT: 可靠的 MQTT 客户端库。
