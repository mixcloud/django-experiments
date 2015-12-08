try:
    from django.template import base as template_base
    from django.template import Library
    register = Library()
except ImportError:
    from django import template as template_base
    register = template_base.Library()

def raw(parser, token):
    # Whatever is between {% raw %} and {% endraw %} will be preserved as
    # raw, unrendered template code.
    text = []
    parse_until = 'endraw'
    tag_mapping = {
        template_base.TOKEN_TEXT: ('', ''),
        template_base.TOKEN_VAR: ('{{', '}}'),
        template_base.TOKEN_BLOCK: ('{%', '%}'),
        template_base.TOKEN_COMMENT: ('{#', '#}'),
    }
    # By the time this template tag is called, the template system has already
    # lexed the template into tokens. Here, we loop over the tokens until
    # {% endraw %} and parse them to TextNodes. We have to add the start and
    # end bits (e.g. "{{" for variables) because those have already been
    # stripped off in a previous part of the template-parsing process.
    while parser.tokens:
        token = parser.next_token()
        if token.token_type == template_base.TOKEN_BLOCK and token.contents == parse_until:
            return template_base.TextNode(u''.join(text))
        start, end = tag_mapping[token.token_type]
        text.append(u'%s%s%s' % (start, token.contents, end))
    parser.unclosed_block_tag(parse_until)
raw = register.tag(raw)

def sort_by_key(field, currently):
    is_negative = currently.find('-') is 0
    current_field = currently.lstrip('-')

    if current_field == field and is_negative:
        return field
    elif current_field == field:
        return '-' + field
    else:
        return field

sort_by_key = register.filter(sort_by_key)
