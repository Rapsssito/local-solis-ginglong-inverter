"""
Fake server for Solis inverter communication.

This server listens for incoming connections and responds with mock data.
It is designed to simulate the behavior of a Solis server so that the inverter can send data to it.

Adapted from the original code by @planetmarshall
and https://github.com/planetmarshall/solis-service/pull/8.
"""

import asyncio
import datetime
import logging
from functools import reduce
from struct import pack, unpack_from
from typing import Any

_LOGGER = logging.getLogger(__name__)
# Protocol constants
HEARTBEAT_REQUEST = 0x41
DATA_REQUEST = 0x42
START_BYTE = 0xA5
END_BYTE = 0x15


def _checksum_byte(buffer: bytes) -> int:
    return reduce(lambda lrc, x: (lrc + x) & 255, buffer) & 255


def _extract_data(buffer: bytes) -> dict[str, int | float | str]:
    return {
        # "clock": unpack_from("<B", buffer, 5)[0],  # Clock from heartbeat
        "timestamp": unpack_from("<I", buffer, 22)[0],  # Unix timestamp
        "inverter_serial_number": buffer[32:48].decode("ascii").rstrip(),
        "inverter_temperature": 0.1 * unpack_from("<H", buffer, 48)[0],  # ºC
        "dc_voltage_1": 0.1 * unpack_from("<H", buffer, 50)[0],  # V
        "dc_voltage_2": 0.1 * unpack_from("<H", buffer, 52)[0],  # V
        "dc_current_1": 0.1 * unpack_from("<H", buffer, 54)[0],  # A
        "dc_current_2": 0.1 * unpack_from("<H", buffer, 56)[0],  # A
        # "unknown_3": int(unpack_from("<I", buffer, 58)[0]),  # ???
        "solar_ac_current": 0.1 * unpack_from("<H", buffer, 62)[0],  # A
        # "unknown_4": int(unpack_from("<I", buffer, 64)[0]),  # ???
        "ac_voltage": 0.1 * unpack_from("<H", buffer, 68)[0],  # V
        "ac_frequency": 0.01 * unpack_from("<H", buffer, 70)[0],  # Hz
        "solar_active_power": int(unpack_from("<I", buffer, 72)[0]),  # W
        "solar_active_energy_today": 0.01 * unpack_from("<I", buffer, 76)[0],  # kWh
        # "unknown_6": int(unpack_from("<L", buffer, 80)[0]),  # ??? Power generated this month (x 0.1)?
        # 88 - 107 ???
        # "unknown_7": int(unpack_from("<I", buffer, 108)[0]),  # ???
        # "unknown_8": int(unpack_from("<I", buffer, 112)[0]),  # ??? # or maybe 2 fields of 16 bits?
        "dc_power": int(unpack_from("<I", buffer, 116)[0]),  # W
        "solar_active_energy_this_month": int(unpack_from("<L", buffer, 120)[0]),  # kWh
        "solar_active_energy_yesterday": 0.1 * unpack_from("<H", buffer, 128)[0],  # kWh
        "solar_active_energy_total": int(unpack_from("<L", buffer, 130)[0]),  # kWh
        # "unknown_10": int(unpack_from("<H", buffer, 138)[0]),  # ???
        # "unknown_11": int(unpack_from("<H", buffer, 140)[0]),  # ???
        "solar_apparent_power": int(unpack_from("<I", buffer, 142)[0]),  # W
        # 146 - 181 ???
        "export_active_power": int(unpack_from("<i", buffer, 182)[0]),  # ??? equals 194 and it is signed
        # "unknown_12": int(unpack_from("<L", buffer, 186)[0]),  # ???
        # "export_active_power_b": int(unpack_from("<i", buffer, 194)[0]),  # ??? equals 182 and it is signed
        # "unknown_13": int(unpack_from("<I", buffer, 198)[0]),  # ??? equals 210
        # "unknown_14": int(unpack_from("<L", buffer, 202)[0]),  # ???
        # "unknown_13b": int(unpack_from("<I", buffer, 198)[0]),  # ??? equals 198
        "load_apparent_power": int(unpack_from("<I", buffer, 214)[0]),  # ??? equals 226
        # "unknown_15": int(unpack_from("<L", buffer, 218)[0]),  # ???
        # "load_apparent_power_b": int(unpack_from("<I", buffer, 226)[0]),  # ??? equals 214
        # 230 - 237 ???
        # "unknown_16": int(unpack_from("<I", buffer, 238)[0]),  # ???
    }


def _parse_header(msghdr: bytes) -> dict[str, int]:
    [payload_length, msg_type, resp_idx, req_idx, serialno] = unpack_from("<xHxBBBI", msghdr, 0)
    return {
        "payload_length": payload_length,
        "msg_type": msg_type,
        "resp_idx": resp_idx,
        "req_idx": req_idx,
        "serialno": serialno,
    }


