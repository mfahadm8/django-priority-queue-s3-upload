import websocket
import json

def on_message(ws, message):
    print("Received:", message)

def on_error(ws, error):
    print("Error:", error)
    
def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed. Status: {close_status_code}, Message: {close_msg}")

def on_open(ws):
    print("Connection established")
    # Sending a message containing the guid to query the file upload status and progress
    ws.send(json.dumps({"guid": "dummy_file.zip"}))

if __name__ == "__main__":
    websocket.enableTrace(True)
    ws = websocket.WebSocketApp("ws://localhost:8001/ws/progress/",
                                on_message = on_message,
                                on_error = on_error,
                                on_close = on_close)
    ws.on_open = on_open
    ws.run_forever()
