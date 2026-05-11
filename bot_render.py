import telebot
import requests
import json
import os
import threading
import time
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from flask import Flask, request

# Configuración
TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("LIKES_API_URL", "https://hubsdev.com/api/frifas/sendlikes")
API1_KEY = os.getenv("LIKES_API1_KEY")
API2_KEY = os.getenv("LIKES_API2_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PAYPAL_LINK = os.getenv("PAYPAL_LINK", "")
PRECIO_VIP = float(os.getenv("PRECIO_VIP_USD", "10.86"))
LLAVE_COLOMBIA = os.getenv("LLAVE_COLOMBIA", "")
PRECIO_VIP_COP = os.getenv("PRECIO_VIP_COP", "40.000")
HL_USER_UID = os.getenv("HL_USER_UID")
HL_API_KEY = os.getenv("HL_API_KEY")
HL_API_URL = os.getenv("HL_API_URL", "https://proapis.hlgamingofficial.com/main/games/freefire/account/api")

# Archivos de datos
GRUPOS_FILE = "grupos.json"
USOS_FILE = "usos.json"
CONFIG_FILE = "config.json"
AUTOLIKE_FILE = "autolike.json"

# Crear app Flask para webhook
app = Flask(__name__)

# ── Funciones de datos ────────────────────────────────────────────────────────
def cargar_json(archivo, default):
    if os.path.exists(archivo):
        try:
            with open(archivo, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return default
    return default

def guardar_json(archivo, data):
    try:
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error guardando {archivo}: {e}")

def cargar_grupos():
    return cargar_json(GRUPOS_FILE, [])

def guardar_grupos(g):
    guardar_json(GRUPOS_FILE, g)

def cargar_config():
    return cargar_json(CONFIG_FILE, {
        "limite_global": 1,
        "limites_por_grupo": {},
        "limites_personales": {},
        "bot_activo": True,
        "grupos_apagados": [],
        "ids_bloqueados": [],
        "usuarios_premium": {},
        "mantenimiento": False,
        "api_activa": "api1",
        "usos_api": {"api1": 0, "api2": 0, "fecha": ""}
    })

def guardar_config(c):
    guardar_json(CONFIG_FILE, c)

def cargar_usos():
    return cargar_json(USOS_FILE, {})

def guardar_usos(u):
    guardar_json(USOS_FILE, u)

def limpiar(texto):
    """Limpia caracteres especiales del texto"""
    if not texto:
        return "N/A"
    return str(texto).replace("*", "").replace("_", "").replace("`", "").replace("[", "").replace("]", "")

# ── Lógica de límites ────────────────────────────────────────────────────────
def get_limite(user_id, chat_id):
    if user_id == ADMIN_ID:
        return 0  # Admin sin límite siempre
    config = cargar_config()
    # 1. Límite personal tiene prioridad
    if str(user_id) in config.get("limites_personales", {}):
        return config["limites_personales"][str(user_id)]
    # 2. Límite por grupo
    if str(chat_id) in config.get("limites_por_grupo", {}):
        return config["limites_por_grupo"][str(chat_id)]
    # 3. Límite global
    return config.get("limite_global", 1)

def get_usos_hoy(user_id, chat_id):
    usos = cargar_usos()
    hoy = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{chat_id}"
    if key not in usos or usos[key]["fecha"] != hoy:
        return 0
    return usos[key]["count"]

def registrar_uso(user_id, chat_id):
    usos = cargar_usos()
    hoy = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{chat_id}"
    if key not in usos or usos[key]["fecha"] != hoy:
        usos[key] = {"fecha": hoy, "count": 1}
    else:
        usos[key]["count"] += 1
    guardar_usos(usos)

def puede_usar(user_id, chat_id):
    if user_id == ADMIN_ID:
        return True
    if es_premium(user_id):
        return True
    limite = get_limite(user_id, chat_id)
    if limite == 0:
        return True  # 0 = sin límite
    return get_usos_hoy(user_id, chat_id) < limite

def es_premium(user_id):
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    key = str(user_id)
    if key not in premium:
        return False
    try:
        expira = datetime.strptime(premium[key], "%Y-%m-%d")
        if datetime.now() > expira:
            # Expiró, quitar premium automáticamente
            del premium[key]
            config["usuarios_premium"] = premium
            guardar_config(config)
            return False
        return True
    except:
        return False

def dias_restantes_premium(user_id):
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    key = str(user_id)
    if key not in premium:
        return 0
    try:
        expira = datetime.strptime(premium[key], "%Y-%m-%d")
        delta = expira - datetime.now()
        return max(0, delta.days)
    except:
        return 0

def get_api_key():
    config = cargar_config()
    api = config.get("api_activa", "api1")
    if api == "api1":
        return API1_KEY
    elif api == "api2":
        return API2_KEY
    return None

def es_admin(user_id):
    return user_id == ADMIN_ID

def grupo_autorizado(chat_id):
    return chat_id in cargar_grupos()

def es_grupo(message):
    if message.from_user.id == ADMIN_ID:
        return True
    return message.chat.type in ["group", "supergroup"]

def buscar_info_jugador(player_id):
    regiones = ["us", "br", "sg", "ru", "id", "tw", "vn", "th", "me", "pk", "ind", "bd"]
    for region in regiones:
        try:
            response = requests.get(HL_API_URL, params={
                "sectionName": "AccountInfo",
                "PlayerUid": player_id,
                "region": region,
                "useruid": HL_USER_UID,
                "api": HL_API_KEY
            }, timeout=10)
            if response.status_code != 200:
                continue
            try:
                data = response.json()
            except:
                continue
            if "error" not in data and data.get("result"):
                data["result"]["_region"] = region
                return data["result"]
        except:
            continue
    return None

# Inicializar bot
bot = telebot.TeleBot(TOKEN)

if not TOKEN:
    raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")
if ADMIN_ID == 0:
    raise RuntimeError("Falta ADMIN_ID en variables de entorno.")
if not HL_USER_UID or not HL_API_KEY:
    raise RuntimeError("Falta HL_USER_UID o HL_API_KEY en variables de entorno.")

# ── Teclados ─────────────────────────────────────────────────────────────────
def teclado_menu_principal():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("/like"),
        KeyboardButton("/info"),
        KeyboardButton("/gremio"),
        KeyboardButton("/mascota"),
        KeyboardButton("/honor")
    )
    return markup

# ── Handlers ─────────────────────────────────────────────────────────────────
@bot.message_handler(func=lambda m: m.chat.type == "private" and m.from_user.id != ADMIN_ID and not (m.text and m.text.startswith("/comprar")))
def solo_privado(message):
    if message.text and message.text.startswith("/start"):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👑 Comprar VIP", url=f"https://t.me/{bot.get_me().username}?start=comprar"))
        bot.reply_to(message,
            "🎮 *Menú principal*\n\n"
            "Este bot funciona en grupos autorizados.\n"
            "Usa uno de estos comandos:\n"
            "• /like <ID>\n"
            "• /info <ID> <región>\n"
            "• /gremio <ID> <región>\n"
            "• /mascota <ID> <región>\n"
            "• /honor <ID> <región>\n\n"
            "Si quieres acceso VIP, toca el botón:",
            parse_mode="Markdown",
            reply_markup=markup
        )
    else:
        bot.reply_to(message,
            "🔒 Bot privado, solo en grupos autorizados.\n"
            "Creador: @sebas992269"
        )

@bot.message_handler(commands=["start"])
def start(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return
    limite = get_limite(message.from_user.id, message.chat.id)
    bot.reply_to(message,
        "🎮 *Bot de Likes Free Fire*\n\n"
        "📋 *Menú activado* (botones abajo)\n\n"
        "Comandos rápidos:\n"
        "• /like <ID>\n"
        "• /info <ID> <región>\n"
        "• /gremio <ID> <región>\n"
        "• /mascota <ID> <región>\n"
        "• /honor <ID> <región>\n\n"
        "Ejemplo: `/like 106540507`\n\n"
        f"⚠️ Tu límite: {limite} uso(s) por día\n\n"
        "Creador: @sebas992269",
        parse_mode="Markdown",
        reply_markup=teclado_menu_principal()
    )

@bot.message_handler(commands=["like"])
def like(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return

    config = cargar_config()
    if config.get("mantenimiento", False) and not es_admin(message.from_user.id):
        bot.reply_to(message,
            "🔧 *Sistema en mantenimiento*\n\n"
            "Estará disponible muy pronto.\n"
            "@sebas992269",
            parse_mode="Markdown"
        )
        return

    if not puede_usar(message.from_user.id, message.chat.id):
        limite = get_limite(message.from_user.id, message.chat.id)
        usos = get_usos_hoy(message.from_user.id, message.chat.id)
        bot.reply_to(message,
            f"⛔ Alcanzaste tu límite diario.\n"
            f"Usaste: {usos}/{limite} veces hoy.\n"
            f"Vuelve mañana 🕐"
        )
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Debes proporcionar un ID.\nEjemplo: /like 106540507")
        return

    player_id = partes[1]
    api_key = get_api_key()
    if api_key is None:
        bot.reply_to(message,
            "⛔ El servicio está desactivado temporalmente.\n"
            "Contacta a @sebas992269.",
            parse_mode="Markdown"
        )
        return

    bot.reply_to(message, "🔍 Enviando likes...")

    try:
        response = requests.get(API_URL, params={"key": api_key, "id": player_id}, timeout=15)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            registrar_uso(message.from_user.id, message.chat.id)
            d = data.get("data", {})
            likes_send = d.get('likes_send', 0)

            if likes_send == 0:
                mensaje = (
                    f"⚠️ Esta cuenta ya tiene el máximo de likes hoy.\n\n"
                    f"👤 Nick: {limpiar(d.get('player_nickname', 'N/A'))}\n"
                    f"🌎 Región: {d.get('region', 'N/A')}\n\n"
                    f"Intenta más tarde 🕐\n\n"
                    f"Creador: @sebas992269"
                )
            else:
                insignia = f"👑 USUARIO PREMIUM — {dias_restantes_premium(message.from_user.id)} días restantes\n\n" if es_premium(message.from_user.id) else ""
                if es_admin(message.from_user.id):
                    mensaje = (
                        f"╔══ 👑 EL CREADOR ESTA USANDO EL SISTEMA ══╗\n\n"
                        f"🚀 LIKES ENVIADOS ✅\n\n"
                        f"👤 Nick: {limpiar(d.get('player_nickname', 'N/A'))}\n"
                        f"🌎 Región: {d.get('region', 'N/A')}\n\n"
                        f"✨ RESULTADO 🔥\n"
                        f"➖ Antes: {d.get('likes_before', 0)}\n"
                        f"➕ Después: {d.get('likes_after', 0)}\n"
                        f"🎉 Enviados: {likes_send} me gusta!\n\n"
                        f"╚════════════════╝\n"
                        f"Creador: @sebas992269"
                    )
                else:
                    mensaje = (
                        f"{insignia}"
                        f"🚀 ME GUSTA ENVIADOS CON ÉXITO! ✅\n\n"
                        f"👤 Nick: {limpiar(d.get('player_nickname', 'N/A'))}\n"
                        f"🌎 Región: {d.get('region', 'N/A')}\n\n"
                        f"✨ RESULTADO 🔥\n"
                        f"➖ Antes: {d.get('likes_before', 0)}\n"
                        f"➕ Después: {d.get('likes_after', 0)}\n"
                        f"🎉 Enviados: {likes_send} me gusta!\n\n"
                        f"Creador: @sebas992269"
                    )
        else:
            mensaje = f"⚠️ Error al enviar likes."

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("👑 Platform - Principal", url="https://t.me/bunlatrixvip")]])
        bot.reply_to(message, mensaje, reply_markup=markup)

    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏱️ La API tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.message_handler(commands=["info"])
