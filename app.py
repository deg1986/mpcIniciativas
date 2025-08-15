# 🚀 MCP Server con Bot Robusto para Render
import os
import json
import threading
import asyncio
import time
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Configuración de logging más detallada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)
CORS(app)

# Configuración
NOCODB_BASE_URL = "https://nocodb.farmuhub.co/api/v2"
NOCODB_TABLE_ID = "m274d90cy3x6ra3"
NOCODB_TOKEN = "-kgNP5Q5G54nlDXPei7IO9PMMyE4pIgxYCi6o17Y"
TELEGRAM_TOKEN = "8309791895:AAGxfmPQ_yvgNY-kyMMDrKR0srb7c20KL5Q"

# Variables globales
bot_running = False
bot_start_time = None
bot_error_count = 0
user_states = {}
telegram_app = None

def get_initiatives():
    """Obtener iniciativas de NocoDB"""
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        params = {'limit': 50}
        
        response = requests.get(url, headers=headers, params=params, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            initiatives = data.get('list', [])
            logger.info(f"✅ Retrieved {len(initiatives)} initiatives from NocoDB")
            return {"success": True, "data": initiatives}
        else:
            logger.error(f"❌ NocoDB HTTP {response.status_code}: {response.text[:200]}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error fetching initiatives: {e}")
        return {"success": False, "error": str(e)}

def create_initiative(data):
    """Crear iniciativa en NocoDB"""
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=20)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Created initiative: {data.get('initiative_name', 'Unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Create failed HTTP {response.status_code}: {response.text[:200]}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error creating initiative: {e}")
        return {"success": False, "error": str(e)}

# ===== ENDPOINTS FLASK =====

@app.route('/')
def home():
    """Endpoint principal"""
    return jsonify({
        "name": "Initiatives MCP Server",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": {
            "enabled": bool(TELEGRAM_TOKEN),
            "running": bot_running,
            "start_time": bot_start_time,
            "error_count": bot_error_count
        }
    })

@app.route('/health')
def health():
    """Health check detallado"""
    nocodb_test = get_initiatives()
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "flask": "running",
            "nocodb": "ok" if nocodb_test.get('success') else "error",
            "telegram_bot": "running" if bot_running else "stopped"
        },
        "bot_info": {
            "running": bot_running,
            "start_time": bot_start_time,
            "error_count": bot_error_count,
            "active_sessions": len(user_states)
        },
        "nocodb_info": {
            "connection": "ok" if nocodb_test.get('success') else "failed",
            "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0,
            "error": nocodb_test.get('error') if not nocodb_test.get('success') else None
        }
    })

