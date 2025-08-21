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
        return "Error en el análisis. Datos básicos están disponibles."
