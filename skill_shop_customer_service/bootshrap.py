import time
import importlib

_module_cache = {}
MODULE_TTL = 120


def dynamic_import(mod_name: str):
    now = time.time()
    if mod_name in _module_cache:
        obj, stamp = _module_cache[mod_name]
        if now - stamp < MODULE_TTL:
            return obj
    mod = importlib.import_module(mod_name)
    _module_cache[mod_name] = (mod, now)
    return mod