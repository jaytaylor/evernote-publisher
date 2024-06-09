#!/usr/bin/env bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 1>/dev/null 2>&1 && pwd)"

main_evernote_publisher() {
    cd "${DIR}"

    source venv3/bin/activate
    ## n.b. virtualenv activation will fail with -o nounset, so set it after.
    #set -o nounset

    # Clear out any empty data files (likely corrupted somehow).
    find 'data' -mindepth 1 -type f -empty -delete

    ./app.py collect outta
    ./app.py generate
}

if [ "${BASH_SOURCE[0]}" = "${0}" ] || [ "${BASH_SOURCE[0]}" = '--' ]; then
    # https://unix.stackexchange.com/a/343270/391515
    # shellcheck disable=SC2015
    [ "${FLOCKER:-}" != "$0" ] && exec env FLOCKER="$0" flock --verbose -en "$0" "$0" "$@" || :

    set -o errexit
    set -o pipefail
    set -o nounset

    if [ "${1:-}" = '-v' ]; then
        printf '%s\n' "INFO: $(basename "$0"):${LINENO} Verbose output enabled" 1>&2
        shift
        set -o xtrace
    fi

    main_evernote_publisher "$@"
fi
