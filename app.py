# 🚀 Servidor MCP para Iniciativas con Bot de Telegram - VERSIÓN SIMPLIFICADA
import os
import json
import time
import threading
import asyncio
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'initiatives-secret-key')

# CORS
CORS(app, origins=["*"], methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

# Configuración
NOCODB_BASE_URL = "https://nocodb.farmuhub.co/api/v2"
NOCODB_TABLE_ID = "m274d90cy3x6ra3"
NOCODB_TOKEN = "-kgNP5Q5G54nlDXPei7IO9PMMyE4pIgxYCi6o17Y"
TELEGRAM_TOKEN = "8309791895:AAGxfmPQ_yvgNY-kyMMDrKR0srb7c20KL5Q"

# Variables globales
initiatives_cache = None
cache_time = None
telegram_app = None
bot_running = False
user_creation_state = {}

def get_nocodb_initiatives():
    """Obtener datos de iniciativas desde NocoDB"""
    global initiatives_cache, cache_time
    
    # Cache por 5 minutos
    if initiatives_cache and cache_time and (time.time() - cache_time) < 300:
        return initiatives_cache
    
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        params = {'limit': 100, 'shuffle': 0, 'offset': 0}
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}", "data": []}
        
        raw_data = response.json()
        initiatives = raw_data.get('list', [])
        
        # Procesar datos
        processed_initiatives = []
        for initiative in initiatives:
            if isinstance(initiative, dict):
                processed_init = {}
                for key, value in initiative.items():
                    clean_key = str(key).strip().replace(' ', '_').replace('-', '_').lower()
                    processed_init[clean_key] = str(value) if value is not None else ""
                processed_initiatives.append(processed_init)
        
        result = {
            "success": True,
            "data": processed_initiatives,
            "metadata": {
                "total_records": len(processed_initiatives),
                "retrieved_at": datetime.now().isoformat()
            }
        }
        
        # Actualizar cache
        initiatives_cache = result
        cache_time = time.time()
        return result
        
    except Exception as e:
        logger.error(f"Error fetching initiatives: {e}")
        return {"success": False, "error": str(e), "data": []}

def create_nocodb_initiative(initiative_data):
    """Crear nueva iniciativa en NocoDB"""
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Validar campos requeridos
        required_fields = ['initiative_name', 'description', 'main_kpi', 'portal', 'owner', 'team']
        for field in required_fields:
            if field not in initiative_data or not initiative_data[field]:
                return {"success": False, "error": f"Campo requerido: {field}"}
        
        # Asegurar campos numéricos
        numeric_fields = ['reach', 'impact', 'confidence', 'effort']
        for field in numeric_fields:
            if field in initiative_data:
                try:
                    initiative_data[field] = float(initiative_data[field])
                except:
                    initiative_data[field] = 0.0
        
        response = requests.post(url, headers=headers, json=initiative_data, timeout=30)
        
        if response.status_code in [200, 201]:
            global initiatives_cache, cache_time
            initiatives_cache = None
            cache_time = None
            
            return {
                "success": True,
                "data": response.json(),
                "message": f"Iniciativa '{initiative_data['initiative_name']}' creada"
            }
        else:
            return {"success": False, "error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        logger.error(f"Error creating initiative: {e}")
        return {"success": False, "error": str(e)}

# ===== ENDPOINTS FLASK =====

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def mcp_endpoint():
    """Endpoint principal MCP"""
    
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add("Access-Control-Allow-Headers", "*")
        response.headers.add("Access-Control-Allow-Methods", "*")
        return response
    
    if request.method == "GET":
        return jsonify({
            "name": "Initiatives MCP Server",
            "version": "1.0.0",
            "description": "MCP server for NocoDB initiatives with Telegram bot",
            "status": "running",
            "telegram_bot": {
                "enabled": bool(TELEGRAM_TOKEN),
                "running": bot_running
            }
        })
    
    if request.method == "POST":
        try:
            if not request.is_json:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Content must be JSON"},
                    "id": None
                }), 400
            
            rpc_request = request.get_json()
            if not rpc_request or 'method' not in rpc_request:
                return jsonify({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid request"},
                    "id": rpc_request.get('id') if rpc_request else None
                }), 400
            
            return handle_mcp_request(rpc_request)
            
        except Exception as e:
            logger.error(f"MCP endpoint error: {e}")
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": None
            }), 500

