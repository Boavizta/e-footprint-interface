const path = require("node:path");
const { promisify } = require("node:util");
const { execFile } = require("node:child_process");
const fs = require("node:fs/promises");
const vscode = require("vscode");

const git = promisify(execFile);
const originalScheme = "plan-main";

function isAllowedFile(file, repoRoot) {
  if (vscode.workspace.getWorkspaceFolder(file)) return true;

  const repositoryNames = new Set(["e-footprint", "e-footprint-interface"]);
  return (vscode.workspace.workspaceFolders || []).some(({ uri }) =>
    repositoryNames.has(path.basename(uri.fsPath))
    && repositoryNames.has(path.basename(repoRoot))
    && path.dirname(uri.fsPath) === path.dirname(repoRoot)
  );
}

async function handleDiff(uri) {
  if (uri.path !== "/diff") return;

  const query = new URLSearchParams(uri.query);
  const filePath = query.get("path");
  if (!filePath || !path.isAbsolute(filePath)) {
    throw new Error("The link does not contain an absolute file path.");
  }

  const file = vscode.Uri.file(filePath);
  if (!(await fs.stat(filePath)).isFile()) {
    throw new Error("The linked path is not a file.");
  }

  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  const relativePath = path.relative(repoRoot, filePath);
  if (!relativePath || relativePath.startsWith(`..${path.sep}`) || path.isAbsolute(relativePath)) {
    throw new Error("The linked file is outside its Git repository.");
  }
  if (!isAllowedFile(file, repoRoot)) {
    throw new Error("Open e-footprint-interface, e-footprint, or their shared workspace in VS Code first.");
  }
  await git("git", ["-C", repoRoot, "rev-parse", "--verify", "main^{commit}"]);

  let existsOnMain = true;
  try {
    await git("git", ["-C", repoRoot, "cat-file", "-e", `main:${relativePath}`]);
  } catch {
    existsOnMain = false;
  }
  const original = file.with({
    scheme: originalScheme,
    query: JSON.stringify({ repoRoot, relativePath, existsOnMain }),
  });

  const line = Number(query.get("line"));
  const column = Number(query.get("column") || 1);
  const options = Number.isInteger(line) && line > 0 && Number.isInteger(column) && column > 0
    ? { selection: new vscode.Range(line - 1, column - 1, line - 1, column - 1) }
    : undefined;
  await vscode.commands.executeCommand(
    "vscode.diff",
    original,
    file,
    `${path.basename(filePath)} (main ↔ working tree)`,
    options,
  );
}

function activate(context) {
  context.subscriptions.push(vscode.workspace.registerTextDocumentContentProvider(originalScheme, {
    async provideTextDocumentContent(uri) {
      const { repoRoot, relativePath, existsOnMain } = JSON.parse(uri.query);
      if (!existsOnMain) return "";
      const { stdout } = await git("git", ["-C", repoRoot, "show", `main:${relativePath}`], {
        maxBuffer: 10 * 1024 * 1024,
      });
      return stdout;
    },
  }));
  context.subscriptions.push(vscode.window.registerUriHandler({
    async handleUri(uri) {
      try {
        await handleDiff(uri);
      } catch (error) {
        vscode.window.showErrorMessage(`Could not open diff vs main: ${error.message}`);
      }
    },
  }));
}

module.exports = { activate };
