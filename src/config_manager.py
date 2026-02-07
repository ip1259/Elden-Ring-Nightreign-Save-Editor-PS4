import orjson
import sys
from pathlib import Path
import os
import threading
from globals import get_system_language


def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).resolve().parent


CONFIG_FILE = os.path.join(get_base_dir(), "editor_config.json")


class ConfigManager:
    _instance = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance._config = cls._instance._load_config()
        return cls._instance

    def __init__(self):
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._initialized = True
                    self._config = self._load_config()
                    self.save()

    def _load_config(self):
        _config = {
            "last_file": "",
            "last_char_index": 0,
            "last_mode": None,
            "language": get_system_language(),
            "theme": "dark",
            "auto_backup": True,
            "max_backups": 5,
            "reduce_message_pop": True
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'rb') as f:
                    loaded_cofig = orjson.loads(f.read())
                    for key, value in loaded_cofig.items():
                        _config[key] = value
        except Exception:
            pass
        return _config

    def save(self):
        try:
            with open(CONFIG_FILE, 'wb') as f:
                f.write(orjson.dumps(self._config, option=orjson.OPT_INDENT_2))
        except Exception:
            pass

    @property
    def config(self):
        return self._config

    @property
    def last_file(self):
        return self._config["last_file"]

    @last_file.setter
    def last_file(self, value):
        with self._lock:
            self._config["last_file"] = value
            self.save()

    @property
    def last_char_index(self):
        return self._config["last_char_index"]

    @last_char_index.setter
    def last_char_index(self, value):
        with self._lock:
            self._config["last_char_index"] = value
            self.save()

    @property
    def language(self):
        return self._config["language"]

    @language.setter
    def language(self, value):
        with self._lock:
            self._config["language"] = value
            self.save()

    @property
    def theme(self):
        return self._config["theme"]

    @theme.setter
    def theme(self, value):
        with self._lock:
            self._config["theme"] = value
            self.save()

    @property
    def auto_backup(self):
        return self._config["auto_backup"]

    @auto_backup.setter
    def auto_backup(self, value):
        with self._lock:
            self._config["auto_backup"] = value
            self.save()

    @property
    def max_backups(self):
        return self._config["max_backups"]

    @max_backups.setter
    def max_backups(self, value):
        with self._lock:
            self._config["max_backups"] = value
            self.save()

    @property
    def reduce_message_pop(self):
        return self._config["reduce_message_pop"]

    @reduce_message_pop.setter
    def reduce_message_pop(self, value):
        with self._lock:
            self._config["reduce_message_pop"] = value
            self.save()

    @property
    def last_mode(self):
        return self._config["last_mode"]

    @last_mode.setter
    def last_mode(self, value):
        with self._lock:
            self._config["last_mode"] = value
            self.save()
