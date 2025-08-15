# 🚀 Servidor MCP para Iniciativas con Bot de Telegram - VERSIÓN RENDER
import os
import json
import time
import sys
import asyncio
import threading
import signal
from datetime import datetime
from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import requests
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import logging

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'initiatives-secret-key')

# CORS más permisivo
CORS(app, 
     origins=["*"],
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["*"],
     supports_credentials=True)

# Configuración de NocoDB
NOCODB_BASE_URL = "https://nocodb.farmuhub.co/api/v2"
NOCODB_TABLE_ID = "m274d90cy3x6ra3"
NOCODB_TOKEN = "-kgNP5Q5G54nlDXPei7IO9PMMyE4pIgxYCi6o17Y"

# Configuración de Telegram
TELEGRAM_TOKEN = "8309791895:AAGxfmPQ_yvgNY-kyMMDrKR0srb7c20KL5Q"

# Cache en memoria
initiatives_cache = None
cache_time = None

# Variables globales para el bot
telegram_app = None
bot_running = False

def clean_value(value):
    """Limpiar y convertir valores para evitar errores de validación"""
    if value is None:
        return ""
    if isinstance(value, (int, float)) and (value != value):  # NaN check
        return 0
    if isinstance(value, str):
        return value.strip()
    return str(value)

def get_nocodb_initiatives():
    """Obtener datos de iniciativas desde NocoDB con cache"""
    global initiatives_cache, cache_time
    
    # Cache por 5 minutos
    if initiatives_cache and cache_time and (time.time() - cache_time) < 300:
        print("📦 Using cached initiatives data")
        return initiatives_cache
    
    try:
        print("🔄 Fetching fresh initiatives data from NocoDB...")
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN
        }
        
        params = {
            'limit': 100,
            'shuffle': 0,
            'offset': 0
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=30)
        print(f"📡 NocoDB response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ HTTP Error: {response.status_code}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}",
                "data": []
            }
        
        raw_data = response.json()
        initiatives = raw_data.get('list', [])
        page_info = raw_data.get('pageInfo', {})
        
        print(f"📈 Found {len(initiatives)} initiatives")
        
        # Procesar iniciativas
        processed_initiatives = []
        for i, initiative in enumerate(initiatives):
            if isinstance(initiative, dict):
                processed_init = {}
                for key, value in initiative.items():
                    clean_key = str(key).strip().replace(' ', '_').replace('-', '_').lower()
                    cleaned_value = clean_value(value)
                    processed_init[clean_key] = cleaned_value
                processed_initiatives.append(processed_init)
        
        result = {
            "success": True,
            "data": processed_initiatives,
            "metadata": {
                "total_records": len(processed_initiatives),
                "source": "NocoDB Initiatives",
                "retrieved_at": datetime.now().isoformat(),
                "page_info": page_info,
                "table_id": NOCODB_TABLE_ID
            }
        }
        
        print(f"✅ Successfully processed {len(processed_initiatives)} initiatives")
        
        # Actualizar cache
        initiatives_cache = result
        cache_time = time.time()
        return result
        
    except Exception as e:
        error_msg = f"Error fetching initiatives: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg, "data": []}

def create_nocodb_initiative(initiative_data):
    """Crear una nueva iniciativa en NocoDB"""
    try:
        print(f"🆕 Creating new initiative: {initiative_data.get('initiative_name', 'Unknown')}")
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        # Validar datos requeridos
        required_fields = ['initiative_name', 'description', 'main_kpi', 'portal', 'owner', 'team']
        for field in required_fields:
            if field not in initiative_data or not initiative_data[field]:
                return {
                    "success": False,
                    "error": f"Campo requerido faltante: {field}"
                }
        
        # Asegurar que los campos numéricos sean números
        numeric_fields = ['reach', 'impact', 'confidence', 'effort']
        for field in numeric_fields:
            if field in initiative_data:
                try:
                    initiative_data[field] = float(initiative_data[field])
                except (ValueError, TypeError):
                    initiative_data[field] = 0.0
        
        response = requests.post(url, headers=headers, json=initiative_data, timeout=30)
        print(f"📡 NocoDB create response status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            # Limpiar cache para que se actualice
            global initiatives_cache, cache_time
            initiatives_cache = None
            cache_time = None
            
            created_initiative = response.json()
            return {
                "success": True,
                "data": created_initiative,
                "message": f"Iniciativa '{initiative_data['initiative_name']}' creada exitosamente"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text[:200]}"
            }
            
    except Exception as e:
        error_msg = f"Error creating initiative: {str(e)}"
        print(f"❌ {error_msg}")
        return {"success": False, "error": error_msg}

