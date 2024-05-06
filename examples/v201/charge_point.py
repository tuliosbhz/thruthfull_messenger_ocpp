import asyncio
import logging
import sys
import time
import os
import json
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



async def main(charger_id):
    async with websockets.connect(
        f"ws://localhost:9002/{charger_id}", subprotocols=["ocpp2.0.1"], ping_interval=None
    ) as ws:
        charge_point = ChargePoint(f"{charger_id}", ws)
        await asyncio.gather(
            charge_point.start(), charge_point.send_boot_notification()
        )

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <charging_point_id>")
        sys.exit(1)
    charging_point_id = sys.argv[1]
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main(charging_point_id))
