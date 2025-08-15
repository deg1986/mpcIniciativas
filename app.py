# 🚀 MCP Server con Bot de Telegram - VERSIÓN ESTABLE PARA RENDER
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

# Configuración de logging
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
user_states = {}

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
            logger.error(f"❌ NocoDB HTTP {response.status_code}")
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
            logger.error(f"❌ Create failed HTTP {response.status_code}")
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
            "start_time": bot_start_time
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
            "active_sessions": len(user_states)
        },
        "nocodb_info": {
            "connection": "ok" if nocodb_test.get('success') else "failed",
            "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0
        }
    })

@app.route('/test')
def test():
    """Test del sistema"""
    nocodb_test = get_initiatives()
    
    return jsonify({
        "test": "OK",
        "timestamp": datetime.now().isoformat(),
        "nocodb_connection": "OK" if nocodb_test.get('success') else "FAILED",
        "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0,
        "telegram_bot_running": bot_running
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

@app.route('/start-bot', methods=['POST'])
def start_bot_endpoint():
    """Endpoint para iniciar el bot manualmente"""
    global bot_running
    
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

# ===== BOT DE TELEGRAM =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    logger.info(f"📱 /start from user {update.effective_user.id}")
    
    text = """🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos disponibles:**
/iniciativas - Ver todas las iniciativas
/crear - Crear nueva iniciativa
/help - Ver ayuda

¿En qué puedo ayudarte?"""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info("✅ Start message sent")
    except Exception as e:
        logger.error(f"❌ Error sending start message: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    logger.info(f"📱 /help from user {update.effective_user.id}")
    
    text = """🆘 **Ayuda**

**Comandos:**
• /iniciativas - Lista todas las iniciativas
• /crear - Crear nueva iniciativa paso a paso
• /help - Esta ayuda

**Uso:**
1. /iniciativas para ver la lista
2. /crear para empezar a crear una nueva"""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info("✅ Help message sent")
    except Exception as e:
        logger.error(f"❌ Error sending help: {e}")

async def list_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciativas"""
    logger.info(f"📱 /iniciativas from user {update.effective_user.id}")
    
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])[:8]
        
        if not initiatives:
            await update.message.reply_text("📭 No hay iniciativas disponibles.")
            return
        
        text = f"🎯 **Iniciativas ({len(initiatives)})**\n\n"
        
        for i, init in enumerate(initiatives, 1):
            name = init.get('initiative_name', 'Sin nombre')
            owner = init.get('owner', 'Sin owner')
            team = init.get('team', 'Sin equipo')
            
            text += f"**{i}. {name}**\n👤 {owner} • 👥 {team}\n\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info(f"✅ Listed {len(initiatives)} initiatives")
        
    except Exception as e:
        logger.error(f"❌ Error listing initiatives: {e}")
        await update.message.reply_text("❌ Error al obtener iniciativas.")

async def create_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /crear"""
    user_id = update.effective_user.id
    logger.info(f"📱 /crear from user {user_id}")
    
    user_states[user_id] = {'step': 'name', 'data': {}}
    
    text = """🆕 **Crear Nueva Iniciativa**

**Paso 1 de 6:** ¿Cuál es el nombre de la iniciativa?"""
    
    try:
        await update.message.reply_text(text, parse_mode='Markdown')
        logger.info(f"✅ Started creation for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error starting creation: {e}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto"""
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        await update.message.reply_text("👋 Usa /help para ver comandos disponibles.")
        return
    
    state = user_states[user_id]
    step = state['step']
    text = update.message.text.strip()
    
    logger.info(f"📝 Step '{step}' for user {user_id}")
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            response = f"✅ Nombre: {text}\n\n**Paso 2 de 6:** Descripción:"
            
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            response = "✅ Descripción guardada\n\n**Paso 3 de 6:** KPI principal:"
            
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            response = f"✅ KPI: {text}\n\n**Paso 4 de 6:** Portal:"
            
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            response = f"✅ Portal: {text}\n\n**Paso 5 de 6:** Owner:"
            
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            response = f"✅ Owner: {text}\n\n**Paso 6 de 6:** Equipo:"
            
        elif step == 'team':
            state['data']['team'] = text
            await finish_creation(update, user_id)
            return
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"❌ Error handling text: {e}")
        await update.message.reply_text("❌ Error procesando respuesta.")
        if user_id in user_states:
            del user_states[user_id]

async def finish_creation(update: Update, user_id: int):
    """Finalizar creación"""
    try:
        state = user_states[user_id]
        data = state['data']
        
        # Valores por defecto
        data.update({
            'reach': 0.5,
            'impact': 0.5, 
            'confidence': 0.5,
            'effort': 0.5
        })
        
        await update.message.reply_text("⏳ Creando iniciativa...")
        
        result = create_initiative(data)
        
        if result.get("success"):
            text = f"🎉 **¡Iniciativa creada!**\n\n**{data['initiative_name']}** agregada exitosamente."
        else:
            text = f"❌ **Error:** {result.get('error')}"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
        if user_id in user_states:
            del user_states[user_id]
            
        logger.info(f"✅ Finished creation for user {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Error finishing creation: {e}")
        await update.message.reply_text("❌ Error al crear iniciativa.")
        if user_id in user_states:
            del user_states[user_id]

async def run_bot():
    """Ejecutar bot con configuración simple y estable"""
    global bot_running, bot_start_time
    
    try:
        logger.info("🤖 Starting Telegram bot...")
        
        # Crear aplicación con configuración mínima
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Agregar handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("iniciativas", list_initiatives_command))
        application.add_handler(CommandHandler("crear", create_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        
        # Marcar como ejecutándose
        bot_running = True
        bot_start_time = datetime.now().isoformat()
        
        logger.info("🤖 Bot started successfully, starting polling...")
        
        # Ejecutar polling con configuración simple
        await application.run_polling(
            drop_pending_updates=True,
            allowed_updates=['message']
        )
        
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        bot_running = False
    
    logger.info("🤖 Bot ended")

def start_bot_thread():
    """Iniciar bot en thread separado"""
    def run():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(run_bot())
        except Exception as e:
            logger.error(f"❌ Bot thread error: {e}")
            global bot_running
            bot_running = False
    
    if TELEGRAM_TOKEN:
        try:
            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            logger.info("🤖 Bot thread started")
            time.sleep(2)  # Dar tiempo para inicializar
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start bot thread: {e}")
            return False
    return False

# ===== INICIO =====

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting server on port {port}")
    print(f"🤖 Telegram configured: {bool(TELEGRAM_TOKEN)}")
    
    # Iniciar bot automáticamente
    if start_bot_thread():
        print("🤖 Bot started automatically")
        # Dar más tiempo para asegurar que se inicie
        time.sleep(5)
        print(f"🤖 Bot running: {bot_running}")
    else:
        print("⚠️ Bot failed to start automatically")
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=port, debug=False)