def create_mcp_response(data, status=200):
    """Crear respuesta MCP con headers específicos"""
    response = make_response(jsonify(data), status)
    response.headers.update({
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Cache-Control': 'no-cache',
        'X-MCP-Protocol': '2024-11-05',
        'X-MCP-Server': 'initiatives-server'
    })
    return response

@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = make_response()
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

@app.route("/", methods=["GET", "POST", "OPTIONS"])
def mcp_endpoint():
    """Endpoint principal MCP"""
    
    if request.method == "OPTIONS":
        return create_mcp_response({})
    
    if request.method == "GET":
        return create_mcp_response({
            "name": "Initiatives MCP Server",
            "version": "1.0.0",
            "description": "MCP server for NocoDB initiatives with Telegram bot",
            "protocol": "Model Context Protocol v2024-11-05",
            "status": "running",
            "auth_required": False,
            "capabilities": {
                "resources": {"subscribe": False, "listChanged": False},
                "tools": {"listChanged": False}
            },
            "telegram_bot": {
                "enabled": True,
                "running": bot_running,
                "token_configured": bool(TELEGRAM_TOKEN)
            }
        })
    
    if request.method == "POST":
        try:
            if not request.is_json:
                return create_mcp_response({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Content must be JSON"},
                    "id": None
                }, 400)
            
            rpc_request = request.get_json()
            if not rpc_request or 'method' not in rpc_request:
                return create_mcp_response({
                    "jsonrpc": "2.0",
                    "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
                    "id": rpc_request.get('id') if rpc_request else None
                }, 400)
            
            return handle_mcp_request(rpc_request)
            
        except Exception as e:
            return create_mcp_response({
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"},
                "id": None
            }, 500)

def handle_mcp_request(rpc_request):
    """Manejar peticiones JSON-RPC del protocolo MCP"""
    method = rpc_request.get('method')
    params = rpc_request.get('params', {})
    request_id = rpc_request.get('id')
    
    if method == "initialize":
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "resources": {"subscribe": False, "listChanged": False},
                    "tools": {"listChanged": False}
                },
                "serverInfo": {
                    "name": "initiatives-server",
                    "version": "1.0.0"
                }
            },
            "id": request_id
        })
    
    elif method == "initialized":
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {},
            "id": request_id
        })
    
    elif method == "tools/list":
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "list_initiatives",
                        "description": "Retrieve all initiatives from NocoDB with optional limit and format options.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum number of initiatives to return (default: 25, max: 100)",
                                    "default": 25,
                                    "minimum": 1,
                                    "maximum": 100
                                },
                                "format": {
                                    "type": "string",
                                    "enum": ["summary", "detailed", "json"],
                                    "description": "Output format - summary: key fields only, detailed: all fields, json: raw data",
                                    "default": "summary"
                                }
                            },
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "create_initiative",
                        "description": "Create a new initiative in NocoDB.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "initiative_name": {"type": "string", "description": "Name of the initiative"},
                                "description": {"type": "string", "description": "Description of the initiative"},
                                "main_kpi": {"type": "string", "description": "Main KPI for the initiative"},
                                "portal": {"type": "string", "description": "Portal associated with the initiative"},
                                "owner": {"type": "string", "description": "Owner of the initiative"},
                                "team": {"type": "string", "description": "Team responsible for the initiative"},
                                "reach": {"type": "number", "description": "Reach score (0-1)", "minimum": 0, "maximum": 1},
                                "impact": {"type": "number", "description": "Impact score (0-1)", "minimum": 0, "maximum": 1},
                                "confidence": {"type": "number", "description": "Confidence score (0-1)", "minimum": 0, "maximum": 1},
                                "effort": {"type": "number", "description": "Effort score (0-1)", "minimum": 0, "maximum": 1}
                            },
                            "required": ["initiative_name", "description", "main_kpi", "portal", "owner", "team"],
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "search_initiatives",
                        "description": "Search initiatives by name, owner, or team.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string", "description": "Search term"},
                                "field": {"type": "string", "enum": ["name", "owner", "team", "all"], "description": "Field to search in (default: all)", "default": "all"},
                                "limit": {"type": "integer", "description": "Maximum results to return", "default": 10, "minimum": 1, "maximum": 50}
                            },
                            "required": ["query"],
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "get_initiatives_stats",
                        "description": "Get statistical overview of initiatives.",
                        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}
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
        elif tool_name == "search_initiatives":
            return handle_search_initiatives(args, request_id)
        elif tool_name == "get_initiatives_stats":
            return handle_get_initiatives_stats(request_id)
        else:
            return create_mcp_response({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"},
                "id": request_id
            })
    
    else:
        return create_mcp_response({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method}"},
            "id": request_id
        })

