import re


class PatternMatcher:

    @staticmethod
    def translate_glob_to_regex(redis_pattern: str) -> str:
        pattern = redis_pattern
        pattern = pattern.replace(".", "\\.")
        pattern = pattern.replace("*", ".*")
        pattern = pattern.replace("?", ".")
        return f"^{pattern}$"

    @staticmethod
    def matches_redis_pattern(key: str, redis_pattern: str) -> bool:
        regex = PatternMatcher.translate_glob_to_regex(redis_pattern)
        return bool(re.match(regex, key))
