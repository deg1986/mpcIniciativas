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
• `iniciativas` - Ver todas las iniciativas + estadísticas
• `buscar <término>` - Buscar iniciativas (info completa)
• `crear` - Crear nueva iniciativa
• `analizar` - Análisis AI del portfolio + métricas

**🔍 Ejemplos de búsqueda:**
• `buscar Product` - Iniciativas del equipo Product
• `buscar droguería` - Todo relacionado con droguerías
• `buscar API` - Iniciativas de API

**💡 Tip:** No necesitas usar `/` - solo escribe la palabra.

**🆘 Ayuda:** Escribe `ayuda` para ver todos los comandos."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_help_command(chat_id):
    """Manejar comando /help"""
    logger.info(f"📱 /help from chat {chat_id}")
    
    text = """📚 **Comandos Disponibles**

**📋 Gestión de Iniciativas:**
• `iniciativas` o `/iniciativas` - Lista completa + estadísticas
• `buscar <término>` o `/buscar` - Búsqueda detallada
• `crear` o `/crear` - Nueva iniciativa (paso a paso)

**📊 Análisis y Reportes:**
• `analizar` o `/analizar` - Análisis AI + métricas del portfolio
• `estadísticas` - Resumen estadístico rápido

**🔍 Búsquedas Específicas:**
• `buscar Product` - Por equipo
• `buscar droguería` - Por término en descripción
• `buscar Juan` - Por responsable
• `buscar API` - Por tecnología/KPI

**💡 Características:**
✅ Búsqueda en nombre, descripción, owner, equipo, KPI
✅ Estadísticas detalladas con porcentajes
✅ Análisis estratégico con IA especializada en Saludia
✅ Información completa de cada iniciativa

**🤖 IA Especializada:**
Nuestro asistente conoce el contexto de Saludia como marketplace farmacéutico y proporciona insights estratégicos específicos para equipos internos.

**📞 Soporte:** Para más ayuda, contacta al equipo de Product."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_list_initiatives(chat_id):
    """Manejar comando para listar iniciativas"""
    logger.info(f"📱 List initiatives from chat {chat_id}")
    
    # Obtener iniciativas
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error obteniendo iniciativas: {data.get('error', 'Error desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas registradas.")
        return
    
    # Calcular estadísticas
    stats = calculate_statistics(initiatives)
    
    # Enviar estadísticas primero
    stats_text = format_statistics_text(stats)
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Enviar lista resumida
    text = f"📋 **LISTA DE INICIATIVAS** (Resumen)\n\n"
    
    # Agrupar por equipos para mejor organización
    teams = {}
    for init in initiatives:
        team = init.get('team', 'Sin equipo')
        if team not in teams:
            teams[team] = []
        teams[team].append(init)
    
    counter = 1
    for team, team_initiatives in teams.items():
        text += f"👥 **{team.upper()}:**\n"
        for init in team_initiatives:
            formatted = format_initiative_summary(init, counter)
            text += f"{formatted}\n\n"
            counter += 1
    
    text += f"💡 **Tip:** Usa `buscar <término>` para información completa de iniciativas específicas."
    
    # Enviar en chunks si es muy largo
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            send_telegram_message(chat_id, chunk, parse_mode='Markdown')
    else:
        send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_search_command(chat_id, query):
    """Manejar comando de búsqueda"""
    logger.info(f"📱 Search '{query}' from chat {chat_id}")
    
    result = search_initiatives(query)
    
    if not result.get("success"):
        send_telegram_message(chat_id, f"❌ Error en búsqueda: {result.get('error', 'Error desconocido')}")
        return
    
    results = result.get("results", [])
    total = result.get("total", 0)
    
    if not results:
        # Sugerir búsquedas alternativas
        suggestions_text = f"""🔍 **Sin resultados para:** "{query}"

**💡 Sugerencias:**
• Verifica la ortografía
• Usa términos más generales
• Prueba buscar por:
  - Equipo: `buscar Product`
  - Owner: `buscar Juan`
  - Tecnología: `buscar API`
  - Portal: `buscar droguería`

**📋 ¿Prefieres ver todas las iniciativas?**
Escribe: `iniciativas`"""
        
        send_telegram_message(chat_id, suggestions_text, parse_mode='Markdown')
        return
    
    # Enviar resultados con información COMPLETA
    text = f"🔍 **RESULTADOS DE BÚSQUEDA**\n"
    text += f"**Término:** {query}\n"
    text += f"**Encontrados:** {total} iniciativa(s)\n\n"
    
    # Mostrar hasta 5 resultados completos
    for i, init in enumerate(results[:5], 1):
        formatted = format_initiative_complete(init, i)
        text += f"{formatted}\n\n"
    
    if total > 5:
        text += f"📝 **Nota:** Se muestran las primeras 5 de {total} iniciativas encontradas.\n"
        text += f"Refina tu búsqueda para resultados más específicos."
    
    # Enviar en chunks si es muy largo
    if len(text) > 4000:
        chunks = [text[i:i+4000] for i in range(0, len(text), 4000)]
        for chunk in chunks:
            send_telegram_message(chat_id, chunk, parse_mode='Markdown')
    else:
        send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_analyze_command(chat_id):
    """Manejar comando de análisis"""
    logger.info(f"📱 Analyze command from chat {chat_id}")
    
    send_telegram_message(chat_id, "🤖 **Analizando portfolio de iniciativas...**\n\nEsto puede tomar unos segundos.", parse_mode='Markdown')
    
    # Obtener iniciativas
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error obteniendo datos: {data.get('error', 'Error desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas para analizar.")
        return
    
    # Enviar estadísticas primero
    stats = calculate_statistics(initiatives)
    stats_text = format_statistics_text(stats)
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Análisis con IA
    if GROQ_API_KEY:
        analysis = analyze_initiatives_with_llm(initiatives)
        
        analysis_text = f"🤖 **ANÁLISIS ESTRATÉGICO CON IA**\n\n{analysis}"
        
        # Enviar en chunks si es muy largo
        if len(analysis_text) > 4000:
            chunks = [analysis_text[i:i+4000] for i in range(0, len(analysis_text), 4000)]
            for chunk in chunks:
                send_telegram_message(chat_id, chunk, parse_mode='Markdown')
        else:
            send_telegram_message(chat_id, analysis_text, parse_mode='Markdown')
    else:
        send_telegram_message(chat_id, "⚠️ Análisis con IA no disponible. Configuración pendiente.", parse_mode='Markdown')

def handle_create_command(chat_id, user_id):
    """Iniciar proceso de creación de iniciativa"""
    logger.info(f"📱 Create command from chat {chat_id}, user {user_id}")
    
    # Inicializar estado del usuario
    user_states[user_id] = {
        'step': 'name',
        'data': {},
        'chat_id': chat_id
    }
    
    text = """🆕 **CREAR NUEVA INICIATIVA**

