import pytest
from web3_utils.cache import Cache, cache_result


@pytest.fixture
def global_cache():
    return Cache()


@pytest.mark.parametrize(
    "initial_cache_data",
    [
        ({"key1": "value1", "key2": "value2"}),
        ({}),
    ],
)
def test_cache_get_or_set(global_cache, initial_cache_data):
    global_cache.cache = initial_cache_data

    key = "test_key"
    value_function = lambda: 42
    result = global_cache.get_or_set(key, value_function)

    assert result == initial_cache_data.get(key, 42)
    assert global_cache.cache[key] == initial_cache_data.get(key, 42)


def test_cache_invalidate_key(global_cache):
    key = "test_key"
    global_cache.cache[key] = 42
    global_cache.invalidate(key)

    assert key not in global_cache.cache


def test_cache_invalidate_all(global_cache):
    global_cache.cache["key1"] = 1
    global_cache.cache["key2"] = 2
    global_cache.invalidate()

    assert len(global_cache.cache) == 0


def test_cache_result_decorator(global_cache):
    @cache_result(global_cache, cache_key_function=lambda x: "key")
    def dummy_function():
        return 42

    result1 = dummy_function()
    result2 = dummy_function()

    assert result1 == result2
    assert "key" in global_cache.cache


def test_cache_result_decorator_with_different_arguments(global_cache):
    @cache_result(global_cache, cache_key_function=lambda x, y: f"key_{x}_{y}")
    def dummy_function(x, y):
        return x + y

    result1 = dummy_function(1, 2)
    result2 = dummy_function(2, 3)

    assert result1 != result2
    assert "key_1_2" in global_cache.cache
    assert "key_2_3" in global_cache.cache


def test_cache_result_decorator_with_invalidation(global_cache):
    @cache_result(global_cache, cache_key_function=lambda x: "key")
    def dummy_function():
        return 42

    result1 = dummy_function()
    global_cache.invalidate("key")
    result2 = dummy_function()

    assert result1 != result2
    assert "key" not in global_cache.cache
