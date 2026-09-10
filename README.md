# BetAI Quant Pro V3

Versão de teste focada em **dados atuais**, baixo consumo de quota e separação clara entre informação ao vivo e histórico.

## O que mudou

- Placar ao vivo e calendário priorizam ESPN para permitir polling curto sem consumir a quota diária da API-Football.
- API-Football é usada para elencos, estatísticas de temporada, odds e dados avançados quando configurada.
- Elencos nunca usam CSV/snapshot local como se fossem atuais.
- IDs de ESPN e API-Football são mantidos em namespaces separados para impedir consultas ao time/partida errados.
- Temporada é calculada dinamicamente por competição.
- Match Center aceita detalhes ESPN quando o jogo veio da ESPN e API-Football quando veio da API-Football.
- Modelo Poisson foi corrigido para normalizar a massa de probabilidade truncada.
- Nenhuma odd, ROI, taxa de acerto, jogador ou partida é inventada.
- A interface pública não inclui métricas de "prova social" sem histórico auditado.

## Secrets no Streamlit Cloud

Em **Settings > Secrets**:

```toml
FOOTBALL_API_KEY = "SUA_CHAVE_API_FOOTBALL"
# opcional, apenas NBA
BALLDONTLIE_API_KEY = "SUA_CHAVE_BALLDONTLIE"
```

Nunca faça commit do `secrets.toml` real.

## Executar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Testes

```bash
python -m py_compile app.py src/sports_data_api.py src/current_model.py src/nba_intelligence.py
python -m unittest discover -s tests -v
```

## Publicação

O pacote entregue inclui `ATUALIZAR_SITE.bat`. Ao executar no Windows ele:

1. cria backup automático do projeto atual na Área de Trabalho;
2. preserva `.git`, `.venv` e Secrets locais;
3. instala a V3;
4. compila e roda os testes;
5. cria commit e envia para `main`;
6. abre o endereço público do Streamlit para teste.

## Observações de cobertura

A ESPN usada como fonte de placar/calendário é uma interface pública sem garantia contratual de estabilidade. Se ela falhar, o sistema tenta a API-Football quando a chave estiver disponível. Dados avançados variam por competição e plano do provedor.

Probabilidades são estimativas estatísticas, não garantia de retorno financeiro.
