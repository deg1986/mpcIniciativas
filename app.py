# 🚀 MCP Saludia - Gestión de Iniciativas con AI para Equipos Internos
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

# Configuración LLM - Groq
GROQ_API_KEY = os.environ.get('GROQ_API_KEY', '')
GROQ_MODEL = "llama-3.1-8b-instant"

# Variables globales
user_states = {}
bot_configured = False

def get_initiatives():
    """Obtener iniciativas de NocoDB"""
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        params = {'limit': 100}  # Aumentado para obtener más datos
        
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

def search_initiatives(query, field="all"):
    """Buscar iniciativas por término"""
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            return {"success": False, "error": data.get("error"), "results": []}
        
        initiatives = data.get("data", [])
        matching = []
        query_lower = query.lower()
        
        search_fields = {
            "all": ['initiative_name', 'description', 'owner', 'team', 'main_kpi', 'portal'],
            "name": ['initiative_name'],
            "owner": ['owner'],
            "team": ['team'],
            "kpi": ['main_kpi'],
            "portal": ['portal'],
            "description": ['description']
        }
        
        fields_to_search = search_fields.get(field, search_fields["all"])
        
        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
                
            for field_name in fields_to_search:
                if field_name in initiative:
                    field_value = str(initiative[field_name]).lower()
                    if query_lower in field_value:
                        matching.append(initiative)
                        break
        
        logger.info(f"✅ Search '{query}' found {len(matching)} results")
        return {"success": True, "results": matching, "total": len(matching)}
        
    except Exception as e:
        logger.error(f"❌ Error searching initiatives: {e}")
        return {"success": False, "error": str(e), "results": []}

def query_llm(prompt, context=None):
    """Consultar LLM con prompt personalizado para Saludia"""
    if not GROQ_API_KEY:
        return {"success": False, "error": "LLM no configurado", "response": "El asistente AI no está disponible en este momento."}
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # PROMPT PERSONALIZADO PARA SALUDIA
        system_message = """Eres el Asistente de Iniciativas de Saludia, especializado en gestión estratégica para equipos internos.

🏢 SOBRE SALUDIA:
- Marketplace líder que conecta droguerías independientes con sellers y laboratorios
- Modelo de negocio: Plataforma que facilita transacciones B2B en el sector farmacéutico
- Stakeholders principales: Droguerías (compradores), Sellers/Laboratorios (vendedores), equipo interno
- Misión: Democratizar el acceso a productos farmacéuticos para droguerías independientes

👥 EQUIPOS INTERNOS DE SALUDIA:
- Product: Desarrollo de funcionalidades del marketplace
- Engineering: Infraestructura técnica y APIs
- Operations: Gestión de operaciones y fulfillment
- Sales: Acquisition de droguerías y sellers
- Marketing: Growth y retención de usuarios
- Customer Success: Soporte y satisfacción de clientes
- Data/Analytics: Business intelligence y métricas

🎯 PORTALES/PRODUCTOS:
- Admin: Panel interno para gestión operacional
- Droguería: Interfaz para compradores (droguerías)
- Seller: Interfaz para vendedores (laboratorios/distribuidores)
- Mobile: Apps móviles para ambos segmentos
- API: Integraciones con sistemas externos

📊 MÉTRICAS DE INICIATIVAS:
- Reach (0-1): Alcance/cobertura (% de usuarios impactados)
- Impact (0-1): Impacto en métricas clave del negocio
- Confidence (0-1): Nivel de confianza en el éxito
- Effort (0-1): Esfuerzo/recursos requeridos para implementar

🎯 TU EXPERTISE COMO CONSULTOR:
- Análisis de portfolio de iniciativas internas
- Optimización de recursos entre equipos
- Identificación de gaps en experiencia de droguerías/sellers
- Recomendaciones para mejorar GMV, retención y satisfacción
- Detección de oportunidades de automatización y eficiencia operacional
- Balance entre growth initiatives vs operational excellence

💡 ESTILO DE RESPUESTA:
- Profesional pero cercano para equipos internos
- Usa emojis estratégicamente para claridad
- Estructura información con bullet points cuando sea útil
- Proporciona insights accionables específicos para marketplace
- Considera el impacto en ambos lados del marketplace (supply & demand)
- Enfócate en métricas que importan: GMV, Take Rate, Retention, NPS
- Siempre en español

🔍 CUANDO ANALICES INICIATIVAS:
1. Evalúa balance entre iniciativas de growth vs operational
2. Identifica oportunidades de colaboración cross-team
3. Considera impacto en ambos lados: droguerías Y sellers
4. Busca gaps en customer experience o friction points
5. Evalúa potencial de automatización para reducir costos operacionales
6. Sugiere KPIs complementarios alineados al negocio del marketplace

🚀 CONTEXTO DE MARKETPLACE FARMACÉUTICO:
- Industria altamente regulada y tradicional
- Importancia de confianza y reliability en transacciones
- Necesidad de gestión eficiente de inventario y logística
- Oportunidades en digitalización de procesos tradicionales

Tu objetivo: Ayudar a los equipos internos a optimizar iniciativas para maximizar el crecimiento y eficiencia del marketplace."""

        messages = [{"role": "system", "content": system_message}]
        
        # Agregar contexto si se proporciona
        if context:
            context_message = f"📋 DATOS ACTUALES DE INICIATIVAS:\n{context}\n\n💭 Analiza considerando los objetivos estratégicos de Saludia como marketplace."
            messages.append({"role": "user", "content": context_message})
        
        # Agregar la consulta del usuario
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            
            logger.info(f"✅ LLM query successful")
            return {"success": True, "response": ai_response}
        else:
            logger.error(f"❌ LLM HTTP {response.status_code}: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}", "response": "Error consultando el asistente AI."}
    
    except Exception as e:
        logger.error(f"❌ Error querying LLM: {e}")
        return {"success": False, "error": str(e), "response": "Error técnico del asistente AI."}

