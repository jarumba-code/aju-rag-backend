import os
base = r'c:\Users\power\Desktop\SCHOOL RAG\frontend\src'
files = {'app/chat/page.tsx': '"use client";'
}
for rel_path, content in files.items():
    full = os.path.join(base, rel_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf8') as f:
        f.write(content)
    print('Wrote', full)
