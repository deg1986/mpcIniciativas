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

def validate_initiative_data(data):
    """Validar datos de iniciativa según esquema de DB"""
    errors = []
    
    # Campos requeridos
    required_fields = ['initiative_name', 'description', 'portal', 'owner', 'team', 'reach', 'impact', 'confidence']
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Campo '{field}' es requerido")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    # Validar longitudes
    if len(data['initiative_name']) > 255:
        errors.append("Nombre de iniciativa debe tener máximo 255 caracteres")
    
    if len(data['description']) > 1000:
        errors.append("Descripción debe tener máximo 1000 caracteres")
    
    if data.get('main_kpi') and len(data['main_kpi']) > 255:
        errors.append("KPI principal debe tener máximo 255 caracteres")
    
    if len(data['owner']) > 100:
        errors.append("Owner debe tener máximo 100 caracteres")
    
    # Validar enums
    valid_portals = ['Seller', 'Droguista', 'Admin']
    if data['portal'] not in valid_portals:
        errors.append(f"Portal debe ser uno de: {', '.join(valid_portals)}")
    
    valid_teams = ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth']
    if data['team'] not in valid_teams:
        errors.append(f"Equipo debe ser uno de: {', '.join(valid_teams)}")
    
    # Validar reach (0-1)
    try:
        reach = float(data['reach'])
        if reach < 0 or reach > 1:
            errors.append("Reach debe estar entre 0 y 1")
        data['reach'] = reach
    except (ValueError, TypeError):
        errors.append("Reach debe ser un número entre 0 y 1")
    
    # Validar impact (1, 2, 3)
    try:
        impact = int(data['impact'])
        if impact not in [1, 2, 3]:
            errors.append("Impact debe ser 1, 2 o 3")
        data['impact'] = impact
    except (ValueError, TypeError):
        errors.append("Impact debe ser 1, 2 o 3")
    
    # Validar confidence (0-1)
    try:
        confidence = float(data['confidence'])
        if confidence < 0 or confidence > 1:
            errors.append("Confidence debe estar entre 0 y 1")
        data['confidence'] = confidence
    except (ValueError, TypeError):
        errors.append("Confidence debe ser un número entre 0 y 1")
    
    # Validar effort (opcional, default 1)
    if 'effort' in data:
        try:
            effort = float(data['effort'])
            if effort <= 0:
                errors.append("Effort debe ser mayor a 0")
            data['effort'] = effort
        except (ValueError, TypeError):
            errors.append("Effort debe ser un número mayor a 0")
    else:
        data['effort'] = 1.0  # Default value
    
    # Validar must_have (opcional, default False)
    if 'must_have' in data:
        if isinstance(data['must_have'], str):
            data['must_have'] = data['must_have'].lower() in ['true', '1', 'yes', 'sí']
        else:
            data['must_have'] = bool(data['must_have'])
    else:
        data['must_have'] = False
    
    return {"valid": len(errors) == 0, "errors": errors, "data": data}

