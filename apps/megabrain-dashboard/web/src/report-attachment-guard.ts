export const REPORT_BEFORE_CLOSE='mb-report-before-close';
/** The mounted editor may retain a File that has not reached the server yet. */
export function mayCloseReport(pid:string,fid?:string):boolean{return window.dispatchEvent(new CustomEvent(REPORT_BEFORE_CLOSE,{cancelable:true,detail:{pid,fid}}));}
