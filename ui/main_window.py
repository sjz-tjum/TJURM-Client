# import sys
# import time
# import os
# import random

# # 清理可能冲突的环境变量
# os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
# os.environ.pop("QT_PLUGIN_PATH", None)

# # Windows 平台指定正确的 QPA
# if sys.platform == "win32":
#     os.environ["QT_QPA_PLATFORM"] = "windows"

# from PyQt5.QtWidgets import (
#     QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
#     QLabel, QPushButton, QTextEdit, QScrollArea, QInputDialog, QApplication
# )
# from PyQt5.QtGui import QPixmap, QImage, QFont
# from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QTimer

# from mqtt_client.client import MQTTReceiver
# from video.processor_thread import VideoProcessorThread
# from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT, DISPLAY_SCALE


# class MainWindow(QMainWindow):
#     """主窗口：MQTT 连接控制、视频显示、日志输出"""

#     # 自定义信号，用于从工作线程安全地追加日志
#     log_signal = pyqtSignal(str)

#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("MQTT H.264 视频接收器")
#         self.setGeometry(100, 100, 1200, 900)

#         # 状态变量
#         self.mqtt: MQTTReceiver | None = None
#         self.processor: VideoProcessorThread | None = None
#         self.connected = False
#         self.frame_count = 0
#         self.last_stat_time = time.time()
#         self.fps_counter = 0
#         self.client_id = ""
#         self._dialog_shown = False

#         # 先创建 UI
#         self._init_ui()

#         # 连接日志信号到 UI 更新槽
#         self.log_signal.connect(self._append_log)

#         # 先显示主窗口
#         self.show()
        
#         # 使用单次定时器延迟弹出对话框（确保主窗口完全渲染）
#         QTimer.singleShot(100, self._get_client_id)

#     # ==================== UI 初始化 ====================
#     def _init_ui(self):
#         """创建并布局所有控件"""
#         central = QWidget()
#         self.setCentralWidget(central)
#         main_layout = QVBoxLayout(central)
#         main_layout.setSpacing(10)
#         main_layout.setContentsMargins(12, 12, 12, 12)

#         # ---- 标题 ----
#         title = QLabel("📡 H.264 低带宽实时图传接收端")
#         title.setAlignment(Qt.AlignCenter)
#         title.setStyleSheet("""
#             QLabel {
#                 font-size: 20px;
#                 font-weight: bold;
#                 padding: 12px;
#                 background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
#                     stop:0 #1a237e, stop:1 #0d47a1);
#                 color: white;
#                 border-radius: 8px;
#             }
#         """)
#         main_layout.addWidget(title)

#         # ---- 控制按钮栏 ----
#         btn_layout = QHBoxLayout()
#         btn_layout.setSpacing(10)

#         self.btn_connect = QPushButton("🔌 连接 MQTT")
#         self.btn_connect.setMinimumHeight(40)
#         self.btn_connect.clicked.connect(self._on_connect_clicked)

#         self.btn_disconnect = QPushButton("🔴 断开连接")
#         self.btn_disconnect.setMinimumHeight(40)
#         self.btn_disconnect.setEnabled(False)
#         self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

#         self.btn_start = QPushButton("▶ 开始解码")
#         self.btn_start.setMinimumHeight(40)
#         self.btn_start.setEnabled(False)
#         self.btn_start.clicked.connect(self._on_start_clicked)

#         self.btn_stop = QPushButton("⏸ 停止解码")
#         self.btn_stop.setMinimumHeight(40)
#         self.btn_stop.setEnabled(False)
#         self.btn_stop.clicked.connect(self._on_stop_clicked)

#         self.btn_clear_log = QPushButton("🧹 清空日志")
#         self.btn_clear_log.setMinimumHeight(40)
#         self.btn_clear_log.clicked.connect(self._on_clear_log_clicked)

#         btn_layout.addWidget(self.btn_connect)
#         btn_layout.addWidget(self.btn_disconnect)
#         btn_layout.addWidget(self.btn_start)
#         btn_layout.addWidget(self.btn_stop)
#         btn_layout.addWidget(self.btn_clear_log)
#         btn_layout.addStretch()

