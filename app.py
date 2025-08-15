# 🚀 Servidor MCP para Iniciativas con Bot de Telegram
import os
import json
import time
import sys
import asyncio
import threading
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
            'limit': 100,  # Aumentamos el límite
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
        print(f"📊 Raw data structure: {list(raw_data.keys())}")
        
        # NocoDB devuelve una estructura con 'list' y 'pageInfo'
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
                                "initiative_name": {
                                    "type": "string",
                                    "description": "Name of the initiative"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of the initiative"
                                },
                                "main_kpi": {
                                    "type": "string",
                                    "description": "Main KPI for the initiative"
                                },
                                "portal": {
                                    "type": "string",
                                    "description": "Portal associated with the initiative"
                                },
                                "owner": {
                                    "type": "string",
                                    "description": "Owner of the initiative"
                                },
                                "team": {
                                    "type": "string",
                                    "description": "Team responsible for the initiative"
                                },
                                "reach": {
                                    "type": "number",
                                    "description": "Reach score (0-1)",
                                    "minimum": 0,
                                    "maximum": 1
                                },
                                "impact": {
                                    "type": "number",
                                    "description": "Impact score (0-1)",
                                    "minimum": 0,
                                    "maximum": 1
                                },
                                "confidence": {
                                    "type": "number",
                                    "description": "Confidence score (0-1)",
                                    "minimum": 0,
                                    "maximum": 1
                                },
                                "effort": {
                                    "type": "number",
                                    "description": "Effort score (0-1)",
                                    "minimum": 0,
                                    "maximum": 1
                                }
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
                                "query": {
                                    "type": "string",
                                    "description": "Search term"
                                },
                                "field": {
                                    "type": "string",
                                    "enum": ["name", "owner", "team", "all"],
                                    "description": "Field to search in (default: all)",
                                    "default": "all"
                                },
                                "limit": {
                                    "type": "integer",
                                    "description": "Maximum results to return",
                                    "default": 10,
                                    "minimum": 1,
                                    "maximum": 50
                                }
                            },
                            "required": ["query"],
                            "additionalProperties": False
                        }
                    },
                    {
                        "name": "get_initiatives_stats",
                        "description": "Get statistical overview of initiatives.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "additionalProperties": False
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
        elif tool_name == "search_initiatives":
            return handle_search_initiatives(args, request_id)
        elif tool_name == "get_initiatives_stats":
            return handle_get_initiatives_stats(request_id)
        else:
            return create_mcp_response({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32601,
                    "message": f"Unknown tool: {tool_name}"
                },
                "id": request_id
            })
    
    else:
        return create_mcp_response({
            "jsonrpc": "2.0",
            "error": {
                "code": -32601,
                "message": f"Method not found: {method}"
            },
            "id": request_id
        })

def format_initiative_summary(initiative, index=None):
    """Formatear iniciativa para vista resumida"""
    summary_parts = []
    
    # Campos clave de la iniciativa
    name = initiative.get('initiative_name', 'Sin nombre')
    owner = initiative.get('owner', 'Sin dueño')
    team = initiative.get('team', 'Sin equipo')
    kpi = initiative.get('main_kpi', 'Sin KPI')
    
    prefix = f"**{index}.** " if index else ""
    summary_parts.append(f"**{name}**")
    summary_parts.append(f"👤 {owner}")
    summary_parts.append(f"👥 {team}")
    summary_parts.append(f"📊 {kpi}")
    
    return prefix + " • ".join(summary_parts)

