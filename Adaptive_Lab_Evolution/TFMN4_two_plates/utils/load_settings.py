import os
import json

_last_mtime = None
_config = {}

def try_reload_config(config_file):
    global _config, _last_mtime
    try:
        mtime = os.path.getmtime(config_file)
        if mtime != _last_mtime:
            with open(config_file) as f:
                new_config = json.load(f)
            _config = new_config
            _last_mtime = mtime
            print("Config updated.")
    except json.JSONDecodeError as e:
        print(f"Invalid config, keeping previous: {e}")
    except Exception as e:
        print(f"Could not read config: {e}")

    return _config

