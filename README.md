# 国家中小学智慧教育平台 电子课本下载工具

[![Codeberg](https://img.shields.io/badge/hosted_at-Codeberg-2185D0?logo=codeberg)](https://codeberg.org/flandre_scarlet/bsetm-dl)
![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

> **⚠️ 本仓库已迁移至 Codeberg**  
> GitHub 上的此仓库仅为只读镜像。请前往 [Codeberg 主仓库](https://codeberg.org/flandre_scarlet/bsetm-dl) 提交 Issue、PR 或获取最新版本。

CLI 工具，可从[国家中小学智慧教育平台](https://basic.smartedu.cn/)获取电子课本 PDF 下载链接并下载。

**版本**: v4.0-cli

## 仓库迁移说明

本项目的开发与维护已迁移至 **Codeberg**：[https://codeberg.org/flandre_scarlet/bsetm-dl](https://codeberg.org/flandre_scarlet/bsetm-dl)

- 📦 **主仓库（含最新代码）**: [Codeberg →](https://codeberg.org/flandre_scarlet/bsetm-dl)
- 🐛 **提交 Issue**: [Codeberg Issues →](https://codeberg.org/flandre_scarlet/bsetm-dl/issues)
- 🔀 **提交 PR**: [Codeberg Pull Requests →](https://codeberg.org/flandre_scarlet/bsetm-dl/pulls)
- ⭐ **Star / Watch**: 请在 Codeberg 关注本项目

> GitHub 仓库的 Issue、PR、Wiki 和 Discussions 均已关闭，不再维护。

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
