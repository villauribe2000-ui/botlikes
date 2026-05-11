# 🚀 Bot Free Fire - Despliegue en Railway

Bot de Telegram para enviar likes en Free Fire, desplegado en Railway con **polling continuo** (sin suspensiones).

## ✨ Características

- ✅ **Sin suspensiones** - Railway mantiene el bot activo 24/7
- 🔄 **Polling continuo** - No requiere webhooks
- 🛠 **Panel de administración completo**
- 👑 **Sistema de usuarios premium**
- 📊 **Control de límites por usuario/grupo**
- 🔧 **Modo mantenimiento**
- 🚫 **Sistema de bloqueo de cuentas**

## 🚀 Despliegue en Railway

### 1. Preparar el repositorio
```bash
git add .
git commit -m "🚀 Bot preparado para Railway"
git push origin main
```

### 2. Crear proyecto en Railway
1. Ve a [railway.app](https://railway.app)
2. Conecta tu repositorio de GitHub
3. Selecciona el repositorio del bot

### 3. Configurar variables de entorno
En el dashboard de Railway, agrega estas variables:

```env
BOT_TOKEN=tu_token_del_bot_de_telegram
ADMIN_ID=tu_id_de_telegram
LIKES_API1_KEY=tu_primera_api_key
LIKES_API2_KEY=tu_segunda_api_key
HL_USER_UID=tu_hl_gaming_uid
HL_API_KEY=tu_hl_gaming_api_key
```

### 4. Variables opcionales
```env
LIKES_API_URL=https://hubsdev.com/api/frifas/sendlikes
PAYPAL_LINK=tu_link_de_paypal
PRECIO_VIP_USD=10.86
LLAVE_COLOMBIA=tu_llave_colombia
PRECIO_VIP_COP=40.000
HL_API_URL=https://proapis.hlgamingofficial.com/main/games/freefire/account/api
```

## 📋 Comandos disponibles

### 👥 Usuarios normales
- `/start` - Menú principal
- `/like <ID>` - Enviar likes a una cuenta
- `/info <ID>` - Información del jugador
- `/gremio <ID>` - Información del gremio
- `/mascota <ID>` - Información de mascota
- `/honor <ID>` - Puntuación de honor
- `/miid` - Ver tu ID de Telegram

### 🛠 Panel de administración
- `/admin` - Ver panel completo
- `/addgrupo <ID>` - Autorizar grupo
- `/delgrupo <ID>` - Desautorizar grupo
- `/bloquear <ID>` - Bloquear cuenta FF
- `/addpremium <ID> [días]` - Agregar premium
- `/limitetodos <número>` - Límite global
- `/mantenimiento` - Activar mantenimiento
- `/verapi` - Ver estado de APIs
- `/testadmin` - Verificar permisos admin

## 🔧 Diferencias con Render

| Característica | Railway | Render |
|---|---|---|
| **Suspensión** | ❌ Nunca se suspende | ✅ Se suspende tras 15 min |
| **Conexión** | 🔄 Polling continuo | 🌐 Webhooks |
| **Uptime** | 🟢 24/7 garantizado | 🟡 Intermitente |
| **Configuración** | 📁 railway.toml | 📁 render.yaml |
| **Dependencias** | 📦 Sin Flask | 📦 Con Flask |

## 🐛 Solución de problemas

### Bot no responde
1. Verifica que `BOT_TOKEN` esté configurado
2. Revisa los logs en Railway Dashboard
3. Confirma que `ADMIN_ID` sea correcto

### Comandos admin no funcionan
1. Usa `/testadmin` para verificar permisos
2. Asegúrate que `ADMIN_ID` sea tu ID exacto
3. Usa `/miid` para obtener tu ID correcto

### APIs no funcionan
1. Verifica `LIKES_API1_KEY` y `LIKES_API2_KEY`
2. Usa `/verapi` para ver el estado
3. Cambia de API con `/activarapi1` o `/activarapi2`

## 📊 Monitoreo

Railway proporciona:
- 📈 Métricas de CPU y memoria
- 📋 Logs en tiempo real
- 🔄 Reinicio automático en caso de error
- 📊 Estadísticas de uptime

## 🆘 Soporte

Creador: [@sebas992269](https://t.me/sebas992269)

---

**¡Tu bot ahora funciona 24/7 sin interrupciones en Railway! 🚀**