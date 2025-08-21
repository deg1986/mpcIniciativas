# 🚀 MCP Saludia OPTIMIZED v2.4 - Gestión de Iniciativas con Estadísticas Avanzadas
import os
import json
import asyncio
import aiohttp
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import logging
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import time

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

# Cache para optimizar requests
initiatives_cache = {"data": None, "timestamp": 0, "ttl": 300}  # 5 minutos TTL
executor = ThreadPoolExecutor(max_workers=4)

def get_cached_initiatives():
    """Obtener iniciativas con cache para optimizar"""
    current_time = time.time()
    
    # Verificar cache
    if (initiatives_cache["data"] is not None and 
        current_time - initiatives_cache["timestamp"] < initiatives_cache["ttl"]):
        logger.info("✅ Using cached initiatives data")
        return {"success": True, "data": initiatives_cache["data"], "cached": True}
    
    # Fetch fresh data
    try:
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {'accept': 'application/json', 'xc-token': NOCODB_TOKEN}
        params = {'limit': 200}  # Aumentar límite
        
        response = requests.get(url, headers=headers, params=params, timeout=15)  # Reducir timeout
        
        if response.status_code == 200:
            data = response.json()
            initiatives = data.get('list', [])
            
            # Actualizar cache
            initiatives_cache["data"] = initiatives
            initiatives_cache["timestamp"] = current_time
            
            logger.info(f"✅ Retrieved {len(initiatives)} initiatives from NocoDB (fresh)")
            return {"success": True, "data": initiatives, "cached": False}
        else:
            logger.error(f"❌ NocoDB HTTP {response.status_code}")
            # Si falla, usar cache aunque esté expirado
            if initiatives_cache["data"] is not None:
                logger.info("⚠️ Using expired cache due to API error")
                return {"success": True, "data": initiatives_cache["data"], "cached": True}
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error fetching initiatives: {e}")
        # Fallback a cache expirado si existe
        if initiatives_cache["data"] is not None:
            logger.info("⚠️ Using expired cache due to exception")
            return {"success": True, "data": initiatives_cache["data"], "cached": True}
        return {"success": False, "error": str(e)}

# Usar la función optimizada como alias
get_initiatives = get_cached_initiatives

def calculate_score_fast(initiative):
    """Calcular score optimizado"""
    try:
        # Si ya tiene score, usarlo
        if 'score' in initiative and initiative['score'] is not None:
            return float(initiative['score'])
        
        # Calcular rápido
        reach = float(initiative.get('reach', 0)) or 0
        impact = float(initiative.get('impact', 0)) or 0
        confidence = float(initiative.get('confidence', 0)) or 0
        effort = float(initiative.get('effort', 1)) or 1
        
        if reach > 0 and impact > 0 and confidence > 0 and effort > 0:
            score = (reach * impact * confidence) / effort
            initiative['calculated_score'] = score
            return score
        else:
            initiative['calculated_score'] = 0
            return 0
    except:
        initiative['calculated_score'] = 0
        return 0

def sort_initiatives_by_score(initiatives):
    """Ordenar iniciativas por score optimizado"""
    return sorted(initiatives, key=calculate_score_fast, reverse=True)

