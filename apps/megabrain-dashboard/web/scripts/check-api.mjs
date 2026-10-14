// Read-only contract smoke check. Pairing exchanges a local key for a session;
// credentials and project contents are never printed or written by this script.
import { readFile } from 'node:fs/promises';
const origin='http://127.0.0.1:8766';
const nativeKey=(await readFile(new URL('../../data/.private/native.key',import.meta.url),'utf8')).trim();
const anonymous=await fetch(`${origin}/api/projects`);
if(anonymous.status!==401)throw new Error(`Anonymous project access should be 401, received ${anonymous.status}`);
const paired=await fetch(`${origin}/api/pair`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:nativeKey})});
if(!paired.ok)throw new Error(`Pairing failed (${paired.status})`);
const cookie=paired.headers.get('set-cookie')?.split(';')[0];
if(!cookie)throw new Error('Pair response did not set a session cookie');
const get=async path=>{const r=await fetch(`${origin}/api${path}`,{headers:{Cookie:cookie}});if(!r.ok)throw new Error(`${path} returned ${r.status}`);return r.json();};
const session=await get('/session');
if(!session.authenticated||!session.csrf)throw new Error('Authenticated session contract incomplete');
const p=await get('/projects');const w=await get('/workspace');const j=await get('/jobs');const guide=await get('/guide');const connection=await get('/connection');
if(!Array.isArray(p.projects)||typeof w.revision!=='number'||!w.data||!Array.isArray(j.jobs)||!Array.isArray(guide.sections))throw new Error('Top-level contract differs');
const checks={anonymous_projects_blocked:true,session_csrf:true,project_count:p.projects.length,workspace_versioned:true,jobs_array:true,guide_sections:guide.sections.length,connection_configured:Boolean(connection.remote_url)};
if(p.projects.length){const id=p.projects[0].id;const detail=await get(`/projects/${id}`);const routing=await get(`/projects/${id}/routing`);if(!Array.isArray(detail.deliveries)||!Array.isArray(detail.assets)||!Array.isArray(routing.data?.routes))throw new Error('Project or routing contract differs');checks.route_categories=routing.data.routes.map(r=>r.id);checks.required_stage_flags=routing.data.routes.every(r=>r.stages.some(s=>s.required));checks.stage_shape=Object.keys(routing.data.routes[0]?.stages[0]||{});}
console.log(JSON.stringify(checks,null,2));
