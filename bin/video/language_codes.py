#!/usr/bin/env python3
"""
ISO 639 language codes reference
Provides authoritative mapping between 2-char (ISO 639-1) and 3-char (ISO 639-2) codes
"""

# ISO 639-1 to ISO 639-2 mapping (authoritative)
# Source: Library of Congress ISO 639-2 Code Table
ISO_639_1_TO_639_2 = {
    'aa': ['aar'],      # Afar
    'ab': ['abk'],      # Abkhazian
    'ae': ['ave'],      # Avestan
    'af': ['afr'],      # Afrikaans
    'ak': ['aka'],      # Akan
    'am': ['amh'],      # Amharic
    'an': ['arg'],      # Aragonese
    'ar': ['ara'],      # Arabic
    'as': ['asm'],      # Assamese
    'av': ['ava'],      # Avaric
    'ay': ['aym'],      # Aymara
    'az': ['aze'],      # Azerbaijani
    'ba': ['bak'],      # Bashkir
    'be': ['bel'],      # Belarusian
    'bg': ['bul'],      # Bulgarian
    'bh': ['bih'],      # Bihari languages
    'bi': ['bis'],      # Bislama
    'bm': ['bam'],      # Bambara
    'bn': ['ben'],      # Bengali
    'bo': ['bod', 'tib'], # Tibetan
    'br': ['bre'],      # Breton
    'bs': ['bos'],      # Bosnian
    'ca': ['cat'],      # Catalan
    'ce': ['che'],      # Chechen
    'ch': ['cha'],      # Chamorro
    'co': ['cos'],      # Corsican
    'cr': ['cre'],      # Cree
    'cs': ['cze', 'ces'], # Czech
    'cu': ['chu'],      # Church Slavic
    'cv': ['chv'],      # Chuvash
    'cy': ['cym', 'wel'], # Welsh
    'da': ['dan'],      # Danish
    'de': ['ger', 'deu'], # German
    'dv': ['div'],      # Divehi
    'dz': ['dzo'],      # Dzongkha
    'ee': ['ewe'],      # Ewe
    'el': ['gre', 'ell'], # Greek
    'en': ['eng'],      # English
    'eo': ['epo'],      # Esperanto
    'es': ['spa'],      # Spanish
    'et': ['est'],      # Estonian
    'eu': ['eus'],      # Basque
    'fa': ['per', 'fas'], # Persian
    'ff': ['ful'],      # Fulah
    'fi': ['fin'],      # Finnish
    'fj': ['fij'],      # Fijian
    'fo': ['fao'],      # Faeroese
    'fr': ['fre', 'fra'], # French
    'fy': ['fry'],      # Frisian
    'ga': ['gle'],      # Irish
    'gd': ['gla'],      # Gaelic
    'gl': ['glg'],      # Galician
    'gn': ['grn'],      # Guarani
    'gu': ['guj'],      # Gujarati
    'gv': ['glv'],      # Manx
    'ha': ['hau'],      # Hausa
    'he': ['heb'],      # Hebrew
    'hi': ['hin'],      # Hindi
    'ho': ['hmo'],      # Hiri Motu
    'hr': ['hrv'],      # Croatian
    'ht': ['hat'],      # Haitian
    'hu': ['hun'],      # Hungarian
    'hy': ['hye'],      # Armenian
    'hz': ['her'],      # Herero
    'ia': ['ina'],      # Interlingua
    'id': ['ind'],      # Indonesian
    'ie': ['ile'],      # Interlingue
    'ig': ['ibo'],      # Igbo
    'ii': ['iii'],      # Sichuan Yi
    'ik': ['ipk'],      # Inupiaq
    'io': ['ido'],      # Ido
    'is': ['ice', 'isl'], # Icelandic
    'it': ['ita'],      # Italian
    'iu': ['iku'],      # Inuktitut
    'ja': ['jpn'],      # Japanese
    'jv': ['jav'],      # Javanese
    'ka': ['geo', 'kat'], # Georgian
    'kg': ['kon'],      # Kongo
    'ki': ['kik'],      # Kikuyu
    'kj': ['kua'],      # Kuanyama
    'kk': ['kaz'],      # Kazakh
    'kl': ['kal'],      # Kalaallisut
    'km': ['khm'],      # Khmer
    'kn': ['kan'],      # Kannada
    'ko': ['kor'],      # Korean
    'kr': ['kau'],      # Kanuri
    'ks': ['kas'],      # Kashmiri
    'ku': ['kur'],      # Kurdish
    'kv': ['kom'],      # Komi
    'kw': ['cor'],      # Cornish
    'ky': ['kir'],      # Kirghiz
    'la': ['lat'],      # Latin
    'lb': ['ltz'],      # Luxembourgish
    'lg': ['lug'],      # Ganda
    'li': ['lim'],      # Limburgan
    'ln': ['lin'],      # Lingala
    'lo': ['lao'],      # Lao
    'lt': ['lit'],      # Lithuanian
    'lu': ['lub'],      # Luba-Katanga
    'lv': ['lav'],      # Latvian
    'mg': ['mlg'],      # Malagasy
    'mh': ['mah'],      # Marshallese
    'mi': ['mao', 'mri'], # Maori
    'mk': ['mac', 'mkd'], # Macedonian
    'ml': ['mal'],      # Malayalam
    'mn': ['mon'],      # Mongolian
    'mr': ['mar'],      # Marathi
    'ms': ['may', 'msa'], # Malay
    'mt': ['mlt'],      # Maltese
    'my': ['bur', 'mya'], # Burmese
    'na': ['nau'],      # Nauru
    'nb': ['nob'],      # Bokmål, Norwegian
    'nd': ['nde'],      # Ndebele, North
    'ne': ['nep'],      # Nepali
    'ng': ['ndo'],      # Ndonga
    'nl': ['dut', 'nld'], # Dutch
    'nn': ['nno'],      # Norwegian Nynorsk
    'no': ['nor'],      # Norwegian
    'nr': ['nbl'],      # Ndebele, South
    'nv': ['nav'],      # Navajo
    'ny': ['nya'],      # Chichewa
    'oc': ['oci'],      # Occitan
    'oj': ['oji'],      # Ojibwa
    'om': ['orm'],      # Oromo
    'or': ['ori'],      # Oriya
    'os': ['oss'],      # Ossetian
    'pa': ['pan'],      # Panjabi
    'pi': ['pli'],      # Pali
    'pl': ['pol'],      # Polish
    'ps': ['pus'],      # Pushto
    'pt': ['por'],      # Portuguese
    'qu': ['que'],      # Quechua
    'rm': ['roh'],      # Romansh
    'rn': ['run'],      # Rundi
    'ro': ['rum', 'ron'], # Romanian
    'ru': ['rus'],      # Russian
    'rw': ['kin'],      # Kinyarwanda
    'sa': ['san'],      # Sanskrit
    'sc': ['srd'],      # Sardinian
    'sd': ['snd'],      # Sindhi
    'se': ['sme'],      # Northern Sami
    'sg': ['sag'],      # Sango
    'si': ['sin'],      # Sinhala
    'sk': ['slo', 'slk'], # Slovak
    'sl': ['slv'],      # Slovenian
    'sm': ['smo'],      # Samoan
    'sn': ['sna'],      # Shona
    'so': ['som'],      # Somali
    'sq': ['sqi', 'alb'], # Albanian
    'sr': ['srp'],      # Serbian
    'ss': ['ssw'],      # Swati
    'st': ['sot'],      # Sotho, Southern
    'su': ['sun'],      # Sundanese
    'sv': ['swe'],      # Swedish
    'sw': ['swa'],      # Swahili
    'ta': ['tam'],      # Tamil
    'te': ['tel'],      # Telugu
    'tg': ['tgk'],      # Tajik
    'th': ['tha'],      # Thai
    'ti': ['tir'],      # Tigrinya
    'tk': ['tuk'],      # Turkmen
    'tl': ['tgl'],      # Tagalog
    'tn': ['tsn'],      # Tswana
    'to': ['ton'],      # Tonga
    'tr': ['tur'],      # Turkish
    'ts': ['tso'],      # Tsonga
    'tt': ['tat'],      # Tatar
    'tw': ['twi'],      # Twi
    'ty': ['tah'],      # Tahitian
    'ug': ['uig'],      # Uighur
    'uk': ['ukr'],      # Ukrainian
    'ur': ['urd'],      # Urdu
    'uz': ['uzb'],      # Uzbek
    've': ['ven'],      # Venda
    'vi': ['vie'],      # Vietnamese
    'vo': ['vol'],      # Volapük
    'wa': ['wln'],      # Walloon
    'wo': ['wol'],      # Wolof
    'xh': ['xho'],      # Xhosa
    'yi': ['yid'],      # Yiddish
    'yo': ['yor'],      # Yoruba
    'za': ['zha'],      # Zhuang
    'zh': ['chi', 'zho'], # Chinese
    'zu': ['zul'],      # Zulu
}

