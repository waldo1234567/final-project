import asyncio
import argparse
import os
import json
import hashlib
import threading
import time
from aiohttp import web
from zeroconf import ServiceInfo, Zeroconf
import requests
from datetime import datetime, timedelta

MANIFEST_SERVER = "http://127.0.0.1:5001"
SERVICE_TYPE = "_dfs-chunk._tcp.local."

def load_chunk_bytes(chunks_dir, file_id, chunk_number):
    fname = f"{file_id}__chunk-{chunk_number}.bin"
    path = os.path.join(chunks_dir, fname)
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()
    
async def handle_chunk(request):
    file_id = request.match_info['file_id']
    chunk_no = request.match_info['chunk_no']
    
    chunks_dir = request.app['chunks_dir']
    data = load_chunk_bytes(chunks_dir, file_id, chunk_no)
    fname = f"{file_id}__chunk-{chunk_no}.bin"
    path = os.path.join(chunks_dir, fname)
    if not os.path.exists(path):
        return web.Response(status=404, text="Chunk not found")
    
    with open(path, "rb") as f:
        data = f.read()
    sha256 = hashlib.sha256(data).hexdigest()
    headers ={
        "X-Chunk-SHA256": sha256,  # TODO: compute sha256 here
        "X-Chunk-Size": str(len(data))
    }
    return web.Response(body=data, headers=headers)

def register_manifest(file_id, chunk_no, peer_id, endpoint, ttl_seconds=48 * 3600):
    url = f"{MANIFEST_SERVER}/manifest/{file_id}"
    expires = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat() + "Z"
    payload = {
        "chunk_number": int(chunk_no),
        "peer_replica": {
            "peer_id": peer_id,
            "endpoint": endpoint,
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "ttl": expires
        } 
    }
    try:
        response = requests.patch(url, json=payload, timeout=5)
        print("manifest register:", response.status_code, response.text)
    except requests.RequestException as e:
        print("manifest register failed:", e)

def manifest_heartbeat(file_id, chunk_no, peer_id, endpoint, interval_sec = 1000):
    while True:
        try:
            register_manifest(file_id, chunk_no, peer_id, endpoint)
        except Exception as e:
            print("heartbeat error:", e)    
        time.sleep(interval_sec)
        
def start_mdns(name, port, peer_id, endpoint):
    desc={'peer_id': peer_id, 'endpoint': endpoint}
    info=ServiceInfo(
        SERVICE_TYPE,
        f"{name}.{SERVICE_TYPE}",
        addresses=[b"\x7f\x00\x00\x01"],
        port=port,
        properties=desc,
    )   
    
    zer = Zeroconf()
    zer.register_service(info)
    print(f"Registered mDNS service {name} on port {port}")
    return zer, info

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks-dir", required=True)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--peer-id", default="peer-local")
    parser.add_argument("--name", default="peer-node")
    args = parser.parse_args()
    
    app = web.Application()
    app.router.add_get('/chunk/{file_id}/{chunk_no}', handle_chunk)
    app['chunks_dir'] = args.chunks_dir
    
    #mdns
    endpoint = f"http://{os.environ.get('HOST_IP', '127.0.0.1')}:{args.port}"
    zer, info = start_mdns(args.name, args.port, args.peer_id, endpoint)
    
    runner = web.AppRunner(app)
    loop = asyncio.get_event_loop()
    async def start_server():
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', args.port)
        await site.start()
        print('server running ...')
        
        for fname in os.listdir(args.chunks_dir):
            if fname.endswith(".bin") and "__chunk-" in fname:
                parts = fname.split("__chunk-")
                file_id = parts[0]
                chunk_no = parts[1].split(".bin")[0]
                chunk_endpoint = f"{endpoint}/chunk/{file_id}/{chunk_no}"
                t = threading.Thread(target=register_manifest,
                             args=(file_id, chunk_no, args.peer_id, chunk_endpoint))
                t.daemon = True
                t.start()
                hb = threading.Thread(target=manifest_heartbeat, args=(file_id, chunk_no, args.peer_id, chunk_endpoint, 1000))
                hb.daemon = True
                hb.start()
                # Also register initially via asyncio to avoid delay
                asyncio.get_event_loop().run_in_executor(None, register_manifest, file_id, chunk_no, args.peer_id, f"{endpoint}/chunk/{file_id}/{chunk_no}")
        while True:
            await asyncio.sleep(3600)
            
    try:
        loop.run_until_complete(start_server())
    except KeyboardInterrupt:           
        print("Shutting down...")
    finally:
        zer.unregister_service(info)
        zer.close()