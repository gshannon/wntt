# .bash_profile

# Get the aliases and functions
if [ -f ~/.bashrc ]; then
	. ~/.bashrc
fi

# User specific environment and startup programs
set -o vi

# These are the default aliases for Ubuntu:
# alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\''s/^\s*[0-9]\+\s*//;s/[;&|]\s*alert$//'\'')"'
# alias egrep='egrep --color=auto'
# alias fgrep='fgrep --color=auto'
# alias grep='grep --color=auto'
# alias l='ls -CF'
# alias la='ls -A'
# alias ll='ls -alF'
# alias ls='ls --color=auto'


# alias la='ls -Fa'
# alias ll='ls -l'
alias lla='ls -Fla'
alias ltr='ls -Fltr'

PATH=$PATH:/home/tides/bin


alias d="docker"
alias di="docker images"
alias up="docker compose  -f ~/docker-compose.yml up -d"
alias down="docker compose  -f ~/docker-compose.yml down"
alias startapp="docker compose -f ~/docker-compose.yml start app"
alias stopapp="docker compose -f ~/docker-compose.yml stop app"
# tail logs
alias logapp="docker logs -f app-c"
alias logapi="docker logs -f api-c"

alias doagent="docker run -d -v /proc:/host/proc:ro -v /sys:/host/sys:ro digitalocean/do-agent:stable"

export LOG=/var/log/wntt
