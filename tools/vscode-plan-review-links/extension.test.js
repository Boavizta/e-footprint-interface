const assert = require("node:assert/strict");
const Module = require("node:module");
const path = require("node:path");
const { test } = require("node:test");

const workspaceRoot = path.resolve(__dirname, "../../..");
const interfaceRoot = path.join(workspaceRoot, "e-footprint-interface");
const calls = [];
const errors = [];
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
    registerUriHandler(value) { handler = value; return { dispose() {} }; },
    showErrorMessage(message) { errors.push(message); },
  },
  commands: {
    async executeCommand(...args) { calls.push(args); },
  },
};

const originalLoad = Module._load;
Module._load = function load(request, ...args) {
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
  const filePath = path.join(__dirname, "extension.js");
  await openDiff(filePath);
  assert.deepEqual(errors, []);
  assert.equal(await contentProvider.provideTextDocumentContent(calls[0][1]), "");
});

test("paths outside the open workspace are rejected", async () => {
  await openDiff(path.join(workspaceRoot, "e-footprint-interface-worktree/AGENTS.md"));
  assert.equal(calls.length, 0);
  assert.match(errors[0], /Open e-footprint-interface/);
});
