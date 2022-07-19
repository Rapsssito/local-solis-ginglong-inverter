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
        "inverter_temperature":             0.1 * unpack_from("<H", buffer, 48)[0],
        "dc_voltage_pv1":                   0.1 * unpack_from("<H", buffer, 50)[0],  # could also be 52
        "dc_current":                       0.1 * unpack_from("<H", buffer, 54)[0],
        "ac_current_t_w_c":                 0.1 * unpack_from("<H", buffer, 62)[0],
        "ac_voltage_t_w_c":                 0.1 * unpack_from("<H", buffer, 68)[0],
        "ac_output_frequency":              0.01 * unpack_from("<H", buffer, 70)[0],
        "daily_active_generation":          0.01 * unpack_from("<H", buffer, 76)[0],
        "total_dc_input_power":             float(unpack_from("<I", buffer, 116)[0]),
        "total_active_generation":          float(unpack_from("<I", buffer, 120)[0]),  # or 130
        "generation_yesterday":             0.1 * unpack_from("<H", buffer, 128)[0],
        "power_grid_total_apparent_power":  float(unpack_from("<I", buffer, 142)[0]),
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
    buffer.write(pack("<B", checksum_byte(checksum_data[1:])))
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
        _LOGGER.error("Received %r from %r" % (data, addr))
        response = _mock_server_response(data)
        writer.write(response)
        _LOGGER.error("Send: %r" % response)
        writer.close()
        # Convert data to dict and pass to on_data
        self.on_data(_extract_data(data))

    async def start_server(self):
        self.server = await asyncio.start_server(self._handle_connection, '0.0.0.0', self.port)
        _LOGGER.error(f"Server started at port {self.port}")

    async def stop_server(self):
        self.server.close()
        await self.server.wait_closed()
        _LOGGER.error(f"Server stopped at port {self.port}")
