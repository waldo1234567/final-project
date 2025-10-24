import requests
import os
from discovery_client import discover_mdns, discover_via_manifest
import hashlib
from datetime import datetime, timedelta

MANIFEST_SERVER = "http://127.0.0.1:5001"
LOCAL_PEER_ID = os.environ.get("P2P_PEER_ID", "peer-demo")
LOCAL_PEER_PORT = os.environ.get("P2P_ENDPOINT", "8081")
HOST_IP = os.environ.get("HOST_IP", "127.0.0.1")

def compute_sha256_bytes(b):
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def register_local_cache(file_id, chunk_no, peer_id=LOCAL_PEER_ID, ttl_seconds=48*3600):
    endpoint = f"http://{HOST_IP}:{LOCAL_PEER_PORT}/chunk/{file_id}/{chunk_no}"
    expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat() + "Z"
    payload = {
        "chunk_number": int(chunk_no),
        "peer_replica": {
            "peer_id": peer_id,
            "endpoint": endpoint,
            "last_seen": datetime.utcnow().isoformat() + "Z",
            "ttl": expires_at
        }
    }
    try:
        r = requests.patch(f"{MANIFEST_SERVER}/manifest/{file_id}", json=payload, timeout=3)
        print("registered local cache:", r.status_code)
    except Exception as e:
        print("register_local_cache failed:", e)

def fetch_chunk_from_peer(endpoint):
    try:
        r = requests.get(endpoint, timeout=5) #TODO: auth token
        if r.status_code == 200:
            return r.content
        else:
            return None
    except requests.RequestException as e:
        print("Error fetching chunk from peer:", e)
        return None
    
def orchestrate_fetch(file_id, chunk_no, save_dir ="downloaded_chunks"):
    local_path = os.path.join(save_dir, f"{file_id}__chunk-{chunk_no}.bin")
    if os.path.exists(local_path):
        print("already local, local_path:", local_path)
        return local_path
    
    peers = discover_mdns(2)
    if not peers:
        #fallback
        peers = discover_via_manifest(file_id,manifest_server= MANIFEST_SERVER)
        
    #try peers
    for p in peers:
        endpoint = p.get("endpoint")
        if endpoint is None:
            continue
        
        ep = endpoint.rstrip('/')  # base endpoint from mdns or manifest
       
        if '/chunk/' in ep:
            ep_full = f"{ep}"
            # If the full path doesn't already include file & chunk, add them
            if not ep_full.endswith(f"/{file_id}/{chunk_no}") and not ep_full.endswith(f"/{chunk_no}"):
                # e.g. endpoint may be ".../chunk" or ".../chunk/"
                ep_full = ep_full.rstrip('/') + f"/{file_id}/{chunk_no}"
        else:
            # endpoint is base like http://IP:PORT -> construct chunk URL
            ep_full = ep + f"/chunk/{file_id}/{chunk_no}"

        print("trying peer", ep_full)
        try:
            r = requests.get(ep_full,timeout=6)
            if r.status_code != 200:
                print("peer returned", r.status_code)
                continue
        
            header_sha = r.headers.get("X-Chunk-SHA256")
            computed = compute_sha256_bytes(r.content)
            if header_sha and header_sha != computed:
                print("SHA mismatch from peer", ep_full, "header:", header_sha, "computed:", computed)
                continue
            os.makedirs(save_dir, exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(r.content)
            print("fetched from peer:", ep_full)
            # register this node as caching the chunk so others can discover it
            register_local_cache(file_id, chunk_no)
            return local_path
        except Exception as e:
            print("peer fetch error", e)
            continue
        
    print("No peers had chunk; fallback to S3 for file", file_id, chunk_no)
    return None

if __name__ == "__main__":
    file_id = "file-uuid"
    chunk_no = 0
    orchestrate_fetch(file_id, chunk_no)