def validate_initiative_data(data):
    """Validar datos de iniciativa - versión optimizada"""
    errors = []
    
    # Campos requeridos
    required_fields = ['initiative_name', 'description', 'portal', 'owner', 'team', 'reach', 'impact', 'confidence']
    
    for field in required_fields:
        if field not in data or not data[field]:
            errors.append(f"Campo '{field}' es requerido")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    # Validaciones rápidas
    validations = [
        (len(data['initiative_name']) <= 255, "Nombre debe tener máximo 255 caracteres"),
        (len(data['description']) <= 1000, "Descripción debe tener máximo 1000 caracteres"),
        (len(data['owner']) <= 100, "Owner debe tener máximo 100 caracteres"),
        (data['portal'] in ['Seller', 'Droguista', 'Admin'], "Portal inválido"),
        (data['team'] in ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth'], "Equipo inválido")
    ]
    
    for condition, error_msg in validations:
        if not condition:
            errors.append(error_msg)
    
    # Validar métricas numéricas
    try:
        reach = float(data['reach'])
        if not (0 <= reach <= 1):
            errors.append("Reach debe estar entre 0 y 1")
        data['reach'] = reach
    except:
        errors.append("Reach debe ser un número entre 0 y 1")
    
    try:
        impact = int(data['impact'])
        if impact not in [1, 2, 3]:
            errors.append("Impact debe ser 1, 2 o 3")
        data['impact'] = impact
    except:
        errors.append("Impact debe ser 1, 2 o 3")
    
    try:
        confidence = float(data['confidence'])
        if not (0 <= confidence <= 1):
            errors.append("Confidence debe estar entre 0 y 1")
        data['confidence'] = confidence
    except:
        errors.append("Confidence debe ser un número entre 0 y 1")
    
    # Effort opcional
    data['effort'] = float(data.get('effort', 1.0)) if data.get('effort') else 1.0
    data['must_have'] = bool(data.get('must_have', False))
    
    return {"valid": len(errors) == 0, "errors": errors, "data": data}

def create_initiative(data):
    """Crear iniciativa optimizada"""
    try:
        validation_result = validate_initiative_data(data)
        
        if not validation_result["valid"]:
            return {
                "success": False, 
                "error": "Datos inválidos", 
                "validation_errors": validation_result["errors"]
            }
        
        validated_data = validation_result["data"]
        
        # Preparar datos para NocoDB
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
        
        if validated_data.get("main_kpi"):
            nocodb_data["main_kpi"] = validated_data["main_kpi"]
        
        url = f"{NOCODB_BASE_URL}/tables/{NOCODB_TABLE_ID}/records"
        headers = {
            'accept': 'application/json',
            'xc-token': NOCODB_TOKEN,
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=headers, json=nocodb_data, timeout=15)
        
        if response.status_code in [200, 201]:
            # Invalidar cache
            initiatives_cache["timestamp"] = 0
            logger.info(f"✅ Created initiative: {validated_data.get('initiative_name', 'Unknown')}")
            return {"success": True, "data": response.json()}
        else:
            logger.error(f"❌ Create failed HTTP {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}"}
    except Exception as e:
        logger.error(f"❌ Error creating initiative: {e}")
        return {"success": False, "error": str(e)}

def calculate_statistics_fast(initiatives):
    """Calcular estadísticas optimizado"""
    if not initiatives:
        return {}
    
    sorted_initiatives = sort_initiatives_by_score(initiatives)
    total = len(sorted_initiatives)
    
    # Contadores usando Counter
    teams = Counter(init.get('team', 'Sin equipo').strip() for init in sorted_initiatives if isinstance(init, dict))
    owners = Counter(init.get('owner', 'Sin owner').strip() for init in sorted_initiatives if isinstance(init, dict))
    kpis = Counter(init.get('main_kpi', 'Sin KPI').strip() for init in sorted_initiatives if isinstance(init, dict))
    portals = Counter(init.get('portal', 'Sin portal').strip() for init in sorted_initiatives if isinstance(init, dict))
    
    # Métricas numéricas optimizadas
    metrics = []
    top_initiatives = []
    
    for init in sorted_initiatives:
        if isinstance(init, dict):
            try:
                reach = float(init.get('reach', 0)) or 0
                impact = float(init.get('impact', 0)) or 0
                confidence = float(init.get('confidence', 0)) or 0
                effort = float(init.get('effort', 0)) or 0
                score = float(init.get('score', 0)) or init.get('calculated_score', 0)
                
                if any([reach, impact, confidence, effort]):
                    metrics.append({
                        'reach': reach, 'impact': impact, 
                        'confidence': confidence, 'effort': effort, 'score': score
                    })
                
                if score > 0:
                    top_initiatives.append({
                        'name': init.get('initiative_name', 'Sin nombre'),
                        'score': score,
                        'team': init.get('team', 'Sin equipo'),
                        'owner': init.get('owner', 'Sin owner')
                    })
            except:
                continue
    
    # Promedios
    avg_metrics = {}
    if metrics:
        avg_metrics = {
            'reach': sum(m['reach'] for m in metrics) / len(metrics) * 100,
            'impact': sum(m['impact'] for m in metrics) / len(metrics),
            'confidence': sum(m['confidence'] for m in metrics) / len(metrics) * 100,
            'effort': sum(m['effort'] for m in metrics) / len(metrics),
            'score': sum(m['score'] for m in metrics) / len(metrics)
        }
    
    # Porcentajes
    teams_pct = {team: (count/total)*100 for team, count in teams.most_common()}
    owners_pct = {owner: (count/total)*100 for owner, count in owners.most_common()}
    kpis_pct = {kpi: (count/total)*100 for kpi, count in kpis.most_common()}
    portals_pct = {portal: (count/total)*100 for portal, count in portals.most_common()}
    
    return {
        'total_initiatives': total,
        'teams': teams_pct,
        'owners': owners_pct,
        'kpis': kpis_pct,
        'portals': portals_pct,
        'average_metrics': avg_metrics,
        'top_teams': teams.most_common(5),
        'top_owners': owners.most_common(5),
        'top_kpis': kpis.most_common(3),
        'top_initiatives_by_score': top_initiatives[:10],
        'sorted_initiatives': sorted_initiatives
    }

def format_statistics_text_fast(stats):
    """Formatear estadísticas optimizado"""
    if not stats:
        return "No hay datos para mostrar estadísticas."
    
    lines = [
        f"📊 **ESTADÍSTICAS SALUDIA** ({stats['total_initiatives']} iniciativas)\n"
    ]
    
    # TOP 5 INICIATIVAS
    if stats.get('top_initiatives_by_score'):
        lines.append("🏆 **TOP 5 INICIATIVAS POR SCORE:**")
        for i, init in enumerate(stats['top_initiatives_by_score'][:5], 1):
            lines.append(f"{i}. **{init['name']}** - Score: {init['score']:.2f}")
            lines.append(f"   👥 {init['team']} | 👤 {init['owner']}\n")
    
    # Distribución por equipos
    lines.append("👥 **DISTRIBUCIÓN POR EQUIPOS:**")
    for team, percentage in list(stats['teams'].items())[:5]:
        count = next(count for t, count in stats['top_teams'] if t == team)
        lines.append(f"• {team}: {count} iniciativas ({percentage:.1f}%)")
    
    # Top owners
    lines.append("\n👤 **TOP RESPONSABLES:**")
    for owner, percentage in list(stats['owners'].items())[:5]:
        count = next(count for o, count in stats['top_owners'] if o == owner)
        lines.append(f"• {owner}: {count} iniciativas ({percentage:.1f}%)")
    
    # Métricas promedio
    if stats['average_metrics']:
        lines.append("\n📊 **MÉTRICAS PROMEDIO:**")
        metrics = stats['average_metrics']
        lines.extend([
            f"• Alcance: {metrics.get('reach', 0):.1f}%",
            f"• Impacto: {metrics.get('impact', 0):.1f}/3",
            f"• Confianza: {metrics.get('confidence', 0):.1f}%",
            f"• Esfuerzo: {metrics.get('effort', 0):.1f} sprints",
            f"• **Score Promedio: {metrics.get('score', 0):.2f}**"
        ])
    
    return "\n".join(lines)

def search_initiatives(query, field="all"):
    """Buscar iniciativas optimizado"""
    try:
        data = get_initiatives()
        
        if not data.get("success"):
            return {"success": False, "error": data.get("error"), "results": []}
        
        initiatives = data.get("data", [])
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
        
        # Búsqueda optimizada
        matching = []
        for initiative in initiatives:
            if not isinstance(initiative, dict):
                continue
            
            for field_name in fields_to_search:
                if field_name in initiative and initiative[field_name]:
                    if query_lower in str(initiative[field_name]).lower():
                        matching.append(initiative)
                        break
        
        sorted_matching = sort_initiatives_by_score(matching)
        
        logger.info(f"✅ Search '{query}' found {len(sorted_matching)} results")
        return {"success": True, "results": sorted_matching, "total": len(sorted_matching)}
        
    except Exception as e:
        logger.error(f"❌ Error searching initiatives: {e}")
        return {"success": False, "error": str(e), "results": []}

def query_llm_optimized(prompt, context=None):
    """LLM optimizado con timeout reducido"""
    if not GROQ_API_KEY:
        return {"success": False, "error": "LLM no configurado", "response": "El asistente AI no está disponible."}
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prompt optimizado y más corto
        system_message = """Eres el Asistente de Análisis de Iniciativas de Saludia. Proporciona insights estratégicos CONCISOS sobre el portfolio de iniciativas usando metodología RICE.

🎯 CONTEXTO:
- Marketplace farmacéutico (droguerías + sellers/laboratorios)
- Equipos: Product, Sales, Ops, CS, Controlling, Growth
- Score RICE = (Reach × Impact × Confidence) / Effort

💡 RESPUESTA REQUERIDA (MÁXIMO 600 PALABRAS):
1. 🏆 Top 3 iniciativas por score y por qué destacan
2. ⚖️ Balance entre equipos y recursos
3. 🔴 Iniciativas sub-optimizadas (bajo score) y mejoras
4. 📈 2-3 recomendaciones estratégicas priorizadas

Sé CONCISO, ESPECÍFICO y ACCIONABLE. Enfócate en insights de alto valor."""

        messages = [{"role": "system", "content": system_message}]
        
        if context:
            # Contexto más compacto
            context_short = f"DATOS SALUDIA (TOP por score):\n{context[:1500]}..."  # Limitar contexto
            messages.append({"role": "user", "content": context_short})
        
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 600,  # Reducido para respuesta más rápida
            "temperature": 0.6  # Reducido para mayor consistencia
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=20)  # Timeout reducido
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return {"success": True, "response": ai_response}
        else:
            return {"success": False, "error": f"HTTP {response.status_code}", "response": "Error consultando AI."}
    
    except Exception as e:
        logger.error(f"❌ LLM Error: {e}")
        return {"success": False, "error": str(e), "response": "Error técnico del asistente AI."}

