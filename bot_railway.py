import telebot
import requests
import json
import os
import time
from datetime import datetime, timedelta
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

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

def bot_activo_en(chat_id):
    config = cargar_config()
    if not config.get("bot_activo", True):
        return False
    return chat_id not in config.get("grupos_apagados", [])

def es_grupo(message):
    if message.from_user.id == ADMIN_ID:
        return True
    return message.chat.type in ["group", "supergroup"]

def buscar_info_jugador(player_id):
    if not HL_USER_UID or not HL_API_KEY:
        return None
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
    print("⚠️ Advertencia: HL_USER_UID o HL_API_KEY no configurados. Comandos /info, /gremio, /mascota no funcionarán.")

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
@bot.message_handler(func=lambda m: m.chat.type == "private" and m.from_user.id != ADMIN_ID and not (m.text and (m.text.startswith("/start") or m.text.startswith("/comprar") or m.text.startswith("/miid") or m.text.startswith("/like") or m.text.startswith("/info"))))
def solo_privado(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("👑 Comprar VIP", url=f"https://t.me/{bot.get_me().username}?start=comprar"))
    bot.reply_to(message,
        "🔒 *Bot privado*\n\n"
        "Este bot funciona principalmente en grupos autorizados.\n\n"
        "📋 *Comandos disponibles en privado:*\n"
        "• /start - Menú principal\n"
        "• /miid - Ver tu ID\n"
        "• /like <ID> - Enviar likes (si eres premium)\n"
        "• /info <ID> - Info de jugador\n\n"
        "💡 Para acceso completo, únete a un grupo autorizado.\n\n"
        "Creador: @sebas992269",
        parse_mode="Markdown",
        reply_markup=markup
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
        "🚀 *Desplegado en Railway* - Sin suspensiones\n\n"
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

    if not bot_activo_en(message.chat.id) and not es_admin(message.from_user.id) and not es_premium(message.from_user.id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("👑 Comprar VIP", url=f"https://t.me/{bot.get_me().username}?start=comprar"))
        bot.reply_to(message,
            "🔒 *Este servicio requiere membresía Premium.*\n\n"
            "El bot está apagado en este grupo.\n"
            "Contacta a @sebas992269 para adquirir premium.",
            parse_mode="Markdown",
            reply_markup=markup
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
            "Contacta a @sebas992269."
        )
        return

    bot.reply_to(message, "🔍 Enviando likes...")

    try:
        response = requests.get(API_URL, params={"key": api_key, "id": player_id}, timeout=15)
        data = response.json()

        # Nueva condición correcta para API en portugués
        if response.status_code == 200 and data.get("sucesso") is True:
            registrar_uso(message.from_user.id, message.chat.id)
            
            try:
                info = data["data"][0]
                conta = info["conta"]
                likes = info["likes"]
                likes_enviados = likes.get("enviadas", 0)
                antes = likes.get("antes", 0)
                depois = likes.get("depois", 0)  # ← Correcto - usar valor real de la API
                nick = limpiar(conta.get("nome_conta", "N/A"))
                region = conta.get("region", "N/A").upper()
                
                # Debug para verificar valores
                print(f"[DEBUG] Likes - Antes: {antes}, Enviados: {likes_enviados}, Depois: {depois}")

                if likes_enviados == 0:
                    mensaje = (
                        f"⚠️ Esta cuenta ya tiene el máximo de likes hoy.\n\n"
                        f"👤 Nick: {nick}\n"
                        f"🌎 Región: {region}\n\n"
                        f"Intenta más tarde 🕐"
                    )
                else:
                    insignia = f"👑 USUARIO PREMIUM — {dias_restantes_premium(message.from_user.id)} días restantes\n\n" if es_premium(message.from_user.id) else ""
                    
                    if es_admin(message.from_user.id):
                        mensaje = f"╔══ 👑 EL CREADOR ESTA USANDO EL SISTEMA ══╗\n\n"
                    else:
                        mensaje = insignia
                    
                    mensaje += (
                        f"🚀 ME GUSTA ENVIADOS CON ÉXITO! ✅\n\n"
                        f"👤 Nick: {nick}\n"
                        f"🌎 Región: {region}\n\n"
                        f"✨ RESULTADO 🔥\n"
                        f"➖ Antes: {antes}\n"
                        f"➕ Después: {depois}\n"
                        f"🎉 Enviados: {likes_enviados} me gusta!\n\n"
                    )
                    
                    if es_admin(message.from_user.id):
                        mensaje += "╚════════════════╝\n"
                    
                    mensaje += "🚀 Desplegado en Railway\nCreador: @sebas992269"
                    
            except (KeyError, IndexError, TypeError) as e:
                print(f"[DEBUG] Error parseando respuesta: {e}")
                mensaje = "✅ Likes enviados, pero no se pudo leer el detalle."
        else:
            # Mostrar error real de la API en portugués
            error_msg = data.get("mensagem") or data.get("error") or data.get("message") or "Error desconocido"
            mensaje = f"❌ Error de API: {error_msg}"

        markup = InlineKeyboardMarkup([[InlineKeyboardButton("👑 Platform - Principal", url="https://t.me/bunlatrixvip")]])
        bot.reply_to(message, mensaje, reply_markup=markup)

    except requests.exceptions.Timeout:
        bot.reply_to(message, "⏱️ La API tardó demasiado. Intenta de nuevo.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error de conexión: {str(e)}")

# ── PANEL ADMIN ──────────────────────────────────────────────────────────────
@bot.message_handler(commands=["admin"])
def panel_admin(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    grupos = cargar_grupos()
    texto = (
        "🛠 *Panel de Administración*\n"
        "🚀 *Desplegado en Railway*\n\n"
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
        "*APIs:*\n"
        "/activarapi1 — Activar API 1 (límite 30)\n"
        "/activarapi2 — Activar API 2 (límite 200)\n"
        "/desactivarapi — Desactivar ambas APIs\n"
        "/verapi — Ver API activa\n\n"
        "*Utilidades:*\n"
        "/id — ID del grupo\n"
        "/miid — Tu información\n"
        "/testadmin — Verificar admin"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["addgrupo"])
def add_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /addgrupo <ID>\nEjemplo: /addgrupo -1001234567890")
        return
    try:
        grupo_id = int(partes[1])
        grupos = cargar_grupos()
        if grupo_id not in grupos:
            grupos.append(grupo_id)
            guardar_grupos(grupos)
            bot.reply_to(message, f"✅ Grupo {grupo_id} agregado correctamente.")
        else:
            bot.reply_to(message, f"⚠️ El grupo {grupo_id} ya está autorizado.")
    except ValueError:
        bot.reply_to(message, "❌ ID de grupo inválido.")

@bot.message_handler(commands=["delgrupo"])
def del_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /delgrupo <ID>\nEjemplo: /delgrupo -1001234567890")
        return
    try:
        grupo_id = int(partes[1])
        grupos = cargar_grupos()
        if grupo_id in grupos:
            grupos.remove(grupo_id)
            guardar_grupos(grupos)
            bot.reply_to(message, f"✅ Grupo {grupo_id} eliminado correctamente.")
        else:
            bot.reply_to(message, f"⚠️ El grupo {grupo_id} no está en la lista.")
    except ValueError:
        bot.reply_to(message, "❌ ID de grupo inválido.")

@bot.message_handler(commands=["listagrupos"])
def lista_grupos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    grupos = cargar_grupos()
    if not grupos:
        bot.reply_to(message, "📋 No hay grupos autorizados.")
        return
    texto = "📋 *Grupos autorizados:*\n\n"
    for i, grupo in enumerate(grupos, 1):
        texto += f"{i}. `{grupo}`\n"
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["id"])
def get_id(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    if message.reply_to_message:
        # ID del usuario al que responde
        user_id = message.reply_to_message.from_user.id
        username = message.reply_to_message.from_user.username or "Sin username"
        first_name = message.reply_to_message.from_user.first_name or "Sin nombre"
        bot.reply_to(message, 
            f"👤 *Usuario:* {first_name}\n"
            f"🆔 *ID:* `{user_id}`\n"
            f"📝 *Username:* @{username}",
            parse_mode="Markdown"
        )
    else:
        # ID del grupo/chat actual
        chat_id = message.chat.id
        chat_title = getattr(message.chat, 'title', 'Chat privado')
        bot.reply_to(message,
            f"💬 *Chat:* {chat_title}\n"
            f"🆔 *ID:* `{chat_id}`",
            parse_mode="Markdown"
        )

@bot.message_handler(commands=["bloquear"])
def bloquear_cuenta(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /bloquear <ID>\nEjemplo: /bloquear 106540507")
        return
    
    player_id = partes[1]
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    
    if player_id not in bloqueados:
        bloqueados.append(player_id)
        config["ids_bloqueados"] = bloqueados
        guardar_config(config)
        bot.reply_to(message, f"✅ Cuenta `{player_id}` bloqueada correctamente.")
    else:
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` ya está bloqueada.")

@bot.message_handler(commands=["desbloquear"])
def desbloquear_cuenta(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /desbloquear <ID>\nEjemplo: /desbloquear 106540507")
        return
    
    player_id = partes[1]
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    
    if player_id in bloqueados:
        bloqueados.remove(player_id)
        config["ids_bloqueados"] = bloqueados
        guardar_config(config)
        bot.reply_to(message, f"✅ Cuenta `{player_id}` desbloqueada correctamente.")
    else:
        bot.reply_to(message, f"⚠️ La cuenta `{player_id}` no está bloqueada.")

@bot.message_handler(commands=["listabloqueados"])
def lista_bloqueados(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    bloqueados = config.get("ids_bloqueados", [])
    
    if not bloqueados:
        bot.reply_to(message, "📋 No hay cuentas bloqueadas.")
        return
    
    texto = "🚫 *Cuentas bloqueadas:*\n\n"
    for i, cuenta in enumerate(bloqueados, 1):
        texto += f"{i}. `{cuenta}`\n"
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["addpremium"])
def add_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /addpremium <ID> [días]\nEjemplo: /addpremium 123456789 30")
        return
    
    try:
        user_id = partes[1]
        dias = int(partes[2]) if len(partes) > 2 else 30
        
        fecha_expira = (datetime.now() + timedelta(days=dias)).strftime("%Y-%m-%d")
        
        config = cargar_config()
        premium = config.get("usuarios_premium", {})
        premium[user_id] = fecha_expira
        config["usuarios_premium"] = premium
        guardar_config(config)
        
        bot.reply_to(message, f"✅ Usuario `{user_id}` agregado como premium por {dias} días.\nExpira: {fecha_expira}")
    except ValueError:
        bot.reply_to(message, "❌ Número de días inválido.")

@bot.message_handler(commands=["delpremium"])
def del_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /delpremium <ID>\nEjemplo: /delpremium 123456789")
        return
    
    user_id = partes[1]
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    
    if user_id in premium:
        del premium[user_id]
        config["usuarios_premium"] = premium
        guardar_config(config)
        bot.reply_to(message, f"✅ Usuario `{user_id}` eliminado de premium.")
    else:
        bot.reply_to(message, f"⚠️ El usuario `{user_id}` no es premium.")

@bot.message_handler(commands=["listapremium"])
def lista_premium(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    premium = config.get("usuarios_premium", {})
    
    if not premium:
        bot.reply_to(message, "📋 No hay usuarios premium.")
        return
    
    texto = "👑 *Usuarios Premium:*\n\n"
    for i, (user_id, fecha) in enumerate(premium.items(), 1):
        try:
            expira = datetime.strptime(fecha, "%Y-%m-%d")
            dias_restantes = (expira - datetime.now()).days
            if dias_restantes > 0:
                texto += f"{i}. `{user_id}` - {dias_restantes} días\n"
            else:
                texto += f"{i}. `{user_id}` - ⚠️ Expirado\n"
        except:
            texto += f"{i}. `{user_id}` - Error en fecha\n"
    
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["mantenimiento"])
def activar_mantenimiento(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["mantenimiento"] = True
    guardar_config(config)
    bot.reply_to(message, "🔧 Modo mantenimiento ACTIVADO.\nSolo admins y premium pueden usar el bot.")

@bot.message_handler(commands=["sinmantenimiento"])
def desactivar_mantenimiento(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["mantenimiento"] = False
    guardar_config(config)
    bot.reply_to(message, "✅ Modo mantenimiento DESACTIVADO.\nTodos los usuarios pueden usar el bot.")

@bot.message_handler(commands=["verapi"])
def ver_api(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    api_activa = config.get("api_activa", "api1")
    usos = config.get("usos_api", {"api1": 0, "api2": 0, "fecha": ""})
    
    texto = (
        f"🔧 *Estado de APIs:*\n\n"
        f"📡 *API Activa:* {api_activa.upper()}\n"
        f"📊 *Usos hoy:*\n"
        f"   • API1: {usos.get('api1', 0)}\n"
        f"   • API2: {usos.get('api2', 0)}\n"
        f"📅 *Fecha:* {usos.get('fecha', 'N/A')}"
    )
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["activarapi1"])
def activar_api1(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = "api1"
    guardar_config(config)
    bot.reply_to(message, "✅ API1 activada (límite 30 usos).")

@bot.message_handler(commands=["activarapi2"])
def activar_api2(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = "api2"
    guardar_config(config)
    bot.reply_to(message, "✅ API2 activada (límite 200 usos).")

@bot.message_handler(commands=["desactivarapi"])
def desactivar_api(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    config = cargar_config()
    config["api_activa"] = None
    guardar_config(config)
    bot.reply_to(message, "⚠️ APIs desactivadas. El bot no enviará likes.")

@bot.message_handler(commands=["limitetodos"])
def limite_todos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /limitetodos <número>\nEjemplo: /limitetodos 5\n0 = sin límite")
        return
    
    try:
        limite = int(partes[1])
        config = cargar_config()
        config["limite_global"] = limite
        guardar_config(config)
        
        if limite == 0:
            bot.reply_to(message, "✅ Límite global eliminado. Todos los usuarios sin límite.")
        else:
            bot.reply_to(message, f"✅ Límite global configurado a {limite} uso(s) por día.")
    except ValueError:
        bot.reply_to(message, "❌ Número inválido.")

@bot.message_handler(commands=["limitegrupo"])
def limite_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /limitegrupo <ID_grupo> <límite>\nEjemplo: /limitegrupo -1001234567890 3")
        return
    
    try:
        grupo_id = partes[1]
        limite = int(partes[2])
        config = cargar_config()
        
        if "limites_por_grupo" not in config:
            config["limites_por_grupo"] = {}
        
        config["limites_por_grupo"][grupo_id] = limite
        guardar_config(config)
        
        if limite == 0:
            bot.reply_to(message, f"✅ Grupo `{grupo_id}` sin límite.")
        else:
            bot.reply_to(message, f"✅ Grupo `{grupo_id}` configurado a {limite} uso(s) por día.")
    except ValueError:
        bot.reply_to(message, "❌ Número inválido.")

@bot.message_handler(commands=["limitepersona"])
def limite_persona(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    partes = message.text.split()
    if len(partes) < 3:
        bot.reply_to(message, "❌ Uso: /limitepersona <ID_usuario> <límite>\nEjemplo: /limitepersona 123456789 10")
        return
    
    try:
        user_id = partes[1]
        limite = int(partes[2])
        config = cargar_config()
        
        if "limites_personales" not in config:
            config["limites_personales"] = {}
        
        config["limites_personales"][user_id] = limite
        guardar_config(config)
        
        if limite == 0:
            bot.reply_to(message, f"✅ Usuario `{user_id}` sin límite.")
        else:
            bot.reply_to(message, f"✅ Usuario `{user_id}` configurado a {limite} uso(s) por día.")
    except ValueError:
        bot.reply_to(message, "❌ Número inválido.")

@bot.message_handler(commands=["verlimites"])
def ver_limites(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    config = cargar_config()
    limite_global = config.get("limite_global", 1)
    limites_grupos = config.get("limites_por_grupo", {})
    limites_personales = config.get("limites_personales", {})
    
    texto = f"📊 *Configuración de Límites:*\n\n"
    texto += f"🌐 *Global:* {limite_global} uso(s)/día\n\n"
    
    if limites_grupos:
        texto += "*Por Grupo:*\n"
        for grupo, limite in limites_grupos.items():
            texto += f"   • `{grupo}`: {limite}\n"
        texto += "\n"
    
    if limites_personales:
        texto += "*Personales:*\n"
        for user, limite in limites_personales.items():
            texto += f"   • `{user}`: {limite}\n"
    
    if not limites_grupos and not limites_personales:
        texto += "Sin límites específicos configurados."
    
    bot.reply_to(message, texto, parse_mode="Markdown")

@bot.message_handler(commands=["resetusos"])
def reset_usos(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    # Limpiar archivo de usos
    guardar_usos({})
    bot.reply_to(message, "✅ Usos de todos los usuarios reseteados.")

@bot.message_handler(commands=["apagar"])
def apagar_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    chat_id = message.chat.id
    config = cargar_config()
    grupos_apagados = config.get("grupos_apagados", [])
    
    if chat_id not in grupos_apagados:
        grupos_apagados.append(chat_id)
        config["grupos_apagados"] = grupos_apagados
        guardar_config(config)
        bot.reply_to(message, f"🔴 Bot APAGADO en este grupo.\nSolo admins y premium pueden usarlo.")
    else:
        bot.reply_to(message, "⚠️ El bot ya está apagado en este grupo.")

@bot.message_handler(commands=["encender"])
def encender_grupo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    chat_id = message.chat.id
    config = cargar_config()
    grupos_apagados = config.get("grupos_apagados", [])
    
    if chat_id in grupos_apagados:
        grupos_apagados.remove(chat_id)
        config["grupos_apagados"] = grupos_apagados
        guardar_config(config)
        bot.reply_to(message, f"🟢 Bot ENCENDIDO en este grupo.")
    else:
        bot.reply_to(message, "⚠️ El bot ya está encendido en este grupo.")

@bot.message_handler(commands=["apagarTodo"])
def apagar_todo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    config = cargar_config()
    config["bot_activo"] = False
    guardar_config(config)
    bot.reply_to(message, "🔴 Bot APAGADO en TODOS los grupos.\nSolo admins y premium pueden usarlo.")

@bot.message_handler(commands=["encenderTodo"])
def encender_todo(message):
    if not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ No tienes permiso.")
        return
    
    config = cargar_config()
    config["bot_activo"] = True
    config["grupos_apagados"] = []  # Limpiar grupos apagados individuales
    guardar_config(config)
    bot.reply_to(message, "🟢 Bot ENCENDIDO en TODOS los grupos.")

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

    # Buscar info del jugador usando HL Gaming API
    info = buscar_info_jugador(player_id)
    if info:
        nombre = limpiar(info.get("AccountName", "N/A"))
        region = info.get("AccountRegion", info.get("_region", "N/A")).upper()
        ob = info.get("ReleaseVersion", "N/A")
        likes = info.get("AccountLikes", "N/A")
        exp = info.get("AccountEXP", "N/A")
        create_ts = info.get("AccountCreateTime", 0)
        try:
            fecha_creacion = datetime.fromtimestamp(int(create_ts)).strftime("%d/%m/%Y - %H:%M:%S")
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
            f"🚀 Desplegado en Railway\n"
            f"Creador: @sebas992269"
        )
        bot.reply_to(message, mensaje, parse_mode="Markdown")
    else:
        bot.reply_to(message, "❌ No se pudo encontrar información del jugador.\n⚠️ Verifica que HL_USER_UID y HL_API_KEY estén configurados.")

@bot.message_handler(commands=["gremio"])
def gremio_comando(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /gremio <ID> [región]\nEjemplo: /gremio 106540507 us")
        return

    bot.reply_to(message, "🔍 Buscando información del gremio...")
    bot.reply_to(message, "⚠️ Función de gremio requiere configuración adicional de HL Gaming API.")

@bot.message_handler(commands=["mascota"])
def mascota_comando(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /mascota <ID> [región]\nEjemplo: /mascota 106540507 us")
        return

    bot.reply_to(message, "🔍 Buscando información de la mascota...")
    bot.reply_to(message, "⚠️ Función de mascota requiere configuración adicional de HL Gaming API.")

@bot.message_handler(commands=["honor"])
def honor_comando(message):
    if not es_grupo(message):
        return
    if not grupo_autorizado(message.chat.id) and not es_admin(message.from_user.id):
        bot.reply_to(message, "⛔ Este grupo no está autorizado.\nContacta al creador: @sebas992269")
        return

    partes = message.text.split()
    if len(partes) < 2:
        bot.reply_to(message, "❌ Uso: /honor <ID> [región]\nEjemplo: /honor 106540507 us")
        return

    bot.reply_to(message, "🔍 Buscando puntuación de honor...")
    bot.reply_to(message, "⚠️ Función de honor requiere configuración adicional de HL Gaming API.")

@bot.message_handler(commands=["miid"])
def mi_id(message):
    """Comando para que cualquier usuario vea su ID"""
    user_id = message.from_user.id
    username = message.from_user.username or "Sin username"
    first_name = message.from_user.first_name or "Sin nombre"
    
    bot.reply_to(message,
        f"👤 *Tu información:*\n\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📝 *Nombre:* {first_name}\n"
        f"📝 *Username:* @{username}\n\n"
        f"💡 *Tip:* Copia tu ID para configurarlo como admin",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=["testadmin"])
def test_admin(message):
    """Comando para verificar si eres admin"""
    user_id = message.from_user.id
    admin_id_config = ADMIN_ID
    
    if es_admin(user_id):
        bot.reply_to(message, 
            f"✅ *Eres ADMIN*\n\n"
            f"🆔 Tu ID: `{user_id}`\n"
            f"⚙️ Admin configurado: `{admin_id_config}`\n\n"
            f"🚀 Desplegado en Railway",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(message,
            f"❌ *NO eres admin*\n\n"
            f"🆔 Tu ID: `{user_id}`\n"
            f"⚙️ Admin configurado: `{admin_id_config}`\n\n"
            f"💡 Configura tu ID en las variables de entorno de Railway",
            parse_mode="Markdown"
        )

if __name__ == "__main__":
    print("🚀 Bot iniciado en Railway - Sin suspensiones!")
    
    # Eliminar webhook si existe (para migración desde Render)
    try:
        bot.remove_webhook()
        print("🔧 Webhook eliminado correctamente")
        time.sleep(2)  # Esperar un poco
    except Exception as e:
        print(f"⚠️ Error eliminando webhook: {e}")
    
    print(f"🤖 Bot: @{bot.get_me().username}")
    print("📊 Modo: Polling continuo")
    bot.infinity_polling()