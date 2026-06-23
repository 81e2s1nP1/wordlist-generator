
import argparse
import itertools
import json
import re
import sys
from pathlib import Path

LEET_MAP = {
    'a': '@', 'A': '@', 'e': '3', 'E': '3',
    'i': '1', 'I': '1', 'o': '0', 'O': '0',
    's': '$', 'S': '$', 't': '7', 'T': '7',
    'g': '9', 'G': '9', 'b': '8', 'B': '8',
}

SUFFIX_NUMBERS = [
    '1', '12', '123', '1234', '12345', '123456',
    '2020', '2021', '2022', '2023', '2024', '2025',
    '69', '88', '99', '00', '007',
]
SUFFIX_SYMBOLS = ['!', '!!', '@', '#', '$', '!@#', '123!', '@123', '#1', '$1', '!1']
PREFIX_SYMBOLS = ['!', '@', '#', '_', '.', '-']
VN_SUFFIXES    = ['@123', '123456', '@1234', 'dn', 'hcm', 'sg', 'nt', 'hue', 'qn', 'vn', 'hn', 'hp']
KEYBOARD_WALKS = ['qwerty', 'qwerty123', '12345678', 'asdfgh', 'zxcvbn', 'qazwsx', '1q2w3e', '1q2w3e4r']

def parse_dob(raw: str) -> dict:
    digits = ''.join(c for c in raw if c.isdigit())
    result = {}
    if len(digits) >= 8:
        result['day']   = digits[:2]
        result['month'] = digits[2:4]
        result['year']  = digits[4:8]
        result['year2'] = digits[6:8]
    elif len(digits) >= 4:
        result['year']  = digits[:4]
        result['year2'] = digits[2:4]
    result['full'] = digits
    return result

def leet(word: str) -> str:
    return ''.join(LEET_MAP.get(c, c) for c in word)

def capitalize_variants(word: str) -> list:
    return list({word.lower(), word.upper(), word.capitalize(), word.title()})

def tokenize(raw: str) -> list:
    return [t.strip() for t in re.split(r'[,\s/]+', raw) if t.strip()]

def build_bases(args) -> list:
    bases = set()

    def add(word):
        if word and len(word) >= 2:
            for v in capitalize_variants(word):
                bases.add(v)

    if args.name:
        for t in tokenize(args.name): add(t)
    if args.relatives:
        for t in tokenize(args.relatives): add(t)
    if args.keywords:
        for t in tokenize(args.keywords): add(t)
    if args.address:
        for t in tokenize(args.address): add(t)
    if args.phone:
        ph = ''.join(c for c in args.phone if c.isdigit())
        if ph:
            for s in [ph, ph[-4:], ph[-6:], ph[:4], ph[:6]]:
                bases.add(s)
    if args.dob:
        d = parse_dob(args.dob)
        for v in d.values():
            if v: bases.add(v)
        if 'day' in d and 'month' in d:
            bases.add(d['day'] + d['month'])
            bases.add(d['month'] + d['day'])

    return [b for b in bases if b]

def mutate_osint(bases: list, args) -> set:
    result = set()
    dob = parse_dob(args.dob) if args.dob else {}

    for w in bases:
        if not args.no_leet:
            lw = leet(w)
            result.add(lw)
            result.add(lw.capitalize())
        if not args.no_case:
            result.update(capitalize_variants(w))
        if not args.no_reverse:
            rev = w[::-1]
            result.add(rev)
            result.add(rev.capitalize())
        if not args.no_double:
            result.add(w + w)
            result.add(w.lower() + w.lower())
        if not args.no_suffix_num:
            for s in SUFFIX_NUMBERS:
                result.add(w + s)
            if dob.get('year'):
                result.add(w + dob['year'])
                if dob.get('year2'): result.add(w + dob['year2'])
            if dob.get('day') and dob.get('month'):
                result.add(w + dob['day'] + dob['month'])
                result.add(w + dob['month'] + dob['day'])
        if not args.no_suffix_sym:
            for s in SUFFIX_SYMBOLS: result.add(w + s)
        if not args.no_prefix_sym:
            for s in PREFIX_SYMBOLS: result.add(s + w)
        if args.vn:
            for s in VN_SUFFIXES:
                result.add(w + s)
                result.add(w.capitalize() + s)

    if not args.no_name_combo and dob.get('year'):
        words = [b for b in bases if not b.isdigit() and len(b) > 2][:6]
        for w in words:
            result.add(w + dob['year'])
            result.add(w.capitalize() + dob['year'])
            if dob.get('year2'): result.add(w + dob['year2'])

    if not args.no_name_combo:
        words = [b for b in bases if not b.isdigit() and len(b) > 2][:5]
        for a, b in itertools.permutations(words, 2):
            result.add(a.lower() + b.lower())
            result.add(a.capitalize() + b.lower())
            result.add(a.lower() + '_' + b.lower())
            result.add(a.lower() + '.' + b.lower())
            if dob.get('year'):
                result.add(a.lower() + b.lower() + dob['year'])

    if args.keyboard:
        result.update(KEYBOARD_WALKS)

    result -= set(bases)
    return result