@app.route('/start-bot', methods=['POST'])
def start_bot_endpoint():
    """Endpoint para iniciar/reiniciar el bot"""
    global bot_running, bot_error_count
    
    if bot_running:
        return jsonify({
            "message": "Bot already running",
            "bot_running": True,
            "start_time": bot_start_time
        })
    
    try:
        success = start_bot_thread()
        return jsonify({
            "message": "Bot start attempted",
            "success": success,
            "bot_running": bot_running,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error starting bot via endpoint: {e}")
        return jsonify({
            "message": "Failed to start bot",
            "error": str(e),
            "bot_running": False
        }), 500

@app.route('/test')
def test():
    """Test completo del sistema"""
    nocodb_test = get_initiatives()
    
    return jsonify({
        "test": "OK",
        "timestamp": datetime.now().isoformat(),
        "nocodb": {
            "connection": "OK" if nocodb_test.get('success') else "FAILED",
            "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0,
            "error": nocodb_test.get('error') if not nocodb_test.get('success') else None
        },
        "telegram": {
            "token_configured": bool(TELEGRAM_TOKEN),
            "bot_running": bot_running,
            "start_time": bot_start_time,
            "error_count": bot_error_count
        }
    })

@app.route('/api/initiatives')
def api_initiatives():
    """API para obtener iniciativas"""
    data = get_initiatives()
    return jsonify(data)

@app.route('/api/create', methods=['POST'])
def api_create():
    """API para crear iniciativa"""
    if not request.json:
        return jsonify({"error": "JSON required"}), 400
    
    result = create_initiative(request.json)
    return jsonify(result)

# ===== BOT DE TELEGRAM ROBUSTO =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    logger.info(f"📱 /start command from user {update.effective_user.id}")
    
    text = """🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos disponibles:**
/iniciativas - Ver lista de iniciativas
/crear - Crear nueva iniciativa
/help - Ver esta ayuda

¿En qué puedo ayudarte?"""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info("✅ Start message sent successfully")
    except Exception as e:
        logger.error(f"❌ Error sending start message: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    logger.info(f"📱 /help command from user {update.effective_user.id}")
    
    text = """🆘 **Ayuda - Bot de Iniciativas**

**Comandos disponibles:**
• **/iniciativas** - Lista todas las iniciativas
• **/crear** - Proceso paso a paso para crear nueva iniciativa  
• **/help** - Mostrar esta ayuda

**Cómo usar:**
1. Escribe `/iniciativas` para ver todas las iniciativas
2. Escribe `/crear` para empezar a crear una nueva
3. Sigue las instrucciones paso a paso

**Soporte:** Si hay algún problema, contacta al administrador."""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info("✅ Help message sent successfully")
    except Exception as e:
        logger.error(f"❌ Error sending help message: {e}")

async def list_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciativas"""
    logger.info(f"📱 /iniciativas command from user {update.effective_user.id}")
    
    try:
        await update.message.reply_text("🔄 Obteniendo iniciativas...")
        
        data = get_initiatives()
        
        if not data.get("success"):
            error_msg = f"❌ **Error al obtener iniciativas**\n\nError: {data.get('error', 'Desconocido')}"
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            return
        
        initiatives = data.get("data", [])[:8]  # Máximo 8 para Telegram
        
        if not initiatives:
            await update.message.reply_text("📭 No hay iniciativas disponibles en este momento.")
            return
        
        text = f"🎯 **Lista de Iniciativas ({len(initiatives)})**\n\n"
        
        for i, init in enumerate(initiatives, 1):
            name = init.get('initiative_name', 'Sin nombre')
            owner = init.get('owner', 'Sin owner')
            team = init.get('team', 'Sin equipo')
            
            text += f"**{i}. {name}**\n"
            text += f"👤 {owner} • 👥 {team}\n\n"
        
        text += f"📋 *Mostrando las primeras {len(initiatives)} iniciativas*"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info(f"✅ Listed {len(initiatives)} initiatives successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in list_initiatives_command: {e}")
        await update.message.reply_text("❌ Error al obtener la lista de iniciativas. Intenta de nuevo.")

async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /crear"""
    user_id = update.effective_user.id
    logger.info(f"📱 /crear command from user {user_id}")
    
    user_states[user_id] = {'step': 'name', 'data': {}}
    
    text = """🆕 **Crear Nueva Iniciativa**

Te guiaré paso a paso para crear la iniciativa.

**Paso 1 de 6:** ¿Cuál es el nombre de la iniciativa?

*Escribe el nombre y presiona enviar*"""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info(f"✅ Started creation process for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error starting creation process: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto para la creación de iniciativas"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        text = """👋 **¡Hola!** 

Usa los siguientes comandos:
• `/help` - Ver ayuda completa
• `/iniciativas` - Ver lista
• `/crear` - Crear nueva iniciativa"""
        
        await update.message.reply_text(text, parse_mode='Markdown')
        return
    
    state = user_states[user_id]
    step = state['step']
    text = update.message.text.strip()
    
    logger.info(f"📝 Processing step '{step}' for user {user_id}")
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            response = f"✅ **Nombre guardado:** {text}\n\n**Paso 2 de 6:** ¿Cuál es la descripción de la iniciativa?"
            
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            response = "✅ **Descripción guardada**\n\n**Paso 3 de 6:** ¿Cuál es el KPI principal?\n\n*Ejemplos: Productividad, Ventas, Satisfacción del Cliente*"
            
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            response = f"✅ **KPI guardado:** {text}\n\n**Paso 4 de 6:** ¿En qué portal se ejecutará?\n\n*Ejemplos: Admin, Customer, Partner*"
            
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            response = f"✅ **Portal guardado:** {text}\n\n**Paso 5 de 6:** ¿Quién es el owner/responsable de la iniciativa?"
            
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            response = f"✅ **Owner guardado:** {text}\n\n**Paso 6 de 6:** ¿Qué equipo será responsable?\n\n*Ejemplos: Product, Engineering, Marketing*"
            
        elif step == 'team':
            state['data']['team'] = text
            await finish_creation(update, user_id)
            return
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error handling text for user {user_id}: {e}")
        await update.message.reply_text("❌ Error procesando tu respuesta. Intenta de nuevo.")
        if user_id in user_states:
            del user_states[user_id]

async def finish_creation(update: Update, user_id: int):
    """Finalizar la creación de la iniciativa"""
    try:
        state = user_states[user_id]
        data = state['data']
        
        logger.info(f"🎯 Finishing creation for user {user_id}: {data.get('initiative_name')}")
        
        # Agregar valores por defecto para métricas
        data.update({
            'reach': 0.5,
            'impact': 0.5, 
            'confidence': 0.5,
            'effort': 0.5
        })
        
        # Mostrar resumen
        summary = f"""📋 **Resumen de la Iniciativa:**

**Nombre:** {data['initiative_name']}
**Descripción:** {data['description']}
**KPI:** {data['main_kpi']}
**Portal:** {data['portal']}
**Owner:** {data['owner']}
**Equipo:** {data['team']}

⏳ **Creando iniciativa...**"""
        
        await update.message.reply_text(summary, parse_mode='Markdown')
        
        # Crear la iniciativa
        result = create_initiative(data)
        
        if result.get("success"):
            success_text = f"""🎉 **¡Iniciativa creada exitosamente!**

**{data['initiative_name']}** ha sido agregada al sistema.

Usa `/iniciativas` para ver todas las iniciativas."""
            
            await update.message.reply_text(success_text, parse_mode='Markdown')
            logger.info(f"✅ Successfully created initiative for user {user_id}")
        else:
            error_text = f"""❌ **Error al crear la iniciativa**

**Error:** {result.get('error', 'Error desconocido')}

Intenta de nuevo con `/crear`"""
            
            await update.message.reply_text(error_text, parse_mode='Markdown')
            logger.error(f"❌ Failed to create initiative for user {user_id}: {result.get('error')}")
        
        # Limpiar estado del usuario
        if user_id in user_states:
            del user_states[user_id]
    
    except Exception as e:
        logger.error(f"❌ Error finishing creation for user {user_id}: {e}")
        error_text = f"❌ **Error al crear la iniciativa**\n\nError técnico: {str(e)}\n\nIntenta de nuevo con `/crear`"
        await update.message.reply_text(error_text, parse_mode='Markdown')
        if user_id in user_states:
            del user_states[user_id]

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")

async def run_bot():
    """Ejecutar bot de Telegram con manejo robusto de errores"""
    global bot_running, bot_start_time, bot_error_count, telegram_app
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"🤖 Starting Telegram bot (attempt {retry_count + 1}/{max_retries})...")
            
            # Crear aplicación de Telegram
            telegram_app = (Application.builder()
                           .token(TELEGRAM_TOKEN)
                           .read_timeout(30)
                           .write_timeout(30)
                           .connect_timeout(30)
                           .pool_timeout(30)
                           .build())
            
            # Agregar handlers
            telegram_app.add_handler(CommandHandler("start", start_command))
            telegram_app.add_handler(CommandHandler("help", help_command))
            telegram_app.add_handler(CommandHandler("iniciativas", list_initiatives_command))
            telegram_app.add_handler(CommandHandler("crear", create_command))
            telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
            
            # Error handler
            telegram_app.add_error_handler(error_handler)
            
            # Marcar como ejecutándose
            bot_running = True
            bot_start_time = datetime.now().isoformat()
            
            logger.info("🤖 Bot started successfully, beginning polling...")
            
            # Ejecutar polling con configuración optimizada para Render
            await telegram_app.run_polling(
                poll_interval=2.0,
                timeout=10,
                drop_pending_updates=True,
                allowed_updates=['message']
            )
            
            # Si llegamos aquí, el bot se detuvo normalmente
            break
            
        except Exception as e:
            retry_count += 1
            bot_error_count += 1
            bot_running = False
            
            logger.error(f"❌ Bot error (attempt {retry_count}/{max_retries}): {e}")
            
            if retry_count < max_retries:
                wait_time = retry_count * 5  # 5, 10, 15 seconds
                logger.info(f"🔄 Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ Max retries reached, bot stopped")
                break
    
    bot_running = False
    logger.info("🤖 Bot thread ended")

def start_bot_thread():
    """Iniciar bot en thread separado con manejo de errores"""
    global bot_running
    
    def run():
        try:
            # Crear nuevo event loop para este hilo
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Ejecutar el bot
            loop.run_until_complete(run_bot())
            
        except Exception as e:
            logger.error(f"❌ Critical error in bot thread: {e}")
            global bot_running, bot_error_count
            bot_running = False
            bot_error_count += 1
        finally:
            # Asegurar que el loop se cierre
            try:
                loop.close()
            except:
                pass
    
    if TELEGRAM_TOKEN:
        try:
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            logger.info("🤖 Bot thread started successfully")
            
            # Dar un momento para que se inicie
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start bot thread: {e}")
            return False
    else:
        logger.warning("⚠️ Telegram token not configured")
        return False

# ===== INICIO DE LA APLICACIÓN =====

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting Initiatives MCP Server on port {port}")
    print(f"🔗 NocoDB configured: {bool(NOCODB_TOKEN)}")
    print(f"🤖 Telegram configured: {bool(TELEGRAM_TOKEN)}")
    
    # Iniciar bot de Telegram
    if start_bot_thread():
        print("🤖 Telegram bot initialization started")
        # Dar tiempo para que se inicie
        time.sleep(3)
        print(f"🤖 Bot running status: {bot_running}")
    else:
        print("⚠️ Telegram bot failed to start")
    
    # Iniciar servidor Flask
    try:
        print("🌐 Starting Flask server...")
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Flask server error: {e}")
        print(f"❌ Server failed to start: {e}")
