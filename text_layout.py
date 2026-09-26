"""Metric-based layout for tight PDF text selections, without HTML box padding."""
import hashlib
import re
from pathlib import Path
import pymupdf as fitz


def choose_font(style, text):
    data = style.get('font_data')
    if data:
        font = fitz.Font(fontbuffer=data)
        if all(font.has_glyph(ord(c)) for c in text if not c.isspace()):
            return font
    family = style.get('family','sans-serif')
    base = {'sans-serif':'arial','serif':'times','monospace':'cour'}.get(family,'arial')
    suffix = ('bi' if style.get('bold') and style.get('italic') else 'bd' if style.get('bold') else 'i' if style.get('italic') else '')
    candidate = Path('C:/Windows/Fonts') / (base+suffix+'.ttf')
    font = fitz.Font(fontfile=str(candidate)) if candidate.exists() else fitz.Font('helv')
    if not all(font.has_glyph(ord(c)) for c in text if not c.isspace()):
        raise ValueError('Seçilen font yeni metindeki bazı karakterleri desteklemiyor.')
    return font


def lines_for(font,text,size,width):
    lines=[]
    for paragraph in text.replace('\r\n','\n').replace('\r','\n').split('\n'):
        line=''
        for word in re.findall(r'\S+',paragraph):
            candidate = line+' '+word if line else word
            if font.text_length(candidate,fontsize=size) <= width:
                line=candidate
                continue
            if line:
                lines.append(line)
                line=''
            for char in word:
                if font.text_length(line+char,fontsize=size)>width:
                    if not line:
                        return None
                    lines.append(line)
                    line=''
                line+=char
        lines.append(line)
    return lines


def place_text(page,rect,text,size,auto_fit,style):
    rect=fitz.Rect(rect)
    font=choose_font(style,text)
    ascent,descent=font.ascender,font.descender
    leading=max(1.1,ascent-descent)
    def layout(s):
        lines=lines_for(font,text,s,max(0,rect.width-0.04))
        if lines is None or not lines:
            return None
        height=(ascent-descent)*s+(len(lines)-1)*leading*s
        return lines if height<=rect.height-0.04 else None
    used=size
    lines=layout(size)
    if lines is None and auto_fit and size>6:
        low,high=6.0,size
        lines=layout(low)
        if lines is not None:
            for _ in range(24):
                mid=(low+high)/2
                if layout(mid) is None:
                    high=mid
                else:
                    low=mid
            used=low
            lines=layout(used)
    if lines is None:
        raise ValueError('Metin sığmıyor. Yazı alanının genişliğini veya yüksekliğini artırıp yeniden Uygula’ya basın.')
    buffer=font.buffer
    name='Studio'+hashlib.sha256(buffer).hexdigest()[:12]
    page.insert_font(fontname=name,fontbuffer=buffer)
    color=style.get('color','#172033').lstrip('#')
    rgb=tuple(int(color[i:i+2],16)/255 for i in (0,2,4))
    baseline=rect.y0+0.02+ascent*used
    for line in lines:
        if line:
            page.insert_text((rect.x0+0.02,baseline),line,fontname=name,fontsize=used,color=rgb)
        baseline+=leading*used
    return used