📝 **Paso 1/6:** Nombre de la iniciativa

Por favor, envía el nombre de la nueva iniciativa.

**Ejemplos:**
• "Integración API de pagos"
• "Optimización del checkout"
• "Dashboard analytics v2"

💡 **Tip:** Usa un nombre descriptivo y específico."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de texto durante el proceso de creación"""
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    step = state['step']
    
    try:
        if step == 'name':
            state['data']['initiative_name'] = text
            state['step'] = 'description'
            send_telegram_message(chat_id, """📝 **Paso 2/6:** Descripción

Describe qué hace esta iniciativa y cuál es su objetivo.

**Ejemplo:**
"Implementar sistema de pagos con PSE y tarjetas para mejorar conversión en el checkout de droguerías."

💡 **Tip:** Incluye el problema que resuelve y el beneficio esperado.""", parse_mode='Markdown')
        
        elif step == 'description':
            state['data']['description'] = text
            state['step'] = 'owner'
            send_telegram_message(chat_id, """👤 **Paso 3/6:** Responsable

¿Quién es el owner/responsable principal de esta iniciativa?

**Ejemplo:**
• "Juan Pérez"
• "María García"
• "Carlos Rodriguez"

💡 **Tip:** Nombre completo de la persona responsable.""", parse_mode='Markdown')
        
        elif step == 'owner':
            state['data']['owner'] = text
            state['step'] = 'team'
            send_telegram_message(chat_id, """👥 **Paso 4/6:** Equipo

¿A qué equipo pertenece esta iniciativa?

**Opciones comunes:**
• Product
• Engineering
• Operations
• Sales
• Marketing
• Customer Success
• Data/Analytics

💡 **Tip:** Usa el nombre oficial del equipo.""", parse_mode='Markdown')
        
        elif step == 'team':
            state['data']['team'] = text
            state['step'] = 'kpi'
            send_telegram_message(chat_id, """📊 **Paso 5/6:** KPI Principal

¿Cuál es el KPI o métrica principal que impacta esta iniciativa?

**Ejemplos:**
• "Conversion Rate"
• "GMV"
• "User Retention"
• "API Response Time"
• "Customer Satisfaction"
• "Monthly Active Users"

💡 **Tip:** El KPI más importante que mide el éxito.""", parse_mode='Markdown')
        
        elif step == 'kpi':
            state['data']['main_kpi'] = text
            state['step'] = 'portal'
            send_telegram_message(chat_id, """🖥️ **Paso 6/6:** Portal/Producto

¿En qué portal o producto se implementa?

**Opciones comunes:**
• "Portal Droguería"
• "Portal Seller"
• "Admin Dashboard"
• "Mobile App"
• "API/Backend"
• "Interno"

💡 **Tip:** Dónde verán/usarán los usuarios esta iniciativa.""", parse_mode='Markdown')
        
        elif step == 'portal':
            state['data']['portal'] = text
            
            # Crear la iniciativa
            create_result = create_initiative(state['data'])
            
            if create_result.get('success'):
                # Formatear confirmación
                data = state['data']
                confirmation = f"""✅ **INICIATIVA CREADA EXITOSAMENTE**

🎯 **{data['initiative_name']}**

📝 **Descripción:** {data['description']}
👤 **Responsable:** {data['owner']}
👥 **Equipo:** {data['team']}
📊 **KPI Principal:** {data['main_kpi']}
🖥️ **Portal:** {data['portal']}

🔗 La iniciativa ha sido agregada a la base de datos.

💡 **Próximos pasos:**
• Puedes buscarla con: `buscar {data['initiative_name']}`
• Ver todas: `iniciativas`
• Crear otra: `crear`"""
                
                send_telegram_message(chat_id, confirmation, parse_mode='Markdown')
            else:
                send_telegram_message(chat_id, f"❌ Error creando iniciativa: {create_result.get('error', 'Error desconocido')}\n\n💡 Prueba nuevamente con: `crear`", parse_mode='Markdown')
            
            # Limpiar estado
            del user_states[user_id]
    
    except Exception as e:
        logger.error(f"Error in text message handling: {e}")
        send_telegram_message(chat_id, "❌ Error procesando tu mensaje. Inténtalo nuevamente.", parse_mode='Markdown')
        if user_id in user_states:
            del user_states[user_id]

# ===== MAIN =====

if __name__ == '__main__':
    # Configurar webhook al iniciar
    if TELEGRAM_TOKEN:
        bot_configured = setup_webhook()
        logger.info(f"🤖 Bot webhook configured: {bot_configured}")
    
    # Ejecutar Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