def handle_mcp_request(rpc_request):
    """Manejar peticiones MCP"""
    method = rpc_request.get('method')
    params = rpc_request.get('params', {})
    request_id = rpc_request.get('id')
    
    if method == "initialize":
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "resources": {"subscribe": False, "listChanged": False},
                    "tools": {"listChanged": False}
                },
                "serverInfo": {"name": "initiatives-server", "version": "1.0.0"}
            },
            "id": request_id
        })
    
    elif method == "initialized":
        return jsonify({"jsonrpc": "2.0", "result": {}, "id": request_id})
    
    elif method == "tools/list":
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "list_initiatives",
                        "description": "List all initiatives from NocoDB",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {"type": "integer", "default": 25, "minimum": 1, "maximum": 100}
                            }
                        }
                    },
                    {
                        "name": "create_initiative",
                        "description": "Create new initiative in NocoDB",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "initiative_name": {"type": "string"},
                                "description": {"type": "string"},
                                "main_kpi": {"type": "string"},
                                "portal": {"type": "string"},
                                "owner": {"type": "string"},
                                "team": {"type": "string"},
                                "reach": {"type": "number", "minimum": 0, "maximum": 1},
                                "impact": {"type": "number", "minimum": 0, "maximum": 1},
                                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                                "effort": {"type": "number", "minimum": 0, "maximum": 1}
                            },
                            "required": ["initiative_name", "description", "main_kpi", "portal", "owner", "team"]
                        }
                    }
                ]
            },
            "id": request_id
        })
    
    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        
        if tool_name == "list_initiatives":
            return handle_list_initiatives(args, request_id)
        elif tool_name == "create_initiative":
            return handle_create_initiative(args, request_id)
        else:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                "id": request_id
            })
    
    else:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id
        })

