const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),{test}=require('node:test'),ts=require('typescript');
require.extensions['.ts']=function(module,file){module._compile(ts.transpileModule(fs.readFileSync(file,'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText,file);};
const {deliveryStatusLabel,deliveryStateText,deliveryCaption,deliveryOrigin,shortDate}=require('../src/status-labels.ts');

test('codigo interno de estado vira texto humano, nunca o codigo cru',()=>{
 assert.equal(deliveryStatusLabel('nao_verificado'),'Ainda não conferido');
 assert.equal(deliveryStatusLabel('em_revisao'),'Em revisão');
 assert.equal(deliveryStatusLabel('pronto'),'Pronto');
 assert.equal(deliveryStatusLabel('rascunho'),'Rascunho');
 assert.equal(deliveryStatusLabel('arquivado'),'Arquivado');
 assert.equal(deliveryStatusLabel(undefined),'');
 const unknown=deliveryStatusLabel('aguardando_teste_manual');
 assert.ok(!unknown.includes('_'));assert.equal(unknown,'Aguardando teste manual');
});

test('so diz conferido quando o registro marca a entrega como conferida',()=>{
 assert.equal(deliveryStateText({status:'nao_verificado',verified:false}),'Ainda não conferido');
 assert.equal(deliveryStateText({status:'pronto',verified:true}),'Pronto · conferido');
 assert.equal(deliveryStateText({status:'em_revisao'}),'Em revisão');
 assert.equal(deliveryStateText({}),'Ainda não conferido');
 assert.equal(deliveryStateText({verified:true}),'Conferido');
});

test('legenda da biblioteca: resumo real vale, frase padrao da central some',()=>{
 assert.equal(deliveryCaption({summary:'Revisão final do layout'}),'Revisão final do layout');
 const boiler=deliveryCaption({summary:'Relatório encontrado no projeto; verificação não registrada.',session:'Origem não registrada',updated_at:'2026-10-16T13:20:00Z'});
 assert.ok(!/verifica/i.test(boiler));assert.equal(boiler,shortDate('2026-10-16T13:20:00Z'));assert.ok(boiler.length>0);
 const history=deliveryCaption({summary:'Relatório do histórico; verificação não registrada.',session:'Sessão Marcelinho',updated_at:'2026-10-16T13:20:00Z'});
 assert.ok(history.endsWith('Sessão Marcelinho'));assert.ok(!/verifica/i.test(history));
 assert.equal(deliveryCaption({summary:'verificação não registrada'}),'Resultado do projeto');
 assert.equal(deliveryCaption({summary:'Consultar a pasta; estado ainda não classificado.',session:'Sessão A',updated_at:'2026-10-16T13:20:00Z'}),shortDate('2026-10-16T13:20:00Z')+' · Sessão A');
 assert.equal(deliveryCaption({session:'Origem não registrada'}),'Resultado do projeto');
 assert.equal(deliveryCaption({session:'não informada',updated_at:'2026-10-16T13:20:00Z'}),shortDate('2026-10-16T13:20:00Z'));
 assert.equal(deliveryOrigin('Origem não registrada'),'');assert.equal(deliveryOrigin('não informada'),'');assert.equal(deliveryOrigin(undefined),'');assert.equal(deliveryOrigin(' Sessão Marcelinho '),'Sessão Marcelinho');
});

test('data invalida ou ausente nao vira texto',()=>{
 assert.equal(shortDate(undefined),'');assert.equal(shortDate('nao e data'),'');assert.ok(shortDate('2026-10-16T13:20:00Z').length>0);
});