PLACEHOLDER_TO_KEY = {
    "word": "words", "words": "words",
    "year": "years", "years": "years",
    "number": "numbers", "numbers": "numbers",
    "special": "specials", "specials": "specials",
    "month": "months", "months": "months",
    "season": "seasons", "seasons": "seasons",
    "name": "names", "names": "names",
    "leet": "leets", "leets": "leets",
}

def resolve_key(placeholder, config):
    if placeholder in PLACEHOLDER_TO_KEY:
        return PLACEHOLDER_TO_KEY[placeholder]
    if placeholder in config:
        return placeholder
    if placeholder + "s" in config:
        return placeholder + "s"
    return placeholder

def generate_from_patterns(config: dict) -> list:
    results = []
    for pattern in config.get("patterns", []):
        placeholders = re.findall(r"\{(\w+)\}", pattern)
        if not placeholders:
            results.append(pattern)
            continue
        value_lists = []
        skip = False
        for ph in placeholders:
            values = config.get(resolve_key(ph, config), [])
            if not values:
                skip = True
                break
            value_lists.append(values)
        if skip:
            continue
        for combo in itertools.product(*value_lists):
            word = pattern
            for ph, val in zip(placeholders, combo):
                word = word.replace("{" + ph + "}", val, 1)
            results.append(word)
    return results

def osint_to_config(bases: list, mutations: set, dob_str: str) -> dict:
    dob   = parse_dob(dob_str) if dob_str else {}
    words = sorted({b for b in bases if not b.isdigit() and len(b) >= 2})
    leets = sorted({leet(w) for w in words if leet(w) != w})
    years = []
    if dob.get('year'):  years.append(dob['year'])
    if dob.get('year2'): years.append(dob['year2'])
    years += ['2024', '2025', '2023']
    months = []
    if dob.get('day') and dob.get('month'):
        months.append(dob['day'] + dob['month'])
        months.append(dob['month'] + dob['day'])

    return {
        "words":    words,
        "leets":    leets,
        "years":    years,
        "numbers":  ["123", "1234", "12345", "123456", "88", "99", "00"],
        "specials": ["!", "@", "#", "$", "!@#", "@123"],
        "months":   months,
        "patterns": [
            "{word}",
            "{leet}",
            "{word}{year}",
            "{word}{numbers}",
            "{word}{specials}",
            "{word}{year}{specials}",
            "{word}{specials}{year}",
            "{word}{month}",
            "{word}{month}{year}",
            "{leet}{year}",
            "{leet}{specials}",
            "{leet}{numbers}",
            "{specials}{word}",
            "{specials}{leet}",
        ]
    }

def apply_filters(wordlist: list, args) -> list:
    min_l = args.min or 6
    max_l = args.max or 32
    wordlist = [w for w in wordlist if min_l <= len(w) <= max_l]

    exclude_patterns = []
    for raw in (args.exclude or []):
        for part in raw.split("||"):
            part = part.strip()
            if part: exclude_patterns.append(part)

    if args.exclude_file:
        with open(args.exclude_file, encoding='utf-8') as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith('#'):
                    exclude_patterns.append(line)

    if exclude_patterns:
        compiled = [re.compile(p) for p in exclude_patterns]
        before = len(wordlist)
        wordlist = [w for w in wordlist if not any(rx.search(w) for rx in compiled)]
        print(f"[~] Exclude filter: removed {before - len(wordlist)} entries")

    if not getattr(args, 'no_dedupe', False):
        wordlist = list(dict.fromkeys(wordlist))

    if getattr(args, 'sort', False):
        wordlist.sort()

    return wordlist

