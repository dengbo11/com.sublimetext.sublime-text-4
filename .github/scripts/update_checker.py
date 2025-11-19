#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用应用更新检查器
只需要提供应用名称、版本检查URL和下载地址模板
"""

import re
import sys
import os
import yaml
import hashlib
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime
import json


# Custom YAML representer for literal block style
class literal_str(str):
    pass


def literal_str_presenter(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(literal_str, literal_str_presenter)


class UpdateChecker:
    def __init__(self, config_file):
        """初始化更新检查器"""
        self.config = self.load_config(config_file)
        self.app_name = self.config.get("app_name", "Unknown App")
        self.version_url = self.config.get("version_url", "")
        self.version_pattern = self.config.get("version_pattern", "")
        self.download_url_template = self.config.get("download_url_template", "")

    def load_config(self, config_file):
        """加载配置文件"""
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            sys.exit(1)

    def fetch_latest_version(self):
        """获取最新版本号"""
        try:
            if not self.version_url:
                print("未配置版本检查URL")
                return None

            with urllib.request.urlopen(self.version_url) as response:
                html = response.read().decode("utf-8")

            version_match = re.search(self.version_pattern, html)
            if version_match:
                return version_match.group(1)
            else:
                print(f"无法从页面解析版本号")
                return None
        except urllib.error.URLError as e:
            print(f"获取版本页面失败: {e}")
            return None

    def calculate_sha256(self, url):
        """计算远程文件的SHA256哈希值"""
        try:
            print(f"正在计算文件哈希值: {url}")
            with urllib.request.urlopen(url) as response:
                sha256_hash = hashlib.sha256()
                for chunk in iter(lambda: response.read(4096), b""):
                    sha256_hash.update(chunk)
                return sha256_hash.hexdigest()
        except urllib.error.URLError as e:
            print(f"下载文件失败: {e}")
            return None

    def update_package_version(self, yaml_data, new_build_version):
        """更新package字段中的version"""
        try:
            current_date = datetime.now().strftime("%m%d")
            version_parts = str(new_build_version).split(".")

            # 根据版本号位数构建新版本号
            if len(version_parts) == 1:
                new_version = f"{version_parts[0]}.0.0.{current_date}"
            elif len(version_parts) == 2:
                new_version = f"{version_parts[0]}.{version_parts[1]}.0.{current_date}"
            elif len(version_parts) >= 3:
                new_version = f"{version_parts[0]}.{version_parts[1]}.{version_parts[2]}.{current_date}"
            else:
                new_version = f"{new_build_version}.0.0.{current_date}"

            if "package" in yaml_data and isinstance(yaml_data["package"], dict):
                yaml_data["package"]["version"] = new_version
                print(f"  包版本已更新: {new_version}")
                return True
            else:
                print("  警告：未找到package字段或格式不正确")
                return False
        except Exception as e:
            print(f"  更新包版本失败: {e}")
            return False

    def extract_version_from_filename(self, filename):
        """从文件名提取版本号"""
        # 常见版本号模式
        patterns = [
            r"(\d{4})",  # 4位数字，如 4200
            r"(\d+\.\d+\.\d+)",  # 标准版本号，如 1.2.3
            r"(\d+\.\d+)",  # 两位版本号，如 1.2
            r"(\d+(?:\.\d+)+)",  # 任意位版本号
        ]

        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)

        return None

    def get_current_version_from_yaml(self, yaml_file):
        """从YAML文件中获取当前版本号"""
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = f.read()

            yaml_data = yaml.safe_load(content)
            sources = yaml_data.get("sources", [])

            if not sources:
                return None

            # 从第一个source的URL中提取版本号
            for source in sources:
                url = source.get("url", "")
                if url:
                    current_version = self.extract_version_from_filename(url)
                    if current_version:
                        return current_version

            return None
        except Exception as e:
            print(f"从{yaml_file}读取当前版本失败: {e}")
            return None

    def update_yaml_file(self, yaml_file, new_version):
        """更新YAML文件"""
        try:
            with open(yaml_file, "r", encoding="utf-8") as f:
                content = f.read()

            yaml_data = yaml.safe_load(content)
            sources = yaml_data.get("sources", [])

            if not sources:
                print(f"{yaml_file}中没有找到sources，跳过")
                return False

            # 查找并更新匹配的source
            updated = False
            for source in sources:
                name = source.get("name", "")
                url = source.get("url", "")

                if not name or not url:
                    continue

                # 提取当前版本号
                current_version = self.extract_version_from_filename(name)
                if not current_version:
                    continue

                # 检查架构
                arch = "amd64"
                if "arm64" in name or "aarch64" in name:
                    arch = "arm64"

                # 构建新的下载URL和文件名
                new_url = self.download_url_template.format(
                    version=new_version, arch=arch
                )
                new_name = name.replace(current_version, new_version)

                # 计算哈希值
                print(f"正在计算 {arch} 新版本的哈希值...")
                new_digest = self.calculate_sha256(new_url)
                if not new_digest:
                    continue

                # 更新source
                source["url"] = new_url
                source["digest"] = new_digest
                source["name"] = new_name

                updated = True
                print(f"  已更新 {arch} 架构的source条目")
                break

            if not updated:
                print("  没有找到可更新的source条目")
                return False

            # 更新package版本
            self.update_package_version(yaml_data, new_version)

            # 同步更新build字段中的文件名
            if updated and "build" in yaml_data and isinstance(yaml_data["build"], str):
                build_content = yaml_data["build"]
                # 直接使用新的name替换build字段中的文件名
                # 查找包含旧版本号的文件名模式
                old_filename_pattern = rf"{re.escape(name)}"
                updated_build = re.sub(old_filename_pattern, new_name, build_content)

                if updated_build != build_content:
                    yaml_data["build"] = updated_build
                    print(f"  build字段文件名已同步更新: {new_name}")

            # 保持YAML格式
            if "build" in yaml_data and isinstance(yaml_data["build"], str):
                yaml_data["build"] = literal_str(yaml_data["build"])

            # 写回文件
            updated_content = yaml.dump(
                yaml_data, allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            with open(yaml_file, "w", encoding="utf-8") as f:
                f.write(updated_content)

            print(f"已更新{yaml_file}")
            return True

        except Exception as e:
            print(f"更新{yaml_file}失败: {e}")
            return False

    def find_yaml_files(self):
        """自动查找YAML文件"""
        yaml_files = []

        # 查找主要的linglong.yaml
        if Path("linglong.yaml").exists():
            yaml_files.append("linglong.yaml")

        # 查找架构子目录中的YAML文件
        for arch_dir in ["amd64", "arm64", "sw64", "riscv64", "loong64", "mips64"]:
            arch_yaml = Path(arch_dir) / "linglong.yaml"
            if arch_yaml.exists():
                yaml_files.append(str(arch_yaml))

        return yaml_files

    def run(self):
        """运行更新检查"""
        print(f"开始检查 {self.app_name} 更新...")

        # 获取最新版本
        latest_version = self.fetch_latest_version()
        if not latest_version:
            print("无法获取最新版本，退出")
            return 1

        print(f"最新版本: {latest_version}")

        # 查找所有YAML文件
        yaml_files = self.find_yaml_files()
        if not yaml_files:
            print("未找到任何YAML文件，退出")
            return 1

        print(f"找到 {len(yaml_files)} 个YAML文件")

        # 检查当前版本是否与最新版本一致
        need_update = False
        for yaml_file in yaml_files:
            current_version = self.get_current_version_from_yaml(yaml_file)
            if current_version:
                print(f"{yaml_file} 当前版本: {current_version}")
                if current_version != latest_version:
                    need_update = True
            else:
                need_update = True

        # 如果不需要更新，直接返回
        if not need_update:
            print(f"所有文件当前版本与最新版本({latest_version})一致，无需更新")
            return 0

        # 更新每个YAML文件
        success_count = 0
        for yaml_file in yaml_files:
            print(f"\n处理 {yaml_file}...")
            if self.update_yaml_file(yaml_file, latest_version):
                success_count += 1

        if success_count > 0:
            print(f"\n更新完成！成功更新了 {success_count} 个文件。")
            # 只有在确实有更新时才输出true
            if "GITHUB_OUTPUT" in os.environ or os.environ.get("GITHUB_OUTPUT"):
                output_file = os.environ.get("GITHUB_OUTPUT", "/tmp/output.txt")
                with open(output_file, "a") as f:
                    f.write("has_changes=true\n")
            return 0
        else:
            print("\n所有文件更新失败！")
            return 1


def main():
    """主函数"""
    if len(sys.argv) != 2:
        print("用法: python3 update_checker.py <config_file.json>")
        print("\n配置示例:")
        print("{")
        print('  "app_name": "Sublime Text",')
        print('  "version_url": "https://www.sublimetext.com/download",')
        print('  "version_pattern": "Build\\\\s+(\\\\d{4})",')
        print(
            '  "download_url_template": "https://download.sublimetext.com/sublime-text_build-{version}_{arch}.deb"'
        )
        print("}")
        sys.exit(1)

    config_file = sys.argv[1]
    checker = UpdateChecker(config_file)
    sys.exit(checker.run())


if __name__ == "__main__":
    main()