#         main_layout.addLayout(btn_layout)

#         # ---- 状态栏（LED + 文本 + 统计）----
#         status_layout = QHBoxLayout()

#         self.led_label = QLabel("●")
#         self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
#         self.led_label.setFixedWidth(25)

#         self.status_label = QLabel("未连接")
#         self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")

#         self.stats_label = QLabel("包: 0 | 帧: 0 | FPS: 0.0")
#         self.stats_label.setStyleSheet("font-size: 13px; color: #1565c0;")

#         status_layout.addWidget(self.led_label)
#         status_layout.addWidget(self.status_label)
#         status_layout.addSpacing(20)
#         status_layout.addWidget(self.stats_label)
#         status_layout.addStretch()

#         main_layout.addLayout(status_layout)

#         # ---- 视频显示区域 ----
#         self.video_label = QLabel()
#         self.video_label.setAlignment(Qt.AlignCenter)
#         self.video_label.setMinimumHeight(500)
#         self.video_label.setStyleSheet("""
#             QLabel {
#                 background-color: #1a1a1a;
#                 border: 2px solid #424242;
#                 border-radius: 6px;
#                 color: #9e9e9e;
#                 font-size: 16px;
#             }
#         """)
#         self.video_label.setText("等待视频流...")

#         # 用 QScrollArea 包裹，方便缩放查看
#         scroll = QScrollArea()
#         scroll.setWidget(self.video_label)
#         scroll.setWidgetResizable(True)
#         scroll.setStyleSheet("QScrollArea { border: none; background: #1a1a1a; }")
#         main_layout.addWidget(scroll, stretch=2)

#         # ---- 日志区域 ----
#         self.log_text = QTextEdit()
#         self.log_text.setReadOnly(True)
#         self.log_text.setMaximumHeight(180)
#         self.log_text.setFont(QFont("Consolas", 10))
#         self.log_text.setStyleSheet("""
#             QTextEdit {
#                 background-color: #121212;
#                 color: #a5d6a5;
#                 border: 1px solid #333;
#                 border-radius: 4px;
#                 padding: 6px;
#             }
#         """)
#         main_layout.addWidget(self.log_text)

#         # 初始日志
#         self._append_log("🚀 程序启动，等待 MQTT 连接...")

#         # 应用全局样式（按钮等）
#         self._apply_button_styles()

#     def _apply_button_styles(self):
#         """为按钮统一设置样式"""
#         base_style = """
#             QPushButton {{
#                 font-size: 13px;
#                 font-weight: bold;
#                 padding: 8px 18px;
#                 border: none;
#                 border-radius: 6px;
#                 color: white;
#             }}
#             QPushButton:hover {{ opacity: 0.9; }}
#             QPushButton:pressed {{ opacity: 0.7; }}
#             QPushButton:disabled {{ background-color: #757575; }}
#         """
#         self.setStyleSheet(base_style)

#         self.btn_connect.setStyleSheet("QPushButton { background-color: #2e7d32; }")
#         self.btn_disconnect.setStyleSheet("QPushButton { background-color: #c62828; }")
#         self.btn_start.setStyleSheet("QPushButton { background-color: #1565c0; }")
#         self.btn_stop.setStyleSheet("QPushButton { background-color: #ef6c00; }")
#         self.btn_clear_log.setStyleSheet("QPushButton { background-color: #6a1b9a; }")

#     # ==================== 按钮槽函数 ====================
#     # def _on_connect_clicked(self):
#     #     """连接 MQTT 服务器"""
#     #     if not self.client_id:
#     #         self._append_log("⚠️ 客户端 ID 未设置，请重新输入")
#     #         self._get_client_id()
#     #         return

#     #     self._append_log("⏳ 正在连接 MQTT 服务器...")
#     #     self.btn_connect.setEnabled(False)

