# Instructor guide

[Workshop home](../README.md) · [Participant session](workshop.md)

Teach the 30-minute core as a complete session. Use the second half hour for participants to connect or deploy one component. The timed plan is a delivery estimate, not a claim that everyone will provision a stack within that time.

## Before the event

- Confirm the challenge rules, credit promotion and expiry, and whether the shared inference endpoint alone qualifies.
- Confirm the endpoint URL, team key distribution, model aliases, quotas, and supported features in [inference.md](inference.md). These values describe the supplied workshop deployment and require a live rehearsal.
- Send [setup](00_prework.md) in advance. Ask participants to complete one chat request before arriving.
- Rehearse from a fresh environment. Run notebook 00 completely, then the specific retrieval and tool cells you intend to show. Use Python 3.12 to match the container image.
- Prepare a Linode deployment with a bucket containing the fictional sample files. Keep a PostgreSQL-connected deployment available only if you plan to demonstrate persistence.
- Save a short screen recording or screenshots of a successful request, bucket contents, and deployed app. Label these as recorded examples if you use them.
- Check venue connectivity, display size, terminal font, and notebook kernel. Hide credentials and billing details before screen sharing.

Do not run all five notebooks live. Their combined scope belongs in the hackathon reference material.

## Teach the core session

| Time | Show and explain | Ask participants | Transition |
|---|---|---|---|
| 0–3 | One document question and the challenge goal | What will your application help someone do? | Identify the services behind the answer. |
| 3–8 | [Cloud essentials](cloud.md), request diagram, service table | Where would an uploaded file live? | Call the model before adding infrastructure. |
| 8–14 | Notebook 00 setup and Step 3 chat; change the prompt | Which field contains the answer? | Give the application information the model cannot infer. |
| 14–22 | Prepared bucket, `parking.md`, deployed query, `search_docs` log | Which file supports this answer? | Choose only the services the project needs. |
| 22–27 | [Project paths](build.md) | Name your model feature, cloud component, and proof. | Find the corresponding lab. |
| 27–30 | Reference index, help path, resource cleanup | Can your teammate find the next step? | Close or begin the build session. |

Suggested opening: “By the end of this session, you will make a model request, see how an application answers from a document, and choose an Akamai Cloud service for your project.”

## Demonstration notes

For the first model request, point out `OPENAI_BASE_URL`, the alias `hackathon-chat`, and `messages`. Explain that this endpoint is operated for the workshop and supports selected OpenAI-compatible operations. Compatibility does not imply that every OpenAI API or framework integration is available.

For document retrieval, show the file before asking the question. Then show the tool call and answer. Explain that Object Storage stores the original file while the application performs indexing and retrieval. A successful answer should reflect the file and name its source; exact wording may vary.

For runtime, show the same application on a Linode. Explain Docker Compose, the application port, and the firewall. Introduce LKE as an alternative for teams using Kubernetes. Avoid provisioning a cluster during the core session.

For persistence, if time permits, save a fictional fact, restart the application, and recall it. Explain that PostgreSQL keeps state across processes. The starter's saved notes are shared across sessions; they are not private user memory.

`/health` reports configuration and component states. In particular, `brain: live` is a configured client, not a successful inference probe. Always make an actual chat request before describing the model as reachable.

## Extend to 60 minutes

Follow the build session in [workshop.md](workshop.md#3060-minutes-build-session). Have teams choose a resource owner. Start the bucket and VM path by minute 35. At minute 48, move to validation even if some deployments are still provisioning. Mentors can finish those deployments after the session.

Use the remaining time to change a source document or application prompt. Keep PostgreSQL, LKE, images, and detailed tool calling available as choices for teams that finish early.

## Recover without losing the session

| Problem | Response |
|---|---|
| Account activation pending | Use notebooks and local sample files; pair with an activated team account for deployment |
| Package installation or Wi-Fi delays | Pair participants; use the prepared environment for the demonstration |
| Inference unavailable or quota exhausted | Show a clearly labeled recorded response, inspect the request, and continue with service selection |
| Database or VM still provisioning | Use the prepared deployment; leave the provisioning lab as a follow-up |
| Retrieval answer is unsupported | Inspect the source and tool result together; explain that retrieval and prompts still require evaluation |
| A team already has an app | Direct them to one cloud lab and the inference reference |

## Before handing off to the hackathon

Have every team identify its next lab, the account holding its resources, and who will delete those resources. Point to [demo evidence](build.md#prepare-your-demo) and [costs and cleanup](costs.md). Share the organizer-approved support channel and submission rules verbally or in the event materials.
