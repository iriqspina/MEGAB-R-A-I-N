/* Mapa do harness (cidade MegaBrain) · v1.1 · 261018 (ajuste r1 da crítica de design)
   Fonte: motor/modelos/harness-mapa/mapa.js · embutido por bin/mb-harness-mapa.py
   Núcleo sem DOM (aplicar/diff/medir/desenho) exportado para teste no Node;
   interface só roda com document. Edições ficam como REMENDOS na chave
   'mb-harness-mapa:v1' (no app: rascunho do visor). Sem rede e sem caixas de
   confirmação do navegador (o visor do app as ignora): remover tem Desfazer. */
(function (raiz) {
  'use strict';
  var CHAVE = 'mb-harness-mapa:v1';
  var CHAVE_MOV = 'mb-harness-mapa:movimento';
  var LIMITE_CHAVE = 50000, LIMITE_TOTAL = 128000, GAP = 10;
  var CAMPOS = {
    estacao: ['nome', 'descricao', 'quem', 'condicao', 'bairro', 'tecnico'],
    linha: ['nome', 'cor', 'gatilho', 'frequencia'],
    bairro: ['nome', 'descricao', 'cor']
  };
  var PALETA = ['#1CB0F6', '#FFC800', '#58CC02', '#CE82FF', '#7C8CFF', '#FF82C4', '#2EC4B6', '#FF4B4B', '#A0E426', '#00CD9C', '#B983FF', '#FF6FB5'];

  /* ================= núcleo (sem DOM) ================= */
  function clonar(o) { return JSON.parse(JSON.stringify(o)); }
  function porId(lista, id) { for (var i = 0; i < (lista || []).length; i++) if (lista[i].id === id) return lista[i]; return null; }
  function erro(msg) { var e = new Error(msg); e.mapa = true; return e; }
  function idValido(id) { return typeof id === 'string' && /^[a-z0-9_]{1,40}$/.test(id); }
  function num(v, nome) {
    var n = Number(v);
    if (!isFinite(n)) throw erro('Posição inválida' + (nome ? ' em ' + nome : '') + '.');
    return Math.max(0, Math.min(3000, Math.round(n)));
  }
  function exigeEst(m, id) { var e = porId(m.estacoes, id); if (!e) throw erro('Estação não encontrada: ' + id + '.'); return e; }
  function exigeEstLinha(m, id) {
    var e = exigeEst(m, id);
    if (e.tipo && e.tipo !== 'estacao') throw erro('“' + e.nome + '” é placa ou depósito e não entra em linha.');
    return e;
  }
  function exigeLinha(m, id) { var l = porId(m.linhas, id); if (!l) throw erro('Linha não encontrada: ' + id + '.'); return l; }
  function semDuplicata(lista) { var v = {}; for (var i = 0; i < lista.length; i++) { if (v[lista[i]]) throw erro('A estação ' + lista[i] + ' aparece duas vezes na mesma linha.'); v[lista[i]] = 1; } }
  function ajustarLinha(m, l) {
    if (l.esperas) l.esperas = l.esperas.filter(function (s) { return l.estacoes.indexOf(s) >= 0; });
    if (l.curva_cedo) l.curva_cedo = l.curva_cedo.filter(function (s) { return l.estacoes.indexOf(s) >= 0; });
    if (l.volta) {
      var a = l.estacoes.indexOf(l.volta.de), b = l.estacoes.indexOf(l.volta.para);
      if (a < 0 || b < 0 || b >= a) delete l.volta;
    }
    if (!l.volta) (m.cenarios || []).forEach(function (c) { if (c.linha === l.id && c.resultado === 'volta_1x') c.resultado = 'aprovado'; });
    var temEspera = l.esperas && l.esperas.length;
    if (!temEspera) (m.cenarios || []).forEach(function (c) { if (c.linha === l.id && c.resultado === 'espera') c.resultado = 'aprovado'; });
  }

  function palavras(t) { return String(t || '').split(/\s+/).filter(Boolean).length; }
  function checarTexto(campo, v) {
    if (campo === 'nome' && (palavras(v) > 3 || v.length > 28)) throw erro('Use até 3 palavras no nome; os detalhes vão na descrição.');
    if (campo === 'descricao' && palavras(v) > 20) throw erro('A descrição passa de 20 palavras. Encurte para caber no mapa.');
  }
  function aplicarUm(m, p) {
    if (!p || typeof p !== 'object') throw erro('Remendo inválido.');
    var e, l, i;
    m.notas = m.notas || []; m.ligacoes = m.ligacoes || []; m.cenarios = m.cenarios || [];
    switch (p.op) {
      case 'mover':
        e = exigeEst(m, p.estacao); e.x = num(p.x, e.nome); e.y = num(p.y, e.nome); break;
      case 'editar': {
        var lista = p.tipo === 'estacao' ? m.estacoes : p.tipo === 'linha' ? m.linhas : p.tipo === 'bairro' ? m.bairros : null;
        if (!lista) throw erro('Tipo de edição desconhecido: ' + p.tipo + '.');
        var alvo = porId(lista, p.id);
        if (!alvo) throw erro('Não encontrei ' + p.tipo + ' ' + p.id + '.');
        if (CAMPOS[p.tipo].indexOf(p.campo) < 0) throw erro('Campo que não se edita pelo mapa: ' + p.campo + '.');
        var v = String(p.valor == null ? '' : p.valor).trim();
        if (p.campo === 'nome' && !v) throw erro('O nome não pode ficar vazio.');
        if (p.campo === 'quem' && !(m.responsaveis || {})[v]) throw erro('Responsável desconhecido: ' + v + '.');
        if (p.campo === 'bairro' && !porId(m.bairros, v)) throw erro('Bairro desconhecido: ' + v + '.');
        if (p.campo === 'cor' && !/^#[0-9a-fA-F]{6}$/.test(v)) throw erro('Cor inválida: use #RRGGBB.');
        if (v.length > 400) throw erro('Texto longo demais (máximo 400 caracteres).');
        if (p.tipo === 'estacao') checarTexto(p.campo, v);
        alvo[p.campo] = v; break;
      }
      case 'nova_estacao': {
        if (!idValido(p.id)) throw erro('Id de estação inválido: ' + p.id + '.');
        if (porId(m.estacoes, p.id)) throw erro('Já existe uma estação com o id ' + p.id + '.');
        var ref = p.depois_de ? exigeEst(m, p.depois_de) : null;
        var bz = p.bairro || (ref ? ref.bairro : (porId(m.bairros, 'centro') ? 'centro' : m.bairros[0].id));
        if (!porId(m.bairros, bz)) throw erro('Bairro desconhecido: ' + bz + '.');
        var quem = p.quem || 'escolhida';
        if (!(m.responsaveis || {})[quem]) quem = Object.keys(m.responsaveis || {})[0];
        var nova = {
          id: p.id, nome: String(p.nome || 'Nova etapa').trim() || 'Nova etapa', bairro: bz,
          x: num(p.x != null ? p.x : (ref ? ref.x + 55 : 600)), y: num(p.y != null ? p.y : (ref ? ref.y : 350)),
          descricao: String(p.descricao || 'Etapa nova criada no mapa. Descreva o que ela faz.'),
          quem: quem, condicao: String(p.condicao || 'a definir'),
          arquivos: [], verificado: false, nota_prova: 'Criada no mapa; ainda não existe no harness.'
        };
        checarTexto('nome', nova.nome); checarTexto('descricao', nova.descricao);
        m.estacoes.push(nova);
        if (p.linha) {
          l = exigeLinha(m, p.linha);
          i = ref ? l.estacoes.indexOf(ref.id) : -1;
          if (ref && i < 0) throw erro('A estação ' + ref.id + ' não está na linha ' + l.id + '.');
          l.estacoes.splice(i + 1, 0, nova.id);
        }
        break;
      }
      case 'remover_estacao': {
        e = exigeEst(m, p.id);
        m.linhas.forEach(function (ln) {
          if (ln.estacoes.indexOf(p.id) >= 0 && ln.estacoes.length <= 2) throw erro('A linha “' + ln.nome + '” ficaria com menos de 2 estações. Remova a linha antes.');
        });
        m.estacoes.splice(m.estacoes.indexOf(e), 1);
        m.linhas.forEach(function (ln) { ln.estacoes = ln.estacoes.filter(function (s) { return s !== p.id; }); ajustarLinha(m, ln); });
        m.ligacoes = m.ligacoes.filter(function (g) { return g.de !== p.id && g.para !== p.id; });
        m.notas = m.notas.filter(function (n) { return n.alvo !== 'estacao:' + p.id; });
        break;
      }
      case 'nova_linha': {
        if (!idValido(p.id)) throw erro('Id de linha inválido: ' + p.id + '.');
        if (porId(m.linhas, p.id)) throw erro('Já existe uma linha com o id ' + p.id + '.');
        var ests = (p.estacoes || []).slice();
        if (ests.length < 2) throw erro('Uma linha precisa de pelo menos 2 estações.');
        ests.forEach(function (s) { exigeEstLinha(m, s); }); semDuplicata(ests);
        var cor = p.cor || '#8C9EFF';
        if (!/^#[0-9a-fA-F]{6}$/.test(cor)) throw erro('Cor inválida: use #RRGGBB.');
        m.linhas.push({ id: p.id, nome: String(p.nome || 'Nova linha').trim() || 'Nova linha', cor: cor,
          gatilho: String(p.gatilho || 'A definir.'), frequencia: String(p.frequencia || 'A definir.'), estacoes: ests, verificado: false });
        if (!porId(m.cenarios, 'c_' + p.id)) m.cenarios.push({ id: 'c_' + p.id, linha: p.id, pedido: 'Pedido de exemplo', resultado: 'aprovado' });
        break;
      }
      case 'remover_linha': {
        l = exigeLinha(m, p.id);
        if (m.linhas.length <= 1) throw erro('O mapa precisa de pelo menos uma linha.');
        m.linhas.splice(m.linhas.indexOf(l), 1);
        m.cenarios = m.cenarios.filter(function (c) { return c.linha !== p.id; });
        m.notas = m.notas.filter(function (n) { return n.alvo !== 'linha:' + p.id; });
        if (m.preferencias && !porId(m.cenarios, m.preferencias.cenario_inicial) && m.cenarios[0]) m.preferencias.cenario_inicial = m.cenarios[0].id;
        break;
      }
      case 'ordem': {
        l = exigeLinha(m, p.linha);
        var ord = (p.estacoes || []).slice();
        if (ord.length < 2) throw erro('Uma linha precisa de pelo menos 2 estações.');
        ord.forEach(function (s) { exigeEstLinha(m, s); }); semDuplicata(ord);
        l.estacoes = ord; ajustarLinha(m, l); break;
      }
      case 'incluir': {
        l = exigeLinha(m, p.linha); e = exigeEstLinha(m, p.estacao);
        if (l.estacoes.indexOf(e.id) >= 0) throw erro('“' + e.nome + '” já está na linha “' + l.nome + '”.');
        i = p.depois_de ? l.estacoes.indexOf(p.depois_de) : -1;
        if (p.depois_de && i < 0) throw erro('A estação ' + p.depois_de + ' não está na linha ' + l.id + '.');
        l.estacoes.splice(i + 1, 0, e.id); break;
      }
      case 'nota': {
        var texto = String(p.texto || '').trim();
        if (!texto) throw erro('A nota está vazia.');
        if (texto.length > 1000) throw erro('Nota longa demais (máximo 1000 caracteres).');
        var mt = /^(estacao|linha|bairro):(.+)$/.exec(p.alvo || '');
        if (p.alvo !== 'mapa') {
          if (!mt) throw erro('Alvo de nota inválido: ' + p.alvo + '.');
          var col = mt[1] === 'estacao' ? m.estacoes : mt[1] === 'linha' ? m.linhas : m.bairros;
          if (!porId(col, mt[2])) throw erro('A nota aponta para algo que não existe: ' + p.alvo + '.');
        }
        var nid = p.id || ('n' + (m.notas.length + 1));
        if (!idValido(nid) || porId(m.notas, nid)) throw erro('Id de nota inválido ou repetido: ' + nid + '.');
        m.notas.push({ id: nid, alvo: p.alvo, texto: texto, em: String(p.em || ''), quem: 'voce' });
        break;
      }
      case 'remover_nota': {
        var n = porId(m.notas, p.id); if (!n) throw erro('Nota não encontrada: ' + p.id + '.');
        m.notas.splice(m.notas.indexOf(n), 1); break;
      }
      default: throw erro('Remendo desconhecido: ' + p.op + '.');
    }
    return m;
  }

  function aplicar(base, ops, tolerante) {
    var m = clonar(base), ignorados = [], aceitos = [];
    (ops || []).forEach(function (p) {
      var copia = clonar(m);
      try { aplicarUm(m, p); aceitos.push(p); }
      catch (e) { if (!tolerante) throw e; m = copia; ignorados.push({ op: p, erro: e.message }); }
    });
    return { modelo: m, ignorados: ignorados, aceitos: aceitos };
  }

  function mapa(lista) { var r = {}; (lista || []).forEach(function (x) { r[x.id] = x; }); return r; }
  function diff(base, atual) {
    var ops = [], bE = mapa(base.estacoes), aE = mapa(atual.estacoes), bL = mapa(base.linhas), aL = mapa(atual.linhas);
    base.linhas.forEach(function (l) { if (!aL[l.id]) ops.push({ op: 'remover_linha', id: l.id }); });
    atual.estacoes.forEach(function (e) {
      if (!bE[e.id]) ops.push({ op: 'nova_estacao', id: e.id, nome: e.nome, bairro: e.bairro, x: e.x, y: e.y, quem: e.quem, descricao: e.descricao, condicao: e.condicao });
    });
    atual.linhas.forEach(function (l) {
      var b = bL[l.id];
      if (!b) ops.push({ op: 'nova_linha', id: l.id, nome: l.nome, cor: l.cor, gatilho: l.gatilho, frequencia: l.frequencia, estacoes: l.estacoes.slice() });
      else if (JSON.stringify(b.estacoes) !== JSON.stringify(l.estacoes)) ops.push({ op: 'ordem', linha: l.id, estacoes: l.estacoes.slice() });
    });
    base.estacoes.forEach(function (e) { if (!aE[e.id]) ops.push({ op: 'remover_estacao', id: e.id }); });
    atual.estacoes.forEach(function (e) {
      var b = bE[e.id]; if (!b) return;
      if (b.x !== e.x || b.y !== e.y) ops.push({ op: 'mover', estacao: e.id, x: e.x, y: e.y });
      CAMPOS.estacao.forEach(function (c) { if ((b[c] || '') !== (e[c] || '')) ops.push({ op: 'editar', tipo: 'estacao', id: e.id, campo: c, valor: e[c] || '' }); });
    });
    atual.linhas.forEach(function (l) {
      var b = bL[l.id]; if (!b) return;
      CAMPOS.linha.forEach(function (c) { if ((b[c] || '') !== (l[c] || '')) ops.push({ op: 'editar', tipo: 'linha', id: l.id, campo: c, valor: l[c] || '' }); });
    });
    var bB = mapa(base.bairros);
    atual.bairros.forEach(function (z) {
      var b = bB[z.id]; if (!b) return;
      CAMPOS.bairro.forEach(function (c) { if ((b[c] || '') !== (z[c] || '')) ops.push({ op: 'editar', tipo: 'bairro', id: z.id, campo: c, valor: z[c] || '' }); });
    });
    var bN = mapa(base.notas), aN = mapa(atual.notas);
    (atual.notas || []).forEach(function (n) { if (!bN[n.id]) ops.push({ op: 'nota', id: n.id, alvo: n.alvo, texto: n.texto, em: n.em || '' }); });
    (base.notas || []).forEach(function (n) { if (!aN[n.id]) ops.push({ op: 'remover_nota', id: n.id }); });
    return ops;
  }

  function nomeDe(m, tipo, id) {
    var x = porId(tipo === 'linha' ? m.linhas : tipo === 'bairro' ? m.bairros : m.estacoes, id);
    return x ? x.nome : id;
  }
  var ROT_CAMPO = { nome: 'o nome', descricao: 'a descrição', quem: 'quem faz', condicao: 'a condição', bairro: 'o bairro', tecnico: 'o termo técnico', cor: 'a cor', gatilho: 'o gatilho', frequencia: 'a frequência' };
  function resumo(ops, base, atual) {
    return ops.map(function (p) {
      switch (p.op) {
        case 'mover': return 'Moveu a estação “' + nomeDe(atual, 'estacao', p.estacao) + '” no desenho.';
        case 'editar': {
          var antes = porId(p.tipo === 'linha' ? base.linhas : p.tipo === 'bairro' ? base.bairros : base.estacoes, p.id);
          var a = antes ? (antes[p.campo] || '') : '';
          return 'Mudou ' + (ROT_CAMPO[p.campo] || p.campo) + ' de ' + (p.tipo === 'linha' ? 'linha' : p.tipo === 'bairro' ? 'bairro' : 'estação') + ' “' + (antes ? antes.nome : p.id) + '”: “' + a + '” → “' + p.valor + '”.';
        }
        case 'nova_estacao': return 'Criou a estação “' + p.nome + '” (bairro ' + nomeDe(atual, 'bairro', p.bairro) + ').';
        case 'remover_estacao': return 'Removeu a estação “' + nomeDe(base, 'estacao', p.id) + '”.';
        case 'nova_linha': return 'Criou a linha “' + p.nome + '” com ' + p.estacoes.length + ' estações.';
        case 'remover_linha': return 'Removeu a linha “' + nomeDe(base, 'linha', p.id) + '”.';
        case 'ordem': return 'Mudou a ordem da linha “' + nomeDe(atual, 'linha', p.linha) + '”: ' + p.estacoes.map(function (s) { return nomeDe(atual, 'estacao', s); }).join(' → ') + '.';
        case 'incluir': return 'Incluiu “' + nomeDe(atual, 'estacao', p.estacao) + '” na linha “' + nomeDe(atual, 'linha', p.linha) + '”.';
        case 'nota': {
          var mt = /^(estacao|linha|bairro):(.+)$/.exec(p.alvo || '');
          return 'Nota de arquitetura' + (mt ? ' em “' + nomeDe(atual, mt[1], mt[2]) + '”' : '') + ': “' + p.texto + '”.';
        }
        case 'remover_nota': return 'Apagou a nota ' + p.id + '.';
        default: return 'Mudança ' + p.op + '.';
      }
    });
  }

  /* custo que o servidor do app mede (json.dumps ASCII: acento vale 6) */
  function custoServidor(s) {
    var n = 2;
    for (var i = 0; i < s.length; i++) {
      var c = s.charCodeAt(i);
      if (c === 34 || c === 92) n += 2;
      else if (c < 32) n += (c === 8 || c === 9 || c === 10 || c === 12 || c === 13) ? 2 : 6;
      else if (c > 127) n += 6;
      else n += 1;
    }
    return n;
  }
  function custoArmazenamento(par) { // par: [[chave, valor], ...] como json.dumps(dict) com separadores ', ' e ': '
    var n = 2;
    par.forEach(function (kv, i) { n += custoServidor(kv[0]) + 2 + custoServidor(kv[1]) + (i ? 2 : 0); });
    return n;
  }
  function hash(s) { var h = 0x811c9dc5; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; } return ('0000000' + h.toString(16)).slice(-8); }

  /* desenho: faixas paralelas por estação (slots) + curvas suaves */
  function slotsDe(m) {
    var r = {};
    m.estacoes.forEach(function (e) { r[e.id] = []; });
    m.linhas.forEach(function (l) { l.estacoes.forEach(function (s) { if (r[s] && r[s].indexOf(l.id) < 0) r[s].push(l.id); }); });
    return r;
  }
  function pontoNaLinha(m, sl, eId, lId) {
    var e = porId(m.estacoes, eId), ls = sl[eId] || [lId], k = ls.length, i = Math.max(0, ls.indexOf(lId));
    return { x: e.x, y: e.y + (i - (k - 1) / 2) * GAP };
  }
  function f(n) { return Math.round(n * 10) / 10; }
  function segmento(A, B, cedo) {
    var dx = B.x - A.x, dy = B.y - A.y, ax = Math.abs(dx);
    if (Math.abs(dy) < 0.5 || ax < 1) return ' L' + f(B.x) + ' ' + f(B.y);
    var s = dx >= 0 ? 1 : -1, L = Math.min(ax, Math.max(80, Math.abs(dy) * 1.8));
    if (cedo) {
      var x1 = A.x + s * L;
      return ' C' + f(A.x + s * L / 2) + ' ' + f(A.y) + ' ' + f(A.x + s * L / 2) + ' ' + f(B.y) + ' ' + f(x1) + ' ' + f(B.y) + (ax > L ? ' L' + f(B.x) + ' ' + f(B.y) : '');
    }
    var x0 = B.x - s * L;
    return (ax > L ? ' L' + f(x0) + ' ' + f(A.y) : '') + ' C' + f(x0 + s * L / 2) + ' ' + f(A.y) + ' ' + f(x0 + s * L / 2) + ' ' + f(B.y) + ' ' + f(B.x) + ' ' + f(B.y);
  }
  function caminhosDaLinha(m, sl, l) {
    var pts = l.estacoes.map(function (s) { return pontoNaLinha(m, sl, s, l.id); });
    var cedo = l.curva_cedo || [], segs = [], d = 'M' + f(pts[0].x) + ' ' + f(pts[0].y);
    for (var i = 1; i < pts.length; i++) {
      var sg = segmento(pts[i - 1], pts[i], cedo.indexOf(l.estacoes[i - 1]) >= 0);
      segs.push('M' + f(pts[i - 1].x) + ' ' + f(pts[i - 1].y) + sg); d += sg;
    }
    var volta = null;
    if (l.volta) {
      var a = pts[l.estacoes.indexOf(l.volta.de)], b = pts[l.estacoes.indexOf(l.volta.para)];
      var dv = l.volta.lado === 'cima' ? -42 : 42;
      if (a && b) volta = 'M' + f(a.x) + ' ' + f(a.y) + ' C' + f(a.x) + ' ' + f(a.y + dv) + ' ' + f(b.x) + ' ' + f(b.y + dv) + ' ' + f(b.x) + ' ' + f(b.y);
    }
    return { d: d, segs: segs, pts: pts, volta: volta };
  }

  // Estimativa de leitura: 3,5 palavras/s e 0,6 s para localizar a parada.
  function tempoLeitura(texto, velocidade, minimo) {
    var palavras = (String(texto || '').match(/\S+/g) || []).length;
    return Math.max(1.8, Number(minimo) || 0, 0.6 + palavras / 3.5) / (Number(velocidade) > 0 ? Number(velocidade) : 1);
  }
  function pontasDaLinha(l) {
    var ids = l && l.estacoes || []; return ids.length ? [ids[0], ids[ids.length - 1]] : [];
  }
  function orientacao(m, l, celular) {
    var ids = pontasDaLinha(l), nomes = ids.map(function (id) { return (porId(m.estacoes, id) || {}).nome || id; });
    return (celular ? 'De cima para baixo: ' : 'Da esquerda para a direita: ') + nomes.join(' → ') + '. Aperte Tocar.';
  }
  var CORE = { tempoLeitura: tempoLeitura, pontasDaLinha: pontasDaLinha, orientacao: orientacao, aplicar: aplicar, aplicarUm: aplicarUm, diff: diff, resumo: resumo, custoServidor: custoServidor,
    custoArmazenamento: custoArmazenamento, hash: hash, slotsDe: slotsDe, caminhosDaLinha: caminhosDaLinha, clonar: clonar,
    CAMPOS: CAMPOS, CHAVE: CHAVE, LIMITE_CHAVE: LIMITE_CHAVE, LIMITE_TOTAL: LIMITE_TOTAL };
  if (typeof module === 'object' && module && module.exports) { module.exports = CORE; return; }
  raiz.MapaHarnessNucleo = CORE;
  if (typeof document === 'undefined' || !raiz.HARNESS) return;

  /* ================= interface ================= */
  var H = raiz.HARNESS, BASE = H.base, doc = document, html = doc.documentElement;
  var NS = 'http://www.w3.org/2000/svg';
  var $ = function (id) { return doc.getElementById(id); };
  var ops = [], lotes = [], modelo = clonar(BASE), desfeitos = 0, salvoEstado = 'nada';
  var ui = { modo: 'ver', lista: false, cenario: null, sel: null, selLinha: null, tracando: null, vel: 1, reduzido: false, celular: false, agora: false, detalhe: null };
  var anim = { beats: [], i: 0, tocando: false, raf: 0, timer: 0, mov: null, fim: false };
  var primeiraNarracao = true;
  var medida = { segs: {}, volta: {} };
  var mq = raiz.matchMedia ? raiz.matchMedia('(max-width: 760px)') : null;
  var mqMov = raiz.matchMedia ? raiz.matchMedia('(prefers-reduced-motion: reduce)') : null;
  var params = {};
  try { (location.search || '').replace(/^\?/, '').split('&').forEach(function (kv) { var p = kv.split('='); if (p[0]) params[decodeURIComponent(p[0])] = decodeURIComponent(p[1] || ''); }); } catch (e) {}

  function el(tag, attrs, pai) {
    var x = doc.createElementNS(NS, tag);
    for (var k in attrs || {}) if (attrs[k] != null) x.setAttribute(k, attrs[k]);
    if (pai) pai.appendChild(x); return x;
  }
  function h(tag, attrs, filhos) {
    var x = doc.createElement(tag);
    for (var k in attrs || {}) {
      if (attrs[k] == null) continue;
      if (k === 'texto') x.textContent = attrs[k];
      else if (k === 'html') x.innerHTML = attrs[k];
      else x.setAttribute(k, attrs[k]);
    }
    (filhos || []).forEach(function (c) { if (c) x.appendChild(typeof c === 'string' ? doc.createTextNode(c) : c); });
    return x;
  }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function est(id) { return porId(modelo.estacoes, id); }
  function linha(id) { return porId(modelo.linhas, id); }
  function bairro(id) { return porId(modelo.bairros, id); }
  function quem(id) { return (modelo.responsaveis || {})[id] || { nome: id || '—', sigla: '?', cor: '#8E8EA0' }; }
  function linhasDa(eId) { return modelo.linhas.filter(function (l) { return l.estacoes.indexOf(eId) >= 0; }); }
  function ancora(e) { var ls = linhasDa(e.id); return (ls.length ? ls[0].id : e.bairro) + '/' + e.id; }
  function cenario() { return porId(modelo.cenarios, ui.cenario) || modelo.cenarios[0]; }
  function linhaAtual() { var c = cenario(); return c ? linha(c.linha) : modelo.linhas[0]; }

  var ICON = {
    tocar: '<path d="M7 5l12 7-12 7z" fill="currentColor"/>',
    pausar: '<path d="M7 5h4v14H7zM13 5h4v14h-4z" fill="currentColor"/>',
    doc: '<path d="M7 3h7l4 4v14H7zM14 3v4h4M9.5 12h6M9.5 16h6" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>',
    seta: '<path d="M4 12h15M13 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'
  };
  /* pictogramas dos bairros (24×24, traço): a cidade aparece pelo desenho, não pela cor */
  var BZ_ICON = {
    regras: 'M4 4h16v10H4zM8 8h8M8 11h5M12 14v6M8 20h8',
    portaria: 'M3 21V9l5-4 5 4v12M3 21h18M13 14h8M16 14v7M6 13h4v4H6z',
    triagem: 'M3 4h18l-7 8v6l-4 3v-9z',
    oficina: 'M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7zM12 2v3.5M12 18.5V22M2 12h3.5M18.5 12H22M4.9 4.9l2.5 2.5M16.6 16.6l2.5 2.5M4.9 19.1l2.5-2.5M16.6 7.4l2.5-2.5',
    centro: 'M3 21V11l5 3v-3l5 3V4h5v17zM3 21h18',
    correio: 'M3 11a4 4 0 0 1 8 0v7H3zM11 7h7a3 3 0 0 1 3 3v8H11M7 18v4M15 3v4h3',
    posto: 'M3 17a9 9 0 1 1 18 0M12 17l4.5-5.5M3 20h18',
    ponte: 'M2 16h20M4 16V8M20 16V8M4 8c4 7 12 7 16 0M8 16v-3M12 16v-2M16 16v-3',
    doca: 'M5 21V3h3v18M8 5h12l-3 4M17 9v6M15 15h4M3 21h8',
    armazem: 'M3 21V10l9-6 9 6v11zM7 21v-7h10v7M7 17h10'
  };
  var PREDIO = 'M0 30V14h9V5h9v9h6V9h8v21h5V17h9v13z';
  function svgIcone(nome) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + (ICON[nome] || '') + '</svg>'; }

  /* ---------- persistência (remendos) ---------- */
  function lerArmazem(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function paresArmazem(substituir) {
    var par = [];
    try {
      for (var i = 0; i < localStorage.length; i++) {
        var k = localStorage.key(i); if (k == null) continue;
        par.push([k, k === CHAVE && substituir != null ? substituir : String(localStorage.getItem(k) || '')]);
      }
    } catch (e) {}
    if (substituir != null && !par.some(function (kv) { return kv[0] === CHAVE; })) par.push([CHAVE, substituir]);
    return par;
  }
  function textoRascunho() { return JSON.stringify({ v: 1, base_id: H.base_id, ops: ops, lotes: lotes, salvo_em: new Date().toISOString() }); }
  function medir(t) {
    var total = custoArmazenamento(paresArmazem(t));
    var pc = Math.max(t.length / LIMITE_CHAVE, total / LIMITE_TOTAL);
    return { chave: t.length, total: total, pct: pc };
  }
  function salvar() {
    var t = textoRascunho(), md = medir(t);
    if (md.pct > 0.5 && ops.length > 4) { // compacta: guarda só a diferença final
      var compacto = diff(BASE, modelo);
      if (JSON.stringify(compacto).length < JSON.stringify(ops).length) { ops = compacto; lotes = []; t = textoRascunho(); md = medir(t); }
    }
    if (md.pct >= 1) { salvoEstado = 'cheio'; atualizarEspaco(md); toast('Não coube no rascunho do app. Use Exportar agora para não perder estas mudanças.'); return false; }
    try { localStorage.setItem(CHAVE, t); salvoEstado = 'salvo'; }
    catch (e) { salvoEstado = 'indisponivel'; }
    atualizarEspaco(md);
    if (md.pct >= 0.8 && salvoEstado === 'salvo') toast('Rascunho chegando ao limite (' + Math.round(md.pct * 100) + '%). Envie as mudanças para a IA ou exporte.');
    return salvoEstado === 'salvo';
  }
  var salvarT = 0;
  function salvarLogo() { // espaçado: no app cada gravação vira uma linha de histórico no banco
    if (salvoEstado !== 'indisponivel') salvoEstado = 'pendente';
    atualizarEspaco(); clearTimeout(salvarT); salvarT = setTimeout(function () { salvarT = 0; salvar(); }, 1200);
  }
  function salvarJa() { clearTimeout(salvarT); salvarT = 0; return salvar(); }
  function atualizarEspaco(md) {
    var s = $('mh-espaco'); if (!s) return;
    md = md || medir(textoRascunho());
    var pc = Math.round(md.pct * 100);
    var est = salvoEstado === 'salvo' ? 'salvo' : salvoEstado === 'pendente' ? 'salvando…' : salvoEstado === 'indisponivel' ? 'não salvo neste modo: use Exportar' : salvoEstado === 'cheio' ? 'cheio: exporte' : 'sem mudanças';
    s.textContent = 'Rascunho: ' + pc + '% do espaço · ' + est;
    s.classList.toggle('alerta', md.pct >= 0.8 || salvoEstado === 'indisponivel' || salvoEstado === 'cheio');
    var d = $('mh-desfazer'); if (d) d.disabled = !ops.length || desfeitos >= 20;
  }
  function carregar() {
    var t = lerArmazem(CHAVE), d = null;
    try { d = t ? JSON.parse(t) : null; } catch (e) { d = null; }
    if (!d || d.v !== 1 || !Array.isArray(d.ops)) return;
    var lista = d.ops.slice(), aplic = H.lotes_aplicados || [], corte = 0;
    (d.lotes || []).forEach(function (lt) { if (lt && aplic.indexOf(lt.id) >= 0 && lt.n > corte) corte = lt.n; });
    lista = lista.slice(corte);
    lotes = (d.lotes || []).filter(function (lt) { return lt && lt.n > corte; }).map(function (lt) { return { id: lt.id, n: lt.n - corte }; });
    var r = aplicar(BASE, lista, true);
    modelo = r.modelo; ops = r.aceitos; salvoEstado = 'salvo';
    if (corte) setTimeout(function () { toast('Suas mudanças enviadas já entraram na planta. O rascunho guardou só o que veio depois.'); }, 300);
    if (r.ignorados.length) setTimeout(function () { toast(r.ignorados.length + ' mudança(s) antiga(s) não se aplicam mais à planta nova e ficaram de fora.'); }, 900);
    if (corte || r.ignorados.length) salvar();
  }
  function fazer(op, opcoes) {
    opcoes = opcoes || {};
    op.em = op.em || new Date().toISOString();
    var copia = clonar(modelo);
    try { aplicarUm(modelo, op); }
    catch (e) { modelo = copia; toast(e.message); return false; }
    if (opcoes.juntar && ops.length) {
      var u = ops[ops.length - 1];
      if (u.op === 'mover' && op.op === 'mover' && u.estacao === op.estacao && Date.now() - Date.parse(u.em) < 1500) ops.pop();
    }
    ops.push(op); desfeitos = 0;
    salvarLogo(); redesenhar();
    return true;
  }
  function desfazer() {
    if (!ops.length) { toast('Nada para desfazer.'); return; }
    if (desfeitos >= 20) { toast('Limite de 20 desfazer seguidos.'); return; }
    ops.pop(); desfeitos++;
    modelo = aplicar(BASE, ops, true).modelo;
    if (ui.sel && !est(ui.sel)) ui.sel = null;
    salvarLogo(); redesenhar(); toast('Desfeito.');
  }

  /* ---------- toast ---------- */
  var toastT = 0;
  function toast(msg, acao) { // no topo do palco; some em 6 s (8 s com ação); "Entendi" fecha na hora
    var t = $('mh-toast'); if (!t) return;
    t.innerHTML = ''; t.appendChild(h('span', { texto: msg }));
    if (acao) { var b = h('button', { type: 'button', 'class': 'prim', texto: acao.rotulo }); b.addEventListener('click', function () { t.hidden = true; acao.fn(); }); t.appendChild(b); }
    var ok = h('button', { type: 'button', texto: 'Entendi' }); ok.addEventListener('click', function () { t.hidden = true; }); t.appendChild(ok);
    var br = $('mh-barra'), ed = $('mh-edit'), topo = br ? br.getBoundingClientRect().bottom : 60;
    if (ed && !ed.hidden) topo = Math.max(topo, ed.getBoundingClientRect().bottom);
    t.style.top = ui.celular ? '' : Math.round(Math.max(8, topo) + 10) + 'px';
    t.hidden = false; clearTimeout(toastT); toastT = setTimeout(function () { t.hidden = true; }, acao ? 8000 : 6000);
  }

  /* ---------- desenho desktop ---------- */
  var CW = 7.9; // largura média de letra do rótulo de estação (14 px, negrito)
  function limpar(g) { if (g) while (g.firstChild) g.removeChild(g.firstChild); }
  function meiaAltura(k) { return k > 1 ? (24 + (k - 1) * GAP) / 2 : 13; }
  function extensaoNo(e, k) {
    if (e.tipo === 'placa') { var w = Math.max(80, e.nome.length * 7.4 + 24); return { l: e.x - w / 2, r: e.x + w / 2, t: e.y - 15, b: e.y + 15 }; }
    if (e.tipo === 'deposito') return { l: e.x - 54, r: e.x + 54, t: e.y - 19, b: e.y + 19 };
    var hh = meiaAltura(k), ls = quebrar(e.nome), n = ls.length;
    var lw = Math.min(170, Math.max.apply(null, ls.map(function (s) { return s.length; })) * CW) / 2 + 4;
    var rot = e.rotulo || 'baixo', ex = { l: e.x - 15, r: e.x + 15, t: e.y - hh - 2, b: e.y + hh + 2 };
    if (rot === 'cima') { ex.t = e.y - hh - 6 - n * 15; ex.l = Math.min(ex.l, e.x - lw); ex.r = Math.max(ex.r, e.x + lw); }
    else if (rot === 'esq') ex.l = e.x - 18 - lw * 2;
    else if (rot === 'dir') ex.r = e.x + 18 + lw * 2;
    else { ex.b = e.y + hh + 5 + n * 15; ex.l = Math.min(ex.l, e.x - lw); ex.r = Math.max(ex.r, e.x + lw); }
    return ex;
  }
  function quebrar(nome) {
    if (nome.length <= 14 || nome.indexOf(' ') < 0) return [nome];
    var p = nome.split(' '), melhor = [nome], dif = 1e9;
    for (var i = 1; i < p.length; i++) { var a = p.slice(0, i).join(' '), b = p.slice(i).join(' '), d = Math.abs(a.length - b.length); if (d < dif) { dif = d; melhor = [a, b]; } }
    return melhor;
  }
  /* desenho da legenda (26×18) — no SVG e na lista do celular */
  var LEG = {
    etapa: '<circle cx="13" cy="9" r="6.5" fill="var(--mapa)" stroke="var(--roxo)" stroke-width="3.5"/>',
    revisao: '<rect x="8" y="4" width="10" height="10" transform="rotate(45 13 9)" fill="var(--mapa)" stroke="var(--roxo)" stroke-width="3"/>',
    baldeacao: '<rect x="2" y="3" width="22" height="12" rx="6" fill="var(--mapa)" stroke="var(--tinta)" stroke-width="2.5"/>',
    nao_testada: '<circle cx="13" cy="9" r="6.5" fill="var(--mapa)" stroke="var(--fraco)" stroke-width="3" stroke-dasharray="3 2.5"/>',
    volta: '<path d="M2 14c0-11 22-11 22 0" fill="none" stroke="var(--laranja)" stroke-width="2.6" stroke-dasharray="4 3"/>',
    pedido: '<rect x="2" y="1" width="22" height="16" rx="4" fill="var(--roxo)"/><path d="M6.5 5h13v8h-13zM6.5 5l6.5 4.5 6.5-4.5" fill="none" stroke="#0B0B16" stroke-width="1.4"/>'
  };
  function nomeCurto(k) { var r = modelo.responsaveis[k] || {}; return r.curto || r.nome || k; }
  function usados() { var u = {}; modelo.estacoes.forEach(function (e) { u[e.quem] = 1; }); return Object.keys(modelo.responsaveis || {}).filter(function (k) { return u[k]; }); }
  /* caixas para não desenhar nada por cima de rótulo, trilho ou borda de quarteirão */
  function cruza(a, b, m) { m = m || 0; return a.x < b.x + b.w + m && b.x < a.x + a.w + m && a.y < b.y + b.h + m && b.y < a.y + a.h + m; }
  function caixa(t, dx, dy) { try { var b = t.getBBox(); return b.width ? { x: b.x + (dx || 0), y: b.y + (dy || 0), w: b.width, h: b.height } : null; } catch (x) { return null; } }
  function obstaculos() {
    var o = [];
    [].forEach.call(doc.querySelectorAll('#g-est .est'), function (g) {
      var e = est(g.getAttribute('data-est')); if (!e) return;
      var t = g.querySelector('.rot'), c = t && caixa(t, e.x, e.y); if (c) o.push(c);
      var k = (geo.sl[e.id] || []).length, hh = e.tipo === 'placa' ? 15 : e.tipo === 'deposito' ? 19 : meiaAltura(k) + 2, hw = e.tipo === 'deposito' ? 54 : e.tipo === 'placa' ? 45 : 15;
      o.push({ x: e.x - hw, y: e.y - hh, w: 2 * hw, h: 2 * hh });
    });
    [].forEach.call(doc.querySelectorAll('#g-bzrot text, #g-marcos > g, #g-elev text, #g-linhas .volta-rot'), function (t) { var c = caixa(t); if (c) o.push(c); });
    return o;
  }
  function noTrilho(r) {
    var svg = $('mh-mapa'), pt = svg.createSVGPoint();
    if (!geo.trc) geo.trc = [].map.call(doc.querySelectorAll('#g-linhas .trilho-alvo'), function (p) { var b = caixa(p) || { x: 0, y: 0, w: 0, h: 0 }; return { p: p, b: { x: b.x - 10, y: b.y - 10, w: b.w + 20, h: b.h + 20 } }; });
    var passo = Math.max(6, r.w / 10);
    for (var i = 0; i < geo.trc.length; i++) {
      if (!cruza(r, geo.trc[i].b)) continue;
      for (var yy = r.y; yy <= r.y + r.h + 0.1; yy += r.h / 2) for (var xx = r.x; xx <= r.x + r.w + 0.1; xx += passo) {
        pt.x = xx; pt.y = yy; try { if (geo.trc[i].p.isPointInStroke(pt)) return true; } catch (x) { return false; }
      }
    }
    return false;
  }
  function custo(r, obs, semBorda) { // 0 = lugar livre; quanto maior, pior (rótulo > trilho > borda)
    if (r.x < 4 || r.y < 4 || r.x + r.w > geo.W - 4 || r.y + r.h > geo.H - 4) return 99;
    var c = 0;
    obs.forEach(function (o) { if (cruza(r, o, 3)) c += 6; });
    if (!semBorda) (geo.bz || []).forEach(function (b) { if (cruza(r, b) && !(r.x >= b.x && r.y >= b.y && r.x + r.w <= b.x + b.w && r.y + r.h <= b.y + b.h)) c += 2; });
    return c + (c < 12 && noTrilho(r) ? 4 : 0);
  }
  function livre(r, obs, semBorda) { return custo(r, obs, semBorda) === 0; }
  var geo = { W: 1380, H: 830, sl: {}, cam: {}, bz: [] };
  function desenharMapa(parcial) {
    var svg = $('mh-mapa'); if (!svg) return;
    var sl = slotsDe(modelo); geo.sl = sl; geo.trc = null;
    var W = 0, Hh = 0;
    modelo.estacoes.forEach(function (e) { W = Math.max(W, e.x + 90); Hh = Math.max(Hh, e.y + 48); });
    W = Math.max(W, 1380); Hh = Math.max(Hh, 600); geo.W = W; geo.H = Hh;
    svg.setAttribute('viewBox', '0 0 ' + W + ' ' + Hh);
    var palco = $('mh-palco'); if (palco) palco.style.setProperty('--ar', (W / Hh).toFixed(4));
    var gb = $('g-bairros'), gr = $('g-bzrot'), gl = $('g-linhas'), gg = $('g-lig'), gv = $('g-elev'), gk = $('g-marcos'), gm = $('g-mais'), gmed = $('g-medida');
    [gb, gr, gl, gg, gv, gk, gm, gmed, $('g-marcos-conectores')].forEach(limpar);
    geo.bz = []; geo.W = W;
    var pontas = pontasDaLinha(linhaAtual());
    geo.marcos = [];
    geo.marcos.push(caixaMarco(est(pontas[0]), 'COMEÇA AQUI', (est(pontas[0]) || {}).nome, 20));
    geo.marcos.push(caixaMarco(est(pontas[1]), 'CHEGA AQUI', (est(pontas[1]) || {}).nome, 10, 70));
    // bairros: quarteirão neutro + pictograma + nome (a cor saturada fica só nas linhas)
    modelo.bairros.forEach(function (z) {
      var membros = modelo.estacoes.filter(function (e) { return e.bairro === z.id; });
      if (!membros.length) return;
      var bx;
      if (z.faixa === 'topo' || z.faixa === 'base') {
        var t = 1e9, b = -1e9; membros.forEach(function (e) { var x = extensaoNo(e, 1); t = Math.min(t, x.t); b = Math.max(b, x.b); });
        bx = { x: 8, y: t - 16, w: W - 16, h: (b - t) + 26 };
      } else {
        var L = 1e9, R = -1e9, T = 1e9, B = -1e9;
        membros.forEach(function (e) { var x = extensaoNo(e, (sl[e.id] || []).length); L = Math.min(L, x.l); R = Math.max(R, x.r); T = Math.min(T, x.t); B = Math.max(B, x.b); });
        geo.marcos.forEach(function (m) { if (m && m.e.bairro === z.id) { L = Math.min(L, m.x); R = Math.max(R, m.x + m.w); B = Math.max(B, m.y + m.h); } });
        bx = { x: L - 10, y: T - 22, w: (R - L) + 20, h: (B - T) + 26 };
      }
      var g = el('g', { 'class': 'bz', 'data-bairro': z.id }, gb);
      el('rect', { x: f(bx.x), y: f(bx.y), width: f(bx.w), height: f(bx.h), rx: 18 }, g);
      geo.bz.push({ id: z.id, x: bx.x, y: bx.y, w: bx.w, h: bx.h, g: g, faixa: z.faixa });
      var ic = BZ_ICON[z.id], tw = z.nome.length * 8.1 + (ic ? 24 : 0), x0 = z.rotulo_lado === 'dir' ? bx.x + bx.w - 12 - tw : bx.x + 12;
      var gt = el('g', { 'class': 'bzr', 'data-bairro': z.id }, gr);
      if (ic) el('path', { d: ic, transform: 'translate(' + f(x0) + ' ' + f(bx.y + 3) + ') scale(.74)' }, gt);
      var tx = el('text', { x: f(x0 + (ic ? 24 : 0)), y: f(bx.y + 17) }, gt); tx.textContent = z.nome;
    });
    // elevadores da memória: linha neutra até o armazém (lê no começo, grava no fim)
    var banda = geo.bz.filter(function (b) { return b.faixa === 'base'; })[0];
    (modelo.elevadores || []).forEach(function (v) {
      var e = est(v.estacao); if (!e || !banda) return;
      var k = (sl[e.id] || []).length, x = e.x + (v.dx || 0), y0 = v.dx ? e.y + meiaAltura(k) + 4 : extensaoNo(e, k).b + 4, dir = x > W / 2;
      el('path', { 'class': 'elev', d: 'M' + f(x) + ' ' + f(y0) + 'V' + f(banda.y) }, gv);
      var t = el('text', { 'class': 'elev-rot', x: f(dir ? x - 8 : x + 8), y: f(banda.y - 13), 'text-anchor': dir ? 'end' : 'start' }, gv);
      t.textContent = (/^grava/.test(v.texto) ? '↓ ' : '↑ ') + v.texto;
    });
    // linhas
    geo.cam = {}; medida = { segs: {}, volta: {} };
    modelo.linhas.forEach(function (l) {
      if (l.estacoes.length < 2) return;
      var c = caminhosDaLinha(modelo, sl, l); geo.cam[l.id] = c;
      var g = el('g', { 'class': 'ln', 'data-linha': l.id }, gl);
      el('path', { 'class': 'casco', d: c.d }, g);
      if (c.volta) {
        el('path', { 'class': 'volta', d: c.volta }, g);
        var a = c.pts[l.estacoes.indexOf(l.volta.de)], b = c.pts[l.estacoes.indexOf(l.volta.para)];
        var vy = l.volta.lado === 'cima' ? Math.min(a.y, b.y) - 41 : Math.max(a.y, b.y) + 50;
        var vt = el('text', { 'class': 'volta-rot', x: f((a.x + b.x) / 2), y: f(vy), 'text-anchor': 'middle' }, g);
        vt.textContent = 'volta ' + (l.volta.max || 1) + '× se a revisão pedir ajuste';
      }
      el('path', { 'class': 'trilho', d: c.d, stroke: l.cor }, g);
      var alvo = el('path', { 'class': 'trilho-alvo', d: c.d, 'data-linha': l.id }, g);
      if (ui.modo === 'editar') alvo.setAttribute('data-cf-ignorar', '');
      medida.segs[l.id] = c.segs.map(function (s) { return el('path', { d: s }, gmed); });
      medida.volta[l.id] = c.volta ? el('path', { d: c.volta }, gmed) : null;
    });
    // "+" entre estações (editar, só a linha escolhida, na cor dela, acima do trilho)
    if (ui.modo === 'editar' && !ui.tracando) {
      var lsel = linha(ui.selLinha) || (ui.sel && linhasDa(ui.sel)[0]);
      if (lsel && geo.cam[lsel.id]) {
        var pts = geo.cam[lsel.id].pts;
        for (var i = 1; i < pts.length; i++) {
          var mx = (pts[i - 1].x + pts[i].x) / 2, my = (pts[i - 1].y + pts[i].y) / 2;
          var gp = el('g', { 'class': 'mais', style: '--c:' + lsel.cor, transform: 'translate(' + f(mx) + ' ' + f(my - 26) + ')', tabindex: '0', role: 'button', 'data-cf-ignorar': '',
            'aria-label': 'Criar etapa em ' + lsel.nome + ' entre ' + est(lsel.estacoes[i - 1]).nome + ' e ' + est(lsel.estacoes[i]).nome, 'data-linha': lsel.id, 'data-depois': lsel.estacoes[i - 1], 'data-x': f(mx), 'data-y': f(my) }, gm);
          el('circle', { r: 11 }, gp); el('path', { d: 'M-5 0h10M0 -5v10' }, gp);
          var tt = el('title', {}, gp); tt.textContent = '+ etapa em ' + lsel.nome;
        }
      }
    }
    desenharMarcos(gk);
    if (parcial) { posicionarEstacoes(); return; }
    desenharEstacoes();
    var obs = obstaculos();
    desenharLigacoes(obs);
    desenharPredios(obs);
    desenharParados(obs);
    desenharNotas();
    aplicarFoco();
    posicionarTrem();
  }
  /* ligações (só em foco/animação): até placa ou depósito andam em L por um corredor livre, sem cruzar rótulo (P11) */
  function desenharLigacoes(obs) {
    var gg = $('g-lig'); limpar(gg);
    var topo = geo.bz.filter(function (b) { return b.faixa === 'topo'; })[0], base = geo.bz.filter(function (b) { return b.faixa === 'base'; })[0];
    (modelo.ligacoes || []).forEach(function (lg, i) {
      var a = est(lg.de), b = est(lg.para); if (!a || !b) return;
      var d = 'M' + a.x + ' ' + a.y + ' L' + b.x + ' ' + b.y, tx = (a.x + b.x) / 2 + 6, ty = (a.y + b.y) / 2;
      var banda = b.tipo === 'deposito' ? base : b.tipo === 'placa' ? topo : null;
      if (banda && (!a.tipo || a.tipo === 'estacao')) {
        var k = (geo.sl[a.id] || []).length, ex = extensaoNo(a, k), desce = banda === base, hh = meiaAltura(k);
        var y0 = desce ? a.y + hh + 6 : a.y - hh - 6, yc = desce ? banda.y - 7 : banda.y + banda.h + 7, lw = Math.max(15, Math.max(a.x - ex.l, ex.r - a.x)), lane = null;
        for (var j = 0; j < 14 && lane === null; j++) [1, -1].forEach(function (s) {
          var x = a.x + s * (lw + 8 + j * 14), r = { x: x - 3, y: Math.min(y0, yc), w: 6, h: Math.abs(yc - y0) };
          if (lane === null && !obs.some(function (o) { return cruza(r, o, 2); })) lane = x;
        });
        if (lane === null) lane = a.x + lw + 8;
        d = 'M' + f(a.x) + ' ' + f(a.y) + 'L' + f(lane) + ' ' + f(y0) + 'V' + f(yc) + 'H' + f(b.x) + 'V' + f(b.y);
        var txt = (lg.tipo === 'grava' ? '↓ grava: ' : '↑ lê: ') + lg.rotulo, tw = txt.length * 6.6 + 4, ach = false;
        for (var yy = Math.min(y0, yc) + 26; yy < Math.max(y0, yc) - 4 && !ach; yy += 12) [1, -1].forEach(function (s) { // rótulo ao lado do corredor, num lugar livre
          var r = { x: s > 0 ? lane + 6 : lane - 6 - tw, y: yy - 11, w: tw, h: 14 };
          if (!ach && !obs.some(function (o) { return cruza(r, o, 2); })) { ach = true; tx = s > 0 ? lane + 6 : lane - 6 - tw; ty = yy; }
        });
        if (!ach) { tx = lane + 6; ty = desce ? yc - 6 : yc + 16; }
      } else { // entre duas estações: rótulo no primeiro trecho livre da reta
        var tw2 = (lg.rotulo.length + 7) * 6.6;
        [0.5, 0.38, 0.62, 0.28, 0.72].some(function (q) { var x = a.x + (b.x - a.x) * q + 6, y = a.y + (b.y - a.y) * q, r = { x: x, y: y - 11, w: tw2, h: 14 }; if (obs.some(function (o) { return cruza(r, o, 2); })) return false; tx = x; ty = y; return true; });
      }
      el('path', { 'class': 'lig', d: d, 'data-de': lg.de, 'data-para': lg.para, id: 'lig-' + i }, gg);
      var t = el('text', { 'class': 'lig-rot', x: f(tx), y: f(ty), 'data-de': lg.de, 'data-para': lg.para }, gg);
      t.textContent = (lg.tipo === 'grava' ? '↓ grava: ' : '↑ lê: ') + lg.rotulo;
    });
  }
  /* placas grandes de começo e fim + legenda dentro do palco (P1, P2, P3, P9) */
  function caixaMarco(e, t1, t2, dx, dy) { // calculada antes dos bairros: o quarteirão da ponta abraça a placa
    if (!e) return null;
    var k = (geo.sl[e.id] || []).length, ex = extensaoNo(e, k), w = Math.max(t1.length * 11.6, t2.length * 8.2) + 30, hgt = 50;
    var cx = Math.max(12 + w / 2, Math.min(geo.W - 12 - w / 2, e.x + (dx || 0)));
    var limiteTopo = 8, limiteBase = geo.H - 8, obs = [];
    modelo.estacoes.forEach(function (s) {
      var b = extensaoNo(s, (geo.sl[s.id] || []).length), faixa = (bairro(s.bairro) || {}).faixa;
      obs.push({ x: b.l, y: b.t, w: b.r - b.l, h: b.b - b.t });
      if (faixa === 'topo') limiteTopo = Math.max(limiteTopo, b.b + 22);
      if (faixa === 'base') limiteBase = Math.min(limiteBase, b.t - 22);
    });
    (geo.marcos || []).forEach(function (m) { if (m) obs.push(m); });
    var cand = [{ x: cx - w / 2, y: ex.t - (dy || 44) - hgt }], best, score = Infinity;
    [-180,-90,0,90,180].forEach(function (xx) { [-140,-90,-50,0,50,90,140].forEach(function (yy) { cand.push({ x: e.x - w / 2 + xx, y: e.y - hgt / 2 + yy }); }); });
    cand.forEach(function (r, i) {
      r.x = Math.max(12, Math.min(geo.W - 12 - w, r.x)); r.y = Math.max(limiteTopo, Math.min(limiteBase - hgt, r.y)); r.w = w; r.h = hgt;
      var s = obs.filter(function (o) { return cruza(r, o, 8); }).length * 100000 + Math.hypot(r.x + w / 2 - e.x, r.y + hgt / 2 - e.y) + (i ? 8 : 0);
      if (s < score) { best = r; score = s; }
    });
    return { e: e, t1: t1, t2: t2, x: best.x, y: best.y, w: w, h: hgt, ex: ex };
  }
  function marco(g, m) {
    if (!m) return;
    var e = m.e, ex = m.ex, w = m.w, hgt = m.h, x = m.x, y = m.y, cx = x + w / 2, t1 = m.t1, t2 = m.t2;
    var gg = el('g', { 'class': 'marco', 'data-ponta': e.id }, g);
    var cy = y + hgt / 2, vx = e.x - cx, vy = e.y - cy, len = Math.hypot(vx, vy) || 1, ux = vx / len, uy = vy / len;
    var k = 1 / Math.max(Math.abs(vx) / (w / 2 + 3), Math.abs(vy) / (hgt / 2 + 3)), ax = cx + vx * k, ay = cy + vy * k;
    var tx = e.x - ux * 19, ty = e.y - uy * (meiaAltura((geo.sl[e.id] || []).length) + 7);
    el('path', { 'class': 'marco-conector', d: 'M' + f(ax) + ' ' + f(ay) + 'L' + f(tx) + ' ' + f(ty) + 'M' + f(tx - ux * 7 - uy * 5) + ' ' + f(ty - uy * 7 + ux * 5) + 'L' + f(tx) + ' ' + f(ty) + 'L' + f(tx - ux * 7 + uy * 5) + ' ' + f(ty - uy * 7 - ux * 5) }, $('g-marcos-conectores'));
    el('rect', { 'class': 'halo', x: f(x), y: f(y), width: f(w), height: hgt, rx: 12 }, gg);
    el('rect', { 'class': 'fundo', x: f(x), y: f(y), width: f(w), height: hgt, rx: 12 }, gg);
    var a = el('text', { 'class': 't1', x: f(cx), y: f(y + 22), 'text-anchor': 'middle' }, gg); a.textContent = t1;
    var b = el('text', { 'class': 't2', x: f(cx), y: f(y + 41), 'text-anchor': 'middle' }, gg); b.textContent = t2;
  }
  function desenharMarcos(gk) {
    (geo.marcos || []).forEach(function (m) { marco(gk, m); });
    var leg = modelo.legenda || [];
    function livreDe(b) { var x = 0; modelo.estacoes.forEach(function (e) { if (e.bairro === b.id) x = Math.max(x, extensaoNo(e, 1).r); }); return x + 26; }
    var topo = geo.bz.filter(function (b) { return b.faixa === 'topo'; })[0], base = geo.bz.filter(function (b) { return b.faixa === 'base'; })[0];
    var q = leg.filter(function (it) { return it.id === 'quem'; })[0];
    if (q && topo) { // quem faz: o selo que aparece dentro de cada estação
      var g = el('g', { 'class': 'leg', 'aria-label': 'Legenda: quem faz' }, gk), x0 = livreDe(topo), x = x0, y = topo.y + 24;
      var tt = el('text', { 'class': 'tit', x: f(x), y: f(y) }, g); tt.textContent = q.texto + ':'; x += q.texto.length * 8.2 + 14;
      usados().forEach(function (k) {
        var r = modelo.responsaveis[k], nm = nomeCurto(k), sw = r.sigla.length > 1 ? 26 : 20, w = sw + 5 + nm.length * 7.3 + 9;
        if (x + w > geo.W - 10) { x = x0; y += 23; }
        el('rect', { x: f(x), y: f(y - 15), width: sw, height: 20, rx: 5, fill: 'var(--card2)', stroke: 'var(--linha2)' }, g);
        var s = el('text', { x: f(x + sw / 2), y: f(y), 'text-anchor': 'middle', 'class': 'tit', style: 'font-size:12px' }, g); s.textContent = r.sigla;
        var n = el('text', { x: f(x + sw + 5), y: f(y) }, g); n.textContent = nm;
        x += w;
      });
    }
    if (base) { // símbolos
      var g2 = el('g', { 'class': 'leg', 'aria-label': 'Legenda dos símbolos' }, gk), xb0 = livreDe(base), xb = xb0, yb = base.y + 27;
      leg.forEach(function (it) {
        if (it.id === 'quem' || !LEG[it.id]) return;
        var w = 31 + it.texto.length * 7.2 + 16;
        if (xb + w > geo.W - 10) { xb = xb0; yb += 24; }
        var gi = el('g', { transform: 'translate(' + f(xb) + ' ' + f(yb - 13) + ')' }, g2); gi.innerHTML = LEG[it.id];
        var tx = el('text', { x: f(xb + 31), y: f(yb) }, g2); tx.textContent = it.texto;
        xb += w;
      });
    }
  }
  function desenharPredios(obs) { // silhuetas de prédios a 6 % nos cantos vazios de cada quarteirão
    (geo.bz || []).forEach(function (b) {
      if (b.faixa || b.w < 150 || b.h < 90) return;
      var c = [[b.x + b.w - 56, b.y + b.h - 38], [b.x + 10, b.y + b.h - 38], [b.x + b.w - 56, b.y + 8]];
      for (var i = 0; i < c.length; i++) {
        var r = { x: c[i][0], y: c[i][1], w: 46, h: 30 };
        if (livre(r, obs, true)) { el('path', { 'class': 'predio', d: PREDIO, transform: 'translate(' + f(r.x) + ' ' + f(r.y) + ')' }, b.g); return; }
      }
    });
  }
  function desenharEstacoes() {
    var g = $('g-est'); limpar(g);
    var sl = geo.sl;
    modelo.estacoes.forEach(function (e) {
      var ls = sl[e.id] || [], k = ls.length, q = quem(e.quem);
      var cls = 'est' + (e.tipo === 'placa' ? ' placa' : e.tipo === 'deposito' ? ' deposito' : '') + (e.verificado ? '' : ' nv') + (ui.sel === e.id ? ' sel' : '');
      var lab = e.nome + ' · ' + q.nome + (e.papel === 'revisao' ? ' · revisão' : '') + ' · segue quando ' + (e.condicao || '—') + (e.verificado ? '' : ' · não verificado');
      var gr = el('g', { 'class': cls, tabindex: '0', role: 'button', 'aria-label': lab, 'data-est': e.id, 'data-cf-ancora': ancora(e),
        transform: 'translate(' + e.x + ' ' + e.y + ')' }, g);
      if (ui.modo === 'editar') gr.setAttribute('data-cf-ignorar', '');
      if (e.tipo === 'placa') {
        var w = Math.max(80, e.nome.length * 7.4 + 24);
        el('rect', { 'class': 'foco', x: f(-w / 2 - 4), y: -18, width: f(w + 8), height: 36, rx: 9 }, gr);
        el('rect', { 'class': 'tb', x: f(-w / 2), y: -14, width: f(w), height: 28, rx: 7 }, gr);
        var tp = el('text', { 'class': 'rot', x: 0, y: 4.5, 'text-anchor': 'middle' }, gr); tp.textContent = e.nome;
        el('rect', { 'class': 'alvo', x: f(-w / 2 - 4), y: -22, width: f(w + 8), height: 44 }, gr);
        return;
      }
      if (e.tipo === 'deposito') {
        el('rect', { 'class': 'foco', x: -58, y: -23, width: 116, height: 46, rx: 12 }, gr);
        el('rect', { 'class': 'tb', x: -54, y: -18, width: 108, height: 36, rx: 9 }, gr);
        el('rect', { 'class': 'tampa', x: -54, y: -18, width: 108, height: 6, rx: 3 }, gr);
        var td = el('text', { 'class': 'rot', x: 0, y: 8, 'text-anchor': 'middle' }, gr); td.textContent = e.nome;
        el('rect', { 'class': 'alvo', x: -58, y: -24, width: 116, height: 48 }, gr);
        return;
      }
      var hh = meiaAltura(k), cor = k ? linha(ls[0]).cor : 'var(--fraco)';
      el('rect', { 'class': 'foco', x: -18, y: f(-hh - 5), width: 36, height: f(2 * hh + 10), rx: 18 }, gr);
      if (k > 1) {
        el('rect', { 'class': 'casco-no', x: -13.75, y: f(-hh - 1.75), width: 27.5, height: f(2 * hh + 3.5), rx: 13.75 }, gr);
        el('rect', { 'class': 'no-baldeacao', x: -12, y: f(-hh), width: 24, height: f(2 * hh), rx: 12 }, gr);
      } else if (e.papel === 'revisao') { // revisão = losango
        el('rect', { 'class': 'casco-no', x: -11.2, y: -11.2, width: 22.4, height: 22.4, transform: 'rotate(45)' }, gr);
        el('rect', { 'class': 'no', x: -8.6, y: -8.6, width: 17.2, height: 17.2, transform: 'rotate(45)', stroke: cor }, gr);
      } else {
        el('circle', { 'class': 'casco-no', r: 13.75 }, gr);
        el('circle', { 'class': 'no', r: 11, stroke: cor }, gr);
      }
      var sg = el('g', { 'class': 'selo', 'aria-hidden': 'true' }, gr), stx = el('text', { x: 0, y: 4.6, 'text-anchor': 'middle', style: q.sigla.length > 1 ? 'font-size:10.5px' : null }, sg);
      stx.textContent = q.sigla;
      var linhasTxt = quebrar(e.nome), rot = e.rotulo || 'baixo';
      var tx = el('text', { 'class': 'rot', 'text-anchor': rot === 'esq' ? 'end' : rot === 'dir' ? 'start' : 'middle' }, gr);
      linhasTxt.forEach(function (t, i) {
        var y = rot === 'cima' ? -hh - 8 - (linhasTxt.length - 1 - i) * 15 : rot === 'baixo' ? hh + 16 + i * 15 : 5 + (i - (linhasTxt.length - 1) / 2) * 15;
        var x = rot === 'esq' ? -18 : rot === 'dir' ? 18 : 0;
        var ts = el('tspan', { x: x, y: f(y) }, tx); ts.textContent = t;
      });
      var ext = extensaoNo(e, k);
      el('rect', { 'class': 'alvo', x: f(Math.min(-22, ext.l - e.x)), y: f(Math.min(-22, ext.t - e.y)), width: f(Math.max(44, ext.r - ext.l)), height: f(Math.max(44, ext.b - ext.t)) }, gr);
    });
  }
  function posicionarEstacoes() {
    [].forEach.call(doc.querySelectorAll('#g-est .est'), function (g) { var e = est(g.getAttribute('data-est')); if (e) g.setAttribute('transform', 'translate(' + e.x + ' ' + e.y + ')'); });
    if (!arr) desenharParados();
    desenharNotas(); posicionarTrem();
  }
  /* "o que está parado agora" (fotografia): pílula com palavra, ligada à estação dona, longe de trilho e rótulo (P8) */
  function desenharParados(obs) {
    var g = $('g-parados'); limpar(g);
    var foto = H.foto; if (!ui.agora || !foto || !foto.estacionados || ui.celular || !$('g-est').firstChild) return;
    obs = obs || obstaculos();
    foto.estacionados.forEach(function (p) {
      var e = est(p.estacao); if (!e) return;
      var txt = p.curto || ((p.n > 99 ? '99+' : String(p.n)) + (p.sufixo || '')), pw = Math.round(txt.length * 7.2 + 20), ph = 22;
      var hh = meiaAltura((geo.sl[e.id] || []).length), d = hh + 18 + ph / 2, sx = pw / 2 + 12, cand = [];
      [-d, d, -d - 26, d + 26, -d - 52, d + 52].forEach(function (vy) { [0, -pw / 2 + 14, pw / 2 - 14, -pw / 2 - 24, pw / 2 + 24, -pw - 30, pw + 30].forEach(function (vx) { cand.push([vx, vy]); }); });
      cand.push([sx + 16, 0], [-sx - 16, 0]);
      var esc = null, melhor = 1e9;
      for (var i = 0; i < cand.length && melhor > 0; i++) { // o primeiro lugar livre; se nenhum, o menos ruim
        var r = { x: e.x + cand[i][0] - pw / 2, y: e.y + cand[i][1] - ph / 2, w: pw, h: ph }, c = custo(r, obs) + i / 100;
        if (c < melhor) { melhor = c; esc = r; }
        if (c < 1) break;
      }
      obs.push(esc);
      var gr = el('g', { 'class': 'parado', tabindex: '0', role: 'button', 'aria-label': 'Agora: ' + p.rotulo, 'data-agora': p.estacao }, g);
      var cx = esc.x + pw / 2, cy = esc.y + ph / 2, lado = Math.abs(cy - e.y) < hh;
      var x2 = lado ? (cx > e.x ? esc.x : esc.x + pw) : Math.max(esc.x + 10, Math.min(esc.x + pw - 10, e.x)), y2 = lado ? cy : (cy > e.y ? esc.y : esc.y + ph);
      var ang = Math.atan2(y2 - e.y, x2 - e.x);
      el('line', { x1: f(e.x + Math.cos(ang) * 15), y1: f(e.y + Math.sin(ang) * (hh + 2)), x2: f(x2), y2: f(y2) }, gr);
      el('rect', { 'class': 'hl', x: f(esc.x - 3), y: f(esc.y - 3), width: pw + 6, height: ph + 6, rx: 14 }, gr);
      el('rect', { 'class': 'pl', x: f(esc.x), y: f(esc.y), width: pw, height: ph, rx: 11 }, gr);
      var t = el('text', { x: f(cx), y: f(esc.y + 15.5), 'text-anchor': 'middle' }, gr); t.textContent = txt;
      var tt = el('title', {}, gr); tt.textContent = 'Agora (fotografia de ' + foto.quando_txt + '): ' + p.rotulo;
    });
  }
  function desenharNotas() {
    var g = $('g-notas'); limpar(g);
    var cont = {};
    (modelo.notas || []).forEach(function (n) { var m = /^estacao:(.+)$/.exec(n.alvo || ''); if (m) cont[m[1]] = (cont[m[1]] || 0) + 1; });
    Object.keys(cont).forEach(function (id) {
      var e = est(id); if (!e) return;
      var gr = el('g', { 'class': 'nota-pino', transform: 'translate(' + f(e.x - 18) + ' ' + f(e.y - 20) + ')' }, g);
      el('circle', { r: 8 }, gr); var t = el('text', { y: 3.5, 'text-anchor': 'middle' }, gr); t.textContent = String(cont[id]);
    });
  }
  function aplicarFoco() {
    var l = linhaAtual(), ativo = anim.iniciado || anim.tocando;
    [].forEach.call(doc.querySelectorAll('#g-linhas .ln'), function (g) {
      var id = g.getAttribute('data-linha');
      g.classList.toggle('apagada', !!(ui.tracando ? false : (ativo && l && id !== l.id) || (ui.modo === 'editar' && ui.selLinha && id !== ui.selLinha)));
      g.classList.toggle('ativa', !!(ativo && l && id === l.id && !ui.tracando));
    });
    [].forEach.call(doc.querySelectorAll('#g-est .est'), function (g) {
      var id = g.getAttribute('data-est'), e = est(id);
      var fora = ativo && l && l.estacoes.indexOf(id) < 0 && (!e || !e.tipo || e.tipo === 'estacao');
      g.classList.toggle('apagada', !!fora);
      g.classList.toggle('sel', ui.sel === id || (ui.tracando && ui.tracando.indexOf(id) >= 0));
    });
    var gp = $('g-parados'); if (gp) gp.classList.toggle('apagada', !!ativo);
    var c = $('mh-barra'); if (c && l) c.style.setProperty('--c', l.cor);
  }
  function ligar(eId, on) {
    [].forEach.call(doc.querySelectorAll('#g-lig [data-de="' + eId + '"],#g-lig [data-para="' + eId + '"]'), function (x) { x.classList.toggle('on', on); });
  }
  function apagarLigacoes() { [].forEach.call(doc.querySelectorAll('#g-lig .on'), function (x) { x.classList.remove('on'); }); }

  /* ---------- animação ---------- */
  function montarBeats() {
    var c = cenario(), l = c ? linha(c.linha) : null; anim.beats = []; anim.i = 0; anim.fim = false;
    if (!l) return;
    var r = l.estacoes, esp = l.esperas || [], v = l.volta && c.resultado === 'volta_1x' ? l.volta : null, voltou = false, B = anim.beats;
    var e0 = est(r[0]);
    B.push({ est: r[0], seg: null, estado: 'inicio', narr: (r[0] === 'voce' ? 'Você pede: “' + c.pedido + '”.' : 'Pedido “' + c.pedido + '” começa em ' + e0.nome + '.') + ' Linha ' + l.nome + ', ' + r.length + ' estações.' });
    for (var j = 1; j < r.length; j++) {
      var e = est(r[j]), q = quem(e.quem), ult = j === r.length - 1;
      var estado = ult ? 'entregue' : (v && v.de === r[j] && !voltou) ? 'ajuste' : (v && v.de === r[j] && voltou) ? 'aprovado' : esp.indexOf(r[j]) >= 0 && c.resultado === 'espera' ? 'espera' : 'trabalhando';
      var narr;
      if (estado === 'entregue') narr = 'Entregue em ' + e.nome + '. ' + e.descricao;
      else if (estado === 'ajuste') narr = e.nome + ' (' + q.nome + ') pediu ajuste. O pedido volta 1 vez para “' + est(v.para).nome + '”.';
      else if (estado === 'aprovado') narr = e.nome + ' (' + q.nome + ') revisou de novo e aprovou. Segue.';
      else if (estado === 'espera') narr = 'Espera você em ' + e.nome + ': ' + e.descricao;
      else narr = e.nome + ' (' + q.nome + '): ' + e.descricao + ' Segue quando ' + e.condicao + '.';
      B.push({ est: r[j], seg: { linha: l.id, i: j - 1 }, estado: estado, narr: narr });
      if (estado === 'ajuste') {
        voltou = true; var k = r.indexOf(v.para);
        B.push({ est: v.para, seg: { linha: l.id, volta: true }, estado: 'trabalhando', narr: 'De volta em “' + est(v.para).nome + '” para ajustar. É a única volta.' });
        j = k;
      } else if (estado === 'espera') {
        B.push({ est: r[j], seg: null, estado: 'liberado', narr: 'Você respondeu (' + e.condicao + '). O pedido segue.' });
      }
    }
  }
  function ptEst(eId, lId) { var e = est(eId); if (!e) return { x: 0, y: 0 }; return lId && geo.sl[eId] ? pontoNaLinha(modelo, geo.sl, eId, lId) : { x: e.x, y: e.y }; }
  var CHIP = {
    inicio: { txt: 'Pedido', bg: null, ic: 'M-3 -4h8v8h-8zM-3 -4l4 4 4-4' },
    trabalhando: { txt: 'Trabalhando', bg: null, ic: 'M-4 0a4 4 0 1 1 1.2 2.8M-4 3v-3h3' },
    ajuste: { txt: 'Ajuste pedido', bg: 'var(--laranja)', ic: 'M3 -3a4 4 0 1 0 1 4M3 -6v3h-3' },
    espera: { txt: 'Espera você', bg: 'var(--amarelo)', ic: 'M-3 4v-6M-1 4v-8M1 4v-7M3 4v-5M-5 1l2 3h6' },
    liberado: { txt: 'Liberado', bg: 'var(--verde)', ic: 'M-4 0l3 3 5-6' },
    aprovado: { txt: 'Aprovado', bg: 'var(--verde)', ic: 'M-4 0l3 3 5-6' },
    entregue: { txt: 'Entregue', bg: 'var(--verde)', ic: 'M0 -5l1.5 3.2 3.5.4-2.6 2.4.7 3.5L0 2.8-3.1 4.5l.7-3.5L-5 -1.4l3.5-.4z' }
  };
  function ate8(t) { var n = 0, o = []; String(t).split(/\s+/).forEach(function (x) { if (!x) return; if (x === '·') { o.push(x); return; } if (n < 8) o.push(x); else if (n === 8) o[o.length - 1] += '…'; n++; }); return o.join(' '); }
  function textoBalao(e, estado) { // até 8 palavras, colado no trem (P5)
    var q = quem(e.quem), c = cenario();
    if (estado === 'inicio') return ate8('Você pede: “' + (c ? c.pedido : '') + '”');
    if (estado === 'ajuste') return ate8(q.nome + ' pediu ajuste · volta 1 vez');
    if (estado === 'espera') return ate8('Espera você · ' + e.condicao);
    if (estado === 'liberado') { var b0 = anim.beats[anim.i], nx = anim.beats[anim.i + 1]; return b0 && b0.estado === 'liberado' ? 'Você respondeu · segue' : ate8('Liberado · segue para ' + (nx && est(nx.est) ? est(nx.est).nome : 'a próxima')); }
    if (estado === 'entregue') return ate8('Chegou em ' + e.nome);
    return ate8(q.nome + ' · segue quando ' + e.condicao);
  }
  function rastro(l) { // trecho já percorrido a 100 %; o resto da linha fica a 40 % (classe .ativa)
    var g = $('g-rastro'); limpar(g); if (!g || !l || ui.celular || !(anim.iniciado || anim.mov)) return;
    var mv = anim.mov && anim.mov.p ? anim.mov : null;
    for (var k = 1; k <= anim.i; k++) {
      var b = anim.beats[k]; if (!b || !b.seg || (mv && k === anim.i)) continue;
      var p = elementoSeg(b); if (p) el('path', { 'class': 'rastro', d: p.getAttribute('d'), stroke: l.cor, 'stroke-dasharray': b.seg.volta ? '7 6' : null }, g);
    }
    if (mv) el('path', { 'class': 'rastro', d: mv.p.getAttribute('d'), stroke: l.cor, 'stroke-dasharray': f(mv.len * (mv.e || 0)) + ' ' + f(mv.len + 20) }, g);
  }
  function desenharAnim(pos, estado, eId) {
    var g = $('g-anim'); if (!g) return;
    limpar(g);
    var l = linhaAtual(); rastro(l); if (!l || !pos) return;
    var e = eId ? est(eId) : null;
    if (e && estado && (estado === 'trabalhando' || estado === 'ajuste' || estado === 'espera')) {
      var pc = estado === 'ajuste' ? 'var(--laranja)' : estado === 'espera' ? 'var(--amarelo)' : l.cor;
      el('circle', { 'class': 'pulso', cx: f(pos.x), cy: f(pos.y), r: 18, stroke: pc }, g);
    }
    if (e && estado === 'entregue') el('circle', { 'class': 'brilho', cx: f(pos.x), cy: f(pos.y), r: 20, fill: 'var(--verde)' }, g);
    var tr = el('g', { 'class': 'trem', id: 'mh-trem', transform: 'translate(' + f(pos.x) + ' ' + f(pos.y) + ')' }, g);
    el('rect', { x: -30, y: -23, width: 60, height: 46, rx: 14, fill: l.cor, opacity: '.28' }, tr);
    el('rect', { 'class': 'corpo', x: -23, y: -16, width: 46, height: 32, rx: 7, fill: l.cor }, tr);
    el('path', { 'class': 'env', d: 'M-12 -8h24v16h-24zM-12 -8l12 9 12-9' }, tr);
    if (!(e && estado && CHIP[estado] && (anim.iniciado || estado !== 'inicio'))) return;
    // balão colado no trem: estado (cor + ícone + palavra) e o que acontece, em até 8 palavras
    var ch = CHIP[estado], txt = textoBalao(e, estado), cw = ch.txt.length * 7.6 + 36, w = Math.max(cw, txt.length * 7.3) + 20, hb = 62;
    var obs = [], ests = l.estacoes;
    [].forEach.call(doc.querySelectorAll('#g-est .est'), function (gg) { var id = gg.getAttribute('data-est'), x = est(id); if (x && ests.indexOf(id) >= 0) { var c = caixa(gg.querySelector('.rot'), x.x, x.y); if (c) obs.push(c); obs.push({ x: x.x - 15, y: x.y - 15, w: 30, h: 30 }); } });
    [].forEach.call(doc.querySelectorAll('#g-marcos > g'), function (t) { var c = caixa(t); if (c) obs.push(c); });
    var cand = [[-w / 2, -32 - hb], [-w / 2, 32], [34, -hb / 2], [-34 - w, -hb / 2], [-w / 2, -60 - hb], [-w / 2, 60]], bx = null;
    for (var i = 0; i < cand.length && !bx; i++) {
      var r = { x: Math.max(6, Math.min(geo.W - w - 6, pos.x + cand[i][0])), y: pos.y + cand[i][1], w: w, h: hb };
      if (r.y > 4 && r.y + hb < geo.H - 4 && !obs.some(function (o) { return cruza(r, o, 2); })) bx = r;
    }
    if (!bx) bx = { x: Math.max(6, Math.min(geo.W - w - 6, pos.x - w / 2)), y: pos.y - 32 - hb < 4 ? pos.y + 32 : pos.y - 32 - hb, w: w, h: hb };
    var gb = el('g', { 'class': 'balao' }, g);
    el('rect', { x: f(bx.x), y: f(bx.y), width: f(w), height: hb, rx: 12, stroke: l.cor }, gb);
    var st = el('g', { 'class': 'st', transform: 'translate(' + f(bx.x + 10 + cw / 2) + ' ' + f(bx.y + 20) + ')' }, gb);
    el('rect', { x: f(-cw / 2), y: -12, width: f(cw), height: 24, fill: ch.bg || l.cor }, st);
    el('path', { d: ch.ic, transform: 'translate(' + f(-cw / 2 + 14) + ' 0)' }, st);
    var t = el('text', { x: f(-cw / 2 + 26), y: 4.4 }, st); t.textContent = ch.txt;
    var t2 = el('text', { 'class': 'bt', x: f(bx.x + 10), y: f(bx.y + 50) }, gb); t2.textContent = txt;
  }
  function posicionarTrem() {
    if (ui.celular) { desenharVertAnim(); return; }
    var b = anim.beats[anim.i]; if (!b) { desenharAnim(null); return; }
    var l = linhaAtual();
    if (anim.mov && anim.mov.pos) { desenharAnim(anim.mov.pos, null, null); return; }
    desenharAnim(ptEst(b.est, l && l.id), b.estado, b.est);
  }
  function narrar(texto) {
    var n = $('mh-narra-tx'); if (n) n.textContent = texto;
    var c = $('mh-narra-n'); if (c) c.textContent = anim.iniciado && anim.beats.length ? (anim.i + 1) + '/' + anim.beats.length : '';
    marcarRegua();
  }
  /* régua de paradas: cada ponto é uma parada; clique leva até ela (você está aqui = ponto maior) */
  function montarRegua() {
    var r = $('mh-regua'); if (!r) return; r.innerHTML = '';
    var sel = !ui.celular ? h('select', { id: 'mh-parada-sel', 'aria-label': 'Ir à parada desta linha' }) : null;
    anim.beats.forEach(function (b, i) {
      var e = est(b.est), nome = e ? e.nome : '?';
      if (sel) sel.appendChild(h('option', { value: String(i), texto: (i + 1) + '/' + anim.beats.length + ' · ' + nome }));
      else r.appendChild(h('span', { 'aria-hidden': 'true' }, [h('i')]));
    });
    if (sel) r.appendChild(sel);
    marcarRegua();
  }
  function marcarRegua() {
    var k = anim.iniciado ? anim.i : 0;
    var sel = $('mh-parada-sel'); if (sel) { sel.value = String(k); return; }
    [].forEach.call(doc.querySelectorAll('#mh-regua > *'), function (x, i) { x.classList.toggle('atual', i === k); x.classList.toggle('feito', anim.iniciado && i < k); if (i === k && x.setAttribute) x.setAttribute('aria-current', 'step'); else x.removeAttribute('aria-current'); });
  }
  function irPara(k) {
    pausar(); cancelAnimationFrame(anim.raf); anim.mov = null;
    anim.i = Math.max(0, Math.min(anim.beats.length - 1, k)); anim.fim = false; chegar(); atualizarBotoes();
  }
  function chegar() {
    var b = anim.beats[anim.i]; anim.mov = null; anim.iniciado = true;
    apagarLigacoes(); if (b) ligar(b.est, true);
    var eb = b && est(b.est);
    narrar(!b ? '' : ui.celular && eb ? eb.nome + ': ' + textoBalao(eb, b.estado) : b.narr); // celular: até 2 linhas (P6)
    aplicarFoco(); posicionarTrem();
    if (ui.celular) rolarParaAtiva();
    if (anim.i >= anim.beats.length - 1) { anim.fim = true; anim.tocando = false; atualizarBotoes(); }
  }
  function duracaoMov() { return (modelo.preferencias.segundos_por_trecho || 1.2) / ui.vel; }
  function pausaDe(b) {
    var e = est(b.est), tx = ui.celular && e ? e.nome + ': ' + textoBalao(e, b.estado) : b.narr;
    var base = tempoLeitura(tx, ui.vel, modelo.preferencias.pausa_na_estacao || 0.6);
    if (ui.reduzido) base = Math.max(base, 1.25 / ui.vel);
    if (b.estado === 'espera') return base + 1.6 / ui.vel;
    if (b.estado === 'ajuste') return base + 1.0 / ui.vel;
    if (b.estado === 'inicio') return base + 0.6 / ui.vel;
    return base;
  }
  function elementoSeg(b) {
    if (!b.seg) return null;
    if (b.seg.volta) return medida.volta[b.seg.linha] || null;
    return (medida.segs[b.seg.linha] || [])[b.seg.i] || null;
  }
  function moverAte(k, dur, pronto) {
    var b = anim.beats[k]; anim.i = k;
    var p = elementoSeg(b);
    if (!p || ui.reduzido || ui.celular || dur <= 0) {
      if (ui.celular && !ui.reduzido && dur > 0 && b.seg) { animarVert(dur, pronto); return; }
      chegar(); pronto && pronto(); return;
    }
    var len = p.getTotalLength(), dirReversa = false;
    anim.mov = { p: p, len: len, dur: dur, prog: 0, t0: performance.now(), pronto: pronto, rev: dirReversa, pos: null };
    apagarLigacoes();
    passoRaf();
  }
  function animarVert(dur, pronto) {
    anim.mov = { vert: true, restante: dur, t0: performance.now(), pronto: pronto };
    desenharVertAnim(dur);
    anim.timer = setTimeout(function () { anim.mov = null; chegar(); pronto && pronto(); }, dur * 1000);
  }
  function passoRaf() {
    var mv = anim.mov; if (!mv || mv.vert) return;
    var agora = performance.now(), t = Math.min(1, mv.prog + (agora - mv.t0) / (mv.dur * 1000));
    var e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
    var pt = mv.p.getPointAtLength(mv.len * e); mv.pos = { x: pt.x, y: pt.y }; mv.e = e;
    desenharAnim(mv.pos, null, null);
    if (t >= 1) { var pr = mv.pronto; anim.mov = null; chegar(); pr && pr(); return; }
    anim.raf = requestAnimationFrame(passoRaf);
  }
  function agendar() {
    if (!anim.tocando) return;
    if (anim.i >= anim.beats.length - 1) { anim.tocando = false; anim.fim = true; atualizarBotoes(); return; }
    var prox = anim.i + 1, b = anim.beats[prox];
    if (!b.seg) { anim.i = prox; chegar(); anim.timer = setTimeout(agendar, pausaDe(b) * 1000); return; }
    // portão: liberado na saída (cor + ícone + palavra)
    var atual = anim.beats[anim.i];
    if (atual && (atual.estado === 'trabalhando' || atual.estado === 'aprovado' || atual.estado === 'liberado' || atual.estado === 'inicio') && !ui.celular) {
      desenharAnim(ptEst(atual.est, linhaAtual().id), 'liberado', atual.est);
      anim.timer = setTimeout(function () { if (anim.tocando) moverAte(prox, ui.reduzido ? 0 : duracaoMov(), function () { if (anim.tocando) anim.timer = setTimeout(agendar, pausaDe(b) * 1000); }); }, (ui.reduzido ? 450 : 380) / ui.vel);
      return;
    }
    moverAte(prox, ui.reduzido ? 0 : duracaoMov(), function () { if (anim.tocando) anim.timer = setTimeout(agendar, pausaDe(b) * 1000); });
  }
  function tocar() {
    if (anim.tocando) { pausar(); return; }
    if (anim.fim || !anim.beats.length) reiniciar(true);
    anim.tocando = true; atualizarBotoes(); aplicarFoco();
    if (anim.mov && anim.mov.vert) { animarVert(anim.mov.restante, anim.mov.pronto); return; }
    if (anim.mov && !anim.mov.vert) { anim.mov.t0 = performance.now(); passoRaf(); return; }
    if (anim.i === 0) { chegar(); anim.timer = setTimeout(agendar, pausaDe(anim.beats[0]) * 1000); }
    else agendar();
  }
  function pausar() {
    anim.tocando = false; clearTimeout(anim.timer); cancelAnimationFrame(anim.raf);
    if (anim.mov && anim.mov.vert) {
      var t = $('mh-vtrem'), mv = anim.mov; mv.restante = Math.max(0, mv.restante - (performance.now() - mv.t0) / 1000); mv.t0 = performance.now();
      if (t) { var tr = raiz.getComputedStyle(t).transform; t.style.transition = 'none'; t.style.transform = tr; }
    }
    if (anim.mov && !anim.mov.vert) { var mv = anim.mov; mv.prog = Math.min(1, mv.prog + (performance.now() - mv.t0) / (mv.dur * 1000)); }
    atualizarBotoes();
  }
  function passo() {
    if (anim.tocando) pausar();
    if (anim.mov) { cancelAnimationFrame(anim.raf); clearTimeout(anim.timer); anim.mov = null; chegar(); return; }
    if (anim.fim || anim.i >= anim.beats.length - 1) { reiniciar(true); chegar(); return; }
    if (anim.i === 0 && !anim.iniciado) { chegar(); return; }
    var prox = anim.i + 1;
    moverAte(prox, ui.reduzido ? 0 : Math.min(0.7, duracaoMov()), null);
    aplicarFoco();
  }
  function reiniciar(silencioso) {
    pausar(); anim.mov = null; montarBeats(); anim.i = 0; anim.fim = false; anim.iniciado = false; montarRegua();
    apagarLigacoes(); aplicarFoco(); posicionarTrem(); atualizarBotoes();
    var l = linhaAtual(), c = cenario();
    if (!silencioso && l) narrar(orientacao(modelo, l, ui.celular));
    primeiraNarracao = false;
    if (ui.celular) desenharVert();
  }
  function atualizarBotoes() {
    var b = $('mh-tocar'); if (!b) return;
    b.innerHTML = svgIcone(anim.tocando ? 'pausar' : 'tocar') + '<span>' + (anim.tocando ? 'Pausar' : anim.fim ? 'Tocar de novo' : 'Tocar') + '</span>';
    b.setAttribute('aria-label', anim.tocando ? 'Pausar a animação' : 'Tocar a animação do pedido');
  }

  /* ---------- celular: vertical ---------- */
  function desenharVert() {
    var box = $('mh-vert'); if (!box) return;
    box.innerHTML = '';
    var l = linhaAtual(); if (!l) return;
    var sl = slotsDe(modelo), bzAnt = null;
    l.estacoes.forEach(function (id, i) {
      var e = est(id), q = quem(e.quem), outras = (sl[id] || []).filter(function (x) { return x !== l.id; });
      if (e.bairro !== bzAnt) { bzAnt = e.bairro; box.appendChild(h('div', { 'class': 'vbairro' + (i ? ' trilho' : ''), style: '--c:' + l.cor, texto: (bairro(e.bairro) || {}).nome || '' })); }
      var em = outras.length ? h('em', { 'aria-label': 'Baldeação com ' + outras.map(function (o) { return linha(o).nome; }).join(', ') }, outras.map(function (o) { return h('i', { style: '--x:' + linha(o).cor }); })) : null;
      var ult = i === l.estacoes.length - 1, marca = i === 0 ? 'COMEÇA AQUI' : ult ? 'CHEGA AQUI' : '';
      var row = h('button', { type: 'button', 'class': 'vrow' + (outras.length ? ' bald' : e.papel === 'revisao' ? ' rev' : '') + (e.verificado ? '' : ' nv') + (ult ? ' ult' : '') + (ui.sel === id ? ' sel' : ''),
        style: '--c:' + l.cor, 'data-est': id, 'data-cf-ancora': ancora(e), 'data-i': String(i),
        'aria-label': (marca ? marca + ': ' : '') + e.nome + ' · ' + q.nome + (e.papel === 'revisao' ? ' · revisão' : '') + ' · segue quando ' + e.condicao + (e.verificado ? '' : ' · não verificado') }, [
        h('span', { 'class': 'vno', 'aria-hidden': 'true' }, [h('span', { texto: q.sigla })]),
        h('span', { 'class': 'vtx' }, [marca ? h('span', { 'class': 'vmarco', texto: marca }) : null, h('b', { texto: e.nome }), h('small', { texto: q.nome + ' · ' + e.condicao }), em])
      ]);
      box.appendChild(row);
    });
    if (l.volta) box.appendChild(h('div', { 'class': 'vvolta', id: 'mh-vvolta', 'aria-hidden': 'true' }));
    box.appendChild(h('div', { 'class': 'vtrem', id: 'mh-vtrem', style: 'background:' + l.cor, 'aria-hidden': 'true' }));
    if (ui.modo === 'editar') {
      var mais = h('div', { 'class': 'vmais' }, [
        h('button', { type: 'button', 'class': 'mh-b', 'data-acao': 'v-add', texto: '+ Estação no fim' })
      ]);
      box.appendChild(mais);
    }
    var extra = h('div', { 'class': 'vextra' });
    [['regras', 'placa'], ['armazem', 'deposito']].forEach(function (par) {
      var itens = modelo.estacoes.filter(function (e) { return e.tipo === par[1]; });
      if (!itens.length) return;
      var z = bairro(itens[0].bairro) || { nome: par[0] };
      extra.appendChild(h('h4', { texto: z.nome }));
      extra.appendChild(h('div', { 'class': 'grade' }, itens.map(function (e) {
        return h('button', { type: 'button', 'data-est': e.id, 'data-cf-ancora': ancora(e), 'aria-label': e.nome + ' · ' + quem(e.quem).nome }, [e.nome, h('small', { texto: e.condicao })]);
      })));
    });
    extra.appendChild(h('h4', { texto: 'Legenda' }));
    extra.appendChild(legendaHtml());
    box.appendChild(extra);
    requestAnimationFrame(function () { posicionarVolta(); desenharVertAnim(); });
  }
  function rowTop(i) { var r = doc.querySelector('#mh-vert .vrow[data-i="' + i + '"]'); return r ? r.offsetTop + r.offsetHeight / 2 : 0; }
  function posicionarVolta() {
    var l = linhaAtual(), v = $('mh-vvolta'); if (!l || !l.volta || !v) return;
    var a = rowTop(l.estacoes.indexOf(l.volta.para)), b = rowTop(l.estacoes.indexOf(l.volta.de));
    v.style.top = a + 'px'; v.style.height = Math.max(10, b - a) + 'px';
  }
  function desenharVertAnim(dur) {
    var t = $('mh-vtrem'); if (!t) return;
    var b = anim.beats[anim.i], l = linhaAtual(); if (!b || !l) return;
    var i = l.estacoes.indexOf(b.est), y = rowTop(i) - 11;
    t.style.transition = dur && !ui.reduzido ? 'transform ' + dur + 's ease-in-out' : 'none';
    t.style.transform = 'translateY(' + y + 'px)';
    [].forEach.call(doc.querySelectorAll('#mh-vert .vrow'), function (r) {
      var ativa = Number(r.getAttribute('data-i')) === i;
      r.classList.toggle('ativa', ativa);
      var old = r.querySelector('.vchip'); if (old) old.parentNode.removeChild(old);
      if (ativa && !anim.mov && b.estado && CHIP[b.estado]) {
        var ch = CHIP[b.estado];
        var s = h('span', { 'class': 'vchip', style: 'display:inline-flex;align-items:center;gap:4px;margin-left:8px;padding:1px 8px;border-radius:8px;font:800 11.5px var(--ui);color:#0B0B16;background:' + (ch.bg || l.cor) }, [svgMini(ch.ic), ch.txt]);
        var bb = r.querySelector('.vtx b'); if (bb) bb.appendChild(s);
      }
    });
  }
  function svgMini(d) { var s = doc.createElementNS(NS, 'svg'); s.setAttribute('viewBox', '-7 -7 14 14'); s.setAttribute('width', '12'); s.setAttribute('height', '12'); s.setAttribute('aria-hidden', 'true'); var p = el('path', { d: d, fill: 'none', stroke: '#0B0B16', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, s); return s; }
  function rolarParaAtiva() {
    var r = doc.querySelector('#mh-vert .vrow.ativa'); if (!r || !r.getBoundingClientRect) return;
    var bx = r.getBoundingClientRect(), br = $('mh-barra'), topo = br ? br.getBoundingClientRect().bottom : 120;
    // centro da tela: fica longe da barra presa no topo e do chip do cursor embaixo (P6)
    if (bx.top < topo + 8 || bx.bottom > (raiz.innerHeight || 800) - 90) { try { r.scrollIntoView({ block: 'center', behavior: 'auto' }); } catch (e) {} }
  }

  /* ---------- lista equivalente ---------- */
  function desenharLista() {
    var box = $('mh-lista'); if (!box) return; box.innerHTML = '';
    box.appendChild(h('p', { 'class': 'gat', texto: 'Mesma informação do mapa, em tabela. Cada linha é um processo; as estações estão em ordem.' }));
    modelo.linhas.forEach(function (l) {
      box.appendChild(h('h3', { style: '--c:' + l.cor }, [h('i'), l.nome]));
      box.appendChild(h('p', { 'class': 'gat', texto: 'Quando: ' + l.gatilho + ' Frequência: ' + l.frequencia + (l.volta ? ' Volta para ajuste: no máximo ' + (l.volta.max || 1) + '.' : '') }));
      var tb = h('table'), th = h('thead', {}, [h('tr', {}, ['#', 'Estação', 'Quem faz', 'Segue quando', 'Bairro'].map(function (x) { return h('th', { scope: 'col', texto: x }); }))]);
      tb.appendChild(th); var bd = h('tbody'); tb.appendChild(bd);
      l.estacoes.forEach(function (id, i) {
        var e = est(id);
        bd.appendChild(h('tr', {}, [
          h('td', { 'data-th': '#', texto: String(i + 1) }),
          h('td', { 'data-th': 'Estação', texto: e.nome + (e.verificado ? '' : ' (não verificado)') }),
          h('td', { 'data-th': 'Quem faz', texto: quem(e.quem).nome }),
          h('td', { 'data-th': 'Segue quando', texto: e.condicao + ((l.esperas || []).indexOf(id) >= 0 ? ' · espera você' : '') + (l.volta && l.volta.de === id ? ' · se pedir ajuste, volta a ' + est(l.volta.para).nome : '') }),
          h('td', { 'data-th': 'Bairro', texto: (bairro(e.bairro) || {}).nome || '' })
        ]));
      });
      box.appendChild(tb);
    });
    var extras = modelo.estacoes.filter(function (e) { return e.tipo === 'placa' || e.tipo === 'deposito'; });
    box.appendChild(h('h3', { style: '--c:var(--fraco)' }, [h('i'), 'Regras e armazém (fora das linhas)']));
    var ul = h('ul'); extras.forEach(function (e) { ul.appendChild(h('li', { texto: e.nome + ' — ' + e.descricao })); }); box.appendChild(ul);
  }

  /* ---------- detalhe ---------- */
  function abrirDetalhe(tipo, id, focoDe) {
    var p = $('mh-det'); if (!p) return;
    ui.detalhe = { tipo: tipo, id: id, foco: focoDe || null };
    p.innerHTML = '';
    var fechar = h('button', { type: 'button', 'class': 'fechar', 'aria-label': 'Fechar detalhe', texto: '×' });
    fechar.addEventListener('click', fecharDetalhe); p.appendChild(fechar);
    if (tipo === 'estacao') detalheEstacao(p, est(id));
    else if (tipo === 'linha') detalheLinha(p, linha(id));
    else if (tipo === 'agora') detalheAgora(p, id);
    p.hidden = false; p.scrollTop = 0; html.classList.add('det-aberto');
    deslocarPalco(tipo === 'estacao' ? id : null);
    var h2 = p.querySelector('h2'); if (h2) { h2.setAttribute('tabindex', '-1'); try { h2.focus({ preventScroll: true }); } catch (e) { h2.focus(); } }
  }
  function fecharDetalhe() {
    var p = $('mh-det'); if (!p || p.hidden) return; p.hidden = true; html.classList.remove('det-aberto'); deslocarPalco(null);
    var f0 = ui.detalhe && ui.detalhe.foco; ui.detalhe = null;
    if (ui.modo === 'ver') { ui.sel = null; aplicarFoco(); apagarLigacoes(); }
    if (f0 && f0.focus) try { f0.focus({ preventScroll: true }); } catch (e) {}
  }
  function campo(rot, input) { var lb = h('label', { texto: rot }); lb.appendChild(input); return lb; }
  function detalheEstacao(p, e) {
    if (!e) { p.appendChild(h('h2', { texto: 'Estação removida' })); return; }
    var q = quem(e.quem), z = bairro(e.bairro) || {}, ls = linhasDa(e.id), editar = ui.modo === 'editar';
    p.appendChild(h('h2', { texto: e.nome }));
    p.appendChild(h('div', {}, [h('span', { 'class': 'tag', html: (BZ_ICON[z.id] ? '<svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true"><path d="' + BZ_ICON[z.id] + '" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>' : '') + esc(z.nome || '') }),
      e.papel === 'revisao' ? h('span', { 'class': 'tag', texto: '◆ etapa de revisão' }) : null]));
    var dl = h('dl');
    function item(t, conteudo) { dl.appendChild(h('dt', { texto: t })); var dd = h('dd'); if (typeof conteudo === 'string') dd.textContent = conteudo; else dd.appendChild(conteudo); dl.appendChild(dd); }
    if (!editar) {
      p.appendChild(h('ul', { 'class': 'resumo' }, [
        h('li', {}, [h('span', { html: svgIcone('doc') }), h('span', { texto: e.descricao })]),
        h('li', {}, [h('span', { 'class': 'mh-sl', texto: q.sigla, title: q.nome }), h('span', {}, [h('b', { texto: q.nome }), ' faz esta etapa' + (e.quem === 'auto' ? ' (script ou gancho que roda sozinho)' : '')])]),
        h('li', {}, [h('span', { html: svgIcone('seta') }), h('span', {}, ['Segue quando ', h('b', { texto: e.condicao })])])
      ]));
      if (ls.length) item('Linhas que passam aqui', h('span', {}, ls.map(function (l) { return h('span', { 'class': 'tag', style: '--c:' + l.cor }, [h('i'), l.nome]); })));
      if (e.tecnico) item('Termo técnico', e.tecnico);
      var lig = (modelo.ligacoes || []).filter(function (g) { return g.de === e.id || g.para === e.id; });
      if (lig.length) item('Conversa com', h('ul', {}, lig.map(function (g) { var o = est(g.de === e.id ? g.para : g.de); return h('li', { texto: (g.tipo === 'grava' ? 'grava em ' : 'lê de ') + (o ? o.nome : '?') + ': ' + g.rotulo }); })));
      item('Prova', h('span', {}, [h('span', { 'class': e.verificado ? 'ok' : 'nv', texto: e.verificado ? '✓ Conferido no arquivo' : '⚠ Não verificado' }), e.nota_prova ? h('span', { texto: ' · ' + e.nota_prova }) : null]));
      if ((e.arquivos || []).length) item('Arquivos que provam', h('ul', {}, e.arquivos.map(function (a) { return h('li', { 'class': 'arq', texto: a }); })));
      var parado = H.foto && (H.foto.estacionados || []).filter(function (x) { return x.estacao === e.id; });
      if (parado && parado.length) item('Agora (fotografia de ' + H.foto.quando_txt + ')', h('ul', {}, parado.map(function (x) { return h('li', { texto: x.rotulo }); })));
    }
    p.appendChild(dl);
    if (editar) formEstacao(p, e, ls);
    notasDe(p, 'estacao:' + e.id);
    var maisAntes = linhaDoMais(); ui.sel = e.id;
    if (ui.modo === 'editar' && !ui.celular && linhaDoMais() !== maisAntes) desenharMapa(true);
    aplicarFoco(); apagarLigacoes(); ligar(e.id, true);
  }
  function formEstacao(p, e, ls) {
    var nome = h('input', { type: 'text', value: e.nome, maxlength: '40' });
    var desc = h('textarea', { maxlength: '400' }); desc.value = e.descricao || '';
    var cond = h('input', { type: 'text', value: e.condicao || '', maxlength: '120' });
    var qsel = h('select'); Object.keys(modelo.responsaveis).forEach(function (k) { var o = h('option', { value: k, texto: modelo.responsaveis[k].nome }); if (k === e.quem) o.selected = true; qsel.appendChild(o); });
    var bsel = h('select'); modelo.bairros.forEach(function (z) { var o = h('option', { value: z.id, texto: z.nome }); if (z.id === e.bairro) o.selected = true; bsel.appendChild(o); });
    function ligarCampo(inp, c) { inp.addEventListener('change', function () { var v = inp.value.trim(); if (v === (e[c] || '')) return; fazer({ op: 'editar', tipo: 'estacao', id: e.id, campo: c, valor: v }); abrirDetalhe('estacao', e.id); }); }
    ligarCampo(nome, 'nome'); ligarCampo(desc, 'descricao'); ligarCampo(cond, 'condicao'); ligarCampo(qsel, 'quem'); ligarCampo(bsel, 'bairro');
    p.appendChild(campo('Nome (1 a 3 palavras)', nome));
    p.appendChild(campo('O que é (até 20 palavras)', desc));
    p.appendChild(campo('Quem faz', qsel));
    p.appendChild(campo('Segue quando', cond));
    p.appendChild(campo('Bairro', bsel));
    var acoes = h('div', { 'class': 'acoes' });
    if (!e.tipo || e.tipo === 'estacao') {
      var lsel = h('select', { 'aria-label': 'Linha para incluir esta estação' });
      var o0 = h('option', { value: '', texto: 'Escolha uma linha…', disabled: '' }); o0.selected = true; lsel.appendChild(o0);
      modelo.linhas.forEach(function (l) { if (l.estacoes.indexOf(e.id) < 0) lsel.appendChild(h('option', { value: l.id, texto: l.nome })); });
      if (ls.length) {
        var bAdd = h('button', { type: 'button', 'class': 'mh-b', texto: '+ Estação depois desta' });
        bAdd.addEventListener('click', function () { criarDepois(ls[0].id, e.id); }); acoes.appendChild(bAdd);
        var l0 = ls[0], i0 = l0.estacoes.indexOf(e.id);
        var bSobe = h('button', { type: 'button', 'class': 'mh-b', texto: '← Antes', title: 'Passa para antes na linha ' + l0.nome, disabled: i0 <= 0 ? '' : null });
        bSobe.addEventListener('click', function () { var o = l0.estacoes.slice(); o.splice(i0, 1); o.splice(i0 - 1, 0, e.id); fazer({ op: 'ordem', linha: l0.id, estacoes: o }); abrirDetalhe('estacao', e.id); });
        var bDesce = h('button', { type: 'button', 'class': 'mh-b', texto: 'Depois →', title: 'Passa para depois na linha ' + l0.nome, disabled: i0 >= l0.estacoes.length - 1 ? '' : null });
        bDesce.addEventListener('click', function () { var o = l0.estacoes.slice(); o.splice(i0, 1); o.splice(i0 + 1, 0, e.id); fazer({ op: 'ordem', linha: l0.id, estacoes: o }); abrirDetalhe('estacao', e.id); });
        acoes.appendChild(bSobe); acoes.appendChild(bDesce);
      }
      if (lsel.options.length > 1) {
        var bInc = h('button', { type: 'button', 'class': 'mh-b', texto: 'Incluir na linha' });
        bInc.addEventListener('click', function () { var l = linha(lsel.value); if (!l) { toast('Escolha uma linha antes.'); return; } fazer({ op: 'incluir', linha: l.id, estacao: e.id, depois_de: l.estacoes[l.estacoes.length - 2] || null }); abrirDetalhe('estacao', e.id); });
        p.appendChild(campo('Incluir esta estação em outra linha', lsel)); acoes.appendChild(bInc);
      }
    }
    p.appendChild(acoes);
    var bRem = h('button', { type: 'button', 'class': 'mh-b mh-b--perigo', texto: 'Remover estação' });
    bRem.addEventListener('click', function () { remover(e.id); });
    p.appendChild(h('hr')); p.appendChild(h('div', { 'class': 'acoes' }, [bRem]));
  }
  function notasDe(p, alvo) {
    var ns = (modelo.notas || []).filter(function (n) { return n.alvo === alvo; });
    p.appendChild(h('p', { 'class': 'dt', texto: 'Notas de arquitetura' }));
    ns.forEach(function (n) {
      var d = h('div', { 'class': 'nota' }, [n.texto, h('small', { texto: (n.em || '').slice(0, 16).replace('T', ' ') })]);
      if (ui.modo === 'editar') { var b = h('button', { type: 'button', 'class': 'mh-b', style: 'min-height:32px;margin-top:6px', texto: 'Apagar nota' }); b.addEventListener('click', function () { fazer({ op: 'remover_nota', id: n.id }); reabrir(); }); d.appendChild(b); }
      p.appendChild(d);
    });
    var ta = h('textarea', { maxlength: '1000', placeholder: 'Quero que isso funcione assim…', 'aria-label': 'Nova nota de arquitetura' });
    var b = h('button', { type: 'button', 'class': 'mh-b', texto: 'Adicionar nota' });
    b.addEventListener('click', function () {
      var t = ta.value.trim(); if (!t) { toast('Escreva a nota antes.'); return; }
      if (fazer({ op: 'nota', id: 'n' + Date.now().toString(36), alvo: alvo, texto: t })) { toast('Nota guardada. Ela vai junto em “Enviar mudanças para a IA”.'); reabrir(); }
    });
    p.appendChild(ta); p.appendChild(h('div', { 'class': 'acoes' }, [b]));
  }
  function reabrir() { if (ui.detalhe) abrirDetalhe(ui.detalhe.tipo, ui.detalhe.id, ui.detalhe.foco); }
  function detalheLinha(p, l) {
    if (!l) { p.appendChild(h('h2', { texto: 'Linha removida' })); return; }
    var editar = ui.modo === 'editar';
    p.appendChild(h('h2', { texto: l.nome }));
    p.appendChild(h('div', {}, [h('span', { 'class': 'tag', style: '--c:' + l.cor }, [h('i'), l.estacoes.length + ' estações']), h('span', { 'class': 'tag', style: '--c:' + (l.verificado ? 'var(--verde)' : 'var(--amarelo)') }, [h('i'), l.verificado ? 'conferida' : 'não verificada'])]));
    var dl = h('dl');
    if (!editar) {
      dl.appendChild(h('dt', { texto: 'Quando acontece' })); dl.appendChild(h('dd', { texto: l.gatilho }));
      dl.appendChild(h('dt', { texto: 'Frequência' })); dl.appendChild(h('dd', { texto: l.frequencia }));
    }
    dl.appendChild(h('dt', { texto: 'Estações, em ordem' }));
    dl.appendChild(h('dd', {}, [h('ol', {}, l.estacoes.map(function (s) { var e = est(s); return h('li', { texto: e.nome + ' — ' + quem(e.quem).nome }); }))]));
    p.appendChild(dl);
    if (editar) {
      var nome = h('input', { type: 'text', value: l.nome, maxlength: '40' });
      var gat = h('input', { type: 'text', value: l.gatilho || '', maxlength: '200' });
      var fr = h('input', { type: 'text', value: l.frequencia || '', maxlength: '200' });
      [[nome, 'nome'], [gat, 'gatilho'], [fr, 'frequencia']].forEach(function (par) { par[0].addEventListener('change', function () { var v = par[0].value.trim(); if (v === (l[par[1]] || '')) return; fazer({ op: 'editar', tipo: 'linha', id: l.id, campo: par[1], valor: v }); abrirDetalhe('linha', l.id); }); });
      p.appendChild(campo('Nome da linha', nome)); p.appendChild(campo('Quando acontece', gat)); p.appendChild(campo('Frequência', fr));
      var cores = h('div', { 'class': 'mh-cores', role: 'group', 'aria-label': 'Cor da linha' });
      PALETA.forEach(function (c) { var b = h('button', { type: 'button', style: '--c:' + c, 'aria-label': 'Cor ' + c, 'aria-pressed': String(c.toLowerCase() === String(l.cor).toLowerCase()) }); b.addEventListener('click', function () { fazer({ op: 'editar', tipo: 'linha', id: l.id, campo: 'cor', valor: c }); abrirDetalhe('linha', l.id); }); cores.appendChild(b); });
      p.appendChild(h('label', { texto: 'Cor' })); p.appendChild(cores);
      var bRem = h('button', { type: 'button', 'class': 'mh-b', texto: 'Remover linha' });
      bRem.addEventListener('click', function () { var nomeL = l.nome; if (fazer({ op: 'remover_linha', id: l.id })) { fecharDetalhe(); ui.selLinha = null; if (!porId(modelo.cenarios, ui.cenario)) ui.cenario = modelo.cenarios[0].id; montarChips(); reiniciar(); toast('Linha “' + nomeL + '” removida.', { rotulo: 'Desfazer', fn: desfazer }); } });
      p.appendChild(h('div', { 'class': 'acoes' }, [bRem]));
    }
    var bTocar = h('button', { type: 'button', 'class': 'mh-b mh-b--prim', texto: 'Tocar esta linha' });
    bTocar.addEventListener('click', function () { var c = modelo.cenarios.filter(function (x) { return x.linha === l.id; })[0]; if (c) { escolherCenario(c.id); fecharDetalhe(); tocar(); } });
    p.appendChild(h('div', { 'class': 'acoes' }, [bTocar]));
    notasDe(p, 'linha:' + l.id);
  }
  function detalheAgora(p, foco) {
    var F = H.foto;
    p.appendChild(h('h2', { texto: 'Agora na cidade' }));
    if (!F) { p.appendChild(h('p', { texto: 'Esta versão foi gerada sem fotografia dos dados.' })); return; }
    p.appendChild(h('p', { style: 'color:var(--corpo);margin:4px 0 0', texto: 'Fotografia de ' + F.quando_txt + ', lida sem gravar nada. Não é ao vivo: para atualizar, gere o mapa de novo.' }));
    var dl = h('dl');
    function sec(t, conteudo, fonte) { dl.appendChild(h('dt', { texto: t })); var dd = h('dd'); dd.appendChild(conteudo); if (fonte) dd.appendChild(h('div', { 'class': 'arq', texto: 'fonte: ' + fonte })); dl.appendChild(dd); }
    var s = F.sessoes || {};
    sec('Sessões nas últimas 24 h: ' + (s.total != null ? s.total : 'NAO_MEDIDO'), h('ul', {}, Object.keys(s.por_cliente || {}).map(function (k) { return h('li', { texto: k + ': ' + s.por_cliente[k] }); })), s.fonte);
    var pd = F.pedidos || {};
    sec('Pedidos no app: ' + (pd.total != null ? pd.total : 'NAO_MEDIDO'), h('ul', {}, (pd.ultimos || []).map(function (x) { return h('li', { texto: x.icone + ' ' + x.status_txt + ' · ' + x.titulo + ' · ' + x.quando }); })), pd.fonte);
    var rl = F.relatorios || {};
    sec('Relatórios em 24 h: ' + (rl.total != null ? rl.total : 'NAO_MEDIDO'), h('ul', {}, (rl.ultimos || []).map(function (x) { return h('li', { texto: x.tipo + ' · ' + x.titulo + ' · ' + x.quando }); })), rl.fonte);
    var ct = F.cotas || {};
    sec('Cotas por conta', h('ul', {}, (ct.contas || []).map(function (x) { return h('li', { texto: x.conta + ': ' + (x.pct == null ? 'NAO_MEDIDO' : x.pct + '% usado') + (x.janela ? ' (' + x.janela + ')' : '') + (x.de ? ' · medido ' + x.de : '') }); })), ct.fonte);
    var cm = F.comentarios || {};
    sec('Comentários pendentes: ' + (cm.pendentes != null ? cm.pendentes : 'NAO_MEDIDO'), h('ul', {}, Object.keys(cm.por_status || {}).map(function (k) { return h('li', { texto: k + ': ' + cm.por_status[k] }); })), cm.fonte);
    p.appendChild(dl);
    var tg = h('button', { type: 'button', 'class': 'mh-b', 'aria-pressed': String(ui.agora), texto: ui.agora ? 'Esconder do mapa o que está parado' : 'Mostrar no mapa o que está parado' });
    tg.addEventListener('click', function () { definirAgora(!ui.agora); });
    p.appendChild(h('div', { 'class': 'acoes' }, [tg]));
    if ((F.avisos || []).length) p.appendChild(h('ul', {}, F.avisos.map(function (a) { return h('li', { 'class': 'nv', texto: a }); })));
  }

  /* ---------- edição ---------- */
  function novoId(prefixo) { var b = prefixo + Date.now().toString(36).slice(-6), i = 0, id = b; while (est(id) || linha(id)) id = b + (++i); return id; }
  function criarDepois(lId, depois, x, y) {
    var l = linha(lId), i = l.estacoes.indexOf(depois), a = est(depois), b = est(l.estacoes[i + 1]);
    var nx = x != null ? x : b ? (a.x + b.x) / 2 : a.x + 90, ny = y != null ? y : b ? (a.y + b.y) / 2 : a.y;
    var id = novoId('e');
    if (fazer({ op: 'nova_estacao', id: id, nome: 'Nova etapa', linha: lId, depois_de: depois, bairro: a.bairro, x: Math.round(nx / 5) * 5, y: Math.round(ny / 5) * 5 })) {
      ui.sel = id; aplicarFoco();
      if (ui.celular) abrirDetalhe('estacao', id); else setTimeout(function () { renomear(id); }, 30);
      toast('Estação criada. Dê um nome e descreva o que ela faz.');
    }
  }
  function remover(id) {
    var e = est(id); if (!e) return;
    if (fazer({ op: 'remover_estacao', id: id })) {
      fecharDetalhe(); ui.sel = null; reiniciar(true);
      toast('Estação “' + e.nome + '” removida.', { rotulo: 'Desfazer', fn: desfazer });
    }
  }
  function renomear(id) {
    var g = doc.querySelector('#g-est [data-est="' + id + '"]'), palco = $('mh-palco'), e = est(id);
    if (!g || !palco || !e) return;
    var r = g.getBoundingClientRect(), pr = palco.getBoundingClientRect();
    var inp = h('input', { type: 'text', 'class': 'mh-renomear', value: e.nome, maxlength: '40', 'aria-label': 'Novo nome da estação' });
    inp.style.left = Math.max(4, r.left - pr.left + r.width / 2 - 75) + 'px'; inp.style.top = Math.max(4, r.top - pr.top + r.height / 2 - 17) + 'px';
    palco.appendChild(inp); inp.focus(); inp.select();
    var feito = false;
    function fim(ok) {
      if (feito) return; feito = true;
      var v = inp.value.trim(); if (inp.parentNode) inp.parentNode.removeChild(inp);
      if (ok && v && v !== e.nome) fazer({ op: 'editar', tipo: 'estacao', id: id, campo: 'nome', valor: v });
      var g2 = doc.querySelector('#g-est [data-est="' + id + '"]'); if (g2) try { g2.focus({ preventScroll: true }); } catch (x) {}
    }
    inp.addEventListener('keydown', function (ev) { if (ev.key === 'Enter') { ev.preventDefault(); fim(true); } else if (ev.key === 'Escape') { ev.preventDefault(); fim(false); } });
    inp.addEventListener('blur', function () { fim(true); });
  }
  function pontoSvg(ev) {
    var svg = $('mh-mapa'), m = svg.getScreenCTM(); if (!m) return { x: 0, y: 0 };
    var p = svg.createSVGPoint(); p.x = ev.clientX; p.y = ev.clientY; p = p.matrixTransform(m.inverse()); return { x: p.x, y: p.y };
  }
  var arr = null;
  function aoBaixar(ev) {
    if (ui.modo !== 'editar' || ui.celular || ev.button !== 0) return;
    var g = ev.target.closest && ev.target.closest('#g-est .est'); if (!g) return;
    var id = g.getAttribute('data-est'), e = est(id); if (!e) return;
    var p = pontoSvg(ev);
    arr = { id: id, g: g, dx: p.x - e.x, dy: p.y - e.y, x0: e.x, y0: e.y, moveu: false, pid: ev.pointerId };
    try { g.setPointerCapture(ev.pointerId); } catch (x) {}
  }
  function aoMover(ev) {
    if (!arr || ev.pointerId !== arr.pid) return;
    var p = pontoSvg(ev), e = est(arr.id);
    var nx = Math.round((p.x - arr.dx) / 5) * 5, ny = Math.round((p.y - arr.dy) / 5) * 5;
    if (!arr.moveu && Math.hypot(nx - arr.x0, ny - arr.y0) < 4) return;
    arr.moveu = true; arr.g.classList.add('arrastando');
    e.x = Math.max(10, Math.min(2000, nx)); e.y = Math.max(10, Math.min(1400, ny));
    desenharMapa(true);
  }
  function aoSoltar(ev) {
    if (!arr || ev.pointerId !== arr.pid) return;
    var a = arr; arr = null; a.g.classList.remove('arrastando');
    var e = est(a.id);
    if (a.moveu) {
      var x = e.x, y = e.y; e.x = a.x0; e.y = a.y0;
      fazer({ op: 'mover', estacao: a.id, x: x, y: y });
      a.engolir = true; engolirClique = Date.now();
    }
  }
  var engolirClique = 0;

  /* ---------- exportar / importar / enviar ---------- */
  function pacote() {
    var patches = diff(BASE, modelo), lote = hash(JSON.stringify(patches));
    return { formato: 'megabrain-harness-mapa-remendos', versao: 1, base_id: H.base_id, lote: lote, gerado_em: new Date().toISOString(), patches: patches, resumo: resumo(patches, BASE, modelo) };
  }
  function marcarLote(lote) { lotes = lotes.filter(function (x) { return x.id !== lote; }); lotes.push({ id: lote, n: ops.length }); salvarJa(); }
  function abrirIO(titulo, texto, modo) {
    var p = $('mh-io'); p.innerHTML = '';
    p.appendChild(h('h2', { texto: titulo, tabindex: '-1' }));
    if (modo === 'exportar') {
      p.appendChild(h('p', { texto: 'Copie este texto e cole no chat da IA ou salve num arquivo .json. A IA aplica com: python bin/mb-harness-mapa.py --aplicar-remendos <arquivo>.' }));
      var ta = h('textarea', { readonly: '', 'aria-label': 'Mudanças em texto', id: 'mh-io-texto' }); ta.value = texto; p.appendChild(ta);
      var bc = h('button', { type: 'button', 'class': 'mh-b mh-b--prim', texto: 'Copiar' });
      bc.addEventListener('click', function () {
        ta.removeAttribute('readonly'); ta.focus(); ta.select(); var ok = false;
        try { ok = doc.execCommand('copy'); } catch (e) { ok = false; }
        ta.setAttribute('readonly', '');
        toast(ok ? 'Copiado. Cole no chat da IA.' : 'Não deu para copiar sozinho: o texto está selecionado, use Ctrl+C.');
      });
      var bf = h('button', { type: 'button', 'class': 'mh-b', texto: 'Fechar' }); bf.addEventListener('click', fecharIO);
      p.appendChild(h('div', { 'class': 'acoes' }, [bc, bf]));
    } else {
      p.appendChild(h('p', { texto: 'Escolha um arquivo .json exportado deste mapa ou cole o texto. As mudanças entram por cima da planta atual.' }));
      var inp = h('input', { type: 'file', accept: '.json,application/json', id: 'mh-io-arquivo', 'aria-label': 'Arquivo de mudanças' });
      var ta2 = h('textarea', { 'aria-label': 'Cole aqui as mudanças', id: 'mh-io-texto', placeholder: 'ou cole aqui o texto exportado' });
      inp.addEventListener('change', function () {
        var arq = inp.files && inp.files[0]; if (!arq) return;
        var fr = new FileReader(); fr.onload = function () { ta2.value = String(fr.result || ''); toast('Arquivo lido. Confira e clique Aplicar.'); }; fr.onerror = function () { toast('Não consegui ler o arquivo.'); }; fr.readAsText(arq);
      });
      var msg = h('p', { id: 'mh-io-msg', role: 'status' });
      var ba = h('button', { type: 'button', 'class': 'mh-b mh-b--prim', texto: 'Aplicar', id: 'mh-io-aplicar' });
      ba.addEventListener('click', function () { var r = importarTexto(ta2.value); msg.textContent = r.msg; if (r.ok) { fecharIO(); toast(r.msg); } });
      var bf2 = h('button', { type: 'button', 'class': 'mh-b', texto: 'Fechar' }); bf2.addEventListener('click', fecharIO);
      p.appendChild(inp); p.appendChild(ta2); p.appendChild(msg); p.appendChild(h('div', { 'class': 'acoes' }, [ba, bf2]));
    }
    p.hidden = false; var h2 = p.querySelector('h2'); if (h2) h2.focus();
  }
  function fecharIO() { var p = $('mh-io'); if (p) p.hidden = true; }
  function extrairPatches(d) {
    if (Array.isArray(d)) return d;
    if (!d || typeof d !== 'object') return null;
    if (Array.isArray(d.patches)) return d.patches;
    if (d.mapa_harness) return extrairPatches(d.mapa_harness);
    if (d.respostas) return extrairPatches(d.respostas);
    if (d.feedback) return extrairPatches(d.feedback);
    return null;
  }
  function importarTexto(t) {
    var d; try { d = JSON.parse(t); } catch (e) { return { ok: false, msg: 'O texto não é um JSON válido.' }; }
    var ps = extrairPatches(d); if (!ps || !ps.length) return { ok: false, msg: 'Não achei mudanças (campo "patches") nesse texto.' };
    var teste = clonar(modelo);
    try { ps.forEach(function (p) { aplicarUm(teste, p); }); } catch (e) { return { ok: false, msg: 'Não apliquei nada: ' + e.message }; }
    var agora = new Date().toISOString();
    ps.forEach(function (p) { var c = clonar(p); c.em = c.em || agora; ops.push(c); });
    modelo = teste; desfeitos = 0; salvarJa(); redesenhar();
    return { ok: true, msg: ps.length + ' mudança(s) importada(s) e salvas no rascunho.' };
  }
  function enviar() {
    var pk = pacote();
    if (!pk.patches.length) { toast('Nenhuma mudança para enviar ainda.'); return; }
    var texto = 'Mudanças no mapa do harness (' + pk.patches.length + '):\n' + pk.resumo.map(function (r, i) { return (i + 1) + '. ' + r; }).join('\n') +
      '\n\nPara aplicar: salve o JSON (respostas.mapa_harness) e rode python bin/mb-harness-mapa.py --aplicar-remendos <arquivo>. Lote ' + pk.lote + '.';
    var api = raiz.MegaBrainReport;
    if (api && typeof api.saveFeedback === 'function') {
      try {
        api.saveFeedback({ kind: 'decisions', finalizado: true, respostas: { mapa_harness: { formato: pk.formato, base_id: pk.base_id, lote: pk.lote, patches: pk.patches, resumo: pk.resumo } }, resumo_texto: texto.slice(0, 30000) });
        marcarLote(pk.lote);
        toast('Enviado ao app. Agora clique em “Salvar no projeto”, embaixo, para a IA receber.');
        return;
      } catch (e) {}
    }
    marcarLote(pk.lote);
    abrirIO('Copie e cole no chat da IA', texto + '\n\n' + JSON.stringify(pk, null, 1), 'exportar');
  }

  /* ---------- montagem ---------- */
  function montarChips() { // computador: chips (legenda de cor das linhas); celular: um seletor só
    var box = $('mh-chips'), sel = $('mh-linha-sel'); box.innerHTML = ''; if (sel) sel.innerHTML = '';
    modelo.cenarios.forEach(function (c) {
      var l = linha(c.linha); if (!l) return;
      var b = h('button', { type: 'button', 'class': 'mh-chip', role: 'radio', 'aria-checked': String(c.id === ui.cenario), style: '--c:' + l.cor, 'data-cenario': c.id, title: l.gatilho }, [h('i', { 'aria-hidden': 'true' }), l.nome]);
      box.appendChild(b);
      if (sel) { var o = h('option', { value: c.id, texto: l.nome }); if (c.id === ui.cenario) o.selected = true; sel.appendChild(o); }
    });
  }
  function escolherCenario(id) {
    if (!porId(modelo.cenarios, id)) return;
    ui.cenario = id;
    [].forEach.call(doc.querySelectorAll('#mh-chips .mh-chip'), function (b) { b.setAttribute('aria-checked', String(b.getAttribute('data-cenario') === id)); });
    var sel = $('mh-linha-sel'); if (sel && sel.value !== id) sel.value = id;
    reiniciar(); redesenhar(); posicionarTrem(); medirTopo();
  }
  function montarAgora() { // interruptor "mostrar o que está parado agora" (fotografia datada, não é ao vivo)
    var box = $('mh-agora'); if (!box) return; box.innerHTML = '';
    var F = H.foto;
    if (!F) { box.appendChild(h('span', { 'class': 'mh-sw', html: '<span>Sem fotografia nesta versão</span>' })); return; }
    var s = F.sessoes || {}, pd = F.pedidos || {}, rl = F.relatorios || {}, ct = F.cotas || {}, cm = F.comentarios || {};
    var sw = h('button', { type: 'button', id: 'mh-agora-sw', 'class': 'mh-b mh-sw', role: 'switch', 'aria-checked': String(ui.agora),
      title: 'Fotografia de ' + F.quando_txt + ', lida sem gravar nada. Não é ao vivo.',
      'aria-label': 'Mostrar o que está parado agora (fotografia de ' + F.quando_txt + ': ' + (s.total == null ? '?' : s.total) + ' sessões em 24 horas, ' + (pd.total == null ? '?' : pd.total) + ' pedidos no app, ' + (rl.total == null ? '?' : rl.total) + ' relatórios em 24 horas, ' + (cm.pendentes == null ? '?' : cm.pendentes) + ' comentários pendentes' + (ct.maior ? ', cota mais usada ' + ct.maior.conta + ' ' + ct.maior.pct + '%' : '') + ')' },
      [h('i', { 'aria-hidden': 'true' }), h('span', {}, ['Mostrar o que está parado agora', h('small', { texto: 'foto de ' + F.quando_txt.replace(/\/\d{4}/, '') + ' · não é ao vivo' })])]);
    sw.addEventListener('click', function () { definirAgora(!ui.agora); });
    var num = h('button', { type: 'button', id: 'mh-agora-num', 'class': 'mh-b', texto: 'Números', title: 'Números e fontes da fotografia', hidden: ui.agora ? null : '' });
    num.addEventListener('click', function () { abrirDetalhe('agora', null, num); });
    box.appendChild(sw); box.appendChild(num);
  }
  function definirAgora(v) {
    ui.agora = !!v;
    var s = $('mh-agora-sw'); if (s) s.setAttribute('aria-checked', String(ui.agora));
    var n = $('mh-agora-num'); if (n) n.hidden = !ui.agora;
    desenharParados(); aplicarFoco();
    if (ui.detalhe && ui.detalhe.tipo === 'agora') abrirDetalhe('agora');
  }
  function legendaHtml() { // mesma legenda do mapa, para a lista do celular
    var ul = h('ul', { 'class': 'vleg', 'aria-label': 'Legenda' });
    (modelo.legenda || []).forEach(function (it) {
      if (it.id === 'quem') { ul.appendChild(h('li', {}, [h('b', { texto: it.texto + ':' })].concat(usados().map(function (k) { return h('span', {}, [h('span', { 'class': 'mh-sl', texto: modelo.responsaveis[k].sigla }), ' ' + nomeCurto(k)]); })))); return; }
      if (LEG[it.id]) ul.appendChild(h('li', { html: '<svg viewBox="0 0 26 18" aria-hidden="true">' + LEG[it.id] + '</svg>' + esc(it.texto) }));
    });
    return ul;
  }
  function redesenhar() {
    if (ui.lista) desenharLista();
    if (ui.celular) desenharVert(); else desenharMapa();
    atualizarEspaco();
  }
  function definirModo(m) {
    ui.modo = m; ui.tracando = null;
    html.classList.toggle('modo-editar', m === 'editar');
    $('mh-edit').hidden = m !== 'editar';
    [].forEach.call(doc.querySelectorAll('[data-modo]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-modo') === m)); });
    if (m === 'editar') pausar();
    fecharMenu(); fecharDetalhe(); redesenhar(); reiniciar(true); medirTopo();
  }
  function definirReduzido(v, salvarPref) {
    ui.reduzido = v; html.classList.toggle('mov-reduzido', v);
    var b = $('mh-mov'); if (b) { b.setAttribute('aria-pressed', String(v)); b.querySelector('span').textContent = 'Movimento: ' + (v ? 'reduzido' : 'normal'); }
    if (salvarPref) try { localStorage.setItem(CHAVE_MOV, v ? 'reduzido' : 'normal'); } catch (e) {}
  }
  function definirCelular() {
    var c = !!(mq && mq.matches);
    if (c === ui.celular && $('mh-vert').childNodes.length) return;
    ui.celular = c; pausar(); anim.mov = null; arrumarMenu(); redesenhar(); posicionarTrem(); montarRegua(); medirTopo();
  }
  /* celular: Reiniciar, velocidade, Ver/Editar, tema, movimento e "parado agora" vão para o menu ⋯ (P2, P6) */
  var casas = [];
  function arrumarMenu() {
    var menu = $('mh-menu'); if (!menu) return;
    if (!casas.length) ['mh-reiniciar', 'mh-vel', 'mh-modos', 'mh-prefs'].forEach(function (id) { var n = $(id); if (n) { var m = doc.createComment(id); n.parentNode.insertBefore(m, n); casas.push([n, m]); } });
    casas.forEach(function (c) { if (ui.celular || c[0].id !== 'mh-modos') menu.appendChild(c[0]); else c[1].parentNode.insertBefore(c[0], c[1].nextSibling); });
    fecharMenu();
  }
  function fecharMenu() { var m = $('mh-menu'), b = $('mh-menu-btn'); if (m) m.hidden = true; if (b) b.setAttribute('aria-expanded', 'false'); }
  function medirTopo() { // altura da barra presa e do que vem antes do mapa: o mapa inteiro cabe na tela
    var b = $('mh-barra'), pa = $('mh-palco');
    if (b) html.style.setProperty('--mh-barra-h', Math.round(b.getBoundingClientRect().height) + 'px');
    if (pa && ui.modo !== 'editar') html.style.setProperty('--mh-acima', Math.round(pa.getBoundingClientRect().top + (raiz.scrollY || raiz.pageYOffset || 0)) + 'px');
  }
  function deslocarPalco(id) { // o painel não cobre a estação escolhida: o mapa anda para a esquerda (P11)
    var pa = $('mh-palco'); if (!pa) return;
    var dx = 0, atual = ui.dx || 0;
    if (id && !ui.celular) {
      var g = doc.querySelector('#g-est [data-est="' + id + '"]'), det = $('mh-det');
      if (g && det && !det.hidden) { var r = g.getBoundingClientRect(), dr = det.getBoundingClientRect(); if (r.right + atual > dr.left - 16) dx = Math.min(r.right + atual - dr.left + 56, dr.width + 40); }
    }
    ui.dx = Math.round(dx); pa.style.transform = ui.dx ? 'translateX(' + (-ui.dx) + 'px)' : '';
  }
  function iniciar() {
    carregar();
    var mv = lerArmazem(CHAVE_MOV);
    definirReduzido(mv === 'reduzido' || (mv !== 'normal' && !!(mqMov && mqMov.matches)), false);
    ui.cenario = (params.cenario && porId(modelo.cenarios, params.cenario)) ? params.cenario : (porId(modelo.cenarios, modelo.preferencias.cenario_inicial) ? modelo.preferencias.cenario_inicial : modelo.cenarios[0].id);
    ui.celular = !!(mq && mq.matches);
    if (params.tema === 'claro' || params.tema === 'escuro') {
      html.setAttribute('data-tema', params.tema);
      var bt = $('btn-tema'), btx = $('btn-tema-txt');
      if (bt) bt.setAttribute('aria-pressed', String(params.tema === 'claro'));
      if (btx) btx.textContent = 'Tema: ' + params.tema;
    }
    if (params.reduzido === '1') definirReduzido(true, false);
    if (params.agora === '1') ui.agora = true;
    var btT = $('btn-tema'); if (btT) btT.title = 'Tema claro ou escuro';
    arrumarMenu(); montarChips(); montarAgora();
    redesenhar(); reiniciar(); medirTopo();
    if (params.modo === 'editar') definirModo('editar');
    if (params.lista === '1') alternarLista();
    var np = parseInt(params.passo, 10);
    if (np > 0) { for (var i = 0; i < np && anim.i < anim.beats.length - 1; i++) { anim.i++; } chegar(); }
    if (params.sel && est(params.sel)) abrirDetalhe('estacao', params.sel);
    if (params.agora === '1') abrirDetalhe('agora');
    // eventos
    $('mh-tocar').addEventListener('click', tocar);
    $('mh-regua').addEventListener('change', function (ev) { if (ev.target.id === 'mh-parada-sel') irPara(Number(ev.target.value)); });
    $('mh-linha-sel').addEventListener('change', function (ev) { escolherCenario(ev.target.value); });
    $('mh-menu-btn').addEventListener('click', function () { var m = $('mh-menu'), ab = m.hidden; m.hidden = !ab; this.setAttribute('aria-expanded', String(ab)); });
    doc.addEventListener('click', function (ev) { var m = $('mh-menu'); if (m && !m.hidden && !m.contains(ev.target) && !$('mh-menu-btn').contains(ev.target)) fecharMenu(); }, true);
    $('mh-passo').addEventListener('click', passo);
    $('mh-reiniciar').addEventListener('click', function () { reiniciar(); });
    [].forEach.call(doc.querySelectorAll('[data-vel]'), function (b) { b.addEventListener('click', function () {
      var nv = Number(b.getAttribute('data-vel'));
      if (anim.mov && !anim.mov.vert && anim.tocando) { var mvv = anim.mov; mvv.prog = Math.min(1, mvv.prog + (performance.now() - mvv.t0) / (mvv.dur * 1000)); mvv.t0 = performance.now(); mvv.dur = mvv.dur * ui.vel / nv; }
      ui.vel = nv; [].forEach.call(doc.querySelectorAll('[data-vel]'), function (x) { x.setAttribute('aria-pressed', String(x === b)); });
    }); });
    [].forEach.call(doc.querySelectorAll('[data-modo]'), function (b) { b.addEventListener('click', function () { definirModo(b.getAttribute('data-modo')); }); });
    $('mh-lista-btn').addEventListener('click', alternarLista);
    $('mh-mov').addEventListener('click', function () { definirReduzido(!ui.reduzido, true); if (anim.mov) { clearTimeout(anim.timer); cancelAnimationFrame(anim.raf); var pr = anim.mov.pronto; anim.mov = null; chegar(); pr && pr(); } });
    $('mh-chips').addEventListener('click', function (ev) { var b = ev.target.closest('[data-cenario]'); if (b) escolherCenario(b.getAttribute('data-cenario')); });
    $('mh-chips').addEventListener('keydown', function (ev) {
      if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
      var bs = [].slice.call(doc.querySelectorAll('#mh-chips .mh-chip')), i = bs.indexOf(doc.activeElement); if (i < 0) return;
      ev.preventDefault(); var n = bs[(i + (ev.key === 'ArrowRight' ? 1 : bs.length - 1)) % bs.length]; n.focus(); escolherCenario(n.getAttribute('data-cenario'));
    });
    var svg = $('mh-mapa');
    svg.addEventListener('click', function (ev) {
      if (Date.now() - engolirClique < 350) return;
      var t = ev.target;
      var mais = t.closest && t.closest('.mais'); if (mais) { criarDepois(mais.getAttribute('data-linha'), mais.getAttribute('data-depois'), Number(mais.getAttribute('data-x')), Number(mais.getAttribute('data-y'))); return; }
      var pa = t.closest && t.closest('.parado'); if (pa) { abrirDetalhe('agora', null, pa); return; }
      var g = t.closest && t.closest('.est');
      if (g) {
        var id = g.getAttribute('data-est');
        if (ui.tracando) { var e0 = est(id); if (e0.tipo && e0.tipo !== 'estacao') { toast('Placas e depósitos não entram em linha.'); return; } if (ui.tracando.indexOf(id) < 0) ui.tracando.push(id); aplicarFoco(); toast('Nova linha: ' + ui.tracando.map(function (s) { return est(s).nome; }).join(' → '), { rotulo: 'Concluir', fn: concluirTraco }); return; }
        if (ui.modo === 'editar') {
          var antes = linhaDoMais(); ui.sel = id; ui.selLinha = null;
          if (linhaDoMais() !== antes) desenharMapa(true); aplicarFoco();
        }
        abrirDetalhe('estacao', id, doc.querySelector('#g-est [data-est="' + id + '"]')); return;
      }
      var tl = t.closest && t.closest('.trilho-alvo');
      if (tl) { var lid = tl.getAttribute('data-linha'); if (ui.modo === 'editar') { ui.selLinha = lid; ui.sel = null; desenharMapa(); } abrirDetalhe('linha', lid); return; }
    });
    svg.addEventListener('dblclick', function (ev) { if (ui.modo !== 'editar') return; var g = ev.target.closest && ev.target.closest('.est'); if (g) { ev.preventDefault(); renomear(g.getAttribute('data-est')); } });
    svg.addEventListener('pointerdown', aoBaixar);
    svg.addEventListener('pointermove', aoMover);
    svg.addEventListener('pointerup', aoSoltar);
    svg.addEventListener('pointercancel', aoSoltar);
    svg.addEventListener('focusin', function (ev) { var g = ev.target.closest && ev.target.closest('.est'); if (g && !anim.tocando) ligar(g.getAttribute('data-est'), true); });
    svg.addEventListener('focusout', function (ev) { var g = ev.target.closest && ev.target.closest('.est'); if (g && !anim.tocando && ui.sel !== g.getAttribute('data-est')) ligar(g.getAttribute('data-est'), false); });
    svg.addEventListener('mouseover', function (ev) { var g = ev.target.closest && ev.target.closest('.est'); if (g && !anim.tocando && !arr) ligar(g.getAttribute('data-est'), true); });
    svg.addEventListener('mouseout', function (ev) { var g = ev.target.closest && ev.target.closest('.est'); if (g && !anim.tocando && ui.sel !== g.getAttribute('data-est')) ligar(g.getAttribute('data-est'), false); });
    svg.addEventListener('keydown', function (ev) {
      var g = ev.target.closest && ev.target.closest('.est, .mais, .parado'); if (!g) return;
      if (g.classList.contains('mais') || g.classList.contains('parado')) { if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); g.dispatchEvent(new MouseEvent('click', { bubbles: true })); } return; }
      var id = g.getAttribute('data-est'), e = est(id);
      if (ev.key === 'Enter' || ev.key === ' ') { ev.preventDefault(); if (ui.modo === 'editar' && ev.key === 'Enter') renomear(id); else abrirDetalhe('estacao', id, g); return; }
      if (ui.modo !== 'editar') return;
      var passoPx = ev.shiftKey ? 1 : 10, dx = 0, dy = 0;
      if (ev.key === 'ArrowLeft') dx = -passoPx; else if (ev.key === 'ArrowRight') dx = passoPx; else if (ev.key === 'ArrowUp') dy = -passoPx; else if (ev.key === 'ArrowDown') dy = passoPx;
      if (dx || dy) { ev.preventDefault(); ui.sel = id; fazer({ op: 'mover', estacao: id, x: e.x + dx, y: e.y + dy }, { juntar: true }); var g2 = doc.querySelector('#g-est [data-est="' + id + '"]'); if (g2) g2.focus(); return; }
      if (ev.key === 'Delete' || ev.key === 'Backspace') { ev.preventDefault(); remover(id); }
    });
    $('mh-vert').addEventListener('click', function (ev) {
      var b = ev.target.closest('[data-est]'); if (b) { abrirDetalhe('estacao', b.getAttribute('data-est'), b); return; }
      var a = ev.target.closest('[data-acao="v-add"]'); if (a) { var l = linhaAtual(); criarDepois(l.id, l.estacoes[l.estacoes.length - 1]); }
    });
    $('mh-agora').addEventListener('keydown', function () {});
    doc.addEventListener('keydown', function (ev) {
      var tag = (ev.target && ev.target.tagName) || '';
      if ((ev.ctrlKey || ev.metaKey) && !ev.shiftKey && (ev.key === 'z' || ev.key === 'Z') && ui.modo === 'editar' && !/INPUT|TEXTAREA|SELECT/.test(tag)) { ev.preventDefault(); desfazer(); return; }
      if (ev.key === 'Escape' && !$('mh-menu').hidden) { fecharMenu(); $('mh-menu-btn').focus(); return; }
      if (ev.key === 'Escape') { if (ui.tracando) { ui.tracando = null; $('mh-palco').classList.remove('mh-tracando'); aplicarFoco(); toast('Nova linha cancelada.'); return; } if (!$('mh-io').hidden) { fecharIO(); return; } fecharDetalhe(); }
      if (ev.key === 'Enter' && ui.tracando && !/INPUT|TEXTAREA|SELECT|BUTTON/.test(tag)) { ev.preventDefault(); concluirTraco(); }
    });
    $('mh-desfazer').addEventListener('click', desfazer);
    $('mh-nova-linha').addEventListener('click', function () {
      if (ui.celular) { toast('Para criar linha, use o computador (precisa clicar nas estações no mapa).'); return; }
      ui.tracando = []; fecharDetalhe(); $('mh-palco').classList.add('mh-tracando'); desenharMapa();
      toast('Clique nas estações na ordem da nova linha. Enter conclui, Esc cancela.', { rotulo: 'Concluir', fn: concluirTraco });
    });
    $('mh-exportar').addEventListener('click', function () { var pk = pacote(); if (!pk.patches.length) { toast('Nenhuma mudança para exportar ainda.'); return; } marcarLote(pk.lote); abrirIO('Exportar mudanças', JSON.stringify(pk, null, 1), 'exportar'); });
    $('mh-importar').addEventListener('click', function () { abrirIO('Importar mudanças', '', 'importar'); });
    $('mh-enviar').addEventListener('click', enviar);
    if (mq) { var cb = function () { definirCelular(); }; if (mq.addEventListener) mq.addEventListener('change', cb); else if (mq.addListener) mq.addListener(cb); }
    raiz.addEventListener('resize', function () { medirTopo(); if (ui.celular) { posicionarVolta(); desenharVertAnim(); } });
    raiz.addEventListener('pagehide', function () { if (salvarT) salvarJa(); });
    doc.addEventListener('visibilitychange', function () { if (doc.visibilityState === 'hidden' && salvarT) salvarJa(); });
    raiz.__mapaHarness = { ui: ui, anim: anim, modelo: function () { return modelo; }, ops: function () { return ops; }, tocar: tocar, pausar: pausar, passo: passo, reiniciar: reiniciar,
      escolher: escolherCenario, modo: definirModo, reduzido: definirReduzido, fazer: fazer, desfazer: desfazer, pacote: pacote, importarTexto: importarTexto, enviar: enviar,
      posTrem: function () { var t = $('mh-trem'); if (!t) return null; var m = /translate\(([-\d.]+)[ ,]+([-\d.]+)\)/.exec(t.getAttribute('transform') || ''); return m ? { x: Number(m[1]), y: Number(m[2]) } : null; },
      ptEst: function (id) { return ptEst(id, linhaAtual() && linhaAtual().id); }, medir: function () { return medir(textoRascunho()); } };
  }
  function linhaDoMais() { var l = linha(ui.selLinha) || (ui.sel && linhasDa(ui.sel)[0]); return l ? l.id : ''; }
  function concluirTraco() {
    var tr = ui.tracando; if (!tr) return;
    $('mh-palco').classList.remove('mh-tracando');
    ui.tracando = null;
    if (tr.length < 2) { aplicarFoco(); toast('Uma linha precisa de pelo menos 2 estações. Nada foi criado.'); return; }
    var usadas = modelo.linhas.map(function (l) { return l.cor.toLowerCase(); });
    var cor = PALETA.filter(function (c) { return usadas.indexOf(c.toLowerCase()) < 0; })[0] || PALETA[modelo.linhas.length % PALETA.length];
    var id = novoId('l'), n = modelo.linhas.length + 1;
    if (fazer({ op: 'nova_linha', id: id, nome: 'Nova linha ' + n, cor: cor, estacoes: tr })) {
      montarChips(); ui.selLinha = id; escolherCenario('c_' + id); desenharMapa(); abrirDetalhe('linha', id);
      toast('Linha criada. Dê um nome a ela no painel.');
    }
  }
  function alternarLista() {
    ui.lista = !ui.lista;
    $('mh-lista').hidden = !ui.lista;
    $('mh-mapa').style.display = ui.lista ? 'none' : '';
    $('mh-vert').style.display = ui.lista ? 'none' : '';
    var b = $('mh-lista-btn'); b.setAttribute('aria-pressed', String(ui.lista)); b.textContent = ui.lista ? 'Mapa' : 'Lista'; b.title = ui.lista ? 'Voltar ao mapa' : 'Ver a mesma informação em tabela';
    if (ui.lista) desenharLista();
  }

  try { iniciar(); }
  catch (e) {
    var n = $('mh-narra-tx'); if (n) n.textContent = 'O mapa não conseguiu iniciar: ' + e.message + '. A lista abaixo continua disponível.';
    try { var ls = $('mh-lista'); ui.lista = false; alternarLista(); } catch (x) {}
  }
})(typeof window !== 'undefined' ? window : this);
