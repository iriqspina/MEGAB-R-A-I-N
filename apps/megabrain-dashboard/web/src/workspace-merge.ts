// Merge independent saves. Conflicting human edits still require a decision.
export function mergeWorkspace(base:Record<string,unknown>,local:Record<string,unknown>,remote:Record<string,unknown>):Record<string,unknown>|null{
  let conflict=false;
  const same=(a:unknown,b:unknown)=>JSON.stringify(a)===JSON.stringify(b);
  function merge(a:unknown,b:unknown,c:unknown,key=''):unknown{
    if(same(b,c))return b;if(same(a,b))return c;if(same(a,c))return b;
    if((key==='returnCursor'||key==='notificationReadId')&&typeof b==='number'&&typeof c==='number')return Math.max(b,c);
    if(a&&b&&c&&typeof a==='object'&&typeof b==='object'&&typeof c==='object'&&!Array.isArray(a)&&!Array.isArray(b)&&!Array.isArray(c)){
      const aa=a as Record<string,unknown>,bb=b as Record<string,unknown>,cc=c as Record<string,unknown>;
      return Object.fromEntries([...new Set([...Object.keys(aa),...Object.keys(bb),...Object.keys(cc)])].map(k=>[k,merge(aa[k],bb[k],cc[k],k)]));
    }
    conflict=true;return b;
  }
  const result=merge(base,local,remote) as Record<string,unknown>;return conflict?null:result;
}
