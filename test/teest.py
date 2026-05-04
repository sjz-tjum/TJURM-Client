import struct

VIDEO_DATA_FMT = '<Hq290s'
VIDEO_DATA_SIZE = 300

def check_continuity(filename):
    last_seq = None
    line_count = 0
    inconsistencies = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or ':' not in line:
                continue
                
            parts = line.split(': ', 1)
            line_seq = int(parts[0])
            hex_str = parts[1]
            
            # 解析二进制
            hex_bytes = bytes.fromhex(hex_str)
            if len(hex_bytes) >= 2:
                # 小端序解析前两个字节
                parsed_seq = struct.unpack('<H', hex_bytes[:2])[0]
                
                if parsed_seq != line_seq:
                    print(f"行{line_count}: 不一致! 行首={line_seq}, 解析={parsed_seq}")
                    inconsistencies += 1
                
                # 连续性检查
                if last_seq is not None:
                    expected = (last_seq + 1) & 0xFFFF
                    if parsed_seq != expected:
                        gap = (parsed_seq - expected) & 0xFFFF
                        print(f"行{line_count}: seq不连续! 前={last_seq}, 当前={parsed_seq}, 期望={expected}, 间隙={gap}")
                
                last_seq = parsed_seq
                line_count += 1
    
    print(f"\n检查完成:")
    print(f"总行数: {line_count}")
    print(f"不一致数: {inconsistencies}")
    print(f"连续性: {'完美' if inconsistencies == 0 else '有问题'}")

if __name__ == "__main__":
    check_continuity("raw_data.txt")