def analyze_initiatives_with_llm(initiatives):
    """Analizar iniciativas usando LLM"""
    if not initiatives:
        return "No hay iniciativas para analizar."
    
    # Preparar contexto detallado para el LLM
    context = f"PORTFOLIO ACTUAL DE SALUDIA ({len(initiatives)} iniciativas):\n\n"
    
    # Agrupar por equipos para mejor análisis
    teams = {}
    for init in initiatives:
        team = init.get('team', 'Sin equipo')
        if team not in teams:
            teams[team] = []
        teams[team].append(init)
    
    for team, team_initiatives in teams.items():
        context += f"📋 EQUIPO {team.upper()} ({len(team_initiatives)} iniciativas):\n"
        for init in team_initiatives:
            name = init.get('initiative_name', 'Sin nombre')
            owner = init.get('owner', 'Sin owner')
            kpi = init.get('main_kpi', 'Sin KPI')
            portal = init.get('portal', 'Sin portal')
            reach = init.get('reach', 'N/A')
            impact = init.get('impact', 'N/A')
            confidence = init.get('confidence', 'N/A')
            effort = init.get('effort', 'N/A')
            
            context += f"  • {name}\n"
            context += f"    Owner: {owner} | KPI: {kpi} | Portal: {portal}\n"
            context += f"    Métricas: R:{reach} I:{impact} C:{confidence} E:{effort}\n"
        context += "\n"
    
    prompt = """Realiza un análisis estratégico completo del portfolio de iniciativas de Saludia.

ANÁLISIS REQUERIDO:
1. 📊 Distribución de recursos y esfuerzo entre equipos
2. 🎯 Balance entre iniciativas de growth vs operational excellence
3. 🔄 Oportunidades de sinergia cross-team para el marketplace
4. ⚠️ Gaps críticos en experiencia de droguerías o sellers
5. 📈 Recomendaciones específicas para maximizar GMV y retención

Enfócate en insights accionables para líderes de equipos internos."""
    
    result = query_llm(prompt, context)
    return result.get("response", "Error analizando iniciativas.")

