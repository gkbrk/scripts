#!/bin/sh

log () {
    DATE=$(date "+%H:%M:%S")
    printf "[%s] %s\n" "${DATE}" "${1}"
}

vacuumSqlite () {
    file="${1}";shift
    log "Vaccuming ${file}..."
    sqlite3 "${file}" "REINDEX"
    sqlite3 "${file}" "VACUUM"
    sqlite3 "${file}" "REINDEX"
}

log "Reading profiles..."

find "${HOME}/.mozilla/firefox" -maxdepth 1 -type d |\
    while IFS= read -r profile
    do
        log "Processing ${profile}..."

        find "${profile}" -type f -wholename '*.sqlite' |\
            while IFS= read -r db
            do
                vacuumSqlite "${db}"
            done
    done

#timevalue=`python3 -c "import time;print(round((time.time() - 24*60*60*30) * 1000000))"`

# Clean old cookies
#echo "Cleaning old cookies..."
#sqlite3 ~/.mozilla/firefox/$profile/cookies.sqlite "DELETE FROM moz_cookies WHERE lastAccessed < $timevalue;"

# Clean history
#echo "Cleaning history..."
#sqlite3 ~/.mozilla/firefox/$profile/places.sqlite "DELETE FROM moz_places WHERE last_visit_date < $timevalue;"
