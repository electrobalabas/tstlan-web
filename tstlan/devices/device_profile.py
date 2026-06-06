from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from tstlan.devices.models import Device, DeviceStatus
from tstlan.models import NetVar, NetVarCType, NetVarMode


@dataclass
class DeviceProfile:
    name: str
    device_type: str
    variables: list[NetVar]
    # сырые спеки сигналов по имени переменной; их разбирает сторона прибора
    signals: dict[str, dict[str, Any]]


def load_profile(path: Path) -> DeviceProfile:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    variables: list[NetVar] = []
    signals: dict[str, dict[str, Any]] = {}
    for raw in data["variables"]:
        signal = raw.get("signal")
        variables.append(
            NetVar(
                raw["name"],
                NetVarCType(raw["ctype"]),
                _mode(raw.get("mode"), signal),
                value=raw.get("initial", 0),
            )
        )
        if signal is not None:
            signals[raw["name"]] = signal
    return DeviceProfile(
        name=data["name"],
        device_type=data.get("device_type", "Эмулятор"),
        variables=variables,
        signals=signals,
    )


def device_from_profile(profile: DeviceProfile, device_id: str) -> Device:
    return Device(
        id=device_id,
        name=profile.name,
        type=profile.device_type,
        enabled=True,
        status=DeviceStatus.OK,
        variables=profile.variables,
    )


def _mode(raw_mode: str | None, signal: dict[str, Any] | None) -> NetVarMode:
    if raw_mode is not None:
        return NetVarMode(raw_mode)
    # переменная с сигналом по умолчанию только на чтение (сенсор)
    return NetVarMode.R if signal is not None else NetVarMode.RW