def format_initiative_detailed(initiative, index=None):
    """Formatear iniciativa con información detallada"""
    try:
        name = initiative.get('initiative_name', 'Sin nombre')
        description = initiative.get('description', 'Sin descripción')
        owner = initiative.get('owner', 'Sin owner')
        team = initiative.get('team', 'Sin equipo')
        kpi = initiative.get('main_kpi', 'Sin KPI')
        portal = initiative.get('portal', 'Sin portal')
        
        # Métricas con validación
        reach = initiative.get('reach', 0)
        impact = initiative.get('impact', 0)
        confidence = initiative.get('confidence', 0)
        effort = initiative.get('effort', 0)
        
        # Convertir a números si es posible
        try:
            reach = float(reach) if reach else 0
            impact = float(impact) if impact else 0
            confidence = float(confidence) if confidence else 0
            effort = float(effort) if effort else 0
        except:
            reach = impact = confidence = effort = 0
        
        # Formatear métricas como porcentajes
        reach_pct = f"{reach*100:.0f}%" if reach > 0 else "N/A"
        impact_pct = f"{impact*100:.0f}%" if impact > 0 else "N/A"
        confidence_pct = f"{confidence*100:.0f}%" if confidence > 0 else "N/A"
        effort_pct = f"{effort*100:.0f}%" if effort > 0 else "N/A"
        
        prefix = f"**{index}.** " if index else ""
        
        formatted = f"""{prefix}🎯 **{name}**
📝 {description[:100]}{'...' if len(description) > 100 else ''}
👤 **Owner:** {owner} | 👥 **Equipo:** {team}
📊 **KPI:** {kpi} | 🖥️ **Portal:** {portal}
📈 **Métricas:** Alcance {reach_pct} | Impacto {impact_pct} | Confianza {confidence_pct} | Esfuerzo {effort_pct}"""
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting initiative: {e}")
        return f"{index}. **{initiative.get('initiative_name', 'Error de formato')}**"

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
        "name": "Saludia Initiatives MCP Server",
        "version": "2.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "company": "Saludia Marketplace",
        "description": "Sistema de gestión de iniciativas para equipos internos",
        "telegram_bot": {
            "enabled": bool(TELEGRAM_TOKEN),
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook" if TELEGRAM_TOKEN else None
        },
        "ai_assistant": {
            "enabled": bool(GROQ_API_KEY),
            "model": GROQ_MODEL,
            "provider": "Groq",
            "specialized_for": "Saludia marketplace context"
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
            "telegram_bot": "webhook_configured" if bot_configured else "not_configured",
            "ai_assistant": "configured" if GROQ_API_KEY else "not_configured"
        },
        "bot_info": {
            "webhook_configured": bot_configured,
            "active_sessions": len(user_states)
        },
        "nocodb_info": {
            "connection": "ok" if nocodb_test.get('success') else "failed",
            "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0
        },
        "ai_info": {
            "provider": "Groq",
            "model": GROQ_MODEL,
            "context": "Saludia marketplace operations",
            "api_key_configured": bool(GROQ_API_KEY)
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

@app.route('/api/initiatives')
def api_initiatives():
    """API para obtener iniciativas"""
    data = get_initiatives()
    return jsonify(data)

@app.route('/api/initiatives/search', methods=['GET'])
def api_search_initiatives():
    """API para buscar iniciativas"""
    query = request.args.get('q', '').strip()
    field = request.args.get('field', 'all')
    
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    result = search_initiatives(query, field)
    return jsonify(result)

@app.route('/api/create', methods=['POST'])
def api_create():
    """API para crear iniciativa"""
    if not request.json:
        return jsonify({"error": "JSON required"}), 400
    
    result = create_initiative(request.json)
    return jsonify(result)

@app.route('/ai/query', methods=['POST'])
def ai_query_endpoint():
    """Endpoint para consultar el LLM directamente"""
    if not request.json or 'prompt' not in request.json:
        return jsonify({"error": "Prompt required"}), 400
    
    prompt = request.json['prompt']
    context = request.json.get('context')
    
    result = query_llm(prompt, context)
    return jsonify(result)

@app.route('/ai/analyze-initiatives', methods=['POST'])
def analyze_initiatives_endpoint():
    """Endpoint para analizar iniciativas con AI"""
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            return jsonify({
                "success": False,
                "error": "No se pudieron obtener las iniciativas",
                "analysis": "Error al acceder a los datos."
            }), 500
        
        initiatives = data.get("data", [])
        analysis = analyze_initiatives_with_llm(initiatives)
        
        return jsonify({
            "success": True,
            "initiatives_count": len(initiatives),
            "analysis": analysis,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "analysis": "Error técnico durante el análisis."
        }), 500

# ===== BOT DE TELEGRAM =====

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
                elif text == '/analizar' or text == '/analyze':
                    handle_analyze_command(chat_id)
                elif text.startswith('/buscar ') or text.startswith('/search '):
                    query = text.split(' ', 1)[1] if ' ' in text else ""
                    if query:
                        handle_search_command(chat_id, query)
                    else:
                        send_telegram_message(chat_id, "❓ Uso: /buscar <término>\n\nEjemplo: /buscar Product")
                elif text.startswith('/preguntar ') or text.startswith('/ask '):
                    question = text.split(' ', 1)[1] if ' ' in text else ""
                    if question:
                        handle_ai_question(chat_id, question)
                    else:
                        send_telegram_message(chat_id, "❓ Uso: /preguntar <tu pregunta>\n\nEjemplo: /preguntar ¿Qué iniciativas necesita el equipo de Sales?")
                elif text.startswith('/'):
                    # Comando desconocido
                    send_telegram_message(chat_id, "❓ Comando no reconocido. Usa /help para ver comandos disponibles.")
                else:
                    # Mensaje de texto - proceso de creación o consulta AI
                    if user_id in user_states:
                        handle_text_message(chat_id, user_id, text)
                    else:
                        # Consulta general al AI
                        handle_ai_question(chat_id, text)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "ERROR", 500

def handle_start_command(chat_id):
    """Manejar comando /start"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot de Iniciativas Saludia**

¡Hola! Soy tu asistente de gestión de iniciativas para equipos internos de Saludia.

**🏢 Saludia:** Marketplace que conecta droguerías independientes con sellers y laboratorios.

**📋 Comandos principales:**
/iniciativas - Ver todas las iniciativas detalladas
/buscar <término> - Buscar iniciativas específicas
/crear - Crear nueva iniciativa
/analizar - Análisis AI del portfolio completo
/preguntar <pregunta> - Consultar al asistente AI

**🔍 Ejemplos de búsqueda:**
• `/buscar Product` - Iniciativas del equipo Product
• `/buscar droguería` - Iniciativas relacionadas con droguerías
• `/buscar API` - Iniciativas de integraciones

**🤖 Consultas AI:**
• "¿Qué gaps veo en el customer experience?"
• "¿Cómo balancear growth vs operational excellence?"
• "¿Qué iniciativas faltan para mejorar seller experience?"

¿En qué puedo ayudarte hoy?"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_help_command(chat_id):
    """Manejar comando /help"""
    logger.info(f"📱 /help from chat {chat_id}")
    
    text = """🆘 **Ayuda - Bot Saludia**

**📋 Gestión de Iniciativas:**
• /iniciativas - Lista completa con métricas detalladas
• /buscar <término> - Buscar por nombre, equipo, owner, etc.
• /crear - Proceso guiado para nueva iniciativa

**🤖 Asistente AI especializado:**
• /analizar - Análisis estratégico del portfolio
• /preguntar <pregunta> - Consultas específicas
• O simplemente escribe tu pregunta

**🔍 Búsquedas avanzadas:**
• `/buscar Product team` - Por equipo
• `/buscar GMV` - Por KPI
• `/buscar seller` - Por término en descripción
• `/buscar Droguería portal` - Por portal

**💡 Ejemplos de preguntas AI:**
• "¿Qué iniciativas impactan más a las droguerías?"
• "¿Hay overlap entre equipos Product y Engineering?"
• "¿Qué gaps veo en la experiencia de sellers?"
• "¿Cómo priorizar las iniciativas por ROI?"

**🎯 Contexto:** Todas las respuestas están especializadas para el marketplace farmacéutico de Saludia.

¿Qué necesitas consultar?"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_list_initiatives(chat_id):
    """Manejar comando /iniciativas con información detallada"""
    logger.info(f"📱 /iniciativas from chat {chat_id}")
    
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            send_telegram_message(chat_id, f"❌ Error: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, "📭 No hay iniciativas disponibles en Saludia.")
            return
        
        # Agrupar por equipos para mejor organización
        teams = {}
        for init in initiatives:
            team = init.get('team', 'Sin equipo')
            if team not in teams:
                teams[team] = []
            teams[team].append(init)
        
        # Mostrar resumen primero
        summary_text = f"📊 **Portfolio Saludia - {len(initiatives)} iniciativas**\n\n"
        
        for team, team_initiatives in teams.items():
            summary_text += f"👥 **{team}:** {len(team_initiatives)} iniciativas\n"
        
        summary_text += f"\n🔍 **Tip:** Usa `/buscar <término>` para buscar específicas"
        summary_text += f"\n🤖 **Tip:** Usa `/analizar` para insights AI"
        
        send_telegram_message(chat_id, summary_text, "Markdown")
        
        # Mostrar primeras 5 iniciativas detalladas
        detailed_text = "📋 **Primeras 5 iniciativas detalladas:**\n\n"
        
        for i, initiative in enumerate(initiatives[:5], 1):
            detailed_text += format_initiative_detailed(initiative, i) + "\n\n"
        
        if len(initiatives) > 5:
            detailed_text += f"📋 *Mostrando 5 de {len(initiatives)}. Usa `/buscar` para encontrar específicas.*"
        
        send_telegram_message(chat_id, detailed_text, "Markdown")
        
        logger.info(f"✅ Listed {len(initiatives)} initiatives with details")
        
    except Exception as e:
        logger.error(f"❌ Error listing initiatives: {e}")
        send_telegram_message(chat_id, "❌ Error al obtener iniciativas.")

def handle_search_command(chat_id, query):
    """Manejar comando /buscar"""
    logger.info(f"📱 /buscar from chat {chat_id}: {query}")
    
    try:
        send_telegram_message(chat_id, f"🔍 Buscando '{query}'...")
        
        result = search_initiatives(query)
        
        if not result.get("success"):
            send_telegram_message(chat_id, f"❌ Error en búsqueda: {result.get('error')}")
            return
        
        matching = result.get("results", [])
        total = result.get("total", 0)
        
        if not matching:
            # Sugerir búsquedas alternativas con AI
            ai_suggestion = query_llm(f"El usuario buscó '{query}' pero no encontré resultados. Sugiere 3 términos de búsqueda alternativos relacionados con iniciativas de marketplace farmacéutico.")
            
            no_results_text = f"🔍 **Sin resultados para:** `{query}`\n\n"
            
            if ai_suggestion.get("success"):
                no_results_text += f"💡 **Sugerencias del AI:**\n{ai_suggestion.get('response')}\n\n"
            
            no_results_text += "**Términos comunes:**\n• Product, Engineering, Sales\n• droguería, seller, laboratorio\n• API, mobile, admin"
            
            send_telegram_message(chat_id, no_results_text, "Markdown")
            return
        
        # Mostrar resultados
        results_text = f"🔍 **Resultados para:** `{query}`\n**Encontradas:** {total} iniciativas\n\n"
        
        # Mostrar hasta 5 resultados detallados
        for i, initiative in enumerate(matching[:5], 1):
            results_text += format_initiative_detailed(initiative, i) + "\n\n"
        
        if total > 5:
            results_text += f"📋 *Mostrando 5 de {total} resultados. Refina tu búsqueda para menos resultados.*\n\n"
        
        # Agregar insights AI sobre los resultados
        if len(matching) >= 2:
            ai_insight = query_llm(f"Analiza brevemente estos {len(matching)} resultados de búsqueda para '{query}' y proporciona 1-2 insights clave.", 
                                 json.dumps([{
                                     'name': init.get('initiative_name'),
                                     'team': init.get('team'),
                                     'kpi': init.get('main_kpi'),
                                     'owner': init.get('owner')
                                 } for init in matching[:5]], ensure_ascii=False))
            
            if ai_insight.get("success"):
                results_text += f"🤖 **Insight AI:**\n{ai_insight.get('response')}"
        
        send_telegram_message(chat_id, results_text, "Markdown")
        logger.info(f"✅ Search '{query}' returned {total} results")
        
    except Exception as e:
        logger.error(f"❌ Error in search: {e}")
        send_telegram_message(chat_id, "❌ Error durante la búsqueda.")

def handle_analyze_command(chat_id):
    """Manejar comando /analizar"""
    logger.info(f"📱 /analizar from chat {chat_id}")
    
    try:
        send_telegram_message(chat_id, "🤖 Analizando portfolio de iniciativas de Saludia...")
        
        data = get_initiatives()
        
        if not data.get("success"):
            send_telegram_message(chat_id, f"❌ Error obteniendo datos: {data.get('error')}")
            return
        
        initiatives = data.get("data", [])
        
        if not initiatives:
            send_telegram_message(chat_id, "📭 No hay iniciativas para analizar.")
            return
        
        analysis = analyze_initiatives_with_llm(initiatives)
        
        response_text = f"🤖 **Análisis AI - Portfolio Saludia**\n**Iniciativas analizadas:** {len(initiatives)}\n\n{analysis}"
        
        # Telegram tiene límite de 4096 caracteres por mensaje
        if len(response_text) > 4000:
            # Dividir el mensaje
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for i, part in enumerate(parts):
                if i == 0:
                    send_telegram_message(chat_id, part, "Markdown")
                else:
                    send_telegram_message(chat_id, f"**Continuación {i+1}:**\n\n{part}", "Markdown")
        else:
            send_telegram_message(chat_id, response_text, "Markdown")
        
        logger.info(f"✅ AI analysis completed for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in AI analysis: {e}")
        send_telegram_message(chat_id, "❌ Error durante el análisis AI.")

def handle_ai_question(chat_id, question):
    """Manejar preguntas al AI"""
    logger.info(f"🤖 AI question from chat {chat_id}: {question}")
    
    try:
        send_telegram_message(chat_id, "🤖 Consultando al asistente AI de Saludia...")
        
        # Obtener contexto de iniciativas para la consulta
        data = get_initiatives()
        context = None
        
        if data.get("success") and data.get("data"):
            initiatives = data.get("data", [])[:10]  # Limitar contexto
            context_parts = []
            
            # Agrupar por equipos para contexto más útil
            teams = {}
            for init in initiatives:
                team = init.get('team', 'Sin equipo')
                if team not in teams:
                    teams[team] = []
                teams[team].append(init)
            
            context_parts.append(f"CONTEXTO ACTUAL SALUDIA ({len(initiatives)} iniciativas):")
            for team, team_inits in teams.items():
                context_parts.append(f"\n{team}: {len(team_inits)} iniciativas")
                for init in team_inits[:3]:  # Max 3 por equipo en contexto
                    name = init.get('initiative_name', 'Sin nombre')
                    kpi = init.get('main_kpi', 'Sin KPI')
                    portal = init.get('portal', 'Sin portal')
                    context_parts.append(f"  • {name} (KPI: {kpi}, Portal: {portal})")
            
            context = "\n".join(context_parts)
        
        result = query_llm(question, context)
        
        if result.get("success"):
            response_text = f"🤖 **Respuesta del AI Saludia:**\n\n{result.get('response')}"
        else:
            response_text = f"❌ **Error:** {result.get('response', 'No se pudo consultar al AI.')}"
        
        # Manejar mensajes largos
        if len(response_text) > 4000:
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            for part in parts:
                send_telegram_message(chat_id, part, "Markdown")
        else:
            send_telegram_message(chat_id, response_text, "Markdown")
        
        logger.info(f"✅ AI response sent to chat {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Error handling AI question: {e}")
        send_telegram_message(chat_id, "❌ Error consultando al asistente AI.")

def handle_create_command(chat_id, user_id):
    """Manejar comando /crear"""
    logger.info(f"📱 /crear from user {user_id}")
    
    user_states[user_id] = {'step': 'name', 'data': {}, 'chat_id': chat_id}
    
    text = """🆕 **Crear Nueva Iniciativa Saludia**

Te guiaré paso a paso para crear una iniciativa optimizada para nuestro marketplace.

**Paso 1 de 6:** ¿Cuál es el nombre de la iniciativa?

💡 **Ejemplos para Saludia:**
• "Seller Onboarding Automation"
• "Droguería Mobile Experience Upgrade"
• "Inventory Sync API v2"

🤖 **Tip:** Escribe "sugerir nombres" si necesitas ideas del AI"""
    
    send_telegram_message(chat_id, text, "Markdown")

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de texto para creación"""
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    step = state['step']
    
    logger.info(f"📝 Step '{step}' for user {user_id}")
    
    try:
        if step == 'name':
            if text.lower() in ['sugerir nombres', 'sugerir', 'ayuda nombres']:
                # Sugerir nombres con AI
                ai_suggestion = query_llm("Sugiere 5 nombres creativos para nuevas iniciativas de Saludia marketplace, considerando diferentes equipos y objetivos como growth, operational efficiency, customer experience, etc.")
                
                if ai_suggestion.get("success"):
                    suggestion_text = f"🤖 **Sugerencias de nombres:**\n\n{ai_suggestion.get('response')}\n\n📝 **Escribe el nombre que prefieras:**"
                    send_telegram_message(chat_id, suggestion_text, "Markdown")
                else:
                    send_telegram_message(chat_id, "❌ Error obteniendo sugerencias. Escribe el nombre de tu iniciativa:")
                return
            
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            response = f"✅ **Nombre:** {text}\n\n**Paso 2 de 6:** ¿Cuál es la descripción de la iniciativa?\n\n💡 **Incluye:** Objetivo, beneficio para droguerías/sellers, impacto esperado"
            
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'kpi'
            response = "✅ **Descripción guardada**\n\n**Paso 3 de 6:** ¿Cuál es el KPI principal?\n\n💡 **KPIs comunes en Saludia:**\n• GMV, Take Rate, Conversion Rate\n• User Retention, NPS, Time to Onboard\n• Order Volume, Inventory Turnover"
            
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            response = f"✅ **KPI:** {text}\n\n**Paso 4 de 6:** ¿En qué portal/producto impacta?\n\n💡 **Portales Saludia:**\n• Droguería (app compradores)\n• Seller (app vendedores)\n• Admin (panel interno)\n• Mobile (apps móviles)\n• API (integraciones)"
            
        elif step == 'portal':
            state['data']['portal'] = text
            state['step'] = 'owner'
            response = f"✅ **Portal:** {text}\n\n**Paso 5 de 6:** ¿Quién es el owner/líder de esta iniciativa?\n\n💡 **Puede ser una persona específica o rol**"
            
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            response = f"✅ **Owner:** {text}\n\n**Paso 6 de 6:** ¿Qué equipo será responsable?\n\n💡 **Equipos Saludia:**\n• Product, Engineering, Operations\n• Sales, Marketing, Customer Success\n• Data/Analytics"
            
        elif step == 'team':
            state['data']['team'] = text
            await finish_creation(chat_id, user_id)
            return
        
        send_telegram_message(chat_id, response, "Markdown")
        
    except Exception as e:
        logger.error(f"❌ Error handling text: {e}")
        send_telegram_message(chat_id, "❌ Error procesando respuesta.")
        if user_id in user_states:
            del user_states[user_id]

async def finish_creation(chat_id, user_id):
    """Finalizar creación con sugerencias AI"""
    try:
        state = user_states[user_id]
        data = state['data']
        
        # Sugerir métricas optimizadas con AI
        ai_metrics = query_llm(f"Para la iniciativa '{data['initiative_name']}' del equipo {data['team']} de Saludia marketplace, sugiere valores realistas (0-1) para reach, impact, confidence y effort. Considera el contexto del marketplace farmacéutico.")
        
        # Valores por defecto mejorados para marketplace
        default_metrics = {
            'reach': 0.6,  # Alcance moderado típico
            'impact': 0.7,  # Impacto esperado alto
            'confidence': 0.8,  # Confianza alta en execution
            'effort': 0.5   # Esfuerzo medio
        }
        
        data.update(default_metrics)
        
        # Mostrar resumen con sugerencias AI
        summary = f"📋 **Resumen de Iniciativa Saludia:**\n\n"
        summary += f"🎯 **Nombre:** {data['initiative_name']}\n"
        summary += f"📝 **Descripción:** {data['description']}\n"
        summary += f"📊 **KPI:** {data['main_kpi']}\n"
        summary += f"🖥️ **Portal:** {data['portal']}\n"
        summary += f"👤 **Owner:** {data['owner']}\n"
        summary += f"👥 **Equipo:** {data['team']}\n\n"
        summary += f"📈 **Métricas (auto-calculadas):**\n"
        summary += f"• Alcance: {data['reach']*100:.0f}%\n"
        summary += f"• Impacto: {data['impact']*100:.0f}%\n"
        summary += f"• Confianza: {data['confidence']*100:.0f}%\n"
        summary += f"• Esfuerzo: {data['effort']*100:.0f}%\n\n"
        
        if ai_metrics.get("success"):
            summary += f"🤖 **Sugerencias AI:**\n{ai_metrics.get('response')}\n\n"
        
        summary += "⏳ **Creando iniciativa...**"
        
        send_telegram_message(chat_id, summary, "Markdown")
        
        # Crear la iniciativa
        result = create_initiative(data)
        
        if result.get("success"):
            success_text = f"🎉 **¡Iniciativa creada en Saludia!**\n\n"
            success_text += f"**{data['initiative_name']}** ha sido agregada al portfolio.\n\n"
            success_text += "📋 **Próximos pasos:**\n"
            success_text += "• Usa `/analizar` para ver impacto en portfolio\n"
            success_text += "• Usa `/buscar {data['team']}` para ver iniciativas del equipo\n"
            success_text += "• Pregunta al AI sobre sinergias con otras iniciativas"
        else:
            success_text = f"❌ **Error al crear iniciativa:**\n{result.get('error', 'Error desconocido')}\n\nIntenta de nuevo con `/crear`"
        
        send_telegram_message(chat_id, success_text, "Markdown")
        
        if user_id in user_states:
            del user_states[user_id]
            
        logger.info(f"✅ Finished creation for user {user_id}")
    
    except Exception as e:
        logger.error(f"❌ Error finishing creation for user {user_id}: {e}")
        error_text = f"❌ **Error al crear la iniciativa**\n\nError técnico: {str(e)}\n\nIntenta de nuevo con `/crear`"
        send_telegram_message(chat_id, error_text, "Markdown")
        if user_id in user_states:
            del user_states[user_id]

@app.route('/test')
def test():
    """Test del sistema"""
    nocodb_test = get_initiatives()
    search_test = search_initiatives("test", "all") if nocodb_test.get("success") else {"success": False}
    
    return jsonify({
        "test": "OK",
        "timestamp": datetime.now().isoformat(),
        "company": "Saludia Marketplace",
        "nocodb_connection": "OK" if nocodb_test.get('success') else "FAILED",
        "initiatives_count": len(nocodb_test.get('data', [])) if nocodb_test.get('success') else 0,
        "search_functionality": "OK" if search_test.get('success') else "FAILED",
        "telegram_webhook_configured": bot_configured,
        "ai_configured": bool(GROQ_API_KEY),
        "features": [
            "detailed_initiative_listing",
            "advanced_search",
            "ai_analysis",
            "contextual_recommendations",
            "saludia_marketplace_optimization"
        ]
    })

# ===== INICIO =====

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    print(f"🚀 Starting Saludia Initiatives MCP Server on port {port}")
    print(f"🏢 Company: Saludia Marketplace (Droguerías + Sellers + Laboratorios)")
    print(f"🎯 Purpose: Internal teams initiatives management")
    print(f"🤖 Telegram webhook: {WEBHOOK_URL}/telegram-webhook")
    print(f"🧠 AI Assistant: {'Configured with Saludia context' if GROQ_API_KEY else 'Not configured'}")
    print(f"🔍 Features: Advanced search, detailed listings, AI analysis")
    
    # Iniciar Flask
    app.run(host='0.0.0.0', port=port, debug=False)
