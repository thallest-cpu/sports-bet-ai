const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
  cors: {
    origin: '*',
    methods: ['GET', 'POST']
  }
});

// Banco de dados em memória simulando jogos ativos com telemetria espacial (Canvas/SVG)
const jogosEmAndamento = {
  '123': {
    matchId: '123',
    timeCasa: 'Flamengo',
    timeVisitante: 'Palmeiras',
    placar: '1 x 0',
    tempo: "38'",
    stats: {
      chutesGolCasa: 3,
      chutesGolFora: 1,
      chutesTotalCasa: 7,
      chutesTotalFora: 4,
      posseCasa: 58,
      posseFora: 42,
      escanteiosCasa: 4,
      escanteiosFora: 2,
      ataquesPerigososCasa: 32,
      ataquesPerigososFora: 18,
      cartoesAmarelosCasa: 1,
      cartoesAmarelosFora: 2,
      cartoesVermelhosCasa: 0,
      cartoesVermelhosFora: 0,
      xgCasa: 1.42,
      xgFora: 0.38
    },
    odds: { casa: 1.85, empate: 3.20, fora: 4.10, variacaoCasa: 'neutral' },
    ultimoEvento: {
      tipo: 'SAFE_POSSESSION',
      texto: 'Bola em jogo no meio campo',
      time: 'casa',
      posse: 'casa',
      bolaX: 50,
      bolaY: 30,
      direcaoAtaque: 'direita',
      intensidade: 'baixa'
    }
  }
};

// Gerenciamento de conexões dos clientes
io.on('connection', (socket) => {
  console.log(`Cliente conectado: ${socket.id}`);

  // Cliente solicita entrar na sala de um jogo específico
  socket.on('join_match', ({ matchId }) => {
    const roomId = `match_${matchId}`;
    socket.join(roomId);
    console.log(`Socket ${socket.id} entrou no jogo ${matchId}`);

    // Envia o estado atual do jogo imediatamente ao conectar
    if (!jogosEmAndamento[matchId]) {
      jogosEmAndamento[matchId] = {
        matchId: String(matchId),
        timeCasa: 'Mandante',
        timeVisitante: 'Visitante',
        placar: '0 x 0',
        tempo: "15'",
        stats: { chutesGolCasa: 1, chutesGolFora: 0, posseCasa: 52, posseFora: 48, escanteiosCasa: 2, escanteiosFora: 1, ataquesPerigososCasa: 15, ataquesPerigososFora: 12, xgCasa: 0.45, xgFora: 0.20 },
        odds: { casa: 2.10, empate: 3.10, fora: 3.40, variacaoCasa: 'neutral' },
        ultimoEvento: { tipo: 'SAFE_POSSESSION', texto: 'Bola em disputa no meio', time: 'casa', posse: 'casa', bolaX: 50, bolaY: 30, direcaoAtaque: 'direita' }
      };
    }
    socket.emit('match_update', jogosEmAndamento[matchId]);
  });

  // Cliente sai da sala do jogo
  socket.on('leave_match', ({ matchId }) => {
    socket.leave(`match_${matchId}`);
    console.log(`Socket ${socket.id} saiu do jogo ${matchId}`);
  });

  // Simulação de eventos disparados pelo frontend
  socket.on('simulate_pitch_event', ({ matchId, eventType, team }) => {
    const jogo = jogosEmAndamento[matchId];
    if (jogo) {
      const isHome = team !== 'fora';
      if (eventType === 'DANGEROUS_ATTACK') {
        jogo.stats.ataquesPerigososCasa += isHome ? 1 : 0;
        jogo.stats.ataquesPerigososFora += isHome ? 0 : 1;
        jogo.ultimoEvento = {
          tipo: 'DANGEROUS_ATTACK',
          texto: `⚡ Ataque Perigoso - ${isHome ? jogo.timeCasa : jogo.timeVisitante}`,
          time: isHome ? 'casa' : 'fora',
          posse: isHome ? 'casa' : 'fora',
          bolaX: isHome ? 82 : 18,
          bolaY: 28,
          direcaoAtaque: isHome ? 'direita' : 'esquerda',
          intensidade: 'perigo_maximo'
        };
      } else if (eventType === 'SHOT') {
        jogo.stats.chutesGolCasa += isHome ? 1 : 0;
        jogo.stats.chutesGolFora += isHome ? 0 : 1;
        jogo.ultimoEvento = {
          tipo: 'SHOT_ON_TARGET',
          texto: `🎯 Chute a Gol Defendido! (${isHome ? jogo.timeCasa : jogo.timeVisitante})`,
          time: isHome ? 'casa' : 'fora',
          posse: isHome ? 'casa' : 'fora',
          bolaX: isHome ? 94 : 6,
          bolaY: 30,
          direcaoAtaque: isHome ? 'direita' : 'esquerda',
          intensidade: 'alta'
        };
      } else if (eventType === 'CORNER') {
        jogo.stats.escanteiosCasa += isHome ? 1 : 0;
        jogo.stats.escanteiosFora += isHome ? 0 : 1;
        jogo.ultimoEvento = {
          tipo: 'CORNER',
          texto: `🚩 Escanteio a Favor - ${isHome ? jogo.timeCasa : jogo.timeVisitante}`,
          time: isHome ? 'casa' : 'fora',
          posse: isHome ? 'casa' : 'fora',
          bolaX: isHome ? 96 : 4,
          bolaY: 4,
          direcaoAtaque: isHome ? 'direita' : 'esquerda',
          intensidade: 'media'
        };
      } else if (eventType === 'GOAL') {
        const parts = jogo.placar.split('x');
        let h = parseInt(parts[0]) || 0;
        let a = parseInt(parts[1]) || 0;
        if (isHome) h++; else a++;
        jogo.placar = `${h} x ${a}`;
        jogo.ultimoEvento = {
          tipo: 'GOAL',
          texto: `⚽ GOOOOOOOL DO ${isHome ? jogo.timeCasa.toUpperCase() : jogo.timeVisitante.toUpperCase()}!`,
          time: isHome ? 'casa' : 'fora',
          posse: isHome ? 'casa' : 'fora',
          bolaX: isHome ? 98 : 2,
          bolaY: 30,
          direcaoAtaque: isHome ? 'direita' : 'esquerda',
          intensidade: 'gol'
        };
      }
      io.to(`match_${matchId}`).emit('match_update', jogo);
    }
  });

  socket.on('disconnect', () => {
    console.log(`Cliente desconectado: ${socket.id}`);
  });
});