def handle_list_initiatives(args, request_id):
    """Manejar listado de iniciativas"""
    data = get_nocodb_initiatives()
    
    if not data.get("success"):
        return jsonify({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"❌ Error: {data.get('error', 'Unknown error')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    limit = min(int(args.get("limit", 25)), 100)
    limited_initiatives = initiatives[:limit]
    
    result_text = f"🎯 **Lista de Iniciativas**\n\n**Total:** {len(initiatives)}\n**Mostrando:** {len(limited_initiatives)}\n\n"
    
    if limited_initiatives:
        for i, initiative in enumerate(limited_initiatives, 1):
            if isinstance(initiative, dict):
                name = initiative.get('initiative_name', 'Sin nombre')
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                result_text += f"**{i}. {name}**\n👤 {owner} • 👥 {team}\n\n"
    else:
        result_text += "*No se encontraron iniciativas.*\n"
    
    return jsonify({
        "jsonrpc": "2.0",
        "result": {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        },
        "id": request_id
    })

def handle_create_initiative(args, request_id):
    """Manejar creación de iniciativa"""
    result = create_nocodb_initiative(args)
    
    if result.get("success"):
        result_text = f"✅ **Iniciativa Creada**\n\n**Nombre:** {args.get('initiative_name')}\n**Owner:** {args.get('owner')}\n**Equipo:** {args.get('team')}"
    else:
        result_text = f"❌ **Error:** {result.get('error', 'Unknown error')}"
    
    return jsonify({
        "jsonrpc": "2.0",
        "result": {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        },
        "id": request_id
    })

# ===== BOT DE TELEGRAM =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    welcome_text = """🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos:**
/iniciativas - Ver iniciativas
/crear - Crear iniciativa
/help - Ayuda

¿En qué puedo ayudarte?"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    help_text = """🆘 **Ayuda**

**Comandos disponibles:**
🎯 /iniciativas - Listar iniciativas
📝 /crear - Crear nueva iniciativa
🆘 /help - Esta ayuda

**Ejemplos:**
• /iniciativas - Ve todas las iniciativas
• /crear - Proceso paso a paso para crear"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciativas"""
    try:
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])[:10]
        
        if not initiatives:
            await update.message.reply_text("📭 No hay iniciativas.")
            return
        
        response_text = f"🎯 **Iniciativas ({len(initiatives)})**\n\n"
        
        for i, initiative in enumerate(initiatives, 1):
            if isinstance(initiative, dict):
                name = initiative.get('initiative_name', 'Sin nombre')
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                
                response_text += f"**{i}. {name}**\n👤 {owner} • 👥 {team}\n\n"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in list_initiatives: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def create_initiative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /crear"""
    user_id = update.effective_user.id
    
    user_creation_state[user_id] = {'step': 'name', 'data': {}}
    
    await update.message.reply_text(
        "🆕 **Crear Iniciativa**\n\n**Paso 1/6:** ¿Nombre de la iniciativa?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto"""
    user_id = update.effective_user.id
    
    if user_id not in user_creation_state:
        await update.message.reply_text("👋 Usa /help para ver comandos.")
        return
    
    state = user_creation_state[user_id]
    step = state['step']
    text = update.message.text.strip()
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            await update.message.reply_text(f"✅ Nombre: {text}\n\n**Paso 2/6:** Descripción:")
        
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            await update.message.reply_text("✅ Descripción ok\n\n**Paso 3/6:** KPI principal:")
        
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            await update.message.reply_text(f"✅ KPI: {text}\n\n**Paso 4/6:** Portal:")
        
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            await update.message.reply_text(f"✅ Portal: {text}\n\n**Paso 5/6:** Owner:")
        
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            await update.message.reply_text(f"✅ Owner: {text}\n\n**Paso 6/6:** Equipo:")
        
        elif step == 'team':
            state['data']['team'] = text
            await create_initiative_final(update, user_id)
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def create_initiative_final(update: Update, user_id: int):
    """Crear iniciativa final"""
    try:
        state = user_creation_state[user_id]
        data = state['data']
        
        # Valores por defecto
        data.update({'reach': 0.5, 'impact': 0.5, 'confidence': 0.5, 'effort': 0.5})
        
        await update.message.reply_text("⏳ Creando iniciativa...")
        
        result = create_nocodb_initiative(data)
        
        if result.get("success"):
            await update.message.reply_text(
                f"🎉 **¡Iniciativa creada!**\n\n**{data['initiative_name']}** agregada al sistema."
            )
        else:
            await update.message.reply_text(f"❌ Error: {result.get('error')}")
        
        if user_id in user_creation_state:
            del user_creation_state[user_id]
    
    except Exception as e:
        logger.error(f"Error creating initiative: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def setup_telegram_bot():
    """Configurar bot de Telegram"""
    global telegram_app, bot_running
    
    try:
        logger.info("🤖 Initializing Telegram bot...")
        
        telegram_app = (Application.builder()
                       .token(TELEGRAM_TOKEN)
                       .build())
        
        # Handlers
        telegram_app.add_handler(CommandHandler("start", start_command))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("iniciativas", list_initiatives_command))
        telegram_app.add_handler(CommandHandler("crear", create_initiative_command))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("🤖 Starting bot polling...")
        bot_running = True
        
        await telegram_app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        bot_running = False

def run_telegram_bot():
    """Ejecutar bot en hilo separado"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(setup_telegram_bot())
    except Exception as e:
        logger.error(f"❌ Bot thread error: {e}")

# ===== ENDPOINTS ADICIONALES =====

@app.route("/health")
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": {
            "configured": bool(TELEGRAM_TOKEN),
            "running": bot_running
        },
        "nocodb": {
            "configured": bool(NOCODB_TOKEN)
        }
    })

@app.route("/test-nocodb")
def test_nocodb():
    """Test NocoDB connection"""
    data = get_nocodb_initiatives()
    return jsonify(data)

@app.route("/bot-status")
def bot_status():
    """Bot status"""
    return jsonify({
        "bot_running": bot_running,
        "token_configured": bool(TELEGRAM_TOKEN),
        "active_sessions": len(user_creation_state),
        "timestamp": datetime.now().isoformat()
    })

@app.route("/api/initiatives")
def api_initiatives():
    """API para listar iniciativas"""
    data = get_nocodb_initiatives()
    if data.get("success"):
        return jsonify({"success": True, "data": data.get("data", [])})
    else:
        return jsonify({"success": False, "error": data.get("error")}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting MCP Server on port {port}")
    print(f"🤖 Telegram Bot: {'Configured' if TELEGRAM_TOKEN else 'Not configured'}")
    
    # Iniciar bot si está configurado
    if TELEGRAM_TOKEN:
        try:
            bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
            bot_thread.start()
            print("🤖 Telegram bot thread started")
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=port, debug=False)
