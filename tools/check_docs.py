"""Validate local documentation links, code fences, Bash examples, and Python syntax."""
import ast
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote,urlsplit

ROOT=Path(__file__).resolve().parents[1]


def prose(text):
    lines=[];opened=None
    for line in text.splitlines():
        match=re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$',line)
        if opened:
            if match and match[1][0]==opened[0] and len(match[1])>=len(opened) and not match[2].strip():opened=None
        elif match:opened=match[1]
        else:lines.append(line)
    return '\n'.join(lines),opened is None


def anchors(text):
    result=set();used={}
    for line in text.splitlines():
        match=re.match(r'^#{1,6}\s+(.+)',line)
        if match:
            slug=re.sub(r'[^\w\- ]','',match[1].lower()).replace(' ','-')
            count=used.get(slug,0);used[slug]=count+1
            result.add(f'{slug}-{count}' if count else slug)
    return result


def main():
    names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
    files=[ROOT/name for name in set(names) if name and (ROOT/name).is_file()]
    documents={p:prose(p.read_text()) for p in files if p.suffix=='.md'}
    errors=[];links=0;bash=0
    for p in files:
        if p.suffix=='.py':
            try:ast.parse(p.read_text(),filename=str(p))
            except SyntaxError as exc:errors.append(str(exc))
    for p,(content,closed) in documents.items():
        if not closed:errors.append(f'{p.name}: unclosed code fence')
        for match in re.finditer(r'\]\(([^\n)]+)\)',content):
            target=match[1].strip().strip('<>');url=urlsplit(target)
            if url.scheme or url.netloc:continue
            links+=1;dest=(p.parent/unquote(url.path)).resolve() if url.path else p
            if not dest.exists():errors.append(f'{p.name}: missing {target}')
            elif url.fragment and dest in documents and unquote(url.fragment) not in anchors(documents[dest][0]):errors.append(f'{p.name}: missing heading {target}')
        for block in re.findall(r'^```bash\n(.*?)^```',p.read_text(),re.M|re.S):
            result=subprocess.run(['bash','-n'],input=block,text=True,capture_output=True)
            bash+=1
            if result.returncode:errors.append(f'{p.name}: invalid Bash example')
    if errors:print('\n'.join(errors));return 1
    print(f'Documentation OK: {len(documents)} documents, {links} local links, {bash} Bash examples; Python source syntax valid.')
    return 0


if __name__=='__main__':raise SystemExit(main())
