"""统一配置管理：config.json + 兼容旧版 pet.json / current.json"""

import os
import json
import shutil
from pet.pet_manager import discover_pets, get_current_pet_id, set_current_pet_id, PetConfig

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

# ---- GIF 动作自动识别关键词 ----
ACTION_KEYWORDS = {
    "idle": ["idle", "stand", "normal", "default"],
    "talk": ["talk", "chat", "speak", "say"],
    "thinking": ["thinking", "think", "wait", "waiting", "loading", "process"],
    "sleep_start": ["sleep_0", "sleep_start", "sleeping_0"],
    "sleep_loop": ["sleep_1", "sleep_loop", "sleeping_1", "sleeping"],
    "walk": ["walk", "move", "run", "go"],
}

DEFAULT_CONFIG = {
    "current_pet": "feibi",
    "display": {
        "scale": 0.4,
        "topmost": True,
        "initial_x": 200,
        "initial_y": 200,
        "opacity": 1.0,
        "bg_mode": "transparent",  # "transparent" | "color"
        "bg_color": "#010101",     # 透明色键值
    },
    "llm": {
        "provider": "ollama",
        "base_url": "http://localhost:11434",
        "model": "qwen2.5:7b",
        "api_key": "",
        "temperature": 0.7,
    },
}


def load_config() -> dict:
    """加载统一配置，首次运行时从旧版配置迁移"""
    if os.path.isfile(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # 合并默认值（兼容新增字段）
            return _merge_defaults(cfg)
        except Exception:
            pass
    return _migrate_from_legacy()


def _merge_defaults(cfg: dict) -> dict:
    """深度合并默认值，确保新字段存在"""
    import copy
    result = copy.deepcopy(DEFAULT_CONFIG)
    _deep_merge(result, cfg)
    return result


def _deep_merge(base: dict, override: dict):
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _migrate_from_legacy() -> dict:
    """从旧版 pet/current.json 迁移"""
    cfg = dict(DEFAULT_CONFIG)
    pet_id = get_current_pet_id()
    cfg["current_pet"] = pet_id
    save_config(cfg)
    return cfg


def save_config(cfg: dict):
    """保存统一配置到 config.json"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        # 同步旧版 current.json（兼容）
        set_current_pet_id(cfg.get("current_pet", "feibi"))
    except Exception:
        pass


# ---- GIF 自动识别 ----
def auto_detect_gifs(folder: str) -> dict[str, str]:
    """扫描文件夹中的 GIF，自动按关键词分类。
    返回 {"idle": "idle.gif", "talk": "talk.gif", ...}
    """
    result = {}
    if not os.path.isdir(folder):
        return result

    gif_files = [f for f in os.listdir(folder)
                 if f.lower().endswith(".gif")]

    for gif_name in gif_files:
        name_lower = gif_name.lower()
        base_no_ext = os.path.splitext(name_lower)[0]

        for action, keywords in ACTION_KEYWORDS.items():
            for kw in keywords:
                if kw in base_no_ext:
                    if action not in result:
                        result[action] = gif_name
                    break

    # 如果只匹配到一个包含 sleep 关键词的 GIF，同时作为 sleep_start 和 sleep_loop
    if "sleep_loop" in result and "sleep_start" not in result:
        for kw in ["sleep_0", "sleep_start"]:
            for gif_name in gif_files:
                if kw in os.path.splitext(gif_name.lower())[0]:
                    result["sleep_start"] = gif_name
                    break
            if "sleep_start" in result:
                break

    if "sleep_start" in result and "sleep_loop" not in result:
        result["sleep_loop"] = result["sleep_start"]

    # 如果只有单独 sleep 关键词匹配到 sleep_loop 但没有 sleep_start
    if "sleep_loop" in result and "sleep_start" not in result:
        result["sleep_start"] = result["sleep_loop"]

    return result


# ---- 宠物导入 ----
def import_pet_from_folder(folder: str, pet_name: str = None) -> tuple[str, dict] | tuple[None, str]:
    """从素材文件夹导入宠物。
    folder: GIF 素材所在文件夹
    pet_name: 宠物名（默认用文件夹名）
    返回 (pet_id, gif_map) 或 (None, 错误信息)
    """
    if not os.path.isdir(folder):
        return None, f"文件夹不存在: {folder}"

    if pet_name is None:
        pet_name = os.path.basename(folder.rstrip("/\\"))

    gif_map = auto_detect_gifs(folder)
    if not gif_map:
        return None, "未检测到任何 GIF 文件"

    if "idle" not in gif_map:
        return None, "缺少 idle 动作的 GIF（文件名需包含 idle/stand/normal）"

    import re
    pet_id = re.sub(r'[^a-zA-Z0-9一-鿿_]', '', pet_name)
    if not pet_id:
        pet_id = "imported_pet"

    pet_dir = os.path.join(BASE_DIR, "pet", pet_id)
    if os.path.exists(pet_dir):
        # 如果已存在，追加数字后缀
        cnt = 1
        while os.path.exists(os.path.join(BASE_DIR, "pet", f"{pet_id}_{cnt}")):
            cnt += 1
        pet_id = f"{pet_id}_{cnt}"
        pet_dir = os.path.join(BASE_DIR, "pet", pet_id)

    os.makedirs(os.path.join(pet_dir, "sounds"), exist_ok=True)

    # 复制 GIF
    for action, filename in gif_map.items():
        src = os.path.join(folder, filename)
        dst = os.path.join(pet_dir, filename)
        if os.path.isfile(src):
            shutil.copy2(src, dst)

    # 生成 pet.json
    pet_json = {
        "name": pet_name,
        "prompt": f"你是桌面宠物{pet_name}。用简短活泼的语气回答。",
        "gifs": gif_map,
    }
    with open(os.path.join(pet_dir, "pet.json"), "w", encoding="utf-8") as f:
        json.dump(pet_json, f, ensure_ascii=False, indent=2)

    return pet_id, gif_map


def delete_pet(pet_id: str) -> bool:
    """删除宠物目录，返回是否成功"""
    pet_dir = os.path.join(BASE_DIR, "pet", pet_id)
    if not os.path.isdir(pet_dir):
        return False
    shutil.rmtree(pet_dir)
    return True


def get_available_pets() -> dict[str, PetConfig]:
    """重新发现宠物并返回"""
    return discover_pets()
