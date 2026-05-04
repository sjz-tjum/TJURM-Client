#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MQTT H.264 视频接收端 - 程序入口
Windows 专用版本
"""

import sys
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

# ==== 启用高 DPI 支持 ====
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QCoreApplication
QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

# ==== 导入其他模块 ====
import signal
import time
from datetime import datetime
import json
import struct
import math
import numpy as np
import io
from collections import deque, defaultdict
import threading
import hashlib
from fractions import Fraction
import tempfile

# 导入可能冲突的库
try:
    import cv2
except ImportError:
    cv2 = None
    print("[WARN] OpenCV 未安装")

try:
    import av
except ImportError:
    av = None
    print("[WARN] av 未安装")

from ui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    # 设置字体
    from PyQt5.QtGui import QFont
    font = QFont("Microsoft YaHei", 9)
    app.setFont(font)
    
    # 创建窗口
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()