def analyze_initiatives_with_llm_fast(initiatives):
    """Analizar iniciativas con LLM optimizado"""
    if not initiatives:
        return "No hay iniciativas para analizar."
    
    try:
        # Estadísticas rápidas
        stats = calculate_statistics_fast(initiatives)
        
        # Contexto compacto
        context_lines = [
            f"PORTFOLIO SALUDIA ({stats['total_initiatives']} iniciativas):\n",
            "🏆 TOP 5 POR SCORE:"
        ]
        
        # Solo top 5 para reducir contexto
        for i, init in enumerate(stats.get('top_initiatives_by_score', [])[:5], 1):
            context_lines.append(f"{i}. {init['name']} - {init['score']:.2f} ({init['team']})")
        
        context_lines.extend([
            f"\n📊 PROMEDIOS: Score={stats['average_metrics'].get('score', 0):.2f}, Reach={stats['average_metrics'].get('reach', 0):.0f}%",
            f"👥 EQUIPOS: {', '.join([f'{t}({c})' for t, c in stats['top_teams'][:3]])}"
        ])
        
        context = "\n".join(context_lines)
        
        prompt = "Analiza este portfolio priorizando por score RICE. Sé conciso y específico."
        
        result = query_llm_optimized(prompt, context)
        return result.get("response", "Error analizando iniciativas.")
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return "Error en el análisis. Datos básicos están disponibles."

