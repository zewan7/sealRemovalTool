#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
印章去除工具 - 一个用于去除图片和PDF文档中印章的工具
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="stamp-remover",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="一个用于去除图片和PDF文档中印章的工具",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/stamp-remover",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Scientific/Engineering :: Image Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    python_requires=">=3.8",
    install_requires=[
        "PySide6>=6.5.0",
        "Pillow>=9.0.0",
        "numpy>=1.21.0",
        "PyMuPDF>=1.21.0",
        "pdf2image>=1.16.0",
        "PyPDF2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "stamp-remover=stamp_remover.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "stamp_remover": ["ui/*.ui", "resources/*"],
    },
)

