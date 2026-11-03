const path = require("node:path");
const os = require("node:os");
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

/** The absolute file a route's query names: `path` as given, or `repo` — a path from the
 *  repository root, sent by a served page (PyCharm's "open in browser") that cannot know its
 *  folder on disk — in the first open workspace folder that holds it. */
async function fileFromQuery(query) {
  const filePath = query.get("path");
  if (filePath) {
    if (!path.isAbsolute(filePath)) throw new Error("The link does not contain an absolute file path.");
    return filePath;
  }
  const repoPath = query.get("repo");
  if (!repoPath || path.isAbsolute(repoPath) || repoPath.split("/").includes("..")) {
    throw new Error("The link does not name a file.");
  }
  for (const { uri } of vscode.workspace.workspaceFolders || []) {
    const candidate = path.join(uri.fsPath, repoPath);
    if (await fs.stat(candidate).then((s) => s.isFile(), () => false)) return candidate;
  }
  throw new Error(`No open workspace folder holds ${repoPath}; open the repository in VS Code first.`);
}

/** The cursor position a route's `line` / `column` ask for, if any. */
function selectionAt(query) {
  const line = Number(query.get("line"));
  const column = Number(query.get("column") || 1);
  return Number.isInteger(line) && line > 0 && Number.isInteger(column) && column > 0
    ? new vscode.Range(line - 1, column - 1, line - 1, column - 1)
    : undefined;
}

/** A plain click from a served page: open the file at the line, as `vscode://file/` does for an
 *  absolute path. */
async function handleOpen(uri) {
  if (uri.path !== "/open") return false;
  const query = new URLSearchParams(uri.query);
  await vscode.window.showTextDocument(vscode.Uri.file(await fileFromQuery(query)), { selection: selectionAt(query) });
  return true;
}

async function handleDiff(uri) {
  if (uri.path !== "/diff") {
    const { version } = require("./package.json");
    throw new Error(`unknown route "${uri.path}" (extension ${version}); reload the window if it was just updated.`);
  }

  const query = new URLSearchParams(uri.query);
  const filePath = await fileFromQuery(query);

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

  const selection = selectionAt(query);
  const options = selection ? { selection } : undefined;
  await vscode.commands.executeCommand(
    "vscode.diff",
    original,
    file,
    `${path.basename(filePath)} (main ↔ working tree)`,
    options,
  );
}

