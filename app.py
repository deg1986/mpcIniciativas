# 🚀 MCP Saludia - Gestión de Iniciativas con Estadísticas Avanzadas
import os
import json
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from collections import Counter

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
        params = {'limit': 100}
        
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

def calculate_statistics(initiatives):
    """Calcular estadísticas detalladas con porcentajes"""
    if not initiatives:
        return {}
    
    total = len(initiatives)
    
    # Contadores
    teams = Counter()
    owners = Counter()
    kpis = Counter()
    portals = Counter()
    
    # Métricas numéricas
    total_reach = 0
    total_impact = 0
    total_confidence = 0
    total_effort = 0
    metric_count = 0
    
    for init in initiatives:
        if isinstance(init, dict):
            # Contadores básicos
            team = init.get('team', 'Sin equipo').strip()
            owner = init.get('owner', 'Sin owner').strip()
            kpi = init.get('main_kpi', 'Sin KPI').strip()
            portal = init.get('portal', 'Sin portal').strip()
            
            teams[team] += 1
            owners[owner] += 1
            kpis[kpi] += 1
            portals[portal] += 1
            
            # Métricas numéricas
            try:
                reach = float(init.get('reach', 0)) if init.get('reach') else 0
                impact = float(init.get('impact', 0)) if init.get('impact') else 0
                confidence = float(init.get('confidence', 0)) if init.get('confidence') else 0
                effort = float(init.get('effort', 0)) if init.get('effort') else 0
                
                if reach > 0 or impact > 0 or confidence > 0 or effort > 0:
                    total_reach += reach
                    total_impact += impact
                    total_confidence += confidence
                    total_effort += effort
                    metric_count += 1
            except:
                pass
    
    # Calcular porcentajes
    teams_pct = {team: (count/total)*100 for team, count in teams.most_common()}
    owners_pct = {owner: (count/total)*100 for owner, count in owners.most_common()}
    kpis_pct = {kpi: (count/total)*100 for kpi, count in kpis.most_common()}
    portals_pct = {portal: (count/total)*100 for portal, count in portals.most_common()}
    
    # Métricas promedio
    avg_metrics = {}
    if metric_count > 0:
        avg_metrics = {
            'reach': (total_reach / metric_count) * 100,
            'impact': (total_impact / metric_count) * 100,
            'confidence': (total_confidence / metric_count) * 100,
            'effort': (total_effort / metric_count) * 100
        }
    
    return {
        'total_initiatives': total,
        'teams': teams_pct,
        'owners': owners_pct,
        'kpis': kpis_pct,
        'portals': portals_pct,
        'average_metrics': avg_metrics,
        'top_teams': teams.most_common(5),
        'top_owners': owners.most_common(5),
        'top_kpis': kpis.most_common(3)
    }

