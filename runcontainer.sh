#!/bin/sh

# runcontainer.sh - Small shell script for running code in Linux containers
# Copyright 2021  Gokberk Yaltirakli <opensource@gkbrk.com>

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    (1) Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
#
#    (2) Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
#    (3)The name of the author may not be used to endorse or promote products
#    derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
# IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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

# temppath - Generate a randomized path name
#
# This function generated a random path in /tmp/. No files or directories are
# created by this function, that part is left to the caller. This is done so
# that the caller may decide if they want to create a directory or a file.
#
# Returns
# -------
# string
#     The randomized path
temppath () {
    rand=$(randstr 20)
    name="/tmp/container.${rand}"
    printf "%s" "${name}"
}

# queue_cleanup - Remove a file or directory after the script exits
cleanup_list=$(temppath)

queue_cleanup () {
    printf "%s\n" "$1" >> "${cleanup_list}"
}

queue_cleanup "${cleanup_list}"

# mktempd - Create a temporary directory with a random name
#
# Parameters
# ----------
# None
#
# Returns
# -------
# The name of the directory
mktempd () {
    name=$(temppath)
    mkdir "${name}"
    printf "%s" "${name}"
}

# tar_extract - Extract a tar file
tar_extract () {
    TAR="$1";shift
    TARGET="$1";shift
    cd "${TARGET}" || exit
    tar xf "${TAR}"
}

# get_abspath - Turn a relative path into an absolute path
#
# Parameters
# ----------
# relpath : string
#     Relative path to convert
#
# Returns
# -------
# string
#     The absolute path
get_abspath () {
    RELPATH="$1";shift
    dir=$(dirname "${RELPATH}")
    dir=$(cd "${dir}"; pwd)
    RELPATH=$(basename "${RELPATH}")
    printf "%s/%s" "${dir}" "${RELPATH}"
}

run_on_host () {
    script="$1";shift
    workdir="$1";shift
    p=$(temppath)

    echo "#!/bin/sh" > "${p}"
    echo "${script}" > "${p}"
    chmod +x "${p}"
    (cd "${workdir}"; "${p}" "$@")
    rm -f "${p}"
}

run_on_container () {
    SCRIPT="$1";shift
    tdir="$1";shift
    machineid=$(randstr 25)
    scriptname=$(randstr 25)

    mkdir -p "${tdir}/container-misc/"
    echo "#!/bin/sh" > "${tdir}/container-misc/${scriptname}"
    echo "${script}" >> "${tdir}/container-misc/${scriptname}"
    chmod +x "${tdir}/container-misc/${scriptname}"
    
    systemd-nspawn -q --console=pipe -M "${machineid}" -D "${tdir}" "/container-misc/${scriptname}"

    rm -f "${tdir}/container-misc/${scriptname}"
}

cleanup () {
    while IFS= read -r line
    do
        rm -rf "${line}"
    done < "${cleanup_list}"
}
trap cleanup 0 1 2 3 6 15

# ----- MAIN -----

main () {
    # Keep the working directory around, we will run the host commands from this
    # path.
    workdir=$(pwd)
    
    IMAGE="$1";shift
    IMAGE=$(get_abspath "${IMAGE}")
    
    SCRIPT="$1";shift
    SCRIPT=$(get_abspath "${SCRIPT}")
    
    # Create a temporary directory for the container, queue a cleanup after the
    # script termination, and extract the TAR image there.
    temp_container=$(mktempd)
    queue_cleanup "${temp_container}"
    tar_extract "${IMAGE}" "${temp_container}"

    parse_and_execute_script "${workdir}" "${SCRIPT}" "${temp_container}"
}

parse_and_execute_script () {
    workdir="$1";shift
    path="$1";shift
    container="$1";shift

    # This is a very simple parser that splits the given file into sections.
    
    script=""
    SCRIPTSECTION="container"
    while IFS= read -r line
    do
        if printf "%s" "${line}" | grep -q "^## section "
        then
            if [ "${SCRIPTSECTION}" = "host" ]
            then
                run_on_host "${script}" "${workdir}" "${container}"
            elif [ "${SCRIPTSECTION}" = "container" ]
            then
                run_on_container "${script}" "${container}"
            else
                echo "[WARNING] Unknown section: ${SCRIPTSECTION}. Skipping..."
            fi
            
            SCRIPTSECTION=$(printf "%s" "${line}" | sed 's/## section //')
            script=""
        else
            script=$(printf "%s\n%s" "${script}" "${line}")
        fi
    done < "${path}"
}

main "$@"