/** The `it(` / `test(` / `describe(` call at or just after `line`, as vitest's -t wants it. */
function testNameAt(source, line) {
  const lines = source.split(/\r?\n/);
  const call = /^\s*(?:it|test|describe)(?:\.(?:only|skip|each|skipIf|runIf)(?:\([^)]*\))?)?\s*\(\s*(['"`])((?:\\.|(?!\1).)*)\1/;
  for (let i = line - 1; i < Math.min(lines.length, line + 2); i += 1) {
    const match = lines[i]?.match(call);
    if (match) return match[2].replace(/\\(['"`])/g, "$1");
  }
  return null;
}

/** Which vitest config runs a test file: the db and migrations suites have their own. */
function configFor(relativePath) {
  if (relativePath.startsWith("tests/db/")) return ["--config", "vitest.db.config.ts"];
  if (relativePath.startsWith("tests/migrations/")) return ["--config", "vitest.migrations.config.ts"];
  return [];
}

async function handleDebugTest(uri) {
  if (uri.path !== "/debug-test") return false;

  const query = new URLSearchParams(uri.query);
  const filePath = await fileFromQuery(query);
  const file = vscode.Uri.file(filePath);
  const folder = vscode.workspace.getWorkspaceFolder(file);
  if (!folder) throw new Error("Open the repository in VS Code first.");

  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  const relativePath = path.relative(repoRoot, filePath).split(path.sep).join("/");
  const line = Number(query.get("line"));
  const source = await fs.readFile(filePath, "utf8");
  const name = Number.isInteger(line) && line > 0 ? testNameAt(source, line) : null;

  const args = ["run", ...configFor(relativePath), relativePath];
  if (name) args.push("-t", name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));

  // `break=<path>:<line>|<path>:<line>` — the narrative's watch points, absolute from a page
  // opened as a file, from the repository root from a served one.
  // Each becomes a source breakpoint unless one is already set on that line, so
  // the debugger stops where the narrative says to look; the ones added here go
  // when the run ends, so they never catch an unrelated debugging session.
  const wanted = (query.get("break") || "").split("|").filter(Boolean).map((entry) => {
    const match = entry.match(/^(.*):(\d+)$/);
    if (!match) throw new Error(`Bad breakpoint "${entry}".`);
    const breakPath = path.isAbsolute(match[1]) ? match[1] : path.join(repoRoot, match[1]);
    return { file: vscode.Uri.file(breakPath), line: Number(match[2]) };
  });
  const existing = new Set(vscode.debug.breakpoints
    .filter((b) => b instanceof vscode.SourceBreakpoint)
    .map((b) => `${b.location.uri.fsPath}:${b.location.range.start.line + 1}`));
  const added = wanted
    .filter(({ file, line }) => !existing.has(`${file.fsPath}:${line}`))
    .map(({ file, line }) => new vscode.SourceBreakpoint(new vscode.Location(file, new vscode.Position(line - 1, 0))));
  if (added.length > 0) vscode.debug.addBreakpoints(added);

  await vscode.window.showTextDocument(file, {
    selection: name ? new vscode.Range(line - 1, 0, line - 1, 0) : undefined,
    preserveFocus: true,
  });
  const run = `plan-review-links-${Date.now()}`;
  const ended = vscode.debug.onDidTerminateDebugSession((session) => {
    if (session.configuration.planReviewRun !== run) return;
    ended.dispose();
    vscode.debug.removeBreakpoints(added);
  });
  const started = await vscode.debug.startDebugging(folder, {
    planReviewRun: run,
    type: "node",
    request: "launch",
    name: name ? `vitest · ${name}` : `vitest · ${relativePath}`,
    program: path.join(repoRoot, "node_modules", "vitest", "vitest.mjs"),
    args,
    cwd: repoRoot,
    console: "integratedTerminal",
    autoAttachChildProcesses: true,
    smartStep: true,
    skipFiles: ["<node_internals>/**", "**/node_modules/**"],
  });
  if (!started) {
    ended.dispose();
    vscode.debug.removeBreakpoints(added);
  }
  return true;
}

// A separate route keeps the existing vitest links working unchanged.
async function handleDebugPytest(uri) {
  if (uri.path !== "/debug-pytest") return false;
  if (!vscode.workspace.isTrusted) throw new Error("Trust the workspace before running a reproduction.");

  const query = new URLSearchParams(uri.query);
  const filePath = await fs.realpath(await fileFromQuery(query));
  const file = vscode.Uri.file(filePath);
  const { stdout } = await git("git", ["-C", path.dirname(filePath), "rev-parse", "--show-toplevel"]);
  const repoRoot = stdout.trim();
  if (!isAllowedFile(file, repoRoot)) {
    throw new Error("Open e-footprint-interface, e-footprint, or their shared workspace in VS Code first.");
  }
  const relativePath = path.relative(repoRoot, filePath).split(path.sep).join("/");
  const test = query.get("test");
  if (!relativePath.startsWith("tests/") || !relativePath.endsWith(".py")
      || !test || !/^(?:Test\w*::)?test_\w+(?:\[[^\r\n]+\])?$/.test(test)) {
    throw new Error("The link must name a Python test under tests/ and its pytest test id.");
  }
  const debuggerExtension = vscode.extensions.getExtension("ms-python.debugpy");
  if (!debuggerExtension) throw new Error("Install the Python Debugger extension (ms-python.debugpy) first.");
  await debuggerExtension.activate();

  // Resolve Poetry in this repository even when the parent workspace or library is open.
  const configuredPoetry = vscode.workspace.getConfiguration("python", file).get("poetryPath", "poetry");
  const localPoetry = path.join(os.homedir(), ".local", "bin", "poetry");
  const poetry = configuredPoetry === "poetry" && await fs.stat(localPoetry).then((s) => s.isFile(), () => false)
    ? localPoetry : configuredPoetry;
  const environment = await git(poetry, ["env", "info", "--executable"], { cwd: repoRoot });
  const python = environment.stdout.trim();
  if (!path.isAbsolute(python)) throw new Error("No Poetry environment found; run poetry install in the repository first.");

  const args = ["--runxfail", "--no-cov", "-o", "addopts=", "-s", "-vv", "--tb=long", "-x", `${relativePath}::${test}`];
  if (relativePath.startsWith("tests/e2e/")) args.push("--base-url", "http://localhost:8000", "--headed");
  await vscode.window.showTextDocument(file, { selection: selectionAt(query), preserveFocus: true });
  const started = await vscode.debug.startDebugging(vscode.workspace.getWorkspaceFolder(file), {
    type: "debugpy",
    request: "launch",
    name: `Reproduction · ${test}`,
    python,
    module: "pytest",
    args,
    cwd: repoRoot,
    envFile: path.join(repoRoot, ".env"),
    env: { RAISE_EXCEPTIONS: "1", PYTEST_ADDOPTS: "" },
    console: "integratedTerminal",
    redirectOutput: true,
    justMyCode: false,
    stopOnEntry: false,
  });
  if (!started) throw new Error("VS Code could not start the Python debugger.");
  return true;
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
        if (await handleOpen(uri)) return;
        if (await handleDebugTest(uri)) return;
        if (await handleDebugPytest(uri)) return;
        await handleDiff(uri);
      } catch (error) {
        vscode.window.showErrorMessage(`Plan review links: ${error.message}`);
      }
    },
  }));
}

module.exports = { activate };
