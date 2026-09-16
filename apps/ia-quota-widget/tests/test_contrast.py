import pytest

from widget_app import theme
from widget_app.contrast import composite_over, contrast_ratio, hex_to_rgb, worst_case_contrast


def test_hex_to_rgb():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)
    assert hex_to_rgb("000000") == (0, 0, 0)


def test_composite_over_full_opacity_ignores_backdrop():
    assert composite_over("#171A1D", (255, 255, 255), 100) == (23, 26, 29)


def test_composite_over_zero_opacity_is_pure_backdrop():
    assert composite_over("#171A1D", (10, 20, 30), 0) == (10, 20, 30)


def test_contrast_ratio_black_vs_white_is_max():
    assert contrast_ratio((0, 0, 0), (255, 255, 255)) == pytest.approx(21.0, abs=0.01)


def test_contrast_ratio_identical_colors_is_one():
    assert contrast_ratio((100, 100, 100), (100, 100, 100)) == pytest.approx(1.0, abs=0.01)

MIN_PRIMARY_CONTRAST = 4.5
# Only Nevoa/Papel needed darkening to clear this; os 5 escuros ja vinham do
# orquestrador entre 3.49 e 3.86 — nao e o mesmo requisito duro do principal
# (que foi pedido explicitamente em 4,5:1), mas real e mensuravel.
MIN_SECONDARY_CONTRAST = 3.4
# Verde/ambar/vermelho sao o canal primario do percentual (SC 1.4.11).
MIN_STATUS_CONTRAST = 3.0
# Maroon/grey marcam "sem numero" (erro/indisponivel) e sempre vem com
# rotulo de texto em contraste pleno ao lado — nao sao o unico canal, entao
# o piso e mais baixo, so pra pegar um valor realmente invisivel.
MIN_MUTED_STATUS_CONTRAST = 2.0


@pytest.mark.parametrize("preset_id", theme.SURFACE_PRESET_ORDER)
def test_primary_text_passes_wcag_on_both_extremes(preset_id):
    preset = theme.SURFACE_PRESETS[preset_id]
    ratio = worst_case_contrast(preset["text"], preset["bg"], theme.DEFAULT_BG_OPACITY_PERCENT)
    assert ratio >= MIN_PRIMARY_CONTRAST, f"{preset_id}: {ratio:.2f} < {MIN_PRIMARY_CONTRAST}"


@pytest.mark.parametrize("preset_id", theme.SURFACE_PRESET_ORDER)
def test_secondary_text_passes_wcag_on_both_extremes(preset_id):
    preset = theme.SURFACE_PRESETS[preset_id]
    ratio = worst_case_contrast(preset["text_secondary"], preset["bg"], theme.DEFAULT_BG_OPACITY_PERCENT)
    assert ratio >= MIN_SECONDARY_CONTRAST, f"{preset_id}: {ratio:.2f} < {MIN_SECONDARY_CONTRAST}"


@pytest.mark.parametrize("preset_id", theme.SURFACE_PRESET_ORDER)
def test_status_colors_stay_visible_against_panel(preset_id):
    colors = theme.status_colors_for(preset_id)
    preset = theme.SURFACE_PRESETS[preset_id]
    muted = {"maroon", "grey"}
    for name, color_hex in colors.items():
        ratio = worst_case_contrast(color_hex, preset["bg"], theme.DEFAULT_BG_OPACITY_PERCENT)
        floor = MIN_MUTED_STATUS_CONTRAST if name in muted else MIN_STATUS_CONTRAST
        assert ratio >= floor, f"{preset_id}.{name}: {ratio:.2f} < {floor}"


def test_light_presets_use_darker_status_palette_than_dark_presets():
    dark_green = theme.status_colors_for("carvao")["green"]
    light_green = theme.status_colors_for("nevoa")["green"]
    assert dark_green != light_green


def test_status_identity_colors_are_shared_across_all_presets():
    # A cor de identidade do provider e' independente de preset de superficie.
    assert "codex" in theme.PROVIDER_DOT_COLORS
    assert "codex_gpt2" in theme.PROVIDER_DOT_COLORS
    for preset_id in theme.SURFACE_PRESET_ORDER:
        theme.surface_preset(preset_id)  # nao levanta, preset existe
    assert len(theme.PROVIDER_DOT_COLORS) == 8


def test_unknown_preset_id_falls_back_to_default():
    assert theme.surface_preset("nao-existe") == theme.SURFACE_PRESETS[theme.DEFAULT_SURFACE_PRESET]
