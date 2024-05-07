import asyncio
import logging
import sys
import time
import os
import json

import socket
import netifaces
from scapy.all import ARP, Ether, srp

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")

    sys.exit(1)

from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call

logging.basicConfig(level=logging.INFO)

class ChargePoint(cp):
    round_trip_times = []
    interval : int
    ip : str

    async def send_heartbeat(self, interval):
        request = call.HeartbeatPayload()
        while True:
            sent_time = time.time()
            await self.call(request)
            self.round_trip_times.append(time.time() - sent_time)
            await asyncio.sleep(interval)
            await self.write_key_performance_indicators()

    async def send_boot_notification(self):
        request = call.BootNotificationPayload(
            charging_station={"model": f"Wallbox {self.id}", "vendor_name": f"INESCTEC"},
            reason="PowerUp",
        )
        response = await self.call(request)

        if response.status == "Accepted":
            print("Connected to central system.")
            self.interval = response.interval
            await self.send_heartbeat(response.interval)

    async def write_key_performance_indicators(self):
        filename = "rtt_ocpp_messages.txt"
        if self.interval:
            data_hora = time.strftime('%Y-%m-%d %H:%M:%S')
            # Escrever os dados no arquivo
            results = {'Data hora':data_hora, 
                        'RTT': self.round_trip_times
                        }
            if os.path.exists(filename):
                mode = "a"  # If the file exists, open it in append mode
            else:
                mode = "w"  # If the file doesn't exist, open it in write mode
            with open(filename, mode) as arquivo:
                json.dump(results, arquivo)
                arquivo.write('\n')


def get_local_ip_address():
    # Get the IP address of the default network interface
    default_interface = netifaces.gateways()['default'][netifaces.AF_INET][1]
    local_ip = netifaces.ifaddresses(default_interface)[netifaces.AF_INET][0]['addr']
    # Modify the last octet of the IP address to '.0'
    local_ip_parts = local_ip.split('.')
    local_ip_parts[-1] = '0'
    local_network = '.'.join(local_ip_parts) + '/24'
    return local_network

def discover_devices_on_network(ip_range):
    arp = ARP(pdst=ip_range)
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    result = srp(packet, timeout=3, verbose=False)[0]
    
    devices = []
    for sent, received in result:
        devices.append({'ip': received.psrc, 'mac': received.hwsrc})
    devices.append({'ip': "localhost", 'mac': ""}) if len(devices) == 0 else None
    return devices

async def main(charger_id):
    local_network = get_local_ip_address() #Search for the local network base address
    devices_to_search = discover_devices_on_network(ip_range=local_network) # Discover the devices connected on the network
    csms_addr_index = 0
    while True:
        try:
            if csms_addr_index <= len(devices_to_search):
                print(csms_addr_index)
                print(len(devices_to_search))
                async with websockets.connect(
                    f"ws://{devices_to_search[csms_addr_index]['ip']}:9002/{charger_id}", subprotocols=["ocpp2.0.1"], ping_interval=None
                ) as ws:
                    charge_point = ChargePoint(f"{charger_id}", ws)
                    await asyncio.gather(
                        charge_point.start(), charge_point.send_boot_notification()
                    )
                csms_addr_index += 1
                await asyncio.sleep(5) #Espera 5 segundos caso o dispositivo não seja o CSMS
            else:
                csms_addr_index = 0
        except Exception as e:
            logging.error(f"Error trying to connect to CSMS on address: {str(e)}")
            devices_to_search = discover_devices_on_network(ip_range=local_network)
            await asyncio.sleep(6)
        

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <charging_point_id>")
        sys.exit(1)
    charging_point_id = sys.argv[1]
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main(charging_point_id))