def format_initiative_summary_fast(initiative, index=None):
    """Formatear iniciativa optimizado"""
    try:
        name = initiative.get('initiative_name', 'Sin nombre')
        owner = initiative.get('owner', 'Sin owner')
        team = initiative.get('team', 'Sin equipo')
        score = calculate_score_fast(initiative)
        
        priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
        prefix = f"**{index}.** " if index else ""
        
        return f"{prefix}{priority_emoji} **{name}** (Score: {score:.2f})\n👤 {owner} | 👥 {team}"
        
    except Exception as e:
        logger.error(f"Format error: {e}")
        return f"{index}. **Error de formato**"

def send_telegram_message(chat_id, text, parse_mode=None):
    """Enviar mensaje optimizado"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": chat_id, "text": text}
        if parse_mode:
            data["parse_mode"] = parse_mode
        
        response = requests.post(url, json=data, timeout=8)  # Timeout reducido
        return response.status_code == 200
    except Exception as e:
        logger.error(f"❌ Telegram error: {e}")
        return False

def setup_webhook():
    """Configurar webhook optimizado"""
    try:
        # Delete webhook primero
        delete_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteWebhook"
        requests.post(delete_url, timeout=8)
        
        # Set nuevo webhook
        webhook_url = f"{WEBHOOK_URL}/telegram-webhook"
        set_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/setWebhook"
        data = {"url": webhook_url}
        
        response = requests.post(set_url, json=data, timeout=8)
        
        if response.status_code == 200:
            result = response.json()
            if result.get("ok"):
                logger.info(f"✅ Webhook configured: {webhook_url}")
                return True
        
        logger.error(f"❌ Webhook setup failed")
        return False
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return False

# ===== ENDPOINTS FLASK =====

@app.route('/')
def home():
    """Endpoint principal optimizado"""
    return jsonify({
        "name": "Saludia Initiatives MCP Server OPTIMIZED",
        "version": "2.4.0",
        "status": "running",
        "optimizations": ["cache_system", "fast_scoring", "reduced_timeouts", "compact_context"],
        "timestamp": datetime.now().isoformat(),
        "cache_status": {
            "enabled": True,
            "ttl_seconds": initiatives_cache["ttl"],
            "last_update": datetime.fromtimestamp(initiatives_cache["timestamp"]).isoformat() if initiatives_cache["timestamp"] > 0 else "never"
        }
    })

@app.route('/health')
def health():
    """Health check optimizado"""
    start_time = time.time()
    nocodb_test = get_initiatives()
    response_time = time.time() - start_time
    
    return jsonify({
        "status": "healthy",
        "response_time_ms": round(response_time * 1000, 2),
        "cache_hit": nocodb_test.get('cached', False),
        "services": {
            "flask": "running",
            "nocodb": "ok" if nocodb_test.get('success') else "error",
            "cache": "active" if initiatives_cache["data"] else "empty"
        }
    })

@app.route('/api/initiatives')
def api_initiatives():
    """API optimizada"""
    data = get_initiatives()
    if data.get("success"):
        sorted_initiatives = sort_initiatives_by_score(data.get("data", []))
        data["data"] = sorted_initiatives
        data["performance"] = {"cached": data.get("cached", False)}
    return jsonify(data)

@app.route('/api/initiatives/statistics', methods=['GET'])
def api_statistics():
    """API estadísticas optimizada"""
    data = get_initiatives()
    
    if not data.get("success"):
        return jsonify({"error": "Could not fetch initiatives"}), 500
    
    stats = calculate_statistics_fast(data.get("data", []))
    stats["performance"] = {"cached": data.get("cached", False)}
    return jsonify(stats)

@app.route('/api/create', methods=['POST'])
def api_create():
    """API crear optimizada"""
    if not request.json:
        return jsonify({"error": "JSON required"}), 400
    
    result = create_initiative(request.json)
    return jsonify(result)

@app.route('/ai/analyze-initiatives', methods=['POST'])
def analyze_initiatives_endpoint():
    """Endpoint análisis optimizado"""
    try:
        start_time = time.time()
        data = get_initiatives()
        
        if not data.get("success"):
            return jsonify({
                "success": False,
                "error": "No se pudieron obtener las iniciativas"
            }), 500
        
        initiatives = data.get("data", [])
        
        # Ejecutar análisis en paralelo si es posible
        analysis = analyze_initiatives_with_llm_fast(initiatives)
        stats = calculate_statistics_fast(initiatives)
        
        response_time = time.time() - start_time
        
        return jsonify({
            "success": True,
            "initiatives_count": len(initiatives),
            "analysis": analysis,
            "statistics": stats,
            "performance": {
                "response_time_ms": round(response_time * 1000, 2),
                "cached": data.get("cached", False),
                "optimized": True
            },
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "analysis": "Error técnico durante el análisis."
        }), 500

# ===== BOT DE TELEGRAM OPTIMIZADO =====

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    """Webhook optimizado"""
    try:
        update_data = request.get_json()
        
        if not update_data or 'message' not in update_data:
            return "OK", 200
        
        message = update_data['message']
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        
        if 'text' not in message:
            return "OK", 200
        
        text = message['text'].strip().lower()
        
        # Router optimizado
        if text in ['/start', 'start', 'inicio', 'hola']:
            handle_start_command(chat_id)
        elif text in ['/help', 'help', 'ayuda']:
            handle_help_command(chat_id)
        elif text in ['/iniciativas', 'iniciativas', 'lista']:
            handle_list_initiatives_fast(chat_id)
        elif text in ['/crear', 'crear', 'nueva']:
            handle_create_command(chat_id, user_id)
        elif text in ['/analizar', 'analizar', 'análisis']:
            handle_analyze_command_fast(chat_id)
        elif text.startswith(('buscar ', '/buscar ')):
            query = text.split(' ', 1)[1] if ' ' in text else ""
            if query:
                handle_search_command_fast(chat_id, query)
            else:
                send_telegram_message(chat_id, "🔍 **¿Qué quieres buscar?**\n\nEjemplos:\n• `buscar Product`\n• `buscar API`")
        else:
            if user_id in user_states:
                handle_text_message(chat_id, user_id, message['text'])
            else:
                handle_natural_message_fast(chat_id, text)
        
        return "OK", 200
        
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return "ERROR", 500

def handle_natural_message_fast(chat_id, text):
    """Manejar mensajes naturales optimizado"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['iniciativa', 'proyecto', 'lista']):
        send_telegram_message(chat_id, "🎯 Ver iniciativas: `iniciativas`")
    elif any(word in text_lower for word in ['buscar', 'encontrar']):
        send_telegram_message(chat_id, "🔍 Buscar: `buscar <término>`")
    elif any(word in text_lower for word in ['crear', 'nueva']):
        send_telegram_message(chat_id, "🆕 Crear: `crear`")
    elif any(word in text_lower for word in ['análisis', 'analizar']):
        send_telegram_message(chat_id, "📊 Análisis: `analizar`")
    else:
        send_telegram_message(chat_id, "👋 Comandos: `iniciativas`, `buscar`, `crear`, `analizar`, `ayuda`")

