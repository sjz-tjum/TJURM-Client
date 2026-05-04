import struct
import threading
import time
from collections import defaultdict
from utils.constants import PACKET_SIZE, HEADER_SIZE, HEADER_FIELDS

class PacketReassembler:
    def __init__(self, stale_timeout=3.0):
        self._frames = defaultdict(dict)     # frame_id -> {idx: bytes}
        self._timestamps = {}                # frame_id -> first_packet_time
        self._lock = threading.Lock()
        self.stale_timeout = stale_timeout

    def add_packet(self, raw_packet: bytes):
        """返回 (full_frame_bytes, frame_id, total_packets) 或 (None,None,None)"""
        if len(raw_packet) != PACKET_SIZE:
            return None, None, None

        header = raw_packet[:HEADER_SIZE]
        frame_id, pkt_idx, total, data_len = struct.unpack('!IIII', header)
        payload = raw_packet[HEADER_SIZE:]

        with self._lock:
            frame_key = frame_id
            self._frames[frame_key][pkt_idx] = payload
            if frame_key not in self._timestamps:
                self._timestamps[frame_key] = time.time()

            if len(self._frames[frame_key]) == total:
                # 拼接
                full = bytearray()
                for i in range(total):
                    full.extend(self._frames[frame_key].get(i, b''))
                # 截取实际长度
                if len(full) > data_len:
                    full = full[:data_len]
                # 清理
                del self._frames[frame_key]
                del self._timestamps[frame_key]
                return bytes(full), frame_id, total
            else:
                return None, None, None

    def cleanup_stale(self):
        """清理超时未完成的帧，由外部定时调用"""
        now = time.time()
        with self._lock:
            stale = [fid for fid, ts in self._timestamps.items() if now - ts > self.stale_timeout]
            for fid in stale:
                del self._frames[fid]
                del self._timestamps[fid]