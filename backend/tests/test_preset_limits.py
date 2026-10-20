from app.schemas import (
    NEGATIVE_STYLE_LIMIT,
    STYLE_TEXT_LIMIT,
    PresetCreate,
    PresetUpdate,
    _style_length,
)


def test_negative_prompt_is_trimmed_to_limit():
    preset = PresetCreate(name="a", genre="rock", negative_style_prompt="n" * 2500)
    assert len(preset.negative_style_prompt) == NEGATIVE_STYLE_LIMIT


def test_short_fields_are_not_changed():
    preset = PresetCreate(
        name="a", genre="rock", style_prompt="warm", negative_style_prompt="no autotune"
    )
    assert preset.style_prompt == "warm"
    assert preset.negative_style_prompt == "no autotune"


def test_style_text_is_fitted_to_limit_trimming_description_first():
    preset = PresetCreate(
        name="a", genre="rock", style_prompt="s" * 900, description="d" * 500
    )
    assert preset.style_prompt == "s" * 900
    assert len(preset.description) < 500
    assert _style_length(preset.model_dump()) <= STYLE_TEXT_LIMIT


def test_style_text_limit_holds_for_many_long_fields():
    long = "x" * 800
    preset = PresetCreate(
        name="a",
        genre="rock",
        bpm_min=90,
        bpm_max=110,
        energy=0.5,
        style_prompt=long,
        sound_scene=long,
        hooks_prompt=long,
        effects_prompt=long,
        chorus_vocal_style=long,
        description=long,
    )
    assert _style_length(preset.model_dump()) <= STYLE_TEXT_LIMIT


def test_update_schema_applies_limits():
    update = PresetUpdate(negative_style_prompt="n" * 1500)
    assert len(update.negative_style_prompt) == NEGATIVE_STYLE_LIMIT