def create_initiative(data):
    """Crear iniciativa en NocoDB con validaciones"""
    try:
        # Validar datos
        validation_result = validate_initiative_data(data)
        
        if not validation_result["valid"]:
            return {
                "success": False, 
                "error": "Datos inválidos", 
                "validation_errors": validation_result["errors"]
            }
        
        validated_data = validation_result["data"]
        
        # Preparar datos para NocoDB (solo campos permitidos)
        nocodb_data = {
            "initiative_name": validated_data["initiative_name"],
            "description": validated_data["description"],
            "portal": validated_data["portal"],
            "owner": validated_data["owner"],
            "team": validated_data["team"],
            "reach": validated_data["reach"],
            "impact": validated_data["impact"],
            "confidence": validated_data["confidence"],
            "effort": validated_data["effort"],
            "must_have": validated_data["must_have"]
        }
        
        # Agregar main_kpi solo si está presente
        if validated_data.get("main_kpi"):
            nocodb_data["main_kpi"] = validated_data["main_kpi"]
        
        # Hacer petición a NocoDB
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=nocodb_data, timeout=20)
        
        if response.status_code in [200, 201]:
            logger.info(f"✅ Created initiative: {validated_data.get('initiative_name', 'Unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Create failed HTTP {response.status_code}: {response.text}")
            return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
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
            'impact': (total_impact / metric_count),
            'confidence': (total_confidence / metric_count) * 100,
            'effort': (total_effort / metric_count)
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
        text += f"• Impacto: {metrics.get('impact', 0):.1f}/3\n"
        text += f"• Confianza: {metrics.get('confidence', 0):.1f}%\n"
        text += f"• Esfuerzo: {metrics.get('effort', 0):.1f} sprints\n"
    
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
- Sales: Acquisition de droguerías y sellers
- Ops: Gestión operacional y fulfillment
- CS: Customer Success y soporte
- Controlling: Control financiero y métricas
- Growth: Marketing y crecimiento

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
        context += f"• Impacto: {metrics.get('impact', 0):.1f}/3\n"
        context += f"• Confianza: {metrics.get('confidence', 0):.1f}%\n"
        context += f"• Esfuerzo: {metrics.get('effort', 0):.1f} sprints\n"
    
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
        status = initiative.get('status', 'Pending')
        
        # Métricas con validación
        reach = initiative.get('reach', 0)
        impact = initiative.get('impact', 0)
        confidence = initiative.get('confidence', 0)
        effort = initiative.get('effort', 1)
        score = initiative.get('score', 0)
        
        # Convertir a números si es posible
        try:
            reach = float(reach) if reach else 0
            impact = float(impact) if impact else 0
            confidence = float(confidence) if confidence else 0
            effort = float(effort) if effort else 1
            score = float(score) if score else 0
        except:
            reach = impact = confidence = effort = score = 0
        
        # Formatear métricas
        reach_pct = f"{reach*100:.0f}%" if reach > 0 else "N/A"
        impact_val = f"{impact:.0f}/3" if impact > 0 else "N/A"
        confidence_pct = f"{confidence*100:.0f}%" if confidence > 0 else "N/A"
        effort_val = f"{effort:.1f} sprints" if effort > 0 else "N/A"
        score_val = f"{score:.2f}" if score > 0 else "N/A"
        
        prefix = f"**{index}.** " if index else ""
        
        # Formato COMPLETO para búsquedas
        formatted = f"""{prefix}🎯 **{name}**

📝 **Descripción:**
{description}

👤 **Responsable:** {owner}
👥 **Equipo:** {team}
📊 **KPI Principal:** {kpi}
🖥️ **Portal:** {portal}
📋 **Status:** {status}

📈 **Métricas RICE:**
• Alcance: {reach_pct}
• Impacto: {impact_val}
• Confianza: {confidence_pct}
• Esfuerzo: {effort_val}
• **Score:** {score_val}

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
        status = initiative.get('status', 'Pending')
        
        prefix = f"**{index}.** " if index else ""
        
        formatted = f"""{prefix}🎯 **{name}**
👤 {owner} | 👥 {team} | 📊 {kpi} | 📋 {status}"""
        
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
        "version": "2.2.0",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "company": "Saludia Marketplace",
        "description": "Sistema de gestión de iniciativas con validaciones y estadísticas avanzadas",
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
            "ai_strategic_analysis",
            "complete_data_validation",
            "rice_scoring_system"
        ],
        "database_schema": {
            "required_fields": ["initiative_name", "description", "portal", "owner", "team", "reach", "impact", "confidence"],
            "valid_portals": ["Seller", "Droguista", "Admin"],
            "valid_teams": ["Product", "Sales", "Ops", "CS", "Controlling", "Growth"],
            "auto_fields": ["id", "score", "status", "created_at", "updated_at"]
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
• `crear` - Crear nueva iniciativa con validaciones
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
• `iniciativas` - Lista completa + estadísticas
• `buscar <término>` - Búsqueda detallada
• `crear` - Nueva iniciativa (8 pasos con validaciones)

**📊 Análisis y Reportes:**
• `analizar` - Análisis AI + métricas del portfolio
• `estadísticas` - Resumen estadístico rápido

**🔍 Búsquedas Específicas:**
• `buscar Product` - Por equipo
• `buscar droguería` - Por término en descripción
• `buscar Juan` - Por responsable
• `buscar API` - Por tecnología/KPI

**💡 Características Nuevas:**
✅ Validaciones completas según DB schema
✅ Métricas RICE (Reach, Impact, Confidence, Effort)
✅ Score automático calculado
✅ Equipos: Product, Sales, Ops, CS, Controlling, Growth
✅ Portales: Seller, Droguista, Admin

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
    """Iniciar proceso de creación de iniciativa con validaciones"""
    logger.info(f"📱 Create command from chat {chat_id}, user {user_id}")
    
    # Inicializar estado del usuario
    user_states[user_id] = {
        'step': 'name',
        'data': {},
        'chat_id': chat_id
    }
    
    text = """🆕 **CREAR NUEVA INICIATIVA**

📝 **Paso 1/8:** Nombre de la iniciativa

Por favor, envía el nombre de la nueva iniciativa (máximo 255 caracteres).

**Ejemplos:**
• "Integración API de pagos"
• "Optimización del checkout"
• "Dashboard analytics v2"

