#!/bin/bash
#SBATCH -o /dev/null
#SBATCH -t "{{ timelimit }}"
#SBATCH --ntasks {{ ntasks|default(1) }}
#SBATCH --cpus-per-task {{ cpus|default(1) }}
{% if no_multithreading %}
#SBATCH --hint=nomultithread
{% endif %}
{% if exclusive %}
#SBATCH --exclusive
{% endif %}
{% if max_running > 0 %}
#SBATCH --array=0-{{ projects|length() - 1 }}%{{ max_running }}
{% else %}
#SBATCH --array=0-{{ projects|length() - 1 }}
{% endif %}
{# FIXME: Still requires support for max running #}
#SBATCH --nice={{ nice }}

# List of available projects
projects=(
{% for p in projects %}
'{{ p }}'
{% endfor %}
)
# End of list of available projects
_project="${projects[$SLURM_ARRAY_TASK_ID]}"

exec 1> {{ log }}-$_project
exec 2>&1

# Prepare cluster node
exec 9> {{ lockfile }}
flock -x 9 && {
  if [ ! -d '{{ prefix }}' ]; then
    echo "$(date) [$(hostname)] prepare local node"
    mkdir -p '{{ prefix }}'
  fi
  rm '{{ lockfile }}'
}
exec 9>&-
# End of prepare cluster node

# Configuration
{% for line in config %}
{{ line }}
{% endfor %}
# End of configuration

scontrol update JobId=${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID} JobName="{{ name }} $_project"
srun -c 1 hostname

# Cleanup cluster node
file=$(mktemp -q) && {
  cat << EOF > $file
#!/bin/sh
#SBATCH --nice={{ nice_clean }}
#SBATCH -o /dev/null
exec 1>> {{ log }}-$_project
exec 2>&1
echo "$(date) [$(hostname)] node cleanup begin"
rm -r "{{ prefix }}"
rm "{{ clean_lockfile }}"
echo "$(date) [$(hostname)] node cleanup end"
EOF
  _inner_file=$(mktemp -q) && {
    cat << EOF > $_inner_file
#!/bin/bash
if [ ! -f '{{ clean_lockfile }}' ]; then
  touch '{{ clean_lockfile }}'
  echo "$(date) [$(hostname)] clean for $(hostname)"
  sbatch --time="15:00" --job-name="$(hostname)-cleanup" \
    -A {{ slurm_account }} -p {{ slurm_partition }} \
    --dependency=afterany:$SLURM_ARRAY_JOB_ID \
    --nodelist=$SLURM_JOB_NODELIST -n 1 -c 1 "$file"
fi
EOF
  }
  flock -x "{{ clean_lockdir }}" bash $_inner_file
  rm -f "$file"
  rm -f "$_inner_file"
}
# End of cleanup cluster node

# SLURM Command
{{ node_command }}