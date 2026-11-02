# Document processing

Task 25. Written on 2 November 2026. The owners are in [COMPONENTS.md](COMPONENTS.md). The fields are in [INTAKE.md](../product/INTAKE.md). The ready rule is in [RULES.md](RULES.md).

This file is the path for one upload. It is not a parser, an API, or a rule the agent may state. The model does not mark ready.

## Roles

The role comes from the intake. The model does not classify the file into a research row.

- Title paper. The lease when the person is the named tenant. The ownership paper when the person is the owner.
- Identity or permit paper, when the intake requires it. S-02 does not require it.

## Path

Accepted files are PDF, JPEG, and PNG. Any other file is a failed upload, E-01, and stores no extraction. An empty file is the same failure.

The file is written on the API process, on the upload row. There is no second store and no background job. Replacing that role deletes the old file and the old mismatch. Deleting the person deletes the file. Session expiry keeps it. The audit row records the replacement and stores no bytes.

A PDF text layer is read without the model. The extracted fields are the name, and the address when the paper shows one. A PDF with no text layer, or a JPEG or PNG, may be proposed by the model as those two strings. FastAPI keeps the proposal only as those two strings. No name means unreadable, E-02, and the extraction stays empty.

When two papers disagree, the person names which value is correct. That is the confirmation. The engine does not choose. The package is the agreed name and address, and the CH-01 link only when [RULES.md](RULES.md) says ready. The path does not fill an official form and does not file.
