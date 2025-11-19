# 通用更新检查器使用说明

这个版本只需要提供4个基本参数，其他都由代码自动推断和处理。

## 快速开始

### 1. 创建配置文件

创建一个 JSON 配置文件，只需要4个参数：

```json
{
  "app_name": "应用名称",
  "version_url": "版本检查页面URL",
  "version_pattern": "正则表达式提取版本号",
  "download_url_template": "下载地址模板"
}
```

### 2. 运行检查器

```bash
python3 .github/scripts/update_checker.py config.json
```

## 配置参数详解

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `app_name` | 应用名称，用于显示 | `"Sublime Text"` |
| `version_url` | 检查最新版本的网页URL | `"https://www.sublimetext.com/download"` |
| `version_pattern` | 从网页提取版本号的正则表达式，第一个捕获组是版本号 | `"Build\\s+(\\d{4})"` |
| `download_url_template` | 下载URL模板，支持 `{version}` 和 `{arch}` 占位符 | `"https://download.site.com/app-{version}_{arch}.deb"` |

## 实际示例

### Sublime Text 配置

```json
{
  "app_name": "Sublime Text",
  "version_url": "https://www.sublimetext.com/download",
  "version_pattern": "Build\\s+(\\d{4})",
  "download_url_template": "https://download.sublimetext.com/sublime-text_build-{version}_{arch}.deb"
}
```

### VS Code 配置（假设）

```json
{
  "app_name": "Visual Studio Code",
  "version_url": "https://code.visualstudio.com/updates",
  "version_pattern": "Version\\s+(\\d+\\.\\d+\\.\\d+)",
  "download_url_template": "https://update.code.visualstudio.com/{version}/linux-deb-{arch}/stable"
}
```

## 智能特性

### 自动架构检测

- 自动识别文件名中的 `amd64`、`arm64`、`sw64`、`riscv64`、`loong64`、`mips64`
- 默认使用 `amd64` 如果无法识别

### 自动版本号提取

- 支持多种版本号格式：4200、1.2.3、1.2
- 自动从现有文件名中提取版本号模式

### 自动文件发现

- 自动查找 `linglong.yaml`
- 自动查找 `amd64/linglong.yaml`、`arm64/linglong.yaml` 等架构子目录

### 智能YAML更新

- 自动匹配和更新 sources 中的条目
- 自动计算文件哈希值
- 自动更新 package 版本号
- 保持YAML格式不变

## GitHub Actions 集成

更新工作流文件使用新脚本：

```yaml
- name: Run update checker
  run: python3 .github/scripts/ultra_simple_update_checker.py simple_config.json
```

## 迁移指南

从硬编码脚本迁移：

1. **分析原脚本**：提取 `app_name`、`version_url`、`version_pattern`、`download_url_template`
2. **创建配置文件**：将提取的信息写成JSON格式
3. **测试配置**：运行新脚本确保工作正常
4. **更新工作流**：修改GitHub Actions使用新脚本

## 版本号处理

自动处理各种版本号格式：

- `4200` → `4200.0.0.1120`
- `1.2` → `1.2.0.1120`
- `1.2.3` → `1.2.3.1120`
- `1.2.3.4` → `1.2.3.1120`（取前三位）

## 错误处理

- 清晰的错误信息和提示
- 自动跳过无法处理的文件
- 详细的处理日志
