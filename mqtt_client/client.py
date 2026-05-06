import queue
import paho.mqtt.client as mqtt
from typing import Optional
import os
import platform

# ==== Windows 专用配置 - 与 WSL 相反 ====
def setup_windows_environment():
    """Windows 环境配置"""
    system = platform.system()
    
    if system == "Windows":
        print("[INFO] Windows 环境")
        
        # 1. 清除所有 Linux/WSL 的 Qt 设置
        os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)
        os.environ.pop("QT_PLUGIN_PATH", None)
        
        # 2. 重要：Windows 用 "windows"，不是 "xcb"！
        os.environ["QT_QPA_PLATFORM"] = "windows"
        
        # 3. 设置 Windows 插件路径
        try:
            import PyQt5
            pyqt_path = os.path.dirname(PyQt5.__file__)
            plugin_path = os.path.join(pyqt_path, "Qt5", "plugins")
            
            if os.path.exists(plugin_path):
                # Windows 需要设置插件路径
                os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = plugin_path
                print(f"[INFO] 设置 Qt 插件路径: {plugin_path}")
        except ImportError:
            print("[ERROR] PyQt5 未安装")
            sys.exit(1)
        
        return True
    return False

# 设置环境
setup_windows_environment()
from PyQt5.QtCore import QObject, pyqtSignal


class MQTTReceiver(QObject):
    """
    MQTT 接收器封装
    - 使用 paho.mqtt 库
    - 网络接收在独立线程中运行
    - 收到的消息放入 queue.Queue，供处理线程消费
    """
    
    # 信号：连接状态变化（可选，用于 UI 更新）
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, broker_host: str, broker_port: int, client_id: str, local_ip: Optional[str] = None):
        super().__init__()
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.local_ip = local_ip
        # 消息队列（线程安全）
        self.message_queue = queue.Queue(maxsize=500)
        
        # 创建 MQTT 客户端
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        
        self.connected = False
        
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] 连接成功: {self.broker_host}:{self.broker_port}")
            self.connection_status.emit(True, "连接成功")
        else:
            self.connected = False
            error_msg = self._get_rc_message(rc)
            print(f"[MQTT] 连接失败: {error_msg}")
            self.connection_status.emit(False, f"连接失败: {error_msg}")
    
    def _on_disconnect(self, client, userdata, rc):
        """断开连接回调"""
        self.connected = False
        print(f"[MQTT] 连接断开 (rc={rc})")
        self.connection_status.emit(False, "连接已断开")
    
    def _on_message(self, client, userdata, msg):
        """
        消息接收回调（在 paho 网络线程中执行）
        仅做最轻量的入队操作，避免阻塞网络线程
        """
        try:
            # 非阻塞入队，队列满时丢弃旧消息
            self.message_queue.put_nowait(msg)
        except queue.Full:
            # 队列满，丢弃最旧的一条消息，再尝试放入新消息
            try:
                self.message_queue.get_nowait()
                self.message_queue.put_nowait(msg)
            except queue.Empty:
                pass
            print("[MQTT] 警告: 消息队列已满，丢弃旧消息")
    
    def _get_rc_message(self, rc: int) -> str:
        """获取连接返回码对应的描述"""
        rc_messages = {
            0: "连接成功",
            1: "协议版本错误",
            2: "客户端标识符无效",
            3: "服务器不可用",
            4: "用户名或密码错误",
            5: "未授权"
        }
        return rc_messages.get(rc, f"未知错误 ({rc})")
    
    def connect(self) -> bool:
        """连接到 MQTT 服务器"""
        try:
            print(f"[MQTT] 正在连接 {self.broker_host}:{self.broker_port}...")
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()  # 启动网络线程
            return True
        except Exception as e:
            print(f"[MQTT] 连接异常: {e}")
            self.connection_status.emit(False, f"连接异常: {e}")
            return False
    
    def disconnect(self):
        """断开 MQTT 连接"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
            print("[MQTT] 已断开连接")
        except Exception as e:
            print(f"[MQTT] 断开连接异常: {e}")
    
    def subscribe(self, topic: str, qos: int = 0):
        """订阅主题"""
        if not self.connected:
            print(f"[MQTT] 未连接，无法订阅: {topic}")
            return False
        
        try:
            self.client.subscribe(topic, qos=qos)
            print(f"[MQTT] 已订阅: {topic} (qos={qos})")
            return True
        except Exception as e:
            print(f"[MQTT] 订阅失败 {topic}: {e}")
            return False
    
    def unsubscribe(self, topic: str):
        """取消订阅"""
        try:
            self.client.unsubscribe(topic)
            print(f"[MQTT] 已取消订阅: {topic}")
        except Exception as e:
            print(f"[MQTT] 取消订阅失败: {e}")
    
    def is_connected(self) -> bool:
        """返回当前连接状态"""
        return self.connected