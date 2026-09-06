/** A policy PDF filename as shown in the UI — drop the `.pdf`, keep the rest. */
export function documentName(filename: string): string {
  return filename.replace(/\.pdf$/i, "");
}
