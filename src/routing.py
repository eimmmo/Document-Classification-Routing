from pathlib import Path

import yaml

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "configs" / "routing.yaml"


def load_config(path=DEFAULT_CONFIG) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_action(confidence: float, config: dict) -> str:
    t = config["thresholds"]
    if confidence >= t["auto_route"]:
        return "auto_route"
    if confidence >= t["needs_review"]:
        return "needs_review"
    return "manual"


def route(label: str, confidence: float, config: dict = None) -> dict:
    config = config or load_config()
    department = config["routes"].get(label, config["fallback_department"])
    action = get_action(confidence, config)
    if label not in config["routes"]:
        action = "manual"
    return {
        "document_type": label,
        "confidence": round(float(confidence), 4),
        "route_to": department,
        "action": action,
    }


if __name__ == "__main__":
    print(route("Complaint", 0.94))
    print(route("Contract", 0.72))
    print(route("Complaint", 0.40))