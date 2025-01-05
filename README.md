# Hugging Face Downloader

A GUI tool for downloading models, datasets, and spaces from Hugging Face.

[中文文档](README_zh.md)

## Features

- Download entire repositories or single files
- Support for models, datasets, and spaces
- Multi-language support (English, Chinese)
- Custom save path
- Progress tracking
- Private repository support with token
- Automatic retry and fallback mechanisms
- SSL verification bypass for regions with connection issues

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/hf_downloader.git
cd hf_downloader
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python gui.py
```

2. Enter the repository information:
   - Repository ID (e.g., bert-base-chinese or username/repo-name)
   - Select repository type (model, dataset, or space)
   - Choose between downloading entire repository or single file
   - For single file download, specify filename and optional subfolder
   - Optionally provide HF token for private repositories
   - Choose custom save path or use default cache directory

3. Click "Start Download" and wait for completion

## Requirements

- Python 3.6+
- PyQt6
- huggingface_hub
- requests
- python-dotenv
- dnspython

## Known Issues

- SSL certificate verification might fail in some regions
- Download might be slow in certain locations
- Some private repositories might require additional authentication

## Contributing

Feel free to open issues or submit pull requests for any bugs or improvements.