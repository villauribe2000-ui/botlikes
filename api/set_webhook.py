import requests
import os
from http.server import BaseHTTPRequestHandler
import json

TOKEN = os.getenv("BOT_TOKEN")

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            # Obtener la URL base de Vercel
            webhook_url = f"https://{self.headers.get('host')}/api/webhook"
            
            # Configurar el webhook
            response = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/setWebhook",
                json={"url": webhook_url}
            )
            
            result = response.json()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            if result.get("ok"):
                self.wfile.write(json.dumps({
                    "status": "success",
                    "message": f"Webhook configurado correctamente en: {webhook_url}",
                    "result": result
                }).encode())
            else:
                self.wfile.write(json.dumps({
                    "status": "error",
                    "message": "Error al configurar webhook",
                    "result": result
                }).encode())
                
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "error",
                "message": str(e)
            }).encode())