def format_initiative_summary(initiative, index=None):
    """Formatear iniciativa para vista resumida"""
    name = initiative.get('initiative_name', 'Sin nombre')
    owner = initiative.get('owner', 'Sin dueño')
    team = initiative.get('team', 'Sin equipo')
    kpi = initiative.get('main_kpi', 'Sin KPI')
    
    prefix = f"**{index}.** " if index else ""
    summary_parts = [f"**{name}**", f"👤 {owner}", f"👥 {team}", f"📊 {kpi}"]
    
    return prefix + " • ".join(summary_parts)

# [Aquí van todas las funciones handle_* del MCP - las mantengo iguales]
def handle_list_initiatives(args, request_id):
    data = get_nocodb_initiatives()
    
    if not data.get("success"):
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error al obtener iniciativas**\n\n**Error:** {data.get('error', 'Error desconocido')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    limit = min(int(args.get("limit", 25)), 100)
    format_type = args.get("format", "summary")
    limited_initiatives = initiatives[:limit]
    
    if format_type == "json":
        json_str = json.dumps(limited_initiatives, indent=2, ensure_ascii=False, default=str)
        result_text = f"📊 **Iniciativas en formato JSON**\n\n**Registros:** {len(limited_initiatives)} de {len(initiatives)}\n\n```json\n{json_str}\n```"
    elif format_type == "detailed":
        result_text = f"📊 **Listado Detallado**\n\n**Total:** {len(initiatives)}\n**Mostrando:** {len(limited_initiatives)}\n\n"
        for i, initiative in enumerate(limited_initiatives, 1):
            if isinstance(initiative, dict):
                result_text += f"### 🎯 Iniciativa #{i}\n"
                for key, value in initiative.items():
                    result_text += f"- **{key}:** {value}\n"
                result_text += "\n"
    else:  # summary
        result_text = f"🎯 **Lista de Iniciativas**\n\n**Total:** {len(initiatives)}\n**Mostrando:** {len(limited_initiatives)}\n\n"
        if limited_initiatives:
            for i, initiative in enumerate(limited_initiatives, 1):
                if isinstance(initiative, dict):
                    result_text += format_initiative_summary(initiative, i) + "\n"
        else:
            result_text += "*No se encontraron iniciativas.*\n"
    
    return create_mcp_response({
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
    result = create_nocodb_initiative(args)
    
    if result.get("success"):
        result_text = f"✅ **Iniciativa Creada**\n\n**Nombre:** {args.get('initiative_name')}\n**Owner:** {args.get('owner')}\n**Equipo:** {args.get('team')}"
    else:
        result_text = f"❌ **Error:** {result.get('error', 'Error desconocido')}"
    
    return create_mcp_response({
        "jsonrpc": "2.0",
        "result": {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        },
        "id": request_id
    })

def handle_search_initiatives(args, request_id):
    query = args.get("query", "").strip().lower()
    if not query:
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": "❌ **Término de búsqueda requerido**"
                }]
            },
            "id": request_id
        })
    
    data = get_nocodb_initiatives()
    if not data.get("success"):
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error:** {data.get('error')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    matching = []
    
    for initiative in initiatives:
        if isinstance(initiative, dict):
            text_fields = ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal']
            for field_name in text_fields:
                if field_name in initiative and query in str(initiative[field_name]).lower():
                    matching.append(initiative)
                    break
    
    result_text = f"🔍 **Búsqueda: `{args.get('query')}`**\n**Encontradas:** {len(matching)}\n\n"
    if matching:
        for i, initiative in enumerate(matching[:10], 1):
            result_text += format_initiative_summary(initiative, i) + "\n"
    else:
        result_text += "*No se encontraron resultados.*"
    
    return create_mcp_response({
        "jsonrpc": "2.0",
        "result": {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        },
        "id": request_id
    })

def handle_get_initiatives_stats(request_id):
    data = get_nocodb_initiatives()
    if not data.get("success"):
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error:** {data.get('error')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    result_text = f"📈 **Estadísticas**\n\n**Total:** {len(initiatives)} iniciativas\n"
    
    return create_mcp_response({
        "jsonrpc": "2.0",
        "result": {
            "content": [{
                "type": "text",
                "text": result_text
            }]
        },
        "id": request_id
    })

# ===== BOT DE TELEGRAM - VERSIÓN CORREGIDA =====

# Estado para creación de iniciativas
user_creation_state = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start del bot"""
    welcome_text = """🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos disponibles:**
/iniciativas - Ver todas las iniciativas
/crear - Crear una nueva iniciativa
/buscar <término> - Buscar iniciativas
/stats - Ver estadísticas
/help - Ver esta ayuda

¿En qué puedo ayudarte?"""
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help del bot"""
    help_text = """🆘 **Ayuda - Bot de Iniciativas**

**Comandos disponibles:**

🎯 **/iniciativas** - Listar todas las iniciativas
📝 **/crear** - Crear una nueva iniciativa
🔍 **/buscar** <término> - Buscar iniciativas
📈 **/stats** - Ver estadísticas
🆘 **/help** - Mostrar esta ayuda

**Ejemplos:**
• `/buscar Product` - Busca iniciativas del equipo Product
• `/crear` - Inicia el proceso de creación

¿Necesitas ayuda con algo específico?"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def list_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciativas del bot"""
    try:
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])[:10]  # Limitar para Telegram
        
        if not initiatives:
            await update.message.reply_text("📭 No se encontraron iniciativas.")
            return
        
        response_text = f"🎯 **Iniciativas ({len(initiatives)} de {len(data.get('data', []))})**\n\n"
        
        for i, initiative in enumerate(initiatives, 1):
            if isinstance(initiative, dict):
                name = initiative.get('initiative_name', 'Sin nombre')
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                
                response_text += f"**{i}. {name}**\n"
                response_text += f"👤 {owner} • 👥 {team}\n\n"
        
        if len(data.get('data', [])) > 10:
            response_text += f"📋 *Mostrando las primeras 10 de {len(data.get('data', []))} iniciativas*"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in list_initiatives_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def search_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /buscar del bot"""
    try:
        if not context.args:
            await update.message.reply_text("🔍 **Uso:** `/buscar <término>`\n\nEjemplo: `/buscar Product`")
            return
        
        query = " ".join(context.args)
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        matching = []
        
        query_lower = query.lower()
        for initiative in initiatives:
            if isinstance(initiative, dict):
                text_fields = ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal']
                for field_name in text_fields:
                    if field_name in initiative and query_lower in str(initiative[field_name]).lower():
                        matching.append(initiative)
                        break
        
        if not matching:
            await update.message.reply_text(f"🔍 No se encontraron iniciativas con: `{query}`")
            return
        
        limited_results = matching[:5]
        response_text = f"🔍 **Resultados para: `{query}`**\n**Encontradas:** {len(matching)}\n\n"
        
        for i, initiative in enumerate(limited_results, 1):
            name = initiative.get('initiative_name', 'Sin nombre')
            owner = initiative.get('owner', 'Sin dueño')
            team = initiative.get('team', 'Sin equipo')
            
            response_text += f"**{i}. {name}**\n👤 {owner} • 👥 {team}\n\n"
        
        if len(matching) > 5:
            response_text += f"📋 *Mostrando las primeras 5 de {len(matching)} encontradas*"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search_initiatives_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats del bot"""
    try:
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            await update.message.reply_text("📊 No hay iniciativas para analizar.")
            return
        
        owners = {}
        teams = {}
        
        for initiative in initiatives:
            if isinstance(initiative, dict):
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                
                owners[owner] = owners.get(owner, 0) + 1
                teams[team] = teams.get(team, 0) + 1
        
        response_text = f"📈 **Estadísticas**\n\n**📊 Total:** {len(initiatives)} iniciativas\n\n"
        
        # Top 3 owners
        response_text += f"**👤 Top Owners:**\n"
        for owner, count in sorted(owners.items(), key=lambda x: x[1], reverse=True)[:3]:
            response_text += f"• {owner}: {count}\n"
        
        # Top 3 teams
        response_text += f"\n**👥 Top Teams:**\n"
        for team, count in sorted(teams.items(), key=lambda x: x[1], reverse=True)[:3]:
            response_text += f"• {team}: {count}\n"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def create_initiative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /crear del bot"""
    user_id = update.effective_user.id
    
    user_creation_state[user_id] = {
        'step': 'name',
        'data': {}
    }
    
    await update.message.reply_text(
        "🆕 **Crear Nueva Iniciativa**\n\n"
        "Te guiaré paso a paso.\n\n"
        "**Paso 1/6:** ¿Cuál es el nombre de la iniciativa?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes para creación de iniciativas"""
    user_id = update.effective_user.id
    
    if user_id not in user_creation_state:
        await update.message.reply_text("👋 ¡Hola! Usa /help para ver los comandos disponibles.")
        return
    
    state = user_creation_state[user_id]
    step = state['step']
    text = update.message.text.strip()
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            await update.message.reply_text(f"✅ Nombre: {text}\n\n**Paso 2/6:** ¿Cuál es la descripción?")
        
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            await update.message.reply_text("✅ Descripción guardada\n\n**Paso 3/6:** ¿Cuál es el KPI principal?")
        
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            await update.message.reply_text(f"✅ KPI: {text}\n\n**Paso 4/6:** ¿En qué portal se ejecutará?")
        
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            await update.message.reply_text(f"✅ Portal: {text}\n\n**Paso 5/6:** ¿Quién es el owner?")
        
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            await update.message.reply_text(f"✅ Owner: {text}\n\n**Paso 6/6:** ¿Qué equipo será responsable?")
        
        elif step == 'team':
            state['data']['team'] = text
            await create_initiative_final(update, user_id)
    
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def create_initiative_final(update: Update, user_id: int):
    """Crear la iniciativa final"""
    try:
        state = user_creation_state[user_id]
        data = state['data']
        
        # Valores por defecto para métricas
        data.update({
            'reach': 0.5,
            'impact': 0.5,
            'confidence': 0.5,
            'effort': 0.5
        })
        
        summary = f"📋 **Resumen:**\n\n"
        summary += f"**Nombre:** {data['initiative_name']}\n"
        summary += f"**Owner:** {data['owner']}\n"
        summary += f"**Equipo:** {data['team']}\n\n"
        summary += "⏳ Creando iniciativa..."
        
        await update.message.reply_text(summary, parse_mode='Markdown')
        
        result = create_nocodb_initiative(data)
        
        if result.get("success"):
            await update.message.reply_text(
                f"🎉 **¡Iniciativa creada!**\n\n"
                f"**{data['initiative_name']}** ha sido agregada.\n\n"
                "Usa /iniciativas para ver todas."
            )
        else:
            await update.message.reply_text(f"❌ **Error:** {result.get('error', 'Error desconocido')}")
        
        if user_id in user_creation_state:
            del user_creation_state[user_id]
    
    except Exception as e:
        logger.error(f"Error in create_initiative_final: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancel"""
    user_id = update.effective_user.id
    
    if user_id in user_creation_state:
        del user_creation_state[user_id]
        await update.message.reply_text("❌ Creación cancelada.")
    else:
        await update.message.reply_text("No hay proceso activo.")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejar errores del bot"""
    logger.error(f"Exception while handling an update: {context.error}")

# ===== CONFIGURACIÓN CORREGIDA PARA RENDER =====

async def setup_telegram_bot():
    """Configurar bot con manejo robusto de errores"""
    global telegram_app, bot_running
    
    try:
        logger.info("🤖 Initializing Telegram bot...")
        
        # Configurar Application con timeouts más largos
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
        telegram_app.add_handler(CommandHandler("buscar", search_initiatives_command))
        telegram_app.add_handler(CommandHandler("stats", stats_command))
        telegram_app.add_handler(CommandHandler("crear", create_initiative_command))
        telegram_app.add_handler(CommandHandler("cancel", cancel_command))
        
        # Handler para mensajes de texto
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Error handler
        telegram_app.add_error_handler(error_handler)
        
        logger.info("🤖 Starting Telegram bot polling...")
        bot_running = True
        
        # Iniciar polling con parámetros optimizados para Render
        await telegram_app.run_polling(
            poll_interval=1.0,
            timeout=10,
            drop_pending_updates=True,
            allowed_updates=['message', 'callback_query']
        )
        
    except Exception as e:
        logger.error(f"❌ Error in setup_telegram_bot: {e}")
        bot_running = False

def run_telegram_bot():
    """Ejecutar bot en hilo separado con manejo de errores mejorado"""
    global bot_running
    
    loop = None
    try:
        # Crear nuevo event loop para este hilo
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        logger.info("🤖 Starting Telegram bot thread...")
        
        # Ejecutar setup del bot
        loop.run_until_complete(setup_telegram_bot())
        
    except Exception as e:
        logger.error(f"❌ Critical error in telegram bot thread: {e}")
        bot_running = False
    finally:
        if loop and not loop.is_closed():
            loop.close()
        logger.info("🤖 Telegram bot thread ended")

def start_telegram_bot_thread():
    """Iniciar bot en hilo daemon"""
    if TELEGRAM_TOKEN:
        try:
            telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
            telegram_thread.start()
            logger.info("🤖 Telegram bot thread started")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to start telegram thread: {e}")
            return False
    else:
        logger.warning("⚠️ Telegram token not configured")
        return False

# ===== ENDPOINTS ADICIONALES =====

@app.route("/health")
def health():
    """Health check mejorado"""
    return create_mcp_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": {
            "configured": bool(TELEGRAM_TOKEN),
            "running": bot_running,
            "active_sessions": len(user_creation_state)
        },
        "nocodb": {
            "configured": bool(NOCODB_TOKEN),
            "table_id": NOCODB_TABLE_ID
        },
        "cache": {
            "has_cache": initiatives_cache is not None,
            "cache_age": time.time() - cache_time if cache_time else None
        }
    })

@app.route("/test-nocodb")
def test_nocodb():
    """Probar conexión con NocoDB"""
    data = get_nocodb_initiatives()
    return create_mcp_response(data)

@app.route("/debug")
def debug_endpoint():
    """Debug completo"""
    data = get_nocodb_initiatives()
    
    debug_info = {
        "nocodb_connection": "OK" if data.get("success") else "FAILED",
        "error": data.get("error"),
        "initiatives_count": len(data.get("data", [])),
        "metadata": data.get("metadata", {}),
        "telegram_bot": {
            "token_configured": bool(TELEGRAM_TOKEN),
            "running": bot_running,
            "active_creation_sessions": len(user_creation_state),
            "user_states": list(user_creation_state.keys())
        },
        "cache_info": {
            "has_cache": initiatives_cache is not None,
            "cache_age_seconds": time.time() - cache_time if cache_time else None
        },
        "sample_data": data.get("data", [])[:2] if data.get("data") else []
    }
    
    return create_mcp_response(debug_info)

@app.route("/bot-status")
def bot_status():
    """Endpoint específico para verificar estado del bot"""
    return create_mcp_response({
        "bot_running": bot_running,
        "token_configured": bool(TELEGRAM_TOKEN),
        "active_sessions": len(user_creation_state),
        "app_initialized": telegram_app is not None,
        "timestamp": datetime.now().isoformat()
    })

@app.route("/wake-bot", methods=["POST"])
def wake_bot():
    """Endpoint para despertar/reiniciar el bot"""
    global bot_running
    
    if not bot_running and TELEGRAM_TOKEN:
        success = start_telegram_bot_thread()
        return create_mcp_response({
            "action": "wake_bot",
            "success": success,
            "bot_running": bot_running,
            "timestamp": datetime.now().isoformat()
        })
    else:
        return create_mcp_response({
            "action": "wake_bot",
            "message": "Bot already running or token not configured",
            "bot_running": bot_running,
            "timestamp": datetime.now().isoformat()
        })

# Endpoints REST simplificados
@app.route("/api/list-initiatives")
def api_list_initiatives():
    """REST endpoint para listar iniciativas"""
    limit = request.args.get('limit', 25, type=int)
    data = get_nocodb_initiatives()
    
    if data.get("success"):
        initiatives = data.get("data", [])[:limit]
        return create_mcp_response({
            "success": True,
            "count": len(initiatives),
            "data": initiatives
        })
    else:
        return create_mcp_response({
            "success": False,
            "error": data.get("error")
        }, 500)

@app.route("/api/create-initiative", methods=["POST"])
def api_create_initiative():
    """REST endpoint para crear iniciativa"""
    if not request.is_json:
        return create_mcp_response({"error": "JSON required"}, 400)
    
    data = request.get_json()
    result = create_nocodb_initiative(data)
    
    if result.get("success"):
        return create_mcp_response(result)
    else:
        return create_mcp_response(result, 400)

@app.route("/endpoints")
def list_endpoints():
    """Listar todos los endpoints"""
    endpoints = {
        "mcp_endpoints": {
            "root": {"url": "/", "methods": ["GET", "POST", "OPTIONS"], "description": "Endpoint principal MCP"}
        },
        "debug_endpoints": {
            "health": "/health",
            "test_nocodb": "/test-nocodb", 
            "debug": "/debug",
            "bot_status": "/bot-status",
            "wake_bot": "/wake-bot",
            "endpoints": "/endpoints"
        },
        "api_endpoints": {
            "list_initiatives": "/api/list-initiatives",
            "create_initiative": "/api/create-initiative"
        },
        "mcp_tools": ["list_initiatives", "create_initiative", "search_initiatives", "get_initiatives_stats"],
        "telegram_bot": {
            "configured": bool(TELEGRAM_TOKEN),
            "running": bot_running,
            "commands": ["/start", "/help", "/iniciativas", "/buscar", "/stats", "/crear", "/cancel"]
        }
    }
    
    return create_mcp_response(endpoints)

# ===== MANEJO DE SEÑALES PARA SHUTDOWN GRACEFUL =====

def signal_handler(sig, frame):
    """Manejar señales de shutdown"""
    global bot_running
    logger.info("🛑 Received shutdown signal")
    bot_running = False
    
    if telegram_app:
        try:
            # Intentar cerrar el bot gracefully
            asyncio.create_task(telegram_app.stop())
        except Exception as e:
            logger.error(f"Error stopping telegram app: {e}")
    
    sys.exit(0)

# Registrar signal handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting Initiatives MCP Server on port {port}")
    print(f"🔗 NocoDB Table: {NOCODB_TABLE_ID}")
    print(f"🤖 Telegram Bot: {'Configured' if TELEGRAM_TOKEN else 'Not configured'}")
    print("🔧 Available tools: list_initiatives, create_initiative, search_initiatives, get_initiatives_stats")
    
    # Iniciar bot de Telegram si está configurado
    bot_started = start_telegram_bot_thread()
    if bot_started:
        print("🤖 Telegram bot started successfully")
    else:
        print("⚠️ Telegram bot failed to start")
    
    # Iniciar servidor Flask
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"❌ Flask server error: {e}")
        print(f"❌ Server failed to start: {e}")
