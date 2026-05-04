# 包格式
PACKET_SIZE = 300               # 单包总字节数
HEADER_SIZE = 10                # 头部长度
PAYLOAD_SIZE = PACKET_SIZE - HEADER_SIZE   # 284 字节

# 头部字段 (大端序)
HEADER_FIELDS = ('frame_id', 'packet_index', 'total_packets', 'data_length')

# 视频参数
VIDEO_WIDTH = 300
VIDEO_HEIGHT = 300
DISPLAY_SCALE = 0.5            # 显示缩放倍数