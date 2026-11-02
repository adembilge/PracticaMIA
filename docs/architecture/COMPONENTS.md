# System components

Task 21. Written on 2 November 2026. The features are in [PRODUCT.md](../product/PRODUCT.md). The ready rule is in [INTAKE.md](../product/INTAKE.md). The turns are in [CONVERSATION.md](../product/CONVERSATION.md).

This file names owners and the two request paths. It is not a schema, an API, or a rule the agent may state. Tables stay in Task 22. Case states stay in Task 23.

## Owners

One owner per job.

- Next.js shows the six screens. It does not decide ready, and it does not call the model.
- FastAPI is the only writer of the case. It decides ready from the intake: the title paper is present, and the name and the new address on the uploaded papers agree. It refuses a password.
- LangGraph runs one turn. It asks the one missing field. It does not store the case except by calling FastAPI.
- PostgreSQL stores the case, the messages, and the upload records. FastAPI is the only component that writes it.
- The knowledge engine stores the research rows and their unreviewed status. Asked for a deadline, an unasked paper, or the only sign-in method, it returns that this release does not state that. It does not promote an unresolved dossier row.
- Document processing reads one upload and returns the name and the address, or unreadable. It does not mark ready.
- The model writes the reply sentences and may propose the extracted name and address. FastAPI checks them. The model does not choose the door or a value when two papers disagree.

```mermaid
flowchart TD
  browser[Browser]
  web[Nextjs]
  api[FastAPI]
  graph[LangGraph]
  db[PostgreSQL]
  knowledge[KnowledgeEngine]
  docs[DocumentProcessing]
  model[Model]
  browser --> web
  web --> api
  api --> graph
  api --> db
  api --> docs
  graph --> model
  graph --> knowledge
  graph --> api
```

A chat turn and an upload are both one synchronous request. The turn waits for the model and, if a file was just uploaded, for the read of that file. There is no background job. Files stay with the API process. No second store.

## What each feature uses

- Choose the door. LangGraph asks F-02 or F-03 once. FastAPI records supported or excluded. An excluded story has no case row.
- Check the papers. Document processing reads the file. FastAPI compares the name and the new address. A mismatch or a missing title paper stays not ready.
- Keep the case. PostgreSQL holds the answers, the uploads, the missing field, and the package. Coming back reads that row. It does not read ANPR.
- Hand over. Next.js shows the CH-01 link only when FastAPI says ready. Nothing in this system files the declaration.
