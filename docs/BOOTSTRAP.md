# Bootstrap on a New Machine

1. Install Hermes.
2. Authenticate GitHub.
3. Clone this private repo.
4. Run `bash bootstrap/bootstrap_machine.sh`.
5. Fill `~/.hermes/.env` locally.
6. Run `hermes model` / `hermes setup` / provider OAuth logins as needed.
7. Run `bash bootstrap/verify.sh`.

This repo does not carry credentials. If a model/provider fails after bootstrap, fix local credentials rather than editing this repo.
