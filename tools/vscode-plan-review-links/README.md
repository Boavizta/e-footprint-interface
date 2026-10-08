# Plan Review Links

This local VS Code extension opens a source link's working copy beside its `main` revision. It supports both repositories in the `e-footprint-full` workspace, including when VS Code has only one of them open. A file absent from `main` is compared against empty content.

Open `e-footprint-full` (or the relevant repository) in VS Code, then install the extension's VSIX. The `simplified-inputs/plan.html` file keeps its normal open-file links; right-click a linked file and choose **Open diff vs main**.

To package after editing the extension, run `npx @vscode/vsce package` in this directory. Install the resulting `.vsix` with VS Code's **Extensions: Install from VSIX...** command, or with `code --install-extension plan-review-links-0.0.2.vsix`. Reload VS Code after replacing an installed version.

The comparison is against the local `main` commit and includes uncommitted working-tree edits. It does not fetch from the remote or change the checkout.
