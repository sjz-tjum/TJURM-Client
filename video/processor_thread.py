# 可用第二版
# from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QTimer
# import struct
# import queue
# import time
# import cv2
# from PyQt5.QtGui import QImage

# from mqtt_client.protobuf_parser import parse_video_packet
# from video.h264_decoder import H264Decoder
# from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT

# VIDEO_DATA_FMT = '<Hq290s'   # uint16 seq_id, int64 timestamp, uint8 data[290]
# VIDEO_DATA_SIZE = 2 + 8 + 290  # 300 字节

# class VideoProcessorThread(QThread):
#     status_update = pyqtSignal(str)
#     frame_ready = pyqtSignal(QImage)
#     stats_updated = pyqtSignal(int, int, float, float, int)   # 包, 帧, 解码fps, 显示fps, 丢包

#     def __init__(self, mqtt_receiver):
#         super().__init__()
#         self.mqtt = mqtt_receiver
#         self.running = True

#         self.decoder = H264Decoder(VIDEO_WIDTH, VIDEO_HEIGHT)
#         self.stream_buffer = bytearray()
#         self.last_seq = None
#         self.lost_packets = 0
#         self.extradata_extracted = False   # 标记是否已从包0提取 extradata

#         self.frame_buffer = []
#         self.buffer_lock = QMutex()

#         # 统计变量
#         self.received_packets = 0
#         self.decoded_frames = 0
#         self.last_stat_time = time.time()
#         self.fps_counter = 0
#         self.current_fps = 0.0
#         self.display_fps_counter = 0
#         self.last_display_stat_time = time.time()

#         self.render_timer = QTimer()
#         self.render_timer.timeout.connect(self._on_render)
#         self.render_timer.start(1)  # 尽快刷新

#     def run(self):
#         try:
#             import psutil
#             p = psutil.Process()
#             p.nice(psutil.HIGH_PRIORITY_CLASS)
#         except Exception as e:
#             self.status_update.emit(f"优先级设置失败: {e}")
#         self.status_update.emit("视频处理线程启动")
#         while self.running:
#             # 如果消息队列堆积太多，丢弃旧消息
#             while self.mqtt.message_queue.qsize() > 5:
#                 try:
#                     self.mqtt.message_queue.get_nowait()
#                 except queue.Empty:
#                     break
#             try:
#                 mqtt_msg = self.mqtt.message_queue.get(timeout=0.01)
#                 qsize = self.mqtt.message_queue.qsize()
#                 if qsize > 10:
#                     self.status_update.emit(f"队列积压: {qsize}")
#                 self._process_message(mqtt_msg)
#             except queue.Empty:
#                 pass
#             self._update_stats()

#     @staticmethod
#     def _find_nal_start_code(buf, start=0):
#         for i in range(start, len(buf) - 3):
#             if buf[i:i+4] == b'\x00\x00\x00\x01' or buf[i:i+3] == b'\x00\x00\x01':
#                 return i
#         return -1

#     @staticmethod
#     def _extract_and_convert_avcc(h264_data: bytes):
#         """从 Annex‑B 字节中提取 SPS 和 PPS，返回 avcC 格式的 bytes，失败返回 None"""
#         sps = pps = None
#         i = 0
#         while i < len(h264_data) - 4:
#             start = VideoProcessorThread._find_nal_start_code(h264_data, i)
#             if start == -1:
#                 break
#             # 确定起始码长度
#             if h264_data[start:start+4] == b'\x00\x00\x00\x01':
#                 nal_len = 4
#             elif h264_data[start:start+3] == b'\x00\x00\x01':
#                 nal_len = 3
#             else:
#                 i = start + 1
#                 continue
#             nal_type_pos = start + nal_len
#             if nal_type_pos >= len(h264_data):
#                 break
#             nal_type = h264_data[nal_type_pos] & 0x1F

#             # 找下一个起始码确定当前 NAL 结束位置
#             next_start = VideoProcessorThread._find_nal_start_code(h264_data, start + 1)
#             nal_end = next_start if next_start != -1 else len(h264_data)

#             if nal_type == 7:    # SPS
#                 sps = h264_data[start:nal_end]
#             elif nal_type == 8:  # PPS
#                 pps = h264_data[start:nal_end]

