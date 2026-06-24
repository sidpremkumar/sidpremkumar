#!/usr/bin/env python3
"""
skyline_gen.py - isometric GitHub contribution "skyline" (grow-and-stay)
Towers rise oldest->newest in a wave, then FREEZE at full height (no collapse).
Month labels run along the base as a timeline. Pure SMIL, no JS.
Usage: python3 skyline_gen.py <username> <output.svg>
"""
import sys, re, datetime, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (skyline-gen)"}
HW, HD = 11.0, 5.5
HMAX, HMIN = 80.0, 3.0
GROW = 0.8        # per-tower grow duration (s)
SPREAD = 3.2      # wave spread across all weeks (s)

def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read().decode("utf-8","replace")

def parse(html):
    tips={}
    for fid,txt in re.findall(r'for="(contribution-day-component-\d+-\d+)"[^>]*>([^<]*)</tool-tip>',html):
        t=txt.strip().lower(); m=re.match(r'([\d,]+)',t)
        tips[fid]=0 if t.startswith("no") else (int(m.group(1).replace(",",""))if m else 0)
    cells={}
    for tag in re.findall(r'<td[^>]*class="ContributionCalendar-day"[^>]*>',html):
        did=re.search(r'id="(contribution-day-component-(\d+)-(\d+))"',tag); dd=re.search(r'data-date="([0-9-]+)"',tag)
        if did and dd: cells[did.group(1)]=(int(did.group(2)),int(did.group(3)),dd.group(1))
    return tips,cells

def get_data(user):
    tips,cells=parse(fetch(f"https://github.com/users/{user}/contributions"))
    ncols=max(c for _,c,_ in cells.values())+1
    grid=[[0]*ncols for _ in range(7)]; coldate={}; ty=0
    for cid,(r,c,d) in cells.items():
        v=tips.get(cid,0); grid[r][c]=v; ty+=v
        if c not in coldate or d<coldate[c]: coldate[c]=d
    mx=max(max(r) for r in grid) or 1
    months=[]; seen=set()
    for c in sorted(coldate):
        dt=datetime.date.fromisoformat(coldate[c]); k=(dt.year,dt.month)
        if k not in seen: seen.add(k); months.append((c,dt.strftime("%b").upper()))
    life=0
    for y in range(2014,datetime.date.today().year+1):
        try:
            t,c=parse(fetch(f"https://github.com/users/{user}/contributions?from={y}-01-01&to={y}-12-31"))
            life+=sum(t.get(i,0) for i in c)
        except: pass
    return grid,ncols,mx,ty,life,months

def ramp(t):
    stops=[(0,(8,42,26)),(0.35,(15,110,60)),(0.7,(28,205,100)),(1.0,(0,255,136))]
    t=max(0.0,min(1.0,t))
    for i in range(len(stops)-1):
        a,(ar,ag,ab)=stops[i]; b,(br,bg,bb)=stops[i+1]
        if t<=b:
            f=0 if b==a else (t-a)/(b-a)
            return (ar+(br-ar)*f,ag+(bg-ag)*f,ab+(bb-ab)*f)
    return stops[-1][1]
def shade(rgb,k): return "#%02x%02x%02x"%tuple(max(0,min(255,int(v*k)))for v in rgb)
def pts(p): return " ".join(f"{x:.0f},{y:.0f}" for x,y in p)
def faces(cx,yb,h):
    N=(cx,yb-HD);E=(cx+HW,yb);S=(cx,yb+HD);W=(cx-HW,yb)
    Nt=(N[0],N[1]-h);Et=(E[0],E[1]-h);St=(S[0],S[1]-h);Wt=(W[0],W[1]-h)
    return [Wt,St,S,W],[St,Et,E,S],[Nt,Et,St,Wt]

def towers(grid,ncols,mx):
    out=[];minx=miny=1e9;maxx=maxy=-1e9
    for c in range(ncols):
        for r in range(7):
            v=grid[r][c];t=v/mx
            h=HMIN+(HMAX-HMIN)*(t**0.5)
            cx=(c-r)*HW;yb=(c+r)*HD
            d=min((c/max(ncols-1,1))*SPREAD+r*0.03, SPREAD+0.3)
            out.append({"order":c+r,"c":c,"cx":cx,"yb":yb,"h":h,"v":v,"rgb":ramp(t),"delay":d})
            minx=min(minx,cx-HW);maxx=max(maxx,cx+HW)
            miny=min(miny,yb-h-HD);maxy=max(maxy,yb+HD)
    out.sort(key=lambda z:(z["order"],z["c"]))
    return out,(minx,miny,maxx,maxy)

