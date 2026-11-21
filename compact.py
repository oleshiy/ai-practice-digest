"""Shared outline for explicitly tagged compact daily readers."""
import re
from urllib.parse import urlsplit

LINK=re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
SECTION=re.compile(r'^(?:🔥|➡️) \*\*(.+?)\*\*$')
PRACTICE={'Что из этого применить в платформе','Что можно внедрить за две недели'}

def parse_finding_ids(value):
    if not re.fullmatch(r'[1-9][0-9]*(?:[+,][1-9][0-9]*)*', value):
        raise ValueError('invalid compact finding IDs')
    return tuple(tuple(map(int, group.split('+'))) for group in value.split(','))


def supporting_links(meta, topics):
    """Validate additional source links against their canonical reader paragraph."""
    by_anchor = {topic['anchor']: topic for topic in topics}
    sources = {}
    for key, value in meta.items():
        if not key.startswith('supporting_'):
            continue
        anchor = 'finding-' + key.removeprefix('supporting_')
        if anchor not in by_anchor:
            raise ValueError(f'invalid supporting source target: {key}')
        matches = list(LINK.finditer(value))
        if not matches or ' '.join(m[0] for m in matches) != value:
            raise ValueError(f'{key} must contain space-separated Markdown links')
        seen = set(by_anchor[anchor]['urls'])
        for match in matches:
            url = urlsplit(match[2])
            if (not url.hostname or url.username is not None or any(c in match[2] for c in '<>')
                    or not match[1].strip() or match[2] in seen):
                raise ValueError(f'{key} contains a duplicate or invalid source')
            seen.add(match[2])
        sources[anchor] = [m[0] for m in matches]
    return sources


def render_sources(links, inline):
    if not links:
        return ''
    items = ''.join('<li>' + inline(link) + '</li>' for link in links)
    return '<details><summary>Источники</summary><ul>' + items + '</ul></details>'


def compact_outline(text, finding_ids=None):
    """Keep paragraph text intact; derive titles from its first complete sentence."""
    lines=text.splitlines();i=0;section='';sections=[];paragraphs={};topics=[];plain_sections=0
    while i<len(lines):
        line=lines[i]
        label=SECTION.fullmatch(line)
        if line.startswith('## ') or label:
            section=(line[3:] if line.startswith('## ') else label[1]).strip().rstrip(':')
            sections.append(section)
            if label:
                plain_sections+=1
                paragraphs[i]={'anchor':'compact-section-'+str(plain_sections),'section':section}
            i+=1;continue
        if not line.strip() or re.match(r'^(#{1,4} |\d+\. |- |!\[)',line):i+=1;continue
        start=i;paragraph=[]
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#{1,4} |\d+\. |- |!\[)',lines[i]):
            paragraph.append(lines[i].strip());i+=1
        value=' '.join(paragraph)
        if not value.startswith('🔹 ') or section in PRACTICE:continue
        link=LINK.search(value)
        if not link:raise ValueError('compact topic requires a public source link')
        visible=re.sub(r'[`*]','',LINK.sub(lambda match:match[1],value[2:])).strip()
        title=re.split(r'[.!?]+(?:\s|$)',visible,maxsplit=1)[0].strip()
        topic={'anchor':'finding-'+str(len(topics)+1),'title':title,'url':link[2],
               'section':section,'body':value,'urls':list(dict.fromkeys(m[2] for m in LINK.finditer(value)))}
        paragraphs[start]=topic;topics.append(topic)
    if finding_ids is not None:
        groups = [(value,) if isinstance(value, int) else value for value in finding_ids]
        ids = [number for group in groups for number in group]
        if (len(groups) != len(topics) or not all(groups)
                or sorted(ids) != list(range(1, len(ids) + 1))):
            raise ValueError('finding_ids must assign every previous ID to exactly one compact topic')
        for topic, group in zip(topics, groups):
            topic['anchor'] = f'finding-{group[0]}'
            topic['aliases'] = [f'finding-{number}' for number in group[1:]]
    return {'topics':topics,'sections':sections,'paragraphs':paragraphs}