def format_statistics_text(stats):
    """Formatear estadísticas para mostrar en Telegram"""
    if not stats:
        return "No hay datos para mostrar estadísticas."
    
    text = f"📊 **ESTADÍSTICAS SALUDIA** ({stats['total_initiatives']} iniciativas)\n\n"
    
    # Distribución por equipos
    text += "👥 **DISTRIBUCIÓN POR EQUIPOS:**\n"
    for team, percentage in list(stats['teams'].items())[:5]:
        count = next(count for t, count in stats['top_teams'] if t == team)
        text += f"• {team}: {count} iniciativas ({percentage:.1f}%)\n"
    
    # Top owners
    text += f"\n👤 **TOP RESPONSABLES:**\n"
    for owner, percentage in list(stats['owners'].items())[:5]:
        count = next(count for o, count in stats['top_owners'] if o == owner)
        text += f"• {owner}: {count} iniciativas ({percentage:.1f}%)\n"
    
    # KPIs más comunes
    text += f"\n📈 **KPIs MÁS COMUNES:**\n"
    for kpi, percentage in list(stats['kpis'].items())[:3]:
        count = next(count for k, count in stats['top_kpis'] if k == kpi)
        text += f"• {kpi}: {count} iniciativas ({percentage:.1f}%)\n"
    
    # Métricas promedio
    if stats['average_metrics']:
        text += f"\n📊 **MÉTRICAS PROMEDIO:**\n"
        metrics = stats['average_metrics']
        text += f"• Alcance: {metrics.get('reach', 0):.1f}%\n"
        text += f"• Impacto: {metrics.get('impact', 0):.1f}%\n"
        text += f"• Confianza: {metrics.get('confidence', 0):.1f}%\n"
        text += f"• Esfuerzo: {metrics.get('effort', 0):.1f}%\n"
    
    return text

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
        
        # PROMPT ESPECIALIZADO PARA SALUDIA
        system_message = """Eres el Asistente de Análisis de Iniciativas de Saludia, especializado en insights estratégicos para equipos internos.

🏢 SOBRE SALUDIA:
- Marketplace farmacéutico que conecta droguerías independientes con sellers y laboratorios
- Enfoque en democratizar acceso a productos farmacéuticos
- Stakeholders: Droguerías (compradores), Sellers/Laboratorios (vendedores), equipo interno

👥 EQUIPOS INTERNOS:
- Product: Desarrollo de funcionalidades del marketplace
- Engineering: Infraestructura técnica y APIs
- Operations: Gestión operacional y fulfillment
- Sales: Acquisition de droguerías y sellers
- Marketing: Growth y retención
- Customer Success: Soporte y satisfacción
- Data/Analytics: Business intelligence

🎯 TU EXPERTISE:
- Análisis de portfolio de iniciativas
- Identificación de gaps estratégicos
- Optimización de recursos entre equipos
- Balance growth vs operational excellence
- Impacto en experiencia de droguerías y sellers

💡 ESTILO:
- Profesional pero conversacional para equipos internos
- Insights accionables específicos para marketplace
- Considera impacto en ambos lados del marketplace
- Enfócate en métricas clave: GMV, Take Rate, Retention, NPS
- Siempre en español

🔍 AL ANALIZAR:
1. Balance entre growth vs operational initiatives
2. Distribución de recursos entre equipos
3. Gaps en customer experience (droguerías/sellers)
4. Oportunidades de automatización
5. Sinergias cross-team

Tu objetivo: Proporcionar insights estratégicos para optimizar el portfolio de iniciativas."""

        messages = [{"role": "system", "content": system_message}]
        
        if context:
            context_message = f"📋 DATOS ACTUALES DE SALUDIA:\n{context}\n\n💭 Proporciona análisis estratégico:"
            messages.append({"role": "user", "content": context_message})
        
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
            return {"success": True, "response": ai_response}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "response": "Error consultando el asistente AI."}
    
    except Exception as e:
        return {"success": False, "error": str(e), "response": "Error técnico del asistente AI."}

def analyze_initiatives_with_llm(initiatives):
    """Analizar iniciativas usando LLM con estadísticas"""
    if not initiatives:
        return "No hay iniciativas para analizar."
    
    # Calcular estadísticas
    stats = calculate_statistics(initiatives)
    
    # Preparar contexto detallado con estadísticas
    context = f"PORTFOLIO SALUDIA - ANÁLISIS ESTADÍSTICO:\n\n"
    context += f"📊 TOTAL: {stats['total_initiatives']} iniciativas\n\n"
    
    # Distribución por equipos con porcentajes
    context += "👥 DISTRIBUCIÓN POR EQUIPOS:\n"
    for team, count in stats['top_teams']:
        pct = stats['teams'][team]
        context += f"• {team}: {count} iniciativas ({pct:.1f}%)\n"
    
    # Top owners
    context += f"\n👤 TOP RESPONSABLES:\n"
    for owner, count in stats['top_owners']:
        pct = stats['owners'][owner]
        context += f"• {owner}: {count} iniciativas ({pct:.1f}%)\n"
    
    # Métricas promedio
    if stats['average_metrics']:
        context += f"\n📈 MÉTRICAS PROMEDIO:\n"
        metrics = stats['average_metrics']
        context += f"• Alcance: {metrics.get('reach', 0):.1f}%\n"
        context += f"• Impacto: {metrics.get('impact', 0):.1f}%\n"
        context += f"• Confianza: {metrics.get('confidence', 0):.1f}%\n"
        context += f"• Esfuerzo: {metrics.get('effort', 0):.1f}%\n"
    
    # Agregar detalles de iniciativas por equipo
    teams = {}
    for init in initiatives:
        team = init.get('team', 'Sin equipo')
        if team not in teams:
            teams[team] = []
        teams[team].append(init)
    
    context += f"\n📋 DETALLE POR EQUIPOS:\n"
    for team, team_initiatives in teams.items():
        context += f"\n{team.upper()} ({len(team_initiatives)} iniciativas):\n"
        for init in team_initiatives[:3]:  # Máximo 3 por equipo
            name = init.get('initiative_name', 'Sin nombre')
            kpi = init.get('main_kpi', 'Sin KPI')
            portal = init.get('portal', 'Sin portal')
            context += f"  • {name} (KPI: {kpi}, Portal: {portal})\n"
    
    prompt = """Analiza este portfolio de iniciativas de Saludia y proporciona insights estratégicos.

ANÁLISIS REQUERIDO:
1. 📊 Evaluación de la distribución actual de recursos
2. ⚖️ Balance entre growth initiatives vs operational excellence
3. 🔄 Oportunidades de sinergia cross-team específicas
4. ⚠️ Gaps críticos en experiencia de droguerías o sellers
5. 📈 Recomendaciones prioritarias para maximizar impacto del marketplace

Enfócate en insights accionables para líderes de equipos internos de Saludia."""
    
    result = query_llm(prompt, context)
    return result.get("response", "Error analizando iniciativas.")

