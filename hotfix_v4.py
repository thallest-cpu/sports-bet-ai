from pathlib import Path
import hashlib

def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def apply_hotfix(root: Path) -> None:
    path = root / 'src/sports_data_api.py'
    text = path.read_text(encoding="utf-8")
    if _sha(text) != '4281bd4f5adcd6710eaa08c4c99f3e5450a4e2aba094987cdd5abc1e938e078a':
        raise RuntimeError("Versão inesperada para hotfix: " + str(path))
    rows = text.splitlines(keepends=True)
    rows[331:331] = ['\n', '    # Estado agregado: uma liga com falha não deve apagar várias consultas ESPN bem-sucedidas.\n', '    if successful > 0:\n', '        suffix = f"; {len(failures)} liga(s) com falha" if failures else ""\n', '        _set_status("espn", True, f"{successful}/{attempted} competição(ões) consultada(s){suffix}")\n', '    elif attempted > 0:\n', '        _set_status("espn", False, "Não foi possível consultar a ESPN neste momento.")\n', '    else:\n', '        _set_status("espn", False, "Competição sem cobertura ESPN configurada.")\n']
    rows[324:324] = ['        successful += 1\n']
    rows[322:323] = ['        if payload is None:\n', '            failures.append(slug)\n']
    rows[319:319] = ['    attempted = len(slugs)\n', '    successful = 0\n', '    failures: List[str] = []\n']
    rows[194:194] = ['        _set_status("espn", True, f"{slug} disponível (cache)")\n']
    rows[172:173] = ['            _set_status("api_football", False, _friendly_api_error(message))\n']
    rows[119:119] = ['    }\n', '\n', '\n', 'def _friendly_api_error(message: str) -> str:\n', '    """Traduz erros frequentes da API-Football para mensagens úteis ao visitante."""\n', '    raw = str(message or "").strip()\n', '    low = raw.lower()\n', '    quota_terms = ("request limit", "daily limit", "quota", "requests limit", "rate limit")\n', '    if any(term in low for term in quota_terms):\n', '        return "Limite diário da API-Football atingido. Dados avançados voltam quando a cota for renovada."\n', '    if "invalid" in low and ("key" in low or "token" in low):\n', '        return "Chave da API-Football inválida ou não autorizada."\n', '    if "subscription" in low or "plan" in low:\n', '        return "Este recurso não está disponível no plano atual da API-Football."\n', '    return raw or "Falha ao consultar a API-Football."\n', '\n', '\n', 'def football_source_state() -> Dict[str, Any]:\n', '    """Estado consolidado, separando configuração de disponibilidade real."""\n', '    api = dict(_PROVIDER_STATUS["api_football"])\n', '    espn = dict(_PROVIDER_STATUS["espn"])\n', '    configured = api_key_configured()\n', '    usable = bool(api.get("ok") is True or espn.get("ok") is True)\n', '    return {\n', '        "configured": configured,\n', '        "usable": usable,\n', '        "api": api,\n', '        "espn": espn,\n']
    rows[87:88] = ['    for name in names:\n', '        value = os.environ.get(name, "").strip()\n', '        if value:\n', '            return value\n', '    return ""\n']
    rows[82:85] = ['        for name in names:\n', '            value = st.secrets.get(name, "")\n', '            if value:\n', '                return str(value).strip()\n']
    rows[80:80] = ['    """Resolve a chave sem expô-la e aceita nomes legados comuns.\n', '\n', '    O nome oficial continua sendo ``FOOTBALL_API_KEY``. Os aliases existem\n', '    apenas para tornar upgrades de versões antigas tolerantes a configurações\n', '    já salvas no Streamlit Cloud.\n', '    """\n', '    names = ("FOOTBALL_API_KEY", "API_FOOTBALL_KEY", "APISPORTS_KEY")\n']
    text = "".join(rows)
    if _sha(text) != '73e278ac938d34b1b75a47d8f5a86b28146a06587f208a5a71d1e87128601069':
        raise RuntimeError("Falha de integridade após hotfix: " + str(path))
    path.write_text(text, encoding="utf-8")
    path = root / 'v3_app.py'
    text = path.read_text(encoding="utf-8")
    if _sha(text) != 'b4c79c43da89e0d974568cb393f1f11c8815fcf7f0a62371fc40d7e398181a29':
        raise RuntimeError("Versão inesperada para hotfix: " + str(path))
    rows = text.splitlines(keepends=True)
    rows[773:774] = ['    f"<div class=\'source-note\'><b>Fontes:</b> {esc(provider_summary())}. Placar ao vivo prioriza ESPN para preservar a quota diária da API-Football; dados avançados usam API-Football quando disponível. Nenhum CSV histórico é apresentado como dado atual. Página renderizada: {footer_now.strftime(\'%d/%m/%Y %H:%M:%S\')} (Brasília). O horário nos cartões indica a última verificação daquela seção.<br><br><b>Aviso:</b> probabilidades são estimativas estatísticas e não garantem resultados financeiros.</div>",\n']
    rows[740:741] = ['        st.info("NBA ainda não está ativada neste site. O administrador precisa conectar a fonte de dados da NBA antes de liberar jogos e elencos.")\n']
    rows[524:525] = ['            today_state = football_source_state()\n', '            if today_state["espn"].get("ok") is True or today_state["api"].get("ok") is True:\n', '                st.info("Consulta concluída: nenhuma partida encontrada hoje nesta competição.")\n', '            else:\n', '                st.warning("Não foi possível consultar o calendário desta competição agora. Isso não confirma ausência de jogos.")\n']
    rows[495:496] = ['            live_state = football_source_state()\n', '            espn_ok = live_state["espn"].get("ok") is True\n', '            api_ok = live_state["api"].get("ok") is True\n', '            if espn_ok or api_ok:\n', '                st.info("Consulta concluída: nenhuma partida ao vivo encontrada no filtro atual. O painel continuará verificando automaticamente.")\n', '            else:\n', '                st.warning("Não foi possível confirmar partidas ao vivo agora porque as fontes estão indisponíveis. Tente novamente mais tarde.")\n', '            upcoming = get_api_football_fixtures_by_league(\n', '                selected_league_id, season=season, next_games=3\n', '            )\n', '            if upcoming:\n', '                st.markdown("### Próximos jogos da competição selecionada")\n', '                for fx in upcoming[:3]:\n', '                    render_match_card(fx)\n']
    rows[491:493] = ['        c2.metric("Cobertura", "1 liga" if only_selected else f"{len(API_FOOTBALL_LEAGUES)} ligas",\n', '                  help=selected_league_name if only_selected else "Competições monitoradas")\n', '        c3.metric("Dados verificados", now_live.strftime("%H:%M:%S"))\n']
    rows[460:461] = ['    <span class="pill {provider_pill_class()}">{esc(provider_summary())}</span>\n']
    rows[457:458] = ['    <span class="pill live">● APP ONLINE</span>\n']
    rows[419:420] = ['        if api_state.get("ok") is True:\n', '            st.success("API-Football disponível", icon="✅")\n', '        elif api_state.get("ok") is False:\n', '            st.warning("API-Football configurada, mas indisponível agora", icon="⚠️")\n', '        else:\n', '            st.info("API-Football configurada; aguardando primeira validação.", icon="ℹ️")\n']
    rows[418:418] = ['    # Pré-valida a fonte gratuita no carregamento da página. A resposta fica\n', '    # em cache, então isso não gera chamadas repetidas a cada componente.\n', '    try:\n', '        get_api_football_today_fixtures(selected_league_id)\n', '    except Exception:\n', '        pass\n', '\n', '    source_state = football_source_state()\n', '    api_state = source_state["api"]\n']
    rows[396:396] = ['\n', '\n', 'def provider_pill_class() -> str:\n', '    state = football_source_state()\n', '    return "live" if state["usable"] else "warn"\n']
    rows[389:395] = ['    state = football_source_state()\n', '    espn = state["espn"]\n', '    api = state["api"]\n', '\n', '    if espn.get("ok") is True:\n', '        espn_txt = "ESPN OK"\n', '    elif espn.get("ok") is False:\n', '        espn_txt = "ESPN indisponível"\n', '    else:\n', '        espn_txt = "ESPN ainda não verificada"\n', '\n', '    if api.get("ok") is True:\n', '        api_txt = "API-Football OK"\n', '    elif api.get("ok") is False:\n', '        api_txt = "API-Football indisponível"\n', '    elif state["configured"]:\n', '        api_txt = "API-Football configurada"\n', '    else:\n', '        api_txt = "API-Football sem chave"\n']
    rows[34:34] = ['    football_source_state,\n']
    text = "".join(rows)
    if _sha(text) != 'f829ba3ce1eab10f42ce11529e677650adc061dce6fe6ecd9bb7eebe0dbfdba8':
        raise RuntimeError("Falha de integridade após hotfix: " + str(path))
    path.write_text(text, encoding="utf-8")
