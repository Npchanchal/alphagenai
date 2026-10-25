/** Which workbench tab this seat may open. A desk read stays open. Writes follow the feature. */

export function deskTabVisible(id: string, has: (feature: string) => boolean): boolean {
  switch (id) {
    case "labeling":
      return has("labeling");
    case "feedback":
      return has("feedback");
    case "import":
      return has("desk_write");
    case "wordmap":
      return has("wordmap");
    case "vernacular":
      return has("vernacular");
    case "reports":
      return has("ic_export");
    case "console":
    case "review":
    case "corpus":
    case "pit":
    case "parameters":
    case "csm":
      return true;
    default:
      return false;
  }
}
