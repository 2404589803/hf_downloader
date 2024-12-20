import sys
import os
import requests
import logging
from PyQt6.QtWidgets import *
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from huggingface_hub import hf_hub_download, login, HfApi, snapshot_download
from dotenv import load_dotenv
import time
import socket
import random
import traceback
import shutil
import urllib3
import dns.resolver
from urllib.parse import urlparse
import tempfile
import json
import ssl
import base64
import ctypes
import winreg
import http.client

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('download.log'),
        logging.StreamHandler()
    ]
)

# 自定义SSL上下文
class CustomSSLContext(ssl.SSLContext):
    def wrap_socket(self, *args, **kwargs):
        kwargs['server_hostname'] = 'huggingface.co'
        return super().wrap_socket(*args, **kwargs)

# 自定义HTTP连接
class CustomHTTPSConnection(http.client.HTTPSConnection):
    def connect(self):
        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        
        context = CustomSSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('DEFAULT')
        
        self.sock = context.wrap_socket(sock, server_hostname=self.host)

class DownloadThread(QThread):
    progress_signal = pyqtSignal(str)
    progress_value = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, repo_id, filename=None, subfolder=None, token=None, download_full_repo=False, repo_type="model", save_path=None):
        super().__init__()
        self.repo_id = repo_id
        self.filename = filename
        self.subfolder = subfolder
        self.token = token
        self.download_full_repo = download_full_repo
        self.repo_type = repo_type
        self.save_path = save_path
        self.max_retries = 100
        self.chunk_size = 1024 * 1024
        self.timeout = (30, 300)
        self.force_download = True
        
        # 禁用所有SSL验证和警告
        ssl._create_default_https_context = ssl._create_unverified_context
        urllib3.disable_warnings()
        
        # 设置环境变量
        os.environ['HF_HUB_ENABLE_HF_TRANSFER'] = "1"
        os.environ['HF_HUB_DOWNLOAD_TIMEOUT'] = "600"
        os.environ['HUGGINGFACE_HUB_VERBOSITY'] = "debug"
        os.environ['HF_HUB_DISABLE_PROGRESS_BARS'] = "1"
        os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = "1"
        os.environ['HF_HUB_ENABLE_HTTP_BACKEND'] = "1"
        os.environ['CURL_CA_BUNDLE'] = ""
        os.environ['SSL_CERT_FILE'] = ""
        os.environ['REQUESTS_CA_BUNDLE'] = ""
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = "1"
        os.environ['HF_HUB_DISABLE_EXPERIMENTAL_WARNING'] = "1"
        
        # 修改系统DNS设置
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "NameServer", 0, winreg.REG_SZ, "8.8.8.8,8.8.4.4")
            winreg.CloseKey(key)
        except:
            pass
            
        # 修改TLS设置
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\SecurityProviders\SCHANNEL\Protocols\TLS 1.2\Client", 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "DisabledByDefault", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "Enabled", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
        except:
            pass
        
        # 修改hosts
        try:
            with open(r"C:\Windows\System32\drivers\etc\hosts", "a+", encoding='utf-8') as f:
                f.seek(0)
                content = f.read()
                if "huggingface.co" not in content:
                    ips = [
                        "13.35.41.100",
                        "13.226.238.94",
                        "13.224.189.59",
                        "13.35.41.69",
                        "108.138.101.19"
                    ]
                    for ip in ips:
                        f.write(f"\n{ip} huggingface.co")
                        f.write(f"\n{ip} cdn-lfs.huggingface.co")
                        f.write(f"\n{ip} s3.amazonaws.com")
                        f.write(f"\n{ip} s3-us-west-2.amazonaws.com")
        except:
            pass
            
        # 替换requests的默认HTTPS适配器
        import requests.adapters
        class CustomHTTPAdapter(requests.adapters.HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                kwargs['ssl_context'] = CustomSSLContext(ssl.PROTOCOL_TLS_CLIENT)
                return super().init_poolmanager(*args, **kwargs)
                
        requests.adapters.HTTPAdapter = CustomHTTPAdapter
        
    def make_request(self, url, method="GET", headers=None, data=None):
        """使用自定义的HTTPS连接发送请求"""
        parsed_url = urlparse(url)
        conn = CustomHTTPSConnection(parsed_url.netloc)
        
        try:
            conn.request(method, parsed_url.path + "?" + parsed_url.query if parsed_url.query else parsed_url.path,
                        body=data,
                        headers=headers or {})
            response = conn.getresponse()
            return response
        finally:
            conn.close()
        
    def configure_network(self):
        """配置网络连接"""
        # 设置更长的超时时间
        socket.setdefaulttimeout(600)  # 10分钟超时
        
        session = requests.Session()
        
        # 设置请求头
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Pragma': 'no-cache',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest',
            'Origin': 'https://huggingface.co',
            'Referer': 'https://huggingface.co/',
            'Host': 'huggingface.co',
            'X-Forwarded-For': '104.196.242.10',
            'X-Real-IP': '104.196.242.10',
            'CF-IPCountry': 'US'
        })
        
        # 完全禁用SSL验证
        session.verify = False
        
        return session

    def run(self):
        try:
            logging.info(f"Starting download for repo_id: {self.repo_id}, repo_type: {self.repo_type}")
            
            if self.token:
                login(token=self.token)
                logging.info("Successfully logged in with token")
                self.progress_signal.emit("已登录 Hugging Face")
                self.progress_value.emit(10)

            self.progress_signal.emit("正在准备下载...")
            self.progress_value.emit(20)
            
            # 配置下载参数
            download_kwargs = {
                "repo_id": self.repo_id,
                "repo_type": self.repo_type,
                "token": self.token,
                "local_dir_use_symlinks": False,
                "resume_download": True,
                "force_download": True,
                "max_workers": 1,  # 减少并发数以避免连接重置
                "tqdm_class": None,  # 禁用进度条
                "etag_timeout": 600,  # 增加超时时间
                "local_files_only": False
            }

            # 使用snapshot_download直接下载整个仓库
            if self.download_full_repo:
                try:
                    # 设置下载目录
                    if self.save_path:
                        download_kwargs["local_dir"] = os.path.join(self.save_path, self.repo_id.split('/')[-1])
                    
                    self.progress_signal.emit("开始下载仓库...")
                    self.progress_value.emit(30)
                    
                    # 尝试下载
                    for attempt in range(5):  # 增加重试次数到5次
                        try:
                            self.progress_signal.emit(f"尝试下载 (第{attempt + 1}次)...")
                            self.progress_value.emit(40 + attempt * 10)
                             
                            # 使用自定义的HTTPS连接
                            os.environ['REQUESTS_CA_BUNDLE'] = ''
                            os.environ['SSL_CERT_FILE'] = ''
                             
                            downloaded_path = snapshot_download(**download_kwargs)
                            self.progress_value.emit(90)
                            break
                        except Exception as e:
                            if attempt < 4:  # 如果不是最后一次尝试
                                self.progress_signal.emit(f"下载失败，正在重试 ({attempt + 2}/5)...")
                                time.sleep(10)  # 增加等待时间到10秒
                            else:
                                raise e
                    
                    self.progress_value.emit(100)
                    self.finished_signal.emit(True, f"仓库已成功下载到: {downloaded_path}")
                    return
                    
                except Exception as e:
                    error_msg = str(e)
                    logging.error(f"Error during repository download: {error_msg}")
                    logging.error(traceback.format_exc())
                    
                    # 尝试使用其他仓库类型
                    if "not found" in error_msg.lower():
                        other_types = [t for t in ["model", "dataset", "space"] if t != self.repo_type]
                        for other_type in other_types:
                            try:
                                self.progress_signal.emit(f"尝试使用其他仓库类型: {other_type}")
                                download_kwargs["repo_type"] = other_type
                                downloaded_path = snapshot_download(**download_kwargs)
                                if self.save_path:
                                    final_path = os.path.join(self.save_path, self.repo_id.split('/')[-1])
                                    if os.path.exists(final_path):
                                        shutil.rmtree(final_path)
                                    shutil.copytree(downloaded_path, final_path)
                                    downloaded_path = final_path
                                self.progress_value.emit(100)
                                self.finished_signal.emit(True, f"仓库已成功下载到: {downloaded_path}")
                                return
                            except:
                                continue
                    
                    self.finished_signal.emit(False, f"下载失败: {error_msg}")
                    return
            else:
                try:
                    # 设置下载目录
                    if self.save_path:
                        local_dir = os.path.join(self.save_path, self.repo_id.split('/')[-1])
                        os.makedirs(local_dir, exist_ok=True)
                    else:
                        local_dir = None

                    self.progress_value.emit(50)
                    downloaded_path = hf_hub_download(
                        repo_id=self.repo_id,
                        filename=self.filename,
                        subfolder=self.subfolder,
                        repo_type=self.repo_type,
                        token=self.token,
                        local_dir=local_dir,
                        force_download=True,
                        resume_download=True
                    )
                    self.progress_value.emit(100)
                    self.finished_signal.emit(True, f"文件已成功下载到: {downloaded_path}")
                    return
                    
                except Exception as e:
                    logging.error(f"Error during file download: {str(e)}")
                    logging.error(traceback.format_exc())
                    self.finished_signal.emit(False, f"下载失败: {str(e)}")
                    return

        except Exception as e:
            logging.error(f"Fatal error during download: {str(e)}")
            logging.error(traceback.format_exc())
            self.finished_signal.emit(False, f"下载失败: {str(e)}")
            
    def __del__(self):
        # 恢复DNS设置
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", 0, winreg.KEY_WRITE)
            winreg.DeleteValue(key, "NameServer")
            winreg.CloseKey(key)
        except:
            pass

class HFDownloaderGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hugging Face 下载工具")
        # 设置固定窗口大小
        self.setFixedSize(600, 700)
        
        # 下载并保存 Hugging Face 图标
        self.download_hf_icon()
        
        # 设置窗口图标
        self.setWindowIcon(QIcon("hf_icon.png"))
        
        # 创建主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 设置窗口样式
        self.setStyleSheet("""
            /* 全局样式 */
            * {
                font-family: "SF Pro Text", -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
                outline: none;
            }
            
            /* 主窗口 */
            QMainWindow {
                background-color: #ffffff;
            }
            
            /* 标签样式 */
            QLabel {
                font-size: 13px;
                color: #1d1d1f;
                padding: 0;
                margin: 0;
                min-width: 90px;
            }
            
            /* 标题标签 */
            QLabel#title {
                font-family: "SF Pro Display", -apple-system, "PingFang SC", sans-serif;
                font-size: 24px;
                font-weight: 500;
                color: #1d1d1f;
                margin: 20px 0;
            }
            
            /* 输入框样式 */
            QLineEdit {
                height: 32px;
                padding: 0 10px;
                border: 1px solid #d2d2d7;
                border-radius: 6px;
                background: #ffffff;
                font-size: 13px;
                color: #1d1d1f;
            }
            
            QLineEdit:focus {
                border-color: #0066cc;
                box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
            }
            
            QLineEdit:hover {
                background: #f5f5f7;
            }
            
            QLineEdit::placeholder {
                color: #86868b;
            }
            
            /* 下拉框样式 */
            QComboBox {
                height: 32px;
                padding: 0 10px;
                border: 1px solid #d2d2d7;
                border-radius: 6px;
                background: #ffffff;
                font-size: 13px;
                color: #1d1d1f;
            }
            
            QComboBox:hover {
                background: #f5f5f7;
            }
            
            QComboBox::drop-down {
                width: 20px;
                border: none;
            }
            
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
            
            /* 复选框样式 */
            QCheckBox {
                font-size: 13px;
                color: #1d1d1f;
                spacing: 8px;
            }
            
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #d2d2d7;
                border-radius: 4px;
            }
            
            QCheckBox::indicator:checked {
                background-color: #0066cc;
                border-color: #0066cc;
                image: url(checkmark.png);
            }
            
            QCheckBox::indicator:hover {
                border-color: #0066cc;
            }
            
            /* 按钮样式 */
            QPushButton {
                height: 32px;
                padding: 0 16px;
                border: none;
                border-radius: 6px;
                background: #0066cc;
                color: #ffffff;
                font-size: 13px;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background: #0077ed;
            }
            
            QPushButton:pressed {
                background: #004499;
            }
            
            QPushButton:disabled {
                background: #d2d2d7;
            }
            
            /* 浏览按钮样式 */
            QPushButton#browseButton {
                background: #f5f5f7;
                color: #1d1d1f;
                border: 1px solid #d2d2d7;
                min-width: 70px;
            }
            
            QPushButton#browseButton:hover {
                background: #e8e8ed;
            }
            
            QPushButton#browseButton:pressed {
                background: #d2d2d7;
            }
            
            /* 消息框样式 */
            QMessageBox {
                background: #ffffff;
            }
            
            QMessageBox QLabel {
                color: #1d1d1f;
                min-width: 300px;
            }
            
            QMessageBox QPushButton {
                min-width: 80px;
            }
            
            /* 进度提示样式 */
            QLabel#progress {
                color: #86868b;
                font-size: 13px;
                margin: 10px 0;
            }
        """)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(30, 20, 30, 20)
        layout.setSpacing(16)
        
        # 添加 Hugging Face 图标
        icon_label = QLabel()
        icon_pixmap = QPixmap("hf_icon.png").scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # 添加标题
        title_label = QLabel("Hugging Face 下载工具")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # 创建表单布局
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        
        # 仓库ID输入
        self.repo_input = QLineEdit()
        self.repo_input.setPlaceholderText("例如: bert-base-chinese 或 username/repo-name")
        form_layout.addRow("仓库 ID:", self.repo_input)
        
        # 仓库类型选择
        self.type_combo = QComboBox()
        self.type_combo.addItems(["model", "dataset", "space"])
        form_layout.addRow("仓库类型:", self.type_combo)
        
        # 下载模式选择
        self.full_repo_checkbox = QCheckBox("下载整个仓库")
        self.full_repo_checkbox.stateChanged.connect(self.on_checkbox_changed)
        form_layout.addRow("", self.full_repo_checkbox)
        
        # 文件名输入
        self.file_input = QLineEdit()
        self.file_input.setPlaceholderText("例如: config.json")
        form_layout.addRow("文件名:", self.file_input)
        self.file_widgets = [self.file_input]
        
        # 子文件夹输入
        self.subfolder_input = QLineEdit()
        self.subfolder_input.setPlaceholderText("可选")
        form_layout.addRow("子文件夹:", self.subfolder_input)
        self.file_widgets.append(self.subfolder_input)
        
        # Token输入
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("可选，用于访问私有仓库")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        form_layout.addRow("HF Token:", self.token_input)
        
        # 保存路径选择
        path_widget = QWidget()
        path_layout = QHBoxLayout(path_widget)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(8)
        
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText("可选，默认使用系统缓存目录")
        
        self.save_path_button = QPushButton("浏览...")
        self.save_path_button.setObjectName("browseButton")
        self.save_path_button.clicked.connect(self.select_save_path)
        
        path_layout.addWidget(self.save_path_input)
        path_layout.addWidget(self.save_path_button)
        form_layout.addRow("保存路径:", path_widget)
        
        # 添加表单布局到主布局
        layout.addLayout(form_layout)
        
        # 添加进度提示
        self.progress_label = QLabel("准备就绪")
        self.progress_label.setObjectName("progress")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        # 下载按钮
        self.download_btn = QPushButton("开始下载")
        self.download_btn.setFixedSize(120, 32)
        self.download_btn.clicked.connect(self.start_download)
        
        # 创建按钮容器并设置居中对齐
        button_container = QHBoxLayout()
        button_container.addStretch()
        button_container.addWidget(self.download_btn)
        button_container.addStretch()
        layout.addLayout(button_container)
        
        # 添加底部空白
        layout.addStretch()
        
        # 加载环境变量
        load_dotenv()
        
        logging.info("GUI initialized successfully")

    def on_checkbox_changed(self, state):
        # 当选择下载整个仓库时，禁用文件名和子文件夹输入
        for widget in self.file_widgets:
            widget.setEnabled(not state)

    def download_hf_icon(self):
        if not os.path.exists("hf_icon.png"):
            url = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
            try:
                response = requests.get(url)
                with open("hf_icon.png", "wb") as f:
                    f.write(response.content)
                logging.info("HF icon downloaded successfully")
            except Exception as e:
                logging.error(f"Failed to download HF icon: {str(e)}")
                logging.error(traceback.format_exc())

    def update_progress(self, message):
        self.progress_label.setText(message)
        logging.info(f"Progress update: {message}")

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        
    def download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.progress_bar.setValue(0)  # 重置进度条
        if success:
            logging.info(f"Download completed successfully: {message}")
            QMessageBox.information(self, "成功", message)
        else:
            logging.error(f"Download failed: {message}")
            QMessageBox.warning(self, "错误", message)
        self.progress_label.setText("准备就绪")

    def select_save_path(self):
        """选择保存路径"""
        path = QFileDialog.getExistingDirectory(self, "选择保存路径")
        if path:
            self.save_path_input.setText(path)

    def start_download(self):
        repo_id = self.repo_input.text().strip()
        download_full_repo = self.full_repo_checkbox.isChecked()
        repo_type = self.type_combo.currentText()
        save_path = self.save_path_input.text().strip()
        
        if not repo_id:
            logging.warning("Missing repository ID")
            QMessageBox.warning(self, "警", "请填写仓库ID！\n\n格式示例：\n- username/repo-name\n- organization/model-name\n- bert-base-chinese")
            return

        if not download_full_repo and not self.file_input.text().strip():
            logging.warning("Missing filename for single file download")
            QMessageBox.warning(self, "警告", "请填写文件名！")
            return

        logging.info(f"Starting download - repo_id: {repo_id}, repo_type: {repo_type}, full_repo: {download_full_repo}, save_path: {save_path}")
        self.download_btn.setEnabled(False)
        self.progress_label.setText("正在初始化下载...")
        
        # 创建下载线程
        self.download_thread = DownloadThread(
            repo_id=repo_id,
            filename=None if download_full_repo else self.file_input.text().strip(),
            subfolder=None if download_full_repo else self.subfolder_input.text().strip() or None,
            token=self.token_input.text().strip() or None,
            download_full_repo=download_full_repo,
            repo_type=repo_type,
            save_path=save_path or None
        )
        
        # 连接信号
        self.download_thread.progress_signal.connect(self.update_progress)
        self.download_thread.progress_value.connect(self.update_progress_bar)
        self.download_thread.finished_signal.connect(self.download_finished)
        
        # 开始下载
        self.download_thread.start()

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        window = HFDownloaderGUI()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        logging.error(f"Application crashed: {str(e)}")
        logging.error(traceback.format_exc()) 