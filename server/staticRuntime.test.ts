import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

const rootDir = path.resolve(import.meta.dirname, "..");

function readProjectFile(relativePath: string) {
  return fs.readFileSync(path.join(rootDir, relativePath), "utf8");
}

describe("production static runtime", () => {
  it("keeps Vite out of the production entrypoint static dependency graph", () => {
    const entrypoint = readProjectFile("server/_core/index.ts");

    expect(entrypoint).toContain('from "./static"');
    expect(entrypoint).not.toMatch(/import\s+\{[^}]*setupVite[^}]*\}\s+from\s+["']\.\/vite["']/);
    expect(entrypoint).not.toMatch(/import\s+[^;]*from\s+["']vite["']/);
    expect(entrypoint).toContain("new Function");
  });

  it("serves production assets from a module that does not import Vite", () => {
    const staticModule = readProjectFile("server/_core/static.ts");
    const viteModule = readProjectFile("server/_core/vite.ts");

    expect(staticModule).toContain("export function serveStatic");
    expect(staticModule).toContain("express.static");
    expect(staticModule).not.toMatch(/from\s+["']vite["']/);
    expect(viteModule).not.toContain("export function serveStatic");
  });
});
