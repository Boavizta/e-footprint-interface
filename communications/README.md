# Communications — interface side

Working drafts for interface communications and the single home for all e-footprint LinkedIn posts and videos.

## Where to find foundations

Strategy, messaging one-pager, pitch deck outline, and the **single editorial calendar** live in the library repo:

- `e-footprint/communications/strategy.md`
- `e-footprint/communications/messaging-one-pager.md`
- `e-footprint/communications/editorial-calendar.csv`

Add articles and release notes here when their subject is the interface. Author every LinkedIn post in `linkedin/posts/` and scripted videos in `video/`, regardless of whether the feature spans the library and interface. Register planned pieces in the calendar in the library repository.

Prefix each post's Markdown filenames with its planned post date as `YY-MM-DD <slug>.md`. Prefix its recording script and generated media filenames with the same date as `YY_MM_DD_<slug>`. Shared files such as `README.md`, `backlog.md`, and `recorder.py` keep stable names.

## What lives here

| Folder | Contents |
|---|---|
| `articles/` | Articles whose dominant subject is an interface feature (e.g. onboarding examples, edge toggle UX, guided tour) |
| `linkedin/posts/` | All e-footprint LinkedIn post drafts |
| `linkedin/backlog.md` | Ideas for future LinkedIn posts |
| `linkedin/archive/` | Superseded LinkedIn plans, retained for context |
| `video/` | Reusable recording code, one script per video, and ignored outputs |
| `release-notes/` | Release notes tied to interface versions |

PS-branded client case studies do **not** live here — they are PS-owned and stay in PS systems.

Tool and method articles stay in the library repository. LinkedIn content has one authoring home here.
