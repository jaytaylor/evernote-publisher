evernote-publisher
==================

Evernote collection system which organizes notes into a flexible format which allows for easy publishing.

## Requirements

* Python
* VirtualEnv
* Evernote API key

## How to run it

Get started with ./publisher.sh.

## Annual Token Expiration

Evernote developer API tokens expire annually.  To generate a fresh one, visit [https://www.evernote.com/api/DeveloperToken.action](https://www.evernote.com/api/DeveloperToken.action) and click "Revoke your developer token", followed by "Create a developer token".

Reminder to Jay: There is no need to recreate your app every year!

## Periodic Refresh Script

Just fill your notebook name into the script below:

```bash
#!/usr/bin/env bash

set -o errexit
set -o pipefail
set -o nounset

#set -x

cd "$(dirname $0)"
. venv/bin/activate
./app.py collect <UNIQUE-NOTEBOOK-NAMEFRAGMENT>
./app.py generate
```