💡 **Tip:** Usa un nombre descriptivo y específico."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de texto durante el proceso de creación con validaciones"""
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    step = state['step']
    
    try:
        if step == 'name':
            if len(text) > 255:
                send_telegram_message(chat_id, "❌ El nombre debe tener máximo 255 caracteres. Intenta con un nombre más corto.")
                return
            
            state['data']['initiative_name'] = text.strip()
            state['step'] = 'description'
            send_telegram_message(chat_id, """📝 **Paso 2/8:** Descripción

Describe qué hace esta iniciativa y cuál es su objetivo (máximo 1000 caracteres).

**Ejemplo:**
"Implementar sistema de pagos con PSE y tarjetas para mejorar conversión en el checkout de droguerías."

💡 **Tip:** Incluye el problema que resuelve y el beneficio esperado.""", parse_mode='Markdown')
        
        elif step == 'description':
            if len(text) > 1000:
                send_telegram_message(chat_id, "❌ La descripción debe tener máximo 1000 caracteres. Intenta con una descripción más corta.")
                return
                
            state['data']['description'] = text.strip()
            state['step'] = 'owner'
            send_telegram_message(chat_id, """👤 **Paso 3/8:** Responsable

¿Quién es el owner/responsable principal de esta iniciativa? (máximo 100 caracteres)

**Ejemplo:**
• "Juan Pérez"
• "María García"
• "Carlos Rodriguez"

💡 **Tip:** Nombre completo de la persona responsable.""", parse_mode='Markdown')
        
        elif step == 'owner':
            if len(text) > 100:
                send_telegram_message(chat_id, "❌ El owner debe tener máximo 100 caracteres.")
                return
                
            state['data']['owner'] = text.strip()
            state['step'] = 'team'
            send_telegram_message(chat_id, """👥 **Paso 4/8:** Equipo

¿A qué equipo pertenece esta iniciativa?

**Opciones válidas:**
• `Product`
• `Sales`
• `Ops`
• `CS`
• `Controlling`
• `Growth`

💡 **Tip:** Escribe exactamente uno de los nombres de arriba.""", parse_mode='Markdown')
        
        elif step == 'team':
            valid_teams = ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth']
            team_input = text.strip()
            
            # Buscar coincidencia case-insensitive
            matched_team = None
            for team in valid_teams:
                if team.lower() == team_input.lower():
                    matched_team = team
                    break
            
            if not matched_team:
                teams_list = "• " + "\n• ".join(valid_teams)
                send_telegram_message(chat_id, f"❌ Equipo inválido. Debe ser uno de:\n\n{teams_list}")
                return
            
            state['data']['team'] = matched_team
            state['step'] = 'portal'
            send_telegram_message(chat_id, """🖥️ **Paso 5/8:** Portal/Producto

¿En qué portal se implementa esta iniciativa?

**Opciones válidas:**
• `Seller` - Portal de vendedores/laboratorios
• `Droguista` - Portal de droguerías
• `Admin` - Panel administrativo interno

💡 **Tip:** Escribe exactamente una de las opciones de arriba.""", parse_mode='Markdown')
        
        elif step == 'portal':
            valid_portals = ['Seller', 'Droguista', 'Admin']
            portal_input = text.strip()
            
            # Buscar coincidencia case-insensitive
            matched_portal = None
            for portal in valid_portals:
                if portal.lower() == portal_input.lower():
                    matched_portal = portal
                    break
            
            if not matched_portal:
                portals_list = "• " + "\n• ".join(valid_portals)
                send_telegram_message(chat_id, f"❌ Portal inválido. Debe ser uno de:\n\n{portals_list}")
                return
            
            state['data']['portal'] = matched_portal
            state['step'] = 'kpi'
            send_telegram_message(chat_id, """📊 **Paso 6/8:** KPI Principal (Opcional)

¿Cuál es el KPI o métrica principal que impacta esta iniciativa?

**Ejemplos:**
• "Conversion Rate"
• "GMV"
• "User Retention"
• "API Response Time"
• "Customer Satisfaction"

💡 **Tip:** Deja en blanco si no tienes un KPI específico (envía: `ninguno`)""", parse_mode='Markdown')
        
        elif step == 'kpi':
            kpi_input = text.strip()
            if kpi_input.lower() not in ['ninguno', 'no', 'n/a', '']:
                if len(kpi_input) > 255:
                    send_telegram_message(chat_id, "❌ El KPI debe tener máximo 255 caracteres.")
                    return
                state['data']['main_kpi'] = kpi_input
            
            state['step'] = 'reach'
            send_telegram_message(chat_id, """📈 **Paso 7/8:** Métricas RICE

Ahora configuremos las métricas RICE para priorización:

**REACH (Alcance):** ¿Qué % de usuarios impacta?
Envía un número entre 0 y 100.

**Ejemplos:**
• `85` - 85% de usuarios
• `25` - 25% de usuarios
• `100` - Todos los usuarios

💡 **Tip:** Solo el número, sin el símbolo %""", parse_mode='Markdown')
        
        elif step == 'reach':
            try:
                reach_input = float(text.strip())
                if reach_input < 0 or reach_input > 100:
                    send_telegram_message(chat_id, "❌ El reach debe estar entre 0 y 100.")
                    return
                
                # Convertir a decimal (0-1)
                state['data']['reach'] = reach_input / 100
                state['step'] = 'impact'
                send_telegram_message(chat_id, """💥 **IMPACT (Impacto):** ¿Qué tanto impacto tiene en el KPI?

**Opciones:**
• `1` - Impacto bajo
• `2` - Impacto medio  
• `3` - Impacto alto

💡 **Tip:** Solo envía el número (1, 2 o 3)""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Por favor envía un número válido entre 0 y 100.")
                return
        
        elif step == 'impact':
            try:
                impact_input = int(text.strip())
                if impact_input not in [1, 2, 3]:
                    send_telegram_message(chat_id, "❌ El impact debe ser 1, 2 o 3.")
                    return
                
                state['data']['impact'] = impact_input
                state['step'] = 'confidence'
                send_telegram_message(chat_id, """🎯 **CONFIDENCE (Confianza):** ¿Qué % de confianza tienes en el impacto?

Envía un número entre 0 y 100.

**Ejemplos:**
• `90` - 90% de confianza
• `70` - 70% de confianza
• `50` - 50% de confianza

💡 **Tip:** Solo el número, sin el símbolo %""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Por favor envía un número válido: 1, 2 o 3.")
                return
        
        elif step == 'confidence':
            try:
                confidence_input = float(text.strip())
                if confidence_input < 0 or confidence_input > 100:
                    send_telegram_message(chat_id, "❌ La confidence debe estar entre 0 y 100.")
                    return
                
                # Convertir a decimal (0-1)
                state['data']['confidence'] = confidence_input / 100
                state['step'] = 'effort'
                send_telegram_message(chat_id, """⚡ **EFFORT (Esfuerzo):** ¿Cuántos sprints/semanas de desarrollo?

Envía un número decimal.

**Ejemplos:**
• `1` - 1 sprint
• `2.5` - 2.5 sprints
• `0.5` - Medio sprint

💡 **Tip:** Deja en blanco para usar valor por defecto (1 sprint). Envía: `default`""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Por favor envía un número válido entre 0 y 100.")
                return
        
        elif step == 'effort':
            effort_input = text.strip().lower()
            
            if effort_input in ['default', 'defecto', '']:
                state['data']['effort'] = 1.0
            else:
                try:
                    effort_value = float(effort_input)
                    if effort_value <= 0:
                        send_telegram_message(chat_id, "❌ El effort debe ser mayor a 0.")
                        return
                    state['data']['effort'] = effort_value
                except ValueError:
                    send_telegram_message(chat_id, "❌ Por favor envía un número válido mayor a 0, o 'default'.")
                    return
            
            # Crear la iniciativa
            create_result = create_initiative(state['data'])
            
            if create_result.get('success'):
                # Calcular score para mostrar
                data = state['data']
                score = (data['reach'] * data['impact'] * data['confidence']) / data['effort']
                
                confirmation = f"""✅ **INICIATIVA CREADA EXITOSAMENTE**

🎯 **{data['initiative_name']}**

📝 **Descripción:** {data['description']}
👤 **Responsable:** {data['owner']}
👥 **Equipo:** {data['team']}
🖥️ **Portal:** {data['portal']}
📊 **KPI Principal:** {data.get('main_kpi', 'No especificado')}

📈 **Métricas RICE:**
• **Reach:** {data['reach']*100:.0f}% de usuarios
• **Impact:** {data['impact']}/3
• **Confidence:** {data['confidence']*100:.0f}%
• **Effort:** {data['effort']} sprints
• **Score:** {score:.2f}

🔗 La iniciativa ha sido agregada con status "Pending".

💡 **Próximos pasos:**
• Buscar: `buscar {data['initiative_name']}`
• Ver todas: `iniciativas`
• Crear otra: `crear`"""
                
                send_telegram_message(chat_id, confirmation, parse_mode='Markdown')
            else:
                error_msg = f"❌ Error creando iniciativa: {create_result.get('error', 'Error desconocido')}"
                
                if 'validation_errors' in create_result:
                    error_msg += "\n\n**Errores de validación:**\n"
                    for error in create_result['validation_errors']:
                        error_msg += f"• {error}\n"
                
                error_msg += "\n💡 Prueba nuevamente con: `crear`"
                send_telegram_message(chat_id, error_msg, parse_mode='Markdown')
            
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
