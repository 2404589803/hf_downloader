# <img src="https://huggingface.co/front/assets/huggingface_logo-noborder.svg" alt="Hugging Face" width="32" height="32" style="vertical-align: middle"> Hugging Face 下载工具

这是一个 Hugging Face 图形化下载工具。

## 功能特点

- 🚀 图形化界面，操作简单直观
- 🔄 智能重试机制，自动处理网络问题
- ⏸️ 支持断点续传，避免重复下载
- 📊 详细的下载状态提示
- 🔐 支持私有仓库访问（通过 Token）

## 系统要求

- Python 3.7 或更高版本
- Windows/Linux/MacOS 操作系统

## 安装步骤

1. 克隆本仓库：
```bash
git clone https://github.com/2404589803/hf_downloader.git
cd hf_downloader
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

## 使用说明

1. 启动程序：
```bash
python gui.py
```

2. 在界面中填写以下信息：
   - 仓库ID（必填）：例如 `bert-base-chinese`
   - 文件名（必填）：例如 `config.json`
   - 子文件夹路径（可选）：如果文件在子文件夹中
   - Hugging Face Token（可选）：用于访问私有仓库

3. 点击"开始下载"按钮即可开始下载

## 技术特性

### 下载优化
- 智能重试机制（最多50次尝试）
- 自适应等待时间（根据错误类型，5-300秒不等）
- 持久连接和连接池优化
- 支持断点续传
- 智能错误处理机制

### 安全特性
- Token 安全存储
- HTTPS 安全传输
- 文件完整性校验

## 故障排除

### 常见问题解决方案

1. **速率限制问题**
   - 系统会自动处理速率限制
   - 等待时间会动态调整（最长300秒）
   - 无需手动干预

2. **连接超时**
   - 自动重试机制
   - 智能等待策略（最长60秒）
   - 断点续传确保数据完整性

3. **大文件下载**
   - 支持断点续传功能
   - 1MB分块下载
   - 实时显示下载进度
   - 支持后台下载

## 使用建议

1. 首次使用建议：
   - 确保网络连接稳定
   - 建议登录 Hugging Face 账号
   - 测试小文件下载以熟悉操作

2. 私有仓库访问：
   - 提前准备好访问 Token
   - 确保 Token 具有适当权限
   - 妥善保管 Token 信息

3. 下载过程中：
   - 保持程序窗口开启
   - 关注下载进度提示
   - 避免频繁切换网络

## 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进这个工具。

## 许可证

本项目采用 MIT 许可证