def format_initiative_complete(initiative, index=None):
    """Formatear iniciativa con información COMPLETA para búsquedas"""
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
        
        # Formato COMPLETO para búsquedas
        formatted = f"""{prefix}🎯 **{name}**

📝 **Descripción:**
{description}

👤 **Responsable:** {owner}
👥 **Equipo:** {team}
📊 **KPI Principal:** {kpi}
🖥️ **Portal/Producto:** {portal}

📈 **Métricas de Iniciativa:**
• Alcance: {reach_pct}
• Impacto: {impact_pct}
• Confianza: {confidence_pct}
• Esfuerzo: {effort_pct}

━━━━━━━━━━━━━━━━━━━━━"""
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting initiative: {e}")
        return f"{index}. **{initiative.get('initiative_name', 'Error de formato')}**"

def format_initiative_summary(initiative, index=None):
    """Formatear iniciativa en modo resumen para listados"""
    try:
        name = initiative.get('initiative_name', 'Sin nombre')
        owner = initiative.get('owner', 'Sin owner')
        team = initiative.get('team', 'Sin equipo')
        kpi = initiative.get('main_kpi', 'Sin KPI')
        
        prefix = f"**{index}.** " if index else ""
        
        formatted = f"""{prefix}🎯 **{name}**
👤 {owner} | 👥 {team} | 📊 {kpi}"""
        
        return formatted
        
    except Exception as e:
        logger.error(f"Error formatting initiative summary: {e}")
        return f"{index}. **{initiative.get('initiative_name', 'Error')}**"

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
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=10)
        
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
        "version": "2.1.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "company": "Saludia Marketplace",
        "description": "Sistema de gestión de iniciativas con estadísticas avanzadas",
        "telegram_bot": {
            "enabled": bool(TELEGRAM_TOKEN),
            "webhook_configured": bot_configured,
            "webhook_url": f"{WEBHOOK_URL}/telegram-webhook" if TELEGRAM_TOKEN else None
        },
        "ai_assistant": {
            "enabled": bool(GROQ_API_KEY),
            "model": GROQ_MODEL,
            "provider": "Groq",
            "specialized_for": "Saludia marketplace analytics"
        },
        "features": [
            "detailed_search_with_descriptions",
            "advanced_statistics_with_percentages",
            "team_and_owner_analytics",
            "ai_strategic_analysis"
        ]
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

@app.route('/api/initiatives/statistics', methods=['GET'])
def api_statistics():
    """API para obtener estadísticas"""
    data = get_initiatives()
    
    if not data.get("success"):
        return jsonify({"error": "Could not fetch initiatives"}), 500
    
    stats = calculate_statistics(data.get("data", []))
    return jsonify(stats)

