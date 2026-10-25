from app.rules import flag_value, parse_reference_range
from tools.generate_reports import generate_report


def test_generator_is_reproducible():
    _, a = generate_report(seed=7)
    _, b = generate_report(seed=7)
    assert a == b


def test_ground_truth_flags_match_rule_engine():
    for seed in range(30):
        _, truth = generate_report(seed=seed, degrade_image=False)
        for row in truth["rows"]:
            low, high = parse_reference_range(row["reference_range"])
            assert row["expected_flag"] == flag_value(row["value"], low, high)


def test_dataset_contains_abnormal_and_normal_rows():
    flags = {r["expected_flag"] for s in range(30) for r in generate_report(s, degrade_image=False)[1]["rows"]}
    assert {"low", "normal", "high"} <= flags


def test_all_layouts_render_images():
    for layout in ("grid", "compact", "range_first"):
        img, truth = generate_report(seed=1, layout=layout)
        assert img.size[0] > 1000 and truth["layout"] == layout
