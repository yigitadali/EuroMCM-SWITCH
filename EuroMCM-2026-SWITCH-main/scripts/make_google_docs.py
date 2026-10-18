
import argparse
import re
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PAPER=ROOT/'paper'

def expand(path):
    text=path.read_text()
    return re.sub(r'\\input\{([^}]+)\}',lambda m:expand(PAPER/(m[1]+'.tex')),text)

def main():
    p=argparse.ArgumentParser();p.add_argument('--pandoc',default='pandoc');args=p.parse_args()
    text=expand(PAPER/'main.tex')
    ids=['problem','routellm','frugalgpt','routellmcode','gsm']
    text=re.sub(r'\\includegraphics\[([^\]]*)\]\{([^}]+)\.pdf\}',
                lambda m:'\\includegraphics['+m[1]+']{'+m[2]+'.png}',text)
    text=re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+', '.join(str(ids.index(k)+1) for k in m[1].split(','))+']',text)
    text=text.replace('\\begin{thebibliography}{9}','\\section*{References}\n\\begin{enumerate}')
    text=text.replace('\\end{thebibliography}','\\end{enumerate}')
    text=re.sub(r'\\bibitem\{[^}]+\}',lambda m:'\\item',text)
    style=(PAPER/'euro-mcm.sty').read_text()
    team=re.search(r'\\newcommand\{\\TeamNumber\}\{(\d{9})\}',style)[1]
    text=text.replace('\\usepackage{euro-mcm}','\\newcommand{\\TeamNumber}{'+team+'}')
    text=text.replace('\\widehat Q','\\widehat{Q}').replace('\\hat d','\\hat{d}')
    text=text.replace('G_{\\rm new}','G_{\\mathrm{new}}').replace('G_{\\rm old}','G_{\\mathrm{old}}')
    text=text.replace('\\begin{equation}','$$').replace('\\end{equation}','$$')
    text=text.replace('\\begin{align}','$$\\begin{aligned}').replace('\\end{align}','\\end{aligned}$$')
    (PAPER/'google_docs_conversion.tex').write_text(text)
    subprocess.run([args.pandoc,'google_docs_conversion.tex','--from=latex+raw_tex','--to=docx',
                    '--resource-path=.:../figures','--reference-doc=google_docs_reference.docx',
                    '--lua-filter=../scripts/google_docs.lua','--number-sections',
                    '--output=SWITCH_Google_Docs.docx'],cwd=PAPER,check=True)
    print('Editable DOCX generated. Review layout after Google Docs import.')

if __name__=='__main__':main()
