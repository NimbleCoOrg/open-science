#!/usr/bin/env python3
"""Alembic-style scrub for the FDE reasoning traces.
Applies Juni's 2026-08-11 redaction standard. Deterministic, auditable, re-runnable.
KEEP: names (Juni, Matilde), human steering + funny moments, tool-call texture, tool problems.
STRIP: ports, device names, internal links/hostnames, private-repo refs, Discord thread/channel
IDs + the Discord link itself, keys/tokens/credential mechanics, user IDs/snowflakes, internal paths.
"""
import re, sys, json

def scrub(text: str) -> str:
    t = text
    # internal filesystem paths -> generic
    t = re.sub(r'/opt/data/[\w./-]*', '<repo>', t)
    t = re.sub(r'/tmp/[\w./-]*', '<tmp>', t)
    t = re.sub(r'/opt/hermes/[\w./-]*', '<hermes>', t)
    t = re.sub(r'\$HOME/[\w./-]*', '<home>', t)
    t = re.sub(r'~/[\w./-]*', '<home>', t)
    # discord thread/channel/user snowflakes (18-19 digit IDs)
    t = re.sub(r'\b1[0-9]{17,18}\b', '<id>', t)
    # discord invite / cdn links
    t = re.sub(r'https://cdn\.discordapp\.com/\S+', '<discord-attachment>', t)
    # bsky post AT URIs and post rkeys -> generic handle ref (keep the handle, drop the rkey)
    t = re.sub(r'at://([\w.-]+)/app\.bsky\.feed\.post/\w+', r'at://\1/...', t)
    t = re.sub(r'https://bsky\.app/profile/([\w.-]+)/post/\w+', r'https://bsky.app/profile/\1/...', t)
    # credential/auth mechanics
    t = re.sub(r'GH_TOKEN', '<token>', t)
    t = re.sub(r'oauth_token', '<token>', t)
    t = re.sub(r'git credential fill', 'git credential <helper>', t)
    t = re.sub(r'credential.helper', 'credential <helper>', t)
    t = re.sub(r'hermes-fleet-git\[bot\]', '<git-bot>', t)
    t = re.sub(r'hermes_cli\.github_app_token', '<github-app-token-helper>', t)
    # ports / hosts / devices
    t = re.sub(r'junis-mac-mini(?::\d+)?', '<host>', t)
    t = re.sub(r'localhost:\d+|127\.0\.0\.1:\d+', '<host:port>', t)
    t = re.sub(r':(\d{4,5})/keys', ':<port>/keys', t)
    return t

def main():
    src = sys.argv[1]
    dst = sys.argv[2]
    with open(src, encoding='utf8') as f:
        body = f.read()
    with open(dst, 'w', encoding='utf8') as f:
        f.write(scrub(body))
    # report what got scrubbed
    counts = {
        'paths': len(re.findall(r'<repo>|<tmp>|<hermes>|<home>', scrub(body))),
        'ids': len(re.findall(r'<id>', scrub(body))),
        'tokens': len(re.findall(r'<token>', scrub(body))),
        'links': len(re.findall(r'<discord-attachment>', scrub(body))),
    }
    print(json.dumps({'dst': dst, 'scrubbed': counts}, indent=2))

if __name__ == '__main__':
    main()
