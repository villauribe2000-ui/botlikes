# 🚀 Despliegue en Render - Bot de Telegram Free Fire

## 📊 ¿Por qué Render?

### ✅ **Ventajas del plan gratuito de Render:**
- **750 horas gratis** por mes (suficiente para 24/7)
- **Hasta 25 servicios** en el plan Hobby
- **Persistencia de archivos** (a diferencia de Vercel)
- **Soporte completo para bots** de Telegram
- **Dominios personalizados** incluidos
- **SSL automático** y certificados TLS
- **Logs en tiempo real**
- **Rollbacks automáticos**

### ⚠️ **Limitación importante:**
- Los servicios gratuitos se **suspenden después de 15 minutos** de inactividad
- Se **reactivan automáticamente** cuando llega una nueva request (toma ~1 minuto)

## 🛠️ Archivos creados para Render:

1. **`render.yaml`** - Configuración de despliegue
2. **`bot_render.py`** - Bot adaptado con Flask + webhooks
3. **`README_RENDER.md`** - Esta guía

## 📋 Pasos para desplegar:

### 1. **Crear cuenta en Render**
- Ve a [render.com](https://render.com)
- Regístrate con GitHub/GitLab

### 2. **Conectar repositorio**
- En Render Dashboard → "New" → "Web Service"
- Conecta tu repositorio de GitHub/GitLab
- Selecciona la rama (main/master)

### 3. **Configurar el servicio**
```
Name: freefire-bot
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: python bot_render.py
```

### 4. **Variables de entorno**
En la sección "Environment Variables", agrega:

```bash
BOT_TOKEN=tu_token_de_telegram_bot
ADMIN_ID=tu_id_de_telegram
LIKES_API1_KEY=tu_api_key_1
LIKES_API2_KEY=tu_api_key_2
HL_USER_UID=tu_hl_user_uid
HL_API_KEY=tu_hl_api_key
PAYPAL_LINK=tu_link_de_paypal
LLAVE_COLOMBIA=tu_llave_colombia
```

### 5. **Desplegar**
- Haz clic en "Create Web Service"
- Render construirá y desplegará automáticamente
- El webhook se configurará automáticamente

## 🔧 Funcionalidades incluidas:

### ✅ **Lo que SÍ funciona:**
- ✅ Envío de likes (`/like`)
- ✅ Información de jugadores (`/info`)
- ✅ Persistencia de datos (archivos JSON)
- ✅ Límites por usuario/grupo
- ✅ Sistema de usuarios premium
- ✅ Panel administrativo completo
- ✅ Contadores de uso diarios
- ✅ Configuración de APIs
- ✅ Bloqueo de cuentas

### ⚠️ **Limitaciones:**
- ❌ **AutoLike automático cada 24h** (se suspende el servicio)
- ⚠️ **Retraso de ~1 minuto** al reactivarse después de inactividad

## 🔄 Diferencias con el bot original:

### **Cambios técnicos:**
1. **Webhook en lugar de polling** - Más eficiente para Render
2. **Flask integrado** - Para manejar requests HTTP
3. **Configuración automática** - El webhook se configura solo
4. **Health checks** - Endpoint `/health` para monitoreo

### **Funciones mantenidas:**
- Todos los comandos originales
- Sistema completo de administración
- Persistencia de configuración
- Límites y premium

## 🌐 URLs importantes después del despliegue:

```
Bot webhook: https://tu-app.onrender.com/webhook
Health check: https://tu-app.onrender.com/health
Status: https://tu-app.onrender.com/
```

## 🔍 Monitoreo y logs:

- **Logs en tiempo real** en el dashboard de Render
- **Métricas de uso** incluidas
- **Alertas automáticas** si hay errores

## 💡 Consejos para optimizar:

### **Mantener el bot activo:**
1. **Usar un servicio de ping** (UptimeRobot, etc.)
2. **Configurar un cron job** que haga ping cada 10 minutos
3. **URL para ping:** `https://tu-app.onrender.com/health`

### **Para AutoLike (opcional):**
Si necesitas AutoLike automático, considera:
1. **Upgrade a plan pago** de Render ($7/mes)
2. **Usar un servicio externo** para cron jobs
3. **Implementar con GitHub Actions** (gratis)

## 🆙 Upgrade a plan pago:

Si necesitas **100% uptime** y **AutoLike automático**:
- **Starter Plan**: $7/mes
- **Sin suspensión** por inactividad
- **Recursos dedicados**
- **Soporte prioritario**

## 🚨 Troubleshooting:

### **Bot no responde:**
1. Verifica las variables de entorno
2. Revisa los logs en Render Dashboard
3. Confirma que el webhook esté configurado

### **Error de webhook:**
1. Ve a `https://tu-app.onrender.com/health`
2. Si no carga, revisa los logs de build
3. Verifica que Flask esté corriendo

### **Datos se pierden:**
- En Render los archivos SÍ persisten (a diferencia de Vercel)
- Si se pierden, puede ser un error de permisos

## 📞 Soporte:

- **Logs detallados** en Render Dashboard
- **Documentación:** [render.com/docs](https://render.com/docs)
- **Comunidad:** Discord de Render