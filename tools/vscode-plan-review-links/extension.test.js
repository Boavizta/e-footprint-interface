const assert = require("node:assert/strict");
const Module = require("node:module");
const fs = require("node:fs/promises");
const path = require("node:path");
const { test } = require("node:test");

const workspaceRoot = path.resolve(__dirname, "../../..");
const interfaceRoot = path.join(workspaceRoot, "e-footprint-interface");
const calls = [];
const errors = [];
const debugRuns = [];
const openedFiles = [];
const poetryCalls = [];
let startResult = true;
let debuggerAvailable = true;
let poetryError;
let handler;
let contentProvider;

function fileUri(filePath) {
  return {
    scheme: "file",
    fsPath: filePath,
    with(changes) { return { ...this, ...changes }; },
  };
}

const vscode = {
  Uri: { file: fileUri },
  Range: class Range {
    constructor(startLine, startColumn, endLine, endColumn) {
      Object.assign(this, { startLine, startColumn, endLine, endColumn });
    }
  },
  workspace: {
    isTrusted: true,
    getConfiguration() { return { get: (_key, fallback) => fallback }; },
    getWorkspaceFolder(uri) {
      return uri.fsPath.startsWith(`${interfaceRoot}${path.sep}`) ? { uri: fileUri(interfaceRoot) } : undefined;
    },
    workspaceFolders: [{ uri: fileUri(interfaceRoot) }],
    registerTextDocumentContentProvider(scheme, provider) {
      assert.equal(scheme, "plan-main");
      contentProvider = provider;
      return { dispose() {} };
    },
  },
  window: {
    async showTextDocument(...args) { openedFiles.push(args); },
    registerUriHandler(value) { handler = value; return { dispose() {} }; },
    showErrorMessage(message) { errors.push(message); },
  },
  commands: {
    async executeCommand(...args) { calls.push(args); },
  },
  extensions: {
    getExtension() { return debuggerAvailable ? { async activate() {} } : undefined; },
  },
  debug: {
    async startDebugging(folder, configuration) {
      debugRuns.push({ folder, configuration });
      return startResult;
    },
  },
};

const originalLoad = Module._load;
const childProcess = require("node:child_process");
const { promisify } = require("node:util");
function execFile(command, args, options, callback) {
  if (typeof options === "function") { callback = options; options = undefined; }
  if (path.basename(command) !== "poetry") return childProcess.execFile(command, args, options, callback);
  poetryCalls.push({ args, options });
  callback(poetryError, "/virtualenv/bin/python\n", "");
}
execFile[promisify.custom] = (...args) => new Promise((resolve, reject) => {
  execFile(...args, (error, stdout, stderr) => error ? reject(error) : resolve({ stdout, stderr }));
});
Module._load = function load(request, ...args) {
  if (request === "node:child_process") return {
    ...childProcess,
    execFile,
  };
  return request === "vscode" ? vscode : originalLoad.call(this, request, ...args);
};
const extension = require("./extension.js");
Module._load = originalLoad;
extension.activate({ subscriptions: [] });

async function openDiff(filePath, line) {
  calls.length = 0;
  errors.length = 0;
  const query = new URLSearchParams({ path: filePath });
  if (line) query.set("line", String(line));
  await handler.handleUri({ path: "/diff", query: query.toString() });
}

test("tracked interface file opens its main revision against the working copy", async () => {
  const filePath = path.join(workspaceRoot, "e-footprint-interface/model_builder/domain/object_factory.py");
  await openDiff(filePath, 17);
  assert.deepEqual(errors, []);
  assert.equal(calls.length, 1);
  const [command, left, right, , options] = calls[0];
  assert.equal(command, "vscode.diff");
  assert.equal(left.scheme, "plan-main");
  assert.deepEqual(JSON.parse(left.query), {
    repoRoot: interfaceRoot,
    relativePath: "model_builder/domain/object_factory.py",
    existsOnMain: true,
  });
  assert.match(await contentProvider.provideTextDocumentContent(left), /Domain object factory/);
  assert.equal(right.fsPath, filePath);
  assert.equal(options.selection.startLine, 16);
});

test("tracked library file works while only the interface repository is open", async () => {
  const filePath = path.join(workspaceRoot, "e-footprint/efootprint/abstract_modeling_classes/modeling_object.py");
  await openDiff(filePath);
  assert.deepEqual(errors, []);
  assert.equal(calls[0][1].scheme, "plan-main");
  assert.equal(JSON.parse(calls[0][1].query).repoRoot, path.join(workspaceRoot, "e-footprint"));
  assert.match(await contentProvider.provideTextDocumentContent(calls[0][1]), /ModelingObject/);
  assert.equal(calls[0][2].fsPath, filePath);
});