#     #     # 创建 MQTT 客户端（使用之前输入的 client_id）
#     #     broker = "192.168.12.1"  # 固定 IP 地址
#     #     port = 3333             # 指定的端口
#     #     self.mqtt = MQTTReceiver(
#     #         broker, 
#     #         port, 
#     #         self.client_id, 
#     #         local_ip="192.168.12.2"  # 强制使用有线网卡 IP
#     #     )


#     #     if self.mqtt.connect():
#     #         self.mqtt.subscribe("CustomByteBlock", qos=0)
#     #         self.mqtt.subscribe("/video/#", qos=0)

#     #         self.connected = True
#     #         self.led_label.setStyleSheet("color: #43a047; font-size: 18px;")
#     #         self.status_label.setText("已连接 - 等待视频数据")
#     #         self.btn_disconnect.setEnabled(True)
#     #         self.btn_start.setEnabled(True)

#     #         self._append_log(f"✅ MQTT 连接成功 (broker: {broker}:{port})")
#     #         self._append_log("📡 已订阅主题: /CustomByteBlock , /video/#")
#     #     else:
#     #         self._append_log("❌ MQTT 连接失败，请检查网络")
#     #         self.btn_connect.setEnabled(True)
#     def _on_connect_clicked(self):
#         """连接 MQTT 服务器"""
#         if not self.client_id:
#             self._append_log("⚠️ 客户端 ID 未设置，请重新输入")
#             self._get_client_id()
#             return

#         self._append_log("⏳ 正在连接 MQTT 服务器...")
#         self.btn_connect.setEnabled(False)

#         # 创建 MQTT 客户端（使用之前输入的 client_id）
#         broker = "192.168.12.1"  # 固定 IP 地址
#         port = 3333             # 指定的端口
#         self.mqtt = MQTTReceiver(
#             broker, 
#             port, 
#             self.client_id, 
#             local_ip="192.168.12.2"  # 强制使用有线网卡 IP
#         )
        
#         # 连接状态变化信号
#         self.mqtt.connection_status.connect(self._on_mqtt_status_changed)

#         if self.mqtt.connect():
#             # 注意：connect() 只是启动连接，不代表已连接成功
#             # 订阅操作会在 _on_connect 回调中自动执行
#             self._append_log(f"⏳ MQTT 连接请求已发送，等待确认...")
            
#             # 添加待订阅的主题（这些会在连接成功后自动订阅）
#             self.mqtt.subscribe("CustomByteBlock", qos=0)
#             self.mqtt.subscribe("/video/#", qos=0)
#         else:
#             self._append_log("❌ MQTT 连接请求失败，请检查网络")
#             self.btn_connect.setEnabled(True)


#     def _on_mqtt_status_changed(self, connected: bool, message: str):
#         """MQTT 连接状态变化回调"""
#         if connected:
#             self.connected = True
#             self.led_label.setStyleSheet("color: #43a047; font-size: 18px;")
#             self.status_label.setText("已连接 - 等待视频数据")
#             self.btn_disconnect.setEnabled(True)
#             self.btn_start.setEnabled(True)
            
#             self._append_log(f"✅ MQTT 连接成功")
            
#             # 打印已订阅的主题
#             # if self.mqtt:
#             #     topics = self.mqtt.get_subscribed_topics()
#             #     if topics:
#             #         self._append_log(f"📡 已订阅主题: {', '.join(topics)}")
#         else:
#             self.connected = False
#             self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
#             self.status_label.setText("连接失败")
#             self.btn_connect.setEnabled(True)
#             self.btn_disconnect.setEnabled(False)
#             self.btn_start.setEnabled(False)
            
#             self._append_log(f"❌ MQTT {message}")

#     def _on_disconnect_clicked(self):
#         """断开 MQTT 连接"""
#         self._on_stop_clicked()  # 先停止解码

#         if self.mqtt:
#             self.mqtt.disconnect()
#             self.mqtt = None

#         self.connected = False
#         self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
#         self.status_label.setText("已断开")
#         self.btn_connect.setEnabled(True)
#         self.btn_disconnect.setEnabled(False)
#         self.btn_start.setEnabled(False)

