# 国家中小学智慧教育平台 电子课本下载工具

![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

CLI 工具，可从[国家中小学智慧教育平台](https://basic.smartedu.cn/)获取电子课本 PDF 下载链接并下载。

**版本**: v4.0-cli

## 安装

```bash
pip install -r requirements.txt
```

## 使用

```
python src/main.py <子命令> [参数]
```

### 搜索课本

```bash
python src/main.py search <关键词>
```

按关键词搜索课本，打印匹配的课本名称。

### 解析 URL，获取下载链接

```bash
python src/main.py parse <URL> [URL ...]
```

解析资源页面 URL，输出 PDF 直链。

### 下载 PDF

```bash
python src/main.py download <课本名称> -o <输出目录>
```

按名称搜索并下载课本。支持多线程分块下载和自动重试。

**选项**:
- `-o, --output-dir` — 输出目录（默认当前目录）
- `-t, --threads` — 下载线程数（>1 启用多线程分块下载，需服务器支持 Range）
- `-r, --retry` — 失败重试次数（默认 3）

## 常见问题

### 下载失败？

- 网络不稳定或资源已被移除

## 许可证

MIT
