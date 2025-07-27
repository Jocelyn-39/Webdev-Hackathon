from flask import Flask, request, jsonify, send_file
import requests, qrcode
from io import BytesIO
import uuid

app = Flask(__name__)

# Replace with your OpenRouteService key
ORS_API_KEY = "eyJvcmciOiI1YjNjZTM1OTc4NTExMTAwMDFjZjYyNDgiLCJpZCI6IjFlYjQ4NDg1YTIyNDQxNDBhMDQyMzNiNjY3YjI3ZjEwIiwiaCI6Im11cm11cjY0In0="

# In-memory order storage
orders = {}

# Get distance using OpenRouteService
def get_distance_km(origin_lat, origin_lng, dest_lat, dest_lng):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {"Authorization": ORS_API_KEY}
    payload = {
        "coordinates": [
            [float(origin_lng), float(origin_lat)],
            [float(dest_lng), float(dest_lat)]
        ]
    }

    res = requests.post(url, json=payload, headers=headers).json()
    try:
        distance_m = res["routes"][0]["summary"]["distance"]
        return distance_m / 1000  # meters → km
    except:
        return None

# Calculate delivery fee
def calculate_fee(mode, distance_km, pooled_orders=1, pooled_truck_cost=500):
    if mode == "self":
        return 0
    elif mode == "pooled":
        return pooled_truck_cost / pooled_orders
    elif mode == "warehouse":
        base_rate = 50
        rate_per_km = 10
        return base_rate + (distance_km * rate_per_km)
    return None


@app.route("/")
def home():
    return "Flask Delivery API Running!"


# Create new order
@app.route("/create-order", methods=["POST"])
def create_order():
    data = request.json
    mode = data.get("mode")
    origin_lat = data.get("origin_lat")
    origin_lng = data.get("origin_lng")
    dest_lat = data.get("dest_lat")
    dest_lng = data.get("dest_lng")
    pooled_orders = data.get("pooled_orders", 1)

    distance_km = get_distance_km(origin_lat, origin_lng, dest_lat, dest_lng)
    if distance_km is None:
        return jsonify({"error": "Distance API failed"}), 400

    fee = calculate_fee(mode, distance_km, pooled_orders)

    order_id = str(uuid.uuid4())[:8]  # small unique ID
    orders[order_id] = {
        "mode": mode,
        "distance_km": round(distance_km, 2),
        "fee": fee,
        "status": "Ordered"
    }

    return jsonify({"order_id": order_id, "details": orders[order_id]})


# Check order status
@app.route("/order-status/<order_id>", methods=["GET"])
def order_status(order_id):
    if order_id not in orders:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"order_id": order_id, "details": orders[order_id]})


# Update order status
@app.route("/update-status/<order_id>", methods=["POST"])
def update_status(order_id):
    if order_id not in orders:
        return jsonify({"error": "Order not found"}), 404

    new_status = request.json.get("status")
    if new_status not in ["Ordered", "In Transit", "Delivered"]:
        return jsonify({"error": "Invalid status"}), 400

    orders[order_id]["status"] = new_status
    return jsonify({"message": "Status updated", "details": orders[order_id]})


# Generate QR Code for order
@app.route("/generate-qr/<order_id>", methods=["GET"])
def generate_qr(order_id):
    if order_id not in orders:
        return jsonify({"error": "Order not found"}), 404

    qr_data = {"order_id": order_id, **orders[order_id]}

    img = qrcode.make(str(qr_data))
    buffer = BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)

    return send_file(buffer, mimetype="image/png")


if __name__ == "__main__":
    app.run(debug=True)
