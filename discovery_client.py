from zeroconf import ServiceBrowser, Zeroconf
import time
import requests

SERVICE_TYPE = "_dfs-chunk._tcp.local."

class PeerListener:
    def __init__(self):
        self.peers = {}
        
    def remove_service(self, zeroconf, type, name):
        self.peers.pop(name, None)
        
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if info is None:
            return
        props = {k.decode(): v.decode() for k, v in info.properties.items()}
        endpoint = props.get('endpoint')
        peer_id = props.get('peer_id')
        self.peers[name] = {"peer_id": peer_id, "endpoint": endpoint}
        
def discover_mdns(timeout=5):
    zer = Zeroconf()
    listener = PeerListener()
    browser = ServiceBrowser(zer, SERVICE_TYPE, listener)
    time.sleep(timeout)
    zer.close()
    print("Discovered peers via mDNS:", list(listener.peers.values()))
    return list(listener.peers.values())

def discover_via_manifest(file_id, manifest_server="http://127.0.0.1:5001"):
    try:
        r = requests.get(f"{manifest_server}/manifest/{file_id}", timeout=3)
        if r.status_code != 200:
            return []
        data = r.json()
        peers = []
        for ch in data.get("chunks", []):
            for pr in ch.get("peer_replicas", []):
                peers.append({"peer_id": pr.get("peer_id"), "endpoint": pr.get("endpoint")})
        # dedupe by endpoint
        uniq = {}
        for p in peers:
            uniq[p['endpoint']] = p
        return list(uniq.values())
    except requests.RequestException as e:
        print("Error contacting manifest server:", e)
        return []
    
if __name__ == "__main__":
    print("mdns:", discover_mdns())
    print("manifest:", discover_via_manifest("file-uuid"))