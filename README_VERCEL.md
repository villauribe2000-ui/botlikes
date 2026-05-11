# Despliegue en Vercel - Bot de Telegram Free Fire

## 📋 Pasos para desplegar

### 1. Preparar el proyecto
- Asegúrate de tener todos los archivos necesarios
- El código ha sido adaptado para funcionar con webhooks de Vercel

### 2. Configurar variables de entorno en Vercel
Ve a tu proyecto en Vercel → Settings → Environment Variables y agrega:

```
BOT_TOKEN=tu_token_de_telegram_bot
ADMIN_ID=tu_id_de_telegram
LIKES_API_URL=https://hubsdev.com/api/frifas/sendlikes
LIKES_API1_KEY=tu_api_key_1
LIKES_API2_KEY=tu_api_key_2
HL_USER_UID=tu_hl_user_uid
HL_API_KEY=tu_hl_api_key
HL_API_URL=https://proapis.hlgamingofficial.com/main/games/freefire/account/api
PAYPAL_LINK=tu_link_de_paypal
PRECIO_VIP_USD=10.86
PRECIO_VIP_COP=40.000
LLAVE_COLOMBIA=tu_llave_colombia
```

### 3. Desplegar en Vercel
1. Conecta tu repositorio a Vercel
2. Vercel detectará automáticamente la configuración
3. Despliega el proyecto

### 4. Configurar el webhook
Después del despliegue, visita:
```
https://tu-proyecto.vercel.app/api/set_webhook
```

Esto configurará automáticamente el webhook de Telegram para que apunte a tu función serverless.

### 5. Verificar funcionamiento
- Visita `https://tu-proyecto.vercel.app/api/webhook` para verificar que esté funcionando
- Prueba el bot en Telegram

## ⚠️ Limitaciones importantes

### Persistencia de datos
- **Problema**: Vercel es serverless, no mantiene archivos entre ejecuciones
- **Solución actual**: Los datos se pierden entre reinicios
- **Recomendación**: Integrar una base de datos (MongoDB, PostgreSQL, etc.)

### Funciones que NO funcionarán en Vercel:
1. **AutoLike automático** - Requiere procesos en background
2. **Persistencia de configuración** - Los archivos JSON se pierden
3. **Contadores de uso diario** - Se resetean

### Para producción completa, considera:
1. **Base de datos**: MongoDB Atlas, PlanetScale, Supabase
2. **Cron jobs**: Para tareas programadas como AutoLike
3. **Redis**: Para caché y sesiones temporales

## 🔧 Archivos modificados para Vercel

- `vercel.json` - Configuración de Vercel
- `api/webhook.py` - Función serverless principal
- `api/set_webhook.py` - Configuración automática de webhook
- `requirements.txt` - Dependencias con versiones específicas

## 🚀 Comandos disponibles

El bot mantiene la mayoría de funcionalidades:
- `/start` - Menú principal
- `/like <ID>` - Enviar likes
- `/info <ID>` - Información del jugador
- Funciones administrativas básicas

## 📝 Notas adicionales

- El bot funciona con webhooks en lugar de polling
- Cada request es independiente (stateless)
- Para funcionalidad completa, migra a una base de datos
- Los logs se pueden ver en el dashboard de Vercel