# import av
# import cv2
# import sys
# import os

# def play_raw_h264(raw_h264_path):
#     if not os.path.exists(raw_h264_path):
#         print(f"错误：文件 '{raw_h264_path}' 未找到。")
#         return

#     # 初始化一个 H.264 解码器
#     codec = av.CodecContext.create('h264', 'r')

#     # 对于裸流，解码器通常需要知道分辨率。
#     # 如果你的视频分辨率未知，可以先解码一帧，从解码后的帧中获取宽高再重新初始化。
#     # 这里为了演示，先预设一个常见的分辨率，例如 1280x720。
#     # 如果分辨率不匹配，解码可能会失败或画面花屏。
#     # 更健壮的做法是：先尝试解码，如果失败则从帧信息中获取分辨率并重新创建解码器。
#     codec.width = 300
#     codec.height = 300
#     # 设置像素格式，通常为 'yuv420p'
#     codec.pix_fmt = 'yuv420p'

#     print("正在解码裸 H.264 流...")
#     print("按 'q' 键退出播放。")

#     with open(raw_h264_path, 'rb') as f:
#         while True:
#             # 每次读取一块数据，大小可调整
#             chunk = f.read(64 * 1024)  # 64KB
#             if not chunk:
#                 break

#             # 将裸数据解析为 Packet
#             packets = codec.parse(chunk)

#             # 遍历解析出的每个 Packet
#             for packet in packets:
#                 # 解码 Packet，得到 Frame 列表
#                 frames = codec.decode(packet)
#                 for frame in frames:
#                     # 将帧转换为 numpy 数组 (BGR格式)
#                     img = frame.to_ndarray(format='bgr24')
                    
#                     cv2.imshow('Raw H.264 Player', img)

#                     key = cv2.waitKey(1) & 0xFF
#                     if key == ord('q'):
#                         print("用户请求退出。")
#                         cv2.destroyAllWindows()
#                         return

#     print("文件读取完毕。")
#     cv2.destroyAllWindows()

# if __name__ == "__main__":
#     # 替换为你的 .h264 文件路径
#     file_path = "video_stream.h264"
#     if len(sys.argv) > 1:
#         file_path = sys.argv[1]
#     play_raw_h264(file_path)

# 手动提取脚本（只需运行一次）
sps_nal = bytes.fromhex("0000000167f4001e919b282613f2cb80b506010540000003004000001e23c58b6580")
pps_nal = bytes.fromhex("0000000168eaec4480")
avcc_hex = "01f4001effe1001e67f4001e919b282613f2cb80b506010540000003004000001e23c58b658001000568eaec4480"
with open('avcc_cache.bin', 'wb') as f:
    f.write(bytes.fromhex(avcc_hex))
print("avcc_cache.bin 已生成")