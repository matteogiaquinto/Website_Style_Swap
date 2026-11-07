"""Single-page visual transfer using rendered DOM and measured reference styles."""
import json
import re
from pathlib import Path
from html import escape
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from crawler import SCROLL_JS, USER_AGENT, load_robots

VIEWPORTS = [1440, 768, 390]
PROPS = ['display','flexDirection','flexWrap','justifyContent','alignItems','gap','gridTemplateColumns','width','maxWidth','minHeight','paddingTop','paddingRight','paddingBottom','paddingLeft','marginTop','marginBottom','fontSize','fontWeight','lineHeight','letterSpacing','textAlign','textTransform','borderRadius','borderWidth','borderStyle','boxShadow','objectFit','objectPosition','rowGap','columnGap']
SELECTORS = {'body':'body', 'header':'header, [role=banner]', 'nav':'nav', 'main':'main, [role=main]', 'section':'main section, main article, section', 'h1':'h1', 'h2':'h2', 'h3':'h3', 'p':'p', 'link':'a', 'button':'button, input[type=submit], a[class*=button], a[class*=btn]', 'image':'main img, img', 'footer':'footer, [role=contentinfo]'}
EXTRACT = r'''({selectors, props}) => {
 const visible = e => {const r=e.getBoundingClientRect(),s=getComputedStyle(e);return r.width>0 && r.height>0 && s.visibility !== 'hidden' && s.display !== 'none'};
 const out={}; for (const [role,sel] of Object.entries(selectors)) {const el=[...document.querySelectorAll(sel)].find(visible); if (!el) {out[role]=null;continue} const s=getComputedStyle(el),r=el.getBoundingClientRect();out[role]={selector:sel, tag:el.tagName.toLowerCase(), rect:{width:r.width,height:r.height}, computed:Object.fromEntries(props.map(p=>[p,s[p]]))};}
 const main=document.querySelector('main,[role=main]') || document.body;
 let sections=[...main.querySelectorAll('section,article')].filter(e=>!e.parentElement.closest('section,article'));
 if (!sections.length) sections=[...main.children].filter(e=>!['SCRIPT','STYLE','NOSCRIPT'].includes(e.tagName));
 out.sections=sections.slice(0,40).map((section,index)=>{
   const cs=getComputedStyle(section);
   const sectionStyle=Object.fromEntries(props.map(p=>[p,cs[p]]));
   const nodes=[section,...section.querySelectorAll('div,ul,ol')];
   const layouts=nodes.filter(e=>visible(e) && e.children.length>=2 && e.children.length<=8).map(e=>{
      const style=getComputedStyle(e), children=[...e.children].filter(visible);
      if(children.length<2 || !['flex','grid','inline-flex','inline-grid'].includes(style.display))return null;
      const r=children.map(c=>c.getBoundingClientRect());
      const horizontal=Math.abs(r[0].top-r[1].top)<Math.max(10,Math.min(r[0].height,r[1].height)*0.3) && r[1].left>r[0].left;
      return {childCount:children.length, imageChildren:children.filter(c=>c.matches('img,picture,video') || c.querySelector('img,picture,video')).length,
       display:style.display, direction:style.flexDirection, wrap:style.flexWrap, horizontal, gap:style.gap,
       alignItems:style.alignItems, justifyContent:style.justifyContent,
       widths:r.map(x=>Math.round(x.width)), radius:style.borderRadius};
   }).filter(Boolean).slice(0,30);
   return {index, computed:sectionStyle, layouts};
 });
 return out;
}'''
SOURCE = r'''() => {
 const original=document.documentElement, clone=original.cloneNode(true);
 const originals=[original,...original.querySelectorAll('*')], copies=[clone,...clone.querySelectorAll('*')];
 originals.forEach((el,i)=>{const c=copies[i]; if(!c)return; for(const a of ['href','src','poster','action']) {if(el.hasAttribute(a)){try{const u=new URL(el.getAttribute(a),document.baseURI); if(['http:','https:','mailto:','tel:'].includes(u.protocol)) c.setAttribute(a,u.href); else c.removeAttribute(a)}catch{c.removeAttribute(a)}}} if(el.tagName==='IMG' && el.currentSrc)c.setAttribute('src',el.currentSrc); c.removeAttribute('srcset'); c.removeAttribute('style'); for(const a of [...c.attributes]) if(a.name.toLowerCase().startsWith('on'))c.removeAttribute(a.name); });
 clone.querySelectorAll('script,style,link,base,iframe,object,embed,noscript,template').forEach(e=>e.remove());
 clone.querySelectorAll('a').forEach(e=>{e.setAttribute('target','_blank');e.setAttribute('rel','noopener noreferrer')});
 clone.querySelectorAll('form').forEach(e=>{e.removeAttribute('action');e.setAttribute('onsubmit','return false')});
 const main=original.querySelector('main,[role=main]') || original.querySelector('body');
 let sections=[...main.querySelectorAll('section,article')].filter(e=>!e.parentElement.closest('section,article'));
 if(!sections.length) sections=[...main.children].filter(e=>!['SCRIPT','STYLE','NOSCRIPT'].includes(e.tagName));
 const layouts=[];
 sections.slice(0,40).forEach((section,index)=>{
   const target=copies[originals.indexOf(section)]; if(target)target.setAttribute('data-rs-section',index);
   [section,...section.querySelectorAll('div,ul,ol')].forEach(el=>{
     const children=[...el.children].filter(c=>!['SCRIPT','STYLE','NOSCRIPT','TEMPLATE'].includes(c.tagName));
     if(children.length<2 || children.length>8)return;
     const imageChildren=children.filter(c=>c.matches('img,picture,video') || c.querySelector('img,picture,video')).length;
     const copy=copies[originals.indexOf(el)]; if(!copy)return;
     const id=layouts.length;copy.setAttribute('data-rs-layout',id);
     layouts.push({id,section:index,childCount:children.length,imageChildren});
   });
 });
 const b=getComputedStyle(document.body), h=document.querySelector('h1'), hs=h?getComputedStyle(h):b, a=document.querySelector('a'), as=a?getComputedStyle(a):b, button=document.querySelector('button,input[type=submit],a[class*=button],a[class*=btn]'), bs=button?getComputedStyle(button):null;
 return {html:'<!doctype html>'+clone.outerHTML, layouts, brand:{fontFamily:b.fontFamily,headingFontFamily:hs.fontFamily,bodyColor:b.color,backgroundColor:b.backgroundColor,linkColor:as.color,buttonBackground:bs?bs.backgroundColor:null,buttonColor:bs?bs.color:null}, title:document.title, counts:{headings:document.querySelectorAll('h1,h2,h3,h4,h5,h6').length,images:document.images.length,links:document.links.length,sections:document.querySelectorAll('section,article').length}};
}'''

