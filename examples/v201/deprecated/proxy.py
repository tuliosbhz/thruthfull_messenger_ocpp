import asyncio
import logging
from datetime import datetime

try:
    import websockets
except ModuleNotFoundError:
    print("This example relies on the 'websockets' package.")
    print("Please install it by running: ")
    print()
    print(" $ pip install websockets")
    import sys

    sys.exit(1)

from ocpp.routing import on
from ocpp.v201 import ChargePoint as cp
from ocpp.v201 import call_result
from ocpp.v201 import call

logging.basicConfig(level=logging.INFO)


class ChargePointProxy(cp):
    '''
    Classe que irá escutar mensagens do charge point e irá replicá-las para o CSMS
    '''

    def __init__(self, id, connection, response_timeout=30):
        super().__init__(id, connection, response_timeout)
        self.client_class = cp(id, connection)

    async def connection_with_csms(self, charger_id):
        """
        Try to stablish a connection with a CSMS
        """
        # Check if charger_id is on cp_ids
        # The id of the csms should help to find
        async with websockets.connect(
            f"ws://localhost:9002/{charger_id}", subprotocols=["ocpp2.0.1"], ping_interval=None
        ) as ws:
            #Cria uma classe em forma de replica que estabelece uma conexão com CSMS
            self.client_class = cp(charger_id, ws)
            logging.info(f"PROXY_CLIENT: New CSMS connection {self.client_class}")
            #Replicate the connection received to connect to the CSMS with the same websockets path
            await self.client_class.start()
    
    @on("BootNotification")
    async def on_boot_notification(self, charging_station, reason, **kwargs):
        '''
        Criar o pedido replicado para enviar para o CSMS ou processar e responder
        Buscar o path do pedido realizado ou o id do cliente
        Utilizar o id do cliente para utilizar a função call com o mesmo dado do cliente recebido
        '''
        
        replicated_request = call.BootNotificationPayload(
                                charging_station=charging_station,
                                reason=reason,
                                )
        await asyncio.sleep(1) #Wait to make sure that the connection with CSMS is stablished
        #The request should comes from a copy of the charge point class from the ChargePoint
        print(f"PROXY -> Replicated Request: {replicated_request}")
        csms_response = await self.client_class.call(replicated_request)
        print(f"PROXY -> Response CSMS: {csms_response}")
        return csms_response

    @on("Heartbeat")
    async def on_heartbeat(self):
        replicated_request = call.HeartbeatPayload()
        print(f"PROXY -> Replicated Request: {replicated_request}")
        csms_response = await self.client_class.call(replicated_request)
        print(f"PROXY -> Response CSMS: {csms_response}")
        call_result.HeartbeatPayload(csms_response)
        return csms_response

class ProxyHandler():
    id = "P001"
    cp_ids = []
    csms_ids = []

    async def on_charge_point_connect(self, websocket, path):
        """For every new charge point that connects, create a ChargePoint
        instance and start listening for messages.
        """
        try:
            requested_protocols = websocket.request_headers["Sec-WebSocket-Protocol"]
        except KeyError:
            logging.error("Client hasn't requested any Subprotocol. Closing Connection")
            return await websocket.close()
        if websocket.subprotocol:
            logging.info("Protocols Matched: %s", websocket.subprotocol)
        else:
            # In the websockets lib if no subprotocols are supported by the
            # client and the server, it proceeds without a subprotocol,
            # so we have to manually close the connection.
            logging.warning(
                "Protocols Mismatched | Expected Subprotocols: %s,"
                " but client supports %s | Closing connection",
                websocket.available_subprotocols,
                requested_protocols,
            )
            return await websocket.close()
        
        logging.info(f"PROXY_SERVER: New charge point connection {path}")
        #Get the charge point id from the websockets path created
        charge_point_id = path.strip("/")
        #Add to the proxy handler to register the connections stablished
        self.cp_ids.append(charge_point_id)
        logging.info(f"PROXY_SERVER: CP IDS {self.cp_ids}")

        #The proxy_server class listen for client messages, the chargepoints
        proxy_server = ChargePointProxy(charge_point_id, websocket)
        #As a client replicate the connection received from the CP with the CSMS
        proxy_to_csms_connection = asyncio.create_task(proxy_server.connection_with_csms(charge_point_id))
        proxy_to_cp_connection = asyncio.create_task(proxy_server.start())
        
        await proxy_to_cp_connection
        await proxy_to_csms_connection
        
        #await asyncio.gather(proxy_server.start(), proxy_server.client_class.start())

async def main():
    #  deepcode ignore BindToAllNetworkInterfaces: <Example Purposes>
    '''
    Instantiation of the ProxyHandler class responsible for managing the connections
    '''
    proxy_ocpp = ProxyHandler()
    proxy_ocpp.cp_ids.append(proxy_ocpp.id)
    
    '''
    The server is to receive new connections and handle them
    '''
    server = await websockets.serve(
        proxy_ocpp.on_charge_point_connect, "0.0.0.0", 9000, subprotocols=["ocpp2.0.1"], ping_interval=None
    )
    logging.info("Server Started listening to new connections...")
    await server.wait_closed()


if __name__ == "__main__":
    # asyncio.run() is used when running this example with Python >= 3.7v
    asyncio.run(main())