#             if sps and pps:
#                 break
#             i = nal_end

#         if not sps or not pps:
#             return None

#         # 去掉起始码
#         def strip(nal):
#             if nal[:4] == b'\x00\x00\x00\x01':
#                 return nal[4:]
#             return nal[3:] if nal[:3] == b'\x00\x00\x01' else nal

#         sps_body = strip(sps)
#         pps_body = strip(pps)

#         # 构建 avcC
#         avcc = bytearray()
#         avcc.append(0x01)                    # configurationVersion
#         avcc.append(sps_body[1])             # profile_idc
#         avcc.append(sps_body[2])             # profile_compatibility
#         avcc.append(sps_body[3])             # level_idc
#         avcc.append(0xFF)                    # lengthSizeMinusOne = 3 (1111)
#         avcc.append(0xE1)                    # 1 SPS
#         avcc.append((len(sps_body) >> 8) & 0xFF)
#         avcc.append(len(sps_body) & 0xFF)
#         avcc.extend(sps_body)
#         avcc.append(0x01)                    # 1 PPS
#         avcc.append((len(pps_body) >> 8) & 0xFF)
#         avcc.append(len(pps_body) & 0xFF)
#         avcc.extend(pps_body)
#         return bytes(avcc)

#     def _process_message(self, mqtt_msg):
#         try:
#             raw_data = parse_video_packet(mqtt_msg.payload)
#             if len(raw_data) != VIDEO_DATA_SIZE:
#                 self.status_update.emit(f"警告：包长度异常 ({len(raw_data)})，跳过")
#                 return

#             seq_id, timestamp, h264_chunk = struct.unpack(VIDEO_DATA_FMT, raw_data)
#             self.received_packets += 1

#             # 丢包检测（仅记录，不做破坏性操作）
#             if self.last_seq is not None:
#                 expected = (self.last_seq + 1) & 0xFFFF
#                 if seq_id != expected:
#                     self.lost_packets += 1
#                     self.status_update.emit(f"丢包检测: 期望 {expected}, 收到 {seq_id}")
#             self.last_seq = seq_id

#             # ---------- 关键：收到第一个包(seq=0)时提取 extradata ----------
#             if seq_id == 0 and not self.extradata_extracted:
#                 avcc = self._extract_and_convert_avcc(h264_chunk)
#                 if avcc:
#                     self.decoder.set_extradata(avcc)
#                     self.extradata_extracted = True
#                     self.status_update.emit("已从包0提取并缓存 SPS/PPS")
#                 else:
#                     self.status_update.emit("包0未找到 SPS/PPS，解码仍依赖流内参数集")
#             # -----------------------------------------------------------------

#             self.stream_buffer.extend(h264_chunk)

#             # 缓冲区堆积检测：超过 200KB 时软截断到最新 IDR
#             if len(self.stream_buffer) > 200 * 1024:
#                 idr_pos = -1
#                 # 从后往前寻找最后一个 IDR 起始码
#                 for i in range(len(self.stream_buffer) - 5, 0, -1):
#                     if self.stream_buffer[i:i+4] == b'\x00\x00\x00\x01' or self.stream_buffer[i:i+3] == b'\x00\x00\x01':
#                         nal_start = i + (4 if self.stream_buffer[i:i+4] == b'\x00\x00\x00\x01' else 3)
#                         if nal_start < len(self.stream_buffer) and (self.stream_buffer[nal_start] & 0x1F) == 5:
#                             idr_pos = i
#                             break
#                 if idr_pos >= 0:
#                     del self.stream_buffer[:idr_pos]
#                     self.status_update.emit(f"缓冲区截断到最新 IDR (丢弃 {idr_pos} 字节)")
#                 else:
#                     self.stream_buffer.clear()
#                     self.status_update.emit("缓冲区过大且无 IDR，清空")

#             # 解码
#             images = self.decoder.parse_and_decode(self.stream_buffer)

#             for img in images:
#                 self.decoded_frames += 1
#                 self.fps_counter += 1

#                 h, w, ch = img.shape
#                 bytes_per_line = ch * w
#                 rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#                 qimage = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

#                 self.buffer_lock.lock()
#                 self.frame_buffer.append(qimage)
#                 if len(self.frame_buffer) > 1:
#                     self.frame_buffer.pop(0)
#                 self.buffer_lock.unlock()