# Reverse mapping: ISO 639-2 to ISO 639-1
ISO_639_2_TO_639_1 = {}
for iso_639_1, iso_639_2_codes in ISO_639_1_TO_639_2.items():
    for iso_639_2 in iso_639_2_codes:
        ISO_639_2_TO_639_1[iso_639_2] = iso_639_1

def normalize_language_code(lang_code: str) -> str:
    """Normalize any language code to ISO 639-1 (2-char) format"""
    if not lang_code:
        return 'und'  # undefined
    
    lang_code = lang_code.lower().strip()
    
    # If already 2-char, return as-is
    if len(lang_code) == 2 and lang_code in ISO_639_1_TO_639_2:
        return lang_code
    
    # If 3-char, convert to 2-char
    if len(lang_code) == 3 and lang_code in ISO_639_2_TO_639_1:
        return ISO_639_2_TO_639_1[lang_code]
    
    # If 2-char but not in mapping, return as-is (might be a valid code we don't have)
    if len(lang_code) == 2:
        return lang_code
    
    # Unknown format, return as-is
    return lang_code

def get_all_variants(lang_code: str) -> list[str]:
    """Get all known variants of a language code"""
    normalized = normalize_language_code(lang_code)
    
    if normalized in ISO_639_1_TO_639_2:
        variants = [normalized] + ISO_639_1_TO_639_2[normalized]
        return list(set(variants))  # Remove duplicates
    
    # If not found, return the original code
    return [lang_code]

def matches_language(code1: str, code2: str) -> bool:
    """Check if two language codes refer to the same language"""
    norm1 = normalize_language_code(code1)
    norm2 = normalize_language_code(code2)
    
    return norm1 == norm2 and norm1 != 'und'
