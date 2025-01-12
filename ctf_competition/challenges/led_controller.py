# led_controller.py

import asyncio
from bleak import BleakClient

DEVICE_MAC = "BE:27:8B:03:4C:4B"
CHARACTERISTIC_UUID = "0000afd1-0000-1000-8000-00805f9b34fb"

def create_color_packet(r, g, b, brightness=100):
    return bytearray([0x5A, 0x00, 0x01, r, g, b, 0x00, brightness, 0x00, 0xA5])

COLOR_WHITE = create_color_packet(255, 255, 255)
COLOR_YELLOW = create_color_packet(255, 255, 0)
COLOR_OFF = create_color_packet(0, 0, 0, 0)  # optional: turn off
# ... any other colors you might need

def create_effect_packet(effect_id):
    return bytearray([0x5C, 0x00, effect_id, 0x64, 0x64, 0x00, 0xC5])

EFFECT_PROFILES = {
    "green_strobe": 0x91, 
    "red_strobe":   0x90,
}

async def connect_device(mac_address: str) -> BleakClient:
    client = BleakClient(mac_address)
    await client.connect()
    return client

async def reconnect_if_needed(client: BleakClient):
    if not client.is_connected:
        await client.disconnect()
        await asyncio.sleep(1)
        await client.connect()

async def set_color(client: BleakClient, color_command: bytearray):
    await reconnect_if_needed(client)
    await client.write_gatt_char(CHARACTERISTIC_UUID, color_command)

async def set_effect(client: BleakClient, effect_id: int):
    await reconnect_if_needed(client)
    effect_packet = create_effect_packet(effect_id)
    await client.write_gatt_char(CHARACTERISTIC_UUID, effect_packet)

# ---------------------------------------------------------------------
#            High-level functions to be called from views.py
# ---------------------------------------------------------------------
async def set_color_white():
    client = await connect_device(DEVICE_MAC)
    try:
        await set_color(client, COLOR_WHITE)
    finally:
        await client.disconnect()

async def set_color_yellow():
    client = await connect_device(DEVICE_MAC)
    try:
        await set_color(client, COLOR_YELLOW)
    finally:
        await client.disconnect()

async def blink_green_strobe():
    client = await connect_device(DEVICE_MAC)
    try:
        # Strobe green
        await set_effect(client, EFFECT_PROFILES["green_strobe"])
        # Wait 1 second
        await asyncio.sleep(1)
        # Go back to white
        await set_color(client, COLOR_WHITE)
    finally:
        await client.disconnect()

async def blink_red_strobe():
    client = await connect_device(DEVICE_MAC)
    try:
        # Strobe red
        await set_effect(client, EFFECT_PROFILES["red_strobe"])
        # Wait 1 second
        await asyncio.sleep(1)
        # Go back to white
        await set_color(client, COLOR_WHITE)
    finally:
        await client.disconnect()