#         except Exception as e:
#             self.status_update.emit(f"处理消息异常: {e}")

#     def _on_render(self):
#         self.buffer_lock.lock()
#         if self.frame_buffer:
#             qimage = self.frame_buffer[-1]
#             self.buffer_lock.unlock()
#             self.frame_ready.emit(qimage)
#             self.display_fps_counter += 1
#         else:
#             self.buffer_lock.unlock()

#     def _update_stats(self):
#         now = time.time()
#         if now - self.last_stat_time >= 1.0:
#             self.current_fps = self.fps_counter / (now - self.last_stat_time)

#             elapsed_display = now - self.last_display_stat_time
#             display_fps = self.display_fps_counter / elapsed_display if elapsed_display > 0 else 0.0

#             self.stats_updated.emit(
#                 self.received_packets,
#                 self.decoded_frames,
#                 self.current_fps,
#                 display_fps,
#                 self.lost_packets
#             )
#             self.display_fps_counter = 0
#             self.last_display_stat_time = now
#             self.fps_counter = 0
#             self.last_stat_time = now

#     def stop(self):
#         self.running = False
#         self.render_timer.stop()
#         self.wait(2000)
#         self.decoder.close()


# processor_thread.py（完整版）
from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QTimer
import struct
import queue
import time
import cv2
from PyQt5.QtGui import QImage

from mqtt_client.protobuf_parser import parse_video_packet
from video.h264_decoder import H264Decoder
from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT

VIDEO_DATA_FMT = '<Hq290s'   # seq_id(2) + timestamp(8) + data(290)
VIDEO_DATA_SIZE = 2 + 8 + 290

