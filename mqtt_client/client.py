import queue
import socket
import paho.mqtt.client as mqtt
from PyQt5.QtCore import QObject, pyqtSignal


class MQTTReceiver(QObject):
    """
    MQTT 接收器封装
    - 使用 paho.mqtt 库
    - 网络接收在独立线程中运行
    - 收到的消息放入 queue.Queue，供处理线程消费
    """
    
    # 信号：连接状态变化
    connection_status = pyqtSignal(bool, str)
    
    def __init__(self, broker_host: str, broker_port: int, client_id: str, local_ip: str = None):
        super().__init__()
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id
        self.local_ip = local_ip
        
        # 消息队列（线程安全）
        self.message_queue = queue.Queue(maxsize=500)
        
        # 待订阅的主题列表
        self.pending_subscriptions = []
        # 已订阅的主题集合
        self.subscribed_topics = set()
        
        # 创建 MQTT 客户端
        self.client = mqtt.Client(client_id=client_id, clean_session=True)
        
        # 如果指定了本地 IP，设置自定义 socket
        if self.local_ip:
            self.client.socket = self._create_bound_socket()
        
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        self.connected = False
        
    def _create_bound_socket(self):
        """创建绑定到指定本地 IP 的 socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind((self.local_ip, 0))
            print(f"[MQTT] Socket 已绑定到本地 IP: {self.local_ip}")
        except Exception as e:
            print(f"[MQTT] 绑定本地 IP {self.local_ip} 失败: {e}")
        
        return sock
        
    def _on_connect(self, client, userdata, flags, rc):
        """连接回调"""
        if rc == 0:
            self.connected = True
            print(f"[MQTT] 连接成功: {self.broker_host}:{self.broker_port}")
            
            # 连接成功后，自动订阅所有待订阅的主题
            for topic, qos in self.pending_subscriptions:
                self._do_subscribe(topic, qos)
            self.pending_subscriptions.clear()
            
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
        """消息接收回调"""
        try:
            self.message_queue.put_nowait(msg)
        except queue.Full:
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
    
    def _do_subscribe(self, topic: str, qos: int = 0):
        """实际执行订阅操作"""
        try:
            result = self.client.subscribe(topic, qos=qos)
            # result 是一个元组 (result_code, mid)
            # result_code == 0 表示成功
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscribed_topics.add(topic)
                print(f"[MQTT] 已订阅: {topic} (qos={qos})")
                return True
        except Exception as e:
            print(f"[MQTT] 订阅失败 {topic}: {e}")
            return False
    
    def connect(self) -> bool:
        """连接到 MQTT 服务器"""
        try:
            print(f"[MQTT] 正在连接 {self.broker_host}:{self.broker_port}...")
            if self.local_ip:
                print(f"[MQTT] 指定本地绑定 IP: {self.local_ip}")
            
            self.client.connect(self.broker_host, self.broker_port, keepalive=60)
            self.client.loop_start()
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
            self.subscribed_topics.clear()
            print("[MQTT] 已断开连接")
        except Exception as e:
            print(f"[MQTT] 断开连接异常: {e}")
    
    def subscribe(self, topic: str, qos: int = 0):
        """
        订阅主题
        - 如果已连接，立即订阅
        - 如果未连接，加入待订阅列表，等连接成功后自动订阅
        """
        # 清理主题末尾可能存在的空格
        topic = topic.strip()
        
        if self.connected:
            return self._do_subscribe(topic, qos)
        else:
            print(f"[MQTT] 连接未完成，将主题加入待订阅列表: {topic}")
            self.pending_subscriptions.append((topic, qos))
            return True
    
    def unsubscribe(self, topic: str):
        """取消订阅"""
        try:
            self.client.unsubscribe(topic)
            self.subscribed_topics.discard(topic)
            print(f"[MQTT] 已取消订阅: {topic}")
        except Exception as e:
            print(f"[MQTT] 取消订阅失败: {e}")
    
    def get_subscribed_topics(self):
        """获取所有已订阅的主题"""
        return list(self.subscribed_topics)
    
    def is_connected(self) -> bool:
        """返回当前连接状态"""
        return self.connected