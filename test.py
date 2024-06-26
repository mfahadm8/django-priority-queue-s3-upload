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
    print(f"Connection established with GUIDs: {ws.guids}")
    for guid in ws.guids:
        ws.send(json.dumps({"guid": guid, "action": "add"}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='WebSocket Client')
    parser.add_argument('guids', type=str, help='Comma-separated list of GUIDs for the WebSocket connection')
    args = parser.parse_args()

    guids = args.guids.split(",")
    guids_json = json.dumps(guids)  # Convert the list of GUIDs to a JSON string

    websocket.enableTrace(True)
    ws = websocket.WebSocketApp(f"ws://localhost:8001/ws/progress",
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.on_open = on_open
    ws.guids = guids  # Assign guids to ws object for on_open function
    ws.run_forever()
