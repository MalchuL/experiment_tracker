from app.infrastructure.cache.utils.pattern_matcher import PatternMatcher


def test_translate_glob_to_regex():
    assert PatternMatcher.translate_glob_to_regex("*") == "^.*$"
    assert PatternMatcher.translate_glob_to_regex("?") == "^.$"


def tests_concrete_pattern():
    r = PatternMatcher()
    assert r.matches_redis_pattern(
        "scalars_cache:123:456:max_points=100:return_tags=1", "scalars_cache:*"
    )
    assert r.matches_redis_pattern(
        "scalars_cache:123:456:max_points=100:return_tags=1", "scalars_cache:123:*"
    )
    assert r.matches_redis_pattern(
        "scalars_cache:123:456:max_points=100:return_tags=1", "scalars_cache:123:456:*"
    )
    assert r.matches_redis_pattern(
        "scalars_cache:123:456:max_points=100:return_tags=1",
        "scalars_cache:123:456:max_points=100:return_tags=1",
    )
    assert r.matches_redis_pattern(
        "scalars_cache:123:456:max_points=100:return_tags=1",
        "scalars_cache:123:456:max_points=100:return_tags=1",
    )
    assert r.matches_redis_pattern(
        "project:11000118-b179-4e8a-ba4e-edb6c5108e79.experiments.123",
        "project:11000118-b179-4e8a-ba4e-edb6c5108e79.*",
    )
    assert not r.matches_redis_pattern(
        "project:11000118-b179-4e8a-ba4e-edb6c5108e79.experiments.123",
        "project:11000118-b179-4e8a-ba4e-edb6c5108e79.experiments.123.456",
    )
    assert r.matches_redis_pattern(
        "project:11000118-b179-4e8a-ba4e-edb6c5108e79:experiments",
        "project:*:experiments",
    )
