from tstlan.tools.ini2yaml import convert

SAMPLE = """[device]
type=modbus udp
key1=IP
value1=192.168.55.55
key2=Порт
value2=35123
key3=Запрос на получение IP
value3=device_get_ip
key4=Время обновления, мс
value4=200
key5=Биты, только чтение (Discret inputs), байт
value5=0
key6=Биты, чтение/запись (Coils), байт
value6=0
key7=Регистры, чтение/запись (Holding Registers), кол-во
value7=76
key8=Регистры, только чтение (Input Registers), кол-во
value8=0

[vars]
Name_0=some name 1
Type_0=bit
Graph_0=0
Category_0=
Name_34=some name 3
Type_34=u32
Graph_34=1
Category_34=Измерения
Name_36=some name 5
Type_36=float
Graph_36=0
Category_36=
"""


def test_convert_maps_modbus_connection() -> None:
    conn = convert(SAMPLE, "dev")["payload"]["connection"]
    assert conn["transport"] == "modbus_udp"
    assert conn["ip"] == "192.168.55.55"
    assert conn["port"] == 35123
    assert conn["ip_request"] == "device_get_ip"
    assert conn["poll_period_ms"] == 200
    assert conn["modbus"]["holding_registers"] == 76


def test_convert_preserves_variable_index_and_maps_types() -> None:
    variables = convert(SAMPLE, "dev")["payload"]["variables"]
    by_index = {var["index"]: var for var in variables}
    assert [var["index"] for var in variables] == [0, 34, 36]
    assert by_index[0]["ctype"] == "bit"
    assert by_index[36]["ctype"] == "f32"
    assert by_index[34]["graph"] is True
    assert by_index[34]["category"] == "Измерения"


def test_convert_names_config_from_argument() -> None:
    result = convert(SAMPLE, "Прибор")
    assert result["name"] == "Прибор"
    assert result["device_type"] == "Прибор"
