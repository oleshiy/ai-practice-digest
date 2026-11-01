"""Two exact presentations of one supplied email; never a general URL fallback."""
import re

MARKER='openai-pro-email-2026-11-01'
NOTE='Источник — письмо OpenAI получателю Pro, предоставлено пользователем 1 ноября; дата отправки и публичная ссылка неизвестны.'
SOURCE='Письмо OpenAI'
ALLOWLIST={
    '2026-11-01-weekly':{
        'type':'weekly',
        'title':'OpenAI удвоила лимиты Work и Codex в Pro и готовит общий бюджет использования',
        'urls':[],
    },
    '2026-11-01-weekly-short':{
        'type':'working',
        'title':'OpenAI удвоила лимиты Work и Codex в Pro',
        'urls':[
            'https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions',
            'https://latent.space/p/ainews-google-admits-ai-mode-hurts-search-revenue-15-500b-drop-worst-since-2004-ipo-ai-bear-market-c/',
            'https://x.com/claudeai/status/2116220869479428500',
        ],
    },
}

def provided_source(edition):
    """Validate opt-in even when no unlinked topic needs it."""
    if 'provided_source' not in edition:return None
    allowed=ALLOWLIST.get(edition['slug'])
    assert (edition['provided_source']==MARKER and allowed
            and edition['type']==allowed['type'] and 'sections' in edition), 'provided source is not allowlisted'
    return allowed

def provided_topic(edition,title,lines):
    """Match the plain topic, exact note, and its edition-specific supplementary URLs."""
    allowed=provided_source(edition)
    return bool(allowed and title==allowed['title'] and lines.count(NOTE)==1
                and re.findall(r'\]\((https?://[^\s)]+)\)','\n'.join(lines))==allowed['urls'])
