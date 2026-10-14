/** The built-in PDF viewer cannot render inside a sandboxed frame.
 * Only catalogued, same-origin binary-file routes may use that viewer.
 * HTML and all other previews retain their existing sandbox.
 */
export function isLocalPdfPreview(type:string|undefined,value:string,origin:string):boolean{
  if(type!=='pdf')return false;
  try{const url=new URL(value,origin);return url.origin===origin&&!url.username&&!url.password&&!url.search&&!url.hash&&/^\/api\/files\/[a-f0-9]{20}$/.test(url.pathname);}catch{return false;}
}
