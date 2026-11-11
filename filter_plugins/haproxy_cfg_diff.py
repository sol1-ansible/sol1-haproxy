"""Section-level diff of two haproxy.cfg texts.

Both texts are normalised the same way: comments and blank lines dropped, whitespace
collapsed, section headers reduced to "<type> <name>" (a bare "defaults" and
"defaults <name>" compare equal, and "from <x>" is stripped because dataplaneapi
adds it). Lines inside a section are compared as a multiset, since dataplaneapi
reorders keywords when it rewrites the file.
"""
import re

SECTION_RE = re.compile(r'^(global|defaults|frontend|backend|listen|userlist|resolvers|peers|cache|program|ring|http-errors|mailers)(?:\s+(\S+))?(?:\s+from\s+\S+)?\s*$')


def _sections(text):
    out, key = {}, None
    for raw in text.splitlines():
        line = re.sub(r'\s+', ' ', raw.split('#', 1)[0] if not raw.lstrip().startswith('#') else '').strip()
        if not line:
            continue
        m = SECTION_RE.match(line)
        if m:
            kind, name = m.group(1), m.group(2)
            key = kind if kind in ('global', 'defaults') else f'{kind} {name}'
            out.setdefault(key, [])
            continue
        if key is not None:
            out[key].append(line)
    return out


def _multiset_diff(desired, live):
    d, l = list(desired), list(live)
    for x in list(d):
        if x in l:
            d.remove(x)
            l.remove(x)
    return d, l  # (missing from live, extra in live)


def haproxy_cfg_diff(desired_text, live_text):
    want, have = _sections(desired_text), _sections(live_text)
    result = {'create': [], 'delete': [], 'modify': {}, 'unchanged': []}
    for key in sorted(set(want) | set(have)):
        if key not in have:
            result['create'].append(key)
        elif key not in want:
            result['delete'].append(key)
        else:
            add, remove = _multiset_diff(want[key], have[key])
            if add or remove:
                result['modify'][key] = {'add': add, 'remove': remove}
            else:
                result['unchanged'].append(key)
    result['in_sync'] = not (result['create'] or result['delete'] or result['modify'])
    return result


class FilterModule(object):
    def filters(self):
        return {'haproxy_cfg_diff': haproxy_cfg_diff}
