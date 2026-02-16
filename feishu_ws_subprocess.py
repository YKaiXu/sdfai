#!/usr/bin/env python3
"""
Feishu WebSocket Standalone Script
Run as subprocess to avoid event loop conflicts
"""
import sys
import json
import os

APP_ID = sys.argv[1] if len(sys.argv) > 1 else ""
APP_SECRET = sys.argv[2] if len(sys.argv) > 2 else ""
ENCRYPT_KEY = sys.argv[3] if len(sys.argv) > 3 else ""
VERIFICATION_TOKEN = sys.argv[4] if len(sys.argv) > 4 else ""

import lark_oapi as lark

def on_message_sync(data):
    """Sync handler for incoming messages"""
    try:
        event = data.event
        message = event.message
        sender = event.sender
        
        if sender.sender_type == "bot":
            return
        
        message_id = message.message_id
        sender_id = sender.sender_id.open_id if sender.sender_id else "unknown"
        chat_id = message.chat_id
        chat_type = message.chat_type
        msg_type = message.message_type
        
        if msg_type == "text":
            try:
                content = json.loads(message.content).get("text", "")
            except:
                content = message.content or ""
        else:
            content = f"[{msg_type}]"
        
        if not content:
            return
        
        reply_to = chat_id if chat_type == "group" else sender_id
        
        output = json.dumps({
            "type": "message",
            "sender_id": sender_id,
            "chat_id": reply_to,
            "content": content,
            "message_id": message_id
        }, ensure_ascii=False)
        
        sys.stdout.write(output + "\n")
        sys.stdout.flush()
        
    except Exception as e:
        output = json.dumps({"type": "error", "error": str(e)}, ensure_ascii=False)
        sys.stdout.write(output + "\n")
        sys.stdout.flush()

def main():
    sys.stdout.write(json.dumps({"type": "status", "status": "starting"}) + "\n")
    sys.stdout.flush()
    
    event_handler = lark.EventDispatcherHandler.builder(
        ENCRYPT_KEY, VERIFICATION_TOKEN
    ).register_p2_im_message_receive_v1(on_message_sync).build()
    
    ws_client = lark.ws.Client(
        APP_ID,
        APP_SECRET,
        event_handler=event_handler,
        log_level=lark.LogLevel.ERROR
    )
    
    sys.stdout.write(json.dumps({"type": "status", "status": "connected"}) + "\n")
    sys.stdout.flush()
    
    ws_client.start()

if __name__ == "__main__":
    main()
