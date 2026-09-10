# BetAI Quant Pro — versão de teste limpa

Painel Streamlit com dados atuais da API-Football e fallback ESPN limitado para fixtures.

## Dados atuais
- Jogos ao vivo globais (`fixtures?live=all`)
- Jogos de hoje por competição
- Elencos registrados atuais (`players/squads`)
- Eventos, estatísticas, escalações e jogadores por partida
- Classificação atual
- Próximos jogos
- Modelo Poisson transparente usando estatísticas da temporada atual
- Odds reais quando disponibilizadas pela API; nenhuma odd fictícia é criada

## Secrets no Streamlit Cloud
Configure em **Settings > Secrets**:

```toml
FOOTBALL_API_KEY = "..."
# opcional
BALLDONTLIE_API_KEY = "..."
```

## Executar localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Observação
O fallback ESPN cobre fixtures/placares básicos de competições configuradas. Elencos e detalhes avançados não usam snapshot local antigo; quando a API-Football não está disponível, a interface informa que o dado está indisponível.
