# 📊 analytics.py - Análisis y Estadísticas v2.6
import requests
import logging
from collections import Counter
from config import *
from database import sort_initiatives_by_score, calculate_score_fast

logger = logging.getLogger(__name__)

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
    statuses = Counter(init.get('status', 'Sin estado').strip() for init in sorted_initiatives if isinstance(init, dict))
    
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
                        'owner': init.get('owner', 'Sin owner'),
                        'status': init.get('status', 'Sin estado')
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
    statuses_pct = {status: (count/total)*100 for status, count in statuses.most_common()}
    
    return {
        'total_initiatives': total,
        'teams': teams_pct,
        'owners': owners_pct,
        'kpis': kpis_pct,
        'portals': portals_pct,
        'statuses': statuses_pct,
        'average_metrics': avg_metrics,
        'top_teams': teams.most_common(5),
        'top_owners': owners.most_common(5),
        'top_kpis': kpis.most_common(3),
        'top_statuses': statuses.most_common(),
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
            status_emoji = get_status_emoji(init.get('status', ''))
            lines.append(f"{i}. **{init['name']}** - Score: {init['score']:.2f}")
            lines.append(f"   👥 {init['team']} | 👤 {init['owner']} | {status_emoji} {init['status']}\n")
    
    # Distribución por estados
    if stats.get('top_statuses'):
        lines.append("📊 **DISTRIBUCIÓN POR ESTADOS:**")
        for status, count in stats['top_statuses']:
            percentage = stats['statuses'][status]
            emoji = get_status_emoji(status)
            lines.append(f"• {emoji} {status}: {count} iniciativas ({percentage:.1f}%)")
        lines.append("")
    
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
        lines.append("\n📈 **MÉTRICAS PROMEDIO:**")
        metrics = stats['average_metrics']
        lines.extend([
            f"• Alcance: {metrics.get('reach', 0):.1f}%",
            f"• Impacto: {metrics.get('impact', 0):.1f}/3",
            f"• Confianza: {metrics.get('confidence', 0):.1f}%",
            f"• Esfuerzo: {metrics.get('effort', 0):.1f} sprints",
            f"• **Score Promedio: {metrics.get('score', 0):.2f}**"
        ])
    
    return "\n".join(lines)

def get_status_emoji(status):
    """Obtener emoji para estado"""
    status_emojis = {
        'Pending': '⏳',
        'In Sprint': '🔧',
        'Production': '🚀',
        'Monitoring': '📊',
        'Cancelled': '❌',
        'On Hold': '⏸️'
    }
    return status_emojis.get(status, '📋')

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
- Estados: Pending → In Sprint → Production → Monitoring

💡 RESPUESTA REQUERIDA (MÁXIMO 600 PALABRAS):
1. 🏆 Top 3 iniciativas por score y por qué destacan
2. 📊 Análisis de distribución por estados (workflow)
3. ⚖️ Balance entre equipos y recursos
4. 🔴 Iniciativas sub-optimizadas (bajo score) y mejoras
5. 📈 2-3 recomendaciones estratégicas priorizadas

Sé CONCISO, ESPECÍFICO y ACCIONABLE. Enfócate en insights de alto valor considerando el flujo de estados."""

        messages = [{"role": "system", "content": system_message}]
        
        if context:
            # Contexto más compacto
            context_short = f"DATOS SALUDIA (TOP por score):\n{context[:LLM_CONTEXT_LIMIT]}..."
            messages.append({"role": "user", "content": context_short})
        
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": LLM_TEMPERATURE
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=LLM_TIMEOUT)
        
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
        
        # Contexto compacto con información de estados
        context_lines = [
            f"PORTFOLIO SALUDIA ({stats['total_initiatives']} iniciativas):\n",
            "🏆 TOP 5 POR SCORE:"
        ]
        
        # Solo top 5 para reducir contexto
        for i, init in enumerate(stats.get('top_initiatives_by_score', [])[:5], 1):
            status_emoji = get_status_emoji(init.get('status', ''))
            context_lines.append(f"{i}. {init['name']} - Score: {init['score']:.2f} ({init['team']}) {status_emoji} {init['status']}")
        
        # Distribución por estados
        context_lines.append(f"\n📊 ESTADOS:")
        for status, count in stats.get('top_statuses', []):
            percentage = stats['statuses'][status]
            emoji = get_status_emoji(status)
            context_lines.append(f"• {emoji} {status}: {count} ({percentage:.0f}%)")
        
        context_lines.extend([
            f"\n📈 PROMEDIOS: Score={stats['average_metrics'].get('score', 0):.2f}, Reach={stats['average_metrics'].get('reach', 0):.0f}%",
            f"👥 EQUIPOS TOP: {', '.join([f'{t}({c})' for t, c in stats['top_teams'][:3]])}"
        ])
        
        context = "\n".join(context_lines)
        
        prompt = "Analiza este portfolio priorizando por score RICE y considerando el flujo de estados. Sé conciso y específico."
        
        result = query_llm_optimized(prompt, context)
        return result.get("response", "Error analizando iniciativas.")
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return "Error en el análisis. Datos básicos están disponibles."os están disponibles."
