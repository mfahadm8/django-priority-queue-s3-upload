import argparse
import websocket
import json

def on_message(ws, message):
    print("Received:", message)

def on_error(ws, error):
    print("Error:", error)
    
def on_close(ws, close_status_code, close_msg):
    print(f"Connection closed. Status: {close_status_code}, Message: {close_msg}")

def on_open(ws):
    print(f"Connection established with GUID: {ws.guid}")
    ws.send(json.dumps({"guid": ws.guid}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='WebSocket Client')
    parser.add_argument('guid', type=str, help='GUID for the WebSocket connection')
    args = parser.parse_args()

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(f"ws://localhost:8001/ws/progress/{args.guid}/",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.guid = args.guid  # Assign guid to ws object for on_open function
    ws.run_forever()
