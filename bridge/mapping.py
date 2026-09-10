"""Mapping definitions between DiGiCo Aux sends and DS100 parameters."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class Ds100ParamKind(str, Enum):
    ENSPACE_SEND = "enspace_send"
    FG_ROUTING = "fg_routing"


DIGICO_AUX_MAX = 48
FUNCTION_GROUP_MAX = 32


@dataclass
class MappingSpec:
    id: str
    digico_aux: int
    ds100_kind: str  # Ds100ParamKind value
    function_group: int | None = None

    def label(self) -> str:
        if self.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value:
            ds = "En-Space Send"
        elif self.ds100_kind == Ds100ParamKind.FG_ROUTING.value:
            ds = f"Function Group Routing {self.function_group}"
        else:
            ds = self.ds100_kind
        return f"DiGiCo Aux {self.digico_aux} → {ds}"

    def uses_mute_store(self) -> bool:
        """En-Space has no mute — Aux Off uses -120 store/restore."""
        return self.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value

    def validate(self) -> None:
        if not 1 <= self.digico_aux <= DIGICO_AUX_MAX:
            raise ValueError(f"DiGiCo Aux must be 1–{DIGICO_AUX_MAX}")
        if self.ds100_kind == Ds100ParamKind.ENSPACE_SEND.value:
            self.function_group = None
        elif self.ds100_kind == Ds100ParamKind.FG_ROUTING.value:
            if self.function_group is None or not 1 <= self.function_group <= FUNCTION_GROUP_MAX:
                raise ValueError(f"Function Group must be 1–{FUNCTION_GROUP_MAX}")
        else:
            raise ValueError(f"Unknown DS100 parameter: {self.ds100_kind}")


def new_mapping_id() -> str:
    return uuid.uuid4().hex[:10]


def default_mappings() -> list[MappingSpec]:
    return [
        MappingSpec(
            id=new_mapping_id(),
            digico_aux=1,
            ds100_kind=Ds100ParamKind.ENSPACE_SEND.value,
        )
    ]


def mapping_from_dict(data: dict[str, Any]) -> MappingSpec:
    m = MappingSpec(
        id=str(data.get("id") or new_mapping_id()),
        digico_aux=int(data["digico_aux"]),
        ds100_kind=str(data["ds100_kind"]),
        function_group=(
            int(data["function_group"])
            if data.get("function_group") not in (None, "", 0)
            else None
        ),
    )
    m.validate()
    return m


def mappings_to_dicts(mappings: list[MappingSpec]) -> list[dict[str, Any]]:
    return [asdict(m) for m in mappings]


def ds100_param_choices() -> list[dict[str, Any]]:
    choices = [{"id": Ds100ParamKind.ENSPACE_SEND.value, "label": "En-Space Send"}]
    for fg in range(1, FUNCTION_GROUP_MAX + 1):
        choices.append(
            {
                "id": f"fg_routing:{fg}",
                "label": f"Function Group Routing {fg}",
                "kind": Ds100ParamKind.FG_ROUTING.value,
                "function_group": fg,
            }
        )
    return choices
