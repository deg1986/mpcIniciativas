# 📊 analytics.py - Análisis y Estadísticas v2.6 - FIXED + GROWTH FOCUS
import requests
import logging
from collections import Counter
from config import *
from database import sort_initiatives_by_score, calculate_score_fast

logger = logging.getLogger(__name__)

def safe_get_string(init, field, default='Sin datos'):
    """Obtener string de forma segura manejando None values - FIX PRINCIPAL"""
    try:
        value = init.get(field, default)
        if value is None:
            return default
        # Convertir a string y luego hacer strip - ESTO SOLUCIONA EL ERROR
        return str(value).strip() if str(value).strip() else default
    except Exception as e:
        logger.warning(f"Error getting {field}: {e}")
        return default

def calculate_statistics_fast(initiatives):
    """Calcular estadísticas optimizado - FIXED VERSION"""
    if not initiatives:
        return {}
    
    try:
        sorted_initiatives = sort_initiatives_by_score(initiatives)
        total = len(sorted_initiatives)
        
        # Contadores usando Counter - VERSION SEGURA
        teams = Counter()
        owners = Counter() 
        kpis = Counter()
        portals = Counter()
        statuses = Counter()
        
        # Procesar cada iniciativa de forma segura
        for init in sorted_initiatives:
            if isinstance(init, dict):
                try:
                    # Usar safe_get_string para evitar None.strip() - FIX PRINCIPAL
                    team = safe_get_string(init, 'team', 'Sin equipo')
                    owner = safe_get_string(init, 'owner', 'Sin owner') 
                    kpi = safe_get_string(init, 'main_kpi', 'Sin KPI')
                    portal = safe_get_string(init, 'portal', 'Sin portal')
                    status = safe_get_string(init, 'status', 'Sin estado')
                    
                    teams[team] += 1
                    owners[owner] += 1
                    kpis[kpi] += 1
                    portals[portal] += 1
                    statuses[status] += 1
                except Exception as e:
                    logger.warning(f"Error processing initiative: {e}")
                    continue
        
        # Métricas numéricas optimizadas
        metrics = []
        top_initiatives = []
        growth_initiatives = []  # NUEVO: Enfoque en Growth
        
        for init in sorted_initiatives:
            if isinstance(init, dict):
                try:
                    reach = float(init.get('reach', 0)) or 0
                    impact = float(init.get('impact', 0)) or 0
                    confidence = float(init.get('confidence', 0)) or 0
                    effort = float(init.get('effort', 1)) or 1
                    score = float(init.get('score', 0)) or init.get('calculated_score', 0)
                    
                    if any([reach, impact, confidence, effort]):
                        metrics.append({
                            'reach': reach, 'impact': impact, 
                            'confidence': confidence, 'effort': effort, 'score': score
                        })
                    
                    if score > 0:
                        initiative_data = {
                            'name': safe_get_string(init, 'initiative_name', 'Sin nombre'),
                            'score': score,
                            'team': safe_get_string(init, 'team', 'Sin equipo'),
                            'owner': safe_get_string(init, 'owner', 'Sin owner'),
                            'status': safe_get_string(init, 'status', 'Sin estado'),
                            'description': safe_get_string(init, 'description', 'Sin descripción')[:100],
                            'kpi': safe_get_string(init, 'main_kpi', 'Sin KPI'),
                            'portal': safe_get_string(init, 'portal', 'Sin portal')
                        }
                        top_initiatives.append(initiative_data)
                        
                        # NUEVO: Identificar iniciativas de Growth
                        if safe_get_string(init, 'team', '').lower() == 'growth':
                            growth_initiatives.append(initiative_data)
                            
                except Exception as e:
                    logger.warning(f"Error processing metrics for initiative: {e}")
                    continue
        
        # Promedios seguros
        avg_metrics = {}
        if metrics:
            try:
                avg_metrics = {
                    'reach': sum(m['reach'] for m in metrics) / len(metrics) * 100,
                    'impact': sum(m['impact'] for m in metrics) / len(metrics),
                    'confidence': sum(m['confidence'] for m in metrics) / len(metrics) * 100,
                    'effort': sum(m['effort'] for m in metrics) / len(metrics),
                    'score': sum(m['score'] for m in metrics) / len(metrics)
                }
            except Exception as e:
                logger.warning(f"Error calculating averages: {e}")
                avg_metrics = {'reach': 0, 'impact': 0, 'confidence': 0, 'effort': 0, 'score': 0}
        
        # Porcentajes seguros
        teams_pct = {team: (count/total)*100 for team, count in teams.most_common()} if total > 0 else {}
        owners_pct = {owner: (count/total)*100 for owner, count in owners.most_common()} if total > 0 else {}
        kpis_pct = {kpi: (count/total)*100 for kpi, count in kpis.most_common()} if total > 0 else {}
        portals_pct = {portal: (count/total)*100 for portal, count in portals.most_common()} if total > 0 else {}
        statuses_pct = {status: (count/total)*100 for status, count in statuses.most_common()} if total > 0 else {}
        
        # NUEVO: Análisis específico de Growth
        growth_stats = {
            'total_growth_initiatives': len(growth_initiatives),
            'growth_percentage': (len(growth_initiatives)/total)*100 if total > 0 else 0,
            'growth_avg_score': sum(g['score'] for g in growth_initiatives) / len(growth_initiatives) if growth_initiatives else 0,
            'top_growth_initiatives': growth_initiatives[:5]
        }
        
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
            'sorted_initiatives': sorted_initiatives,
            'growth_stats': growth_stats  # NUEVO: Stats específicos de Growth
        }
        
    except Exception as e:
        logger.error(f"❌ Fatal error in calculate_statistics_fast: {e}")
        return {
            'total_initiatives': 0,
            'teams': {}, 'owners': {}, 'kpis': {}, 'portals': {}, 'statuses': {},
            'average_metrics': {}, 'top_teams': [], 'top_owners': [], 'top_kpis': [],
            'top_statuses': [], 'top_initiatives_by_score': [], 'sorted_initiatives': [],
            'growth_stats': {'total_growth_initiatives': 0, 'growth_percentage': 0, 'growth_avg_score': 0, 'top_growth_initiatives': []}
        }

