import sys
import re


def clean_m3u(input_file, output_file='out.m3u8'):
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]

    cleaned = ["#EXTM3U"]
    seen = set()
    i = 0

    while i < len(lines):
        line = lines[i]

        if line.startswith('#EXTINF'):
            info = line
            url = lines[i + 1] if i + 1 < len(lines) else ''

            # Optional deduplication based on URL or name
            if url in seen:
                i += 2
                continue

            seen.add(url)
            cleaned.append(info)
            cleaned.append(url)
            i += 2
        else:
            i += 1

    with open(output_file, 'w', encoding='utf-8') as f:
        for line in cleaned:
            f.write(line + '\n')

    print(f"✅ Cleaned playlist written to: {output_file} ({len(cleaned)//2} channels)")


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python clean_m3u.py <input.m3u>")
    else:
        clean_m3u(sys.argv[1])