def css_value(value, fallback):
    if not value or any(x in str(value).lower() for x in ['url(', ';', '{', '}', 'expression', 'javascript:']): return fallback
    return value

def generate_css(ref, brand):
    d=ref
    def v(role, prop, fallback):
        return css_value((d.get(role) or {}).get('computed',{}).get(prop), fallback)
    def rules(role, props):
        return ';'.join(f'{css}:{v(role, js, default)}' for css,js,default in props)
    typo=[('font-size','fontSize','16px'),('font-weight','fontWeight','400'),('line-height','lineHeight','normal'),('letter-spacing','letterSpacing','normal'),('text-align','textAlign','start'),('text-transform','textTransform','none')]
    spacing=[('padding-top','paddingTop','32px'),('padding-right','paddingRight','24px'),('padding-bottom','paddingBottom','32px'),('padding-left','paddingLeft','24px')]
    body_bg=css_value(brand.get('backgroundColor'), '#fff')
    button_bg=css_value(brand.get('buttonBackground'), 'transparent')
    button_color=css_value(brand.get('buttonColor'), 'inherit')
    if body_bg in ('rgba(0, 0, 0, 0)', 'transparent'): body_bg='#fff'
    return f'''*{{box-sizing:border-box}} html{{scroll-behavior:smooth}} body{{margin:0;background:{body_bg};color:{css_value(brand.get('bodyColor'),'#111')};font-family:{css_value(brand.get('fontFamily'),'sans-serif')};overflow-wrap:anywhere;{rules('body',typo)}}} img,svg,video{{max-width:100%;height:auto}} a{{color:{css_value(brand.get('linkColor'),'inherit')}}} h1,h2,h3,h4,h5,h6{{font-family:{css_value(brand.get('headingFontFamily'),'inherit')}}} header,[role=banner]{{{rules('header',spacing)}}} nav{{{rules('nav',[('display','display','flex'),('gap','gap','16px'),('align-items','alignItems','center'),('flex-wrap','flexWrap','wrap')])}}} main{{width:100%;max-width:{v('main','maxWidth','none')};margin-inline:auto}} section,article{{{rules('section',spacing)};margin-inline:auto}} h1{{{rules('h1',typo)}}} h2{{{rules('h2',typo)}}} h3{{{rules('h3',typo)}}} p{{{rules('p',typo)}}} button,input[type=submit],a[class*=button],a[class*=btn]{{background:{button_bg};color:{button_color};{rules('button',typo+spacing+[('border-radius','borderRadius','0px')])}}} img{{object-fit:{v('image','objectFit','contain')};border-radius:{v('image','borderRadius','0px')}}} footer,[role=contentinfo]{{{rules('footer',spacing)}}} @media(max-width:768px){{header,section,article,footer{{padding-left:20px;padding-right:20px}} h1{{font-size:clamp(2rem,8vw,{v('h1','fontSize','48px')})}} nav{{flex-wrap:wrap}}}}'''

