#!/bin/sh

log () {
    DATE=$(date "+%H:%M:%S")
    printf "[%s] %s\n" "${DATE}" "${1}"
}

sqliteRun () {
    file="${1}";shift
    qry="${1}";shift
    sqlite3 "${file}" "${qry}"
}

find "${HOME}/.mozilla/firefox" -type f -wholename '*.sqlite' |\
    while IFS= read -r file
    do
        log "Processing ${file}..."
        sqliteRun "${file}" "REINDEX"
        sqliteRun "${file}" "VACUUM"
        sqliteRun "${file}" "ANALYZE"
        sqliteRun "${file}" "PRAGMA OPTIMIZE"
        sqliteRun "${file}" "REINDEX"
    done
