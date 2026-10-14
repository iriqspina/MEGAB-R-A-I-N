import type { Asset } from './types';
const normalized=(path:string)=>path.replaceAll('\\','/').replace(/\/$/,'').toLowerCase();
export function resultAsset(result:{path?:string|null;file_id?:string|null},assets:Asset[],source:string):Asset|undefined {
  if(result.file_id){const exact=assets.filter(asset=>asset.id===result.file_id);if(exact.length===1)return exact[0];}
  if(!result.path)return undefined;
  const root=normalized(source).split('/evidence/')[0];
  if(root===normalized(source))return undefined;
  const expected=normalized(result.path);
  const matches=assets.filter(asset=>asset.origin && normalized(/^(?:[a-z]:[\\/]|\/)/i.test(asset.origin)?asset.origin:root+'/'+asset.origin)===expected);
  return matches.length===1?matches[0]:undefined;
}
