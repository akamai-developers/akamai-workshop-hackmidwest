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

## Rehearsal on 2026-10-09

Run from a fresh clone of the pushed revision, in a new virtual environment, with a new `linode-cli` configuration, against one Akamai Cloud account. Every command in the setup page, the workshop page, the five labs, and the cleanup page was pasted as written.

- Setup: the install and the first model request worked. `linode-cli configure --token` asks four default questions, not three; the page now says so.
- Lab 01 by hand, lab 02, lab 04, and lab 05 produced the documented results. The database was active 5 min 43 s after creation and in DNS at 7 min 52 s. The LKE deploy script finished in 3 min 58 s with every status live.
- Lab 03: the deploy script stopped with `Request failed: 500` on the database allow-list update, right after cloud-init. The address had been added anyway. The rerun finished in 1 min 31 s. The troubleshooting page and the lab now say to run it again.
- The workshop's build path (`up.sh --no-db`, `upload.py`, `deploy_linode.sh`) finished in 3 min 51 s and answered a schedule question from the bucket.
- `down.sh` found and deleted all seven resources in 18 s, and the build path's four in 8 s. The account held nothing from the kit afterwards.
- All five notebooks were executed with nbconvert: 58 of 58 cells ran. Notebook 04's two-idea structured request overran its 400-token budget once in four runs and now has 1,000. Outputs were cleared before commit, which the notebook test requires.
- Live endpoint facts checked the same day: `GET /v1/models` works and lists the context window of the chat and embedding models; every other path returns `404`; a 2,100-character image prompt returns `422`; a 9,000-token embedding input is accepted, not rejected.

Found and fixed in this revision: the setup page, the inference reference, and a script test pointed `OPENAI_BASE_URL` at `api.openai.com`, which would have failed every new user at setup step 3 with `401`. `.env.example` was already correct.

Before teaching: the GitHub repository is private, so `git clone` in setup step 2 asks for a username. Make it public or give participants access.
