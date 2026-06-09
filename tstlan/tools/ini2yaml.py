import argparse
import configparser
import re
import sys
from pathlib import Path
from typing import Any

import yaml

from tstlan.configs.schemas import (
    ConfigPayload,
    ConfigVar,
    ConnectionSettings,
    ModbusMap,
    Transport,
)
from tstlan.models import NetVarCType

_TYPE_ALIASES = {"float": "f32", "double": "f64"}


def _map_transport(raw: str) -> Transport:
    value = raw.lower()
    if "modbus" in value:
        return "modbus_udp" if "udp" in value else "modbus_tcp"
    if "gpib" in value:
        return "gpib"
    if "com" in value:
        return "com"
    return "ethernet"


def _map_ctype(raw: str) -> NetVarCType:
    value = raw.strip().lower()
    return NetVarCType(_TYPE_ALIASES.get(value, value))


def _as_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except ValueError:
        return None


def _apply_device_param(
    label: str,
    value: str,
    conn: ConnectionSettings,
    modbus: ModbusMap,
    params: dict[str, str],
) -> None:
    text = label.lower()
    number = _as_int(value)
    if "запрос" in text and "ip" in text:
        conn.ip_request = value
    elif text == "ip" or "ip адрес" in text or ("ip" in text and "адрес" in text):
        conn.ip = value
    elif "порт" in text or text == "port":
        conn.port = number
    elif "обновлен" in text or "измерен" in text:
        if number is not None:
            conn.poll_period_ms = number
    elif "discret" in text:
        modbus.discrete_inputs_bytes = number or 0
    elif "coils" in text:
        modbus.coils_bytes = number or 0
    elif "holding" in text:
        modbus.holding_registers = number or 0
    elif "input registers" in text:
        modbus.input_registers = number or 0
    elif "gpib" in text:
        conn.gpib_addr = number
    elif "com name" in text or text == "com":
        conn.com_name = value
    else:
        params[label] = value


def _parse_connection(device: configparser.SectionProxy) -> ConnectionSettings:
    conn = ConnectionSettings(transport=_map_transport(device.get("type", "")))
    modbus = ModbusMap()
    params: dict[str, str] = {}
    index = 1
    while f"key{index}" in device:
        label = device.get(f"key{index}", "").strip()
        value = device.get(f"value{index}", "").strip()
        if label:
            _apply_device_param(label, value, conn, modbus, params)
        index += 1
    if conn.transport.startswith("modbus") or modbus != ModbusMap():
        conn.modbus = modbus
    conn.params = params
    return conn


def _parse_variables(section: configparser.SectionProxy) -> list[ConfigVar]:
    # `_N` в .ini - лишь номер строки и задаёт порядок; смещение выводится из
    # типа, поэтому сам номер отбрасывается.
    indices = sorted(
        int(match.group(1))
        for key in section
        if (match := re.fullmatch(r"name_(\d+)", key))
    )
    variables: list[ConfigVar] = []
    for index in indices:
        name = section.get(f"name_{index}", "").strip()
        if not name:
            continue
        variables.append(
            ConfigVar(
                name=name,
                ctype=_map_ctype(section.get(f"type_{index}", "")),
                graph=section.get(f"graph_{index}", "0").strip() in ("1", "true"),
                category=section.get(f"category_{index}", "").strip(),
            )
        )
    return variables


def convert(text: str, name: str) -> dict[str, Any]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read_string(text)
    connection = _parse_connection(parser["device"])
    variables = _parse_variables(parser["vars"]) if parser.has_section("vars") else []
    payload = ConfigPayload(connection=connection, variables=variables)
    return {
        "name": name,
        "device_type": name,
        "payload": payload.model_dump(mode="json", exclude_none=True),
    }


def convert_file(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="cp1251")
    return convert(text, path.stem)


def dump_yaml(data: dict[str, Any]) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="ini2yaml", description="Конвертер конфига TSTLAN .ini -> YAML"
    )
    parser.add_argument("input", type=Path, help="путь к .ini (cp1251)")
    parser.add_argument(
        "-o", "--output", type=Path, help="файл YAML (по умолчанию stdout)"
    )
    args = parser.parse_args(argv)

    yaml_text = dump_yaml(convert_file(args.input))
    if args.output is None:
        sys.stdout.write(yaml_text)
    else:
        args.output.write_text(yaml_text, encoding="utf-8")


if __name__ == "__main__":
    main()
