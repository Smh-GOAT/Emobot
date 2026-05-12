from agent_core.llm_client import GPT
from connect import BluetoothClient


if __name__ == '__main__':
    blt = BluetoothClient()
    llm = GPT()
    llm.connect()
    # print(llm.chat("who are you?"))
    # devices = blt.list_devices()
    # if devices:
    #     device_address = devices[0]
    #     blt.connect(device_address)
    #     while True:
    #         question = input('Type command (type "exit" to exit): ')
    #         if question == 'exit':
    #             blt.disconnect()
    #             break
    #         response = llm.chat(question)
    #         blt.send(response)
    # else:
    #     print("No devices found.")
