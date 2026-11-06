# CP3 Connections List

This record distinguishes team-reported integrations from connections evidenced by repository files and CP3 records. “Unknown” means the available information does not establish the fact; it does not prove that access did not exist.

- **Claude Code** — The team reports access to the repository and assignment instructions; possible access to class slides is uncertain. Ricky Vu reportedly configured Claude. Exact model, MCP/plugin/API connections, and the division of application work are not recorded.
- **Codex** — The team reports it was used with Claude Code on the application. The specific accessible context, configured connections, model, configuring team member, and per-feature contributions are not recorded.
- **GitHub Copilot in VS Code** — The team reports use by all members, especially Michael Hartnett and Hillary Haine. The available CP3 records describe local repository acceptance-review and documentation work; Git history does not attribute the broader application and test changes to a particular assistant or model. The exact model and who configured the extension are not verified.
- **Local development and verification** — The project is a local Flask/SQLite prototype. Its recorded CP3 test run uses Python and pytest with isolated temporary SQLite databases; the conformance record also describes an integrated-browser check. These records do not identify which person or AI tool ran each check. This documentation update used local workspace read/edit tools and PowerShell/Git.
- **External services, MCP servers, plugins, and API keys** — No specific external service integration, MCP connection, or API key is identified in the project files or CP3 evidence. The README says vendor messages are stored locally and the app does not send email or contact outside services. This does not certify that no teammate used an external connection during earlier work.

Application sign-in secrets are configured locally through `.env`; they are not external API keys and must not be committed. See [README.md](./README.md) for the local setup and [CP3-final-conformance.md](./evidence/CP3-final-conformance.md) for the verification record.
