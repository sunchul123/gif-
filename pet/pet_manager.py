"""宠物形象管理模块

负责发现宠物配置、读写当前选择、提供 PetConfig 数据类。
"""

import os
import json
import random

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CURRENT_FILE = os.path.join(_BASE_DIR, "current.json")


class PetConfig:
    """单个宠物的配置数据"""

    def __init__(self, pet_id: str, data: dict, base_path: str):
        self.id = pet_id
        self.name = data.get("name", pet_id)
        self.prompt = data.get("prompt", "")
        self.path = base_path
        self.sounds_dir = os.path.join(base_path, "sounds")
        self._raw_gifs = data.get("gifs", {})
        self.gif_files = {}  # 规范化为 {action: [filename, ...]}
        self._resolve_gifs()
        # 自定义动作: {"action_name": {"gif": "xxx.gif", "loop": true}}
        raw_custom = data.get("custom_actions", {})
        self.custom_actions = {}
        for aname, acfg in raw_custom.items():
            if isinstance(acfg, dict):
                gif_val = acfg.get("gif", "")
                self.custom_actions[aname] = {
                    "gif": gif_val,
                    "loop": acfg.get("loop", True),
                }
                if gif_val and aname not in self.gif_files:
                    self.gif_files[aname] = [gif_val] if isinstance(gif_val, str) else list(gif_val)

    def _resolve_gifs(self):
        """规范化 gif_files：字符串→列表，过滤不存在的文件"""
        for key, val in self._raw_gifs.items():
            if isinstance(val, list):
                files = [v for v in val if isinstance(v, str)]
            elif isinstance(val, str):
                files = [val]
            else:
                continue
            existing = [f for f in files if os.path.isfile(os.path.join(self.path, f))]
            if existing:
                self.gif_files[key] = existing

    def get_gif_path(self, gif_key: str) -> str | None:
        """返回 GIF 路径（多文件时随机选择，每次启动固定一次）"""
        filenames = self.gif_files.get(gif_key)
        if not filenames:
            return None
        filename = random.choice(filenames)
        p = os.path.join(self.path, filename)
        return p if os.path.isfile(p) else None

    def get_gif_display(self, gif_key: str) -> str:
        """返回用于 UI 显示的 GIF 文件名（逗号分隔）"""
        filenames = self.gif_files.get(gif_key, [])
        return ", ".join(filenames) if filenames else ""

    def get_sound_files(self) -> list[str]:
        """返回该宠物 sounds/ 目录下所有音频文件路径"""
        if not os.path.isdir(self.sounds_dir):
            return []
        return [
            os.path.join(self.sounds_dir, f)
            for f in os.listdir(self.sounds_dir)
            if f.lower().endswith((".mp3", ".wav"))
        ]


def discover_pets() -> dict[str, PetConfig]:
    """扫描 pet/ 目录，返回 {pet_id: PetConfig}"""
    pets: dict[str, PetConfig] = {}
    if not os.path.isdir(_BASE_DIR):
        return pets
    for name in os.listdir(_BASE_DIR):
        pet_dir = os.path.join(_BASE_DIR, name)
        if not os.path.isdir(pet_dir):
            continue
        json_path = os.path.join(pet_dir, "pet.json")
        if not os.path.isfile(json_path):
            continue
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            pets[name] = PetConfig(name, data, pet_dir)
        except Exception:
            continue
    return pets


def get_current_pet_id() -> str:
    """从 current.json 读取当前宠物 ID"""
    try:
        with open(CURRENT_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d.get("pet_id", "feibi")
    except (FileNotFoundError, json.JSONDecodeError):
        return "feibi"


def set_current_pet_id(pet_id: str):
    """将当前宠物 ID 写入 current.json"""
    try:
        with open(CURRENT_FILE, "w", encoding="utf-8") as f:
            json.dump({"pet_id": pet_id}, f, ensure_ascii=False)
    except Exception:
        pass
