import pytest

from src.routing import load_config, route

CONFIG = load_config()


def test_complaint_high_confidence_auto_routes_to_customer_service():
    r = route("Complaint", 0.94, CONFIG)
    assert r["route_to"] == "Customer Service"
    assert r["action"] == "auto_route"


def test_contract_goes_to_legal():
    r = route("Contract", 0.90, CONFIG)
    assert r["route_to"] == "Legal"
    assert r["action"] == "auto_route"


def test_service_request_goes_to_it_operations():
    r = route("Service Request", 0.90, CONFIG)
    assert r["route_to"] == "IT / Operations"
    assert r["action"] == "auto_route"


def test_medium_confidence_needs_review():
    assert route("Complaint", 0.72, CONFIG)["action"] == "needs_review"


def test_low_confidence_is_manual():
    assert route("Contract", 0.40, CONFIG)["action"] == "manual"


@pytest.mark.parametrize(
    "conf, expected",
    [
        (0.85, "auto_route"),
        (0.8499, "needs_review"),
        (0.60, "needs_review"),
        (0.5999, "manual"),
    ],
)
def test_threshold_boundaries(conf, expected):
    assert route("Complaint", conf, CONFIG)["action"] == expected


def test_unknown_label_is_always_manual():
    r = route("Resume", 0.99, CONFIG)
    assert r["action"] == "manual"
    assert r["route_to"] == CONFIG["fallback_department"]