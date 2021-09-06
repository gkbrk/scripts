#!/bin/sh

# fireprof: Temporary Firefox profile runner
# Gokberk Yaltirakli, 2021

# This script creates temporary Firefox profiles. This is useful for maintaining
# privacy and browsing without permanent "supercookies".

# randstr - Generate a random string.
#
# This function reads from /dev/urandom and generates a random string of length
# N that consists of lowercase letters and numbers.
#
# Parameters
# ----------
# N : number
#     The length of the string
#
# Returns
# -------
# string
#     The random string
randstr () {
    LENGTH="$1";shift
    tr -dc 'a-z0-9' < /dev/urandom | head -c "${LENGTH}"
}

cleanup () {
    rm -rfv "${dir}"
}

dir="/tmp/firefoxprofile-$(randstr 20)/"
mkdir -p "${dir}"
trap cleanup EXIT

user_pref () {
    name="${1}";shift
    val="${1}";shift
    printf 'user_pref("%s", %s);\n' "${name}" "${val}" >> "${dir}/prefs.js"
}

# TODO: Add more overrides from ffprofile.com.

# UI stuff
user_pref browser.uidensity 1
user_pref general.smoothScroll false
user_pref browser.tabs.warnOnClose false
user_pref extensions.activeThemeID "'firefox-compact-dark@mozilla.org'"
user_pref datareporting.policy.dataSubmissionEnabled false

# Disable Google's bullshit protocols
user_pref network.http.http3.enabled false
user_pref network.http.spdy.enabled.http2 false

# Tracking protection
user_pref privacy.trackingprotection.enabled true
user_pref browser.contentblocking.category "'strict'"

# Disable Google safe browsing crap
user_pref browser.safebrowsing.malware.enabled false
user_pref browser.safebrowsing.phishing.enabled false
user_pref browser.safebrowsing.downloads.enabled false

# Disable search suggestions
user_pref browser.search.suggest.enabled false

# New tab page
user_pref browser.newtabpage.activity-stream.feeds.section.topstories false
user_pref browser.newtabpage.activity-stream.feeds.topsites false
user_pref browser.newtabpage.activity-stream.showSearch false

# Misc
user_pref browser.formfill.enable false
user_pref extensions.pocket.enabled false
user_pref security.ssl.disable_session_identifiers true

# DRM stuff
user_pref media.gmp-provider.enabled false
user_pref media.gmp-widevinecdm.enabled false

if [ "${1}" ]
then
    url="${1}"
else
    url="https://lite.duckduckgo.com/lite/"
fi
   
# Finally, execute Firefox with the temporary profile directory. After this
# process exits, the cleanup function will nuke the temporary profile.

MOZ_ENABLE_WAYLAND=1 firefox-nightly --profile "${dir}/" --no-remote --new-instance "${url}"
