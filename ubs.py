#!/usr/bin/env python3
import argparse
import subprocess
import sys
import os
import json
from pathlib import Path
import re

# ============= КОНФИГУРАЦИЯ =============
CONFIG = {
    "APP_NAME": "PyNetSys",          # Название приложения
    "MAIN_SCRIPT": "main.py",        # Главный скрипт/файл для сборки
    "ICON_FILE": "icon.ico",         # Файл иконки (None если не нужен)
    "VERSION_FILE": "version.txt",   # Файл с версией
    "BUILD_DIR": "build",            # Директория для временных файлов
    "DIST_DIR": "dist",              # Директория для готовых билдов
    
    # Настройки версионирования
    "VERSION_MODULE": "version.py",  # Модуль для экспорта версии
    "CONFIG_MODULE": "config_data.py",# Модуль для конфига
    
    # Метаданные
    "AUTHOR": "Your Name",
    "DESCRIPTION": "App Description",
    "COMPANY": "Your Company",
    "COPYRIGHT": "Copyright © 2025",
    
    # Настройки языков
    "LANGUAGE": "python",            # python/cpp/rust/go (режимы сборки)
    "BUILD_COMMAND": {               # Команды сборки для разных языков
        "python": [
            "pyinstaller", "--onefile", "--name", "{exe_name}",
            "--distpath", "{dist_dir}", "--workpath", "{build_dir}",
            "--console", "{main_script}"
        ],
        "cpp": ["g++", "{main_script}", "-o", "{exe_name}"],
        "rust": ["cargo", "build", "--release"],
        "go": ["go", "build", "-o", "{exe_name}"]
    },
    
    # Дополнительные параметры
    "AUTO_VERSION_MODULE": True,     # Автоматически генерировать модуль версии
    "AUTO_CONFIG_MODULE": True,      # Автоматически генерировать конфиг
}
# ========= КОНЕЦ КОНФИГУРАЦИИ ==========

class VersionManager:
    def __init__(self, version_file):
        self.version_file = Path(version_file)
        if not self.version_file.exists():
            self.current_version = "1.0.0"
            self.save()
        else:
            self.current_version = self.version_file.read_text().strip()

    def save(self):
        self.version_file.write_text(self.current_version)

    def parse(self):
        clean = self.current_version.strip().lower().lstrip("v")
        m = re.match(r"^(\d+)\.(\d+)\.(\d+)$", clean)
        if not m:
            print(f"[!] Invalid version format: '{self.current_version}', resetting to 1.0.0")
            self.current_version = "1.0.0"
            self.save()
            return [1, 0, 0]
        return list(map(int, m.groups()))

    def bump(self, mode):
        major, minor, patch = self.parse()
        if mode == "major":
            self.current_version = f"{major+1}.0.0"
        elif mode == "minor":
            self.current_version = f"{major}.{minor+1}.0"
        elif mode == "patch":
            self.current_version = f"{major}.{minor}.{patch+1}"
        self.save()

    def set(self, v):
        if not re.match(r"^\d+\.\d+\.\d+$", v):
            raise ValueError("Invalid version format")
        self.current_version = v
        self.save()

class Builder:
    def __init__(self, config, version):
        self.config = config
        self.version = version
        self.project_dir = Path(__file__).parent
        
    def prepare_build(self):
        """Подготовка файлов перед сборкой"""
        # Генерация модуля версии
        if self.config["AUTO_VERSION_MODULE"]:
            version_path = self.project_dir / self.config["VERSION_MODULE"]
            version_path.write_text(f'__version__ = "{self.version}"\n')
            print(f"[+] Version embedded: {version_path}")

        # Генерация конфиг-модуля
        if self.config["AUTO_CONFIG_MODULE"]:
            config_path = self.project_dir / self.config["CONFIG_MODULE"]
            meta = {
                "author": self.config["AUTHOR"],
                "description": self.config["DESCRIPTION"],
                "company": self.config["COMPANY"],
                "copyright": self.config["COPYRIGHT"],
                "version": self.version
            }
            config_path.write_text("config = " + json.dumps(meta, indent=4) + "\n")
            print(f"[+] Config embedded: {config_path}")

    def build(self):
        """Запуск процесса сборки"""
        language = self.config["LANGUAGE"]
        build_cmd = self.config["BUILD_COMMAND"].get(language)
        
        if not build_cmd:
            raise ValueError(f"Unsupported language: {language}")
        
        # Создаем рабочие директории
        build_dir = self.project_dir / self.config["BUILD_DIR"]
        dist_dir = self.project_dir / self.config["DIST_DIR"]
        build_dir.mkdir(exist_ok=True)
        dist_dir.mkdir(exist_ok=True)
        
        # Форматируем команду сборки
        exe_name = f"{self.config['APP_NAME']}-v{self.version}"
        cmd = [
            part.format(
                exe_name=exe_name,
                main_script=self.config["MAIN_SCRIPT"],
                build_dir=build_dir,
                dist_dir=dist_dir,
                icon=self.config["ICON_FILE"]
            ) for part in build_cmd
        ]
        
        # Добавляем иконку для Python
        if language == "python" and self.config["ICON_FILE"]:
            cmd.insert(1, "--icon")
            cmd.insert(2, str(self.config["ICON_FILE"]))
        
        print(f"[>] Building {exe_name} ({language}): {' '.join(cmd)}")
        subprocess.run(cmd, check=True, cwd=self.project_dir)
        print(f"[✓] Build complete: {dist_dir / exe_name}")

def main():
    parser = argparse.ArgumentParser(description="Universal build system")
    version_group = parser.add_mutually_exclusive_group()
    version_group.add_argument("--major", action="store_true", help="Bump major version")
    version_group.add_argument("--minor", action="store_true", help="Bump minor version")
    version_group.add_argument("--patch", action="store_true", help="Bump patch version")
    version_group.add_argument("--set-version", metavar="X.Y.Z", help="Set specific version")
    
    args = parser.parse_args()
    vm = VersionManager(CONFIG["VERSION_FILE"])

    if args.set_version:
        vm.set(args.set_version)
    elif args.major:
        vm.bump("major")
    elif args.minor:
        vm.bump("minor")
    elif args.patch:
        vm.bump("patch")

    print(f"[>] Using version: {vm.current_version}")
    builder = Builder(CONFIG, vm.current_version)
    builder.prepare_build()
    builder.build()

if __name__ == "__main__":
    main()
