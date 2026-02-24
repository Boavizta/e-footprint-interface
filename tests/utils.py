from pathlib import Path

test_rootdir = Path(__file__).parent

def assert_dicts_equal(json1, json2, path=""):
    """
    Recursively asserts that two JSON-like Python structures are equal,
    ignoring dictionary key order and list element order.

    Raises an AssertionError if a mismatch is found.
    """
    if type(json1) != type(json2):
        raise AssertionError(f"Type mismatch at {path or 'root'}: {type(json1).__name__} != {type(json2).__name__}")

    if isinstance(json1, dict):
        keys1 = set(json1.keys())
        keys2 = set(json2.keys())
        if keys1 != keys2:
            raise AssertionError(f"Key mismatch at {path or 'root'}: {keys1} != {keys2}")
        for key in keys1:
            assert_dicts_equal(json1[key], json2[key], path + f".{key}")
    elif isinstance(json1, list):
        unmatched = list(json2)
        for i, item1 in enumerate(json1):
            for j, item2 in enumerate(unmatched):
                try:
                    assert_dicts_equal(item1, item2, path + f"[{i}]")
                    unmatched.pop(j)
                    break
                except AssertionError:
                    continue
            else:
                raise AssertionError(f"No match found for list element at {path}[{i}]: {item1}")
        if unmatched:
            raise AssertionError(f"Extra elements in second list at {path}: {unmatched}")
    else:
        if json1 != json2:
            raise AssertionError(f"Value mismatch at {path or 'root'}: {json1} != {json2}")