def frame_header(W,lt,ty,bd):
    return (f'<rect x="10" y="10" width="{W-20}" height="30" rx="9" fill="#06150c"/>'
            f'<rect x="10" y="30" width="{W-20}" height="10" fill="#06150c"/>'
            f'<circle cx="30" cy="25" r="5" fill="#ff5f56"/><circle cx="50" cy="25" r="5" fill="#ffbd2e"/><circle cx="70" cy="25" r="5" fill="#27c93f"/>'
            f'<text x="{W//2}" y="29" text-anchor="middle" fill="#3fae6f" font-size="13" letter-spacing="1">sid@matrix: ~/contributions</text>'
            f'<text x="28" y="62" fill="#7df9aa" font-size="15" filter="url(#g)"><tspan fill="#39d65a">$</tspan> git log --author=sid --all --oneline | wc -l</text>'
            f'<text x="28" y="84" fill="#e8fff0" font-size="16" filter="url(#g)"><tspan fill="#00ff88" font-size="19" font-weight="bold">{lt}</tspan>  commits  <tspan fill="#39d65a">::</tspan>  <tspan fill="#00ff88">{ty}</tspan> this year  <tspan fill="#39d65a">::</tspan>  busiest day <tspan fill="#00ff88">{bd}</tspan></text>')

def svg_shell(W,H,inner,updated):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="\'Courier New\',Courier,monospace">'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#03100a"/><stop offset="1" stop-color="#000"/></linearGradient>'
            f'<filter id="g" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="1.0"/><feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>'
            f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="9" fill="#000" fill-opacity="0.55" stroke="#0f3d22" stroke-width="1.4"/>'
            f'{inner}'
            f'<text x="{W-26}" y="{H-18}" text-anchor="end" fill="#2c6b46" font-size="11">updated {updated} \u00b7 last 12 months</text></svg>')

def anim_once(flat,full,delay):
    return (f'<animate attributeName="points" begin="{delay:.2f}s" dur="{GROW}s" '
            f'calcMode="spline" keySplines="0.34 0 0.2 1" keyTimes="0;1" '
            f'values="{flat};{full}" fill="freeze"/>')

def build(grid,ncols,mx,ty,life,months,animate=True):
    tw,(minx,miny,maxx,maxy)=towers(grid,ncols,mx)
    pad=34; ox=pad-minx; oy=pad-miny+86
    LABELBAND=42
    W=int(maxx-minx+pad*2); H=int(maxy-miny+pad*2+86+LABELBAND)
    updated=datetime.date.today().isoformat()
    body=[]
    for d in tw:
        cx,yb,h,rgb,v=d["cx"],d["yb"],d["h"],d["rgb"],d["v"]
        Lf,Rf,Tf=faces(cx,yb,h)
        if v==0:
            body.append(f'<polygon points="{pts(faces(cx,yb,HMIN)[2])}" fill="{shade(rgb,1.0)}"/>')
            continue
        if not animate:
            body.append(f'<polygon points="{pts(Lf)}" fill="{shade(rgb,0.42)}"/><polygon points="{pts(Rf)}" fill="{shade(rgb,0.66)}"/><polygon points="{pts(Tf)}" fill="{shade(rgb,1.0)}"/>')
            continue
        L0,R0,T0=faces(cx,yb,0.0); dl=d["delay"]
        for ff,fl,k in ((Lf,L0,0.42),(Rf,R0,0.66),(Tf,T0,1.0)):
            body.append(f'<polygon points="{pts(fl)}" fill="{shade(rgb,k)}">{anim_once(pts(fl),pts(ff),dl)}</polygon>')
    # ---- month timeline along the base (front r=6 edge) ----
    labels=[]
    R=6
    # faint baseline following the front edge
    x0=ox+(0-R)*HW; y0=oy+(0+R)*HD+HD; x1=ox+((ncols-1)-R)*HW; y1=oy+((ncols-1)+R)*HD+HD
    labels.append(f'<line x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}" stroke="#10532e" stroke-width="1"/>')
    for (c,lbl) in months:
        bx=ox+(c-R)*HW; by=oy+(c+R)*HD+HD
        labels.append(f'<line x1="{bx:.0f}" y1="{by:.0f}" x2="{bx:.0f}" y2="{by+7:.0f}" stroke="#1c7a44" stroke-width="1.4"/>'
                      f'<text x="{bx:.0f}" y="{by+19:.0f}" text-anchor="middle" fill="#43b873" font-size="11" letter-spacing="1">{lbl}</text>')
    inner=(frame_header(W,f"{life:,}",f"{ty:,}",str(mx))
           + f'<g transform="translate({ox:.0f},{oy:.0f})" filter="url(#g)">{"".join(body)}</g>'
           + "".join(labels))
    return svg_shell(W,H,inner,updated)

if __name__=="__main__":
    user=sys.argv[1] if len(sys.argv)>1 else "sidpremkumar"
    out =sys.argv[2] if len(sys.argv)>2 else "skyline.svg"
    grid,ncols,mx,ty,life,months=get_data(user)
    open(out,"w").write(build(grid,ncols,mx,ty,life,months,animate=True))
    print(f"wrote {out} | life={life:,} year={ty:,} busiest={mx} months={len(months)}")
