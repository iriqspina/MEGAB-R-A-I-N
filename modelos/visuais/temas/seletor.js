/* Persistência com três quedas: localStorage → sessionStorage → memória.
   Necessário porque em file:// o Safari LANÇA SecurityError no localStorage
   (só sessionStorage passa) e o Chrome compartilha UMA origem entre todos os
   arquivos locais — daí o namespace na chave. */
(function(){
  var R=document.documentElement, K='mb-relatorio:';
  var mem={};
  function get(k){ try{ var v=localStorage.getItem(K+k); if(v!=null) return v; }catch(e){}
                   try{ var s=sessionStorage.getItem(K+k); if(s!=null) return s; }catch(e){}
                   return mem[k]||null; }
  function set(k,v){ mem[k]=v;
    try{ v==null?localStorage.removeItem(K+k):localStorage.setItem(K+k,v); return; }catch(e){}
    try{ v==null?sessionStorage.removeItem(K+k):sessionStorage.setItem(K+k,v); }catch(e){} }

  function aplica(tema,modo){
    if(tema) R.setAttribute('data-tema',tema);
    if(modo){ R.setAttribute('data-modo',modo); R.style.colorScheme=modo==='escuro'?'dark':'light'; }
    else{ R.removeAttribute('data-modo'); R.style.colorScheme='light dark'; }
  }
  function sistemaEscuro(){ try{ return matchMedia('(prefers-color-scheme: dark)').matches; }catch(e){ return false; } }

  function marca(grupo,valor){
    document.querySelectorAll('[data-grupo="'+grupo+'"]').forEach(function(b){
      b.setAttribute('aria-checked', String(b.dataset.valor===valor));
    });
  }
  function dica(){
    var d=document.querySelector('[data-dica-modo]'); if(!d) return;
    var m=R.getAttribute('data-modo');
    d.textContent = m ? '' : 'sistema → ' + (sistemaEscuro()?'escuro':'claro');
  }

  var tema=get('tema')||R.getAttribute('data-tema')||'01-editorial';
  var modo=get('modo');
  aplica(tema,modo); marca('tema',tema); marca('modo',modo||'sistema');

  document.addEventListener('click',function(ev){
    var b=ev.target.closest('[data-grupo]'); if(!b||b.disabled) return;
    var g=b.dataset.grupo, v=b.dataset.valor;
    if(g==='tema'){ set('tema',v); aplica(v,R.getAttribute('data-modo')); marca('tema',v); }
    else{
      // Regra da Lea Verou: se a escolha coincide com o sistema, NÃO grave —
      // gravar converte um ajuste temporário em pin permanente sem saída.
      var coincide = (v==='escuro')===sistemaEscuro();
      var efetivo = (v==='sistema'||coincide) ? null : v;
      set('modo',efetivo); aplica(null,efetivo); marca('modo',efetivo||'sistema');
    }
    dica();
  });

  // preview ao vivo no hover (padrão VS Code), revertido ao sair sem clicar
  var antes=null;
  document.addEventListener('mouseover',function(ev){
    var b=ev.target.closest('[data-grupo="tema"]'); if(!b||b.disabled) return;
    if(antes===null) antes=R.getAttribute('data-tema');
    R.setAttribute('data-tema', b.dataset.valor);
  });
  document.addEventListener('mouseout',function(ev){
    var b=ev.target.closest('[data-grupo="tema"]'); if(!b||antes===null) return;
    if(ev.relatedTarget && ev.relatedTarget.closest && ev.relatedTarget.closest('[data-grupo="tema"]')) return;
    R.setAttribute('data-tema', antes); antes=null;
  });
  dica();
})();
