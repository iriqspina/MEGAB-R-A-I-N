import type { Workspace } from './types';
export type DockPosition='left'|'right'|'top'|'bottom';
export type RailMode='expanded'|'icons'|'hidden';
export function workspacePreferences(ws:Workspace){
  const positions:DockPosition[]=['left','right','top','bottom'];
  const modes:RailMode[]=['expanded','icons','hidden'];
  return {
    position:positions.includes(ws.railPosition as DockPosition)?ws.railPosition as DockPosition:'left',
    mode:modes.includes(ws.railMode as RailMode)?ws.railMode as RailMode:'expanded',
    theme:ws.theme==='light'?'light':'dark',
    spacing:ws.spacing===70?70:ws.spacing===100?100:75,
  };
}
