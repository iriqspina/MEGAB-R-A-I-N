// Gesto de mover/redimensionar compartilhado pelas três grades (home, quadro do projeto e Respostas).
// Fora do gesto o texto continua selecionável; durante o gesto a classe no <html> desliga a seleção e
// os iframes (que engoliriam o ponteiro). A classe sai no fim do gesto, no cancelamento, ao perder o
// foco da janela (depois de terminar o Draggable) e na desmontagem da grade que o iniciou.
import {useEffect,useMemo,type Ref} from 'react';

export const RESIZE_ALL=['n','s','e','w','ne','nw','se','sw'] as const;
export const RESIZE_NARROW=['s'] as const;
export type ResizeAxis=typeof RESIZE_ALL[number];
/** Controles internos nunca iniciam arraste; a alça é só o título. */
export const DRAG_CANCEL='button,input,textarea,select,a,iframe,summary,[contenteditable],.react-resizable-handle';
/** Títulos que servem de alça nas três grades. */
export const HANDLE_TITLES='.module-head,.home-panel-title,.response-window-title';
const GESTURE='mb-grid-gesture';
let release:null|(()=>void)=null;
/** Grade dona do gesto em curso: a desmontagem de outra grade (painel fechado, poll) não encerra o gesto alheio. */
let owner:object|null=null;
let lastMouse:MouseEventInit|null=null;
let lastTouches:Touch[]|null=null;
let stopTimer:ReturnType<typeof setTimeout>|null=null;
let terminating=false;

function remember(event?:Event){
  if(!event)return;
  if(typeof TouchEvent!=='undefined'&&event instanceof TouchEvent){lastTouches=Array.from(event.changedTouches.length?event.changedTouches:event.touches);lastMouse=null;return;}
  if(event instanceof MouseEvent&&Number.isFinite(event.clientX)&&Number.isFinite(event.clientY)){
    lastMouse={clientX:event.clientX,clientY:event.clientY,screenX:event.screenX,screenY:event.screenY,ctrlKey:event.ctrlKey,altKey:event.altKey,shiftKey:event.shiftKey,metaKey:event.metaKey};lastTouches=null;
  }
}

/** Cancelar sem mouseup real precisa terminar o Draggable com a última posição real, antes de liberar os iframes. */
function terminate(){
  if(!owner||terminating)return;
  if(!lastMouse&&!lastTouches?.length)return; // Sem evento real nunca fabricar (0,0).
  terminating=true;
  try{
    if(lastTouches?.length)document.dispatchEvent(new TouchEvent('touchend',{bubbles:true,cancelable:true,changedTouches:lastTouches,touches:[],targetTouches:[]}));
    else if(lastMouse)document.dispatchEvent(new MouseEvent('mouseup',{...lastMouse,bubbles:true,cancelable:true,view:window,button:0,buttons:0}));
  }finally{terminating=false;endGridGesture();}
}

/** Sem `by`, encerra qualquer gesto (fim do ponteiro, cancelamento, janela sem foco). Com `by`, só o da própria grade. */
export function endGridGesture(by?:object){
  if(typeof document==='undefined')return;
  if(by&&owner&&by!==owner)return;
  if(terminating)return; // onDragStop/onResizeStop pode entrar aqui durante o dispatch acima.
  owner=null;document.documentElement.classList.remove(GESTURE);
  const done=release;release=null;done?.();
  lastMouse=null;lastTouches=null;if(stopTimer!==null){clearTimeout(stopTimer);stopTimer=null;}
}

export function beginGridGesture(by?:object,start?:Event){
  if(typeof document==='undefined')return;
  owner=by||{};remember(start);document.documentElement.classList.add(GESTURE);
  // Uma seleção iniciada pelo próprio gesto (texto do título) não fica grifada.
  const selection=window.getSelection();const anchor=selection?.anchorNode;const from=anchor instanceof Element?anchor:anchor?.parentElement;
  if(selection&&!selection.isCollapsed&&from?.closest(`.mb-layout-handle,${HANDLE_TITLES}`))selection.removeAllRanges();
  if(release)return;
  const track=(event:Event)=>remember(event);
  // A limpeza de fallback acontece depois dos handlers do Draggable no documento.
  const stop=(event:Event)=>{remember(event);const ending=owner;if(stopTimer!==null)clearTimeout(stopTimer);stopTimer=setTimeout(()=>{stopTimer=null;if(owner===ending)endGridGesture();},0);};
  window.addEventListener('pointermove',track,true);window.addEventListener('mousemove',track,true);window.addEventListener('touchmove',track,true);
  window.addEventListener('pointerup',track,true);window.addEventListener('pointercancel',terminate,true);window.addEventListener('mouseup',stop,true);window.addEventListener('touchend',stop,true);window.addEventListener('touchcancel',terminate,true);window.addEventListener('blur',terminate);
  release=()=>{window.removeEventListener('pointermove',track,true);window.removeEventListener('mousemove',track,true);window.removeEventListener('touchmove',track,true);window.removeEventListener('pointerup',track,true);window.removeEventListener('pointercancel',terminate,true);window.removeEventListener('mouseup',stop,true);window.removeEventListener('touchend',stop,true);window.removeEventListener('touchcancel',terminate,true);window.removeEventListener('blur',terminate);};
}

/**
 * Início e fim do gesto marcados com a identidade desta grade. A desmontagem só limpa o gesto
 * que ela mesma iniciou.
 */
export function useGridGesture(){
  const token=useMemo(()=>({}),[]);
  useEffect(()=>()=>endGridGesture(token),[token]);
  return useMemo(()=>({begin:(...args:unknown[])=>{let event:Event|undefined;for(const arg of args){if(arg instanceof Event){event=arg;break;}if(arg&&typeof arg==='object'&&'nativeEvent' in arg&&arg.nativeEvent instanceof Event){event=arg.nativeEvent;break;}}beginGridGesture(token,event);},end:()=>endGridGesture(token)}),[token]);
}

/**
 * Alça de redimensionamento com área de toque e cursor direcional. Marcada para o comentário por
 * segurar (CursorTools: [data-cf-ignorar]) e para a exclusão local (.mb-layout-handle).
 */
export function resizeHandle(axis:string,ref:Ref<HTMLElement>){
  return <span ref={ref as Ref<HTMLSpanElement>} className={`react-resizable-handle react-resizable-handle-${axis} mb-layout-handle mb-resize-${axis}`} data-cf-ignorar="" aria-hidden="true"/>;
}