// Simulação de atualização de dados e envio em tempo real
setInterval(() => {
  Object.keys(jogosEmAndamento).forEach((matchId) => {
    const jogo = jogosEmAndamento[matchId];
    if (jogo) {
      // Simula pequenas variações nas odds e estatísticas
      const delta = +(Math.random() * 0.08 - 0.04).toFixed(2);
      const oldOdd = jogo.odds.casa;
      jogo.odds.casa = Math.max(1.05, +(oldOdd + delta).toFixed(2));
      jogo.odds.variacaoCasa = jogo.odds.casa > oldOdd ? 'up' : (jogo.odds.casa < oldOdd ? 'down' : 'neutral');

      const isHome = Math.random() > 0.45;
      const eventos = [
        { tipo: 'DANGEROUS_ATTACK', texto: `⚡ Ataque Perigoso - ${isHome ? jogo.timeCasa : jogo.timeVisitante}`, bolaX: isHome ? 78 : 22, bolaY: 28, dir: isHome ? 'direita' : 'esquerda', intensidade: 'perigo_maximo' },
        { tipo: 'CORNER', texto: `🚩 Escanteio - ${isHome ? jogo.timeCasa : jogo.timeVisitante}`, bolaX: isHome ? 96 : 4, bolaY: 5, dir: isHome ? 'direita' : 'esquerda', intensidade: 'media' },
        { tipo: 'SHOT_ON_TARGET', texto: `🎯 Finalização no Alvo (${isHome ? jogo.timeCasa : jogo.timeVisitante})`, bolaX: isHome ? 92 : 8, bolaY: 30, dir: isHome ? 'direita' : 'esquerda', intensidade: 'alta' },
        { tipo: 'SAFE_POSSESSION', texto: `Posse de bola no meio campo (${isHome ? jogo.timeCasa : jogo.timeVisitante})`, bolaX: 50, bolaY: 30, dir: isHome ? 'direita' : 'esquerda', intensidade: 'baixa' }
      ];

      const sel = eventos[Math.floor(Math.random() * eventos.length)];
      jogo.ultimoEvento = {
        tipo: sel.tipo,
        texto: sel.texto,
        time: isHome ? 'casa' : 'fora',
        posse: isHome ? 'casa' : 'fora',
        bolaX: sel.bolaX,
        bolaY: sel.bolaY,
        direcaoAtaque: sel.dir,
        intensidade: sel.intensidade
      };

      if (sel.tipo === 'DANGEROUS_ATTACK') {
        if (isHome) jogo.stats.ataquesPerigososCasa++; else jogo.stats.ataquesPerigososFora++;
      } else if (sel.tipo === 'CORNER') {
        if (isHome) jogo.stats.escanteiosCasa++; else jogo.stats.escanteiosFora++;
      } else if (sel.tipo === 'SHOT_ON_TARGET') {
        if (isHome) jogo.stats.chutesGolCasa++; else jogo.stats.chutesGolFora++;
      }

      // Dispara a atualização SOMENTE para os usuários assistindo a essa partida
      io.to(`match_${matchId}`).emit('match_update', jogo);
    }
  });
}, 3000);

const PORT = process.env.PORT || 4000;
server.listen(PORT, () => {
  console.log(`Servidor WebSocket rodando na porta ${PORT}`);
});
