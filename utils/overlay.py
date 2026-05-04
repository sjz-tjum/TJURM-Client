# -*- coding: utf-8 -*-
"""
绘制准心和中心圆点的工具函数
"""

import cv2
import numpy as np


def draw_crosshair(img: np.ndarray,
                   offset_x: int = 0,
                   offset_y: int = 0,
                   line_width: int = 2,
                   crosshair_color: tuple = (230, 190, 235),  # BGR 淡紫色
                   center_color: tuple = (170, 255, 170)) -> np.ndarray:  # BGR 淡绿色
    """
    在图像上绘制准心（贯穿全屏的十字线）和中心固定圆点
    
    Args:
        img: 输入图像（BGR 格式）
        offset_x: 十字线交点的水平偏移（像素）
        offset_y: 十字线交点的垂直偏移（像素）
        line_width: 十字线宽度
        crosshair_color: 十字线颜色 (B, G, R)
        center_color: 中心圆点颜色 (B, G, R)
    
    Returns:
        绘制后的图像（原地修改）
    """
    try:
        h, w = img.shape[:2]
        
        # 十字线交点位置（可偏移）
        cx = max(0, min(w - 1, w // 2 + offset_x))
        cy = max(0, min(h - 1, h // 2 + offset_y))
        
        # 绘制贯穿全屏的十字线
        cv2.line(img, (0, cy), (w - 1, cy), crosshair_color, line_width, cv2.LINE_AA)
        cv2.line(img, (cx, 0), (cx, h - 1), crosshair_color, line_width, cv2.LINE_AA)
        
        # 绘制画面正中心的固定圆点（不受偏移影响）
        center = (w // 2, h // 2)
        cv2.circle(img, center, 24, center_color, 1, cv2.LINE_AA)
        
        return img
    except Exception as e:
        print(f"[Overlay] 绘制准心失败: {e}")
        return img