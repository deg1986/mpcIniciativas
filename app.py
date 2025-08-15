# 🚀 MCP Server con Bot de Telegram usando WEBHOOK (Compatible con Render)
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
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
WEBHOOK_URL = "https://mpciniciativas.onrender.com"

# Variables globales
user_states = {}
bot_configured = False

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

def send_telegram_message(chat_id, text, parse_mode=None):
    """Enviar mensaje a Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text
        }
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        response = requests.post(url, json=data, timeout=10)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Error sending message: {e}")
        return False

def setup_webhook():
    """Configurar webhook de Telegram"""
    try:
        # Eliminar webhook existente
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
        # Configurar nuevo webhook
        webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
        set_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
        data = {"url": webhook_url}
        
        response = requests.post(set_url, json=data, timeout=10)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Webhook configured: {webhook_url}")
                return True
            else:
                logger.error(f"❌ Webhook setup failed: {result}")
                return False
        else:
            logger.error(f"❌ Webhook HTTP {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"❌ Error setting up webhook: {e}")
        return False

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
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook" if TELEGRAM_TOKEN else None
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
            "telegram_bot": "webhook_configured" if bot_configured else "not_configured"
        },
        "bot_info": {
            "webhook_configured": bot_configured,
            "active_sessions": len(user_states)
        },
        "nocodb_info": {
            "connection": "ok" if nocodb_test.get('success') else "failed",
            "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0
        }
    })

@app.route('/setup-webhook', methods=['POST'])
def setup_webhook_endpoint():
    """Endpoint para configurar webhook"""
    global bot_configured
    
    try:
        success = setup_webhook()
        bot_configured = success
        
        return jsonify({
            "success": success,
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Webhook para recibir mensajes de Telegram"""
    try:
        update_data = request.get_json()
        
        if not update_data:
            return "OK", 200
        
        # Procesar el mensaje
        if 'message' in update_data:
            message = update_data['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            # Comandos
            if 'text' in message:
                text = message['text'].strip()
                
                if text == '/start':
                    handle_start_command(chat_id)
                elif text == '/help':
                    handle_help_command(chat_id)
                elif text == '/iniciativas':
                    handle_list_initiatives(chat_id)
                elif text == '/crear':
                    handle_create_command(chat_id, user_id)
                elif text.startswith('/'):
                    # Comando desconocido
                    send_telegram_message(chat_id, "❓ Comando no reconocido. Usa /help para ver comandos disponibles.")
                else:
                    # Mensaje de texto - proceso de creación
                    handle_text_message(chat_id, user_id, text)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "ERROR", 500

def handle_start_command(chat_id):
    """Manejar comando /start"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot de Iniciativas Farmuhub**

¡Hola! Soy tu asistente para gestionar iniciativas.

**Comandos disponibles:**
/iniciativas - Ver todas las iniciativas
/crear - Crear nueva iniciativa
/help - Ver ayuda

¿En qué puedo ayudarte?"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_help_command(chat_id):
    """Manejar comando /help"""
    logger.info(f"📱 /help from chat {chat_id}")
    
    text = """🆘 **Ayuda**

**Comandos:**
• /iniciativas - Lista todas las iniciativas
• /crear - Crear nueva iniciativa paso a paso
• /help - Esta ayuda

**Uso:**
1. /iniciativas para ver la lista
2. /crear para empezar a crear una nueva"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_list_initiatives(chat_id):
    """Manejar comando /iniciativas"""
    logger.info(f"📱 /iniciativas from chat {chat_id}")
    
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            send_telegram_message(chat_id, f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])[:8]
        
        if not initiatives:
            send_telegram_message(chat_id, "📭 No hay iniciativas disponibles.")
            return
        
        text = f"🎯 **Iniciativas ({len(initiatives)})**\n\n"
        
        for i, init in enumerate(initiatives, 1):
            name = init.get('initiative_name', 'Sin nombre')
            owner = init.get('owner', 'Sin owner')
            team = init.get('team', 'Sin equipo')
            
            text += f"**{i}. {name}**\n👤 {owner} • 👥 {team}\n\n"
        
        send_telegram_message(chat_id, text, "Markdown")
        logger.info(f"✅ Listed {len(initiatives)} initiatives")
        
    except Exception as e:
        logger.error(f"❌ Error listing initiatives: {e}")
        send_telegram_message(chat_id, "❌ Error al obtener iniciativas.")

def handle_create_command(chat_id, user_id):
    """Manejar comando /crear"""
    logger.info(f"📱 /crear from user {user_id}")
    
    user_states[user_id] = {'step': 'name', 'data': {}, 'chat_id': chat_id}
    
    text = """🆕 **Crear Nueva Iniciativa**

**Paso 1 de 6:** ¿Cuál es el nombre de la iniciativa?"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de texto para creación"""
    if user_id not in user_states:
        send_telegram_message(chat_id, "👋 Usa /help para ver comandos disponibles.")
        return
    
    state = user_states[user_id]
    step = state['step']
    
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
            finish_creation(chat_id, user_id)
            return
        
        send_telegram_message(chat_id, response, "Markdown")
        
    except Exception as e:
        logger.error(f"❌ Error handling text: {e}")
        send_telegram_message(chat_id, "❌ Error procesando respuesta.")
        if user_id in user_states:
            del user_states[user_id]

def finish_creation(chat_id, user_id):
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
        
        send_telegram_message(chat_id, "⏳ Creando iniciativa...")
        
        result = create_initiative(data)
        
        if result.get("success"):
            text = f"🎉 **¡Iniciativa creada!**\n\n**{data['initiative_name']}** agregada exitosamente."
        else:
            text = f"❌ **Error:** {result.get('error')}"
        
        send_telegram_message(chat_id, text, "Markdown")
        
        if user_id in user_states:
            del user_states[user_id]
            
        logger.info(f"✅ Finished creation for user {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Error finishing creation: {e}")
        send_telegram_message(chat_id, "❌ Error al crear iniciativa.")
        if user_id in user_states:
            del user_states[user_id]

@app.route('/test')
def test():
    """Test del sistema"""
    nocodb_test = get_initiatives()
    
    return jsonify({
        "test": "OK",
        "timestamp": datetime.now().isoformat(),
        "nocodb_connection": "OK" if nocodb_test.get('success') else "FAILED",
        "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0,
        "telegram_webhook_configured": bot_configured
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

# ===== INICIO =====

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting server on port {port}")
    print(f"🤖 Telegram webhook will be available at: {WEBHOOK_URL}/telegram-webhook")
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=port, debug=False)