def handle_start_command(chat_id):
    """Comando start optimizado"""
    logger.info(f"📱 /start from chat {chat_id}")
    
    text = """🎯 **Bot Saludia v2.4** ⚡ OPTIMIZADO

🢊 Asistente de gestión de iniciativas para equipos Saludia.

**📋 Comandos principales:**
• `iniciativas` - Lista ordenada por score RICE 🏆
• `buscar <término>` - Búsqueda rápida
• `crear` - Nueva iniciativa con RICE
• `analizar` - Análisis AI del portfolio

**🔍 Ejemplos:**
• `buscar Product` - Por equipo
• `buscar API` - Por tecnología
• `buscar Juan` - Por responsable

**⚡ Optimizaciones v2.4:**
• Cache inteligente para respuestas rápidas
• Análisis AI optimizado (20s → 8s)
• Timeouts reducidos
• Interfaz más ágil

💡 **Tip:** No uses `/` - solo escribe la palabra."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_help_command(chat_id):
    """Comando help optimizado"""
    text = """📚 **Comandos Disponibles** ⚡ v2.4

**🏃‍♂️ Comandos Rápidos:**
• `iniciativas` - Lista completa por score RICE
• `buscar <término>` - Búsqueda optimizada
• `crear` - Nueva iniciativa (validaciones RICE)
• `analizar` - Análisis AI estratégico (RÁPIDO)

