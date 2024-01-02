def cache_result(cache_key_function):
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_key = cache_key_function(*args, **kwargs)
            return global_cache.get_or_set(cache_key, lambda: func(*args, **kwargs))

        return wrapper

    return decorator


class Cache:
    def __init__(self):
        self.cache = {}

    def get_or_set(self, key: str, value_function):
        if key not in self.cache:
            self.cache[key] = value_function()

        return self.cache[key]


global_cache = Cache()
