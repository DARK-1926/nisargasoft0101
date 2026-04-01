from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LocationProfile:
    code: str
    city: str
    state: str
    pin_code: str
    x_forwarded_for: str


LOCATION_PROFILES: dict[str, LocationProfile] = {
    "chennai-tn": LocationProfile("chennai-tn", "Chennai", "Tamil Nadu", "600001", "117.240.0.1"),
    "mumbai-mh": LocationProfile("mumbai-mh", "Mumbai", "Maharashtra", "400001", "49.32.0.1"),
    "bengaluru-ka": LocationProfile("bengaluru-ka", "Bengaluru", "Karnataka", "560001", "106.51.0.1"),
    "delhi-dl": LocationProfile("delhi-dl", "Delhi", "Delhi", "110001", "49.36.0.1"),
    "hyderabad-ts": LocationProfile("hyderabad-ts", "Hyderabad", "Telangana", "500001", "183.82.0.1"),
}


def resolve_location(code: str) -> LocationProfile:
    return LOCATION_PROFILES.get(code, LOCATION_PROFILES["chennai-tn"])


def resolve_locations(codes: list[str]) -> list[LocationProfile]:
    return [resolve_location(code) for code in codes]
