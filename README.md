# wordlist-generator

OSINT-based mutation wordlist generator with pattern engine support.

---

## Requirements

Python 3.6+, no external dependencies.

---

## Modes

**Mode 1 — OSINT only**
```bash
python mutagen.py -n "John Smith" -d 15081990 -p 0912345678 -r "Anna,Max" -k "dragon" -o wordlist.txt
```

**Mode 2 — Pattern only (JSON config)**
```bash
python mutagen.py -c config.json -o wordlist.txt
```

**Mode 3 — OSINT + auto pattern (recommended)**
```bash
python mutagen.py -n "John Smith" -d 15081990 --pattern-mode --stats -o wordlist.txt
```

**Mode 4 — Export config for manual tuning**
```bash
python mutagen.py -n "John Smith" -d 15081990 --export-config config.json
# edit config.json, then:
python mutagen.py -c config.json -o wordlist.txt
```

---

## Options

### OSINT inputs (all optional)

| Flag | Description |
|------|-------------|
| `-n, --name` | Full name |
| `-d, --dob` | Date of birth — `15081990` or `15/08/1990` |
| `-p, --phone` | Phone number |
| `-a, --address` | Address or district |
| `-r, --relatives` | Relative/friend names, comma-separated |
| `-k, --keywords` | Extra keywords — pet, nickname, etc. |

### Pattern engine

| Flag | Description |
|------|-------------|
| `-c, --config` | JSON config file |
| `--pattern-mode` | Auto-build config from OSINT data and run pattern engine |
| `--export-config FILE` | Export auto-generated config to file |

### Disable mutations (all enabled by default)

| Flag | Description |
|------|-------------|
| `--no-leet` | Disable leet speak (`a→@`, `e→3`, etc.) |
| `--no-case` | Disable case variants |
| `--no-reverse` | Disable reverse strings |
| `--no-double` | Disable double words (`passpass`) |
| `--no-suffix-num` | Disable numeric suffixes |
| `--no-suffix-sym` | Disable symbol suffixes |
| `--no-prefix-sym` | Disable symbol prefixes |
| `--no-name-combo` | Disable name combinations |
| `--vn` | Enable common VN suffixes (`hcm`, `sg`, `@123`, etc.) |
| `--keyboard` | Enable keyboard walks (`qwerty`, `1q2w3e`, etc.) |

### Filter & output

| Flag | Description |
|------|-------------|
| `-o, --output` | Output file (default: stdout) |
| `--min N` | Minimum password length (default: 6) |
| `--max N` | Maximum password length (default: 32) |
| `-e PATTERN` | Regex exclusion — use `\|\|` to chain multiple |
| `--exclude-file FILE` | File with exclusion patterns, one per line |
| `--sort` | Sort output alphabetically |
| `--no-dedupe` | Keep duplicates |
| `--stats` | Print generation statistics |

---

## JSON config format

```json
{
  "words": ["admin", "root", "john"],
  "years": ["2024", "2025"],
  "numbers": ["123", "1234"],
  "specials": ["!", "@", "#"],
  "months": ["0815", "1508"],
  "patterns": [
    "{word}",
    "{word}{year}",
    "{word}{year}{specials}",
    "{word}{numbers}"
  ]
}
```

Patterns with empty lists are automatically skipped.

---

## Examples

```bash
# Full OSINT + pattern, filter 8-16 chars, save
python mutagen.py -n "John Smith" -d 15081990 -p 0912345678 \
  -r "Anna,Max" -k "dragon" --pattern-mode --min 8 --max 16 \
  --vn --stats -o wordlist.txt

# Exclude numeric-only and short patterns
python mutagen.py -n "John Smith" -d 15081990 \
  -e "^\d+$||^.{1,5}$" -o wordlist.txt

# Pipe into hashcat
python mutagen.py -n "John Smith" -d 15081990 --pattern-mode -o wl.txt
hashcat -a 0 -m 0 hash.txt wl.txt

# Pipe into hydra
python mutagen.py -n "John Smith" -d 15081990 -o wl.txt
hydra -l admin -P wl.txt ssh://192.168.1.1
```