class VideoProcessorThread(QThread):
    status_update = pyqtSignal(str)
    frame_ready = pyqtSignal(QImage)
    stats_updated = pyqtSignal(int, int, float, float, int)   # 包, 帧, 解码fps, 显示fps, 丢包

    def __init__(self, mqtt_receiver):
        super().__init__()
        self.mqtt = mqtt_receiver
        self.running = True

        self.decoder = H264Decoder(VIDEO_WIDTH, VIDEO_HEIGHT)
        self.stream_buffer = bytearray()
        self.last_seq = None
        self.lost_packets = 0
        self.extradata_extracted = False          # 是否已成功提取 extradata

        self.frame_buffer = []
        self.buffer_lock = QMutex()

        # 统计
        self.received_packets = 0
        self.decoded_frames = 0
        self.last_stat_time = time.time()
        self.fps_counter = 0
        self.current_fps = 0.0
        self.display_fps_counter = 0
        self.last_display_stat_time = time.time()

        self.render_timer = QTimer()
        self.render_timer.timeout.connect(self._on_render)
        self.render_timer.start(1)                # 高速刷新

    def run(self):
        try:
            import psutil
            p = psutil.Process()
            p.nice(psutil.HIGH_PRIORITY_CLASS)
        except Exception as e:
            self.status_update.emit(f"优先级设置失败: {e}")
        self.status_update.emit("视频处理线程启动")
        while self.running:
            # 队列积压时丢弃旧包
            while self.mqtt.message_queue.qsize() > 5:
                try:
                    self.mqtt.message_queue.get_nowait()
                except queue.Empty:
                    break
            try:
                mqtt_msg = self.mqtt.message_queue.get(timeout=0.01)
                qsize = self.mqtt.message_queue.qsize()
                if qsize > 10:
                    self.status_update.emit(f"队列积压: {qsize}")
                self._process_message(mqtt_msg)
            except queue.Empty:
                pass
            self._update_stats()

    # ---------- 辅助：从 Annex-B 中提取 SPS/PPS 并生成 avcC ----------
    @staticmethod
    def _find_nal_start_code(buf, start=0):
        for i in range(start, len(buf) - 3):
            if buf[i:i+4] == b'\x00\x00\x00\x01' or buf[i:i+3] == b'\x00\x00\x01':
                return i
        return -1

    @staticmethod
    def _extract_and_convert_avcc(h264_data: bytes):
        """返回 avcC bytes 或 None"""
        sps = pps = None
        i = 0
        while i < len(h264_data) - 4:
            start = VideoProcessorThread._find_nal_start_code(h264_data, i)
            if start == -1:
                break
            if h264_data[start:start+4] == b'\x00\x00\x00\x01':
                nal_len = 4
            elif h264_data[start:start+3] == b'\x00\x00\x01':
                nal_len = 3
            else:
                i = start + 1
                continue
            nal_type_pos = start + nal_len
            if nal_type_pos >= len(h264_data):
                break
            nal_type = h264_data[nal_type_pos] & 0x1F
            next_start = VideoProcessorThread._find_nal_start_code(h264_data, start + 1)
            nal_end = next_start if next_start != -1 else len(h264_data)

            if nal_type == 7:
                sps = h264_data[start:nal_end]
            elif nal_type == 8:
                pps = h264_data[start:nal_end]

            if sps and pps:
                break
            i = nal_end

        if not sps or not pps:
            return None

        def strip(nal):
            if nal[:4] == b'\x00\x00\x00\x01':
                return nal[4:]
            return nal[3:] if nal[:3] == b'\x00\x00\x01' else nal

        sps_body = strip(sps)
        pps_body = strip(pps)

        avcc = bytearray()
        avcc.append(0x01)                     # configurationVersion
        avcc.append(sps_body[1])              # profile_idc
        avcc.append(sps_body[2])              # profile_compatibility
        avcc.append(sps_body[3])              # level_idc
        avcc.append(0xFF)                     # lengthSizeMinusOne = 3
        avcc.append(0xE1)                     # 1 SPS
        avcc.append((len(sps_body) >> 8) & 0xFF)
        avcc.append(len(sps_body) & 0xFF)
        avcc.extend(sps_body)
        avcc.append(0x01)                     # 1 PPS
        avcc.append((len(pps_body) >> 8) & 0xFF)
        avcc.append(len(pps_body) & 0xFF)
        avcc.extend(pps_body)
        return bytes(avcc)

    # ---------- 消息处理 ----------
    def _process_message(self, mqtt_msg):
        try:
            raw_data = parse_video_packet(mqtt_msg.payload)
            if len(raw_data) != VIDEO_DATA_SIZE:
                self.status_update.emit(f"包长度异常 ({len(raw_data)})，跳过")
                return

            seq_id, timestamp, h264_chunk = struct.unpack(VIDEO_DATA_FMT, raw_data)
            self.received_packets += 1

            # 丢包检测（只记录，不做清空 / 重置）
            if self.last_seq is not None:
                expected = (self.last_seq + 1) & 0xFFFF
                if seq_id != expected:
                    self.lost_packets += 1
                    self.status_update.emit(f"丢包: 期望 {expected}, 收到 {seq_id}")
            self.last_seq = seq_id

            # ===== 提取 extradata：只要尚未成功，每个包都尝试（不限于包0）=====
            if not self.extradata_extracted:
                avcc = self._extract_and_convert_avcc(h264_chunk)
                if avcc:
                    self.decoder.set_extradata(avcc)
                    self.extradata_extracted = True
                    self.status_update.emit(f"已从 seq={seq_id} 提取并缓存 SPS/PPS")
            # ================================================================

            self.stream_buffer.extend(h264_chunk)

            # 缓冲区软上限：保留最后一个 IDR
            if len(self.stream_buffer) > 10 * 1024:
                idr_pos = -1
                for i in range(len(self.stream_buffer) - 5, 0, -1):
                    if self.stream_buffer[i:i+4] == b'\x00\x00\x00\x01' or self.stream_buffer[i:i+3] == b'\x00\x00\x01':
                        nal_start = i + (4 if self.stream_buffer[i:i+4] == b'\x00\x00\x00\x01' else 3)
                        if nal_start < len(self.stream_buffer) and (self.stream_buffer[nal_start] & 0x1F) == 5:
                            idr_pos = i
                            break
                if idr_pos >= 0:
                    del self.stream_buffer[:idr_pos]
                    self.status_update.emit(f"缓冲区截断至最新 IDR (丢弃 {idr_pos} 字节)")
                else:
                    self.stream_buffer.clear()
                    self.status_update.emit("缓冲区过大且无 IDR，清空")

            # 解码
            images = self.decoder.parse_and_decode(self.stream_buffer)

            for img in images:
                self.decoded_frames += 1
                self.fps_counter += 1

                h, w, ch = img.shape
                bytes_per_line = ch * w
                rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                qimage = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

                self.buffer_lock.lock()
                self.frame_buffer.append(qimage)
                if len(self.frame_buffer) > 1:
                    self.frame_buffer.pop(0)
                self.buffer_lock.unlock()

        except Exception as e:
            self.status_update.emit(f"处理消息异常: {e}")

    # ---------- 显示 ----------
    def _on_render(self):
        self.buffer_lock.lock()
        if self.frame_buffer:
            qimage = self.frame_buffer[-1]
            self.buffer_lock.unlock()
            self.frame_ready.emit(qimage)
            self.display_fps_counter += 1
        else:
            self.buffer_lock.unlock()

    # ---------- 统计 ----------
    def _update_stats(self):
        now = time.time()
        if now - self.last_stat_time >= 1.0:
            self.current_fps = self.fps_counter / (now - self.last_stat_time)

            elapsed_display = now - self.last_display_stat_time
            display_fps = self.display_fps_counter / elapsed_display if elapsed_display > 0 else 0.0

            self.stats_updated.emit(
                self.received_packets,
                self.decoded_frames,
                self.current_fps,
                display_fps,
                self.lost_packets
            )
            self.display_fps_counter = 0
            self.last_display_stat_time = now
            self.fps_counter = 0
            self.last_stat_time = now

    def stop(self):
        self.running = False
        self.render_timer.stop()
        self.wait(2000)
        self.decoder.close()










