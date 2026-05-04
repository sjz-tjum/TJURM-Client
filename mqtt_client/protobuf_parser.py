from protos import CustomByteBlock_pb2

def parse_video_packet(mqtt_payload: bytes) -> bytes:
    """
    输入: MQTT 原始载荷 (Protobuf 序列化数据)
    输出: 真正的视频包数据 (300 字节)
    """
    block = CustomByteBlock_pb2.CustomByteBlock()
    block.ParseFromString(mqtt_payload)
    return block.data