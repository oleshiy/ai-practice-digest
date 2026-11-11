"""Shared outline for explicitly tagged compact daily readers."""
import re

LINK=re.compile(r'\[([^\]]+)\]\((https?://[^\s)]+)\)')
SECTION=re.compile(r'^(?:🔥|➡️) \*\*(.+?)\*\*$')
PRACTICE={'Что из этого применить в платформе','Что можно внедрить за две недели'}

def compact_outline(text):
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
    return {'topics':topics,'sections':sections,'paragraphs':paragraphs}
