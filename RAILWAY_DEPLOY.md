# Deploy 24/7 en Railway

Este proyecto ya está listo para Railway con:
- `Procfile` -> `worker: python bot.py`
- `requirements.txt`
- `runtime.txt`

## 1) Subir a GitHub

```bash
git add .
git commit -m "prepare railway deploy"
git push
```

## 2) Crear proyecto en Railway

1. Entra a https://railway.app
2. `New Project` -> `Deploy from GitHub repo`
3. Selecciona este repositorio

## 3) Configurar variables de entorno

En Railway -> tu servicio -> `Variables`, agrega:

- `BOT_TOKEN`
- `ADMIN_ID`
- `LIKES_API_URL`
- `LIKES_API1_KEY`
- `LIKES_API2_KEY`
- `HL_USER_UID`
- `HL_API_KEY`
- `HL_API_URL`
- `PAYPAL_LINK`
- `PRECIO_VIP_USD`
- `PRECIO_VIP_COP`
- `LLAVE_COLOMBIA`

Puedes tomar como guía el archivo `.env.example`.

## 4) Verificar arranque

En logs debe aparecer que el bot inicia correctamente.

Si hay error por dependencias, revisa `requirements.txt` y redeploy.
