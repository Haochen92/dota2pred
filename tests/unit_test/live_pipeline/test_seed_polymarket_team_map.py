from live_orchestrator_app.scripts.seed_polymarket_team_map import _norm, _slugify


def test_norm_canonicalizes_for_matching() -> None:
    assert _norm("  Team   Spirit ") == "team spirit"
    assert _norm("Zero-Tenacity") == "zero tenacity"
    assert _norm("VP.Prodigy") == "vp.prodigy"  # punctuation other than -/_ is kept
    assert _norm(None) == ""


def test_slugify_matches_polymarket_style() -> None:
    assert _slugify("Zero Tenacity") == "zero-tenacity"
    assert _slugify("VP.Prodigy") == "vp-prodigy"
    assert _slugify("Nande+4") == "nande-4"
    assert _slugify("  Ilbirs eSports  ") == "ilbirs-esports"