# from PyQt5.QtCore import QThread, pyqtSignal, QMutex, QTimer
# import struct
# import queue
# import time
# import cv2
# from PyQt5.QtGui import QImage

# from mqtt_client.protobuf_parser import parse_video_packet
# # from video.packet_reassembler import PacketReassembler
# from video.h264_decoder import H264Decoder
# from utils.constants import VIDEO_WIDTH, VIDEO_HEIGHT

# # VideoStreamData 结构体解析格式
# VIDEO_DATA_FMT = '<Hq290s'   # uint16 seq_id, int64 timestamp, uint8 data[290]
# VIDEO_DATA_SIZE = 2 + 8 + 290  # 300 字节

# class VideoProcessorThread(QThread):
#     status_update = pyqtSignal(str)
#     frame_ready = pyqtSignal(QImage)
#     # stats_updated = pyqtSignal(int, int, float, int)   # 增加丢包数
#     stats_updated = pyqtSignal(int, int, float, float, int)   # 包, 帧, 解码fps, 显示fps, 丢包
#     def __init__(self, mqtt_receiver):
#         super().__init__()
#         self.mqtt = mqtt_receiver
#         self.running = True

#         self.display_fps_counter = 0          # 新增：显示帧计数
#         self.last_display_stat_time = time.time()   # 新增：显示统计起始时间

#         self.decoder = H264Decoder(VIDEO_WIDTH, VIDEO_HEIGHT)
#         self.stream_buffer = bytearray()   
#         self.last_seq = None               
#         self.lost_packets = 0             

#         self.frame_buffer = []
#         self.buffer_lock = QMutex()

#         # 统计变量
#         self.received_packets = 0
#         self.decoded_frames = 0
#         self.last_stat_time = time.time()
#         self.fps_counter = 0
#         self.current_fps = 0.0
#         self.count = 0
#         self.render_timer = QTimer()
#         self.render_timer.timeout.connect(self._on_render)
#         self.render_timer.start(1)  

#     def run(self):
#         try:
#             import psutil
#             p = psutil.Process()
#             p.nice(psutil.HIGH_PRIORITY_CLASS)
#         except Exception as e:
#             self.status_update.emit(f"优先级设置失败: {e}")
#         self.status_update.emit("视频处理线程启动")
#         while self.running:
#             while self.mqtt.message_queue.qsize() > 5:
#                 try:
#                     _ = self.mqtt.message_queue.get_nowait()
#                 except queue.Empty:
#                     break
#             try:
#                 mqtt_msg = self.mqtt.message_queue.get(timeout=0.01)
#                 qsize = self.mqtt.message_queue.qsize()
#                 if qsize > 10:
#                     self.status_update.emit(f"队列积压: {qsize}")
#                 self._process_message(mqtt_msg)
#             except queue.Empty:
#                 pass
#             self._update_stats()