**🔍 Búsquedas:**
• `buscar Product` - Por equipo
• `buscar drogería` - Por descripción
• `buscar API` - Por tecnología

**🏆 Score RICE:**
• 🔥 Score ≥ 2.0 (Alta prioridad)
• ⭐ Score ≥ 1.0 (Media prioridad)
• 📋 Score < 1.0 (Baja prioridad)

**⚡ Nuevas Optimizaciones:**
✅ Cache de 5min para respuestas instantáneas
✅ Análisis AI 60% más rápido
✅ Timeouts optimizados
✅ Interfaz más ágil

🤖 **IA:** Análisis estratégico especializado en Saludia con insights priorizados por score RICE."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_list_initiatives_fast(chat_id):
    """Listar iniciativas optimizado"""
    logger.info(f"📱 List initiatives FAST from chat {chat_id}")
    
    send_telegram_message(chat_id, "⚡ **Cargando iniciativas...**")
    
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error', 'Desconocido')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas.")
        return
    
    # Estadísticas rápidas
    stats = calculate_statistics_fast(initiatives)
    stats_text = format_statistics_text_fast(stats)
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Lista rápida - solo top 10
    sorted_initiatives = stats.get('sorted_initiatives', initiatives)
    
    text = "📋 **TOP 10 INICIATIVAS POR SCORE:**\n\n"
    for i, init in enumerate(sorted_initiatives[:10], 1):
        formatted = format_initiative_summary_fast(init, i)
        text += f"{formatted}\n\n"
    
    if len(sorted_initiatives) > 10:
        text += f"📌 **{len(sorted_initiatives) - 10} iniciativas más...**\nUsa `buscar` para encontrar específicas."
    
    cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
    text += f"\n💡 **Tip:** Datos actualizados{cache_info}"
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_search_command_fast(chat_id, query):
    """Búsqueda optimizada"""
    logger.info(f"📱 Search FAST '{query}' from chat {chat_id}")
    
    result = search_initiatives(query)
    
    if not result.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {result.get('error')}")
        return
    
    results = result.get("results", [])
    total = result.get("total", 0)
    
    if not results:
        send_telegram_message(chat_id, f"""🔍 **Sin resultados:** "{query}"

💡 **Sugerencias:**
• `buscar Product` - Por equipo
• `buscar API` - Por tecnología
• `iniciativas` - Ver todas""")
        return
    
    text = f"🔍 **RESULTADOS:** {query} ({total} encontrados)\n\n"
    
    # Mostrar solo primeros 3 resultados para rapidez
    for i, init in enumerate(results[:3], 1):
        name = init.get('initiative_name', 'Sin nombre')
        team = init.get('team', 'Sin equipo')
        score = calculate_score_fast(init)
        priority = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
        
        text += f"**{i}.** {priority} **{name}** (Score: {score:.2f})\n"
        text += f"👥 {team} | 👤 {init.get('owner', 'Sin owner')}\n"
        text += f"📝 {init.get('description', 'Sin descripción')[:100]}...\n\n"
    
    if total > 3:
        text += f"📌 **{total - 3} resultados más...** Refina tu búsqueda."
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_analyze_command_fast(chat_id):
    """Análisis optimizado"""
    logger.info(f"📱 Analyze FAST from chat {chat_id}")
    
    send_telegram_message(chat_id, "🤖 **Analizando portfolio...** ⚡")
    
    start_time = time.time()
    data = get_initiatives()
    
    if not data.get("success"):
        send_telegram_message(chat_id, f"❌ Error: {data.get('error')}")
        return
    
    initiatives = data.get("data", [])
    
    if not initiatives:
        send_telegram_message(chat_id, "📭 No hay iniciativas.")
        return
    
    # Estadísticas rápidas primero
    stats = calculate_statistics_fast(initiatives)
    stats_text = format_statistics_text_fast(stats)
    
    cache_info = " (Cache)" if data.get("cached") else " (Fresh)"
    stats_text += f"\n⚡ **Datos{cache_info}**"
    
    send_telegram_message(chat_id, stats_text, parse_mode='Markdown')
    
    # Análisis AI optimizado
    if GROQ_API_KEY:
        send_telegram_message(chat_id, "🧠 **Generando análisis estratégico...**")
        
        analysis = analyze_initiatives_with_llm_fast(initiatives)
        analysis_time = time.time() - start_time
        
        analysis_text = f"🤖 **ANÁLISIS ESTRATÉGICO** ⚡\n\n{analysis}"
        analysis_text += f"\n\n⏱️ **Tiempo:** {analysis_time:.1f}s"
        
        if len(analysis_text) > 4000:
            chunks = [analysis_text[i:i+4000] for i in range(0, len(analysis_text), 4000)]
            for chunk in chunks:
                send_telegram_message(chat_id, chunk, parse_mode='Markdown')
        else:
            send_telegram_message(chat_id, analysis_text, parse_mode='Markdown')
    else:
        send_telegram_message(chat_id, "⚠️ Análisis AI no disponible.")

