# Revision verification

This note records checks for the workshop restructure dated October 2, 2026.

## Completed

- 114 automated tests passed. These include the existing application and fake-cloud deployment tests, internal Markdown and notebook links, notebook code syntax, clean notebook outputs, and the documented tool recipe.
- All five notebooks passed `nbformat` schema validation.
- All shell scripts passed `bash -n`.
- Current participant guides and notebook prose were checked for em dashes and the filler phrases targeted by the rewrite.
- Core product descriptions were checked against the official references linked in the guides.

The Git checkout line-ending test was skipped because the editing workspace was a downloaded file snapshot without a `.git` directory. Tests ran with Python 3.12 and temporary test dependencies; the repository's dependency ranges were not changed.

## Before teaching

Live inference calls, notebook execution against the shared endpoint, and cloud provisioning were not performed for this revision. They require the event key and an authorized cloud account. No cloud resources were provisioned.

Use the [instructor checklist](instructor.md#before-the-event) to rehearse the notebook requests and deployment path. Confirm the live models, aliases, quotas, promotion, service availability, and challenge rules with the organizers. The agendas are teaching estimates rather than measured completion times.