test("new file is compared with empty content", async () => {
  const directory = await fs.mkdtemp(path.join(__dirname, ".review-links-test-"));
  try {
    const filePath = path.join(directory, "new.js");
    await fs.writeFile(filePath, "// new file\n");
    await openDiff(filePath);
    assert.deepEqual(errors, []);
    assert.equal(await contentProvider.provideTextDocumentContent(calls[0][1]), "");
  } finally { await fs.rm(directory, { recursive: true }); }
});

test("paths outside the open workspace are rejected", async () => {
  await openDiff(path.join(workspaceRoot, "e-footprint-interface-worktree/AGENTS.md"));
  assert.equal(calls.length, 0);
  assert.match(errors[0], /Open e-footprint-interface/);
});

async function debugPytest(overrides = {}) {
  debugRuns.length = 0;
  openedFiles.length = 0;
  poetryCalls.length = 0;
  errors.length = 0;
  const query = new URLSearchParams({
    path: path.join(interfaceRoot, "tests/unit_tests/adapters/views/test_views_deletion.py"),
    test: "test_recurrent_need_deletion_rerenders_its_edge_usage_journey_card",
    line: "85",
    ...overrides,
  });
  await handler.handleUri({ path: "/debug-pytest", query: query.toString() });
}

test("pytest link launches the exact reproduction in its Poetry environment with tracebacks visible", async () => {
  await debugPytest();
  assert.deepEqual(errors, []);
  assert.equal(debugRuns.length, 1);
  const { configuration: config } = debugRuns[0];
  assert.equal(config.type, "debugpy");
  assert.equal(config.module, "pytest");
  assert.equal(config.python, "/virtualenv/bin/python");
  assert.equal(config.cwd, interfaceRoot);
  assert.deepEqual(poetryCalls[0].args, ["env", "info", "--executable"]);
  assert.equal(poetryCalls[0].options.cwd, interfaceRoot);
  assert.ok(config.args.includes("--runxfail"));
  assert.ok(config.args.includes("--no-cov"));
  assert.ok(config.args.includes("tests/unit_tests/adapters/views/test_views_deletion.py::test_recurrent_need_deletion_rerenders_its_edge_usage_journey_card"));
  assert.deepEqual(config.env, { RAISE_EXCEPTIONS: "1", PYTEST_ADDOPTS: "" });
  assert.equal(config.console, "integratedTerminal");
  assert.equal(config.redirectOutput, true);
  assert.equal(config.justMyCode, false);
  assert.equal(config.stopOnEntry, false);
  assert.equal(openedFiles[0][1].selection.startLine, 84);
});

test("browser reproduction launches headed with the documented server URL", async () => {
  await debugPytest({
    path: path.join(interfaceRoot, "tests/e2e/objects/test_jobs.py"),
    test: "TestJobs::test_deleting_nested_and_top_level_cards_logs_no_console_error",
  });
  assert.deepEqual(errors, []);
  assert.deepEqual(debugRuns[0].configuration.args.slice(-3), ["--base-url", "http://localhost:8000", "--headed"]);
});

test("links cannot launch a non-test file or a test outside the allowed workspace", async () => {
  for (const file of ["model_builder/views.py", "../e-footprint-interface-worktree/tests/e2e/objects/test_jobs.py"]) {
    await debugPytest({ path: path.resolve(interfaceRoot, file) });
    assert.equal(debugRuns.length, 0);
    assert.equal(errors.length, 1);
  }
  await debugPytest({ test: "--some-option" });
  assert.equal(debugRuns.length, 0);
  assert.match(errors[0], /pytest test id/);
});

test("untrusted workspaces do not execute Poetry or start tests", async () => {
  vscode.workspace.isTrusted = false;
  try {
    await debugPytest();
    assert.equal(poetryCalls.length, 0);
    assert.equal(debugRuns.length, 0);
    assert.match(errors[0], /Trust the workspace/);
  } finally { vscode.workspace.isTrusted = true; }
});

test("missing debugger, Poetry failures and refused debug launches give actionable errors", async () => {
  debuggerAvailable = false;
  try {
    await debugPytest();
    assert.match(errors[0], /Install the Python Debugger/);
    assert.equal(debugRuns.length, 0);
  } finally { debuggerAvailable = true; }
  poetryError = new Error("Poetry environment unavailable");
  try {
    await debugPytest();
    assert.match(errors[0], /Poetry environment unavailable/);
    assert.equal(debugRuns.length, 0);
  } finally { poetryError = undefined; }
  startResult = false;
  try {
    await debugPytest();
    assert.match(errors[0], /could not start the Python debugger/);
  } finally { startResult = true; }
});
