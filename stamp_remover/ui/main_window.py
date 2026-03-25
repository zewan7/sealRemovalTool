#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口类
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, 
    QProgressBar, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QListWidgetItem
)
from PySide6.QtGui import QPixmap, QIcon

from PIL import Image
from PIL.ImageQt import ImageQt

from ..core import ImageProcessingThread, PdfProcessingThread, ThreadManager, PdfRegenerationThread
from .ui_main import Ui_MainWindow
from ..config import PDF_PROCESSING_CONFIG, THREAD_CONFIG
from ..utils.helpers import validate_image_file, validate_pdf_file, get_safe_output_path
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon("stamp_remover/ico/f.ico"))
        self._init_ui()
        self._init_thread_manager()
        self._init_variables()
        
    def _init_ui(self):
        """初始化UI"""
        # 设置图像标签的缩放属性
        self.label_3.setScaledContents(True)
        self.label_4.setScaledContents(True)
        self.label_5.setScaledContents(True)
        self.label_6.setScaledContents(True)
        
        # 连接信号
        self.listWidget.itemClicked.connect(self.on_listWidget_itemClicked)
        self.comboBox.currentIndexChanged.connect(self.on_color_changed)
        self.comboBox_2.currentIndexChanged.connect(self.on_pdf_color_changed)
        
        # 添加进度条到PDF处理区域
        self._add_progress_bar()
        
        # 设置窗口标题
        self.setWindowTitle("印章去除工具 v1.0.0")
        
    def _add_progress_bar(self):
        """添加进度条到PDF处理区域"""
        try:
            # 创建进度条容器
            progress_widget = QWidget()
            progress_layout = QVBoxLayout(progress_widget)
            
            # 进度条标签
            self.progress_label = QLabel("准备就绪")
            progress_layout.addWidget(self.progress_label)
            
            # 进度条
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            progress_layout.addWidget(self.progress_bar)
            
            # 状态标签
            self.status_label = QLabel("")
            progress_layout.addWidget(self.status_label)
            
            # 尝试添加到合适的布局中
            self._add_progress_to_layout(progress_widget)
        except Exception as e:
            logger.error(f"添加进度条失败: {e}")
        
    def _add_progress_to_layout(self, progress_widget):
        """尝试将进度条添加到合适的布局中"""
        # 尝试多个可能的布局名称
        layout_names = ['verticalLayout_4', 'verticalLayout_2', 'horizontalLayout_1']
        
        for layout_name in layout_names:
            if hasattr(self, layout_name):
                layout = getattr(self, layout_name)
                try:
                    layout.addWidget(progress_widget)
                    logger.info(f"进度条已添加到 {layout_name}")
                    return
                except Exception as e:
                    logger.warning(f"无法添加到 {layout_name}: {e}")
                    continue
        
        # 如果都失败了，尝试添加到主布局
        try:
            if hasattr(self, 'centralwidget'):
                central_layout = self.centralwidget.layout()
                if central_layout:
                    central_layout.addWidget(progress_widget)
                    logger.info("进度条已添加到主布局")
                else:
                    logger.warning("警告: 无法找到合适的布局位置")
        except Exception as e:
            logger.error(f"添加进度条失败: {e}")
        
    def _init_thread_manager(self):
        """初始化线程管理器"""
        self.thread_manager = ThreadManager()
        
    def _init_variables(self):
        """初始化变量"""
        self.file_name: Optional[str] = None
        self.processed_image: Optional[Image.Image] = None
        self.pdf_processing_thread: Optional[PdfProcessingThread] = None
        self.is_processing_pdf_image = False
        self.processed_images: list = []  # 存储所有处理后的图片
        
    ###########################################################################
    # 单图片处理
    ###########################################################################
    
    @Slot()
    def on_pushButton_clicked(self):
        """选择图片"""
        try:
            file_name, _ = QFileDialog.getOpenFileName(
                self,
                "选择图片",
                "",
                "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff);;所有文件 (*)"
            )

            if file_name:
                # 验证文件
                is_valid, message = validate_image_file(file_name, strict=True)
                if not is_valid:
                    QMessageBox.warning(self, "文件验证失败", message)
                    logger.warning(f"图片验证失败: {file_name} - {message}")
                    return
                
                logger.info(f"选择的图片: {file_name} - {message}")
                self.file_name = file_name
                
                # 显示图片
                pixmap = QPixmap(self.file_name)
                self.label_3.setPixmap(
                    pixmap.scaled(self.label_3.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                
                # 显示图像信息
                self._show_image_info(file_name)
            else:
                logger.info("用户取消了选择图片")
                
        except Exception as e:
            logger.error(f"选择图片时出错: {e}")
            QMessageBox.critical(self, "错误", f"选择图片失败:\n{str(e)}")

    def _show_image_info(self, image_path: str):
        """显示图像信息"""
        try:
            with Image.open(image_path) as img:
                mode = img.mode
                size = img.size
                logger.info(f"图像信息: 模式={mode}, 尺寸={size}")
                
                # 根据图像模式设置可用的颜色通道
                if mode in ['RGB', 'RGBA']:
                    channels = len(mode)
                    logger.info(f"图像有 {channels} 个通道: {mode}")
                    
                    # 更新颜色选择提示
                    if channels == 3:
                        logger.info("可用颜色: 红色(0), 绿色(1), 蓝色(2)")
                    elif channels == 4:
                        logger.info("可用颜色: 红色(0), 绿色(1), 蓝色(2), Alpha(3)")
                else:
                    logger.warning(f"图像模式 {mode} 不支持颜色通道处理")
        except Exception as e:
            logger.error(f"无法读取图像信息: {e}")

    @Slot()
    def on_pushButton_2_clicked(self):
        """开始执行图像处理"""
        try:
            if not self.file_name:
                QMessageBox.information(self, "提示", "请先选择图片")
                return

            # 再次验证文件
            is_valid, message = validate_image_file(self.file_name, strict=False)
            if not is_valid:
                QMessageBox.warning(self, "文件验证失败", message)
                return

            # 获取处理参数
            channel_index = self.comboBox.currentIndex()
            threshold = self.spinBox.value() if self.spinBox.value() > 0 else 185
            is_contrast = self.checkBox.isChecked()
            is_sharpness = self.checkBox_2.isChecked()
            
            # 创建并启动图像处理线程
            thread = ImageProcessingThread(
                image_path=self.file_name,
                rad_num=threshold,
                channel_index=channel_index,
                is_contrast=is_contrast,
                is_sharpness=is_sharpness
            )
            
            # 注册线程
            self.thread_manager.register_thread("image_processing", thread)
            
            # 连接信号
            thread.finished.connect(self.on_image_processed)
            thread.progress.connect(self._on_image_progress)
            thread.error.connect(self._on_image_error)
            
            # 启动线程
            if self.thread_manager.start_thread("image_processing"):
                logger.info("图像处理线程已启动")
            else:
                QMessageBox.critical(self, "错误", "启动图像处理线程失败")
                
        except Exception as e:
            logger.error(f"启动图像处理失败: {e}")
            QMessageBox.critical(self, "错误", f"启动图像处理失败:\n{str(e)}")

    def _on_image_progress(self, progress: int):
        """图像处理进度回调"""
        logger.info(f"图像处理进度: {progress}%")

    def _on_image_error(self, error_msg: str):
        """图像处理错误回调"""
        logger.error(f"图像处理错误: {error_msg}")
        QMessageBox.critical(self, "处理错误", f"图像处理失败:\n{error_msg}")

    @Slot()
    def on_image_processed(self, processed_image: Image.Image):
        """图像处理完成"""
        try:
            self.processed_image = processed_image
            
            if self.processed_image is not None:
                # 将PIL图像转换为QPixmap并显示
                pixmap = QPixmap.fromImage(ImageQt(self.processed_image.convert("RGBA")))
                self.label_4.setPixmap(
                    pixmap.scaled(self.label_4.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                logger.info("图像处理完成")
            else:
                logger.error("图像处理失败")
                QMessageBox.warning(self, "警告", "图像处理失败")
        except Exception as e:
            logger.error(f"显示处理结果时出错: {e}")
            QMessageBox.critical(self, "错误", f"显示处理结果失败:\n{str(e)}")

    @Slot()
    def on_pushButton_3_clicked(self):
        """保存处理后的图片"""
        try:
            if not self.processed_image:
                QMessageBox.information(self, "提示", "没有可保存的处理后图片")
                return

            # 生成建议的文件名
            original_file_name = os.path.basename(self.file_name)
            name, ext = os.path.splitext(original_file_name)
            current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggested_file_name = f"{name}_processed_{current_time_str}"
            
            # 选择保存路径
            file_name, _ = QFileDialog.getSaveFileName(
                self,
                "保存图片",
                suggested_file_name,
                "PNG 文件 (*.png);;JPEG 文件 (*.jpg *.jpeg);;BMP 文件 (*.bmp);;TIFF 文件 (*.tiff);;所有文件 (*)"
            )
            
            if file_name:
                # 根据文件扩展名选择格式
                if file_name.lower().endswith(('.jpg', '.jpeg')):
                    format = 'JPEG'
                elif file_name.lower().endswith('.png'):
                    format = 'PNG'
                elif file_name.lower().endswith('.bmp'):
                    format = 'BMP'
                elif file_name.lower().endswith('.tiff'):
                    format = 'TIFF'
                else:
                    format = 'PNG'
                
                # 保存图片
                self.processed_image.save(file_name, format=format)
                logger.info(f"图片已保存至: {file_name}")
                QMessageBox.information(self, "成功", f"图片已保存:\n{file_name}")
                
        except Exception as e:
            logger.error(f"保存图片失败: {e}")
            QMessageBox.critical(self, "保存失败", f"保存图片失败:\n{str(e)}")

    @Slot()
    def on_pushButton_7_clicked(self):
        """重置阈值"""
        try:
            self.spinBox.setValue(185)
        except Exception as e:
            logger.error(f"重置阈值失败: {e}")

    ###########################################################################
    # PDF处理
    ###########################################################################
    
    @Slot()
    def on_pushButton_5_clicked(self):
        """选择PDF文件"""
        try:
            input_pdf_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择PDF文件",
                "",
                "PDF文件 (*.pdf);;所有文件 (*)"
            )
            
            if input_pdf_path:
                # 验证PDF文件
                is_valid, message = validate_pdf_file(input_pdf_path, strict=True)
                if not is_valid:
                    QMessageBox.warning(self, "文件验证失败", message)
                    logger.warning(f"PDF验证失败: {input_pdf_path} - {message}")
                    return
                
                logger.info(f"选择的PDF: {input_pdf_path} - {message}")
                self._start_pdf_processing(input_pdf_path)
        except Exception as e:
            logger.error(f"选择PDF文件时出错: {e}")
            QMessageBox.critical(self, "错误", f"选择PDF文件失败:\n{str(e)}")

    def _start_pdf_processing(self, pdf_path: str):
        """开始PDF处理"""
        try:
            # 只显示进度条，隐藏所有文字标签
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(False)
            if hasattr(self, 'status_label'):
                self.status_label.setVisible(False)
            
            # 从配置文件读取设置
            max_workers = PDF_PROCESSING_CONFIG.get('max_workers', 4)
            enable_multithreading = PDF_PROCESSING_CONFIG.get('enable_multithreading', True)
            
            # 创建PDF处理线程
            if enable_multithreading:
                self.pdf_processing_thread = PdfProcessingThread(
                    pdf_path=pdf_path,
                    dpi=PDF_PROCESSING_CONFIG.get('default_dpi', 150),
                    max_workers=max_workers
                )
                logger.info(f"使用多线程处理PDF，工作线程数: {max_workers}")
            else:
                self.pdf_processing_thread = PdfProcessingThread(
                    pdf_path=pdf_path,
                    dpi=PDF_PROCESSING_CONFIG.get('default_dpi', 150),
                    max_workers=1
                )
                logger.info("使用单线程处理PDF")
            
            # 连接信号
            self.pdf_processing_thread.finished.connect(self.on_pdf_processed)
            self.pdf_processing_thread.progress.connect(self._on_pdf_progress)
            self.pdf_processing_thread.status.connect(self._on_pdf_status)
            self.pdf_processing_thread.error.connect(self._on_pdf_error)
            
            # 启动线程
            self.pdf_processing_thread.start()
            
        except Exception as e:
            logger.error(f"启动PDF处理失败: {e}")
            QMessageBox.critical(self, "错误", f"启动PDF处理失败:\n{str(e)}")
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)

    def _on_pdf_progress(self, current: int, total: int):
        """PDF处理进度回调"""
        try:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)
        except Exception as e:
            logger.error(f"更新进度条失败: {e}")

    def _on_pdf_status(self, status: str):
        """PDF处理状态回调"""
        logger.info(f"PDF处理状态: {status}")

    def _on_pdf_error(self, error_msg: str):
        """PDF处理错误回调"""
        logger.error(f"PDF处理错误: {error_msg}")
        QMessageBox.critical(self, "PDF处理错误", f"PDF处理失败:\n{error_msg}")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)

    @Slot()
    def on_pdf_processed(self, output_images: list):
        """PDF处理完成"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            
            self.listWidget.clear()
            
            if output_images:
                self.pdf_images_data = output_images
                
                for i, img_data in enumerate(output_images):
                    page_name = f"第 {i + 1} 页"
                    item = QListWidgetItem(page_name)
                    item.setData(Qt.UserRole, i)
                    self.listWidget.addItem(item)
                
                logger.info(f"成功处理了{len(output_images)}页")
            else:
                logger.warning("PDF处理完成，但没有生成任何图片")
                QMessageBox.warning(self, "警告", "PDF处理完成，但没有生成任何图片")
        except Exception as e:
            logger.error(f"处理PDF结果时出错: {e}")
            QMessageBox.critical(self, "错误", f"处理PDF结果失败:\n{str(e)}")
        finally:
            if hasattr(self, 'pdf_processing_thread') and self.pdf_processing_thread:
                try:
                    self.pdf_processing_thread.cleanup()
                except Exception as e:
                    logger.error(f"清理PDF处理线程失败: {e}")

    @Slot()
    def on_listWidget_itemClicked(self, item):
        """PDF页面点击事件"""
        try:
            if self.is_processing_pdf_image:
                self._cancel_pdf_image_processing()
            
            image_index = item.data(Qt.UserRole)
            if image_index is None or not hasattr(self, 'pdf_images_data'):
                return
                
            if 0 <= image_index < len(self.pdf_images_data):
                img_data = self.pdf_images_data[image_index]
                
                from PIL import Image
                import io
                from PIL.ImageQt import ImageQt
                
                pil_img = Image.open(io.BytesIO(img_data))
                if pil_img.mode != 'RGBA':
                    pil_img = pil_img.convert('RGBA')
                
                qimage = ImageQt(pil_img)
                pixmap = QPixmap.fromImage(qimage)
                
                self.label_5.setPixmap(
                    pixmap.scaled(self.label_5.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                
                self.label_6.setText("正在处理中...")
                
                self._start_pdf_image_processing_from_pil(pil_img)
            else:
                logger.error(f"图片索引超出范围: {image_index}")
        except Exception as e:
            logger.error(f"处理PDF页面点击事件时出错: {e}")
            QMessageBox.critical(self, "错误", f"处理PDF页面失败:\n{str(e)}")

    def _start_pdf_image_processing_from_pil(self, pil_image):
        """从PIL图像开始处理PDF图片"""
        try:
            self.is_processing_pdf_image = True
            
            thread = ImageProcessingThread(
                pil_image=pil_image,
                rad_num=self.spinBox_2.value(),
                channel_index=self.comboBox_2.currentIndex(),
                is_contrast=self.checkBox_3.isChecked(),
                is_sharpness=self.checkBox_4.isChecked()
            )
            
            self.thread_manager.register_thread("pdf_image_processing", thread)
            
            thread.finished.connect(self.on_pdf_image_processed)
            thread.error.connect(self._on_pdf_image_error)
            
            if self.thread_manager.start_thread("pdf_image_processing"):
                logger.info("PDF图片处理线程已启动")
            else:
                QMessageBox.critical(self, "错误", "启动PDF图片处理线程失败")
                self.is_processing_pdf_image = False
        except Exception as e:
            logger.error(f"启动PDF图片处理失败: {e}")
            QMessageBox.critical(self, "错误", f"启动PDF图片处理失败:\n{str(e)}")
            self.is_processing_pdf_image = False

    def _cancel_pdf_image_processing(self):
        """取消PDF图片处理"""
        try:
            if self.thread_manager.is_thread_running("pdf_image_processing"):
                self.thread_manager.stop_thread("pdf_image_processing")
                self.is_processing_pdf_image = False
                logger.info("取消之前的PDF图片处理")
        except Exception as e:
            logger.error(f"取消PDF图片处理失败: {e}")

    @Slot()
    def on_pdf_image_processed(self, processed_image: Image.Image):
        """PDF图片处理完成"""
        try:
            self.is_processing_pdf_image = False
            
            if processed_image is not None:
                pixmap = QPixmap.fromImage(ImageQt(processed_image.convert("RGBA")))
                self.label_6.setPixmap(
                    pixmap.scaled(self.label_6.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
                
                self.processed_images.append(processed_image)
                
                logger.info("PDF图片处理完成")
            else:
                logger.error("PDF图片处理失败")
                self.label_6.setText("处理失败")
        except Exception as e:
            logger.error(f"显示PDF图片处理结果时出错: {e}")
            self.label_6.setText(f"显示失败: {str(e)}")
            self.is_processing_pdf_image = False

    def _on_pdf_image_error(self, error_msg: str):
        """PDF图片处理错误"""
        logger.error(f"PDF图片处理错误: {error_msg}")
        self.label_6.setText(f"处理失败: {error_msg}")
        self.is_processing_pdf_image = False
        QMessageBox.critical(self, "处理错误", f"PDF图片处理失败:\n{error_msg}")
        
        try:
            self.label_6.clear()
        except:
            pass

    @Slot()
    def on_pushButton_6_clicked(self):
        """开始执行PDF图片处理"""
        try:
            current_item = self.listWidget.currentItem()
            if current_item:
                self.on_listWidget_itemClicked(current_item)
            else:
                QMessageBox.information(self, "提示", "请先选择一个PDF页面")
        except Exception as e:
            logger.error(f"执行PDF图片处理时出错: {e}")
            QMessageBox.critical(self, "错误", f"执行PDF图片处理失败:\n{str(e)}")

    @Slot()
    def on_pushButton_4_clicked(self):
        """重置PDF处理阈值"""
        try:
            self.spinBox_2.setValue(185)
        except Exception as e:
            logger.error(f"重置PDF处理阈值失败: {e}")
    
    @Slot()
    def on_pushButton_8_clicked(self):
        """导出所有处理后的图像为PDF"""
        try:
            if not hasattr(self, 'pdf_images_data') or not self.pdf_images_data:
                QMessageBox.information(self, "提示", "没有可导出的PDF图片数据")
                return
            
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存PDF",
                "processed_document.pdf",
                "PDF文件 (*.pdf)"
            )
            
            if save_path:
                self._start_pdf_regeneration(save_path)
        except Exception as e:
            logger.error(f"导出PDF时出错: {e}")
            QMessageBox.critical(self, "错误", f"导出PDF失败:\n{str(e)}")

    def _start_pdf_regeneration(self, save_path: str):
        """开始PDF重新生成过程"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            if hasattr(self, 'progress_label'):
                self.progress_label.setVisible(True)
                self.progress_label.setText("正在重新生成PDF...")
            
            threshold = self.spinBox_2.value()
            channel_index = self.comboBox_2.currentIndex()
            enable_contrast = self.checkBox_3.isChecked()
            enable_sharpness = self.checkBox_4.isChecked()
            
            max_workers = PDF_PROCESSING_CONFIG.get('max_workers', 4)
            
            thread = PdfRegenerationThread(
                image_data_list=self.pdf_images_data,
                output_path=save_path,
                rad_num=threshold,
                channel_index=channel_index,
                enable_contrast=enable_contrast,
                enable_sharpness=enable_sharpness,
                max_workers=max_workers
            )
            
            self.thread_manager.register_thread("pdf_regeneration", thread)
            
            thread.finished.connect(self.on_pdf_regeneration_finished)
            thread.progress.connect(self._on_pdf_progress)
            thread.error.connect(self._on_pdf_regeneration_error)
            
            if self.thread_manager.start_thread("pdf_regeneration"):
                logger.info("PDF重新生成线程已启动")
            else:
                QMessageBox.critical(self, "错误", "启动PDF重新生成线程失败")
                
        except Exception as e:
            logger.error(f"启动PDF重新生成失败: {e}")
            QMessageBox.critical(self, "错误", f"启动PDF重新生成失败:\n{str(e)}")
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)

    @Slot()
    def on_pdf_regeneration_finished(self, output_path: str):
        """PDF重新生成完成"""
        try:
            if hasattr(self, 'progress_bar'):
                self.progress_bar.setVisible(False)
            if hasattr(self, 'progress_label'):
                self.progress_label.setText("PDF重新生成完成")
            
            logger.info(f"PDF已重新生成至: {output_path}")
            QMessageBox.information(self, "成功", f"PDF已重新生成:\n{output_path}")
            
        except Exception as e:
            logger.error(f"处理PDF重新生成结果时出错: {e}")
            QMessageBox.critical(self, "错误", f"处理PDF重新生成结果失败:\n{str(e)}")
        finally:
            if hasattr(self, 'pdf_regeneration_thread') and self.pdf_regeneration_thread:
                try:
                    self.pdf_regeneration_thread.cleanup()
                except Exception as e:
                    logger.error(f"清理PDF重新生成线程失败: {e}")

    def _on_pdf_regeneration_error(self, error_msg: str):
        """PDF重新生成错误"""
        logger.error(f"PDF重新生成错误: {error_msg}")
        QMessageBox.critical(self, "PDF重新生成错误", f"PDF重新生成失败:\n{error_msg}")
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setVisible(False)

    ###########################################################################
    # 其他方法
    ###########################################################################
    
    @Slot()
    def on_color_changed(self, index: int):
        """颜色选择改变"""
        colors = ["红色", "绿色", "蓝色", "Alpha"]
        if 0 <= index < len(colors):
            logger.info(f"颜色选择改变为: {colors[index]}")

    @Slot()
    def on_pdf_color_changed(self, index: int):
        """PDF颜色选择改变"""
        colors = ["红色", "绿色", "蓝色", "Alpha"]
        if 0 <= index < len(colors):
            logger.info(f"PDF颜色选择改变为: {colors[index]}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            logger.info("正在关闭应用程序...")
            
            # 清理所有线程
            if hasattr(self, 'thread_manager'):
                self.thread_manager.cleanup_all()
            
            # 清理PDF处理线程
            if hasattr(self, 'pdf_processing_thread') and self.pdf_processing_thread:
                try:
                    self.pdf_processing_thread.cleanup()
                except Exception as e:
                    logger.error(f"清理PDF处理线程失败: {e}")
            
            logger.info("应用程序已关闭")
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭应用程序时出错: {e}")
            event.accept()