def format_statistics_text_fast(stats):
    """Formatear estadísticas optimizado - GROWTH FOCUSED"""
    if not stats:
        return "No hay datos para mostrar estadísticas."
    
    try:
        lines = [
            f"🎯 **ESTADÍSTICAS SALUDIA - ENFOQUE GROWTH** ({stats['total_initiatives']} iniciativas)\n"
        ]
        
        # NUEVO: Sección específica de Growth
        growth_stats = stats.get('growth_stats', {})
        if growth_stats:
            lines.append("🚀 **ANÁLISIS DE GROWTH:**")
            lines.append(f"• Iniciativas Growth: {growth_stats.get('total_growth_initiatives', 0)} ({growth_stats.get('growth_percentage', 0):.1f}%)")
            lines.append(f"• Score promedio Growth: {growth_stats.get('growth_avg_score', 0):.2f}")
            lines.append("")
            
            # Top Growth initiatives
            top_growth = growth_stats.get('top_growth_initiatives', [])
            if top_growth:
                lines.append("🌟 **TOP INICIATIVAS GROWTH:**")
                for i, init in enumerate(top_growth[:3], 1):
                    priority_emoji = get_priority_emoji_safe(init.get('score', 0))
                    lines.append(f"{i}. {priority_emoji} **{init.get('name', 'Sin nombre')}** - Score: {init.get('score', 0):.2f}")
                    lines.append(f"   📊 {init.get('kpi', 'Sin KPI')} | 🖥️ {init.get('portal', 'Sin portal')}")
                lines.append("")
        
        # TOP 5 INICIATIVAS GENERALES
        if stats.get('top_initiatives_by_score'):
            lines.append("🏆 **TOP 5 INICIATIVAS POR SCORE:**")
            for i, init in enumerate(stats['top_initiatives_by_score'][:5], 1):
                status_emoji = get_status_emoji_safe(init.get('status', ''))
                priority_emoji = get_priority_emoji_safe(init.get('score', 0))
                lines.append(f"{i}. {priority_emoji} **{init.get('name', 'Sin nombre')}** - Score: {init.get('score', 0):.2f}")
                lines.append(f"   👥 {init.get('team', 'Sin equipo')} | 👤 {init.get('owner', 'Sin owner')} | {status_emoji} {init.get('status', 'Sin estado')}")
                lines.append(f"   📝 {init.get('description', 'Sin descripción')}")
                lines.append("")
        
        # Distribución por estados
        if stats.get('top_statuses'):
            lines.append("📊 **DISTRIBUCIÓN POR ESTADOS:**")
            for status, count in stats['top_statuses']:
                percentage = stats['statuses'].get(status, 0)
                emoji = get_status_emoji_safe(status)
                lines.append(f"• {emoji} {status}: {count} iniciativas ({percentage:.1f}%)")
            lines.append("")
        
        # Distribución por equipos con enfoque en Growth
        lines.append("👥 **DISTRIBUCIÓN POR EQUIPOS:**")
        for team, percentage in list(stats['teams'].items())[:6]:  # Aumentado para mostrar Growth
            count = next((count for t, count in stats['top_teams'] if t == team), 0)
            emoji = "🚀" if team == "Growth" else "👥"
            emphasis = "**" if team == "Growth" else ""
            lines.append(f"• {emoji} {emphasis}{team}{emphasis}: {count} iniciativas ({percentage:.1f}%)")
        
        # Top owners
        lines.append("\n👤 **TOP RESPONSABLES:**")
        for owner, percentage in list(stats['owners'].items())[:5]:
            count = next((count for o, count in stats['top_owners'] if o == owner), 0)
            lines.append(f"• {owner}: {count} iniciativas ({percentage:.1f}%)")
        
        # Métricas promedio
        if stats.get('average_metrics'):
            lines.append("\n📈 **MÉTRICAS PROMEDIO:**")
            metrics = stats['average_metrics']
            lines.extend([
                f"• Alcance: {metrics.get('reach', 0):.1f}%",
                f"• Impacto: {metrics.get('impact', 0):.1f}/3",
                f"• Confianza: {metrics.get('confidence', 0):.1f}%",
                f"• Esfuerzo: {metrics.get('effort', 0):.1f} sprints",
                f"• **Score Promedio: {metrics.get('score', 0):.2f}**"
            ])
        
        # NUEVO: Recomendaciones de Growth
        lines.append("\n💡 **RECOMENDACIONES GROWTH:**")
        if growth_stats.get('total_growth_initiatives', 0) < 3:
            lines.append("• ⚠️ Pocas iniciativas de Growth - Considerar más proyectos de crecimiento")
        else:
            lines.append("• ✅ Buen balance de iniciativas de Growth")
            
        high_score_count = sum(1 for init in stats.get('top_initiatives_by_score', []) if init.get('score', 0) >= 2.0)
        if high_score_count < 3:
            lines.append("• ⚠️ Pocas iniciativas de alto impacto (Score ≥ 2.0)")
        else:
            lines.append("• ✅ Suficientes iniciativas de alto impacto")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"❌ Error formatting statistics: {e}")
        return f"Error formateando estadísticas: {str(e)}"