@app.route('/api/create', methods=['POST'])
def api_create():
    """API para crear iniciativa"""
    if not request.json:
        return jsonify({"error": "JSON required"}), 400
    
    result = create_initiative(request.json)
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
        stats = calculate_statistics(initiatives)
        
        return jsonify({
            "success": True,
            "initiatives_count": len(initiatives),
            "analysis": analysis,
            "statistics": stats,
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
        
        if 'message' in update_data:
            message = update_data['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            
            if 'text' in message:
                text = message['text'].strip().lower()  # Convertir a minúsculas
                
                # Comandos con y SIN barra diagonal (más user-friendly)
                if text in ['/start', 'start', 'inicio', 'hola', 'empezar']:
                    handle_start_command(chat_id)
                elif text in ['/help', 'help', 'ayuda', 'comandos']:
                    handle_help_command(chat_id)
                elif text in ['/iniciativas', 'iniciativas', 'lista', 'ver iniciativas', 'mostrar iniciativas']:
                    handle_list_initiatives(chat_id)
                elif text in ['/crear', 'crear', 'nueva iniciativa', 'crear iniciativa', 'agregar']:
                    handle_create_command(chat_id, user_id)
                elif text in ['/analizar', 'analizar', 'analyze', 'análisis', 'estadísticas', 'estadisticas']:
                    handle_analyze_command(chat_id)
                elif (text.startswith('/buscar ') or text.startswith('buscar ') or 
                      text.startswith('search ') or text.startswith('encontrar ')):
                    # Extraer término de búsqueda
                    if text.startswith('/'):
                        query = text.split(' ', 1)[1] if ' ' in text else ""
                    else:
                        query = text.split(' ', 1)[1] if ' ' in text else ""
                    
                    if query:
                        handle_search_command(chat_id, query)
                    else:
                        send_telegram_message(chat_id, "🔍 **¿Qué quieres buscar?**\n\nEjemplos:\n• `buscar Product`\n• `buscar API`\n• `buscar Juan`")
                elif text.startswith('/'):
                    # Comando con / no reconocido
                    send_telegram_message(chat_id, "❓ Comando no reconocido. Escribe `ayuda` para ver opciones disponibles.")
                else:
                    # Mensaje de texto normal
                    if user_id in user_states:
                        # Proceso de creación activo
                        handle_text_message(chat_id, user_id, message['text'])  # Usar texto original
                    else:
                        # Respuesta inteligente para texto libre
                        handle_natural_message(chat_id, text)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "ERROR", 500

def handle_natural_message(chat_id, text):
    """Manejar mensajes en lenguaje natural"""
    text_lower = text.lower()
    
    # Palabras clave para comandos
    if any(word in text_lower for word in ['iniciativa', 'proyecto', 'lista', 'ver', 'mostrar']):
        send_telegram_message(chat_id, "🎯 ¿Quieres ver las iniciativas?\n\nEscribe: `iniciativas`")
    elif any(word in text_lower for word in ['buscar', 'encontrar', 'busco', 'dónde']):
        send_telegram_message(chat_id, "🔍 ¿Qué quieres buscar?\n\nEjemplos:\n• `buscar Product`\n• `buscar API`\n• `buscar droguería`")
    elif any(word in text_lower for word in ['crear', 'nueva', 'agregar', 'añadir']):
        send_telegram_message(chat_id, "🆕 ¿Quieres crear una nueva iniciativa?\n\nEscribe: `crear`")
    elif any(word in text_lower for word in ['análisis', 'analizar', 'estadística', 'resumen']):
        send_telegram_message(chat_id, "📊 ¿Quieres ver el análisis del portfolio?\n\nEscribe: `analizar`")
    elif any(word in text_lower for word in ['ayuda', 'help', 'comando', 'opciones']):
        handle_help_command(chat_id)
    else:
        # Respuesta general amigable
        send_telegram_message(chat_id, """👋 **¡Hola!** No estoy seguro de qué necesitas.

**Opciones disponibles:**
• `iniciativas` - Ver todas las iniciativas
• `buscar <término>` - Buscar algo específico  
• `crear` - Nueva iniciativa
• `analizar` - Estadísticas y análisis
• `ayuda` - Ver todos los comandos

💡 **Tip:** No necesitas usar `/` - solo escribe la palabra.""")

def handle_start_command(chat_id):
    """Manejar comando /start"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot de Iniciativas Saludia**

¡Hola! Soy tu asistente de gestión de iniciativas para equipos internos de Saludia.

**🏢 Saludia:** Marketplace que conecta droguerías independientes con sellers y laboratorios.

**📋 Comandos principales:**
/iniciativas - Ver todas las iniciativas + estadísticas
/buscar <término> - Buscar iniciativas (info completa)
/crear - Crear nueva iniciativa
/analizar - Análisis AI del portfolio + métricas

**🔍 Ejemplos de búsqueda:**
• `/buscar Product` - Iniciativas del equipo Product
• `/buscar droguería` - Todo relacionado con droguerías
• `/buscar API`
