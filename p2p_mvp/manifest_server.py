from flask import Flask, request, jsonify
from collections import defaultdict
import threading

app = Flask(__name__)

manifest = defaultdict(lambda: defaultdict(list))

@app.route('/manifest/<file_id>', methods=['PATCH'])
def patch_manifest(file_id):
    data = request.get_json()
    chunk_number = data.get('chunk_number')
    peer_replica = data.get('peer_replica')
    
    if chunk_number is None or peer_replica is None:
        return jsonify({"error": "Invalid payload"}), 400
    
    # Update the manifest
    manifest[file_id][int(chunk_number)].append(peer_replica)
    return jsonify({"ok": True}) 

@app.route('/manifest/<file_id>', methods=['GET'])
def get_manifest(file_id):
    m = manifest.get(file_id, {})
    # Convert to serializable
    out = []
    for cnum, peers in m.items():
        out.append({
            "chunk_number": cnum,
            "peer_replicas": peers
        })
    return jsonify({"file_id": file_id, "chunks": out})

if __name__ == "__main__":
    app.run(port=5001)