def handle_list_initiatives(args, request_id):
    """Listar iniciativas"""
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
    
    try:
        limit = int(args.get("limit", 25))
        limit = max(1, min(limit, 100))
    except (ValueError, TypeError):
        limit = 25
    
    format_type = args.get("format", "summary")
    if format_type not in ["summary", "detailed", "json"]:
        format_type = "summary"
    
    limited_initiatives = initiatives[:limit]
    
    try:
        if format_type == "json":
            json_str = json.dumps(limited_initiatives, indent=2, ensure_ascii=False, default=str)
            result_text = f"📊 **Iniciativas en formato JSON**\n\n**Registros devueltos:** {len(limited_initiatives)} de {len(initiatives)} totales\n\n```json\n{json_str}\n```"
        
        elif format_type == "detailed":
            result_text = f"📊 **Listado Detallado de Iniciativas**\n\n**Total:** {len(initiatives)}\n**Mostrando:** {len(limited_initiatives)}\n\n"
            
            for i, initiative in enumerate(limited_initiatives, 1):
                if isinstance(initiative, dict):
                    result_text += f"### 🎯 Iniciativa #{i}\n"
                    for key, value in initiative.items():
                        safe_key = str(key) if key is not None else "campo_desconocido"
                        safe_value = str(value) if value is not None else "N/A"
                        result_text += f"- **{safe_key}:** {safe_value}\n"
                    result_text += "\n"
        
        else:  # summary
            result_text = f"🎯 **Lista de Iniciativas**\n\n**Total encontradas:** {len(initiatives)}\n**Mostrando:** {len(limited_initiatives)}\n\n"
            
            if limited_initiatives:
                for i, initiative in enumerate(limited_initiatives, 1):
                    if isinstance(initiative, dict):
                        result_text += format_initiative_summary(initiative, i) + "\n"
            else:
                result_text += "*No se encontraron iniciativas.*\n"
    
    except Exception as e:
        result_text = f"📊 **Lista de Iniciativas**\n\n**Error de formato:** {str(e)}\n**Iniciativas encontradas:** {len(initiatives)}"
    
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
    """Crear nueva iniciativa"""
    result = create_nocodb_initiative(args)
    
    if result.get("success"):
        result_text = f"✅ **Iniciativa Creada Exitosamente**\n\n"
        result_text += f"**Nombre:** {args.get('initiative_name')}\n"
        result_text += f"**Descripción:** {args.get('description')}\n"
        result_text += f"**Owner:** {args.get('owner')}\n"
        result_text += f"**Equipo:** {args.get('team')}\n"
        result_text += f"**KPI Principal:** {args.get('main_kpi')}\n"
        result_text += f"**Portal:** {args.get('portal')}\n\n"
        result_text += f"**Métricas:**\n"
        result_text += f"- Alcance: {args.get('reach', 0)}\n"
        result_text += f"- Impacto: {args.get('impact', 0)}\n"
        result_text += f"- Confianza: {args.get('confidence', 0)}\n"
        result_text += f"- Esfuerzo: {args.get('effort', 0)}\n"
    else:
        result_text = f"❌ **Error al crear iniciativa**\n\n**Error:** {result.get('error', 'Error desconocido')}"
    
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
    """Buscar iniciativas"""
    query = args.get("query", "").strip().lower()
    field = args.get("field", "all")
    limit = int(args.get("limit", 10))
    
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
                    "text": f"❌ **Error al buscar iniciativas**\n\n**Error:** {data.get('error')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    matching_initiatives = []
    
    for initiative in initiatives:
        if not isinstance(initiative, dict):
            continue
        
        match_found = False
        
        if field == "all":
            # Buscar en todos los campos de texto
            text_fields = ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal']
            for field_name in text_fields:
                if field_name in initiative:
                    field_value = str(initiative[field_name]).lower()
                    if query in field_value:
                        match_found = True
                        break
        else:
            # Buscar en campo específico
            field_map = {
                'name': 'initiative_name',
                'owner': 'owner',
                'team': 'team'
            }
            target_field = field_map.get(field, field)
            if target_field in initiative:
                field_value = str(initiative[target_field]).lower()
                if query in field_value:
                    match_found = True
        
        if match_found:
            matching_initiatives.append(initiative)
            if len(matching_initiatives) >= limit:
                break
    
    result_text = f"🔍 **Búsqueda de Iniciativas**\n\n"
    result_text += f"**Término:** `{args.get('query')}`\n"
    result_text += f"**Campo:** {field}\n"
    result_text += f"**Encontradas:** {len(matching_initiatives)} iniciativas\n\n"
    
    if matching_initiatives:
        for i, initiative in enumerate(matching_initiatives, 1):
            result_text += format_initiative_summary(initiative, i) + "\n"
    else:
        result_text += "*No se encontraron iniciativas que coincidan con la búsqueda.*"
    
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
    """Obtener estadísticas de iniciativas"""
    data = get_nocodb_initiatives()
    
    if not data.get("success"):
        return create_mcp_response({
            "jsonrpc": "2.0",
            "result": {
                "content": [{
                    "type": "text",
                    "text": f"❌ **Error al obtener estadísticas**\n\n**Error:** {data.get('error')}"
                }]
            },
            "id": request_id
        })
    
    initiatives = data.get("data", [])
    metadata = data.get("metadata", {})
    
    result_text = f"📈 **Estadísticas de Iniciativas**\n\n"
    result_text += f"**📊 Total de Iniciativas:** {len(initiatives):,}\n"
    result_text += f"**🔗 Fuente:** {metadata.get('source', 'Desconocida')}\n"
    result_text += f"**⏰ Última Actualización:** {metadata.get('retrieved_at', 'Desconocida')}\n\n"
    
    if initiatives:
        # Estadísticas por owner
        owners = {}
        teams = {}
        kpis = {}
        
        for initiative in initiatives:
            if isinstance(initiative, dict):
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                kpi = initiative.get('main_kpi', 'Sin KPI')
                
                owners[owner] = owners.get(owner, 0) + 1
                teams[team] = teams.get(team, 0) + 1
                kpis[kpi] = kpis.get(kpi, 0) + 1
        
        result_text += f"**👤 Top Owners:**\n"
        for owner, count in sorted(owners.items(), key=lambda x: x[1], reverse=True)[:5]:
            result_text += f"- {owner}: {count} iniciativas\n"
        
        result_text += f"\n**👥 Top Teams:**\n"
        for team, count in sorted(teams.items(), key=lambda x: x[1], reverse=True)[:5]:
            result_text += f"- {team}: {count} iniciativas\n"
        
        result_text += f"\n**📊 Top KPIs:**\n"
        for kpi, count in sorted(kpis.items(), key=lambda x: x[1], reverse=True)[:5]:
            result_text += f"- {kpi}: {count} iniciativas\n"
    
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

