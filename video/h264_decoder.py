
# #能用
# import av
# import cv2
# import os
# from utils.overlay import draw_crosshair

# class H264Decoder:
#     def __init__(self, width, height):
#         self.width = width
#         self.height = height
#         self.codec = None
#         self.frame_count = 0
#         self._reset_codec(reason='init')

#     def _reset_codec(self, reason=''):
#         """创建解码器，不再设置任何 extradata，依赖流内参数集"""
#         try:
#             self.codec = av.CodecContext.create('h264', 'r')
#             self.codec.thread_type = 'FRAME'
#             # self.codec.skip_frame = 'NONREF'
#             self.codec.thread_count = 8
#             if hasattr(av.codec.context.Flags, 'LOW_DELAY'):
#                 self.codec.flags |= av.codec.context.Flags.LOW_DELAY
#              # 注入 extradata（如果文件存在）
#             # if os.path.exists('avcc_cache.bin'):
#             #     with open('avcc_cache.bin', 'rb') as f:
#                     # self.codec.extradata = f.read()
#             #     print("[Decoder] 已注入 avcC extradata，无需等待流内 SPS/PPS")
#             # else:
#             #     print("[Decoder] 未找到 avcc_cache.bin，依赖流内参数集（可能失败）")

#             # print(f"[Decoder] 解码器已重置 (原因: {reason})")
#         except Exception as e:
#             print(f"[Decoder] 创建解码器失败: {e}")
#             self.codec = None
#             print(f"[Decoder] 解码器已重置 (原因: {reason})")

#     def reset(self):
#         """外部调用，用于丢包时强制重置"""
#         self._reset_codec(reason='manual reset')

#     @staticmethod
#     def _find_start_code(buf, start=0):
#         """返回起始码位置，未找到返回 -1"""
#         for i in range(start, len(buf) - 3):
#             if buf[i:i+4] == b'\x00\x00\x00\x01' or buf[i:i+3] == b'\x00\x00\x01':
#                 return i
#         return -1









#     def _split_complete_nalus(self, buf: bytearray):
#         """
#         从缓冲区中提取所有完整的 NAL 单元（包含起始码）。
#         返回：(nal_units_list, consumed_bytes)
#         - nal_units_list : list of bytes，每个元素是一个完整的 NAL 单元
#         - consumed_bytes  : 已消费的总字节数（缓冲区中最后一个不完整的 NAL 会保留）
#         """
#         nal_units = []
#         consumed = 0
#         i = 0
#         while i < len(buf):
#             start = self._find_start_code(buf, i)
#             if start == -1:
#                 break
#             next_start = self._find_start_code(buf, start + 1)
#             if next_start == -1:
#                 # 没有下一个起始码 → 最后一个 NAL 可能不完整，保留
#                 break
#             nal_data = buf[start:next_start]
#             nal_units.append(bytes(nal_data))
#             consumed += len(nal_data)
#             i = next_start
#         return nal_units, consumed

#     def parse_and_decode(self, buffer: bytearray):
#         """
#         解码缓冲区中的 Annex‑B H.264 数据。
#         buffer 会被原地修改：已成功解码的数据会被删除。
#         返回解码出的 BGR 图像列表。
#         """
#         if not self.codec or len(buffer) == 0:
#             return []


#         start_pos = self._find_start_code(buffer)
#         if start_pos == -1:

#             if len(buffer) > 150:
#                 print(f"[Decoder] 无起始码，清空 {len(buffer)} 字节")
#                 buffer.clear()
#             return []
#         if start_pos > 0:

#             print(f"[Decoder] 丢弃起始码前 {start_pos} 字节")
#             del buffer[:start_pos]

#         images = []

#         try:
       
#             nal_units, consumed = self._split_complete_nalus(buffer)

#             if consumed > 0:
       
#                 data_to_decode = b''.join(nal_units)
#                 packets = self.codec.parse(data_to_decode)

#                 for pkt in packets:
#                     frames = self.codec.decode(pkt)
#                     for frame in frames:
#                         img = frame.to_ndarray(format='bgr24')
#                         if img.shape[:2] != (self.height, self.width):
#                             img = cv2.resize(img, (self.height, self.width))
#                         # img = draw_crosshair(img)
#                         images.append(img)
#                         self.frame_count += 1

#                 # 消费已处理的数据
#                 del buffer[:consumed]

