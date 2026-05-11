#!/usr/bin/env python3
"""
🚀 Script de inicio para Railway
Inicia el bot con manejo de errores y reinicio automático
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def log(message):
    """Función para logging con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_environment():
    """Verifica que las variables de entorno estén configuradas"""
    required_vars = ["BOT_TOKEN", "ADMIN_ID"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        log(f"❌ Variables de entorno faltantes: {', '.join(missing_vars)}")
        log("💡 Configúralas en el dashboard de Railway")
        return False
    
    log("✅ Variables de entorno verificadas")
    return True

def start_bot():
    """Inicia el bot principal"""
    log("🚀 Iniciando bot de Free Fire en Railway...")
    
    if not check_environment():
        sys.exit(1)
    
    retry_count = 0
    max_retries = 5
    
    while retry_count < max_retries:
        try:
            log(f"🔄 Intento {retry_count + 1}/{max_retries}")
            
            # Ejecutar el bot principal
            result = subprocess.run([sys.executable, "bot_railway.py"], 
                                  capture_output=False, 
                                  text=True)
            
            if result.returncode == 0:
                log("✅ Bot terminó correctamente")
                break
            else:
                log(f"❌ Bot terminó con código de error: {result.returncode}")
                
        except KeyboardInterrupt:
            log("⏹️ Bot detenido por el usuario")
            break
        except Exception as e:
            log(f"💥 Error inesperado: {str(e)}")
        
        retry_count += 1
        if retry_count < max_retries:
            wait_time = min(30 * retry_count, 300)  # Máximo 5 minutos
            log(f"⏳ Esperando {wait_time} segundos antes del siguiente intento...")
            time.sleep(wait_time)
    
    if retry_count >= max_retries:
        log("💀 Máximo número de reintentos alcanzado. Terminando.")
        sys.exit(1)

if __name__ == "__main__":
    start_bot()