#     def _process_message(self, mqtt_msg):
#         try:
#             raw_data = parse_video_packet(mqtt_msg.payload)

#             # 可选：保留调试但不要频繁写文件，或者仅写少量


#             if len(raw_data) != VIDEO_DATA_SIZE:
#                 self.status_update.emit(f"警告：包长度异常 ({len(raw_data)})，跳过")
#                 return

#             seq_id, timestamp, h264_chunk = struct.unpack(VIDEO_DATA_FMT, raw_data)
#             self.received_packets += 1
#             # with open('raw_data2.txt', 'a', encoding='utf-8') as f:
#             #     # 写入 seq_id 和完整 raw_data 的十六进制（每字节空格分隔）
#             #     hex_str = ' '.join(f'{b:02x}' for b in raw_data)
#             #     f.write(f"{seq_id}: {hex_str}\n") 
#             # with open('pure_h264.h264', 'ab') as f:
#             #     f.write(h264_chunk) 
#             # 丢包检测（seq_id 不连续）
#             if self.last_seq is not None:
#                 expected = (self.last_seq + 1) & 0xFFFF
#                 if seq_id != expected :
#                     self.lost_packets += 1
#                     self.status_update.emit(
#                         f"丢包检测: 期望 {expected}, 收到 {seq_id}，重置解码器"
#                     )
#                     if self.count == 0:
#                         self.stream_buffer.clear()
#                         self.decoder.reset()
#                         self.count+=1
#             self.last_seq = seq_id
            

#             # self.decoder.try_cache_sps_pps_from_packet(h264_chunk)


#             # 直接将原始 h264_chunk 追加到缓冲区（不做任何清理）
#             self.stream_buffer.extend(h264_chunk)
#             buf_len = len(self.stream_buffer)
#             if buf_len > 300 * 10:   # 如果超过 3KB 就算堆积
#                 self.status_update.emit(f"流缓冲堆积: {buf_len} 字节")
#                 # self.stream_buffer.clear()
#             # 尝试解码（解码器内部会自行寻找第一个起始码）
#             images = self.decoder.parse_and_decode(self.stream_buffer)

#             for img in images:
#                 self.decoded_frames += 1
#                 self.fps_counter += 1

#                 h, w, ch = img.shape
#                 bytes_per_line = ch * w
#                 rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
#                 qimage = QImage(rgb_img.data, w, h, bytes_per_line, QImage.Format_RGB888).copy()

#                 self.buffer_lock.lock()
#                 self.frame_buffer.append(qimage)
#                 if len(self.frame_buffer) > 1:
#                     self.frame_buffer.pop(0)
#                 self.buffer_lock.unlock()

#         except Exception as e:
#             self.status_update.emit(f"处理消息异常: {e}")

#     def _on_render(self):
#         self.buffer_lock.lock()
#         if self.frame_buffer:
#             qimage = self.frame_buffer[-1]
#             self.buffer_lock.unlock()
#             self.frame_ready.emit(qimage)
#             self.display_fps_counter += 1
#         else:
#             self.buffer_lock.unlock()

#     def _update_stats(self):
#         now = time.time()
#         if now - self.last_stat_time >= 1.0:
#             self.current_fps = self.fps_counter / (now - self.last_stat_time)


#             elapsed_display = now - self.last_display_stat_time
#             display_fps = self.display_fps_counter / elapsed_display if elapsed_display > 0 else 0.0
            
#             # 发射新信号（注意顺序：包, 帧, 解码fps, 显示fps, 丢包）
#             self.stats_updated.emit(
#                 self.received_packets,
#                 self.decoded_frames,
#                 self.current_fps,
#                 display_fps,                # ← 新增参数
#                 self.lost_packets
#             )
#             self.display_fps_counter = 0
#             self.last_display_stat_time = now


#             # self.stats_updated.emit(
#             #     self.received_packets, self.decoded_frames,
#             #     self.current_fps, self.lost_packets
#             # )




#             self.fps_counter = 0
#             self.last_stat_time = now

#     def stop(self):
#         self.running = False
#         self.render_timer.stop()
#         self.wait(2000)
#         self.decoder.close()