#         self._append_log("🔌 MQTT 连接已断开")

#     def _on_start_clicked(self):
#         """启动视频处理线程"""
#         if not self.connected or not self.mqtt:
#             self._append_log("⚠️ 请先连接 MQTT")
#             return

#         self.processor = VideoProcessorThread(self.mqtt)
#         self.processor.status_update.connect(self._append_log)
#         self.processor.frame_ready.connect(self._on_frame_received)
#         self.processor.stats_updated.connect(self._on_stats_updated)
#         self.processor.start()

#         self.btn_start.setEnabled(False)
#         self.btn_stop.setEnabled(True)
#         self.status_label.setText("解码中...")
#         self.video_label.setText("等待第一帧...")

#         self._append_log("▶️ 视频处理线程已启动")

#     def _on_stop_clicked(self):
#         """停止视频处理线程"""
#         if self.processor and self.processor.isRunning():
#             self.processor.stop()
#             self.processor = None

#         self.btn_start.setEnabled(True)
#         self.btn_stop.setEnabled(False)
#         self.status_label.setText("解码已停止")
#         self._append_log("⏸ 视频处理线程已停止")

#     def _on_clear_log_clicked(self):
#         """清空日志区域"""
#         self.log_text.clear()
#         self._append_log("📋 日志已清空")

#     # ==================== 回调与显示 ====================
#     def _on_frame_received(self, qimage: QImage):
#         """接收到解码后的帧，更新显示"""
#         # 缩放以适应显示区域，同时保持宽高比
#         label_size = self.video_label.size()
#         if label_size.width() > 50 and label_size.height() > 50:
#             pixmap = QPixmap.fromImage(qimage)
#             scaled = pixmap.scaled(
#                 label_size.width() - 20,
#                 label_size.height() - 20,
#                 Qt.KeepAspectRatio,
#                 Qt.SmoothTransformation
#             )
#             self.video_label.setPixmap(scaled)

#         self.frame_count += 1

#     # def _on_stats_updated(self, packets: int, frames: int, fps: float):
#     #     """更新状态栏统计"""
#     #     self.stats_label.setText(f"包: {packets} | 帧: {frames} | FPS: {fps:.1f}")
#     def _on_stats_updated(self, packets, frames, decode_fps, display_fps, lost):
#         self.stats_label.setText(
#             f"包: {packets} | 帧: {frames} | 解码FPS: {decode_fps:.1f} | 显示FPS: {display_fps:.1f} | 丢包: {lost}"
#     )

#     def _append_log(self, message: str):
#         """线程安全的日志追加（通过信号槽）"""
#         timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
#         self.log_text.append(f"[{timestamp}] {message}")

#         # 自动滚动到底部
#         scrollbar = self.log_text.verticalScrollBar()
#         if scrollbar:
#             scrollbar.setValue(scrollbar.maximum())

#     # ==================== 客户端 ID 输入对话框 ====================
#     def _get_client_id(self):
#         """弹出对话框让用户输入 MQTT 客户端 ID（跨平台兼容版本）"""
#         # 使用 None 作为 parent，避免 Windows 下的焦点问题
#         dialog = QInputDialog(None)
#         dialog.setWindowTitle("MQTT 客户端 ID")
#         dialog.setLabelText("请输入客户端 ID（留空则自动生成）:")
#         dialog.setTextValue("")
#         dialog.setInputMode(QInputDialog.TextInput)
#         dialog.resize(600, 400)  # 调整大小，更协调
        
#         # 设置窗口标志，确保对话框在最前
#         dialog.setWindowFlags(
#             Qt.Dialog | 
#             Qt.WindowStaysOnTopHint | 
#             Qt.WindowCloseButtonHint
#         )
        