def build_parser():
    p = argparse.ArgumentParser(
        description='mutagen.py — OSINT Mutation + Pattern Wordlist Generator',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Mode 1 - OSINT only:
  python mutagen.py -n "<USERNAME>" -d 15081995 -p 0912345678 -o out.txt

Mode 2 - Pattern only (JSON config):
  python mutagen.py -c config.json -o out.txt

Mode 3 - OSINT + auto pattern:
  python mutagen.py -n "<USERNAME>" -d 15081995 --pattern-mode -o out.txt

Mode 4 - Export generated config for reuse:
  python mutagen.py -n "<USERNAME>" -d 15081995 --export-config config.json
"""
    )

    g = p.add_argument_group('OSINT inputs')
    g.add_argument('-n', '--name',      help='Full name')
    g.add_argument('-d', '--dob',       help='Date of birth (e.g. 15081995)')
    g.add_argument('-p', '--phone',     help='Phone number')
    g.add_argument('-a', '--address',   help='Address / district')
    g.add_argument('-r', '--relatives', help='Relative names, comma-separated')
    g.add_argument('-k', '--keywords',  help='Extra keywords (pet, nickname, etc.)')

    pc = p.add_argument_group('Pattern engine')
    pc.add_argument('-c', '--config',       help='JSON config file')
    pc.add_argument('--pattern-mode',       action='store_true',
                    help='Enable pattern engine with auto config from OSINT data')
    pc.add_argument('--export-config',      metavar='FILE',
                    help='Export auto-generated config to JSON file')

    m = p.add_argument_group('Disable mutations')
    m.add_argument('--no-leet',       action='store_true')
    m.add_argument('--no-case',       action='store_true')
    m.add_argument('--no-reverse',    action='store_true')
    m.add_argument('--no-double',     action='store_true')
    m.add_argument('--no-suffix-num', action='store_true', dest='no_suffix_num')
    m.add_argument('--no-suffix-sym', action='store_true', dest='no_suffix_sym')
    m.add_argument('--no-prefix-sym', action='store_true', dest='no_prefix_sym')
    m.add_argument('--no-name-combo', action='store_true', dest='no_name_combo')
    m.add_argument('--vn',            action='store_true', help='Append common VN suffixes')
    m.add_argument('--keyboard',      action='store_true', help='Include keyboard walks')

    o = p.add_argument_group('Filter & output')
    o.add_argument('-o', '--output',     default='-',  help='Output file (default: stdout)')
    o.add_argument('--min',              type=int, default=6,  metavar='N', help='Min length (default: 6)')
    o.add_argument('--max',              type=int, default=32, metavar='N', help='Max length (default: 32)')
    o.add_argument('-e', '--exclude',    action='append', default=[],
                   help='Regex exclusion pattern, use || for multiple')
    o.add_argument('--exclude-file',     metavar='FILE', help='File with exclusion patterns (one per line)')
    o.add_argument('--no-dedupe',        action='store_true', help='Keep duplicates')
    o.add_argument('--sort',             action='store_true', help='Sort output alphabetically')
    o.add_argument('--stats',            action='store_true', help='Print statistics')

    return p

def print_stats(bases, osint_words, pattern_words, final):
    print(f"\n{'─'*42}")
    print(f"  Base words         : {len(bases)}")
    print(f"  OSINT mutations    : {len(osint_words) - len(bases)}")
    print(f"  Pattern candidates : {len(pattern_words)}")
    print(f"  Total before filter: {len(osint_words) + len(pattern_words)}")
    print(f"  Final (dedup)      : {len(final)}")
    if final:
        lengths = [len(w) for w in final]
        print(f"  Avg length         : {sum(lengths)/len(lengths):.1f}")
        print(f"  Min / Max length   : {min(lengths)} / {max(lengths)}")
    print(f"{'─'*42}\n")

def main():
    parser = build_parser()
    args   = parser.parse_args()

    has_osint  = any([args.name, args.dob, args.phone, args.address, args.relatives, args.keywords])
    has_config = bool(args.config)

    if not has_osint and not has_config:
        parser.print_help()
        print('\n[!] At least one OSINT input or -c config.json is required.', file=sys.stderr)
        sys.exit(1)

    all_words   = set()
    bases       = []
    osint_set   = set()
    pattern_set = set()

    if has_osint:
        bases     = build_bases(args)
        mutations = mutate_osint(bases, args)
        osint_set = set(bases) | mutations
        all_words |= osint_set
        print(f"[+] OSINT bases: {len(bases)} | mutations: {len(mutations)}")

    if has_config:
        with open(args.config, encoding='utf-8') as f:
            config = json.load(f)
        pattern_words = generate_from_patterns(config)
        pattern_set   = set(pattern_words)
        all_words    |= pattern_set
        print(f"[+] Pattern engine (config): {len(pattern_words)} candidates")

    if has_osint and args.pattern_mode and not has_config:
        auto_config   = osint_to_config(bases, osint_set, args.dob or '')
        pattern_words = generate_from_patterns(auto_config)
        pattern_set   = set(pattern_words)
        all_words    |= pattern_set
        print(f"[+] Pattern engine (auto): {len(pattern_words)} candidates")
        if args.export_config:
            with open(args.export_config, 'w', encoding='utf-8') as f:
                json.dump(auto_config, f, ensure_ascii=False, indent=2)
            print(f"[+] Config saved -> {args.export_config}")

    if args.export_config and not args.pattern_mode:
        auto_config = osint_to_config(bases, osint_set, args.dob or '')
        with open(args.export_config, 'w', encoding='utf-8') as f:
            json.dump(auto_config, f, ensure_ascii=False, indent=2)
        print(f"[+] Config saved -> {args.export_config}")

    final = apply_filters(list(all_words), args)

    if args.stats:
        print_stats(bases, osint_set, pattern_set, final)

    if args.output == '-':
        for w in final:
            print(w)
    else:
        Path(args.output).write_text('\n'.join(final), encoding='utf-8')
        print(f"[+] Saved {len(final)} entries -> {args.output}")

if __name__ == '__main__':
    main()