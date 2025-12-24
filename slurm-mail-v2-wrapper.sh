#!/bin/bash

# Wrapper script for slurm-mail-v2.py that allows for usage on any of our machines (theoretically)

# Written by Tyler Jones ;) on 12/23/2025

# initial variables
output_code=1
datetime=$(date)

# make sure modules command exists and load path to it
if [ -f /etc/profile.d/modules.sh ]; then
    source /etc/profile.d/modules.sh
fi

# loop through Python versions to atempt to load
# ordered by version priority (made up by me)
for x in 11 12 9 8 7
do

  # load each module until a successful load
  if module load python/3.$x > /dev/null 2>&1; then
    output_code=0
    break

  fi

done

# store loaded Python environment
loaded_env=$(command -v python || true)

# raise error if output_code is never set to 0
if [ "$output_code" != 0 ]; then

  # send error log to slurmctld.log and exit program
  echo "${datetime}: Slurm MailProg, via /usr/bin/slurm-mail-v2-wrapper.sh, failed to load usable Python module" >> /var/log/slurm/slurmctld.log
  exit 1

# run mail script with variables passed by Slurm using loaded Python environment
else

  exec "$loaded_env" /usr/bin/slurm-mail-v2.py "$@"

fi