def info_comando(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /info <ID> [región]\nEjemplo: /info 106540507 us")
        return

    player_id = partes[1]
    bot.reply_to(message, "🔍 Buscando información del jugador...")

    info = buscar_info_jugador(player_id)
    if info:
        from datetime import datetime as dt
        nombre = limpiar(info.get("AccountName", "N/A"))
        region = info.get("AccountRegion", info.get("_region", "N/A")).upper()
        ob = info.get("ReleaseVersion", "N/A")
        likes = info.get("AccountLikes", "N/A")
        exp = info.get("AccountEXP", "N/A")
        create_ts = info.get("AccountCreateTime", 0)
        try:
            fecha_creacion = dt.fromtimestamp(int(create_ts)).strftime("%d/%m/%Y - %H:%M:%S")
        except:
            fecha_creacion = "N/A"

        mensaje = (
            f"🎮 *INFORMACIÓN DEL JUGADOR*\n\n"
            f"👤 *Nombre:* {nombre}\n"
            f"🆔 *ID:* `{player_id}`\n"
            f"🌎 *Región:* {region} ({ob})\n"
            f"❤️ *Me Gusta:* {likes}\n"
            f"⭐ *Experiencia:* {exp} EXP\n"
            f"📅 *Creación:* {fecha_creacion}\n\n"
            f"Creador: @sebas992269"
        )
        bot.reply_to(message, mensaje, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ No se pudo encontrar información del jugador.")

# ── Webhook Flask ────────────────────────────────────────────────────────────
@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
        return '', 200
    except Exception as e:
        print(f"Error en webhook: {e}")
        return '', 500

@app.route('/health')
def health():
    return 'Bot is running!', 200

@app.route('/')
def index():
    return 'Free Fire Bot is running on Render!', 200

# ── Configurar webhook ──────────────────────────────────────────────────────
def setup_webhook():
    webhook_url = f"https://{os.getenv('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/webhook"
    try:
        bot.remove_webhook()
        time.sleep(1)
        result = bot.set_webhook(url=webhook_url)
        print(f"Webhook configurado: {webhook_url} - Resultado: {result}")
    except Exception as e:
        print(f"Error configurando webhook: {e}")

if __name__ == '__main__':
    # Configurar webhook si estamos en Render
    if os.getenv('RENDER_EXTERNAL_HOSTNAME'):
        setup_webhook()
    
    # Iniciar servidor Flask
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)