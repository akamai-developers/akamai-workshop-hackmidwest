#!/usr/bin/env bash
# Checks every link in the repository's Markdown files.
#   External URLs: fail on any status that is not 2xx or 3xx.
#   Relative links: fail if the file does not exist.
# www.akamai.com and www.linode.com answer 403 to scripts and headless browsers (bot protection).
# Those links are listed as SKIP so you can open them in a browser yourself.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

BOT_PROTECTED='^https?://(www\.)?(akamai|linode)\.com/'
# This repository answers 404 while it is private. Students need it public to clone it.
THIS_REPO='github\.com/akamai-developers/akamai-workshop-hackmidwest'
# Placeholders and API endpoints that are not pages: <ip>, localhost, example hosts, the inference API.
NOT_A_PAGE='[<>{}$]|localhost|127\.0\.0\.1|example\.(com|org)|ws\.akamai-workshops\.com|api\.linode\.com'
UA="Mozilla/5.0 (link check for akamai-workshop-hackmidwest)"

# Tracked and new Markdown files, skipping anything .gitignore hides. File names have no spaces.
files=$(git ls-files --cached --others --exclude-standard '*.md')
failed=$(mktemp)

status_of() {
  local code
  code=$(curl -sI -L --max-time 20 -A "$UA" -o /dev/null -w "%{http_code}" "$1")
  if [[ ! $code =~ ^[23] ]]; then  # some servers refuse HEAD, so try a normal GET before failing
    code=$(curl -s -L --max-time 20 -A "$UA" -o /dev/null -w "%{http_code}" "$1")
  fi
  echo "$code"
}

echo "External links"
grep -ohE 'https?://[^] )>"`'"'"'|]+' $files | sed -E 's/[.,;:]+$//' | sort -u | while read -r url; do
  [[ $url =~ $NOT_A_PAGE ]] && continue
  code=$(status_of "$url")
  if [[ $code =~ ^[23] ]]; then
    echo "  ok   $code $url"
  elif [[ $code == 403 && $url =~ $BOT_PROTECTED ]]; then
    echo "  SKIP $code $url (blocks scripts, open it in a browser)"
  elif [[ $code == 404 && $url =~ $THIS_REPO ]]; then
    echo "  SKIP $code $url (this repository is private; make it public before the event)"
  else
    echo "  FAIL $code $url"
    echo "$url" >> "$failed"
  fi
done

# The anchors GitHub makes from a file's headings: lowercase, punctuation dropped, spaces to hyphens.
anchors() {
  awk '/^```/{code = !code} !code && /^#+ /' "$1" | sed -E 's/^#+ //' | tr '[:upper:]' '[:lower:]' \
    | sed -E 's/[^a-z0-9 _-]//g; s/ /-/g'
}

echo "Relative links"
for file in $files; do
  dir=$(dirname "$file")
  grep -oE '\]\([^)]+\)' "$file" | sed -E 's/^\]\(//; s/\)$//' | while read -r link; do
    [[ -z $link || $link =~ ^(https?:|mailto:) ]] && continue
    target=${link%%#*}
    anchor=""
    [[ $link == *"#"* ]] && anchor=${link#*#}
    path="$dir/$target"
    [[ -z $target ]] && path=$file
    if [[ ! -e $path ]]; then
      echo "  FAIL $file -> $link (no such file)"
      echo "$file -> $link" >> "$failed"
    elif [[ -n $anchor && $path == *.md ]] && ! anchors "$path" | grep -qx -- "$anchor"; then
      echo "  FAIL $file -> $link (no heading for #$anchor)"
      echo "$file -> $link" >> "$failed"
    else
      echo "  ok   $file -> $link"
    fi
  done
done

failures=$(wc -l < "$failed" | tr -d ' ')
rm -f "$failed"
if [[ $failures != 0 ]]; then
  echo "$failures broken link(s)."
  exit 1
fi
echo "All links work."
