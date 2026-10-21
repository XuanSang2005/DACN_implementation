"""Contract error values and RFC 6901 pointers; no transport or persistence."""

from typing import Iterable, Literal, TypedDict

from .codec import JSONValue

type Stage = Literal["parse", "schema", "cross_field", "revision", "system"]
type Target = Literal["input", "request", "system"]
STAGES = ("parse", "schema", "cross_field", "revision", "system")


class Error(TypedDict):
    code: str
    stage: Stage
    target: Target
    pointer: str | None
    related_pointers: list[str]
    message: str
    details: dict[str, JSONValue]


def pointer(parts: Iterable[str | int]) -> str:
    return "".join("/" + str(part).replace("~", "~0").replace("/", "~1") for part in parts)


def error(code: str, stage: Stage, location: str | None, message: str,
          details: dict[str, JSONValue], *, target: Target = "input",
          related: Iterable[str] = ()) -> Error:
    return {"code": code, "stage": stage, "target": target, "pointer": location,
            "related_pointers": sorted(set(related)), "message": message, "details": details}


def error_key(value: Error) -> tuple:
    location = value["pointer"]
    return (STAGES.index(value["stage"]), location is not None, location or "",
            value["code"], value["target"])


def ordered_errors(values: Iterable[Error]) -> list[Error]:
    unique = {}
    for value in values:
        key = (value["stage"], value["target"], value["pointer"], value["code"])
        unique.setdefault(key, value)
    return sorted(unique.values(), key=error_key)
