# 🚀 Instrucciones paso a paso - Despliegue en Railway

## 📋 Preparativos

### 1. Verificar archivos
Asegúrate de tener estos archivos en tu proyecto:
- ✅ `bot_railway.py` - Bot principal con polling
- ✅ `requirements.txt` - Dependencias (sin Flask)
- ✅ `railway.toml` - Configuración de Railway
- ✅ `start_railway.py` - Script de inicio con reintentos
- ✅ `.env.railway.example` - Ejemplo de variables

## 🌐 Paso 1: Subir a GitHub

```bash
# Agregar todos los archivos
git add .

# Hacer commit
git commit -m "🚀 Bot preparado para Railway - Polling continuo sin suspensiones"

# Subir a GitHub
git push origin main
```

## 🚂 Paso 2: Crear proyecto en Railway

1. **Ir a Railway**
   - Ve a [railway.app](https://railway.app)
   - Inicia sesión con GitHub

2. **Crear nuevo proyecto**
   - Click en "New Project"
   - Selecciona "Deploy from GitHub repo"
   - Busca y selecciona tu repositorio

3. **Configurar el proyecto**
   - Railway detectará automáticamente que es un proyecto Python
   - Usará `railway.toml` para la configuración

## ⚙️ Paso 3: Configurar variables de entorno

En el dashboard de Railway:

1. **Ir a Variables**
   - Click en tu proyecto
   - Ve a la pestaña "Variables"

2. **Agregar variables REQUERIDAS:**
   ```
   BOT_TOKEN = tu_token_del_bot_de_telegram
   ADMIN_ID = tu_id_de_telegram
   LIKES_API1_KEY = tu_primera_api_key
   LIKES_API2_KEY = tu_segunda_api_key
   ```

3. **Agregar variables OPCIONALES:**
   ```
   HL_USER_UID = tu_hl_gaming_uid
   HL_API_KEY = tu_hl_gaming_api_key
   PAYPAL_LINK = tu_link_de_paypal
   ```

## 🚀 Paso 4: Desplegar

1. **Despliegue automático**
   - Railway desplegará automáticamente después de configurar las variables
   - Puedes ver el progreso en la pestaña "Deployments"

2. **Verificar logs**
   - Ve a la pestaña "Logs"
   - Deberías ver: "🚀 Bot iniciado en Railway - Sin suspensiones!"

## ✅ Paso 5: Verificar funcionamiento

### Probar comandos básicos:
1. **Verificar admin:**
   ```
   /testadmin
   ```

2. **Ver panel admin:**
   ```
   /admin
   ```

3. **Agregar un grupo:**
   ```
   /addgrupo -1001234567890
   ```

4. **Probar likes:**
   ```
   /like 106540507
   ```

## 🔧 Solución de problemas

### ❌ Bot no responde
**Problema:** El bot no responde a comandos
**Solución:**
1. Verifica que `BOT_TOKEN` esté configurado correctamente
2. Revisa los logs en Railway Dashboard
3. Asegúrate que el bot esté agregado al grupo

### ❌ "No tienes permiso" en comandos admin
**Problema:** Los comandos admin no funcionan
**Solución:**
1. Usa `/miid` para obtener tu ID exacto
2. Configura `ADMIN_ID` con ese número exacto
3. Usa `/testadmin` para verificar

### ❌ "Error de API" al enviar likes
**Problema:** Las APIs no funcionan
**Solución:**
1. Verifica `LIKES_API1_KEY` y `LIKES_API2_KEY`
2. Usa `/verapi` para ver el estado
3. Cambia de API: `/activarapi1` o `/activarapi2`

### ❌ Bot se reinicia constantemente
**Problema:** El bot se reinicia en bucle
**Solución:**
1. Revisa los logs para ver el error específico
2. Verifica que todas las variables requeridas estén configuradas
3. El script `start_railway.py` maneja reintentos automáticamente

## 📊 Monitoreo

### Dashboard de Railway:
- **Logs:** Ver actividad en tiempo real
- **Metrics:** CPU, memoria, red
- **Deployments:** Historial de despliegues
- **Variables:** Gestionar configuración

### Comandos del bot:
- `/verapi` - Estado de las APIs
- `/verlimites` - Configuración de límites
- `/listapremium` - Usuarios premium
- `/listagrupos` - Grupos autorizados

## 🎉 ¡Listo!

Tu bot ahora está funcionando 24/7 en Railway sin suspensiones. 

**Ventajas sobre Render:**
- ✅ Sin suspensiones automáticas
- ✅ Polling continuo más estable
- ✅ Mejor uptime garantizado
- ✅ Reinicio automático en caso de errores

**Soporte:** [@sebas992269](https://t.me/sebas992269)