def structural_css(data, source_layouts):
    """Match section containers only where their child and image counts agree."""
    matches = []
    desktop_sections = data['1440'].get('sections', [])
    for source in source_layouts:
        index = source['section']
        if index >= len(desktop_sections):
            continue
        candidates = desktop_sections[index].get('layouts', [])
        candidates = [c for c in candidates if c['childCount'] == source['childCount'] and c['imageChildren'] == source['imageChildren']]
        if candidates:
            matches.append({'source': source, 'candidate_index': desktop_sections[index]['layouts'].index(candidates[0])})

    def make_rules(width):
        sections = data[str(width)].get('sections', [])
        output = []
        for index, section in enumerate(sections):
            style = section['computed']
            props = [('padding-top','paddingTop'),('padding-right','paddingRight'),('padding-bottom','paddingBottom'),('padding-left','paddingLeft')]
            values = [f'{css}:{css_value(style.get(prop), "0px")}' for css,prop in props]
            output.append(f'[data-rs-section="{index}"]'+'{'+ ';'.join(values) +'}')
        for match in matches:
            source = match['source']
            if source['section'] >= len(sections): continue
            layouts = sections[source['section']]['layouts']
            candidates = [c for c in layouts if c['childCount']==source['childCount'] and c['imageChildren']==source['imageChildren']]
            if not candidates:
                if width < 1440:
                    output.append(f'[data-rs-layout="{source["id"]}"]'+'{display:flex;flex-direction:column}')
                continue
            c = candidates[0]
            selector = f'[data-rs-layout="{source["id"]}"]'
            gap = css_value(c['gap'], '0px')
            align = css_value(c['alignItems'], 'stretch')
            if c['horizontal']:
                widths = c['widths']
                proportions = ' '.join(f'minmax(0,{max(1,w)}fr)' for w in widths)
                output.append(selector+'{display:grid;grid-template-columns:'+proportions+';gap:'+gap+';align-items:'+align+'}')
                output.append(selector+'>*{min-width:0}')
            else:
                output.append(selector+'{display:flex;flex-direction:column;gap:'+gap+';align-items:'+align+'}')
        for role in ('h1','h2','h3','p'):
            style=(data[str(width)].get(role) or {}).get('computed',{})
            if style:
                pairs=[('font-size','fontSize'),('line-height','lineHeight'),('letter-spacing','letterSpacing'),('text-align','textAlign')]
                output.append(role+'{'+ ';'.join(f'{key}:{css_value(style.get(prop),"normal")}' for key,prop in pairs) +'}')
        return ''.join(output)
    css=make_rules(1440)+'@media(max-width:900px){'+make_rules(768)+'}@media(max-width:520px){'+make_rules(390)+'}'
    return css, matches

def build(old_url, ref_url, folder: Path, progress):
    folder.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser=p.chromium.launch(headless=True)
        except Exception:
            browser=p.chromium.launch(channel="chrome", headless=True)
        context=browser.new_context(viewport={'width':1440,'height':900}, user_agent=USER_AGENT, ignore_https_errors=False)
        page=context.new_page()
        def visit(url, name):
            if not load_robots(url).can_fetch(USER_AGENT,url): raise ValueError(f'{name}: accès interdit par robots.txt')
            try: response=page.goto(url,wait_until='domcontentloaded',timeout=45000)
            except PlaywrightTimeout: raise ValueError(f'{name}: délai de chargement dépassé')
            if not response or response.status >= 400: raise ValueError(f'{name}: réponse HTTP {response.status if response else "inconnue"}')
            if 'html' not in response.headers.get('content-type','').lower(): raise ValueError(f'{name}: la réponse ne contient pas une page HTML')
            page.wait_for_timeout(1500)
            page.evaluate(SCROLL_JS)
            return page.url
        progress('Lecture du contenu du site d’origine')
        source_url=visit(old_url,'Site d’origine')
        page.screenshot(path=str(folder/'source.png'),full_page=True,timeout=30000)
        source=page.evaluate(SOURCE)
        progress('Mesure du design de référence')
        final_ref=visit(ref_url,'Site de référence')
        data={}
        for width in VIEWPORTS:
            page.set_viewport_size({'width':width,'height':900})
            page.wait_for_timeout(350)
            data[str(width)]=page.evaluate(EXTRACT,{'selectors':SELECTORS,'props':PROPS})
            page.screenshot(path=str(folder/f'reference-{width}.png'),full_page=True,timeout=30000)
        browser.close()
    progress('Création de l’aperçu')
    structural, matches=structural_css(data,source['layouts'])
    css=generate_css(data['1440'],source['brand']) + structural
    head='<meta name="viewport" content="width=device-width, initial-scale=1"><style>'+css+'</style>'
    html=re.sub(r'<head(?:\s[^>]*)?>',lambda m:m.group(0)+head,source['html'],count=1,flags=re.I)
    if html==source['html']: html=head+html
    (folder/'index.html').write_text(html,encoding='utf-8')
    report={'source_url':source_url,'reference_url':final_ref,'source_brand':source['brand'],'source_counts':source['counts'],'reference_measurements':data,'layout_matches':matches,'limitations':['Les structures sont associées par position de section et nombre de blocs : les associations complexes peuvent être inexactes.','Couleurs et familles de polices du site source conservées conformément à la spécification.','JavaScript et fonctionnalités interactives désactivés dans l’aperçu.','Les ressources distantes restent hébergées sur le site source.','La feuille CSS de référence et les animations ne sont pas transférées.']}
    (folder/'design-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report