#         # 放大字体和输入框
#         dialog.setStyleSheet("""
#             QInputDialog {
#                 min-width: 600px;
#                 min-height: 400px;
#             }
#             QInputDialog QLabel {
#                 font-size: 16px;
#                 font-weight: bold;
#                 padding: 15px;
#             }
#             QInputDialog QLineEdit {
#                 font-size: 16px;
#                 padding: 12px;
#                 min-height: 40px;
#                 margin: 10px 20px;
#                 border: 2px solid #aaa;
#                 border-radius: 6px;
#             }
#             QInputDialog QPushButton {
#                 font-size: 14px;
#                 padding: 10px 30px;
#                 min-width: 100px;
#                 min-height: 40px;
#             }
#         """)
        
    
#         self._center_on_screen(dialog)
        
#         dialog.activateWindow()
#         dialog.raise_()
        
#         if dialog.exec_():
#             text = dialog.textValue().strip()
#             if text:
#                 self.client_id = text
#             else:
#                 self.client_id = f"h264_recv_{int(time.time())}_{random.randint(100,999)}"
#         else:
#             # 用户取消，生成默认 ID
#             self.client_id = f"h264_recv_{int(time.time())}_{random.randint(100,999)}"

#         self._append_log(f"🆔 客户端 ID: {self.client_id}")

#     def _center_on_screen(self, dialog):
#         """将对话框居中到屏幕"""
#         screen = QApplication.primaryScreen()
#         if screen:
#             screen_geometry = screen.geometry()
#             dialog_geometry = dialog.frameGeometry()
#             dialog_geometry.moveCenter(screen_geometry.center())
#             dialog.move(dialog_geometry.topLeft())

#     # ==================== 窗口关闭处理 ====================
#     def closeEvent(self, event):
#         """窗口关闭时清理资源"""
#         self._append_log("🛑 正在关闭程序...")

#         if self.processor and self.processor.isRunning():
#             self.processor.stop()
#             self.processor.wait(1000)

#         if self.mqtt:
#             self.mqtt.disconnect()

#         event.accept()
#         self._append_log("👋 程序已退出")


# # ==================== 主程序入口 ====================
# def main():
#     app = QApplication(sys.argv)
#     window = MainWindow()
#     sys.exit(app.exec_())


# if __name__ == "__main__":
#     main()

import sys
import time
import os
import random

# 清理可能冲突的环境变量
os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
os.environ.pop("QT_PLUGIN_PATH", None)

# Windows 平台指定正确的 QPA
if sys.platform == "win32":
    os.environ["QT_QPA_PLATFORM"] = "windows"

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QScrollArea, QInputDialog, QApplication
)
from PyQt5.QtGui import QPixmap, QImage, QFont
from PyQt5.QtCore import Qt, QDateTime, pyqtSignal, QTimer

from mqtt_client.client import MQTTReceiver
from video.processor_thread import VideoProcessorThread
from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT, DISPLAY_SCALE


