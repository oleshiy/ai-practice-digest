"""One explicit user-provided source exception; never a general URL fallback."""
SLUG='2026-11-01-weekly'
MARKER='openai-pro-email-2026-11-01'
TITLE='OpenAI удвоила лимиты Work и Codex в Pro и готовит общий бюджет использования'
NOTE='Источник — письмо OpenAI получателю Pro, предоставлено пользователем 1 ноября; дата отправки и публичная ссылка неизвестны.'
SOURCE='Письмо OpenAI'

def provided_source(edition):
    """Validate opt-in even when no unlinked topic needs it."""
    if 'provided_source' not in edition:return False
    assert (edition['provided_source']==MARKER and edition['slug']==SLUG
            and edition['type']=='weekly' and 'sections' in edition), 'provided source is not allowlisted'
    return True

def provided_topic(edition,title,lines):
    """The exact plain heading and one exact standalone note identify the email."""
    return provided_source(edition) and title==TITLE and lines.count(NOTE)==1
