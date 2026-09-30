# Content license for published modelings

Status: CC BY 4.0 approved following Boavizta consultation; implementation pending · 2026-09-30

The maintainer confirmed acceptance after the Mattermost consultation posted on 3 September 2026,
with feedback requested through 14 September and no objections for more than two weeks. The
confirmation covers hosting, accounts/public storage, Brevo, licensing, deletion and moderation.
This records that consultation outcome, without describing it as a formal board vote.

## Approved reuse regime

Published modelings use **Creative Commons Attribution 4.0 International (CC BY 4.0)**.
Readers may copy, fork, adapt and republish the licensed content, including commercially, under
its attribution and notice conditions. The standard [deed](https://creativecommons.org/licenses/by/4.0/)
and [legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en) are authoritative.
Boavizta hosts publications without claiming their ownership. The platform also needs publication
terms and a privacy notice; choosing a license does not establish compliance with other obligations.

CC BY preserves credit for transparent modeling while allowing downstream reuse. It was selected
over a ShareAlike requirement; CC0 would remove the attribution condition this feature needs.

## Publication and attribution

At publication, users acknowledge the license and terms and confirm they have the necessary rights
to publish the content. The author/organization is supplied per publication, independently of the
private account email. Show the license on the publish form, public publication and terms page.

A fork captures the source title, public author, exact version, URL and license, and identifies its
forked origin. Preserve applicable notices and indications of modifications. The citation travels
through JSON export/import and is displayed when the fork is published. If the source is removed,
keep that citation unchanged without an additional availability label; following the source URL
shows the neutral unavailable page.

Title, public author, tags and article link can be corrected in place on the current version.
Superseded versions retain their last metadata. Captured fork citations remain snapshots rather
than automatically following later source-metadata edits.

## Exceptional attribution requests

[Section 3(a)(3)](https://creativecommons.org/licenses/by/4.0/legalcode.en#s3a3) requires removal of
the specified attribution information at the licensor's request to the extent reasonably practicable.
Handle such requests manually through the existing contact email or Feedback route, including
historical version metadata and retained fork citations where applicable. This is an exception to
ordinary metadata preservation, not a dedicated product workflow. Add no special request button,
page or attribution-removal wording to the app. Do not promise control over copies held elsewhere.

## Deletion, unpublishing and backups

Owner deletion removes the live publication and all its versions immediately. Account deletion
removes that account and its publications. Their URLs remain reserved and show “This modeling is
no longer available”; they cannot be reassigned. Other people's independently published forks
remain available. Existing PostgreSQL backup copies expire through the seven-day rotation.

Moderator unpublishing hides the entire publication, including every version and its discovery
entry. Its URLs show the same unavailable page. Content is retained privately so a moderator can
restore it at the same addresses, unless its owner permanently deletes it. This is the narrow
exception to public-by-construction long-lived modeling storage.

The terms should explain both deletion and continued reuse, for example:

> You can delete your publications at any time. Their contents will no longer be available on
> the site; existing backup copies expire within seven days. Their addresses remain reserved.
> Copies and forks already obtained by others remain licensed under CC BY 4.0.

The license grant for existing copies is irrevocable subject to its terms. Deletion is not a
recall of other people's copies. The approved behavior must be reflected in the final terms and
privacy notice without claiming that backup copies disappear instantly.

## Remaining verification and drafting

- Check compatibility with embedded reference datasets and other third-party content, preserving
  their notices or restrictions. Publishers can grant only rights they hold; CC BY does not
  relicense unrelated third-party rights.
- Complete the publication terms and privacy notice, including Brevo processing, logs, moderator
  retention, seven-day backup rotation and deletion handling during restore.
- Use the shared contact setting for report links, quota guidance and equivalent existing contact
  surfaces. Its agreed value is `vincent.villet@publicissapient.com`.

These are implementation/planning checks. License selection and feature approval are resolved.
