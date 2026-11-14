# -*- coding: utf-8 -*-
"""Tests for the `encoding` option of the streaming parse entry points"""

import pytest

from ijson import common


# One representative document per encoding shape: legacy CJK double-byte
# encodings, a fixed-width encoding, UTF-16 (with and without BOM) and a
# single-byte non-ASCII encoding. Each document is parsed both from its UTF-8
# form (no `encoding` option) and from its form in the named encoding, and
# both runs must produce exactly the same events.
SAMPLE_DOCS = {
    'gbk': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'gb18030': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'big5': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'shift_jis': '{"key": "日本語テキスト", "list": [1, 2.5, "値"], "empty": {}}',
    'euc_jp': '{"key": "日本語テキスト", "list": [1, 2.5, "値"], "empty": {}}',
    'utf-16': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'utf-16-le': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'utf-32': '{"key": "中文字符串", "list": [1, 2.5, "值"], "empty": {}}',
    'latin-1': '{"key": "café au lait", "list": [1, 2.5, "à"], "empty": {}}',
}


@pytest.mark.parametrize("encoding", sorted(SAMPLE_DOCS))
def test_encoding_events_match_utf8(adaptor, encoding):
    """Events from an encoded document match those of its UTF-8 equivalent"""
    doc = SAMPLE_DOCS[encoding]
    expected = adaptor.basic_parse(doc.encode('utf-8'))
    assert expected == adaptor.basic_parse(doc.encode(encoding), encoding=encoding)


def test_encoding_supported_by_all_entry_points(adaptor):
    """`encoding` is honored by parse/items/kvitems, not only basic_parse"""
    doc = SAMPLE_DOCS['gbk']
    utf8_doc = doc.encode('utf-8')
    gbk_doc = doc.encode('gbk')
    assert adaptor.parse(utf8_doc) == adaptor.parse(gbk_doc, encoding='gbk')
    assert adaptor.items(utf8_doc, '') == adaptor.items(gbk_doc, '', encoding='gbk')
    assert adaptor.kvitems(utf8_doc, '') == adaptor.kvitems(gbk_doc, '', encoding='gbk')


def test_default_and_explicit_utf8_are_identical(adaptor):
    """Omitting `encoding` and passing utf-8 (or an alias) behave the same"""
    doc = SAMPLE_DOCS['gbk'].encode('utf-8')
    expected = adaptor.basic_parse(doc)
    assert expected == adaptor.basic_parse(doc, encoding='utf-8')
    assert expected == adaptor.basic_parse(doc, encoding='utf8')
    assert expected == adaptor.basic_parse(doc, encoding='UTF-8')


def test_unknown_encoding_raises_lookup_error(adaptor):
    """An unknown encoding name is rejected with LookupError"""
    with pytest.raises(LookupError):
        adaptor.basic_parse(b'{}', encoding='no-such-encoding')


def test_undecodable_bytes_raise_unicode_decode_error(adaptor):
    """Bytes invalid in the declared encoding raise UnicodeDecodeError,
    which is not an IncompleteJSONError (i.e. not a resumable truncation)"""
    assert not issubclass(UnicodeDecodeError, common.IncompleteJSONError)
    # 0xff is not a valid GBK lead byte
    with pytest.raises(UnicodeDecodeError):
        adaptor.basic_parse(b'{"key": "\xff"}', encoding='gbk')


def test_truncated_multibyte_char_is_incomplete_json(adaptor):
    """A stream ending mid-character is a truncation, not silently accepted.

    The document `true` is otherwise complete, so the IncompleteJSONError can
    only come from the decoder's final flush reporting the dangling byte."""
    lead_byte = '值'.encode('gbk')[:1]
    with pytest.raises(common.IncompleteJSONError):
        adaptor.basic_parse(b'true' + lead_byte, encoding='gbk')


def test_truncated_multibyte_char_is_incomplete_json_utf16(adaptor):
    """Same as above, for a fixed-width encoding (odd byte count)"""
    doc = 'true'.encode('utf-16-le') + '中'.encode('utf-16-le')[:1]
    with pytest.raises(common.IncompleteJSONError):
        adaptor.basic_parse(doc, encoding='utf-16-le')