class MainWindow(QMainWindow):
    """主窗口：MQTT 连接控制、视频显示、日志输出"""

    # 自定义信号，用于从工作线程安全地追加日志
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("MQTT H.264 视频接收器")
        self.setGeometry(100, 100, 1200, 900)

        # 状态变量
        self.mqtt: MQTTReceiver | None = None
        self.processor: VideoProcessorThread | None = None
        self.connected = False
        self.frame_count = 0
        self.last_stat_time = time.time()
        self.fps_counter = 0
        self.client_id = ""
        self._dialog_shown = False

        # 先创建 UI
        self._init_ui()

        # 连接日志信号到 UI 更新槽
        self.log_signal.connect(self._append_log)

        # 先显示主窗口
        self.show()
        
        # 使用单次定时器延迟弹出对话框（确保主窗口完全渲染）
        QTimer.singleShot(100, self._get_client_id)

    # ==================== UI 初始化 ====================
    def _init_ui(self):
        """创建并布局所有控件"""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ---- 标题 ----
        title = QLabel("📡 H.264 低带宽实时图传接收端")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #0d47a1);
                color: white;
                border-radius: 8px;
            }
        """)
        main_layout.addWidget(title)

        # ---- 控制按钮栏 ----
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_connect = QPushButton("🔌 连接 MQTT")
        self.btn_connect.setMinimumHeight(40)
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.btn_disconnect = QPushButton("🔴 断开连接")
        self.btn_disconnect.setMinimumHeight(40)
        self.btn_disconnect.setEnabled(False)
        self.btn_disconnect.clicked.connect(self._on_disconnect_clicked)

        self.btn_start = QPushButton("▶ 开始解码")
        self.btn_start.setMinimumHeight(40)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start_clicked)

        self.btn_stop = QPushButton("⏸ 停止解码")
        self.btn_stop.setMinimumHeight(40)
        self.btn_stop.setEnabled(False)
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        self.btn_clear_log = QPushButton("🧹 清空日志")
        self.btn_clear_log.setMinimumHeight(40)
        self.btn_clear_log.clicked.connect(self._on_clear_log_clicked)

        # ========== 新增：修改客户端 ID 按钮 ==========
        self.btn_change_id = QPushButton("🆔 修改客户端 ID")
        self.btn_change_id.setMinimumHeight(40)
        self.btn_change_id.clicked.connect(self._on_change_client_id_clicked)
        # =============================================

        btn_layout.addWidget(self.btn_connect)
        btn_layout.addWidget(self.btn_disconnect)
        btn_layout.addWidget(self.btn_start)
        btn_layout.addWidget(self.btn_stop)
        btn_layout.addWidget(self.btn_clear_log)
        btn_layout.addWidget(self.btn_change_id)   # 添加新按钮
        btn_layout.addStretch()

        main_layout.addLayout(btn_layout)

        # ---- 状态栏（LED + 文本 + 统计）----
        status_layout = QHBoxLayout()

        self.led_label = QLabel("●")
        self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
        self.led_label.setFixedWidth(25)

        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("font-size: 13px; font-weight: bold;")

        self.stats_label = QLabel("包: 0 | 帧: 0 | FPS: 0.0")
        self.stats_label.setStyleSheet("font-size: 13px; color: #1565c0;")

        status_layout.addWidget(self.led_label)
        status_layout.addWidget(self.status_label)
        status_layout.addSpacing(20)
        status_layout.addWidget(self.stats_label)
        status_layout.addStretch()

        main_layout.addLayout(status_layout)

        # ---- 视频显示区域 ----
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumHeight(500)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #424242;
                border-radius: 6px;
                color: #9e9e9e;
                font-size: 16px;
            }
        """)
        self.video_label.setText("等待视频流...")

        # 用 QScrollArea 包裹，方便缩放查看
        scroll = QScrollArea()
        scroll.setWidget(self.video_label)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #1a1a1a; }")
        main_layout.addWidget(scroll, stretch=2)

        # ---- 日志区域 ----
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        self.log_text.setFont(QFont("Consolas", 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #121212;
                color: #a5d6a5;
                border: 1px solid #333;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        main_layout.addWidget(self.log_text)

        # 初始日志
        self._append_log("🚀 程序启动，等待 MQTT 连接...")

        # 应用全局样式（按钮等）
        self._apply_button_styles()

    def _apply_button_styles(self):
        """为按钮统一设置样式"""
        base_style = """
            QPushButton {{
                font-size: 13px;
                font-weight: bold;
                padding: 8px 18px;
                border: none;
                border-radius: 6px;
                color: white;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.7; }}
            QPushButton:disabled {{ background-color: #757575; }}
        """
        self.setStyleSheet(base_style)

        self.btn_connect.setStyleSheet("QPushButton { background-color: #2e7d32; }")
        self.btn_disconnect.setStyleSheet("QPushButton { background-color: #c62828; }")
        self.btn_start.setStyleSheet("QPushButton { background-color: #1565c0; }")
        self.btn_stop.setStyleSheet("QPushButton { background-color: #ef6c00; }")
        self.btn_clear_log.setStyleSheet("QPushButton { background-color: #6a1b9a; }")
        self.btn_change_id.setStyleSheet("QPushButton { background-color: #00838f; }")  # 新按钮颜色

    # ==================== 按钮槽函数 ====================
    def _on_connect_clicked(self):
        """连接 MQTT 服务器"""
        if not self.client_id:
            self._append_log("⚠️ 客户端 ID 未设置，请重新输入")
            self._get_client_id()
            return

        self._append_log("⏳ 正在连接 MQTT 服务器...")
        self.btn_connect.setEnabled(False)

        # 创建 MQTT 客户端（使用之前输入的 client_id）
        broker = "192.168.12.1"  # 固定 IP 地址
        port = 3333             # 指定的端口
        self.mqtt = MQTTReceiver(
            broker, 
            port, 
            self.client_id, 
            local_ip="192.168.12.2"  # 强制使用有线网卡 IP
        )
        
        # 连接状态变化信号
        self.mqtt.connection_status.connect(self._on_mqtt_status_changed)

        if self.mqtt.connect():
            self._append_log(f"⏳ MQTT 连接请求已发送，等待确认...")
            self.mqtt.subscribe("CustomByteBlock", qos=0)
            self.mqtt.subscribe("/video/#", qos=0)
        else:
            self._append_log("❌ MQTT 连接请求失败，请检查网络")
            self.btn_connect.setEnabled(True)

    def _on_mqtt_status_changed(self, connected: bool, message: str):
        """MQTT 连接状态变化回调"""
        if connected:
            self.connected = True
            self.led_label.setStyleSheet("color: #43a047; font-size: 18px;")
            self.status_label.setText("已连接 - 等待视频数据")
            self.btn_disconnect.setEnabled(True)
            self.btn_start.setEnabled(True)
            self._append_log(f"✅ MQTT 连接成功")
        else:
            self.connected = False
            self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
            self.status_label.setText("连接失败")
            self.btn_connect.setEnabled(True)
            self.btn_disconnect.setEnabled(False)
            self.btn_start.setEnabled(False)
            self._append_log(f"❌ MQTT {message}")

    def _on_disconnect_clicked(self):
        """断开 MQTT 连接"""
        self._on_stop_clicked()  # 先停止解码

        if self.mqtt:
            self.mqtt.disconnect()
            self.mqtt = None

        self.connected = False
        self.led_label.setStyleSheet("color: #e53935; font-size: 18px;")
        self.status_label.setText("已断开")
        self.btn_connect.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_start.setEnabled(False)

        self._append_log("🔌 MQTT 连接已断开")

    def _on_start_clicked(self):
        """启动视频处理线程"""
        if not self.connected or not self.mqtt:
            self._append_log("⚠️ 请先连接 MQTT")
            return

        self.processor = VideoProcessorThread(self.mqtt)
        self.processor.status_update.connect(self._append_log)
        self.processor.frame_ready.connect(self._on_frame_received)
        self.processor.stats_updated.connect(self._on_stats_updated)
        self.processor.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.status_label.setText("解码中...")
        self.video_label.setText("等待第一帧...")

        self._append_log("▶️ 视频处理线程已启动")

    def _on_stop_clicked(self):
        """停止视频处理线程"""
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.status_label.setText("解码已停止")
        self._append_log("⏸ 视频处理线程已停止")

    def _on_clear_log_clicked(self):
        """清空日志区域"""
        self.log_text.clear()
        self._append_log("📋 日志已清空")

    # ========== 新增：修改客户端 ID 槽函数 ==========
    def _on_change_client_id_clicked(self):
        """实时修改客户端 ID（需在未连接状态下）"""
        if self.connected:
            self._append_log("⚠️ 无法修改客户端 ID：当前已连接，请先断开")
            return

        # 调用与启动时相同的对话框逻辑，但直接赋值
        dialog = QInputDialog(None)
        dialog.setWindowTitle("修改 MQTT 客户端 ID")
        dialog.setLabelText("请输入新的客户端 ID（留空则自动生成）:")
        dialog.setTextValue(self.client_id)  # 显示当前 ID
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.resize(600, 400)
        dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint
        )
        dialog.setStyleSheet("""
            QInputDialog {
                min-width: 600px;
                min-height: 400px;
            }
            QInputDialog QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QInputDialog QLineEdit {
                font-size: 16px;
                padding: 12px;
                min-height: 40px;
                margin: 10px 20px;
                border: 2px solid #aaa;
                border-radius: 6px;
            }
            QInputDialog QPushButton {
                font-size: 14px;
                padding: 10px 30px;
                min-width: 100px;
                min-height: 40px;
            }
        """)
        self._center_on_screen(dialog)
        dialog.activateWindow()
        dialog.raise_()

        if dialog.exec_():
            text = dialog.textValue().strip()
            if text:
                self.client_id = text
            else:
                self.client_id = f"h264_recv_{int(time.time())}_{random.randint(100,999)}"
            self._append_log(f"🆔 客户端 ID 已更新为: {self.client_id}")
    # =============================================

    # ==================== 回调与显示 ====================
    def _on_frame_received(self, qimage: QImage):
        """接收到解码后的帧，更新显示"""
        label_size = self.video_label.size()
        if label_size.width() > 50 and label_size.height() > 50:
            pixmap = QPixmap.fromImage(qimage)
            scaled = pixmap.scaled(
                label_size.width() - 20,
                label_size.height() - 20,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
        self.frame_count += 1

    def _on_stats_updated(self, packets, frames, decode_fps, display_fps, lost):
        self.stats_label.setText(
            f"包: {packets} | 帧: {frames} | 解码FPS: {decode_fps:.1f} | 显示FPS: {display_fps:.1f} | 丢包: {lost}"
        )

    def _append_log(self, message: str):
        """线程安全的日志追加（通过信号槽）"""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss.zzz")
        self.log_text.append(f"[{timestamp}] {message}")
        scrollbar = self.log_text.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    # ==================== 客户端 ID 输入对话框（启动时） ====================
    def _get_client_id(self):
        """弹出对话框让用户输入 MQTT 客户端 ID（仅供启动时）"""
        dialog = QInputDialog(None)
        dialog.setWindowTitle("MQTT 客户端 ID")
        dialog.setLabelText("请输入客户端 ID（留空则自动生成）:")
        dialog.setTextValue("")
        dialog.setInputMode(QInputDialog.TextInput)
        dialog.resize(600, 400)
        dialog.setWindowFlags(
            Qt.Dialog | Qt.WindowStaysOnTopHint | Qt.WindowCloseButtonHint
        )
        dialog.setStyleSheet("""
            QInputDialog {
                min-width: 600px;
                min-height: 400px;
            }
            QInputDialog QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 15px;
            }
            QInputDialog QLineEdit {
                font-size: 16px;
                padding: 12px;
                min-height: 40px;
                margin: 10px 20px;
                border: 2px solid #aaa;
                border-radius: 6px;
            }
            QInputDialog QPushButton {
                font-size: 14px;
                padding: 10px 30px;
                min-width: 100px;
                min-height: 40px;
            }
        """)
        self._center_on_screen(dialog)
        dialog.activateWindow()
        dialog.raise_()

        if dialog.exec_():
            text = dialog.textValue().strip()
            if text:
                self.client_id = text
            else:
                self.client_id = f"h264_recv_{int(time.time())}_{random.randint(100,999)}"
        else:
            self.client_id = f"h264_recv_{int(time.time())}_{random.randint(100,999)}"
        self._append_log(f"🆔 客户端 ID: {self.client_id}")

    def _center_on_screen(self, dialog):
        """将对话框居中到屏幕"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.geometry()
            dialog_geometry = dialog.frameGeometry()
            dialog_geometry.moveCenter(screen_geometry.center())
            dialog.move(dialog_geometry.topLeft())

    # ==================== 窗口关闭处理 ====================
    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self._append_log("🛑 正在关闭程序...")
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait(1000)
        if self.mqtt:
            self.mqtt.disconnect()
        event.accept()
        self._append_log("👋 程序已退出")


# ==================== 主程序入口 ====================
def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()