def get_status_emoji_safe(status):
    """Obtener emoji para estado de forma segura"""
    try:
        if not status:
            return '📋'
        status_emojis = {
            'Pending': '⏳',
            'Reviewed': '👁️',
            'Prioritized': '⭐',
            'Backlog': '📝',
            'Sprint': '🔧',
            'Production': '🚀',
            'Monitoring': '📊',
            'Discarded': '❌',
            'Cancelled': '❌',
            'On Hold': '⏸️'
        }
        return status_emojis.get(str(status).strip(), '📋')
    except:
        return '📋'

def get_priority_emoji_safe(score):
    """Obtener emoji de prioridad de forma segura"""
    try:
        score_val = float(score) if score else 0
        if score_val >= 2.0:
            return "🔥"  # Alta prioridad
        elif score_val >= 1.0:
            return "⭐"  # Media prioridad
        else:
            return "📋"  # Baja prioridad
    except:
        return "📋"

def query_llm_optimized(prompt, context=None):
    """LLM optimizado con timeout reducido - GROWTH FOCUSED"""
    if not GROQ_API_KEY:
        return {"success": False, "error": "LLM no configurado", "response": "El asistente AI no está disponible."}
    
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Prompt optimizado con enfoque en Growth para Saludia
        system_message = """Eres el Asistente Estratégico de Growth de Saludia, marketplace farmacéutico líder en LatAm. Tu especialidad es optimizar iniciativas para maximizar el crecimiento del negocio.

🏥 CONTEXTO SALUDIA:
- Marketplace B2B farmacéutico (droguerías + sellers/laboratorios)
- Misión: Democratizar acceso a productos farmacéuticos
- KPIs clave: GMV, Take Rate, User Retention, NPS, Conversion Rate
- Equipos: Product, Sales, Ops, CS, Controlling, **GROWTH** (tu enfoque principal)

📊 METODOLOGÍA RICE:
- Score = (Reach × Impact × Confidence) / Effort
- 🔥 Score ≥ 2.0: Alta prioridad (ejecutar inmediatamente)
- ⭐ Score ≥ 1.0: Media prioridad (próximos sprints)
- 📋 Score < 1.0: Baja prioridad (re-evaluar)

🎯 ANÁLISIS REQUERIDO (MÁXIMO 800 PALABRAS):
1. 🚀 **Enfoque Growth**: Evaluar iniciativas de crecimiento y su impacto en GMV
2. 🏆 **Top 3 iniciativas** por score y por qué son críticas para el crecimiento
3. 📊 **Balance de portfolio**: Distribución entre Growth, Product, Sales
4. ⚠️ **Gaps identificados**: Oportunidades perdidas de crecimiento
5. 💡 **Recomendaciones estratégicas**: 3 acciones concretas priorizadas
6. 🎯 **Impacto en KPIs**: Cómo las iniciativas afectarán GMV, retention, conversión

🔍 ENFÓCATE EN:
- Iniciativas que maximicen GMV y retention
- Balance entre adquisición (droguerías) y activación (sellers)
- Optimización del embudo de conversión
- Experiencia del usuario en ambos portales

SÉ CONCISO, ESTRATÉGICO y ORIENTADO A RESULTADOS. Prioriza insights accionables para el equipo de Growth."""

        messages = [{"role": "system", "content": system_message}]
        
        if context:
            # Contexto más compacto enfocado en Growth
            context_short = f"PORTFOLIO SALUDIA - DATOS GROWTH:\n{context[:LLM_CONTEXT_LIMIT]}..."
            messages.append({"role": "user", "content": context_short})
        
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": GROQ_MODEL,
            "messages": messages,
            "max_tokens": 800,  # Aumentado para análisis más completo
            "temperature": 0.7  # Ligeramente más creativo
        }
        
        response = requests.post(url, headers=headers, json=data, timeout=LLM_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result['choices'][0]['message']['content']
            return {"success": True, "response": ai_response}
        else:
            logger.error(f"LLM API error: {response.status_code}")
            return {"success": False, "error": f"HTTP {response.status_code}", "response": "Error consultando AI."}
    
    except Exception as e:
        logger.error(f"❌ LLM Error: {e}")
        return {"success": False, "error": str(e), "response": "Error técnico del asistente AI."}

def analyze_initiatives_with_llm_fast(initiatives):
    """Analizar iniciativas con LLM optimizado - GROWTH FOCUSED"""
    if not initiatives:
        return "No hay iniciativas para analizar."
    
    try:
        # Estadísticas rápidas
        stats = calculate_statistics_fast(initiatives)
        
        # Contexto compacto con enfoque en Growth
        context_lines = [
            f"SALUDIA MARKETPLACE - PORTFOLIO GROWTH ({stats['total_initiatives']} iniciativas):\n"
        ]
        
        # Stats de Growth primero
        growth_stats = stats.get('growth_stats', {})
        if growth_stats:
            context_lines.extend([
                f"🚀 GROWTH TEAM:",
                f"• {growth_stats['total_growth_initiatives']} iniciativas ({growth_stats['growth_percentage']:.0f}%)",
                f"• Score promedio: {growth_stats['growth_avg_score']:.2f}",
                ""
            ])
            
            # Top Growth initiatives
            for init in growth_stats.get('top_growth_initiatives', [])[:3]:
                context_lines.append(f"• {init['name']} - Score: {init['score']:.2f} - KPI: {init['kpi']}")
        
        context_lines.append("\n🏆 TOP 5 GENERALES:")
        
        # Solo top 5 para reducir contexto
        for i, init in enumerate(stats.get('top_initiatives_by_score', [])[:5], 1):
            status_emoji = get_status_emoji_safe(init.get('status', ''))
            priority_emoji = get_priority_emoji_safe(init.get('score', 0))
            context_lines.append(f"{i}. {priority_emoji} {init['name']} - Score: {init['score']:.2f} ({init['team']}) {status_emoji}")
        
        # Distribución por equipos
        context_lines.append(f"\n👥 EQUIPOS:")
        for team, percentage in list(stats['teams'].items())[:5]:
            count = next((count for t, count in stats['top_teams'] if t == team), 0)
            emphasis = "**" if team == "Growth" else ""
            context_lines.append(f"• {emphasis}{team}{emphasis}: {count} ({percentage:.0f}%)")
        
        # Estados críticos
        context_lines.append(f"\n📊 ESTADOS:")
        for status, count in stats.get('top_statuses', []):
            percentage = stats['statuses'].get(status, 0)
            context_lines.append(f"• {status}: {count} ({percentage:.0f}%)")
        
        context_lines.extend([
            f"\n📈 MÉTRICAS:",
            f"Score promedio: {stats['average_metrics'].get('score', 0):.2f}",
            f"Alcance promedio: {stats['average_metrics'].get('reach', 0):.0f}%"
        ])
        
        context = "\n".join(context_lines)
        
        prompt = """Analiza este portfolio de Saludia con ENFOQUE EN GROWTH. 

🎯 PRIORIDADES:
1. Evaluar iniciativas de Growth y su potencial de GMV
2. Identificar gaps en estrategia de crecimiento
3. Recomendar acciones concretas para maximizar crecimiento
4. Analizar balance entre adquisición y retención

Sé estratégico y orientado a resultados de negocio."""
        
        result = query_llm_optimized(prompt, context)
        return result.get("response", "Error analizando iniciativas.")
        
    except Exception as e:
        logger.error(f"❌ Analysis error: {e}")
        return f"Error en el análisis: {str(e)}. Datos básicos están disponibles."