#         except Exception as e:
#             print(f"[Decoder] 解码错误: {e}，跳过当前 NAL 重新同步...")
#             # 跳过第一个 NAL（可能是损坏的），寻找下一个起始码
#             if len(buffer) > 1:
#                 next_start = self._find_start_code(buffer, 1)
#                 if next_start != -1:
#                     skip_bytes = next_start
#                     print(f"[Decoder] 跳过 {skip_bytes} 字节")
#                     del buffer[:skip_bytes]
#                     self._reset_codec(reason='sync after error')
#                 else:
#                     print(f"[Decoder] 无法同步")
#                     buffer.clear()
#                     self._reset_codec(reason='reset after error')
#             else:
#                 buffer.clear()
#                 self._reset_codec(reason='clear after error')

#         return images

#     def close(self):
#         self.codec = None



import av
import cv2
from utils.overlay import draw_crosshair

class H264Decoder:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.codec = None
        self.frame_count = 0
        self._cached_extradata = None  # 缓存 avcC extradata
        self._reset_codec(reason='init')

    def set_extradata(self, avcc_bytes: bytes):
        """外部注入 avcC 格式参数集，并立即应用到当前解码器（若存在）"""
        self._cached_extradata = avcc_bytes
        if self.codec:
            self.codec.extradata = avcc_bytes
        print("[Decoder] 已接收外部 extradata 并缓存")

    def _reset_codec(self, reason=''):
        """创建解码器，如果已有缓存的 extradata 则注入"""
        try:
            self.codec = av.CodecContext.create('h264', 'r')
            self.codec.thread_type = 'FRAME'
            self.codec.thread_count = 8
            if hasattr(av.codec.context.Flags, 'LOW_DELAY'):
                self.codec.flags |= av.codec.context.Flags.LOW_DELAY

            # 注入缓存的 extradata
            if self._cached_extradata:
                self.codec.extradata = self._cached_extradata
                print("[Decoder] 已注入缓存的 extradata")
            else:
                print("[Decoder] 暂无 extradata，依赖流内参数集")

            print(f"[Decoder] 解码器已重置 (原因: {reason})")
        except Exception as e:
            print(f"[Decoder] 创建解码器失败: {e}")
            self.codec = None

    def reset(self):
        """外部调用强制重置（例如严重错误时），复用已有 extradata"""
        self._reset_codec(reason='manual reset')

    # ========== 以下原有解码逻辑 ==========
    @staticmethod
    def _find_start_code(buf, start=0):
        for i in range(start, len(buf) - 3):
            if buf[i:i+4] == b'\x00\x00\x00\x01' or buf[i:i+3] == b'\x00\x00\x01':
                return i
        return -1

    def _split_complete_nalus(self, buf: bytearray):
        nal_units = []
        consumed = 0
        i = 0
        while i < len(buf):
            start = self._find_start_code(buf, i)
            if start == -1:
                break
            next_start = self._find_start_code(buf, start + 1)
            if next_start == -1:
                break
            nal_data = buf[start:next_start]
            nal_units.append(bytes(nal_data))
            consumed += len(nal_data)
            i = next_start
        return nal_units, consumed

    def parse_and_decode(self, buffer: bytearray):
        if not self.codec or len(buffer) == 0:
            return []

        # 对齐起始码
        start_pos = self._find_start_code(buffer)
        if start_pos == -1:
            if len(buffer) > 500000:  # 500KB 硬上限防止内存泄漏
                print("[Decoder] 无起始码且过大，清空")
                buffer.clear()
            return []
        if start_pos > 0:
            del buffer[:start_pos]

        images = []
        try:
            nal_units, consumed = self._split_complete_nalus(buffer)
            if consumed > 0:
                data_to_decode = b''.join(nal_units)
                packets = self.codec.parse(data_to_decode)
                for pkt in packets:
                    try:
                        frames = self.codec.decode(pkt)
                        for frame in frames:
                            img = frame.to_ndarray(format='bgr24')
                            if img.shape[:2] != (self.height, self.width):
                                img = cv2.resize(img, (self.height, self.width))
                            images.append(img)
                            self.frame_count += 1
                    except Exception:
                        pass  # 单帧损坏跳过
                del buffer[:consumed]
        except Exception as e:
            # 整个 parse 失败（极少见），不重置解码器，保留数据等待 IDR
            print(f"[Decoder] 解码异常: {e}，保留数据等待下一个 IDR")
        return images

    def close(self):
        self.codec = None