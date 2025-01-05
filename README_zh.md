# Hugging Face 下载工具

一个用于从 Hugging Face 下载模型、数据集和空间的图形界面工具。

[English Documentation](README.md)

## 功能特点

- 支持下载整个仓库或单个文件
- 支持模型、数据集和空间类型
- 多语言支持（中文、英文）
- 自定义保存路径
- 下载进度跟踪
- 支持使用令牌访问私有仓库
- 自动重试和备选方案
- 针对连接问题地区的 SSL 验证绕过

## 安装方法

1. 克隆仓库：
```bash
git clone https://github.com/yourusername/hf_downloader.git
cd hf_downloader
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用方法

1. 运行应用程序：
```bash
python gui.py
```

2. 输入仓库信息：
   - 仓库 ID（例如：bert-base-chinese 或 username/repo-name）
   - 选择仓库类型（模型、数据集或空间）
   - 选择下载整个仓库或单个文件
   - 单文件下载时，指定文件名和可选的子文件夹
   - 可选择提供 HF 令牌用于访问私有仓库
   - 选择自定义保存路径或使用默认缓存目录

3. 点击"开始下载"并等待完成

## 系统要求

- Python 3.6+
- PyQt6
- huggingface_hub
- requests
- python-dotenv
- dnspython

## 已知问题

- 某些地区可能出现 SSL 证书验证失败
- 某些地区下载速度可能较慢
- 某些私有仓库可能需要额外的认证

## 贡献

欢迎为任何错误或改进开启 issue 或提交 pull request。 