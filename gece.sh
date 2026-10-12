#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
mkdir -p logs

TOOLS="Read,Edit,Write,Grep,Glob,Agent,WebSearch,WebFetch,Bash(mktemp:*),Bash(cp:*),Bash(diff:*),Bash(find:*),Bash(rm:*),Bash(git:*),Bash(ls:*)"

# stream-json çıktısını okunur satırlara çevirir
PRETTY='
if .type=="assistant" then
  (.message.content[]? |
    if .type=="text" then "\u001b[36m>> \(.text)\u001b[0m"
    elif .type=="tool_use" then "\u001b[33m[\(.name)]\u001b[0m \((.input.description // .input.file_path // .input.command // .input.pattern // .input.query // "") | tostring | .[0:150])"
    else empty end)
elif .type=="result" then
  "\u001b[32m== SONUÇ ==\u001b[0m\n\(.result // "")"
else empty end'

run () {  # $1 = adım adı, $2 = komut
  echo
  echo -e "\e[1;35m################ $(date +%H:%M) $1 başlıyor ################\e[0m"
  claude -p "$2" \
    --permission-mode acceptEdits \
    --allowedTools "$TOOLS" \
    --output-format stream-json --verbose \
  | tee "logs/$1.jsonl" \
  | jq -r --unbuffered "$PRETTY"
  local code=${PIPESTATUS[0]}
  echo -e "\e[1;35m################ $(date +%H:%M) $1 bitti (çıkış kodu $code) ################\e[0m"
  echo "$(date +%H:%M) $1 çıkış=$code" >> logs/ozet.log
}

run 01-probe "/dev-workflow:decision A slot is reported up only if at least one health probe ran in that slot and every probe that ran returned HTTP 200 within 2 s; a slot in which no probe ran is reported down. This closes the zero-probe gap in D-04 (PRD §10, §23): remove that gap note and that open question. If docs/SPEC.md exists, update rule H-3 to match. --lang Turkish"

run 02-track "/dev-workflow:decision The main Metropolis track is Trust, Identity & AI Infrastructure. Remove the main-track item from PRD §23; keep the observation that the provider posts no bond as a Post-Hackathon item in §25. --lang Turkish"

run 03-cre "/dev-workflow:decision Chainlink CRE is not used in the hackathon, neither as the reporter nor as a simulation demo. The demo and all simulation run with the Docker health-probe node (D-04) on the team's WSL machine. Remove the CRE and CRE deletion-test items from PRD §23 and keep CRE only as a Post-Hackathon option in §25. --lang Turkish"

run 04-tasks "/dev-workflow:plan-tasks PRD §8 Must Have (the full hackathon MVP) --lang Turkish"

echo
echo -e "\e[1;32m======== $(date +%H:%M) HEPSİ BİTTİ — özet: logs/ozet.log ========\e[0m"