# ===== BOT DE TELEGRAM =====

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start del bot"""
    welcome_text = """
🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos disponibles:**
/iniciativas - Ver todas las iniciativas
/crear - Crear una nueva iniciativa
/buscar <término> - Buscar iniciativas
/stats - Ver estadísticas
/help - Ver esta ayuda

¿En qué puedo ayudarte?
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help del bot"""
    help_text = """
🆘 **Ayuda - Bot de Iniciativas**

**Comandos disponibles:**

🎯 **/iniciativas** - Listar todas las iniciativas
📝 **/crear** - Crear una nueva iniciativa (modo interactivo)
🔍 **/buscar** <término> - Buscar iniciativas por nombre, owner o equipo
📈 **/stats** - Ver estadísticas de iniciativas
🆘 **/help** - Mostrar esta ayuda

**Ejemplos:**
• `/buscar Product` - Busca iniciativas del equipo Product
• `/buscar Danna` - Busca iniciativas de Danna
• `/crear` - Inicia el proceso de creación de iniciativa

¿Necesitas ayuda con algo específico?
    """
    await update.message.reply_text(help_text)

async def list_initiatives_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /iniciativas del bot"""
    try:
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error al obtener iniciativas: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])[:10]  # Limitar a 10 para Telegram
        
        if not initiatives:
            await update.message.reply_text("📭 No se encontraron iniciativas.")
            return
        
        response_text = f"🎯 **Iniciativas ({len(initiatives)} de {len(data.get('data', []))})**\n\n"
        
        for i, initiative in enumerate(initiatives, 1):
            if isinstance(initiative, dict):
                name = initiative.get('initiative_name', 'Sin nombre')
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                kpi = initiative.get('main_kpi', 'Sin KPI')
                
                response_text += f"**{i}. {name}**\n"
                response_text += f"👤 {owner} • 👥 {team}\n"
                response_text += f"📊 {kpi}\n\n"
        
        if len(data.get('data', [])) > 10:
            response_text += f"📋 *Mostrando las primeras 10 de {len(data.get('data', []))} iniciativas*"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
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
            await update.message.reply_text(f"❌ Error al buscar: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        matching_initiatives = []
        
        query_lower = query.lower()
        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
            
            # Buscar en campos de texto
            text_fields = ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal']
            for field_name in text_fields:
                if field_name in initiative:
                    field_value = str(initiative[field_name]).lower()
                    if query_lower in field_value:
                        matching_initiatives.append(initiative)
                        break
        
        if not matching_initiatives:
            await update.message.reply_text(f"🔍 No se encontraron iniciativas con: `{query}`")
            return
        
        # Limitar resultados para Telegram
        limited_results = matching_initiatives[:5]
        
        response_text = f"🔍 **Resultados para: `{query}`**\n"
        response_text += f"**Encontradas:** {len(matching_initiatives)}\n\n"
        
        for i, initiative in enumerate(limited_results, 1):
            name = initiative.get('initiative_name', 'Sin nombre')
            owner = initiative.get('owner', 'Sin dueño')
            team = initiative.get('team', 'Sin equipo')
            
            response_text += f"**{i}. {name}**\n"
            response_text += f"👤 {owner} • 👥 {team}\n\n"
        
        if len(matching_initiatives) > 5:
            response_text += f"📋 *Mostrando las primeras 5 de {len(matching_initiatives)} encontradas*"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error en búsqueda: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /stats del bot"""
    try:
        data = get_nocodb_initiatives()
        
        if not data.get("success"):
            await update.message.reply_text(f"❌ Error al obtener estadísticas: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            await update.message.reply_text("📊 No hay iniciativas para analizar.")
            return
        
        # Calcular estadísticas
        owners = {}
        teams = {}
        kpis = {}
        
        for initiative in initiatives:
            if isinstance(initiative, dict):
                owner = initiative.get('owner', 'Sin dueño')
                team = initiative.get('team', 'Sin equipo')
                kpi = initiative.get('main_kpi', 'Sin KPI')
                
                owners[owner] = owners.get(owner, 0) + 1
                teams[team] = teams.get(team, 0) + 1
                kpis[kpi] = kpis.get(kpi, 0) + 1
        
        response_text = f"📈 **Estadísticas de Iniciativas**\n\n"
        response_text += f"**📊 Total:** {len(initiatives)} iniciativas\n\n"
        
        # Top 3 owners
        response_text += f"**👤 Top Owners:**\n"
        for owner, count in sorted(owners.items(), key=lambda x: x[1], reverse=True)[:3]:
            response_text += f"• {owner}: {count}\n"
        
        # Top 3 teams
        response_text += f"\n**👥 Top Teams:**\n"
        for team, count in sorted(teams.items(), key=lambda x: x[1], reverse=True)[:3]:
            response_text += f"• {team}: {count}\n"
        
        # Top 3 KPIs
        response_text += f"\n**📊 Top KPIs:**\n"
        for kpi, count in sorted(kpis.items(), key=lambda x: x[1], reverse=True)[:3]:
            response_text += f"• {kpi}: {count}\n"
        
        await update.message.reply_text(response_text, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error en estadísticas: {str(e)}")

# Estado para el proceso de creación de iniciativas
user_creation_state = {}

async def create_initiative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /crear del bot - inicio del proceso interactivo"""
    user_id = update.effective_user.id
    
    # Inicializar estado de creación
    user_creation_state[user_id] = {
        'step': 'name',
        'data': {}
    }
    
    await update.message.reply_text(
        "🆕 **Crear Nueva Iniciativa**\n\n"
        "Te guiaré paso a paso para crear la iniciativa.\n\n"
        "**Paso 1/6:** ¿Cuál es el nombre de la iniciativa?"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manejar mensajes de texto para el proceso de creación"""
    user_id = update.effective_user.id
    
    if user_id not in user_creation_state:
        # No está en proceso de creación, respuesta general
        await update.message.reply_text(
            "👋 ¡Hola! Usa /help para ver los comandos disponibles."
        )
        return
    
    state = user_creation_state[user_id]
    step = state['step']
    text = update.message.text.strip()
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            await update.message.reply_text(
                f"✅ Nombre: {text}\n\n"
                "**Paso 2/6:** ¿Cuál es la descripción de la iniciativa?"
            )
        
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            await update.message.reply_text(
                f"✅ Descripción guardada\n\n"
                "**Paso 3/6:** ¿Cuál es el KPI principal?\n"
                "Ejemplos: Productividad, Ventas, Satisfacción, etc."
            )
        
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            await update.message.reply_text(
                f"✅ KPI: {text}\n\n"
                "**Paso 4/6:** ¿En qué portal se ejecutará?\n"
                "Ejemplos: Admin, Customer, Partner, etc."
            )
        
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            await update.message.reply_text(
                f"✅ Portal: {text}\n\n"
                "**Paso 5/6:** ¿Quién es el owner/responsable de la iniciativa?"
            )
        
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            await update.message.reply_text(
                f"✅ Owner: {text}\n\n"
                "**Paso 6/6:** ¿Qué equipo será responsable?\n"
                "Ejemplos: Product, Engineering, Marketing, etc."
            )
        
        elif step == 'team':
            state['data']['team'] = text
            state['step'] = 'metrics'
            await update.message.reply_text(
                f"✅ Equipo: {text}\n\n"
                "**Métricas opcionales (presiona /skip para omitir):**\n"
                "Ingresa el alcance (reach) de 0 a 1:\n"
                "Ejemplo: 0.8 para 80% de alcance"
            )
        
        elif step == 'metrics':
            if text.lower() in ['/skip', 'skip']:
                # Saltar métricas y crear iniciativa
                await create_initiative_final(update, user_id)
            else:
                try:
                    reach = float(text)
                    if 0 <= reach <= 1:
                        state['data']['reach'] = reach
                        state['step'] = 'impact'
                        await update.message.reply_text(
                            f"✅ Alcance: {reach}\n\n"
                            "Ingresa el impacto de 0 a 1:"
                        )
                    else:
                        await update.message.reply_text(
                            "❌ El alcance debe estar entre 0 y 1. Intenta de nuevo:"
                        )
                except ValueError:
                    await update.message.reply_text(
                        "❌ Ingresa un número válido entre 0 y 1, o /skip para omitir:"
                    )
        
        elif step == 'impact':
            try:
                impact = float(text)
                if 0 <= impact <= 1:
                    state['data']['impact'] = impact
                    state['step'] = 'confidence'
                    await update.message.reply_text(
                        f"✅ Impacto: {impact}\n\n"
                        "Ingresa la confianza de 0 a 1:"
                    )
                else:
                    await update.message.reply_text(
                        "❌ El impacto debe estar entre 0 y 1. Intenta de nuevo:"
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Ingresa un número válido entre 0 y 1:"
                )
        
        elif step == 'confidence':
            try:
                confidence = float(text)
                if 0 <= confidence <= 1:
                    state['data']['confidence'] = confidence
                    state['step'] = 'effort'
                    await update.message.reply_text(
                        f"✅ Confianza: {confidence}\n\n"
                        "Ingresa el esfuerzo de 0 a 1:"
                    )
                else:
                    await update.message.reply_text(
                        "❌ La confianza debe estar entre 0 y 1. Intenta de nuevo:"
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Ingresa un número válido entre 0 y 1:"
                )
        
        elif step == 'effort':
            try:
                effort = float(text)
                if 0 <= effort <= 1:
                    state['data']['effort'] = effort
                    await create_initiative_final(update, user_id)
                else:
                    await update.message.reply_text(
                        "❌ El esfuerzo debe estar entre 0 y 1. Intenta de nuevo:"
                    )
            except ValueError:
                await update.message.reply_text(
                    "❌ Ingresa un número válido entre 0 y 1:"
                )
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error procesando respuesta: {str(e)}")
        # Limpiar estado en caso de error
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def create_initiative_final(update: Update, user_id: int):
    """Crear la iniciativa final con los datos recopilados"""
    try:
        state = user_creation_state[user_id]
        data = state['data']
        
        # Valores por defecto para métricas si no se proporcionaron
        if 'reach' not in data:
            data['reach'] = 0.5
        if 'impact' not in data:
            data['impact'] = 0.5
        if 'confidence' not in data:
            data['confidence'] = 0.5
        if 'effort' not in data:
            data['effort'] = 0.5
        
        # Mostrar resumen antes de crear
        summary = f"📋 **Resumen de la Iniciativa:**\n\n"
        summary += f"**Nombre:** {data['initiative_name']}\n"
        summary += f"**Descripción:** {data['description']}\n"
        summary += f"**KPI:** {data['main_kpi']}\n"
        summary += f"**Portal:** {data['portal']}\n"
        summary += f"**Owner:** {data['owner']}\n"
        summary += f"**Equipo:** {data['team']}\n"
        summary += f"**Alcance:** {data['reach']}\n"
        summary += f"**Impacto:** {data['impact']}\n"
        summary += f"**Confianza:** {data['confidence']}\n"
        summary += f"**Esfuerzo:** {data['effort']}\n\n"
        summary += "⏳ Creando iniciativa..."
        
        await update.message.reply_text(summary, parse_mode='Markdown')
        
        # Crear la iniciativa
        result = create_nocodb_initiative(data)
        
        if result.get("success"):
            await update.message.reply_text(
                f"🎉 **¡Iniciativa creada exitosamente!**\n\n"
                f"**{data['initiative_name']}** ha sido agregada al sistema.\n\n"
                "Usa /iniciativas para ver todas las iniciativas."
            )
        else:
            await update.message.reply_text(
                f"❌ **Error al crear la iniciativa:**\n{result.get('error', 'Error desconocido')}\n\n"
                "Intenta de nuevo con /crear"
            )
        
        # Limpiar estado del usuario
        if user_id in user_creation_state:
            del user_creation_state[user_id]
    
    except Exception as e:
        await update.message.reply_text(f"❌ Error al crear iniciativa: {str(e)}")
        if user_id in user_creation_state:
            del user_creation_state[user_id]

async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /skip para saltar métricas"""
    user_id = update.effective_user.id
    
    if user_id in user_creation_state:
        state = user_creation_state[user_id]
        if state['step'] in ['metrics', 'impact', 'confidence', 'effort']:
            await create_initiative_final(update, user_id)
        else:
            await update.message.reply_text("No hay nada que saltar en este paso.")
    else:
        await update.message.reply_text("No estás en proceso de creación de iniciativa.")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /cancel para cancelar creación"""
    user_id = update.effective_user.id
    
    if user_id in user_creation_state:
        del user_creation_state[user_id]
        await update.message.reply_text("❌ Creación de iniciativa cancelada.")
    else:
        await update.message.reply_text("No hay proceso de creación activo.")

def setup_telegram_bot():
    """Configurar y ejecutar el bot de Telegram"""
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Comandos
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("iniciativas", list_initiatives_command))
        application.add_handler(CommandHandler("buscar", search_initiatives_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("crear", create_initiative_command))
        application.add_handler(CommandHandler("skip", skip_command))
        application.add_handler(CommandHandler("cancel", cancel_command))
        
        # Manejar mensajes de texto
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Ejecutar el bot
        print("🤖 Starting Telegram bot...")
        application.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        print(f"❌ Error setting up Telegram bot: {str(e)}")

def run_telegram_bot():
    """Ejecutar el bot de Telegram en un hilo separado"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        setup_telegram_bot()
    except Exception as e:
        print(f"❌ Error running Telegram bot: {str(e)}")

# ===== ENDPOINTS ADICIONALES =====

@app.route("/health")
def health():
    """Health check"""
    return create_mcp_response({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "telegram_bot": "configured" if TELEGRAM_TOKEN else "not_configured",
        "nocodb": "configured" if NOCODB_TOKEN else "not_configured"
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
        "sample_data": data.get("data", [])[:2] if data.get("data") else [],
        "telegram_bot": {
            "token_configured": bool(TELEGRAM_TOKEN),
            "active_creation_sessions": len(user_creation_state)
        },
        "cache_info": {
            "has_cache": initiatives_cache is not None,
            "cache_age_seconds": time.time() - cache_time if cache_time else None
        }
    }
    
    return create_mcp_response(debug_info)

# Endpoints REST para probar
@app.route("/api/list-initiatives")
def api_list_initiatives():
    """REST endpoint para listar iniciativas"""
    limit = request.args.get('limit', 25, type=int)
    format_type = request.args.get('format', 'summary')
    
    args = {"limit": limit, "format": format_type}
    mcp_response = handle_list_initiatives(args, "api-test")
    
    return mcp_response.get_data(as_text=True)

@app.route("/api/create-initiative", methods=["POST"])
def api_create_initiative():
    """REST endpoint para crear iniciativa"""
    if not request.is_json:
        return create_mcp_response({"error": "JSON required"}, 400)
    
    data = request.get_json()
    mcp_response = handle_create_initiative(data, "api-test")
    
    return mcp_response.get_data(as_text=True)

@app.route("/api/search-initiatives/<query>")
def api_search_initiatives(query):
    """REST endpoint para buscar iniciativas"""
    field = request.args.get('field', 'all')
    limit = request.args.get('limit', 10, type=int)
    
    args = {"query": query, "field": field, "limit": limit}
    mcp_response = handle_search_initiatives(args, "api-test")
    
    return mcp_response.get_data(as_text=True)

@app.route("/endpoints")
def list_endpoints():
    """Listar todos los endpoints"""
    endpoints = {
        "mcp_endpoints": {
            "root": {
                "url": "/",
                "methods": ["GET", "POST", "OPTIONS"],
                "description": "Endpoint principal MCP"
            }
        },
        "debug_endpoints": {
            "health": "/health",
            "test_nocodb": "/test-nocodb", 
            "debug": "/debug",
            "endpoints": "/endpoints"
        },
        "api_endpoints": {
            "list_initiatives": "/api/list-initiatives",
            "create_initiative": "/api/create-initiative",
            "search_initiatives": "/api/search-initiatives/<query>"
        },
        "mcp_tools": [
            "list_initiatives",
            "create_initiative", 
            "search_initiatives",
            "get_initiatives_stats"
        ],
        "telegram_bot": {
            "configured": bool(TELEGRAM_TOKEN),
            "commands": ["/start", "/help", "/iniciativas", "/buscar", "/stats", "/crear"]
        }
    }
    
    return create_mcp_response(endpoints)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting Initiatives MCP Server on port {port}")
    print(f"🔗 NocoDB Table ID: {NOCODB_TABLE_ID}")
    print(f"🤖 Telegram Bot: {'Configured' if TELEGRAM_TOKEN else 'Not configured'}")
    print("🔧 Available tools: list_initiatives, create_initiative, search_initiatives, get_initiatives_stats")
    
    # Iniciar bot de Telegram en hilo separado si está configurado
    if TELEGRAM_TOKEN:
        telegram_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        telegram_thread.start()
        print("🤖 Telegram bot started in background")
    else:
        print("⚠️ Telegram bot not started - token not configured")
    
    # Iniciar servidor Flask
    app.run(host='0.0.0.0', port=port, debug=False)
