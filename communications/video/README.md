# Scripted demo videos

`recorder.py` holds reusable Playwright recording, on-screen caption, cursor, pacing, and Sankey hover helpers. Each video has a separate script, starting with `sankey.py`. The approach and caption style are adapted from Clémence's September 2026 demo video kit in `../2026-09-Demo_video_generation_guidance/` at the workspace root.

Run a local interface server as described in `INSTALL.md`, with Playwright Chromium and `ffmpeg` available. From the interface repository root:

```bash
EF_LIBRARY_DIR=../e-footprint-worktree poetry run python -m communications.video.sankey
```

`EF_LIBRARY_DIR` points to the paired library checkout containing the updated e-commerce example. In a normal sibling checkout, omit it; the default is `../e-footprint`. `EF_BASE_URL` defaults to `http://127.0.0.1:8000`, and `PW_CHROMIUM` can select a different Chromium executable.

The script imports the model and prepares the opening diagram on a setup page, then records the on-camera flow. It writes an H.264 MP4 to `output/sankey_impact_repartition.mp4`. All media under `output/`, including raw browser footage, is gitignored. Review the rendered video and sampled frames after any UI or caption change.
