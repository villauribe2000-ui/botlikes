import telebot
import requests
import json
import os
import threading
import time
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("LIKES_API_URL", "https://hubsdev.com/api/frifas/sendlikes")
API1_KEY = os.getenv("LIKES_API1_KEY")  # Límite 30
API2_KEY = os.getenv("LIKES_API2_KEY")  # Límite 200
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
PAYPAL_LINK = os.getenv("PAYPAL_LINK", "")
PRECIO_VIP = float(os.getenv("PRECIO_VIP_USD", "10.86"))  # El cliente paga esto para que admin reciba $10
LLAVE_COLOMBIA = os.getenv("LLAVE_COLOMBIA", "")
PRECIO_VIP_COP = os.getenv("PRECIO_VIP_COP", "40.000")
HL_USER_UID = os.getenv("HL_USER_UID")
HL_API_KEY = os.getenv("HL_API_KEY")
HL_API_URL = os.getenv("HL_API_URL", "https://proapis.hlgamingofficial.com/main/games/freefire/account/api")
GRUPOS_FILE = "grupos.json"
USOS_FILE = "usos.json"
CONFIG_FILE = "config.json"
AUTOLIKE_FILE = "autolike.json"

# ── Archivos de datos ────────────────────────────────────────────────────────
def cargar_json(archivo, default):
    if os.path.exists(archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            return json.load(f)
    return default

def guardar_json(archivo, data):
    with open(archivo, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

def cargar_grupos():
    return cargar_json(GRUPOS_FILE, [])

def guardar_grupos(g):
    guardar_json(GRUPOS_FILE, g)

def cargar_config():
    return cargar_json(CONFIG_FILE, {
        "limite_global": 0,
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
    return config.get("limite_global", 0)

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
    expira = datetime.strptime(premium[key], "%Y-%m-%d")
    if datetime.now() > expira:
        # Expiró, quitar premium automáticamente
        del premium[key]
        config["usuarios_premium"] = premium
        guardar_config(config)
        return False
    return True

def dias_restantes_premium(user_id):
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    key = str(user_id)
    if key not in premium:
        return 0
    expira = datetime.strptime(premium[key], "%Y-%m-%d")
    delta = expira - datetime.now()
    return max(0, delta.days)

def get_api_key():
    config = cargar_config()
    api = config.get("api_activa", "api1")
    if api == "api1":
        return API1_KEY
    elif api == "api2":
        return API2_KEY
    return None  # ninguna = desactivada

def id_bloqueado(player_id):
    config = cargar_config()
    return str(player_id) in [str(x) for x in config.get("ids_bloqueados", [])]

def bot_activo_en(chat_id):
    config = cargar_config()
    if not config.get("bot_activo", True):
        return False
    return chat_id not in config.get("grupos_apagados", [])

def registrar_uso_api():
    config = cargar_config()
    hoy = datetime.now().strftime("%Y-%m-%d")
    usos = config.get("usos_api", {"api1": 0, "api2": 0, "fecha": ""})
    if usos.get("fecha") != hoy:
        usos = {"api1": 0, "api2": 0, "fecha": hoy}
    api = config.get("api_activa", "api1")
    if api in usos:
        usos[api] += 1
    config["usos_api"] = usos
    guardar_config(config)

def get_usos_api():
    config = cargar_config()
    hoy = datetime.now().strftime("%Y-%m-%d")
    usos = config.get("usos_api", {"api1": 0, "api2": 0, "fecha": ""})
    if usos.get("fecha") != hoy:
        return {"api1": 0, "api2": 0}
    return usos

def cargar_autolike():
    config = cargar_config()
    return config.get("autolike", [])

def guardar_autolike(data):
    config = cargar_config()
    config["autolike"] = data
    guardar_config(config)

def enviar_likes_auto(player_id, region):
    api_key = get_api_key()
    if not api_key:
        return False
    try:
        response = requests.get(API_URL, params={
            "key": api_key,
            "id": player_id
        }, timeout=15)
        data = response.json()
        if data.get("success"):
            d = data.get("data", {})
            nombre = limpiar(d.get("player_nickname", "N/A"))
            likes_send = d.get("likes_send", 0)
            likes_after = d.get("likes_after", 0)
            try:
                bot.send_message(ADMIN_ID,
                    f"🔄 *AutoLike ejecutado*\n\n"
                    f"👤 *Nick:* {nombre}\n"
                    f"🆔 *ID:* `{player_id}`\n"
                    f"🎉 *Likes enviados:* {likes_send}\n"
                    f"❤️ *Total ahora:* {likes_after}",
                    parse_mode="Markdown"
                )
            except:
                pass
            return True
        return False
    except:
        return False

def ejecutar_autolike():
    while True:
        cuentas = cargar_autolike()
        for cuenta in cuentas:
            enviar_likes_auto(cuenta["id"], cuenta.get("region", "us"))
        time.sleep(86400)  # 24 horas exactas
def es_admin(user_id):
    return user_id == ADMIN_ID

def grupo_autorizado(chat_id):
    return chat_id in cargar_grupos()

def es_grupo(message):
    if message.from_user.id == ADMIN_ID:
        return True
    return message.chat.type in ["group", "supergroup"]

bot = telebot.TeleBot(TOKEN)

if not TOKEN:
    raise RuntimeError("Falta BOT_TOKEN en variables de entorno.")
if ADMIN_ID == 0:
    raise RuntimeError("Falta ADMIN_ID en variables de entorno (ej: 7535906226).")
if not HL_USER_UID or not HL_API_KEY:
    raise RuntimeError("Falta HL_USER_UID o HL_API_KEY en variables de entorno.")

# ── Teclados ─────────────────────────────────────────────────────────────────
def teclado_limites(tipo, extra=""):
    markup = InlineKeyboardMarkup()
    opciones = [1, 2, 3, 5, 10]
    botones = [InlineKeyboardButton(f"{n}x/día", callback_data=f"lim_{tipo}_{n}_{extra}") for n in opciones]
    markup.row(*botones[:3])
    markup.row(*botones[3:])
    markup.row(InlineKeyboardButton("♾️ Sin límite", callback_data=f"lim_{tipo}_0_{extra}"))
    if tipo == "persona":
        markup.row(InlineKeyboardButton("🗑️ Quitar límite personal", callback_data=f"lim_delpersona_0_{extra}"))
    return markup

def teclado_grupos_limite():
    grupos = cargar_grupos()
    if not grupos:
        return None
    markup = InlineKeyboardMarkup()
    for g in grupos:
        markup.add(InlineKeyboardButton(f"Grupo {g}", callback_data=f"selgrupo_{g}"))
    return markup

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

# ── Bloquear privados ────────────────────────────────────────────────────────
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

# ── /start ───────────────────────────────────────────────────────────────────
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

# ── /like ────────────────────────────────────────────────────────────────────
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

    if not bot_activo_en(message.chat.id) and not es_admin(message.from_user.id) and not es_premium(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👑 Comprar VIP", url=f"https://t.me/{bot.get_me().username}?start=comprar"))
        bot.reply_to(message,
            "🔒 *Este servicio requiere membresía Premium.*\n\n"
            "Contacta a @sebas992269 para adquirirla.",
            parse_mode="Markdown",
            reply_markup=markup
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

    if id_bloqueado(player_id) and not es_admin(message.from_user.id):
        bot.reply_to(message,
            f"🚫 *La cuenta* `{player_id}` *está bloqueada por el creador.*\n\n"
            f"Contacta a @sebas992269 para más información.",
            parse_mode="Markdown"
        )
        return

    api_key = get_api_key()
    if api_key is None:
        bot.reply_to(message,
            "⛔ El servicio está desactivado temporalmente.\n"
            "Contacta a @sebas992269.",
            parse_mode="Markdown"
        )
        return

    bot.reply_to(message, "🔍 Buscando cuenta...")

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

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton("🟢 Aceptar", callback_data=f"like_ok_{player_id}_{message.from_user.id}_{message.chat.id}"),
            InlineKeyboardButton("🔴 Cancelar", callback_data=f"like_no_{player_id}_{message.from_user.id}")
        )
        bot.reply_to(message,
            f"🎁 CUENTA ENCONTRADA!\n\n"
            f"- JUGADOR: {nombre}\n"
            f"- REGIÓN: {region} ({ob})\n"
            f"- ME GUSTA ACTUALES: {likes}\n"
            f"- EXPERIENCIA: {exp} EXP\n"
            f"- CREACIÓN: {fecha_creacion}\n\n"
            f"¿Deseas enviar likes a esta cuenta?",
            reply_markup=markup
        )
    else:
        # Si no se encuentra info, enviar likes directamente
        enviar_likes_directo(message, player_id, api_key)

@bot.callback_query_handler(func=lambda call: call.data.startswith("like_ok_") or call.data.startswith("like_no_"))
def callback_like_confirm(call):
    partes = call.data.split("_")
    accion = partes[1]
    player_id = partes[2]
    user_id = int(partes[3])

    if call.from_user.id != user_id:
        bot.answer_callback_query(call.id, "⛔ Este botón no es para ti.")
        return

    if accion == "no":
        bot.edit_message_text("❌ Envío de likes cancelado.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    chat_id = int(partes[4])
    api_key = get_api_key()
    if not api_key:
        bot.edit_message_text("⛔ El servicio está desactivado temporalmente.", call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id)
        return

    bot.edit_message_text(f"⏳ Enviando likes a la cuenta {player_id}...", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

    try:
        response = requests.get(API_URL, params={"key": api_key, "id": player_id}, timeout=15)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            registrar_uso(user_id, chat_id)
            registrar_uso_api()
            limite = get_limite(user_id, chat_id)
            usos = get_usos_hoy(user_id, chat_id)
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
                insignia = f"👑 USUARIO PREMIUM — {dias_restantes_premium(user_id)} días restantes\n\n" if es_premium(user_id) else ""
                if es_admin(user_id):
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
        bot.send_message(call.message.chat.id, mensaje, reply_markup=markup)

    except requests.exceptions.Timeout:
        bot.send_message(call.message.chat.id, "⏱️ La API tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Error: {str(e)}")

def enviar_likes_directo(message, player_id, api_key):
    try:
        response = requests.get(API_URL, params={"key": api_key, "id": player_id}, timeout=15)
        data = response.json()
        if response.status_code == 200 and data.get("success"):
            registrar_uso(message.from_user.id, message.chat.id)
            registrar_uso_api()
            d = data.get("data", {})
            likes_send = d.get('likes_send', 0)
            if likes_send == 0:
                mensaje = f"⚠️ Esta cuenta ya tiene el máximo de likes hoy.\nIntenta más tarde 🕐"
            else:
                mensaje = (
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
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

    api_key = get_api_key()
    if api_key is None:
        bot.reply_to(message,
            "⛔ El servicio está desactivado temporalmente.\n"
            "Contacta a @sebas992269.",
            parse_mode="Markdown"
        )
        return

    try:
        response = requests.get(API_URL, params={"key": api_key, "id": player_id}, timeout=15)
        data = response.json()

        if response.status_code == 200 and data.get("success"):
            registrar_uso(message.from_user.id, message.chat.id)
            registrar_uso_api()
            limite = get_limite(message.from_user.id, message.chat.id)
            usos = get_usos_hoy(message.from_user.id, message.chat.id)
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
            mensaje = f"⚠️ Error al enviar likes.\nRespuesta: {data}"

        bot.reply_to(message, mensaje, reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("👑 Platform - Principal", url="https://t.me/bunlatrixvip")
        ]]))

    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏱️ La API tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ── PANEL ADMIN ──────────────────────────────────────────────────────────────
@bot.message_handler(commands=["admin"])
def panel_admin(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    grupos = cargar_grupos()
    texto = (
        "🛠 *Panel de Administración*\n\n"
        f"📋 Grupos autorizados: {len(grupos)}\n"
        f"⚠️ Límite global: {config.get('limite_global', 1)} uso(s)/día\n\n"
        "*Grupos:*\n"
        "/addgrupo <ID> — Agregar grupo\n"
        "/delgrupo <ID> — Eliminar grupo\n"
        "/listagrupos — Ver grupos\n\n"
        "*Límites:*\n"
        "/limitetodos — Límite global para todos\n"
        "/limitegrupo — Límite por grupo específico\n"
        "/limitepersona <ID> — Límite individual\n"
        "/verlimites — Ver todos los límites\n"
        "/resetusos — Resetear usos de todos\n\n"
        "*Encender/Apagar:*\n"
        "/apagar — Apagar bot en un grupo\n"
        "/encender — Encender bot en un grupo\n"
        "/apagarTodo — Apagar bot en todos los grupos\n"
        "/encenderTodo — Encender bot en todos los grupos\n\n"
        "*Bloqueo de cuentas FF:*\n"
        "/bloquear <ID> — Bloquear cuenta de FF\n"
        "/desbloquear <ID> — Desbloquear cuenta de FF\n"
        "/listabloqueados — Ver cuentas bloqueadas\n\n"
        "*Usuarios Premium:*\n"
        "/addpremium <ID> — Agregar usuario premium\n"
        "/delpremium <ID> — Quitar usuario premium\n"
        "/listapremium — Ver usuarios premium\n\n"
        "*Mantenimiento:*\n"
        "/mantenimiento — Activar modo mantenimiento\n"
        "/sinmantenimiento — Desactivar mantenimiento\n\n"
        "*AutoLike (cada 24h):*\n"
        "/addautolike <ID> <región> — Agregar cuenta\n"
        "/delautolike <ID> — Quitar cuenta\n"
        "/listaautolike — Ver cuentas en autolike\n\n"
        "*APIs:*\n"
        "/activarapi1 — Activar API 1 (límite 30)\n"
        "/activarapi2 — Activar API 2 (límite 200)\n"
        "/desactivarapi — Desactivar ambas APIs\n"
        "/verapi — Ver API activa\n\n"
        "*Utilidades:*\n"
        "/id — ID del grupo\n"
        "/id (respondiendo mensaje) — ID del usuario\n"
        "/info <ID> <región> — Info completa del jugador\n"
        "/ban <ID> — Verificar si cuenta está baneada\n"
        "/gremio <ID> <región> — Info del gremio\n"
        "/mascota <ID> <región> — Info de la mascota\n"
        "/honor <ID> <región> — Puntuación de honor"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

# ── /limitetodos ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=["limitetodos"])
def limite_todos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    bot.reply_to(message,
        "🌐 *Selecciona el límite diario para TODOS los grupos:*",
        parse_mode="Markdown",
        reply_markup=teclado_limites("todos")
    )

# ── /limitegrupo ──────────────────────────────────────────────────────────────
@bot.message_handler(commands=["limitegrupo"])
def limite_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    markup = teclado_grupos_limite()
    if not markup:
        bot.reply_to(message, "⚠️ No hay grupos autorizados aún.")
        return
    bot.reply_to(message,
        "📋 *Selecciona el grupo al que quieres cambiar el límite:*",
        parse_mode="Markdown",
        reply_markup=markup
    )

# ── /limitepersona ────────────────────────────────────────────────────────────
@bot.message_handler(commands=["limitepersona"])
def limite_persona(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /limitepersona <ID>\nEjemplo: /limitepersona 123456789")
        return
    user_target = partes[1].replace("@", "")
    bot.reply_to(message,
        f"👤 *Selecciona el límite para el usuario* `{user_target}`:",
        parse_mode="Markdown",
        reply_markup=teclado_limites("persona", user_target)
    )

# ── Callbacks ─────────────────────────────────────────────────────────────────
@bot.callback_query_handler(func=lambda call: call.data.startswith("selgrupo_"))
def callback_sel_grupo(call):
    if not es_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ No tienes permiso.")
        return
    grupo_id = call.data.split("_")[1]
    bot.edit_message_text(
        f"📋 *Selecciona el límite para el grupo* `{grupo_id}`:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
        reply_markup=teclado_limites("grupo", grupo_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("lim_"))
def callback_limite(call):
    if not es_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ No tienes permiso.")
        return

    partes = call.data.split("_")
    tipo = partes[1]
    numero = int(partes[2])
    extra = partes[3] if len(partes) > 3 else ""

    config = cargar_config()

    if tipo == "delpersona":
        personales = config.get("limites_personales", {})
        if extra in personales:
            del personales[extra]
            config["limites_personales"] = personales
            guardar_config(config)
        bot.edit_message_text(
            f"✅ Límite personal del usuario `{extra}` eliminado. Usará el límite del grupo.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    elif tipo == "todos":
        config["limite_global"] = numero
        guardar_config(config)
        texto = f"✅ Límite global actualizado a *{numero}* uso(s)/día para todos los grupos." if numero > 0 else "✅ Límite global eliminado, todos sin límite."
        bot.edit_message_text(texto, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    elif tipo == "grupo":
        if "limites_por_grupo" not in config:
            config["limites_por_grupo"] = {}
        config["limites_por_grupo"][extra] = numero
        guardar_config(config)
        texto = f"✅ Grupo `{extra}` actualizado a *{numero}* uso(s)/día." if numero > 0 else f"✅ Límite del grupo `{extra}` eliminado."
        bot.edit_message_text(texto, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    elif tipo == "persona":
        if "limites_personales" not in config:
            config["limites_personales"] = {}
        config["limites_personales"][extra] = numero
        guardar_config(config)
        texto = f"✅ Usuario `{extra}` actualizado a *{numero}* uso(s)/día." if numero > 0 else f"✅ Límite del usuario `{extra}` eliminado."
        bot.edit_message_text(texto, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    bot.answer_callback_query(call.id, f"✅ Aplicado.")

# ── /verlimites ───────────────────────────────────────────────────────────────
@bot.message_handler(commands=["verlimites"])
def ver_limites(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    texto = f"⚠️ *Límite global:* {config.get('limite_global', 1)} uso(s)/día\n\n"

    por_grupo = config.get("limites_por_grupo", {})
    if por_grupo:
        texto += "*Límites por grupo:*\n"
        for gid, lim in por_grupo.items():
            texto += f"• `{gid}`: {lim} uso(s)/día\n"
        texto += "\n"

    personales = config.get("limites_personales", {})
    if personales:
        texto += "*Límites personales:*\n"
        for uid, lim in personales.items():
            texto += f"• `{uid}`: {lim} uso(s)/día\n"

    if not por_grupo and not personales:
        texto += "Solo aplica el límite global."

    bot.reply_to(message, texto, parse_mode="Markdown")

# ── Grupos ────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["addgrupo"])
def add_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /addgrupo <ID del grupo>")
        return
    try:
        grupo_id = int(partes[1])
        grupos = cargar_grupos()
        if grupo_id in grupos:
            bot.reply_to(message, "⚠️ Ese grupo ya está autorizado.")
        else:
            grupos.append(grupo_id)
            guardar_grupos(grupos)
            bot.reply_to(message, f"✅ Grupo `{grupo_id}` autorizado correctamente.")
    except ValueError:
        bot.reply_to(message, "❌ El ID debe ser un número.")

@bot.message_handler(commands=["delgrupo"])
def del_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /delgrupo <ID del grupo>")
        return
    try:
        grupo_id = int(partes[1])
        grupos = cargar_grupos()
        if grupo_id not in grupos:
            bot.reply_to(message, "⚠️ Ese grupo no está en la lista.")
        else:
            grupos.remove(grupo_id)
            guardar_grupos(grupos)
            bot.reply_to(message, f"✅ Grupo `{grupo_id}` eliminado correctamente.")
    except ValueError:
        bot.reply_to(message, "❌ El ID debe ser un número.")

@bot.message_handler(commands=["listagrupos"])
def lista_grupos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    grupos = cargar_grupos()
    if not grupos:
        bot.reply_to(message, "📋 No hay grupos autorizados.")
    else:
        texto = "📋 *Grupos autorizados:*\n\n"
        for g in grupos:
            texto += f"• `{g}`\n"
        bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["resetusos"])
def reset_usos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    guardar_usos({})
    bot.reply_to(message, "✅ Usos de todos los usuarios reseteados.")

# ── Encender / Apagar ─────────────────────────────────────────────────────────
def teclado_grupos_onoff(accion):
    grupos = cargar_grupos()
    if not grupos:
        return None
    markup = InlineKeyboardMarkup()
    for g in grupos:
        markup.add(InlineKeyboardButton(f"Grupo {g}", callback_data=f"onoff_{accion}_{g}"))
    return markup

@bot.message_handler(commands=["apagar"])
def apagar_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    markup = teclado_grupos_onoff("apagar")
    if not markup:
        bot.reply_to(message, "⚠️ No hay grupos autorizados.")
        return
    bot.reply_to(message, "🔴 *Selecciona el grupo a apagar:*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=["encender"])
def encender_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    markup = teclado_grupos_onoff("encender")
    if not markup:
        bot.reply_to(message, "⚠️ No hay grupos autorizados.")
        return
    bot.reply_to(message, "🟢 *Selecciona el grupo a encender:*", parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(commands=["apagarTodo"])
def apagar_todo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["bot_activo"] = False
    guardar_config(config)
    bot.reply_to(message, "🔴 Bot desactivado en *todos* los grupos.", parse_mode="Markdown")

@bot.message_handler(commands=["encenderTodo"])
def encender_todo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["bot_activo"] = True
    config["grupos_apagados"] = []
    guardar_config(config)
    bot.reply_to(message, "🟢 Bot activado en *todos* los grupos.", parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("onoff_"))
def callback_onoff(call):
    if not es_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ No tienes permiso.")
        return
    partes = call.data.split("_")
    accion = partes[1]
    grupo_id = int(partes[2])
    config = cargar_config()
    apagados = config.get("grupos_apagados", [])

    if accion == "apagar":
        if grupo_id not in apagados:
            apagados.append(grupo_id)
        config["grupos_apagados"] = apagados
        guardar_config(config)
        bot.edit_message_text(
            f"🔴 Bot desactivado en el grupo `{grupo_id}`.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    elif accion == "encender":
        if grupo_id in apagados:
            apagados.remove(grupo_id)
        config["grupos_apagados"] = apagados
        guardar_config(config)
        bot.edit_message_text(
            f"🟢 Bot activado en el grupo `{grupo_id}`.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    bot.answer_callback_query(call.id)

# ── Bloqueo de cuentas FF ─────────────────────────────────────────────────────
@bot.message_handler(commands=["bloquear"])
def bloquear_id(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /bloquear <ID>\nEjemplo: /bloquear 61668891")
        return
    player_id = partes[1]
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    if str(player_id) in [str(x) for x in bloqueados]:
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` ya está bloqueada.", parse_mode="Markdown")
    else:
        bloqueados.append(str(player_id))
        config["ids_bloqueados"] = bloqueados
        guardar_config(config)
        bot.reply_to(message, f"🚫 Cuenta `{player_id}` bloqueada correctamente.", parse_mode="Markdown")

@bot.message_handler(commands=["desbloquear"])
def desbloquear_id(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /desbloquear <ID>\nEjemplo: /desbloquear 61668891")
        return
    player_id = partes[1]
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    if str(player_id) not in [str(x) for x in bloqueados]:
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` no está bloqueada.", parse_mode="Markdown")
    else:
        bloqueados.remove(str(player_id))
        config["ids_bloqueados"] = bloqueados
        guardar_config(config)
        bot.reply_to(message, f"✅ Cuenta `{player_id}` desbloqueada correctamente.", parse_mode="Markdown")

@bot.message_handler(commands=["listabloqueados"])
def lista_bloqueados(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    if not bloqueados:
        bot.reply_to(message, "📋 No hay cuentas bloqueadas.")
    else:
        texto = "🚫 *Cuentas bloqueadas:*\n\n"
        for b in bloqueados:
            texto += f"• `{b}`\n"
        bot.reply_to(message, texto, parse_mode="Markdown")

# ── Usuarios Premium ──────────────────────────────────────────────────────────
@bot.message_handler(commands=["addpremium"])
def add_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /addpremium <ID de Telegram>\nEjemplo: /addpremium 123456789")
        return
    try:
        user_id = int(partes[1])
        config = cargar_config()
        premium = config.get("usuarios_premium", {})
        from datetime import timedelta
        expira = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        premium[str(user_id)] = expira
        config["usuarios_premium"] = premium
        guardar_config(config)
        bot.reply_to(message,
            f"👑 Usuario `{user_id}` agregado como Premium.\n"
            f"📅 Expira: `{expira}`",
            parse_mode="Markdown"
        )
    except ValueError:
        bot.reply_to(message, "❌ El ID debe ser un número.")

@bot.message_handler(commands=["delpremium"])
def del_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    if not premium:
        bot.reply_to(message, "⚠️ No hay usuarios Premium.")
        return

    # Si viene con ID directo lo quita sin botones
    partes = message.text.split()
    if len(partes) >= 2:
        try:
            user_id = int(partes[1])
            if str(user_id) not in premium:
                bot.reply_to(message, "⚠️ Ese usuario no es Premium.")
            else:
                del premium[str(user_id)]
                config["usuarios_premium"] = premium
                guardar_config(config)
                bot.reply_to(message, f"✅ Usuario `{user_id}` removido del Premium.", parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "❌ El ID debe ser un número.")
        return

    # Sin ID muestra botones con la lista
    markup = InlineKeyboardMarkup()
    for uid, expira in premium.items():
        expira_dt = datetime.strptime(expira, "%Y-%m-%d")
        dias = max(0, (expira_dt - datetime.now()).days)
        markup.add(InlineKeyboardButton(
            f"❌ {uid} — {dias} días restantes",
            callback_data=f"delprem_{uid}"
        ))
    bot.reply_to(message, "👑 *Selecciona el usuario al que quitar Premium:*",
        parse_mode="Markdown", reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delprem_"))
def callback_del_premium(call):
    if not es_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ No tienes permiso.")
        return
    uid = call.data.split("_")[1]
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    if uid in premium:
        del premium[uid]
        config["usuarios_premium"] = premium
        guardar_config(config)
        bot.edit_message_text(
            f"✅ Usuario `{uid}` removido del Premium.",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "⚠️ Ese usuario ya no es Premium.")
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=["listapremium"])
def lista_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    if not premium:
        bot.reply_to(message, "📋 No hay usuarios Premium.")
    else:
        texto = "👑 *Usuarios Premium:*\n\n"
        for uid, expira in premium.items():
            expira_dt = datetime.strptime(expira, "%Y-%m-%d")
            dias = max(0, (expira_dt - datetime.now()).days)
            texto += f"• `{uid}` — expira `{expira}` ({dias} días)\n"
        bot.reply_to(message, texto, parse_mode="Markdown")

# ── Mantenimiento ─────────────────────────────────────────────────────────────
@bot.message_handler(commands=["mantenimiento"])
def activar_mantenimiento(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["mantenimiento"] = True
    guardar_config(config)
    bot.reply_to(message,
        "🔧 *Modo mantenimiento activado.*\n\n"
        "Los usuarios verán un mensaje de mantenimiento al usar /like.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["sinmantenimiento"])
def desactivar_mantenimiento(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["mantenimiento"] = False
    guardar_config(config)
    bot.reply_to(message,
        "✅ *Mantenimiento desactivado.*\n\n"
        "El bot está funcionando con normalidad.",
        parse_mode="Markdown"
    )

# ── Control de APIs ───────────────────────────────────────────────────────────
@bot.message_handler(commands=["activarapi1"])
def activar_api1(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = "api1"
    guardar_config(config)
    usos = get_usos_api()
    bot.reply_to(message,
        f"✅ *API 1 activada* (límite 30 usos/día)\n"
        f"📊 Usos hoy: {usos.get('api1', 0)}/30",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["activarapi2"])
def activar_api2(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = "api2"
    guardar_config(config)
    usos = get_usos_api()
    bot.reply_to(message,
        f"✅ *API 2 activada* (límite 200 usos/día)\n"
        f"📊 Usos hoy: {usos.get('api2', 0)}/200",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["desactivarapi"])
def desactivar_api(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = "ninguna"
    guardar_config(config)
    bot.reply_to(message,
        "🔴 *Ambas APIs desactivadas.*\n"
        "Nadie puede usar /like hasta que actives una.",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["verapi"])
def ver_api(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    api = config.get("api_activa", "api1")
    usos = get_usos_api()
    if api == "api1":
        texto = f"🟢 *API activa: API 1* (límite 30/día)\n📊 Usos hoy: {usos.get('api1', 0)}/30"
    elif api == "api2":
        texto = f"🟢 *API activa: API 2* (límite 200/día)\n📊 Usos hoy: {usos.get('api2', 0)}/200"
    else:
        texto = "🔴 *Ambas APIs desactivadas.*"
    bot.reply_to(message, texto, parse_mode="Markdown")

# ── /id ───────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["id"])
def get_id(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    # Si es una respuesta a un mensaje, muestra el ID de ese usuario
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        bot.reply_to(message,
            f"👤 *ID de* `{user.first_name}`*:*\n`{user.id}`",
            parse_mode="Markdown"
        )
    # Si viene con @usuario como argumento
    elif len(message.text.split()) > 1:
        bot.reply_to(message,
            "⚠️ Para obtener el ID de un usuario, responde a uno de sus mensajes con /id",
            parse_mode="Markdown"
        )
    # Sin argumentos muestra el ID del grupo
    else:
        if message.chat.type in ["group", "supergroup"]:
            bot.reply_to(message,
                f"📋 *ID del grupo:*\n`{message.chat.id}`",
                parse_mode="Markdown"
            )
        else:
            bot.reply_to(message,
                f"📋 *Tu ID:*\n`{message.from_user.id}`",
                parse_mode="Markdown"
            )

# ── /info ─────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["info"])
def info_jugador(message):
    if not es_grupo(message):
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /info <ID> <región>\nEjemplo: /info 106540507 us\n\nRegiones: us, br, sg, ru, id, tw, vn, th, me, pk, ind, bd")
        return

    player_id = partes[1]
    region = partes[2].lower()

    bot.reply_to(message, f"🔍 Buscando información de `{player_id}`...", parse_mode="Markdown")

    try:
        response = requests.get(HL_API_URL, params={
            "sectionName": "AllData",
            "PlayerUid": player_id,
            "region": region,
            "useruid": HL_USER_UID,
            "api": HL_API_KEY
        }, timeout=15)
        data = response.json()

        if "error" in data:
            bot.reply_to(message, f"⚠️ Error: {data['error']}")
            return

        r = data.get("result", {})
        b = r.get("AccountInfo", {})
        g = r.get("GuildInfo", {})
        s = r.get("socialinfo", {})
        pet = r.get("petInfo", {})

        nombre = b.get('AccountName', 'N/A').replace('*', '').replace('_', '').replace('`', '').replace('[', '')
        firma = s.get('AccountSignature', 'N/A').replace('*', '').replace('_', '').replace('`', '').replace('[', '')
        gremio_nombre = g.get('GuildName', 'N/A').replace('*', '').replace('_', '').replace('`', '').replace('[', '') if g else 'N/A'

        mensaje = (
            f"📋 *Información de cuenta*\n\n"
            f"👤 *Nombre:* {nombre}\n"
            f"🆔 *UID:* `{player_id}`\n"
            f"🌎 *Región:* {b.get('AccountRegion', region.upper())}\n"
            f"⭐ *Nivel:* {b.get('AccountLevel', 'N/A')} (EXP: {b.get('AccountEXP', 'N/A')})\n"
            f"❤️ *Likes:* {b.get('AccountLikes', 'N/A')}\n"
            f"🏆 *Rango BR:* {b.get('BrRankPoint', 'N/A')}\n"
            f"🎯 *Rango CS:* {b.get('CsRankPoint', 'N/A')}\n"
            f"🔥 *OB:* {b.get('ReleaseVersion', 'N/A')}\n"
            f"🎖️ *Insignias BP:* {b.get('AccountBPBadges', 'N/A')}\n"
            f"⚖️ *Honor:* {r.get('creditScoreInfo', {}).get('creditScore', 'N/A')}\n"
            f"👤 *Género:* {'Masculino' if s.get('Gender') == 'Gender_MALE' else 'Femenino'}\n"
            f"✍️ *Firma:* {firma}\n"
        )

        if g:
            mensaje += (
                f"\n🏰 *Gremio:* {gremio_nombre}\n"
                f"👥 *Miembros:* {g.get('GuildMember', 'N/A')}/{g.get('GuildCapacity', 'N/A')}\n"
                f"⭐ *Nivel gremio:* {g.get('GuildLevel', 'N/A')}\n"
            )

        if pet:
            mensaje += f"\n🐾 *Mascota nivel:* {pet.get('level', 'N/A')}\n"

        mensaje += f"\nCreador: @sebas992269"

        bot.reply_to(message, mensaje, parse_mode="Markdown")

    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏱️ La API tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")
@bot.message_handler(commands=["comprar"])
def comprar_vip(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇨🇴 Colombia", callback_data="pais_colombia"))
    markup.add(InlineKeyboardButton("🌎 Otro país", callback_data="pais_otro"))
    bot.reply_to(message,
        "👑 *Membresía VIP - 1 mes*\n\n"
        "✅ Sin límite de usos diarios\n"
        "✅ Acceso aunque el bot esté apagado\n"
        "✅ Insignia VIP en cada respuesta\n\n"
        "🌍 *¿De qué país eres?*",
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "pais_colombia")
def pago_colombia(call):
    bot.answer_callback_query(call.id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📸 Ya pagué, enviar comprobante", callback_data="enviar_comprobante"))
    bot.edit_message_text(
        f"🇨🇴 *Pago para Colombia - Llave*\n\n"
        f"👑 *Membresía VIP - 1 mes*\n\n"
        f"💰 Monto: *${PRECIO_VIP_COP} COP*\n"
        f"🔑 Llave: `{LLAVE_COLOMBIA}`\n\n"
        f"1️⃣ Abre tu app bancaria\n"
        f"2️⃣ Busca *Llave* o *Transfiya*\n"
        f"3️⃣ Envía *${PRECIO_VIP_COP} COP* a `{LLAVE_COLOMBIA}`\n"
        f"4️⃣ Toma captura del comprobante\n"
        f"5️⃣ Haz clic en *Ya pagué*\n\n"
        f"Creador: @sebas992269",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "pais_otro")
def pago_otro(call):
    bot.answer_callback_query(call.id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("💳 Pagar con PayPal", url=PAYPAL_LINK))
    markup.add(InlineKeyboardButton("📸 Ya pagué, enviar comprobante", callback_data="enviar_comprobante"))
    bot.edit_message_text(
        f"🌎 *Pago Internacional - PayPal*\n\n"
        f"👑 *Membresía VIP - 1 mes*\n\n"
        f"💰 Monto: *${PRECIO_VIP} USD*\n"
        f"_(incluye comisión PayPal)_\n\n"
        f"1️⃣ Haz clic en *Pagar con PayPal*\n"
        f"2️⃣ Envía exactamente *${PRECIO_VIP} USD*\n"
        f"3️⃣ Haz clic en *Ya pagué*\n\n"
        f"Creador: @sebas992269",
        call.message.chat.id, call.message.message_id,
        parse_mode="Markdown",
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "enviar_comprobante")
def pedir_comprobante(call):
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id,
        "📸 Envía una foto o captura de pantalla de tu comprobante de pago.\n\n"
        "El creador lo revisará y activará tu VIP en breve.\n\n"
        "⚠️ Usa el comando /comprobante seguido de tu mensaje si la foto no funciona."
    )

@bot.message_handler(content_types=["photo", "document"], func=lambda m: m.chat.type == "private" and m.from_user.id != ADMIN_ID)
def recibir_comprobante(message):
    user = message.from_user
    nombre = f"{user.first_name} {user.last_name or ''}".strip()

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("✅ Confirmar VIP", callback_data=f"vip_confirmar_{user.id}"),
        InlineKeyboardButton("❌ Rechazar", callback_data=f"vip_rechazar_{user.id}")
    )

    username = user.username or "sin username"
    caption = (
        f"💳 Solicitud de VIP\n\n"
        f"👤 Usuario: {nombre}\n"
        f"ID: {user.id}\n"
        f"Username: @{username}\n\n"
        f"Revisa el comprobante y confirma o rechaza."
    )

    try:
        if message.photo:
            bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption,
                reply_markup=markup)
        else:
            bot.send_document(ADMIN_ID, message.document.file_id, caption=caption,
                reply_markup=markup)

        bot.reply_to(message,
            "✅ Tu comprobante fue enviado al creador.\n"
            "Recibirás una notificación cuando sea revisado."
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("vip_confirmar_") or call.data.startswith("vip_rechazar_"))
def callback_vip(call):
    if not es_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "⛔ No tienes permiso.")
        return

    partes = call.data.split("_")
    accion = partes[1]
    user_id = int(partes[2])

    if accion == "confirmar":
        from datetime import timedelta
        config = cargar_config()
        premium = config.get("usuarios_premium", {})
        expira = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        premium[str(user_id)] = expira
        config["usuarios_premium"] = premium
        guardar_config(config)

        bot.edit_message_caption(
            f"✅ VIP confirmado para `{user_id}`\nExpira: `{expira}`",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
        try:
            bot.send_message(user_id,
                f"🎉 *¡Tu membresía VIP fue activada!*\n\n"
                f"✅ Tienes acceso VIP por 30 días\n"
                f"📅 Expira: `{expira}`\n\n"
                f"Gracias por tu compra. @sebas992269",
                parse_mode="Markdown"
            )
        except:
            pass

    elif accion == "rechazar":
        bot.edit_message_caption(
            f"❌ Pago rechazado para `{user_id}`",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )
        try:
            bot.send_message(user_id,
                "❌ *Tu comprobante fue rechazado.*\n\n"
                "El pago no pudo ser verificado.\n"
                "Contacta a @sebas992269 para más información.",
                parse_mode="Markdown"
            )
        except:
            pass

    bot.answer_callback_query(call.id)

def limpiar(texto):
    if not texto:
        return "N/A"
    return str(texto).replace('*','').replace('_','').replace('`','').replace('[','').replace(']','')

# ── /ban ──────────────────────────────────────────────────────────────────────
# ── /gremio ───────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["gremio"])
def info_gremio(message):
    if not es_grupo(message):
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /gremio <ID> <región>\nEjemplo: /gremio 106540507 us")
        return
    player_id = partes[1]
    region = partes[2].lower()
    bot.reply_to(message, f"🔍 Buscando gremio de `{player_id}`...", parse_mode="Markdown")
    try:
        response = requests.get(HL_API_URL, params={
            "sectionName": "GuildInfo",
            "PlayerUid": player_id,
            "region": region,
            "useruid": HL_USER_UID,
            "api": HL_API_KEY
        }, timeout=15)
        data = response.json()
        if "error" in data:
            bot.reply_to(message, f"⚠️ Error: {data['error']}")
            return
        g = data.get("result", {})
        mensaje = (
            f"🏰 *Información del Gremio*\n\n"
            f"📛 *Nombre:* {limpiar(g.get('GuildName'))}\n"
            f"🆔 *ID:* `{g.get('GuildID', 'N/A')}`\n"
            f"⭐ *Nivel:* {g.get('GuildLevel', 'N/A')}\n"
            f"👥 *Miembros:* {g.get('GuildMember', 'N/A')}/{g.get('GuildCapacity', 'N/A')}\n"
            f"👑 *Líder ID:* `{g.get('GuildOwner', 'N/A')}`\n\n"
            f"Creador: @sebas992269"
        )
        bot.reply_to(message, mensaje, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ── /mascota ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["mascota"])
def info_mascota(message):
    if not es_grupo(message):
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /mascota <ID> <región>\nEjemplo: /mascota 106540507 us")
        return
    player_id = partes[1]
    region = partes[2].lower()
    bot.reply_to(message, f"🔍 Buscando mascota de `{player_id}`...", parse_mode="Markdown")
    try:
        response = requests.get(HL_API_URL, params={
            "sectionName": "petInfo",
            "PlayerUid": player_id,
            "region": region,
            "useruid": HL_USER_UID,
            "api": HL_API_KEY
        }, timeout=15)
        data = response.json()
        if "error" in data:
            bot.reply_to(message, f"⚠️ Error: {data['error']}")
            return
        p = data.get("result", {})
        mensaje = (
            f"🐾 *Información de Mascota*\n\n"
            f"🆔 *ID mascota:* {p.get('id', 'N/A')}\n"
            f"⭐ *Nivel:* {p.get('level', 'N/A')}\n"
            f"✨ *EXP:* {p.get('exp', 'N/A')}\n"
            f"🎯 *Equipada:* {'Sí' if p.get('isSelected') else 'No'}\n\n"
            f"Creador: @sebas992269"
        )
        bot.reply_to(message, mensaje, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ── /honor ────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["honor"])
def info_honor(message):
    if not es_grupo(message):
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /honor <ID> <región>\nEjemplo: /honor 106540507 us")
        return
    player_id = partes[1]
    region = partes[2].lower()
    bot.reply_to(message, f"🔍 Buscando honor de `{player_id}`...", parse_mode="Markdown")
    try:
        response = requests.get(HL_API_URL, params={
            "sectionName": "creditScoreInfo",
            "PlayerUid": player_id,
            "region": region,
            "useruid": HL_USER_UID,
            "api": HL_API_KEY
        }, timeout=15)
        data = response.json()
        if "error" in data:
            bot.reply_to(message, f"⚠️ Error: {data['error']}")
            return
        c = data.get("result", {})
        score = c.get("creditScore", 0)
        if score >= 90:
            estado = "🟢 Excelente"
        elif score >= 70:
            estado = "🟡 Bueno"
        elif score >= 50:
            estado = "🟠 Regular"
        else:
            estado = "🔴 Malo"
        mensaje = (
            f"⚖️ *Puntuación de Honor*\n\n"
            f"🆔 *UID:* `{player_id}`\n"
            f"📊 *Honor:* {score}/100\n"
            f"📋 *Estado:* {estado}\n\n"
            f"Creador: @sebas992269"
        )
        bot.reply_to(message, mensaje, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

# ── AutoLike ──────────────────────────────────────────────────────────────────
@bot.message_handler(commands=["addautolike"])
def add_autolike(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /addautolike <ID> <región>\nEjemplo: /addautolike 106540507 us")
        return
    player_id = partes[1]
    region = partes[2].lower()
    cuentas = cargar_autolike()
    if any(c["id"] == player_id for c in cuentas):
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` ya está en autolike.", parse_mode="Markdown")
        return
    cuentas.append({"id": player_id, "region": region})
    guardar_autolike(cuentas)

    # Enviar likes inmediatamente
    bot.reply_to(message, f"⏳ Enviando likes ahora a `{player_id}`...", parse_mode="Markdown")
    exito = enviar_likes_auto(player_id, region)
    if exito:
        bot.send_message(message.chat.id,
            f"✅ Cuenta `{player_id}` agregada al autolike.\n"
            f"❤️ Likes enviados ahora.\n"
            f"🔄 Se repetirá cada 24 horas a esta misma hora.",
            parse_mode="Markdown"
        )
    else:
        bot.send_message(message.chat.id,
            f"✅ Cuenta `{player_id}` agregada al autolike.\n"
            f"⚠️ No se pudieron enviar likes ahora (API no disponible).\n"
            f"🔄 Se intentará cada 24 horas.",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=["delautolike"])
def del_autolike(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /delautolike <ID>\nEjemplo: /delautolike 106540507")
        return
    player_id = partes[1]
    cuentas = cargar_autolike()
    nuevas = [c for c in cuentas if c["id"] != player_id]
    if len(nuevas) == len(cuentas):
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` no está en autolike.", parse_mode="Markdown")
        return
    guardar_autolike(nuevas)
    bot.reply_to(message, f"✅ Cuenta `{player_id}` eliminada del autolike.", parse_mode="Markdown")

@bot.message_handler(commands=["listaautolike"])
def lista_autolike(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    cuentas = cargar_autolike()
    if not cuentas:
        bot.reply_to(message, "📋 No hay cuentas en autolike.")
        return
    texto = "🔄 *Cuentas en AutoLike:*\n\n"
    for c in cuentas:
        texto += f"• `{c['id']}` — Región: {c['region'].upper()}\n"
    bot.reply_to(message, texto, parse_mode="Markdown")

print("🤖 Bot iniciado...")
try:
    me = bot.get_me()
    print(f"✅ Conectado como: @{me.username}")
except Exception as e:
    print(f"⚠️ No se pudo obtener el usuario del bot: {e}")
hilo_autolike = threading.Thread(target=ejecutar_autolike, daemon=True)
hilo_autolike.start()
bot.infinity_polling()
