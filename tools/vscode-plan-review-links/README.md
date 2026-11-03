# Plan Review Links

This local VS Code extension opens a plan's source links, compares working files against `main`, and launches linked pytest or vitest tests in the debugger. It supports both repositories in `e-footprint-full`, including when VS Code has only one of them open. A file absent from `main` is compared against empty content.

Open `e-footprint-full` (or the relevant repository) in VS Code, then install the extension's VSIX. Feature `plan.html` files keep their normal open-file links; right-click a linked file and choose **Open diff vs main**.

To package after editing the extension, run `npx @vscode/vsce package` in this directory. Install the resulting `.vsix` with VS Code's **Extensions: Install from VSIX...** command, or with `code --install-extension plan-review-links-0.0.8.vsix`. Run **Developer: Reload Window** after replacing an installed version. Version 0.0.8 includes the existing 0.0.7 served-page and vitest routes.

The comparison is against the local `main` commit and includes uncommitted working-tree edits. It does not fetch from the remote or change the checkout.

## Debug Python reproductions

1. Install Microsoft's **Python Debugger** (`ms-python.debugpy`) extension and run `poetry install --with dev` in the repository.
2. Use a source link in the plan to open a file and set any breakpoints you want.
3. Click **Debug reproduction**. Without breakpoints, the test runs through and prints its failure in both **Terminal** and **Debug Console**. With breakpoints, inspect **Variables**, **Watch**, and the **Call Stack**, or evaluate expressions in **Debug Console**.

The browser or VS Code may ask once to allow opening these links. The launcher adds no breakpoints and does not change your exception-breakpoint settings. If you have enabled pausing on raised exceptions, VS Code may pause even without a source breakpoint; disable that option or Continue to see the final traceback.

Each link runs only its named pytest function (including its parameter cases), stopping at the first failure. It uses that repository's Poetry interpreter, loads its `.env`, sets `RAISE_EXCEPTIONS=1`, and runs with `--runxfail --no-cov -o addopts= -s -vv --tb=long -x`. `PYTEST_ADDOPTS` is cleared for this run so inherited coverage or parallel execution does not interfere with breakpoints. The Python `poetryPath` VS Code setting is respected; otherwise the launcher uses `~/.local/bin/poetry` if present, or `poetry` on PATH. `justMyCode: false` permits stepping into the editable companion library.

For `tests/e2e/`, start Django at `http://localhost:8000` first. The launcher opens a headed Playwright browser. Python breakpoints apply to the pytest process; debugging the separate Django server or browser JavaScript requires attaching the appropriate debugger to that process. Tests that deliberately catch an error still show their assertion failure; their plan's suggested breakpoint is the place to inspect the caught exception.

### Authoring links

Use a static URL with an absolute test-file `path`, a pytest `test` selector, and optionally the suggested source `line`:

```text
vscode://local.plan-review-links/debug-pytest?path=%2Fabsolute%2Frepo%2Ftests%2Ftest_example.py&test=TestExample%3A%3Atest_example&line=42
```

In HTML, escape `&` as `&amp;`. Add `data-review-pytest="../../../tests/test_example.py::TestExample::test_example"`, relative to the plan, so the shared `vscode_review_links.py` converter can refresh the absolute path in another checkout. Debug links do not use `data-review-source-href` and do not get the source-link diff menu.

Run checks with `node --test tools/vscode-plan-review-links/extension.test.js` from the interface repository.
