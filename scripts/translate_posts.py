#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

import frontmatter
from deep_translator import GoogleTranslator
from deep_translator.exceptions import TranslationNotFound

ROOT = Path("/home/patrick/Documents/website/jekyll-awayfromhome-sample/docs/_posts")
LANGS = ["de", "nl", "ar"]
POST_EXTS = {".md", ".markdown"}
DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-")


def derive_ref(file_name: str) -> str:
    stem = Path(file_name).stem
    return DATE_PREFIX_RE.sub("", stem)


def is_liquid_or_template(line: str) -> bool:
    s = line.strip()
    return s.startswith("{%") or s.startswith("{{") or s.startswith("<%");


def translate_text(translator: GoogleTranslator, text: str, cache: Dict[str, str]) -> str:
    if not text.strip():
        return text
    if text in cache:
        return cache[text]
    try:
        out = translator.translate(text)
    except (TranslationNotFound, Exception):
        # Keep original text when the provider cannot translate a specific line.
        out = text
    if out is None:
        out = text
    cache[text] = out
    return out


def translate_line(
    translator: GoogleTranslator,
    line: str,
    cache: Dict[str, str],
    in_code_block: bool,
    in_liquid_include: bool,
) -> Tuple[str, bool, bool]:
    stripped = line.strip()

    if stripped.startswith("```"):
        return line, not in_code_block, in_liquid_include
    if in_code_block:
        return line, in_code_block, in_liquid_include

    if in_liquid_include:
        # Keep multiline include argument lines untouched.
        if "%}" in stripped:
            return line, in_code_block, False
        return line, in_code_block, True

    if not stripped:
        return line, in_code_block, in_liquid_include

    # Keep Liquid/template lines untouched except explicit description values.
    if is_liquid_or_template(line):
        def repl_desc(match: re.Match) -> str:
            quote, val = match.group(1), match.group(2)
            return f'description={quote}{translate_text(translator, val, cache)}{quote}'

        new_line = re.sub(r'description=("|\')(.*?)(\1)', repl_desc, line)
        if stripped.startswith("{% include") and "%}" not in stripped:
            return new_line, in_code_block, True
        return new_line, in_code_block, in_liquid_include

    # Translate markdown headings.
    m = re.match(r'^(#{1,6}\s+)(.+)$', line)
    if m:
        return m.group(1) + translate_text(translator, m.group(2), cache), in_code_block, in_liquid_include

    # Translate bullet and numbered list items.
    m = re.match(r'^(\s*[-*+]\s+)(.+)$', line)
    if m:
        return m.group(1) + translate_text(translator, m.group(2), cache), in_code_block, in_liquid_include

    m = re.match(r'^(\s*\d+\.\s+)(.+)$', line)
    if m:
        return m.group(1) + translate_text(translator, m.group(2), cache), in_code_block, in_liquid_include

    # Translate HTML paragraph content in a conservative way.
    if stripped.startswith("<p") and stripped.endswith("</p>"):
        inner = re.sub(r'^<p[^>]*>|</p>$', '', stripped)
        translated = translate_text(translator, inner, cache)
        open_tag = re.match(r'^<p[^>]*>', stripped).group(0)
        return line.replace(stripped, f"{open_tag}{translated}</p>"), in_code_block, in_liquid_include

    return translate_text(translator, line, cache), in_code_block, in_liquid_include


def build_existing_ref_map(lang_dir: Path) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    if not lang_dir.exists():
        return out
    for p in sorted(lang_dir.iterdir()):
        if not p.is_file() or p.suffix not in POST_EXTS:
            continue
        post = frontmatter.load(p)
        ref = post.get("ref")
        if ref:
            out[str(ref)] = p
    return out


def main() -> None:
    base_posts = [p for p in sorted(ROOT.iterdir()) if p.is_file() and p.suffix in POST_EXTS]

    # Preload existing translation refs per language.
    existing_by_lang = {lang: build_existing_ref_map(ROOT / lang) for lang in LANGS}

    created: List[Path] = []
    updated_base: List[Path] = []

    for base_path in base_posts:
        post = frontmatter.load(base_path)
        ref = post.get("ref")
        if not ref:
            ref = derive_ref(base_path.name)
            post["ref"] = ref
            base_path.write_text(frontmatter.dumps(post), encoding="utf-8")
            updated_base.append(base_path)
            post = frontmatter.load(base_path)

        # Ensure an explicit lang value for base posts.
        if not post.get("lang"):
            post["lang"] = "en"
            base_path.write_text(frontmatter.dumps(post), encoding="utf-8")
            if base_path not in updated_base:
                updated_base.append(base_path)
            post = frontmatter.load(base_path)

        base_title = post.get("title", "")
        base_excerpt = post.get("excerpt", "")
        base_content = post.content

        for lang in LANGS:
            if str(ref) in existing_by_lang[lang]:
                continue

            translator = GoogleTranslator(source="en", target=lang)
            cache: Dict[str, str] = {}

            translated_post = frontmatter.Post(base_content, **dict(post.metadata))
            translated_post["lang"] = lang
            translated_post["ref"] = ref
            translated_post["title"] = translate_text(translator, str(base_title), cache) if base_title else base_title
            translated_post["excerpt"] = translate_text(translator, str(base_excerpt), cache) if base_excerpt else base_excerpt

            out_lines: List[str] = []
            in_code_block = False
            in_liquid_include = False
            for ln in translated_post.content.splitlines():
                out_ln, in_code_block, in_liquid_include = translate_line(
                    translator,
                    ln,
                    cache,
                    in_code_block,
                    in_liquid_include,
                )
                out_lines.append(out_ln)
            translated_post.content = "\n".join(out_lines) + "\n"

            out_dir = ROOT / lang
            out_dir.mkdir(parents=True, exist_ok=True)
            out_file = out_dir / base_path.name
            out_file.write_text(frontmatter.dumps(translated_post), encoding="utf-8")
            created.append(out_file)
            existing_by_lang[lang][str(ref)] = out_file

    print(f"Updated base posts with ref/lang: {len(updated_base)}")
    for p in updated_base:
        print(f"  UPDATED {p}")

    print(f"Created translations: {len(created)}")
    for p in created:
        print(f"  CREATED {p}")


if __name__ == "__main__":
    main()