def _mock_server_response(header: dict[str, int], request_payload: bytes) -> bytes:
    unix_time = int(datetime.datetime.now(tz=datetime.UTC).timestamp())

    payload = pack("<BBIBBBB", request_payload[0], 0x01, unix_time, 0xAA, 0xAA, 0x00, 0x00)
    # Don't know what 0xaa, 0xaa, 0x00, 0x00, but it is always there and seems to not matter the exact two first bytes

    resp_type = header["msg_type"] - 0x30
    # Don't know what the second byte means (0x10)
    header = pack(
        "<BHBBBBI", START_BYTE, len(payload), 0x10, resp_type, header["req_idx"], header["req_idx"], header["serialno"]
    )
    message = header + payload
    message += pack("BB", _checksum_byte(message[1:]), END_BYTE)
    return message


def _is_heartbeat(data: bytes) -> bool:
    """Check if the data is a heartbeat message."""
    return data[4] == HEARTBEAT_REQUEST


def _is_data_message(data: bytes) -> bool:
    """Check if the data is a data message."""
    return data[4] == DATA_REQUEST


class LoggerServer:
    """Fake server for Solis inverter communication."""

    def __init__(self, port: int, on_data: callable, *, forward: bool = False) -> None:
        """Initialize the server."""
        self.port = port
        self.on_data = on_data
        self.server = None
        self.forward = forward

    async def __handle_forward(self, addr: Any, message: bytes) -> bytes | None:
        """Forward the data to the real server."""
        _LOGGER.debug(f"Forwarding request to real server for {addr}")
        try:
            server_reader, server_writer = await asyncio.open_connection("47.88.8.200", 10000)
            server_writer.write(message)
            await server_writer.drain()
            server_data = await server_reader.read(2048)
            server_writer.close()
        except (ConnectionRefusedError, TimeoutError, OSError) as e:
            _LOGGER.exception("Connection error with real server", exc_info=e)
            return None
        if len(server_data) == 0:
            return None
        # Send the response back to the client
        _LOGGER.debug(f"Got response from real server for {addr}")
        return server_data

    async def __handle_fake(self, addr: Any, msg_header: dict[str, int], message: bytes) -> bytes:
        """Handle the data with the fake server."""
        _LOGGER.debug(f"Handling request with fake server for {addr}")
        return _mock_server_response(msg_header, message)

    async def __handle_persistence(self, addr: Any, message: bytes) -> None:
        # It is better to handle all the communications before calling on_data
        if _is_heartbeat(message):
            # Handle heartbeat message
            _LOGGER.debug(f"Received HEARTBEAT message from {addr}")
            # No data to extract, just log the heartbeat
            return
        if _is_data_message(message):
            # Read and extract data from the message
            data_extracted = _extract_data(message)
            _LOGGER.debug(f"Received DATA message from {addr}: {data_extracted}")
            if data_extracted["timestamp"] == 0:
                _LOGGER.debug("Timestamp is 0, this is likely an old message, ignoring it")
                return
            self.on_data(data_extracted)
            return
        _LOGGER.debug(f"Received UNKNOWN message from {addr}")

    async def __handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        while True:
            msghdr = await reader.readexactly(11)
            header = _parse_header(msghdr)
            payload_plus_footer = await reader.readexactly(header["payload_length"] + 2)
            message = msghdr + payload_plus_footer
            addr = writer.get_extra_info("peername")
            _LOGGER.debug(f"Received message from {addr}: {' '.join(format(x, '02x') for x in message)}")
            if message[0] != START_BYTE or message[-1] != END_BYTE or message[-2] != _checksum_byte(message[1:-2]):
                _LOGGER.warning(f"Invalid message from {addr}, ignoring it")
                break
            if self.forward:
                # Forward the data to the real server
                response = await self.__handle_forward(addr, message)
                if response is None:
                    _LOGGER.warning(f"Failed to forward data to real server for {addr}, falling back to fake server")
                    response = await self.__handle_fake(addr, header, message)
            else:
                # Handle the data with the fake server
                response = await self.__handle_fake(header, message)
            # Send the response back to the client
            writer.write(response)
            _LOGGER.debug(f"Sent response to {addr}: {' '.join(format(x, '02x') for x in response)}")
            # Handle persistence of the data
            await self.__handle_persistence(addr, message)
        # Close the connection
        writer.close()

    async def start_server(self) -> None:
        """Start the server and listen for incoming connections."""
        if self.server is not None:
            return
        # Create a server that listens on the specified port
        self.server = await asyncio.start_server(self.__handle_connection, "0.0.0.0", self.port)  # noqa: S104
        _LOGGER.debug(f"Server listening on port {self.port}")

    async def stop_server(self) -> None:
        """Stop the server and close all connections."""
        if self.server is None:
            return
        # Wait for all connections to close
        self.server.close()
        try:
            await self.server.wait_closed()
        except asyncio.CancelledError:
            _LOGGER.warning("Server shutdown cancelled")
        finally:
            self.server = None
            _LOGGER.debug("Server stopped")
