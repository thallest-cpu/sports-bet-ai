# BetAI Quant Pro · V5

Streamlit com dados reais, probabilidades transparentes e histórico auditável.
Entrada: app.py na main; código legível, sem pacotes extraídos em tempo de execução.

## Interface
Ao vivo, Hoje, Ontem / Resultados, Times e jogadores, Análise, Tabela e NBA.
Carrosséis com navegação por toque/teclado. Ontem usa o dia civil de Brasília.
Horário vencido sem placar confirmado é expirado; adiados não são encerrados.

## Metodologia
Poisson poisson-season-v1, 1X2 em 90 minutos + acréscimos. Para o mandante:
média dos gols marcados em casa e sofridos fora pelo visitante; cálculo inverso
para o visitante. Mínimo de 3 partidas por recorte, médias limitadas a 0,15–4,5,
grade de 0–14 normalizada. Sem ajuste por lesões, escalações ou força dos rivais;
sem calibração comprovada. Os campos internos xg são médias Poisson, não xG de chutes.
Probabilidade não é acerto comprovado nem garantia de resultado financeiro.

## Histórico
Primeira previsão por partida/modelo preservada, com instante UTC, início previsto,
ID do provedor, versão, probabilidades, seleção, estatísticas e hash SHA-256.
Empates entre probabilidades seguem casa/empate/fora. Sem registro retroativo.
Acerto/Erro somente após resultado regulamentar confirmado. Prorrogação e pênaltis
exigem placar de 90 minutos. Cancelados/abandonados/administrativos são anulados.
Correções do provedor acrescentam revisões sem apagar evidências anteriores.
Taxa observada = acertos / apuradas; exclui anuladas e pendentes. Exportação JSON.
Hash não é certificação externa nem proteção contra administrador do banco.

## Secrets fora do GitHub
Configure em Streamlit > Settings > Secrets ou variáveis de ambiente:

```toml
FOOTBALL_API_KEY = "<chave>"
BALLDONTLIE_API_KEY = "<opcional>"
BETAI_DATABASE_URL = "postgresql://<usuario>:<senha>@<host>/<banco>?sslmode=require"
FOOTBALL_DAILY_BUDGET = "90"
LICENSED_PHOTO_SOURCES = ""
BETAI_MONITORED_LEAGUES = "71"
```

Sem PostgreSQL, a aplicação NÃO grava previsões nem apresenta taxa de acerto.
SQLite só é selecionado explicitamente pela classe de testes, nunca como fallback
em produção. O disco do Streamlit não garante persistência. Use banco dedicado,
TLS, usuário restrito ao schema e backups no provedor. Schema criado na conexão.
A integração precisa de teste no banco real antes de declarar o histórico ativo.
Nunca versionar secrets.toml, .env, URLs autenticadas ou chaves.

## Operação automática
Análise registra a previsão elegível consultada. Hoje/Resultados apuram registros
a cada cinco minutos de uso. Para operar sem visitantes, configure um agendador
externo com `python worker.py` e os mesmos Secrets. O worker revisa pendentes e
resultados dos últimos sete dias, e registra próximas partidas dentro de 48h.
Somente ligas em BETAI_MONITORED_LEAGUES. Nenhum agendador ativado por padrão.
O sono do Streamlit impede garantir execução contínua dentro do site.
Worker e site em hosts separados precisam de quota compartilhada ou orçamentos
somados inferiores à cota do provedor. A proteção local é por implantação.

## Fontes e quota
- ESPN: placares/calendário TTL 15–120s, tabela/elenco somente com temporada
  confirmada. Interface pública sem contrato de estabilidade. IDs separados.
- API-Football: estatísticas 15min, ranking 1h, elenco 6h, detalhes 60s. Mostra
  temporada e instante de consulta, sem garantir atualização interna do provedor.
- NBA: BALLDONTLIE, jogadores ativos; cobertura e endpoints dependem do plano.
- Fotos desativadas por padrão. Somente recebidas da API, HTTPS no host
  media.api-sports.io, após comprovação de direitos e configuração da fonte
  API-Football em LICENSED_PHOTO_SOURCES. Assinatura da API não prova licença.
- Estado operacional/degradado/cota esgotada; configuração não comprova saúde.
- Cache compartilhado entre visitantes e reruns do processo. Reservas locais
  atômicas em SQLite enquanto o disco existir. Limite padrão 90, ajustável;
  não pressupõe conhecimento do plano contratado. Cota diária bloqueia até
  00:00 UTC para API-Sports direta; falha de rede 5min; HTTP 429 por 60s.
- Atualização manual preserva cache pago e quota. Dados ausentes não viram zeros.

## Testes e execução
```sh
pip install -r requirements.txt
python -m compileall -q app.py src worker.py
python -m unittest discover -s tests -v
streamlit run app.py
```
Dados sintéticos apenas em testes, nunca no site. Testes cobrem fronteira de
início, fusos, persistência, imutabilidade, deduplicação, revisões de resultado,
placar regulamentar, ausência de dados, namespaces, fotos, quota e sete páginas
sem fontes. PostgreSQL e dados pagos reais exigem conexão para validação final.

## Publicação e reversão
Backup remoto: backup/pre-finalizacao-20260910. Para rollback, reverta o commit
V5 na main e aguarde o redeploy. Não reescreva o histórico nem exclua o banco.
Contratos em src/extensions.py preparam planos e eventos, sem cobrança, assinatura,
destinatários ou envio WhatsApp habilitados.

## Referências
- https://www.api-football.com/documentation-v3
- https://www.api-football.com/terms
- https://docs.balldontlie.io/
- https://docs.streamlit.io/develop/concepts/connections/connecting-to-data
- https://docs.streamlit.io/deploy/concepts/secrets
