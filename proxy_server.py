from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

@app.route("/rule34", methods=["GET"])
def rule34_proxy():
    tags = request.args.get("tags", "")
    limit = request.args.get("limit", "100")
    url = "https://rule34.xxx/index.php"

    params = {
        "page": "dapi",
        "s": "post",
        "q": "index",
        "json": "1",
        "tags": tags,
        "limit": limit
    }

    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
