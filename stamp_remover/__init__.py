"""
印章去除工具 (Stamp Remover)

一个专业的印章去除工具，用于处理包含印章的图片和PDF文档。
通过智能图像处理技术，自动识别并去除印章区域，实现文档的清洁化处理。
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"
__description__ = "印章去除工具 - 智能去除图片和PDF中的印章"

from .core import ImageProcessingThread, PdfProcessingThread, ThreadManager
from .ui import MainWindow

__all__ = [
    "__version__",
    "__author__",
    "__email__",
    "__description__",
    "ImageProcessingThread",
    "PdfProcessingThread", 
    "ThreadManager",
    "MainWindow",
]

