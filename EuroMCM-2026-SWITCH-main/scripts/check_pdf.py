from pathlib import Path
import argparse
import json
import re
from collections import Counter
import fitz
ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('pdf',nargs='?',default=str(ROOT/'paper/main.pdf'))
    p.add_argument('--render-dir');args=p.parse_args()
    path=Path(args.pdf);doc=fitz.open(path);texts=[page.get_text() for page in doc]
    ai=[i for i,t in enumerate(texts) if 'Report on the Use of AI Tools' in t]
    # Ignore the TOC occurrence: the actual section includes the explicit template marker.
    ai=[i for i in ai if 'INCOMPLETE DRAFT' in texts[i]]
    assert len(ai)==1 and ai[0]==len(doc)-1,'AI report must be a single final page'
    main_pages=ai[0]
    assert main_pages<=25 and main_pages>0
    assert path.stat().st_size <20_000_000
    assert 'Summary Sheet' in texts[0] and 'Contents' in texts[1]
    memo=[i for i,t in enumerate(texts) if 'To: SWITCH Governing Board' in t]
    assert len(memo)==1
    assert 'Proceed beyond the pilot' in texts[memo[0]],'Memo must fit one page'
    fonts=Counter();outside=[]
    for i,page in enumerate(doc):
        text=texts[i]
        assert re.search(r'Team\s+\d{9}',text),f'No control number on page {i+1}'
        assert re.search(r'Page\s+\d+',text),f'No page header on page {i+1}'
        assert not re.search(r'(?i)yigit|yiğit|bahçeşehir|bahcesehir|@gmail',text),'Identifying text found'
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines',[]):
                for span in line.get('spans',[]):
                    fonts[round(span['size'],2)]+=len(span['text'])
                    box=fitz.Rect(span['bbox'])
                    if box.x0<20 or box.x1>page.rect.width-20 or box.y0<15 or box.y1>page.rect.height-15:
                        outside.append(dict(page=i+1,text=span['text'],bbox=list(box)))
        if args.render_dir:
            out=Path(args.render_dir);out.mkdir(parents=True,exist_ok=True)
            page.get_pixmap(matrix=fitz.Matrix(1.25,1.25)).save(out/f'page_{i+1:02d}.png')
    assert not outside, outside
    report=dict(total_pages=len(doc),main_pages=main_pages,ai_report_pages=1,
                memo_page=memo[0]+1,file_bytes=path.stat().st_size,body_font_size_pdf_points=fonts.most_common(1)[0][0],
                note='12 TeX points render as approximately 11.96 PDF points; math scripts may be smaller.',
                font_character_counts=dict(fonts),summary_one_page=True,header_checks=True,no_identifying_team_text=True,
                unresolved=['Replace 000000000 with the actual nine-digit control number.',
                            'Complete the one-page AI usage report accurately.',
                            'Use the actual nine-digit control number as the submitted PDF filename.'],
                status='LAYOUT CHECKED; DRAFT INCOMPLETE FOR SUBMISSION')
    (ROOT/'results/pdf_check.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
