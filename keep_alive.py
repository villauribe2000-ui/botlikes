#!/usr/bin/env python3
"""
Script para mantener el bot activo en Render
Hace ping cada 10 minutos para evitar que se suspenda
"""

import requests
import time
import os
from datetime import datetime

# URL de tu app en Render (cambiar por la tuya)
RENDER_URL = os.getenv('RENDER_EXTERNAL_URL', 'https://tu-app.onrender.com')
PING_INTERVAL = 600  # 10 minutos en segundos

def ping_service():
    """Hace ping al servicio para mantenerlo activo"""
    try:
        response = requests.get(f"{RENDER_URL}/health", timeout=30)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if response.status_code == 200:
            print(f"[{timestamp}] ✅ Ping exitoso - Bot activo")
            return True
        else:
            print(f"[{timestamp}] ⚠️ Ping falló - Status: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] ❌ Error en ping: {e}")
        return False

def main():
    """Función principal que mantiene el servicio activo"""
    print("🚀 Iniciando keep-alive para Render...")
    print(f"📡 URL objetivo: {RENDER_URL}")
    print(f"⏰ Intervalo: {PING_INTERVAL//60} minutos")
    print("-" * 50)
    
    while True:
        ping_service()
        time.sleep(PING_INTERVAL)

if __name__ == "__main__":
    main()