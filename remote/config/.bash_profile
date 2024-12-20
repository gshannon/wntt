# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

# User specific environment and startup programs
set -o vi

alias l='ls -F'
alias la='ls -Fa'
alias ll='ls -l'
alias lla='ls -Fla'
alias ltr='ls -Fltr'

PATH=$PATH:/home/devel/bin


alias d="docker"
alias di="docker images"
alias up="docker compose up -d"
alias down="docker compose down"
# tail logs
alias logui="docker logs -f app-c"
alias logapi="docker logs -f api-c"

alias doagent="docker run -d -v /proc:/host/proc:ro -v /sys:/host/sys:ro digitalocean/do-agent:stable"

export LOG=/var/log/wntt