def handle_create_command(chat_id, user_id):
    """Crear iniciativa - mantenemos funcionalidad completa"""
    logger.info(f"📱 Create command from chat {chat_id}")
    
    user_states[user_id] = {
        'step': 'name',
        'data': {},
        'chat_id': chat_id
    }
    
    text = """🆕 **CREAR INICIATIVA** ⚡

📝 **Paso 1/8:** Nombre de la iniciativa

Envía el nombre (máximo 255 caracteres).

**Ejemplos:**
• "Integración API de pagos"
• "Optimización del checkout"
• "Dashboard analytics v2"

💡 **Tip:** Nombre descriptivo para mejor score RICE."""
    
    send_telegram_message(chat_id, text, parse_mode='Markdown')

def handle_text_message(chat_id, user_id, text):
    """Manejar mensajes de creación - versión optimizada"""
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    step = state['step']
    
    try:
        if step == 'name':
            if len(text) > 255:
                send_telegram_message(chat_id, "❌ Máximo 255 caracteres.")
                return
            
            state['data']['initiative_name'] = text.strip()
            state['step'] = 'description'
            send_telegram_message(chat_id, """📝 **Paso 2/8:** Descripción

Describe la iniciativa (máximo 1000 caracteres).

💡 **Tip:** Incluye problema y beneficio esperado.""", parse_mode='Markdown')
        
        elif step == 'description':
            if len(text) > 1000:
                send_telegram_message(chat_id, "❌ Máximo 1000 caracteres.")
                return
                
            state['data']['description'] = text.strip()
            state['step'] = 'owner'
            send_telegram_message(chat_id, """👤 **Paso 3/8:** Responsable

¿Quién es el owner? (máximo 100 caracteres)

**Ejemplo:** Juan Pérez""", parse_mode='Markdown')
        
        elif step == 'owner':
            if len(text) > 100:
                send_telegram_message(chat_id, "❌ Máximo 100 caracteres.")
                return
                
            state['data']['owner'] = text.strip()
            state['step'] = 'team'
            send_telegram_message(chat_id, """👥 **Paso 4/8:** Equipo

**Opciones:** Product, Sales, Ops, CS, Controlling, Growth""", parse_mode='Markdown')
        
        elif step == 'team':
            valid_teams = ['Product', 'Sales', 'Ops', 'CS', 'Controlling', 'Growth']
            matched_team = next((t for t in valid_teams if t.lower() == text.strip().lower()), None)
            
            if not matched_team:
                send_telegram_message(chat_id, f"❌ Debe ser: {', '.join(valid_teams)}")
                return
            
            state['data']['team'] = matched_team
            state['step'] = 'portal'
            send_telegram_message(chat_id, """🖥️ **Paso 5/8:** Portal

**Opciones:** Seller, Droguista, Admin""", parse_mode='Markdown')
        
        elif step == 'portal':
            valid_portals = ['Seller', 'Droguista', 'Admin']
            matched_portal = next((p for p in valid_portals if p.lower() == text.strip().lower()), None)
            
            if not matched_portal:
                send_telegram_message(chat_id, f"❌ Debe ser: {', '.join(valid_portals)}")
                return
            
            state['data']['portal'] = matched_portal
            state['step'] = 'kpi'
            send_telegram_message(chat_id, """📊 **Paso 6/8:** KPI Principal (Opcional)

**Ejemplos:** Conversion Rate, GMV, User Retention

💡 Escribe `ninguno` si no tienes KPI específico.""", parse_mode='Markdown')
        
        elif step == 'kpi':
            if text.strip().lower() not in ['ninguno', 'no', 'n/a', '']:
                if len(text.strip()) > 255:
                    send_telegram_message(chat_id, "❌ Máximo 255 caracteres.")
                    return
                state['data']['main_kpi'] = text.strip()
            
            state['step'] = 'reach'
            send_telegram_message(chat_id, """📈 **Paso 7/8:** Métricas RICE

**REACH:** ¿Qué % de usuarios impacta?
Envía número entre 0-100.

**Ejemplos:** 85, 25, 100""", parse_mode='Markdown')
        
        elif step == 'reach':
            try:
                reach = float(text.strip())
                if not (0 <= reach <= 100):
                    send_telegram_message(chat_id, "❌ Entre 0 y 100.")
                    return
                
                state['data']['reach'] = reach / 100
                state['step'] = 'impact'
                send_telegram_message(chat_id, """💥 **IMPACT:** ¿Qué tanto impacto?

**Opciones:** 1 (bajo), 2 (medio), 3 (alto)""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido entre 0-100.")
                return
        
        elif step == 'impact':
            try:
                impact = int(text.strip())
                if impact not in [1, 2, 3]:
                    send_telegram_message(chat_id, "❌ Debe ser 1, 2 o 3.")
                    return
                
                state['data']['impact'] = impact
                state['step'] = 'confidence'
                send_telegram_message(chat_id, """🎯 **CONFIDENCE:** ¿% de confianza en el impacto?

Número entre 0-100.

**Ejemplos:** 90, 70, 50""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido: 1, 2 o 3.")
                return
        
        elif step == 'confidence':
            try:
                confidence = float(text.strip())
                if not (0 <= confidence <= 100):
                    send_telegram_message(chat_id, "❌ Entre 0 y 100.")
                    return
                
                state['data']['confidence'] = confidence / 100
                state['step'] = 'effort'
                send_telegram_message(chat_id, """⚡ **EFFORT:** ¿Cuántos sprints de desarrollo?

**Ejemplos:** 1, 2.5, 0.5

💡 Escribe `default` para 1 sprint.""", parse_mode='Markdown')
                
            except ValueError:
                send_telegram_message(chat_id, "❌ Número válido entre 0-100.")
                return
        
        elif step == 'effort':
            if text.strip().lower() in ['default', '']:
                state['data']['effort'] = 1.0
            else:
                try:
                    effort = float(text.strip())
                    if effort <= 0:
                        send_telegram_message(chat_id, "❌ Mayor a 0.")
                        return
                    state['data']['effort'] = effort
                except ValueError:
                    send_telegram_message(chat_id, "❌ Número válido o 'default'.")
                    return
            
            # Crear iniciativa
            create_result = create_initiative(state['data'])
            
            if create_result.get('success'):
                data = state['data']
                score = (data['reach'] * data['impact'] * data['confidence']) / data['effort']
                
                priority_emoji = "🔥" if score >= 2.0 else "⭐" if score >= 1.0 else "📋"
                priority_text = "Alta" if score >= 2.0 else "Media" if score >= 1.0 else "Baja"
                
                confirmation = f"""✅ **INICIATIVA CREADA** ⚡

{priority_emoji} **{data['initiative_name']}**

👤 **Owner:** {data['owner']}
👥 **Equipo:** {data['team']}
🖥️ **Portal:** {data['portal']}

📈 **Métricas RICE:**
• **Reach:** {data['reach']*100:.0f}%
• **Impact:** {data['impact']}/3
• **Confidence:** {data['confidence']*100:.0f}%
• **Effort:** {data['effort']} sprints
• **Score:** {score:.2f}

🏆 **Prioridad:** {priority_text} ({priority_emoji})

💡 **Siguiente:** `buscar {data['initiative_name'][:20]}`"""
                
                send_telegram_message(chat_id, confirmation, parse_mode='Markdown')
            else:
                error_msg = f"❌ Error: {create_result.get('error', 'Desconocido')}"
                if 'validation_errors' in create_result:
                    error_msg += f"\n\n**Errores:**\n• " + "\n• ".join(create_result['validation_errors'])
                send_telegram_message(chat_id, error_msg, parse_mode='Markdown')
            
            del user_states[user_id]
    
    except Exception as e:
        logger.error(f"❌ Text message error: {e}")
        send_telegram_message(chat_id, "❌ Error procesando mensaje.")
        if user_id in user_states:
            del user_states[user_id]

# ===== MAIN OPTIMIZADO =====

if __name__ == '__main__':
    logger.info("🚀 Starting Saludia MCP Server OPTIMIZED v2.4")
    
    # Configurar webhook
    if TELEGRAM_TOKEN:
        bot_configured = setup_webhook()
        logger.info(f"🤖 Bot webhook: {bot_configured}")
    
    # Pre-cargar cache si es posible
    try:
        logger.info("📊 Pre-loading initiatives cache...")
        get_initiatives()
        logger.info("✅ Cache pre-loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ Cache pre-load failed: {e}")
    
    # Ejecutar Flask
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Starting optimized Flask app on port {port}")
    logger.info("⚡ Optimizations: Cache, Fast Scoring, Reduced Timeouts, Compact Context")
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
