import asyncio
import logging
from struct import unpack_from, pack
from io import BytesIO
from functools import reduce
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


def _checksum_byte(buffer):
    return reduce(lambda lrc, x: (lrc + x) & 255, buffer) & 255


def _extract_data(buffer):
    return {
        "inverter_serial_number":           buffer[32:48].decode("ascii").rstrip(),
        "inverter_temperature":             0.1 * unpack_from("<H", buffer, 48)[0],   # ºC
        "dc_voltage_1":                     0.1 * unpack_from("<H", buffer, 50)[0],   # V
        "dc_voltage_2":                     0.1 * unpack_from("<H", buffer, 52)[0],   # V
        "dc_current_1":                     0.1 * unpack_from("<H", buffer, 54)[0],   # A
        "dc_current_2":                     0.1 * unpack_from("<H", buffer, 56)[0],   # A
        "unknown_3":                        int(unpack_from("<I", buffer, 58)[0]),    # ???
        "solar_ac_current":                 0.1 * unpack_from("<H", buffer, 62)[0],   # A
        "unknown_4":                        int(unpack_from("<I", buffer, 64)[0]),    # ???
        "ac_voltage":                       0.1 * unpack_from("<H", buffer, 68)[0],   # V
        "ac_frequency":                     0.01 * unpack_from("<H", buffer, 70)[0],  # Hz
        "solar_active_power":               int(unpack_from("<I", buffer, 72)[0]),    # W
        "solar_active_energy_today":        0.01 * unpack_from("<I", buffer, 76)[0],  # kWh
        "unknown_6":                        int(unpack_from("<L", buffer, 80)[0]),    # ??? Power generated this month (x 0.1)?
        # 88 - 107 ???
        "unknown_7":                        int(unpack_from("<I", buffer, 108)[0]),   # ???
        "unknown_8":                        int(unpack_from("<I", buffer, 112)[0]),   # ??? # or maybe 2 fields of 16 bits?
        "dc_power":                         int(unpack_from("<I", buffer, 116)[0]),   # W
        "solar_active_energy_this_month":   int(unpack_from("<L", buffer, 120)[0]),   # kWh
        "solar_active_energy_yesterday":    0.1 * unpack_from("<H", buffer, 128)[0],  # kWh
        "solar_active_energy_total":        int(unpack_from("<L", buffer, 130)[0]),   # kWh
        "unknown_10":                       int(unpack_from("<H", buffer, 138)[0]),   # ???
        "unknown_11":                       int(unpack_from("<H", buffer, 140)[0]),   # ???
        "solar_apparent_power":             int(unpack_from("<I", buffer, 142)[0]),   # W
        "unknown_12":                       int(unpack_from("<H", buffer, 146)[0]),   # ???
        "unknown_13":                       int(unpack_from("<H", buffer, 148)[0]),   # ???
        "unknown_14":                       int(unpack_from("<H", buffer, 150)[0]),   # ???
        "unknown_15":                       int(unpack_from("<H", buffer, 152)[0]),   # ???
        "unknown_16":                       int(unpack_from("<H", buffer, 154)[0]),   # ???
        "unknown_17":                       int(unpack_from("<H", buffer, 156)[0]),   # ???
        "unknown_18":                       int(unpack_from("<H", buffer, 158)[0]),   # ???
        "unknown_19":                       int(unpack_from("<H", buffer, 160)[0]),   # ???
        "unknown_19":                       int(unpack_from("<I", buffer, 162)[0]),   # ???
        "unknown_20":                       int(unpack_from("<H", buffer, 166)[0]),   # ???
        "unknown_21":                       int(unpack_from("<H", buffer, 168)[0]),   # ???
        "unknown_22":                       int(unpack_from("<H", buffer, 170)[0]),   # ???
        "unknown_22":                       int(unpack_from("<H", buffer, 172)[0]),   # ???
        "unknown_22":                       int(unpack_from("<L", buffer, 174)[0]),   # ???
        "export_active_power":              int(unpack_from("<i", buffer, 182)[0]),   # ??? equals 194 and it is signed
        "unknown_24":                       int(unpack_from("<L", buffer, 186)[0]),   # ???
        "export_active_power_b":            int(unpack_from("<i", buffer, 194)[0]),   # ??? equals 182 and it is signed
        "unknown_25":                       int(unpack_from("<I", buffer, 198)[0]),   # ??? equals 210
        "unknown_26":                       int(unpack_from("<L", buffer, 202)[0]),   # ???
        "unknown_25b":                      int(unpack_from("<I", buffer, 198)[0]),   # ??? equals 198
        "load_apparent_power":              int(unpack_from("<I", buffer, 214)[0]),   # ??? equals 226
        "unknown_27":                       int(unpack_from("<L", buffer, 218)[0]),   # ???
        "load_apparent_power_b":            int(unpack_from("<I", buffer, 226)[0]),   # ??? equals 214
        # 230 - 237 ???
        "unknown_28":                       int(unpack_from("<I", buffer, 238)[0]),   # ???
    }


def _mock_server_response(data):
    unix_time = int(datetime.utcnow().timestamp())
    mode = data[4] - 0x30
    buffer = BytesIO()

    buffer.write(b'\xa5\n\x00\x10')  # header
    buffer.write(pack("<B", mode))  # mode
    buffer.write(pack("<B", 0))  # clock
    buffer.write(data[6:12])  # prefix
    buffer.write(b'\x01')  # prefix
    buffer.write(pack("<I", unix_time))  # unix_time
    buffer.write(b'\x78\x00\x00\x00')
    checksum_data = buffer.getvalue()
    buffer.write(pack("<B", _checksum_byte(checksum_data[1:])))
    buffer.write(b'\x15')

    return buffer.getvalue()


class LoggerServer:
    def __init__(self, port: int, on_data: callable):
        self.port = port
        self.on_data = on_data

    async def _handle_connection(self, reader, writer):
        data = await reader.read(2048)
        if len(data) == 0:
            return
        addr = writer.get_extra_info('peername')
        response = _mock_server_response(data)
        writer.write(response)
        writer.close()
        # Convert data to dict and pass to on_data
        if data[4] == 0x42:
            # _LOGGER.error(' '.join(format(x, '02x') for x in data))
            self.on_data(_extract_data(data))

    async def start_server(self):
        self.server = await asyncio.start_server(self._handle_connection, '0.0.0.0', self.port)

    async def stop_server(self):
        self.server.close()
        await self.server.wait_closed()
